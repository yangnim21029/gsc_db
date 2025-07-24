# Bug Notes and Discussion - 2025-07-21

## Issue 1: Poetry Installation - Missing toml Module

### Problem
When running `just dev-server`, encountered error:
```
ModuleNotFoundError: No module named 'toml'
```

### Root Cause
Poetry virtual environment was not properly initialized with all dependencies.

### Solution
Run `poetry install` to install all project dependencies including the `toml` module.

## Issue 2: API Server Startup Failure - Undefined get_database Function

### Problem
After fixing the toml issue, the FastAPI server failed to start with error:
```
NameError: name 'get_database' is not defined
```

### Root Cause
The `/api/v1/ranking-data-hourly/` endpoint was using `Depends(get_database)` but the `get_database` function was not defined in `api.py`.

### Solution
Added the missing dependency provider function:
1. Import Database service: `from src.services.database import Database`
2. Add get_database function:
```python
def get_database() -> Database:
    """Get Database instance from container"""
    return container.database()
```

### Commit
- Hash: 77efca9
- Message: "fix: add missing get_database dependency function in API"

## Issue 3: Missing Schema Definitions on Other Machines

### Problem
After pulling changes on another computer, encountered errors about missing schema definitions:
- DailyDataResponse not defined
- DailyDataRequest not defined
- HourlyRankingRequest not defined
- HourlyRankingResponse not defined

### Root Cause
The API endpoints were using schema models that existed locally but weren't committed to the repository.

### Solution
Committed all missing schema definitions in `src/web/schemas.py`:
- Updated RankingDataRequest to support hostname parameter
- Added DailyDataRequest and DailyDataResponse for daily data endpoint
- Added HourlyRankingRequest and HourlyRankingResponse for hourly data endpoint

### Commit
- Hash: 937947e
- Message: "feat: add missing schema definitions for API endpoints"

## Feature Verification: Hostname Support in API

### Verification
Tested that API endpoints support hostname parameter without requiring site_id:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ranking-data/" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "pretty.presslogic.com",
    "start_date": "2025-07-01",
    "end_date": "2025-07-07",
    "group_by": "query",
    "max_results": 10
  }'
```

### Result
Successfully returned data for site_id 18, confirming hostname resolution works correctly.

## Key Learnings

1. **Pre-commit Hooks**: The project has pre-commit hooks that automatically format code. When commits fail due to formatting, re-stage and retry.

2. **Dependency Management**: Always ensure all dependencies are installed with `poetry install` before running the application.

3. **Complete Commits**: When adding new API endpoints, ensure both the endpoint code AND the schema definitions are committed together.

4. **API Design**: All data endpoints now support both `site_id` and `hostname` parameters for flexibility.

## Commands Reference

### Running the API Server
```bash
# Using justfile
just dev-server

# Using poetry directly
poetry run uvicorn src.web.api:app --reload

# Production mode
poetry run uvicorn src.web.api:app --host 0.0.0.0 --port 8000
```
