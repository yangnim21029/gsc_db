# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GSC Database Manager is a modern enterprise-level Google Search Console data management and analysis platform built with Python 3.11+. It overcomes GSC's 16-month data retention limit by providing permanent local storage with high-performance analytics capabilities.

**Key Features:**
- Hybrid SQLite + DuckDB database architecture for OLTP/OLAP operations
- Modern async architecture with Litestar web framework
- 808 RPS API capacity with msgspec serialization (5-10x faster than Pydantic)
- Sequential GSC API processing (100% success rate vs 0% with concurrent)
- Supports both daily and hourly data synchronization

## Development Commands

### Initial Setup
```bash
# Bootstrap project (creates directories, installs dependencies, sets up auth)
just bootstrap

# Or individually:
just init       # Create directory structure
just setup      # Install dependencies with Poetry
just auth       # Configure Google API authentication
```

### Quality Assurance & Testing
```bash
# Run all checks before committing
just check              # Runs lint + type-check + test

# Individual checks
just lint               # Ruff formatting and linting
just type-check         # mypy static type checking
just test               # pytest test suite
just test-parallel      # Parallel test execution (may hang in some cases)

# For pre-commit hooks (excludes lint)
just check-commit

# Run specific tests
poetry run pytest tests/test_specific.py::test_function_name -v
poetry run pytest --cov=src --cov-report=html
```

### Data Synchronization

**Critical: GSC API requires sequential processing. Never use concurrent requests.**

```bash
# Single site sync
just sync-site <site_id> [days] [sync_mode] [fast_mode]
# Example: just sync-site 1 7          # Site 1, last 7 days, skip mode
# Example: just sync-site 1 365 skip fast   # Fast mode for large historical data

# Multiple sites (sequential processing)
just sync-multiple "1 3 5" [days] [sync_mode] [fast_mode]
# Example: just sync-multiple "1 3 5" 14 overwrite

# Hourly data sync (max 10 days due to GSC limits)
just sync-hourly <site_id> [days] [sync_mode]
just sync-hourly-multiple "1 3 5" [days] [sync_mode]

# Check sync status
just sync-status            # All sites
just sync-status <site_id>  # Specific site

# Update database statistics for query optimization
just analyze [table_name]
```

**Sync Modes:**
- `skip` (default): Skip existing records, only insert new data
- `overwrite`: Replace existing data (use for corrections)

**Performance Modes:**
- Standard Mode: Balanced performance and safety (default)
- Fast Mode: Aggressive optimizations for old computers/slow storage (use `fast` parameter)

### API Development
```bash
# Development server with auto-reload
just dev-server    # http://127.0.0.1:8000

# Production server
just prod-server   # http://0.0.0.0:8000

# API testing shortcuts
just api-health
just api-sites
just api-site 1
just api-sync-status-hostname example.com
just api-query-search example.com "search term"
just api-page-performance example.com
```

### Site Management
```bash
# List all sites
just site-list

# Direct CLI usage
poetry run python sync.py list
poetry run python sync.py sync 17 365 skip --fast-mode
poetry run python sync_multiple.py "1,3,5" 7 skip
```

## High-Level Architecture

### Core Architecture Principles

1. **Hybrid Database Design**
   - **SQLite**: Primary transactional storage (OLTP)
   - **DuckDB**: Analytics engine attached to SQLite (OLAP)
   - Seamless integration for complex queries with 10-100x performance gains

2. **Sequential GSC API Processing**
   - **Critical constraint**: GSC API has 0% success rate with concurrent requests
   - All sync operations use `asyncio.Semaphore(1)` to ensure sequential execution
   - 100% success rate with sequential processing

3. **Modern Async Stack**
   - **Litestar**: High-performance async web framework (2-3x faster than FastAPI)
   - **msgspec**: Ultra-fast serialization (5-10x faster than Pydantic)
   - **httpx**: HTTP/2 support with retry logic
   - **aiosqlite**: Async SQLite operations

### Directory Structure

```
src/
├── api/              # Litestar API application
│   ├── app.py       # Main application factory
│   └── routers/     # API endpoint handlers
├── database/        # Data access layer
│   └── hybrid.py    # Hybrid SQLite+DuckDB implementation
├── services/        # Business logic layer
│   ├── gsc_client.py    # Google Search Console client
│   └── sync_service.py  # Data synchronization logic
├── models.py        # msgspec data models
└── config.py        # Pydantic Settings configuration
```

### Key Design Patterns

1. **Dependency Injection**: Litestar's DI for database and cache management
2. **Repository Pattern**: Clean separation between data access and business logic
3. **Retry with Backoff**: Tenacity for handling transient API failures
4. **Streaming Responses**: Memory-efficient CSV exports with async generators
5. **Two-tier Caching**: Memory + Redis with cache-aside pattern

### API Endpoint Structure

```
/api/v1/
├── /sites           # Site management
├── /analytics       # Complex queries and trends
├── /page-keyword-performance  # Page-level analysis
└── /sync           # Synchronization management
```

All endpoints support both `hostname` and `site_id` parameters for flexibility.

### Configuration Management

Environment variables override config values using `__` delimiter:
```bash
export GSC__PATHS__DATABASE=/custom/path/gsc.db
export GSC__SYNC__BATCH_SIZE=1000
export GSC__LOG__LEVEL=DEBUG
```

### Performance Optimizations

1. **Batch Processing**: Configurable batch sizes for bulk operations
2. **Index Management**: Automatic index optimization during large imports
3. **Fast Mode**: Aggressive SQLite pragmas for historical data loading
4. **Streaming Exports**: DuckDB streaming for large result sets
5. **Connection Pooling**: Efficient resource management

### Error Handling Strategy

- **Exponential Backoff**: For transient GSC API failures
- **Rate Limiting**: Respects GSC quotas with tracking
- **Graceful Degradation**: Cache fallback when services unavailable
- **Comprehensive Logging**: Structured logs with Rich console output

## Important Implementation Notes

### Critical Constraints

1. **GSC API Sequential Processing**: This is non-negotiable. The codebase is designed around this limitation.
2. **Data Processing Delay**: GSC data has a 2-3 day processing delay. Recent dates may return 403 errors.
3. **Hourly Data Limits**: GSC only provides hourly data for the last 10 days.

### Test Data Management

- **Always use site_id: 3 (test.com) for testing**
- Never use production site IDs in tests
- Clean test data after testing: `python tests/clean_test_data.py --site-id 3 --days 7`

### Database Considerations

- File-based SQLite (not `:memory:`) for pytest-xdist compatibility
- WAL mode enabled for concurrent reads
- Thread-safe with `asyncio.Lock` protection
- Automatic daily backups with 30-day retention

### Development Patterns

1. **Services are Singletons**: Injected via Litestar DI, never instantiated directly
2. **All Operations are Async**: Use `await` throughout the codebase
3. **Errors Should Bubble Up**: Let the framework handle error responses
4. **Use Type Hints**: Full typing for better IDE support and type checking

### Performance Benchmarks

- API: 808 RPS peak capacity (30 concurrent users)
- Query Performance: 10-100x improvement with DuckDB
- Memory Usage: 50-70% reduction with Polars vs pandas
- Sync Reliability: 100% success rate with sequential processing

## Common Development Tasks

### Adding a New API Endpoint

1. Create router in `src/api/routers/`
2. Define request/response models with msgspec
3. Implement service method in appropriate service class
4. Add router to app in `src/api/app.py`
5. Update CHEATSHEET.md with new endpoint

### Modifying Database Schema

1. Update schema in `src/database/hybrid.py`
2. Add migration logic if needed
3. Update corresponding msgspec models
4. Run tests to ensure compatibility

### Debugging Sync Issues

1. Check `logs/` directory for detailed logs
2. Verify sequential processing is maintained
3. Check for GSC API quota limits
4. Use `--fast-mode` for large historical syncs

## Monitoring and Observability

- Health endpoint: `/health`
- API documentation: `/docs` (Swagger UI)
- OpenTelemetry instrumentation (optional)
- Structured logging with log levels
