# Breadcrumbs: Archiving and Summarizing Your Stars and Page from Feedbin 🍔

A Python tool to manage your Feedbin starred articles and Pages feed entries with automatic AI-powered summaries using Kagi's Universal Summarizer.

## Features

- Fetches entries from your Feedbin "Pages" feed and starred articles
- Generates AI summaries for new entries using Kagi's Universal Summarizer API
- Archives full web pages using monolith (self-contained HTML with embedded resources)
- Merges new entries with existing data while preserving history
- Automatically backs up data with timestamps before updates
- Outputs structured JSON with entry metadata and summaries
- Configurable via TOML configuration file

## Setup

### 1. Install dependencies

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv sync
```

You'll also need [monolith](https://github.com/Y2Z/monolith) installed for archiving web pages:

```bash
# macOS
brew install monolith

# Linux (cargo)
cargo install monolith

# Or download pre-built binaries from GitHub releases
```

### 2. Set environment variables

```bash
export FEEDBIN_EMAIL='your-email@example.com'
export FEEDBIN_PASSWORD='your-password'
export KAGI_API_KEY='your-kagi-api-key'
```

Note: If `KAGI_API_KEY` is not set, the script will still run but won't generate summaries.

### 3. Configure (optional)

On first run, a `config.toml` file will be created automatically with defaults:

```toml
output_dir = "./dist"
kagi_engine = "cecil"
kagi_summary_type = "summary"
```

You can customize:
- **`output_dir`**: Where to store data (default: `./dist`)
- **`kagi_engine`**: Summarization engine - `"cecil"` (fast, friendly), `"agnes"` (formal, technical), or `"muriel"` (premium, $1/summary)
- **`kagi_summary_type`**: Output format - `"summary"` (full summary) or `"takeaway"` (key points)

## Usage

Run the script:

```bash
uv run python breadcrumbs.py
```

The script will:
1. Load configuration from `config.toml`
2. Fetch all entries from your Feedbin "Pages" feed
3. Fetch all your starred articles
4. Merge entries (marking duplicates appropriately)
5. For each new entry:
   - Generate AI summary via Kagi API (if API key provided)
   - Archive the full web page using monolith
6. Save to `dist/data/data.json` with backup of previous version

## Output Structure

Data is saved in `dist/data/data.json`:

```json
{
  "generated_at": "2024-01-15T10:30:00.123456",
  "entries": [
    {
      "id": 12345,
      "title": "Article Title",
      "url": "https://example.com/article",
      "published": "2024-01-15T08:00:00.000000Z",
      "created_at": "2024-01-15T08:05:00.000000Z",
      "entry_type": "page",
      "tldr": "AI-generated summary of the article...",
      "archive_file": "archive/12345_example.com_article.html"
    }
  ]
}
```

### Entry Types

- **`page`**: Entry from your "Pages" feed
- **`star`**: Starred entry (or starred entry that's also in Pages feed)

### Archive Files

Each entry's web page is archived as a self-contained HTML file using [monolith](https://github.com/Y2Z/monolith):
- Stored in `dist/archive/` directory
- Filename format: `{entry_id}_{url_slug}.html`
- Contains all CSS, images, and resources embedded inline
- The `archive_file` field contains the relative path (e.g., `archive/12345_example.com_article.html`)

## Directory Structure

```
.
├── config.toml          # Configuration file
├── breadcrumbs.py       # Main script
├── dist/
│   ├── data/
│   │   ├── data.json              # Current data
│   │   └── data-YYYYMMDD-HHMMSS.json  # Timestamped backups
│   └── archive/
│       └── {entry_id}_{url_slug}.html  # Archived web pages
```

## Tools & APIs Used

- [Feedbin API v2](https://github.com/feedbin/feedbin-api) - RSS feed management
- [Kagi Universal Summarizer API](https://help.kagi.com/kagi/api/summarizer.html) - AI-powered summarization
- [monolith](https://github.com/Y2Z/monolith) - Web page archiving with embedded resources

## Requirements

- Python 3.14+
- [monolith](https://github.com/Y2Z/monolith) - Command-line tool for archiving web pages
- Dependencies managed via `pyproject.toml` (installed with `uv sync`)
