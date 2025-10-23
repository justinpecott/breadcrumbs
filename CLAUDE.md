# Claude Context: Breadcrumbs

This document provides context for Claude Code when working on this project.

## Project Overview

**Purpose**: A Python tool that fetches Feedbin RSS entries (from the "Pages" feed and starred articles) and enriches them with AI-generated summaries from Kagi's Universal Summarizer API.

**Key Features**:
- Fetches entries from Feedbin API (Pages feed + starred articles)
- Generates summaries using Kagi Universal Summarizer
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

2. **Configuration**
   - `load_config()` - Loads/creates TOML config file
   - Default location: `config.toml`
   - Uses Python's built-in `tomllib` (read) and `tomli-w` (write)

3. **Data Management**
   - Merges entries without duplicates (by entry ID)
   - Backs up existing data before updates
   - Only generates summaries for new entries

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
Generate Summaries (Kagi API)
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
      "archive_file": ""
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
3. **API Rate Limiting**: 0.5-second delay between Kagi API calls
4. **Error Handling**: If summarization fails for an entry, it continues with empty tldr
5. **Merge Priority**: If an entry is both in Pages and starred, it's marked as "star"

## Dependencies

- `requests` - HTTP client for API calls
- `tomli-w` - TOML writing (built-in `tomllib` for reading)
- Python 3.11+ required (for `tomllib`)

## Code Style

- Type hints used throughout
- Docstrings with Args/Returns/Raises sections
- Error handling with specific exception types
- Clear variable names following Python conventions

## Future Enhancements

The `archive_file` field is currently unused but reserved for potential features:
- Downloading and archiving full article content
- Storing snapshots of articles
- PDF generation

The `archive/` directory structure is created but not currently used.

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

**Adding new Feedbin API calls**:
- Follow existing pattern with HTTPBasicAuth
- Add docstring with Args/Returns/Raises
- Handle errors appropriately
