# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimalist Google Search Console (GSC) data management system using Parquet files and DuckDB for storage and analytics. The design philosophy is "極簡設計，先跑起來再說" (minimalist design, get it running first).

**Requirements**: Python 3.9 or higher

## Key Commands

### Setup and Dependencies

```bash
# Using Poetry (recommended)
poetry install
poetry shell

# Or using pip
pip install -r requirements.txt

# First time setup - requires client_secret.json from Google Console
# The system will open a browser for OAuth authentication
```

### Data Synchronization

```bash
# Sync all historical data for a site (up to 16 months)
python sync.py https://example.com
python sync.py sc-domain:example.com

# Or with Poetry
poetry run gsc-sync https://example.com
```

### API Server

```bash
# Start Flask API server
python app.py 5000

# Or with Poetry
poetry run gsc-api 5000

# Start MCP service for Claude
python gsc_mcp.py

# Or with Poetry
poetry run gsc-mcp
```

### Testing

```bash
# Run tests
python test.py

# Run with pytest (if tests are migrated)
pytest tests/

# Run with coverage
pytest --cov
```

### Development Tools

```bash
# Linting (configured for 120 char line length)
ruff check .
ruff format .
```

## Architecture and Design Patterns

### Data Storage Structure

- **Parquet files** organized by site and month: `data/{site_folder}/{YYYY-MM}/{YYYY-MM-DD}.parquet`
- Site URLs are sanitized for folder names: `:` and `/` replaced with `_`
- Each day's data is stored in a separate Parquet file

### Core Components

1. **sync.py** - GSC data synchronization

   - OAuth 2.0 authentication flow with browser-based initial setup
   - Syncs up to 480 days (16 months) of historical data - GSC's retention limit
   - Handles GSC API's 25,000 row limit with automatic pagination and batch processing
   - Sequential processing (GSC API doesn't support concurrent requests)
   - Rate limiting: 10-second pause every 10 requests
   - Quota error handling: 15-minute retry on rate limit errors
   - Automatically skips dates where Parquet files already exist
   - Processes data chronologically from oldest to newest

2. **project_query.py** - Shared query functions

   - All SQL queries use `escape_sql_string()` for injection protection
   - Common pattern: site URL → folder name → parquet path
   - Key functions: `track_pages_query()`, `compare_periods()`, `query_intent_analysis()`

3. **app.py** - Flask API endpoints

   - `/track_pages` - Track specific pages and keywords
   - `/compare_periods` - Compare time periods (week/month)
   - `/pages_queries` - Get actual ranking keywords for specific pages
   - `/intent_analysis_data` - Analyze search intent, returns CSV

4. **gsc_mcp.py** - MCP tools for Claude
   - `query` - Execute arbitrary SQL queries
   - `show_page_queries` - View search terms for a page
   - `show_keyword_pages` - View pages ranking for keywords
   - `search_keywords` - Query keywords matching patterns
   - `best_pages` - Query best performing pages in time period
   - `track_pages` - Track performance of specific pages/keywords
   - `pages_queries` - Query actual ranking keywords for pages
   - `compare_periods` - Compare performance across time periods
   - Returns data as dictionaries for AI consumption

### Query Pattern

All queries follow this pattern:

```python
# Convert site URL to folder path
folder_name = site.replace(':', '_').replace('/', '_')
parquet_path = f"data/{folder_name}/*/*.parquet"

# Use DuckDB to query Parquet files
conn = duckdb.connect()
df = conn.execute(f"SELECT * FROM '{parquet_path}' WHERE ...").fetchdf()
```

### Authentication

- Uses OAuth 2.0 with token persistence (`token.pickle`)
- Requires `client_secret.json` from Google Cloud Console
- Token auto-refresh on expiration

## Critical Design Decisions

1. **Sequential API Processing**: GSC API requires sequential requests - never attempt concurrent calls
2. **Parquet + DuckDB**: Chosen for simplicity and performance - no database server needed
3. **SQL Injection Protection**: All user inputs must go through `escape_sql_string()`
4. **Minimalist Approach**: Add features only when needed, not preemptively

關於你說的都很有道理，但是，卻沒有很有用，我們應該做的事情應該是少到可能需要額外增加 10%~20% 才能補齊，而不是做那種包含 80% 未來不需要再優化的事情。

## Known Technical Limitations

- pyarrow 是跟 numpy 有版本相容性問題