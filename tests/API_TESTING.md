# API Contract Testing Guide

## Overview

This directory contains API contract tests to ensure our API endpoints maintain stable interfaces across code changes. These tests verify:

- Response status codes
- Response data structures
- Parameter validation
- Error formats
- CSV export formats
- Performance characteristics

## Quick Start

### Running Quick Tests

```bash
# Run all quick contract tests
python tests/test_api_quick.py

# Test specific endpoint
python tests/test_api_quick.py --endpoint /api/v1/health

# Test with parameters
python tests/test_api_quick.py --endpoint /api/v1/page-keyword-performance --params '{"site_id": 1, "days": 7}'

# Test against different server
python tests/test_api_quick.py --base-url http://staging.example.com
```

### Running Full Test Suite

```bash
# Run all contract tests
poetry run pytest tests/test_api_contract.py -v

# Run specific test
poetry run pytest tests/test_api_contract.py::TestAPIContract::test_root_endpoint_contract -v

# Run with coverage
poetry run pytest tests/test_api_contract.py --cov=src.api --cov-report=html
```

## Test Structure

### 1. Contract Tests (`test_api_contract.py`)

Comprehensive tests that verify:
- Exact response structures
- Data types
- Required fields
- Optional fields
- Error response formats

### 2. Quick Tests (`test_api_quick.py`)

Lightweight script for rapid testing:
- No pytest required
- Colored terminal output
- Can test individual endpoints
- Useful for debugging

### 3. Contract Definitions (`api_contracts.yaml`)

YAML file documenting:
- All endpoints
- Expected parameters
- Response formats
- Error codes
- Data format rules

## API Contracts

### Core Endpoints

1. **Root Endpoint** (`GET /`)
   ```json
   {
     "service": "GSC Database Manager API",
     "version": "2.0.0",
     "docs": "/schema/swagger",
     "openapi": "/schema"
   }
   ```

2. **Health Check** (`GET /api/v1/health`)
   ```json
   {
     "status": "healthy",
     "database": true,
     "timestamp": "2024-01-25T10:30:00Z",
     "version": "2.0.0"
   }
   ```

3. **Sites List** (`GET /api/v1/sites`)
   ```json
   [
     {
       "id": 1,
       "domain": "example.com",
       "name": "Example Site",
       "category": "blog",
       "is_active": true,
       "created_at": "2024-01-01T00:00:00Z",
       "updated_at": "2024-01-01T00:00:00Z"
     }
   ]
   ```

4. **Page-Keyword Performance** (`GET /api/v1/page-keyword-performance`)

   Parameters:
   - `site_id` (required): Site ID
   - `days` (optional): Number of days (default: 30)
   - `start_date` (optional): ISO date
   - `end_date` (optional): ISO date
   - `url_filter` (optional): URL pattern
   - `limit` (optional): Max results (default: 1000)

   Response:
   ```json
   {
     "data": [
       {
         "url": "https://example.com/page",
         "total_clicks": 100,
         "total_impressions": 1000,
         "avg_ctr": 0.1000,
         "avg_position": 5.50,
         "keywords": ["keyword1", "keyword2"],
         "keyword_count": 2
       }
     ],
     "total_pages": 10,
     "total_keywords": 50,
     "generated_at": "2024-01-25T10:30:00Z"
   }
   ```

5. **CSV Export** (`GET /api/v1/page-keyword-performance/csv`)

   Same parameters as JSON endpoint, plus:
   - `max_results` (optional): Limit results

   Response:
   ```csv
   url,total_clicks,total_impressions,avg_ctr,avg_position,keywords,keyword_count
   "https://example.com/page",100,1000,0.1000,5.50,"keyword1|keyword2",2
   ```

### Error Response Format

All errors follow this structure:
```json
{
  "detail": "Error message"
}
```

Or for validation errors:
```json
{
  "detail": [
    {
      "loc": ["query", "site_id"],
      "msg": "Input should be a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

## Data Format Rules

### Numbers
- **CTR**: Always 4 decimal places (e.g., 0.1234)
- **Position**: Always 2 decimal places (e.g., 10.50)
- **Counts**: Always integers

### Dates
- All dates in ISO 8601 format
- Timestamps include timezone (Z for UTC)
- Date parameters accept YYYY-MM-DD format

### CSV Format
- UTF-8 encoding
- Header row always present
- String values quoted
- Keywords separated by pipe (|)
- Line endings: \n

## Backwards Compatibility

When modifying APIs:

✅ **Allowed Changes:**
- Adding new optional parameters
- Adding new fields to responses
- Adding new endpoints
- Improving performance

❌ **Breaking Changes:**
- Changing parameter names
- Changing response field names
- Changing field types
- Removing fields
- Changing error formats

## CI/CD Integration

Contract tests run automatically on:
- Every push to main/develop branches
- Every pull request
- When API files change

GitHub Actions workflow: `.github/workflows/api-contract-tests.yml`

## Adding New Tests

1. Add endpoint definition to `api_contracts.yaml`
2. Add test case to `test_api_contract.py`
3. Add quick test to `test_api_quick.py`
4. Run tests locally before committing

Example:
```python
async def test_new_endpoint_contract(self, client: AsyncTestClient) -> None:
    """Test new endpoint returns expected structure."""
    response = await client.get("/api/v1/new-endpoint")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "field1" in data
    assert isinstance(data["field1"], str)
```

## Troubleshooting

### Test Failures

1. **Status code mismatch**: Check if endpoint exists and permissions
2. **Missing fields**: Verify response includes all required fields
3. **Type errors**: Ensure data types match contract
4. **CSV format**: Check delimiter and quoting

### Running Against Production

```bash
# Test production API (read-only endpoints)
python tests/test_api_quick.py --base-url https://api.example.com
```

### Debugging

```bash
# Verbose output
poetry run pytest tests/test_api_contract.py -vv -s

# Stop on first failure
poetry run pytest tests/test_api_contract.py -x

# Show local variables
poetry run pytest tests/test_api_contract.py -l
```
