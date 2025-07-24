# GSC Database API Cheat Sheet

Quick reference for all API endpoints and CLI commands.

## API Server

```bash
# Start development server
just dev-server  # http://localhost:8000

# Start production server
just prod-server
```

## Sites Management

### List All Sites
```bash
GET /api/v1/sites?active_only=true
```

### Get Site Details
```bash
GET /api/v1/sites/{site_id}
```

### Create New Site
```bash
POST /api/v1/sites
{
  "domain": "sc-domain:example.com",
  "name": "Example Site",
  "category": "news"
}
```

## Analytics & Search

### Search Ranking Data
```bash
POST /api/v1/analytics/ranking-data
{
  "hostname": "example.com",      # or use site_id
  "date_from": "2025-01-01",
  "date_to": "2025-01-31",
  "queries": ["keyword1", "keyword2"],
  "pages": ["url1", "url2"],      # optional
  "exact_match": false,           # default: true
  "group_by": ["query", "page"],  # default: ["query"]
  "limit": 100                    # default: 1000
}
```

### Performance Trends
```bash
GET /api/v1/analytics/performance-trends?hostname=example.com&days=30
# or
GET /api/v1/analytics/performance-trends?site_id=1&days=30
```

Response includes:
- Daily clicks, impressions, avg position
- 7-day rolling average
- Week-over-week changes
- Cumulative metrics

## Page-Keyword Performance

### Get Performance Data
```bash
POST /api/v1/page-keyword-performance/
{
  "hostname": "example.com",  # or use site_id
  "days": 30,                 # optional
  "query": "/article"         # URL filter (optional)
}
```

URL Filter Examples:
- `/article` - All article pages
- `/tag` - All tag pages
- `/news/` - News section
- `/category/tech` - Specific category
- `/author/` - Author pages
- `product-` - Pages containing "product-" in URL
- `.html` - All HTML pages

### Download as CSV
```bash
GET /api/v1/page-keyword-performance/csv?hostname=example.com&days=30&query=/article
```

Note: The `query` parameter uses SQL LIKE pattern matching (`%pattern%`), so it will match any URL containing the specified string.

## Sync Management

### Check Sync Status
```bash
GET /api/v1/sync/status?hostname=example.com&days=30
```

### Trigger Sync (Returns Job Info)
```bash
POST /api/v1/sync/trigger
{
  "hostname": "example.com",    # or use site_id
  "days": 30,
  "sync_mode": "skip",          # or "overwrite"
  "force": false
}
```

## CLI Commands

### Daily Data Sync
```bash
# Single site
just sync-site 1 7              # Site ID 1, last 7 days
just sync-site 1 14 overwrite   # Overwrite mode

# Multiple sites (sequential)
just sync-multiple "1 3 5" 7
just sync-multiple "1,3,5" 14 overwrite

# Direct script
poetry run python sync.py sync 1 7 skip
```

### Hourly Data Sync (Max 10 days)
```bash
# Single site
just sync-hourly 5 2            # Site ID 5, last 2 days
just sync-hourly 5 7 overwrite  # Overwrite mode

# Multiple sites
just sync-hourly-multiple "1 3 5" 2
just sync-hourly-multiple "4,5,11,16" 1

# Direct script
poetry run python sync_hourly.py sync 5 2
```

### Site Management
```bash
# List sites
just site-list

# Check sync status
just sync-status        # All sites
just sync-status 5      # Specific site
```

### Quality Checks
```bash
just check              # All checks (lint, type, test)
just lint               # Code formatting
just type-check         # Type checking
just test               # Run tests
```

## Common Patterns

### Using Hostname vs Site ID
Both are supported for most endpoints:
```javascript
// Using hostname (recommended for UX)
{ "hostname": "example.com", ... }

// Using site_id (faster if known)
{ "site_id": 1, ... }
```

### Date Ranges
```javascript
// Specific dates
{
  "date_from": "2025-01-01",
  "date_to": "2025-01-31"
}

// Or days from today
{ "days": 30 }
```

### Error Responses
```javascript
// 400 Bad Request
{
  "detail": "Either site_id or hostname must be provided"
}

// 404 Not Found
{
  "detail": "Site not found: example.com"
}

// 500 Internal Server Error
{
  "detail": "Database error: ..."
}
```

## Frontend Integration

### Basic Fetch Example
```javascript
// Get sites
const response = await fetch('http://localhost:8000/api/v1/sites');
const sites = await response.json();

// Search queries
const data = await fetch('http://localhost:8000/api/v1/analytics/ranking-data', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    hostname: "example.com",
    date_from: "2025-01-01",
    date_to: "2025-01-31",
    queries: ["keyword"],
    exact_match: false
  })
});

// Get page performance with URL filtering
const articlePages = await fetch('http://localhost:8000/api/v1/page-keyword-performance/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    hostname: "example.com",
    days: 30,
    query: "/article"  // Filter for article pages only
  })
});
```

### Download CSV
```javascript
// Trigger download with URL filter
window.location.href = `http://localhost:8000/api/v1/page-keyword-performance/csv?hostname=${hostname}&days=30&query=/article`;

// Download all pages (no filter)
window.location.href = `http://localhost:8000/api/v1/page-keyword-performance/csv?hostname=${hostname}&days=30`;
```

## Tips

1. **Sequential Processing**: GSC API requires sequential requests. Never use concurrent sync.
2. **URL Filtering**: Use `query` parameter to filter by URL patterns in performance endpoints
3. **Resume Capability**: Daily and hourly syncs support resume from interruption
4. **Data Delay**: GSC data typically has 2-3 day processing delay
5. **Hourly Limit**: Hourly data only available for last 10 days

## Environment Variables

```bash
# Override config values
export GSC__PATHS__DATABASE=/custom/path/gsc.db
export GSC__SYNC__BATCH_SIZE=1000
export GSC__LOG__LEVEL=DEBUG
```

## Health Check

```bash
GET /health

# Response
{
  "status": "healthy",
  "timestamp": "2025-01-24T12:00:00Z",
  "database": {
    "connected": true,
    "sites_count": 5
  }
}
```
