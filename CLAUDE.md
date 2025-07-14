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
```

### Data Synchronization
```bash
# Sync specific site for N days
just sync-site <site_id> [days]

# Example: Sync site ID 1 for last 7 days
just sync-site 1 7

# Batch sync multiple sites
just sync-multiple "1 3 5" [days]       # Enhanced with progress tracking & error handling
just batch-sync "1 3 5" [days]          # Windows-optimized with detailed logging

# Monitor sync progress and status
just sync-status                         # View all sites sync status
just sync-status [site_id]              # View specific site status

# Smart sync with network diagnostics
just smart-sync [site_id] [days]
just conservative-sync [site_id] [days]  # single-threaded, for SSL issues
just adaptive-sync [site_id] [days]      # auto-adjust concurrency
just turbo-sync [site_id] [days]         # high-performance mode

# Full maintenance (sync all, backup, cleanup)
just maintenance
```

### Windows Compatibility Improvements

The project now includes enhanced Windows support:

- **Cross-platform sync commands**: All sync commands now work seamlessly on both Windows and Unix systems
- **Windows-optimized batch sync**: `just batch-sync` provides enhanced error handling and detailed logging for Windows environments
- **Progress monitoring**: Real-time progress tracking with success/failure counts and timing information
- **Proper process management**: Windows-compatible process checking and management
- **Error recovery guidance**: Intelligent suggestions for handling sync failures based on the specific error context

### Sync Status and Monitoring

Instead of using inappropriate commands like `sync daily --day1 --all-sites` to check progress, use:

```bash
# Check current sync status
just sync-status

# Monitor specific site
just sync-status 5

# Check running processes
just check-processes

# View recent sync activity
poetry run gsc-cli sync status --show-recent 20
```

### Site Management
```bash
# List all sites
just site-list

# Add new site
just site-add "sc-domain:example.com"
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
# Network diagnostics
just network-check

# Process management
just check-processes
just kill-processes

# Sitemap redundancy analysis
just sitemap-redundancy --site-id <id>
just sitemap-help

# Backup management
just list-large-backups [count]
just clean-all  # DANGEROUS: deletes all data
```

## Architecture Overview

### Core Structure
- **src/app.py**: Main CLI entry point using Typer
- **src/containers.py**: Dependency injection container using dependency-injector
- **src/config.py**: Pydantic-based configuration management with TOML support

### Service Layer
- **src/services/database.py**: SQLite database operations with thread-safe connection handling
- **src/services/gsc_client.py**: Google Search Console API client with retry logic
- **src/services/site_service.py**: Site management operations
- **src/services/hourly_database.py**: Hourly data synchronization service
- **src/services/analysis_service.py**: Data analysis and reporting

### CLI Commands
- **src/cli/commands.py**: Typer command definitions organized into sub-apps:
  - auth_app: Google API authentication
  - site_app: Site management
  - sync_app: Data synchronization
  - analyze_app: Data analysis and reporting

### Analysis Modules
- **src/analysis/hourly_performance_analyzer.py**: Hourly traffic analysis
- **src/analysis/interactive_data_visualizer.py**: Interactive data visualization

### Web API
- **src/web/api.py**: FastAPI server for external integrations
- **src/web/schemas.py**: Pydantic response models

### Utilities
- **src/utils/rich_console.py**: Rich terminal output configuration
- **src/utils/system_health_check.py**: Network connectivity diagnostics
- **src/utils/state_manager.py**: Application state management

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

The application uses careful concurrency management:
- **SQLite connections**: `check_same_thread=False` with `threading.RLock`
- **GSC API calls**: Configurable worker pools with SSL error handling
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

### Network Issues
The application includes sophisticated network error handling for common GSC API issues:
- SSL handshake failures
- Connection timeouts
- Certificate validation errors

Use `just network-check` to diagnose connectivity issues and choose appropriate sync commands based on network stability.

### Cursor Rules Integration
This project includes Cursor-specific development rules:
- **Python/FastAPI patterns**: Functional programming, RORO pattern, proper error handling
- **Interactive feedback requirements**: MCP interactive_feedback must be called during processes

### Data Safety
- Automatic daily backups to `data/backups/`
- Compression of backup files
- 30-day backup retention policy
- `just clean-all` is destructive - use with extreme caution
