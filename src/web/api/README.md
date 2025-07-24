# GSC-CLI API Structure

## Overview

The API has been refactored into a modular structure for better organization and maintainability.

## Directory Structure

```
src/web/api/
├── __init__.py          # Package initialization
├── main.py              # Main FastAPI application
├── dependencies/        # Shared dependencies
│   └── __init__.py      # Container and dependency functions
├── routers/             # API route modules
│   ├── analytics.py     # Analytics endpoints (/api/v1/analytics/*)
│   ├── health.py        # Health check endpoints
│   ├── performance.py   # Performance data endpoints
│   ├── queries.py       # Query/keyword endpoints
│   ├── sites.py         # Site management endpoints
│   └── sync.py          # Synchronization status endpoints
└── middlewares/         # Custom middlewares (future use)
```

## Router Organization

### 1. **Health Router** (`health.py`)
- `/health` - System health check

### 2. **Sites Router** (`sites.py`)
- `/api/v1/sites/` - List all sites

### 3. **Analytics Router** (`analytics.py`)
- `/api/v1/analytics/ranking-data` - Get ranking data with filters

### 4. **Queries Router** (`queries.py`)
- `/api/v1/sites/{site_id}/queries/search` - Search queries containing keywords (PARTIAL MATCH)

### 5. **Performance Router** (`performance.py`)
- `/api/v1/sites/{site_id}/performance` - Get aggregated performance data
- `/api/v1/sites/{site_id}/ranking-data` - Get ranking data (legacy endpoint)
- `/api/v1/sites/{site_id}/page-keyword-performance` - Get page-keyword combinations
- `/api/v1/page-keyword-performance/` - POST endpoint for page-keyword data
- `/api/v1/page-keyword-performance/csv/` - CSV export endpoint

### 6. **Sync Router** (`sync.py`)
- `/api/v1/sync/status/{site_id}` - Get sync status for a site

## Key Features

### Modular Design
- Each router handles a specific domain of functionality
- Easy to add new endpoints to the appropriate router
- Clear separation of concerns

### Dependency Injection
- All dependencies are managed in `dependencies/__init__.py`
- Consistent dependency injection across all routers
- Easy to mock for testing

### Process Safety
- Uses ProcessSafeDatabase by default
- Supports multi-process deployments (Gunicorn, Uvicorn workers)
- Automatic connection management per process

### Backward Compatibility
- Original `src/web/api.py` still works as a compatibility layer
- All existing imports continue to function
- No breaking changes for API consumers

## Adding New Endpoints

1. Identify the appropriate router or create a new one
2. Add the endpoint to the router
3. If creating a new router, import and include it in `main.py`

Example:
```python
# In routers/new_feature.py
from fastapi import APIRouter

router = APIRouter(prefix="/new-feature", tags=["New Feature"])

@router.get("/example")
async def example_endpoint():
    return {"message": "Hello from new feature"}

# In main.py
from .routers import new_feature
app.include_router(new_feature.router, prefix="/api/v1")
```

## Query Matching Behavior

### Exact Match (Analytics endpoints)
- Used in `/api/v1/analytics/ranking-data`
- `queries: ["男士 理髮"]` only matches exactly "男士 理髮"

### Partial Match (Query search)
- Used in `/api/v1/sites/{site_id}/queries/search`
- `search_term=理髮` matches "男士理髮", "男士 理髮", "理髮店", etc.

## Future Improvements

1. Add request/response validation middleware
2. Add rate limiting middleware
3. Add authentication/authorization
4. Add request logging middleware
5. Create OpenAPI schema customizations
