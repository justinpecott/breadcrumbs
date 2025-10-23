import os
import sys
import json
import tomllib
import tomli_w
from datetime import datetime
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
import time


def get_subscriptions(email: str, password: str) -> list[dict]:
    """
    Fetch all subscriptions from Feedbin API.

    Args:
        email: Feedbin account email
        password: Feedbin account password

    Returns:
        List of subscription dictionaries

    Raises:
        requests.HTTPError: If the API request fails
    """
    url = "https://api.feedbin.com/v2/subscriptions.json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(email, password)
    )

    response.raise_for_status()
    return response.json()


def get_entries(email: str, password: str, subscription_id: int) -> list[dict]:
    """
    Fetch all entries for a specific subscription from Feedbin API.

    Args:
        email: Feedbin account email
        password: Feedbin account password
        subscription_id: ID of the subscription to fetch entries for

    Returns:
        List of entry dictionaries

    Raises:
        requests.HTTPError: If the API request fails
    """
    url = f"https://api.feedbin.com/v2/feeds/{subscription_id}/entries.json"
    # print(url)
    # url = "https://api.feedbin.com/v2/entries.json"
    # print(url)
    response = requests.get(
        url,
        auth=HTTPBasicAuth(email, password)
    )

    response.raise_for_status()
    return response.json()


def get_starred_entries(email: str, password: str) -> list[dict]:
    """
    Fetch all starred entries from Feedbin API.

    Args:
        email: Feedbin account email
        password: Feedbin account password

    Returns:
        List of starred entry IDs

    Raises:
        requests.HTTPError: If the API request fails
    """
    url = "https://api.feedbin.com/v2/starred_entries.json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(email, password)
    )

    response.raise_for_status()
    return response.json()


def get_entries_by_ids(email: str, password: str, entry_ids: list[int]) -> list[dict]:
    """
    Fetch specific entries by their IDs from Feedbin API.

    Args:
        email: Feedbin account email
        password: Feedbin account password
        entry_ids: List of entry IDs to fetch

    Returns:
        List of entry dictionaries

    Raises:
        requests.HTTPError: If the API request fails
    """
    url = "https://api.feedbin.com/v2/entries.json"

    # Feedbin API accepts comma-separated IDs as a query parameter
    params = {"ids": ",".join(map(str, entry_ids))}

    response = requests.get(
        url,
        auth=HTTPBasicAuth(email, password),
        params=params
    )

    response.raise_for_status()
    return response.json()


def summarize_with_kagi(url: str, api_key: str, engine: str = "cecil", summary_type: str = "summary") -> str | None:
    """
    Generate a summary using Kagi Universal Summarizer API.

    Args:
        url: URL of the content to summarize
        api_key: Kagi API key
        engine: Kagi engine to use (cecil, agnes, muriel)
        summary_type: Type of summary (summary or takeaway)

    Returns:
        Summary text or None if summarization fails

    Raises:
        None (errors are caught and logged)
    """
    api_url = "https://kagi.com/api/v0/summarize"

    headers = {
        "Authorization": f"Bot {api_key}"
    }

    data = {
        "url": url,
        "engine": engine,
        "summary_type": summary_type
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        return result.get("data", {}).get("output")
    except requests.RequestException as e:
        print(f"  Warning: Failed to summarize {url}: {e}")
        return None


def load_config(config_path: str = "config.toml") -> dict:
    """
    Load configuration from a TOML file.

    Args:
        config_path: Path to the config file (default: config.toml)

    Returns:
        Dictionary containing configuration values
    """
    default_config = {
        "output_dir": "./dist",
        "kagi_engine": "cecil",
        "kagi_summary_type": "summary"
    }

    config_file = Path(config_path)

    if not config_file.exists():
        print(f"Config file not found at {config_path}, creating default config...")
        with open(config_file, 'wb') as f:
            tomli_w.dump(default_config, f)
        print(f"Created {config_path} with default settings\n")
        return default_config

    try:
        with open(config_file, 'rb') as f:
            config = tomllib.load(f)

        # Merge with defaults for any missing keys
        for key, value in default_config.items():
            if key not in config:
                config[key] = value

        return config
    except (tomllib.TOMLDecodeError, IOError) as e:
        print(f"Warning: Could not parse {config_path}: {e}")
        print("Using default configuration\n")
        return default_config


def main():
    # Load configuration
    config = load_config()

    # Initialize directory structure
    print("Initializing directory structure...")
    dist_dir = Path(config["output_dir"])
    data_dir = dist_dir / "data"
    archive_dir = dist_dir / "archive"

    data_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created directories: {data_dir}, {archive_dir}\n")

    # Get credentials from environment variables
    email = os.getenv("FEEDBIN_EMAIL")
    password = os.getenv("FEEDBIN_PASSWORD")
    kagi_api_key = os.getenv("KAGI_API_KEY")

    if not email or not password:
        print("Error: Please set FEEDBIN_EMAIL and FEEDBIN_PASSWORD environment variables")
        print("\nExample:")
        print("  export FEEDBIN_EMAIL='your-email@example.com'")
        print("  export FEEDBIN_PASSWORD='your-password'")
        sys.exit(1)

    if not kagi_api_key:
        print("Warning: KAGI_API_KEY not set. Summaries will not be generated.")
        print("  export KAGI_API_KEY='your-kagi-api-key'")
        print()

    try:
        print("Fetching subscriptions...")
        subscriptions = get_subscriptions(email, password)

        print(f"\nFound {len(subscriptions)} subscription(s)")

        # Find the "Pages" subscription
        pages_subscription = None
        for sub in subscriptions:
            if sub.get('title') == 'Pages':
                pages_subscription = sub
                break

        if not pages_subscription:
            print("\nError: Could not find a subscription titled 'Pages'")
            print("\nAvailable subscriptions:")
            for sub in subscriptions:
                print(f"  - {sub.get('title')}")
            sys.exit(1)

        print(f"\nFound 'Pages' subscription:")
        print(f"  ID: {pages_subscription.get('id')}")
        print(f"  Feed ID: {pages_subscription.get('feed_id')}")
        print(f"  Feed URL: {pages_subscription.get('feed_url')}")

        feed_id = pages_subscription.get('feed_id')

        # Fetch entries for the Pages feed
        print(f"\nFetching entries for 'Pages' feed (ID: {feed_id})...")
        pages_entries = get_entries(email, password, feed_id)
        print(f"Found {len(pages_entries)} Pages entries")

        # Fetch starred entries
        print(f"\nFetching starred entries...")
        starred_entry_ids = get_starred_entries(email, password)
        print(f"Found {len(starred_entry_ids)} starred entry IDs")

        # Fetch full entry data for starred entries
        starred_entries = []
        if starred_entry_ids:
            print(f"Fetching full data for starred entries...")
            starred_entries = get_entries_by_ids(email, password, starred_entry_ids)
            print(f"Retrieved {len(starred_entries)} starred entries")

        # Merge entries and track their types
        # First add all pages entries
        all_entries = {}
        for entry in pages_entries:
            entry['entry_type'] = 'page'
            all_entries[entry['id']] = entry

        # Then add starred entries (if an entry is both page and starred, mark it as starred)
        for entry in starred_entries:
            if entry['id'] in all_entries:
                all_entries[entry['id']]['entry_type'] = 'star'
            else:
                entry['entry_type'] = 'star'
                all_entries[entry['id']] = entry

        entries = list(all_entries.values())
        print(f"\nTotal unique entries: {len(entries)}\n")

        # Print entries
        for entry in entries:
            print(f"ID: {entry.get('id')}")
            print(f"  Feed ID: {entry.get('feed_id')}")
            print(f"  Title: {entry.get('title')}")
            print(f"  Author: {entry.get('author')}")
            print(f"  URL: {entry.get('url')}")
            print(f"  Published: {entry.get('published')}")
            print(f"  Summary: {entry.get('summary', 'N/A')[:100]}...")
            print()

        # Prepare entries for JSON export
        filtered_entries = []
        for entry in entries:
            filtered_entry = {
                "id": entry.get("id"),
                "title": entry.get("title"),
                "url": entry.get("url"),
                "published": entry.get("published"),
                "created_at": entry.get("created_at"),
                "entry_type": entry.get("entry_type"),
                "tldr": "",
                "archive_file": ""
            }
            filtered_entries.append(filtered_entry)

        # Create output structure with metadata
        now = datetime.now()
        output_data = {
            "generated_at": now.isoformat(),
            "entries": filtered_entries
        }

        # Define output file path
        output_file = data_dir / "data.json"

        # If data.json exists, merge with existing data
        existing_entries = []
        if output_file.exists():
            print(f"\nLoading existing data.json...")
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_generated_at = existing_data.get('generated_at', '')
                    existing_entries = existing_data.get('entries', [])

                    print(f"Found {len(existing_entries)} existing entries")

                    # Create backup with its generated_at timestamp
                    if existing_generated_at:
                        backup_dt = datetime.fromisoformat(existing_generated_at)
                        backup_timestamp = backup_dt.strftime("%Y%m%d-%H%M%S")
                    else:
                        # Fallback to current time if no timestamp in file
                        backup_timestamp = now.strftime("%Y%m%d-%H%M%S")

                    backup_file = data_dir / f"data-{backup_timestamp}.json"

                    # Copy existing file to backup
                    with open(backup_file, 'w', encoding='utf-8') as backup_f:
                        json.dump(existing_data, backup_f, indent=2, ensure_ascii=False)

                    print(f"Created backup: {backup_file}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not parse existing data.json, starting fresh: {e}")
                existing_entries = []

        # Merge entries: keep existing entries, add only new ones
        existing_ids = {entry['id'] for entry in existing_entries}
        new_entries_count = 0
        new_entries_to_add = []

        # Collect new entries
        for entry in filtered_entries:
            if entry['id'] not in existing_ids:
                new_entries_to_add.append(entry)

        # Generate summaries for new entries
        if new_entries_to_add and kagi_api_key:
            print(f"\nGenerating summaries for {len(new_entries_to_add)} new entries...")
            for i, entry in enumerate(new_entries_to_add, 1):
                url = entry.get('url')
                if url:
                    print(f"  [{i}/{len(new_entries_to_add)}] Summarizing: {entry.get('title', 'Untitled')}")
                    summary = summarize_with_kagi(
                        url,
                        kagi_api_key,
                        engine=config["kagi_engine"],
                        summary_type=config["kagi_summary_type"]
                    )
                    if summary:
                        entry['tldr'] = summary
                    # Be respectful to the API - add a small delay between requests
                    if i < len(new_entries_to_add):
                        time.sleep(0.5)
                else:
                    print(f"  [{i}/{len(new_entries_to_add)}] Skipping (no URL): {entry.get('title', 'Untitled')}")

        # Add new entries to existing list
        existing_entries.extend(new_entries_to_add)
        new_entries_count = len(new_entries_to_add)

        print(f"\nAdded {new_entries_count} new entries")
        print(f"Total entries after merge: {len(existing_entries)}")

        # Update output data with merged entries
        output_data['entries'] = existing_entries

        # Write merged JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nWrote {len(existing_entries)} total entries to {output_file}")

    except requests.HTTPError as e:
        if e.response.status_code == 401:
            print("Error: Authentication failed. Please check your credentials.")
        else:
            print(f"Error: API request failed with status {e.response.status_code}")
            print(f"Details: {e.response.text}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Error: Network request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
