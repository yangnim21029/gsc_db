-- Optimize database for page-keyword performance queries
-- These indexes significantly improve query performance for large datasets

-- Composite index for page-keyword performance queries
CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_page_clicks
ON gsc_performance_data(site_id, page, clicks DESC);

-- Index for date range filtering
CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_date
ON gsc_performance_data(site_id, date);

-- Index for keyword aggregation
CREATE INDEX IF NOT EXISTS idx_gsc_performance_site_query_clicks
ON gsc_performance_data(site_id, query, clicks DESC);

-- Composite index for full query pattern
CREATE INDEX IF NOT EXISTS idx_gsc_performance_composite
ON gsc_performance_data(site_id, date, page, query, clicks DESC);

-- Analyze tables to update query planner statistics
ANALYZE gsc_performance_data;
