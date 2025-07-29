# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GSC Database Manager is an enterprise-level Google Search Console data management and analysis tool written in Python. It provides permanent data storage beyond Google's 16-month limit, automated synchronization, hourly precision data, and API services for SEO analysis and AI-driven tools.

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

# Google API authentication
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

# Run a specific test
poetry run pytest tests/test_specific.py::test_function_name -v

# Run tests with coverage
poetry run pytest --cov=src --cov-report=html
```

### Data Synchronization
```bash
# Sync specific site for N days
just sync-site <site_id> [days]

# Example: Sync site ID 1 for last 7 days
just sync-site 1 7

# Batch sync multiple sites
just sync-multiple "1 3 5" [days]       # Sequential sync with progress tracking

# Hourly data synchronization (last few days only)
poetry run gsc-cli sync hourly <site_id> --days <days>
just sync-hourly-multiple "1 3 5" [days]    # Multiple sites hourly sync

# Example: Sync hourly data for site ID 5, last 2 days
poetry run gsc-cli sync hourly 5 --days 2

# Example: Sync multiple sites hourly data, last 1 day
just sync-hourly-multiple "4 5 11 16" 1

# Monitor sync progress and status
just sync-status                         # View all sites sync status
just sync-status [site_id]              # View specific site status

# Full maintenance (sync all, backup, cleanup)
just maintenance
```

### Performance Modes

The system supports two performance modes for data synchronization:

#### Standard Mode (Default)
Optimized for general use with good balance of performance and safety:
- Enhanced cache size (20,000 pages)
- Memory-based temporary tables
- Memory-mapped I/O (128MB)
- Safe synchronous writes (NORMAL mode)
- Suitable for daily syncs (1-30 days)

#### Fast Mode
Aggressive optimizations for old computers or slow storage:
- Disabled synchronous writes (PRAGMA synchronous = OFF)
- Large cache size (50,000 pages)
- Extended memory mapping (256MB)
- Disabled foreign key checks
- Automatic index optimization for large batches
- **Use with caution**: Less safe but 3-5x faster

##### When to Use Fast Mode:
- Syncing large historical data (>30 days)
- Working on slow network storage
- Initial database population
- Old computers with limited resources

##### How to Use Fast Mode:
```bash
# Single site with fast mode
just sync-site 5 365 skip fast

# Multiple sites with fast mode
just sync-multiple "1 2 3" 180 skip fast

# Direct command with fast mode
python sync.py sync 17 365 --fast-mode
```

### Sync Process Information

The sync system uses sequential processing for reliability:

- **Sequential processing**: All sync operations are performed sequentially to ensure GSC API stability
- **Progress tracking**: Real-time progress monitoring with detailed success/failure reporting
- **Error handling**: Comprehensive error handling with intelligent recovery suggestions
- **Cross-platform compatibility**: Works seamlessly on both Windows and Unix systems
- **Data availability delay**: GSC daily data typically has a 2-3 day processing delay. Attempting to sync data from the last 3 days may result in HTTP 403 errors

### Sync Modes

The system supports two sync modes:

- **skip** (default): Skip existing data, only insert new records
- **overwrite**: Replace existing data with new data

```bash
# Use skip mode (default)
poetry run gsc-cli sync daily --site-id 5 --days 7 --sync-mode skip

# Use overwrite mode
poetry run gsc-cli sync daily --site-id 5 --days 7 --sync-mode overwrite
poetry run gsc-cli sync multiple "1 2 3" --days 7 --sync-mode overwrite
```

### Sync Status and Monitoring

Use these commands to monitor sync progress:

```bash
# Check current sync status
just sync-status

# Monitor specific site
just sync-status 5

# View recent sync activity
poetry run gsc-cli sync status
```

### Direct CLI Usage

You can also use the CLI directly without the justfile:

```bash
# Site management
poetry run gsc-cli site list
poetry run gsc-cli site add "sc-domain:example.com"

# Authentication
poetry run gsc-cli auth login

# Daily sync
poetry run gsc-cli sync daily --site-id 5 --days 7
poetry run gsc-cli sync daily --all-sites --days 3

# Multiple site sync
poetry run gsc-cli sync multiple "1 3 5" --days 14

# Hourly sync
poetry run gsc-cli sync hourly 5 --days 2 --force
poetry run gsc-cli sync hourly-multiple "4 5 11 16" --days 1
poetry run gsc-cli sync hourly-multiple "21 16" --days 2 --force

# Analysis
poetry run gsc-cli analyze report 5 --days 30
```

### Site Management
```bash
# List all sites
just site-list

# Add new site
just site-add "sc-domain:example.com"
```

### Data Analysis
```bash
# Generate performance report for a site
poetry run gsc-cli analyze report <site_id> --days <days>

# Example: Generate 30-day report for site ID 5
poetry run gsc-cli analyze report 5 --days 30
```

### API Development
```bash
# Start development server with auto-reload
just dev-server

# Start production server
just prod-server
```

### Utilities
```bash
# Sitemap redundancy analysis
just sitemap-redundancy --site-id <id>
just sitemap-help

# Backup management
just list-large-backups [count]
```

## Architecture Overview

### Core Structure
- **src/app.py**: Main CLI entry point using Typer with dependency injection context
- **src/containers.py**: Dependency injection container using dependency-injector pattern
  - Shared database connection with thread-safe locking
  - Singleton services for all components
  - Container instance passed through Typer context
- **src/config.py**: Pydantic-based configuration management with TOML support
  - Environment variable override with `__` delimiter for nested values
  - Automatic path resolution relative to project root

### Service Layer
- **src/services/database.py**: SQLite database operations with thread-safe connection handling
  - Single connection with `check_same_thread=False`
  - `threading.RLock` for reentrant locking
  - `isolation_level=None` for auto-commit mode
  - Sync modes: skip (default) and overwrite
- **src/services/gsc_client.py**: Google Search Console API client with retry logic
  - Sequential processing with `max_workers=1` for API stability
  - Exponential backoff retry with Tenacity
  - Per-minute and daily quota tracking
- **src/services/site_service.py**: Site management operations
- **src/services/hourly_database.py**: Hourly data synchronization service
- **src/services/analysis_service.py**: Data analysis and reporting
- **src/services/data_aggregation_service.py**: Efficient batch data aggregation

### CLI Commands
- **src/cli/commands.py**: Typer command definitions organized into sub-apps:
  - auth_app: Google API authentication
  - site_app: Site management
  - sync_app: Data synchronization (daily/hourly with sequential processing)
  - analyze_app: Data analysis and reporting
  - All commands receive services via dependency injection

### Jobs
- **src/jobs/bulk_data_synchronizer.py**: Batch sync orchestrator with progress tracking

### Analysis Modules
- **src/analysis/hourly_performance_analyzer.py**: Hourly traffic analysis
- **src/analysis/interactive_data_visualizer.py**: Interactive data visualization

### Web API
- **src/web/api.py**: FastAPI server for external integrations
  - RESTful endpoints at `/api/v1/`
  - Shared container instance with CLI
  - Automatic OpenAPI documentation
- **src/web/schemas.py**: Pydantic response models

### Utilities
- **src/utils/rich_console.py**: Rich terminal output configuration
- **src/utils/system_health_check.py**: Network connectivity diagnostics
- **src/utils/state_manager.py**: Application state management
  - Sync progress tracking
  - Last sync timestamps per site
  - Recovery from interrupted syncs

## Key Technologies

### Core Stack
- **Python 3.11+**: Required minimum version
- **Poetry**: Dependency management and virtual environments
- **Just**: Task runner (replaces Makefile)
- **Typer**: CLI framework with type hints
- **FastAPI**: Web API framework
- **Pydantic**: Data validation and settings management

### Database & APIs
- **SQLite**: Local database with thread-safe operations
- **Google API Client**: Search Console data access
- **pandas**: Data manipulation and analysis

### Development Tools
- **Ruff**: Fast linting and code formatting
- **mypy**: Static type checking
- **pytest**: Testing framework with parallel execution support
- **pre-commit**: Git hooks for quality assurance

### Visualization & Reporting
- **Rich**: Terminal output enhancement
- **matplotlib/seaborn**: Statistical plotting
- **plotly**: Interactive visualizations
- **openpyxl**: Excel report generation

## Configuration Management

The project uses a hybrid configuration system:
- **config.toml**: Base configuration file
- **Pydantic Settings**: Type-safe configuration with environment variable override
- **Environment Variables**: Runtime configuration override

Configuration sections:
- `paths`: File and directory locations
- `log`: Logging configuration
- `retry`: API retry settings
- `sync`: Data synchronization settings

## Threading and Concurrency

The application uses sequential processing with careful resource management:
- **SQLite connections**: `check_same_thread=False` with `threading.RLock`
- **GSC API calls**: Sequential processing with `max_workers=1` to ensure API stability
- **Tenacity**: Exponential backoff for API retry logic

## Testing Strategy

- **Unit tests**: Individual component testing
- **Integration tests**: End-to-end workflow testing
- **Concurrency tests**: Database lock and threading validation
- **README functionality tests**: Automated validation of documented features

## Error Handling

- **SSL/TLS errors**: Automatic retry with exponential backoff
- **API rate limits**: Built-in quota management
- **Network connectivity**: Health checks with diagnostic reporting
- **Database locks**: Proper resource cleanup and timeout handling

## Important Notes

### Critical Design Decisions

1. **Sequential Processing is Intentional**: Never use parallel processing for GSC API calls. The `max_workers=1` setting prevents API rate limiting and SSL errors.

2. **Database Locking Strategy**: All database operations must acquire the shared lock to prevent "database is locked" errors. The lock is reentrant to support nested operations.

3. **Path Resolution**: All paths in configuration are resolved relative to the project root for portability.

4. **Shared Container Instance**: The dependency injection container is shared between CLI and API to maintain singleton services.

5. **File-based Test Databases**: Tests use file-based SQLite databases, not `:memory:`, for pytest-xdist compatibility.

### Network Issues
The application includes sophisticated network error handling for common GSC API issues:
- SSL handshake failures with automatic retry
- Connection timeouts with exponential backoff
- Certificate validation errors with diagnostic messages
- Health check system for connectivity troubleshooting

### Development Patterns

1. **Dependency Injection**: Services are injected via the container, never instantiated directly in commands.

2. **Error Recovery**: All sync operations support resumption from the last successful state.

3. **Quota Management**: API quotas are tracked per-minute and per-day with automatic reset logic.

4. **Configuration Override**: Use environment variables like `GSC__PATHS__DATABASE` to override nested config values.

### Testing Considerations

- Run `just test` for sequential tests or `just test-parallel` for parallel execution
- Use `just check` before commits to run all quality checks
- Integration tests validate actual GSC API interactions when credentials are available
- README functionality tests ensure documentation accuracy

### Data Safety
- Automatic daily backups to `data/backups/`
- Compression of backup files with gzip
- 30-day backup retention policy
- Backup naming includes timestamp for easy identification

## Test Data Management

### Important: Test Site Usage
- **Always use site_id: 3 (test.com) for testing**
- Never use production site IDs in test scripts (e.g., site_id: 17 for urbanlifehk.com)
- Test scripts have been updated to use the test site
- Clean up test data after testing to avoid data pollution

### Test Data Cleanup
```bash
# Clean test data from recent days
python tests/clean_test_data.py --site-id 3 --days 7

# Clean all test data (use with caution)
python tests/clean_test_data.py --site-id 3 --all

# Clean future-dated data (likely test data)
python tests/clean_test_data.py --future
```

### Modified Test Scripts
The following test scripts have been updated to use test site (site_id: 3):
- `tests/stress/stress_test.py` - Also includes automatic cleanup
- `tests/performance/load_test.py` - Also includes automatic cleanup
- `tests/integration/test_gsc_concurrent.py`
- `tests/integration/test_resume_sync.py`
- `tests/integration/test_gsc_limits.py`

## Memories

- First memory entry about project setup and configuration strategy
- 2025-07-24: Fixed test data pollution issue - discovered test scripts were using production site_id 17, updated all scripts to use test site_id 3 instead
- 2025-07-25: Improved dashboard performance by replacing Chart.js with lightweight SVG charts for data visualization
- 2025-07-25: Reorganized test files into proper `tests/` directory structure following Python best practices
- 2025-07-25: Fixed API issues and optimized CSV export performance:
  - Added root path (/) and /docs redirect to fix 404 errors
  - Implemented streaming CSV export using DuckDB analytics to handle large datasets efficiently
  - Added max_results parameter to CSV endpoint for result limiting
  - Created performance indexes for faster queries on large datasets
  - Replaced GROUP_CONCAT with efficient window functions to prevent memory issues
- Legacy code should not be used, as it is old code that might need optimization. Consider moving legacy parts to `.legacy/` directory for future reference