# GSC Database Manager Test Suite

## Test Organization

```
tests/
├── performance/      # Performance and load tests
│   └── load_test.py
├── stress/          # Stress tests  
│   └── stress_test.py
├── integration/     # Integration tests
│   ├── test_gsc_concurrent.py
│   ├── test_gsc_limits.py
│   ├── test_real_gsc_auth.py
│   └── test_resume_sync.py
└── clean_test_data.py  # Test data cleanup utility
```

## Running Tests

### Performance Tests
```bash
# Run load test
poetry run python tests/performance/load_test.py

# Run stress test
poetry run python tests/stress/stress_test.py
```

### Integration Tests
```bash
# Test GSC API concurrency
poetry run python tests/integration/test_gsc_concurrent.py

# Test GSC API limits
poetry run python tests/integration/test_gsc_limits.py

# Test authentication
poetry run python tests/integration/test_real_gsc_auth.py

# Test sync resume functionality
poetry run python tests/integration/test_resume_sync.py
```

### Clean Up Test Data
```bash
# Clean recent test data (default: last 7 days)
poetry run python tests/clean_test_data.py

# Clean all test data for site
poetry run python tests/clean_test_data.py --site-id 3 --all

# Clean future-dated data
poetry run python tests/clean_test_data.py --future
```

## Important Notes

1. **Always use test site (site_id: 3)** for testing
2. **Never use production site IDs** in tests
3. **Clean up test data** after running tests
4. Test scripts include automatic cleanup where appropriate

## Test Site Information

- Site ID: 3
- Domain: test.com
- Purpose: Testing only

## Continuous Integration

For CI/CD pipelines, ensure:
1. Test database is isolated
2. Test data is cleaned after each run
3. Production credentials are not exposed