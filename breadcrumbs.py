import json
import logging
import os
import re
import subprocess
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import tomli_w
from jinja2 import Environment, FileSystemLoader
from requests.auth import HTTPBasicAuth


def setup_logging(log_dir: Path, log_level: str = "INFO") -> None:
    """
    Set up logging to both console and file.

    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"breadcrumbs-{timestamp}.log"

    # Convert log level string to logging constant
    log_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.info(f"Logging to {log_file}")


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

    response = requests.get(url, auth=HTTPBasicAuth(email, password))

    response.raise_for_status()
    return response.json()


def get_entries(email: str, password: str, subscription_id: int) -> list[dict]:
    """
    Fetch all entries for a specific subscription from Feedbin API.
    Handles pagination to retrieve all entries (100 per page).

    Args:
        email: Feedbin account email
        password: Feedbin account password
        subscription_id: ID of the subscription to fetch entries for

    Returns:
        List of entry dictionaries

    Raises:
        requests.HTTPError: If the API request fails
    """
    all_entries = []
    url = f"https://api.feedbin.com/v2/feeds/{subscription_id}/entries.json"
    page = 1

    while url:
        response = requests.get(url, auth=HTTPBasicAuth(email, password))
        response.raise_for_status()

        entries = response.json()
        all_entries.extend(entries)
        logging.debug(f"Fetched page {page} ({len(entries)} entries)")

        # Check for next page in Link header
        url = None
        if "Link" in response.headers:
            links = response.headers["Link"].split(", ")
            for link in links:
                if 'rel="next"' in link:
                    # Extract URL from <URL>; rel="next" format
                    url = link[link.find("<") + 1 : link.find(">")]
                    page += 1
                    break

    return all_entries


def get_starred_entries(email: str, password: str) -> list[dict]:
    """
    Fetch all starred entry IDs from Feedbin API.
    Handles pagination to retrieve all IDs (100 per page).

    Args:
        email: Feedbin account email
        password: Feedbin account password

    Returns:
        List of starred entry IDs

    Raises:
        requests.HTTPError: If the API request fails
    """
    all_ids = []
    url = "https://api.feedbin.com/v2/starred_entries.json"
    page = 1

    while url:
        response = requests.get(url, auth=HTTPBasicAuth(email, password))
        response.raise_for_status()

        ids = response.json()
        all_ids.extend(ids)
        logging.debug(f"Fetched starred IDs page {page} ({len(ids)} IDs)")

        # Check for next page in Link header
        url = None
        if "Link" in response.headers:
            links = response.headers["Link"].split(", ")
            for link in links:
                if 'rel="next"' in link:
                    # Extract URL from <URL>; rel="next" format
                    url = link[link.find("<") + 1 : link.find(">")]
                    page += 1
                    break

    return all_ids


def get_entries_by_ids(email: str, password: str, entry_ids: list[int]) -> list[dict]:
    """
    Fetch specific entries by their IDs from Feedbin API.
    Handles batching if more than 100 IDs are provided.

    Args:
        email: Feedbin account email
        password: Feedbin account password
        entry_ids: List of entry IDs to fetch

    Returns:
        List of entry dictionaries

    Raises:
        requests.HTTPError: If the API request fails
    """
    all_entries = []
    url = "https://api.feedbin.com/v2/entries.json"

    # Batch IDs in groups of 100 to avoid URL length issues
    batch_size = 100
    total_batches = (len(entry_ids) + batch_size - 1) // batch_size

    for batch_num, i in enumerate(range(0, len(entry_ids), batch_size), 1):
        batch = entry_ids[i : i + batch_size]
        params = {"ids": ",".join(map(str, batch))}

        response = requests.get(url, auth=HTTPBasicAuth(email, password), params=params)
        response.raise_for_status()

        entries = response.json()
        all_entries.extend(entries)
        logging.debug(f"Fetched entry batch {batch_num}/{total_batches} ({len(entries)} entries)")

    return all_entries


def summarize_with_kagi(
    url: str, api_key: str, engine: str = "cecil", summary_type: str = "summary"
) -> str | None:
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

    headers = {"Authorization": f"Bot {api_key}"}

    data = {"url": url, "engine": engine, "summary_type": summary_type}

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=30)

        response.raise_for_status()
        result = response.json()

        return result.get("data", {}).get("output")
    except requests.RequestException as e:
        logging.warning(f"Failed to summarize {url}: {e}")
        return None


def url_to_slug(url: str) -> str:
    """
    Convert a URL to a safe filename slug.

    Args:
        url: URL to convert

    Returns:
        Slug suitable for use as a filename
    """
    # Parse the URL
    parsed = urlparse(url)

    # Combine domain and path
    slug_parts = []

    # Add domain (remove www. prefix)
    domain = parsed.netloc.replace("www.", "")
    slug_parts.append(domain)

    # Add path components (remove leading/trailing slashes)
    path = parsed.path.strip("/")
    if path:
        slug_parts.append(path)

    # Join with underscores and clean up
    slug = "_".join(slug_parts)

    # Remove or replace special characters
    slug = re.sub(r"[^\w\-.]", "_", slug)

    # Remove consecutive underscores
    slug = re.sub(r"_+", "_", slug)

    # Trim to reasonable length (keep extension if present)
    if len(slug) > 200:
        slug = slug[:200]

    # Remove trailing underscores/dashes
    slug = slug.rstrip("_-")

    return slug


def archive_entry(
    url: str,
    archive_dir: Path,
    entry_id: int,
    no_video: bool = True,
    no_audio: bool = True,
    no_js: bool = True,
) -> str | None:
    """
    Archive a web page using monolith.

    Args:
        url: URL to archive
        archive_dir: Directory to save archived files
        entry_id: Entry ID for fallback naming
        no_video: Remove video sources (default: True)
        no_audio: Remove audio sources (default: True)
        no_js: Remove JavaScript (default: True)

    Returns:
        Relative path to the archived file, or None if archiving fails
    """
    try:
        # Generate filename from URL
        slug = url_to_slug(url)

        # Add entry ID to ensure uniqueness
        filename = f"{entry_id}_{slug}.html"
        output_path = archive_dir / filename

        # Run monolith to archive the page
        # Build command with optional flags based on configuration
        logging.info(f"Archiving to: {filename}")

        cmd = ["monolith", url, "-o", str(output_path)]
        if no_video:
            cmd.append("--no-video")
        if no_audio:
            cmd.append("--no-audio")
        if no_js:
            cmd.append("--no-js")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and output_path.exists():
            # Return relative path from dist directory
            return f"archive/{filename}"
        else:
            logging.warning(f"monolith failed with exit code {result.returncode}")
            if result.stderr:
                logging.error(f"Error: {result.stderr[:200]}")
            return None

    except subprocess.TimeoutExpired:
        logging.warning("Archiving timed out after 60 seconds")
        return None
    except Exception as e:
        logging.warning(f"Failed to archive {url}: {e}")
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
        "log_level": "INFO",
    }

    config_file = Path(config_path)

    if not config_file.exists():
        logging.info(f"Config file not found at {config_path}, creating default config...")
        with open(config_file, "wb") as f:
            tomli_w.dump(default_config, f)
        logging.info(f"Created {config_path} with default settings")
        return default_config

    try:
        with open(config_file, "rb") as f:
            config = tomllib.load(f)

        # Merge with defaults for any missing keys
        for key, value in default_config.items():
            if key not in config:
                config[key] = value

        return config
    except (tomllib.TOMLDecodeError, IOError) as e:
        logging.warning(f"Could not parse {config_path}: {e}")
        logging.info("Using default configuration")
        return default_config


def render_html(output_data: dict, output_file: Path) -> None:
    """
    Render HTML page from entry data using Jinja2 template.

    Args:
        output_data: Dictionary containing entries and metadata
        output_file: Path to save the HTML file

    Raises:
        IOError: If template cannot be read or HTML cannot be written
    """
    # Set up Jinja2 environment
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))

    # Add custom filter for date formatting
    def format_date(date_string: str) -> str:
        """Convert ISO date to readable format (e.g., 'Jan 15, 2024')"""
        try:
            if not date_string:
                return ""
            # Parse ISO format and format as "Jan 15, 2024"
            dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y")
        except (ValueError, AttributeError):
            # If parsing fails, return first 10 chars as fallback
            return date_string[:10] if date_string else ""

    # Add custom filter for datetime formatting
    def format_datetime(date_string: str) -> str:
        """Convert ISO datetime to readable format (e.g., 'Jan 15, 2024 at 3:45 PM')"""
        try:
            if not date_string:
                return ""
            # Parse ISO format and format as "Jan 15, 2024 at 3:45 PM"
            dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y at %I:%M %p")
        except (ValueError, AttributeError):
            # If parsing fails, return the original string
            return date_string

    env.filters["format_date"] = format_date
    env.filters["format_datetime"] = format_datetime

    template = env.get_template("index.html")

    # Render template with data
    html_content = template.render(
        entries=output_data.get("entries", []),
        generated_at=output_data.get("generated_at", ""),
    )

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    logging.info(f"Generated HTML page: {output_file}")


def render_content_archive(entry: dict, archive_dir: Path) -> str | None:
    """
    Render a content archive HTML file for a single entry using Jinja2 template.

    Args:
        entry: Entry dictionary containing content and metadata
        archive_dir: Directory to save the content archive file

    Returns:
        Relative path to the content archive file, or None if rendering fails

    Raises:
        IOError: If template cannot be read or HTML cannot be written
    """
    try:
        # Generate filename with 'content-' prefix to avoid collision with monolith archives
        entry_id = entry.get("id")
        slug = url_to_slug(entry.get("url", ""))
        filename = f"content-{entry_id}_{slug}.html"
        output_path = archive_dir / filename

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(template_dir))

        # Add custom filter for date formatting
        def format_date(date_string: str) -> str:
            """Convert ISO date to readable format (e.g., 'Jan 15, 2024')"""
            try:
                if not date_string:
                    return ""
                # Parse ISO format and format as "Jan 15, 2024"
                dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
                return dt.strftime("%b %d, %Y")
            except (ValueError, AttributeError):
                # If parsing fails, return first 10 chars as fallback
                return date_string[:10] if date_string else ""

        env.filters["format_date"] = format_date

        template = env.get_template("entry.html")

        # Render template with entry data
        html_content = template.render(
            title=entry.get("title", "Untitled"),
            url=entry.get("url", ""),
            published=format_date(entry.get("published", "")),
            created_at=format_date(entry.get("created_at", "")),
            entry_type=entry.get("entry_type", "page"),
            content=entry.get("content", ""),
            archive_file=entry.get("archive_file", ""),
        )

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"Generated content archive: {filename}")

        # Return relative path from dist directory
        return f"archive/{filename}"

    except Exception as e:
        logging.warning(f"Failed to render content archive for entry {entry.get('id')}: {e}")
        return None


def main():
    # Load configuration
    config = load_config()

    # Initialize directory structure
    dist_dir = Path(config["output_dir"])
    data_dir = dist_dir / "data"
    archive_dir = dist_dir / "archive"
    log_dir = dist_dir / "logs"

    data_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging
    setup_logging(log_dir, config.get("log_level", "INFO"))

    logging.info("Initializing directory structure...")
    logging.info(f"Created directories: {data_dir}, {archive_dir}")

    # Get credentials from environment variables
    email = os.getenv("FEEDBIN_EMAIL")
    password = os.getenv("FEEDBIN_PASSWORD")
    kagi_api_key = os.getenv("KAGI_API_KEY")

    if not email or not password:
        logging.error(
            "Please set FEEDBIN_EMAIL and FEEDBIN_PASSWORD environment variables"
        )
        logging.info("Example:")
        logging.info("  export FEEDBIN_EMAIL='your-email@example.com'")
        logging.info("  export FEEDBIN_PASSWORD='your-password'")
        sys.exit(1)

    if not kagi_api_key:
        logging.warning("KAGI_API_KEY not set. Summaries will not be generated.")
        logging.info("  export KAGI_API_KEY='your-kagi-api-key'")

    try:
        logging.info("Fetching subscriptions...")
        subscriptions = get_subscriptions(email, password)

        logging.info(f"Found {len(subscriptions)} subscription(s)")

        # Find the "Pages" subscription
        pages_subscription = None
        for sub in subscriptions:
            if sub.get("title") == "Pages":
                pages_subscription = sub
                break

        if not pages_subscription:
            logging.error("Could not find a subscription titled 'Pages'")
            logging.info("Available subscriptions:")
            for sub in subscriptions:
                logging.info(f"  - {sub.get('title')}")
            sys.exit(1)

        logging.info("Found 'Pages' subscription:")
        logging.info(f"  ID: {pages_subscription.get('id')}")
        logging.info(f"  Feed ID: {pages_subscription.get('feed_id')}")
        logging.info(f"  Feed URL: {pages_subscription.get('feed_url')}")

        feed_id = pages_subscription.get("feed_id")

        # Fetch entries for the Pages feed
        logging.info(f"Fetching entries for 'Pages' feed (ID: {feed_id})...")
        pages_entries = get_entries(email, password, feed_id)
        logging.info(f"Found {len(pages_entries)} Pages entries")

        # Fetch starred entries
        logging.info("Fetching starred entries...")
        starred_entry_ids = get_starred_entries(email, password)
        logging.info(f"Found {len(starred_entry_ids)} starred entry IDs")

        # Fetch full entry data for starred entries
        starred_entries = []
        if starred_entry_ids:
            logging.info("Fetching full data for starred entries...")
            starred_entries = get_entries_by_ids(email, password, starred_entry_ids)
            logging.info(f"Retrieved {len(starred_entries)} starred entries")

        # Merge entries and track their types
        # First add all pages entries
        all_entries = {}
        for entry in pages_entries:
            entry["entry_type"] = "page"
            all_entries[entry["id"]] = entry

        # Then add starred entries (if an entry is both page and starred, mark it as starred)
        for entry in starred_entries:
            if entry["id"] in all_entries:
                all_entries[entry["id"]]["entry_type"] = "star"
            else:
                entry["entry_type"] = "star"
                all_entries[entry["id"]] = entry

        entries = list(all_entries.values())
        logging.info(f"Total unique entries: {len(entries)}")

        # Create a mapping from entry ID to full entry data (for content archive generation)
        full_entries_map = {entry["id"]: entry for entry in entries}

        # Print entries
        for entry in entries:
            logging.debug(f"ID: {entry.get('id')}")
            logging.debug(f"  Feed ID: {entry.get('feed_id')}")
            logging.debug(f"  Title: {entry.get('title')}")
            logging.debug(f"  Author: {entry.get('author')}")
            logging.debug(f"  URL: {entry.get('url')}")
            logging.debug(f"  Published: {entry.get('published')}")
            logging.debug(f"  Summary: {entry.get('summary', 'N/A')[:100]}...")
            pass

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
                "content": entry.get("content", ""),
                "summary": entry.get("summary", ""),  # Feedbin's summary
                "tldr": "",  # AI-generated summary (will be filled later if available)
                "archive_file": "",
                "content_archive_file": "",
            }
            filtered_entries.append(filtered_entry)

        # Create output structure with metadata
        now = datetime.now()
        output_data = {"generated_at": now.isoformat(), "entries": filtered_entries}

        # Define output file path
        output_file = data_dir / "data.json"

        # If data.json exists, merge with existing data
        existing_entries = []
        if output_file.exists():
            logging.info("Loading existing data.json...")
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    existing_generated_at = existing_data.get("generated_at", "")
                    existing_entries = existing_data.get("entries", [])

                    logging.info(f"Found {len(existing_entries)} existing entries")

                    # Create backup with its generated_at timestamp
                    if existing_generated_at:
                        backup_dt = datetime.fromisoformat(existing_generated_at)
                        backup_timestamp = backup_dt.strftime("%Y%m%d-%H%M%S")
                    else:
                        # Fallback to current time if no timestamp in file
                        backup_timestamp = now.strftime("%Y%m%d-%H%M%S")

                    backup_file = data_dir / f"data-{backup_timestamp}.json"

                    # Copy existing file to backup
                    with open(backup_file, "w", encoding="utf-8") as backup_f:
                        json.dump(existing_data, backup_f, indent=2, ensure_ascii=False)

                    logging.info(f"Created backup: {backup_file}")
            except (json.JSONDecodeError, KeyError) as e:
                logging.info(
                    f"Warning: Could not parse existing data.json, starting fresh: {e}"
                )
                existing_entries = []

        # Merge entries: keep existing entries, add only new ones
        existing_ids = {entry["id"] for entry in existing_entries}
        new_entries_count = 0
        new_entries_to_add = []

        # Collect new entries
        for entry in filtered_entries:
            if entry["id"] not in existing_ids:
                new_entries_to_add.append(entry)

        # Generate summaries and archive new entries
        if new_entries_to_add:
            if kagi_api_key:
                logging.info(
                    f"\nGenerating summaries for {len(new_entries_to_add)} new entries..."
                )
            else:
                logging.info(f"Processing {len(new_entries_to_add)} new entries...")

            for i, entry in enumerate(new_entries_to_add, 1):
                url = entry.get("url")
                entry_id = entry.get("id")

                if url:
                    logging.info(
                        f"  [{i}/{len(new_entries_to_add)}] Processing: {entry.get('title', 'Untitled')}"
                    )

                    # Generate summary if API key is available
                    if kagi_api_key:
                        logging.info("Summarizing...")
                        ai_summary = summarize_with_kagi(
                            url,
                            kagi_api_key,
                            engine="cecil",
                            summary_type="summary",
                        )
                        if ai_summary:
                            entry["tldr"] = ai_summary

                    # Archive the page using monolith
                    archive_path = archive_entry(
                        url,
                        archive_dir,
                        entry_id,
                        no_video=True,
                        no_audio=True,
                        no_js=True,
                    )
                    if archive_path:
                        entry["archive_file"] = archive_path

                    # Generate content archive from Feedbin content
                    if entry.get("content"):
                        # Get full entry data with content field
                        full_entry = full_entries_map.get(entry_id)
                        if full_entry:
                            # Create a combined entry dict with both filtered and full data
                            archive_entry_data = {**entry, "content": full_entry.get("content", "")}
                            content_archive_path = render_content_archive(archive_entry_data, archive_dir)
                            if content_archive_path:
                                entry["content_archive_file"] = content_archive_path

                    # Be respectful to APIs - add a small delay between requests
                    if i < len(new_entries_to_add):
                        time.sleep(0.5)
                else:
                    logging.info(
                        f"  [{i}/{len(new_entries_to_add)}] Skipping (no URL): {entry.get('title', 'Untitled')}"
                    )

        # Add new entries to existing list
        existing_entries.extend(new_entries_to_add)
        new_entries_count = len(new_entries_to_add)

        logging.info(f"Added {new_entries_count} new entries")
        logging.info(f"Total entries after merge: {len(existing_entries)}")

        # Ensure all entries have both summary and tldr fields (for backward compatibility)
        for entry in existing_entries:
            if "summary" not in entry:
                entry["summary"] = ""
            if "tldr" not in entry:
                entry["tldr"] = ""

        # Update output data with merged entries
        output_data["entries"] = existing_entries

        # Write merged JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Wrote {len(existing_entries)} total entries to {output_file}")

        # Generate HTML page
        html_file = dist_dir / "index.html"
        logging.info("Generating HTML page...")
        render_html(output_data, html_file)

    except requests.HTTPError as e:
        if e.response.status_code == 401:
            logging.error("Authentication failed. Please check your credentials.")
        else:
            logging.error(f"API request failed with status {e.response.status_code}")
            logging.error(f"Details: {e.response.text}")
        sys.exit(1)
    except requests.RequestException as e:
        logging.error(f"Network request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
