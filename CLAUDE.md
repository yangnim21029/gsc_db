# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GSC Database Manager is a modernized Google Search Console data management and analysis tool written in Python. It provides permanent data storage beyond Google's 16-month limit, automated synchronization, high-performance API services, and advanced analytics for SEO analysis and AI-driven tools.

**🚀 Modernization Status**: This is the refactored version using 2025 best practices including Litestar, msgspec, DuckDB, and hybrid database architecture.

## Development Commands

### Setup and Installation
```bash
# Initialize project structure (creates directories, checks environment)
just init

# Install dependencies
just setup
# or
poetry install

# Bootstrap project (init + install + auth)
just bootstrap

# Google API authentication (manual setup required)
just auth
```

### Quality Assurance
```bash
# Run all quality checks (lint, type-check, test)
just check

# Individual checks
just lint          # Code formatting with Ruff
just type-check    # mypy type checking
just test          # pytest test suite
just test-parallel # parallel test execution (may hang in some cases)

# Pre-commit checks only (excludes lint)
just check-commit
```

### Data Synchronization

**CRITICAL: GSC API DOES NOT SUPPORT CONCURRENT ACCESS**
- Tested 2025-07-25: Concurrent requests = 0% success rate
- Sequential requests = 100% success rate
- All sync operations use sequential processing with delays

```bash
# Sync specific site for N days with sync mode
just sync-site <site_id> [days] [sync_mode]

# Examples
just sync-site 17 7 skip          # Skip existing records (default)
just sync-site 17 14 overwrite    # Overwrite existing records

# Batch sync multiple sites (SEQUENTIAL ONLY)
just sync-multiple "1,3,17" [days] [sync_mode]

# Examples
just sync-multiple "1,3,17" 7 skip
just sync-multiple "1 3 17" 14 overwrite  # Space-separated also works
```

### Sync Modes

The system supports two sync modes:

- **skip** (default): Skip existing records, only insert new data
- **overwrite**: Replace existing records with new data (useful for data corrections)

### Direct Sync Scripts

You can also use the sync scripts directly:

```bash
# List all sites
poetry run python sync.py list

# Single site sync
poetry run python sync.py sync <site_id> [days] [sync_mode]

# Multiple sites sequential sync
poetry run python sync_multiple.py "1,3,17" [days] [sync_mode]
```

### Hourly Data Synchronization

GSC API now supports hourly data for the last 10 days. This provides much more granular insights:

```bash
# Sync hourly data for a single site
just sync-hourly <site_id> [days] [sync_mode]

# Examples
just sync-hourly 5 2              # Last 2 days, skip mode
just sync-hourly 5 7 overwrite    # Last 7 days, overwrite mode

# Batch sync hourly data for multiple sites
just sync-hourly-multiple "1 3 5" [days] [sync_mode]

# Examples
just sync-hourly-multiple "4 5 11 16" 1     # Last 1 day
just sync-hourly-multiple "21,16" 3 overwrite  # Last 3 days, overwrite

# Direct hourly sync scripts
poetry run python sync_hourly.py list         # List all sites
poetry run python sync_hourly.py sync 5 2     # Sync site 5, 2 days
poetry run python sync_hourly_multiple.py "1 2 3" 1  # Multiple sites
```

**Hourly Data Notes:**
- Only available for the last 10 days (GSC API limitation)
- Provides hour-by-hour breakdown of queries, pages, and performance
- Useful for understanding daily traffic patterns
- Data includes timezone information (Pacific time)

### Site Management
```bash
# List all sites
just site-list
```

### API Development
```bash
# Start development server with auto-reload
just dev-server

# Start production server
just prod-server
```

### API Testing
```bash
# Health check
just api-health

# List sites
just api-sites

# Test ranking data with hostname
just api-query-search urbanlifehk.com 美容

# Test page performance
just api-page-performance urbanlifehk.com
```

## Architecture Overview

### Core Structure (Modernized)
- **src/api/app.py**: Litestar web application with high-performance routing
- **src/database/hybrid.py**: SQLite + DuckDB hybrid database for OLTP + OLAP
- **src/config.py**: Pydantic Settings v2 based configuration with .env support
- **sync.py**: Direct sync script without CLI framework complexity
- **sync_multiple.py**: Sequential multi-site sync with progress tracking

### Service Layer
- **src/services/gsc_client.py**: Async Google Search Console API client
  - **CRITICAL**: Uses `max_workers=1` for sequential processing only
  - HTTP/2 support with httpx for better performance
  - Exponential backoff retry with proper error handling
- **src/services/cache.py**: Optional Redis-based caching layer
- **src/services/monitoring.py**: OpenTelemetry integration (disabled by default)

### Modern Web API
- **src/api/app.py**: Litestar application (2-3x faster than FastAPI)
  - msgspec serialization (5-10x faster than Pydantic)
  - Full async support with concurrent request handling
  - OpenAPI/Swagger documentation with CORS support
  - Tested performance: 808 RPS at 30 concurrent users
- **src/api/routes.py**: RESTful endpoints with hostname-based queries
- **src/models.py**: msgspec-based request/response models

### Database Architecture
- **Hybrid SQLite + DuckDB**: SQLite for OLTP, DuckDB for analytical queries
- **Async Operations**: Full async/await support with aiosqlite
- **Connection Pooling**: Efficient connection management
- **Type Safety**: Full type hints throughout

## Key Technologies (Modernized Stack)

### Core Stack
- **Python 3.12+**: Latest Python with performance improvements
- **Poetry**: Dependency management and virtual environments
- **Just**: Task runner (replaces Makefile)
- **Litestar ^2.8.0**: High-performance web framework
- **msgspec ^0.18.0**: Ultra-fast serialization library

### Database & APIs
- **SQLite + DuckDB**: Hybrid database architecture
- **Polars**: High-performance data processing (replaces pandas)
- **httpx**: Modern async HTTP client with HTTP/2 support
- **aiosqlite**: Async SQLite interface

### Development Tools
- **Ruff**: Fast linting and code formatting
- **mypy**: Static type checking
- **pytest**: Testing framework with async support
- **OpenTelemetry**: Optional monitoring (disabled by default)

## Critical GSC API Limitations

### Concurrent Access Restriction
**TESTED AND CONFIRMED 2025-07-25:**

```
Execution Mode    Success Rate    Recommendation
Sequential        100%            ✅ REQUIRED
Concurrent        0%              ❌ NEVER USE
Batch             62.5%           ⚖️ LIMITED
```

**Code Implementation:**
- All GSC API clients use `max_workers=1`
- Sequential processing with 200-500ms delays between requests
- Never use `asyncio.gather()` or concurrent execution for GSC API calls
- Comments throughout codebase warn about this limitation

### API Rate Limits
- 200 requests per 100 seconds per project
- 3 requests per second burst rate
- Daily quota: 25,000 requests per day

## Configuration Management

Modern configuration using Pydantic Settings v2:

```python
# Environment variables with GSC_ prefix
GSC_DATABASE_PATH=/path/to/db
GSC_API_HOST=0.0.0.0
GSC_API_PORT=8000
GSC_ENABLE_CACHE=false
```

## Performance Benchmarks

### API Performance (Tested)
- **30 concurrent users**: 808 RPS, 23.78ms avg response time
- **10 concurrent users**: 499 RPS, 15.84ms avg response time
- **Single user**: 80.78 RPS, 12.26ms avg response time

### Query Performance
- DuckDB analytical queries: 10-100x faster than pure SQLite
- Window functions and time-series analysis support
- Polars data processing: 50-70% memory reduction vs pandas

## Testing Strategy

### Performance Testing
```bash
# API load testing
poetry run python load_test.py

# API stress testing
poetry run python stress_test.py

# GSC API concurrency testing
poetry run python test_gsc_limits.py
```

### Unit and Integration Tests
```bash
# Run all tests
just test

# Run specific test
poetry run pytest tests/test_database.py -v
```

## Important Notes

### Critical Design Decisions

1. **GSC API Sequential Processing**:
   - **NEVER** use concurrent/parallel processing for GSC API calls
   - Concurrent requests result in 100% failure rate
   - All sync operations must be sequential with delays

2. **Simplified Architecture**:
   - Removed Typer CLI framework for complexity reduction
   - Direct Python scripts for sync operations
   - Optional Redis caching (can run without)

3. **Hybrid Database Strategy**:
   - SQLite for transactional operations and storage
   - DuckDB for analytical queries and data export
   - Best of both worlds: reliability + performance

4. **Modern Web Framework**:
   - Litestar replaces FastAPI for 2-3x performance improvement
   - msgspec replaces Pydantic for 5-10x serialization speed
   - Full async support throughout the stack

### Sync Mode Usage

- **skip mode** (default): For daily updates and new data insertion
- **overwrite mode**: For data corrections and historical data updates
- Always specify mode explicitly in production scripts

### API Endpoints Support

All API endpoints support both `site_id` and `hostname` parameters:
- Use `hostname` for user-friendly queries (single lookup)
- Use `site_id` for direct database queries (faster)

### Development Workflow

```bash
# Standard development cycle
just check          # Run all quality checks
just dev-server     # Start development server
just api-health     # Test API is working
just sync-site 17 7 # Test sync functionality
```

## Sync Process Information

### Sequential Processing Details
- **Progress Tracking**: Real-time progress with success/failure counts
- **Error Recovery**: Intelligent retry with exponential backoff
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Data Delay**: GSC data has 2-3 day processing delay

### Batch Sync Features
- **Site-by-site processing**: Complete one site before starting next
- **Inter-site delays**: 2-second delays between sites for API stability
- **Timeout handling**: 5-minute timeout per site with graceful failure
- **Result summaries**: Detailed reports with performance metrics

## Error Handling

- **SSL/TLS errors**: Automatic retry with exponential backoff
- **API rate limits**: Built-in quota management with delays
- **Network connectivity**: Health checks with diagnostic reporting
- **Database operations**: Proper connection handling and cleanup

## Data Safety

- **Database backups**: Automatic backup recommendations
- **Sync state tracking**: Resume interrupted syncs from last success
- **Mode validation**: Prevent accidental data overwrites
- **Error logging**: Comprehensive error reporting and recovery suggestions

## Documentation

- **CHEATSHEET.md**: Commands for users without `just` tool
- **IMPLEMENTATION_REVIEW.md**: Detailed comparison with modernization proposal
- **API Documentation**: Available at http://localhost:8000/docs when server is running

## Memory Notes for Claude Code

- GSC API requires sequential processing (tested and confirmed)
- Project uses modern Python stack (Litestar, msgspec, DuckDB)
- Sync modes: skip (default) for updates, overwrite for corrections
- API supports both site_id and hostname parameters
- Performance tested: 808 RPS peak, 100% sequential sync success rate
