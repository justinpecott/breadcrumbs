# Claude Context: Breadcrumbs

This document provides context for Claude Code when working on this project.

## Project Overview

**Purpose**: A Python tool that fetches Feedbin RSS entries (from the "Pages" feed and starred articles) and enriches them with AI-generated summaries from Kagi's Universal Summarizer API. It also archives the full web pages using monolith.

**Key Features**:
- Fetches entries from Feedbin API (Pages feed + starred articles)
- Generates summaries using Kagi Universal Summarizer
- Archives complete web pages using monolith (self-contained HTML)
- Merges new entries with existing data without duplicates
- Automatic backup with timestamps before updates
- TOML-based configuration

## Architecture

### Main Components

1. **API Integration**
   - `get_subscriptions()` - Fetches all Feedbin subscriptions
   - `get_entries()` - Fetches entries for a specific feed
   - `get_starred_entries()` - Fetches starred entry IDs
   - `get_entries_by_ids()` - Fetches full entry data by IDs
   - `summarize_with_kagi()` - Generates summaries via Kagi API

2. **Archiving**
   - `url_to_slug()` - Converts URLs to safe filenames
   - `archive_entry()` - Archives web pages using monolith CLI tool
   - Creates self-contained HTML files with embedded resources
   - Generates unique filenames: `{entry_id}_{url_slug}.html`

3. **Configuration**
   - `load_config()` - Loads/creates TOML config file
   - Default location: `config.toml`
   - Uses Python's built-in `tomllib` (read) and `tomli-w` (write)

4. **Data Management**
   - Merges entries without duplicates (by entry ID)
   - Backs up existing data before updates
   - Only generates summaries and archives for new entries

### Data Flow

```
Feedbin API
    ↓
Fetch Pages Feed + Starred Entries
    ↓
Merge & Deduplicate
    ↓
Load Existing data.json
    ↓
Identify New Entries
    ↓
For Each New Entry:
  - Generate Summary (Kagi API)
  - Archive Page (monolith)
    ↓
Backup Old Data → Merge → Save New Data
```

## Configuration

**File**: `config.toml`

```toml
output_dir = "./dist"              # Where to store data
kagi_engine = "cecil"              # cecil | agnes | muriel
kagi_summary_type = "summary"      # summary | takeaway
```

**Kagi Engines**:
- **cecil**: Fast, friendly summaries (default, consumer-grade)
- **agnes**: Formal, technical summaries (consumer-grade)
- **muriel**: Premium summaries ($1/summary, enterprise-grade)

## Environment Variables

Required:
- `FEEDBIN_EMAIL` - Feedbin account email
- `FEEDBIN_PASSWORD` - Feedbin account password

Optional:
- `KAGI_API_KEY` - Kagi API key (if not set, summaries won't be generated)

## Output Structure

**Location**: `{output_dir}/data/data.json`

```json
{
  "generated_at": "ISO timestamp",
  "entries": [
    {
      "id": 12345,
      "title": "...",
      "url": "...",
      "published": "...",
      "created_at": "...",
      "entry_type": "page" | "star",
      "tldr": "AI summary",
      "archive_file": "archive/12345_example.com_article.html"
    }
  ]
}
```

**Entry Types**:
- `page` - From "Pages" feed
- `star` - Starred entry (takes precedence if entry is both)

## Important Behaviors

1. **Idempotency**: Running the script multiple times is safe - it only processes new entries
2. **Backups**: Old `data.json` is backed up with timestamp before updates
3. **API Rate Limiting**: 0.5-second delay between entry processing operations
4. **Error Handling**:
   - If summarization fails for an entry, it continues with empty tldr
   - If archiving fails for an entry, it continues with empty archive_file
5. **Merge Priority**: If an entry is both in Pages and starred, it's marked as "star"
6. **Archiving**:
   - Each entry gets a unique filename: `{entry_id}_{url_slug}.html`
   - Archive path stored as relative path from dist directory
   - 60-second timeout per archive operation

## Dependencies

- `requests` - HTTP client for API calls
- `tomli-w` - TOML writing (built-in `tomllib` for reading)
- `monolith` - CLI tool for archiving web pages (external dependency)
- Python 3.11+ required (for `tomllib`)
- Standard library: `subprocess`, `re`, `urllib.parse` (for archiving)

## Code Style

- Type hints used throughout
- Docstrings with Args/Returns/Raises sections
- Error handling with specific exception types
- Clear variable names following Python conventions

## Future Enhancements

Potential improvements:
- PDF generation from archived HTML files
- Configurable archiving options (timeout, monolith flags)
- Parallel processing for faster archiving
- Archive compression for storage efficiency

## Testing Notes

- Uses `uv` for dependency management
- No formal test suite yet
- Manual testing recommended with small data sets first

## Common Tasks

**Adding a new config option**:
1. Add to `default_config` dict in `load_config()`
2. Use in relevant function
3. Document in README.md

**Changing summarization behavior**:
- Modify `summarize_with_kagi()` function
- Consider config options for user customization

**Modifying archiving behavior**:
- Adjust `archive_entry()` function for different monolith flags
- Modify `url_to_slug()` for different filename patterns
- Consider adding config options for timeout or storage location

**Adding new Feedbin API calls**:
- Follow existing pattern with HTTPBasicAuth
- Add docstring with Args/Returns/Raises
- Handle errors appropriately
