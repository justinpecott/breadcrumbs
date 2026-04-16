# Copilot Instructions

## Commands

- Install dependencies: `uv sync`
- Run the archive job: `uv run python breadcrumbs.py`
- Open the generated interface locally: `open dist/index.html`
- Runtime prerequisites: Python 3.14+, the external `monolith` CLI, `FEEDBIN_EMAIL`, and `FEEDBIN_PASSWORD`. `KAGI_API_KEY` is optional.

## Architecture

- This repo is a single-script application. `breadcrumbs.py` owns config loading, Feedbin API calls, entry merging, archiving, JSON persistence, and HTML generation. The only view layer lives in `templates/index.html` and `templates/entry.html`.
- `main()` loads or creates `config.toml`, initializes `dist/data`, `dist/archive`, and `dist/logs`, then fetches two sources from Feedbin: the subscription titled exactly `Pages` and the user's starred entries.
- Pages are fetched directly from the Pages feed, while starred items are fetched in two steps: starred entry IDs first, then full entry payloads via `get_entries_by_ids()`. The two sets are merged by entry ID before export.
- `dist/data/data.json` is the persistent source of truth. Each run loads any existing file, creates a timestamped backup in `dist/data/`, processes only entry IDs that are not already present, then rewrites `data.json` and regenerates `dist/index.html`.
- Archiving is intentionally dual-path: `archive_entry()` uses `monolith` to save a full-page archive, and `render_content_archive()` renders a reader-view HTML file from Feedbin's extracted `content` field using `templates/entry.html`.
- `render_html()` passes the merged JSON data into `templates/index.html`, which contains the client-side search, page/star filtering, summary expansion, and keyboard shortcut behavior.

## Key conventions

- Keep the two summary sources separate. Feedbin's RSS/feed summary is stored in `summary`; Kagi output is stored in `tldr`. Do not overwrite `summary` with AI output.
- The merge rule is deliberate: Pages entries are loaded first, then starred entries win on duplicates by changing `entry_type` to `"star"`.
- Only new entries should be summarized and archived. Existing records in `data.json` are preserved and extended rather than rebuilt from scratch.
- Archive filenames must stay deterministic and unique. Full archives use `{entry_id}_{url_slug}.html`; reader-view archives use `content-{entry_id}_{url_slug}.html`.
- Paths stored in JSON stay relative to the dist root, e.g. `archive/12345_example.com_article.html`, so the generated HTML works when opened directly from disk.
- Backward compatibility is handled in-place: older entries missing `summary` or `tldr` are normalized before rendering.
- Web archives are intentionally created with `monolith --no-video --no-audio --no-js` for cleaner self-contained snapshots.
- Kagi summarization is intentionally hardcoded to `engine="cecil"` and `summary_type="summary"` unless the summarization behavior is being changed on purpose.
- Config is intentionally minimal. If you add a config option, update `default_config` in `load_config()` and document it in `README.md`.
- Date formatting is implemented as local Jinja filters inside both `render_html()` and `render_content_archive()`. If date display changes, update both code paths.
- Per-entry failures for Kagi summarization or archiving are soft failures: the script logs the problem, leaves the related output fields empty, and continues processing the rest of the run.
