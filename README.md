# Feedbin Fun

A Python script to interact with the Feedbin API and list your RSS feed subscriptions.

## Setup

1. Install dependencies using uv:
```bash
uv sync
```

2. Set your Feedbin credentials as environment variables:
```bash
export FEEDBIN_EMAIL='your-email@example.com'
export FEEDBIN_PASSWORD='your-password'
```

## Usage

Run the script to list all your subscriptions:

```bash
uv run python main.py
```

The script will:
- Authenticate with the Feedbin API using HTTP Basic authentication
- Fetch all your subscriptions
- Display them with details including ID, title, feed URL, site URL, and creation date

## Example Output

```
Fetching subscriptions...

Found 3 subscription(s):

ID: 12345
  Title: Example Blog
  Feed URL: https://example.com/feed.xml
  Site URL: https://example.com
  Created: 2024-01-01T00:00:00.000000Z

...
```

## API Documentation

This script uses the [Feedbin API v2](https://github.com/feedbin/feedbin-api).
