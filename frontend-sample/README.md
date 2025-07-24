# GSC API Frontend Integration Guide

This guide demonstrates how to integrate with the GSC Database API using modern frontend technologies without any build steps.

## Quick Start

1. Start the GSC API server:

   ```bash
   just dev-server
   # API will be available at http://localhost:8000
   ```

2. Open `index.html` in your browser or serve it locally:

   ```bash
   # Using Python
   python -m http.server 8080

   # Using Node.js
   npx serve .
   ```

## Available Examples

### 1. Simple API Tester (`index.html`)

- Basic form interface to test all API endpoints
- Uses Alpine.js for interactivity and Tailwind CSS for styling
- No build steps required

### 2. Advanced Dashboard (`dashboard.html`)

- Interactive dashboard with lightweight SVG charts
- Uses React (via CDN) with custom SVG charting (replaced Chart.js for 10x better performance)
- Form-based data loading (click "Load Dashboard" to fetch data)
- URL filtering support for analyzing specific page types
- Adjustable result limits to control data volume

**Performance Improvements**:
- Replaced Chart.js with custom SVG implementation for significantly faster rendering
- Added `limit` parameter to API calls to restrict result sets
- Form-based submission prevents unnecessary API calls on state changes
- URL filtering allows focusing on specific page patterns (e.g., `/article`, `/tag`)

**Performance Note**: For large sites with extensive data:
- Start with shorter date ranges (7-14 days) and lower result limits
- Use URL filters to focus on specific page types
- The API now supports limiting results for better performance
- Use the more focused search.html for specific query analysis

### 3. Query Search Tool (`search.html`)

- Specialized tool for searching GSC queries
- Export results to CSV
- Uses Vue.js (via CDN)

## API Endpoints

### Sites Management

- `GET /api/v1/sites` - List all sites
- `GET /api/v1/sites/{site_id}` - Get site details
- `POST /api/v1/sites` - Create new site

### Analytics

- `POST /api/v1/analytics/ranking-data` - Get ranking data with filters
- `GET /api/v1/analytics/performance-trends` - Get performance trends

### Performance Data

- `POST /api/v1/page-keyword-performance/` - Get page-keyword performance
  - Supports URL filtering with `query` parameter (e.g., `/article`, `/tag`, `/news`)
- `GET /api/v1/page-keyword-performance/csv/` - Download as CSV
  - Same filtering options available via query parameter

### Sync Status

- `GET /api/v1/sync/status` - Check sync status
- `POST /api/v1/sync/trigger` - Trigger sync (returns job info)

## Authentication

Currently, the API doesn't require authentication for local development. For production:

1. Add API key authentication
2. Use CORS configuration
3. Implement rate limiting

## CORS Setup

For local development, you may need to handle CORS. The API server includes CORS middleware, but you can also use a proxy.

## Tech Stack Used

- **Minimal Stack**: Alpine.js + Tailwind CSS
- **Advanced Stack**: React/Vue + Chart.js + Tailwind CSS
- **No build tools required** - Everything loads from CDN

**Note**: These examples use CDN versions of libraries for simplicity. For production use:

- Use PostCSS or Tailwind CLI instead of the CDN version
- Bundle and minify JavaScript dependencies
- Implement proper error boundaries and loading states

## Tips for Frontend Developers

1. **Use site hostname instead of site_id** when possible for better UX
2. **Handle loading states** - Some queries can take a few seconds
3. **Implement pagination** for large result sets
4. **Cache responses** when appropriate
5. **Show meaningful error messages** to users

## Example API Calls

```javascript
// Get sites
const response = await fetch('http://localhost:8000/api/v1/sites');
const sites = await response.json();

// Search queries
const searchData = {
  hostname: 'example.com',
  date_from: '2025-01-01',
  date_to: '2025-01-31',
  queries: ['keyword'],
  exact_match: false,
  limit: 100
};

const response = await fetch(
  'http://localhost:8000/api/v1/analytics/ranking-data',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(searchData)
  }
);
```
