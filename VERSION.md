# GSC Database Version History

## Version 2.1.0 (2025-01-24)

### New Features
- **Hourly Data Sync**: Added support for GSC hourly data synchronization
  - New commands: `just sync-hourly` and `just sync-hourly-multiple`
  - Scripts: `sync_hourly.py` and `sync_hourly_multiple.py`
  - Limited to last 10 days per GSC API constraints
  - Supports resume capability for interrupted syncs

- **Frontend Sample Directory**: Created `/frontend-sample` with examples
  - Simple API tester using Alpine.js + Tailwind CSS
  - Advanced dashboard using React + Chart.js
  - Query search tool using Vue.js
  - Complete API examples in JavaScript

- **Documentation Updates**:
  - Added CHEATSHEET.md for quick API reference
  - Updated CLAUDE.md with hourly sync documentation
  - Added VERSION.md for tracking changes

### Improvements
- Enhanced URL filtering for page-keyword performance endpoints
  - Support for filtering by patterns like `/article`, `/tag`, `/news`
  - Available in both POST and CSV download endpoints
- Added more examples in frontend samples demonstrating URL filtering

### Bug Fixes
- Fixed site_id assignment bug causing "0 inserted" in overwrite mode
- Fixed memory issues in sync by processing data day-by-day
- Fixed type checking errors in cache.py
- Fixed date type imports in hybrid.py

### Technical Changes
- Modernized GSC client to use HOUR dimension and HOURLY_ALL dataState
- Added `insert_hourly_data()` and `delete_hourly_data_for_date()` to database
- Improved sync progress tracking to support hourly sync type

---

## Version 2.0.0 (2025-01-23)

### Major Refactoring
- **Complete Modernization**: Migrated from FastAPI to Litestar
  - Replaced Pydantic with msgspec for better performance
  - Implemented hybrid SQLite + DuckDB architecture
  - Added modern async/await patterns throughout

### Core Features
- **High-Performance API**: Litestar-based API with msgspec serialization
- **Hybrid Database**: SQLite for storage, DuckDB for analytics
- **Resume Capability**: Added sync progress tracking for interrupted syncs
- **Memory Efficient**: Day-by-day processing to handle large datasets

### Infrastructure
- Sequential processing enforced for GSC API compatibility
- Thread-safe database operations with proper locking
- Comprehensive error handling and retry logic
- Path resolution relative to project root

### Breaking Changes
- API endpoints moved to Litestar framework
- Models migrated from Pydantic to msgspec
- Database operations now use hybrid approach
- Configuration uses TOML instead of JSON

---

## Version 1.0.0 (Legacy)

### Original Features
- FastAPI-based web API
- SQLite database with direct queries
- Basic daily sync functionality
- Google Search Console integration
- Multi-process support (deprecated due to GSC API limitations)

### Known Issues (Fixed in v2.0)
- Memory overflow when syncing large datasets
- No resume capability for interrupted syncs
- GSC API pagination not properly implemented
- Concurrent processing caused 100% failure rate

---

## Migration Notes

### From v1.x to v2.x
1. **API Changes**: Update all API calls to new Litestar endpoints
2. **Model Changes**: Replace Pydantic models with msgspec
3. **Database**: No migration needed - backward compatible
4. **Configuration**: Convert JSON config to TOML format

### From v2.0 to v2.1
- No breaking changes
- New features are additive
- Hourly sync is optional and separate from daily sync

## Future Roadmap

### Planned for v2.2
- [ ] Complete type checking fixes
- [ ] Add comprehensive test coverage
- [ ] Implement data archival to Parquet
- [ ] Add real-time sync monitoring dashboard

### Planned for v3.0
- [ ] GraphQL API support
- [ ] Multi-tenant architecture
- [ ] Advanced analytics with ML insights
- [ ] Automated anomaly detection
