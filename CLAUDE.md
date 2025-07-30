# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a minimalist Google Search Console (GSC) data management system using Parquet files and DuckDB for storage and analytics. The design philosophy is "極簡設計，先跑起來再說" (minimalist design, get it running first).

**Requirements**: Python 3.10 or higher (specified in pyproject.toml)

## Key Commands

### Setup and Dependencies

```bash
# Using Poetry (recommended)
poetry install
poetry shell

# Or using pip
pip install -r requirements.txt

# Set OpenAI API key for natural language queries
export OPENAI_API_KEY=your_api_key_here
# Or add to .env file

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

# List accessible GSC sites
python list_sites.py
```

### API Server

```bash
# Start Flask API server (includes web UI)
python app.py 5000

# Or with Poetry
poetry run gsc-api 5000

# Access web UI at http://localhost:5000
# Natural language query interface at http://localhost:5000/query

# Start MCP service for Claude
python gsc_mcp.py

# Or with Poetry
poetry run gsc-mcp
```

### Testing

```bash
# Run tests (single test file, no formal test suite)
python test.py

# No pytest setup currently exists
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
- Multiple sites already have synced data in the data/ directory

### Core Components

1. **sync.py** - GSC data synchronization

   - OAuth 2.0 authentication flow with browser-based initial setup
   - Syncs up to 480 days (16 months) of historical data - GSC's retention limit
   - Simple batch processing: queries all 4 dimensions (query, page, device, country)
   - Handles GSC API's 25,000 row limit with automatic pagination
   - Shows progress when multiple batches are needed (e.g., "批次 2: +25000 筆，總計 50000 筆")
   - Sequential processing (GSC API doesn't support concurrent requests)
   - Rate limiting: 10-second pause every 10 requests
   - Quota error handling: 15-minute retry on rate limit errors
   - Automatically skips dates where Parquet files already exist
   - Processes data chronologically from oldest to newest

2. **app.py** - Flask API server with web UI

   - **API Endpoints:**
     - `/track_pages` - Track specific pages and keywords
     - `/compare_periods` - Compare time periods (week/month)
     - `/pages_queries` - Get actual ranking keywords for specific pages
     - `/intent_analysis_data` - Analyze search intent, returns CSV
     - `/query` - Natural language SQL interface using OpenAI
   - **Web UI:**
     - Main dashboard at `/` (templates/index.html)
     - Natural language query interface at `/query` (templates/query.html)
     - Static assets in static/css/ and static/js/
   - CORS enabled for cross-origin requests

3. **gsc_mcp.py** - MCP tools for Claude

   - `query` - Execute arbitrary SQL queries
   - `show_page_queries` - View search terms for a page
   - `show_keyword_pages` - View pages ranking for keywords
   - `search_keywords` - Query keywords matching patterns
   - `best_pages` - Query best performing pages in time period
   - `track_pages` - Track performance of specific pages/keywords
   - `pages_queries` - Query actual ranking keywords for pages
   - `compare_periods` - Compare performance across time periods
   - Returns data as dictionaries for AI consumption

4. **list_sites.py** - Utility to list all accessible GSC sites

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

### Natural Language Query Feature

The web UI includes a natural language SQL interface powered by OpenAI:

- Converts natural language to DuckDB SQL queries
- Accessible at http://localhost:5000/query
- Requires OPENAI_API_KEY environment variable

### Authentication

- Uses OAuth 2.0 with token persistence (`token.pickle`)
- Requires `client_secret.json` from Google Cloud Console
- Token auto-refresh on expiration

## Critical Design Decisions

1. **Sequential API Processing**: GSC API requires sequential requests - never attempt concurrent calls
2. **Parquet + DuckDB**: Chosen for simplicity and performance - no database server needed
3. **SQL Injection Protection**: All user inputs must go through `escape_sql_string()`
4. **Minimalist Approach**: Add features only when needed, not preemptively
5. **Natural Language Interface**: OpenAI integration for user-friendly queries

關於你說的都很有道理，但是，卻沒有很有用，我們應該做的事情應該是少到可能需要額外增加 10%~20% 才能補齊，而不是做那種包含 80% 未來不需要再優化的事情。

## Known Technical Limitations

- pyarrow 是跟 numpy 有版本相容性問題 (numpy <2 constraint)

## Database Handling Notes

- DuckDB query returns NaN for divisions by zero, Backend converts NaN to None/null
- Parquet files support columnar storage for efficient analytical queries

## Available Example Data

The data/ directory contains synced data for multiple sites including:

- holidaysmart.io
- mamidaily.com
- presslogic.com
