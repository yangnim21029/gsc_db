"""Data models using msgspec for high-performance serialization."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

import msgspec


class SyncMode(str, Enum):
    """
    GSC data synchronization modes.
    
    SKIP (default): Skip existing records, only insert new data
    OVERWRITE: Replace existing records with new data (useful for data corrections)
    """
    SKIP = "skip"
    OVERWRITE = "overwrite"


class Site(msgspec.Struct, kw_only=True):
    """Site model."""
    
    id: int
    domain: str
    name: str
    category: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PerformanceData(msgspec.Struct, kw_only=True):
    """GSC performance data model."""
    
    site_id: int
    date: date
    page: str
    query: str
    device: str = "DESKTOP"
    search_type: str = "WEB"
    clicks: int
    impressions: int
    ctr: float
    position: float


class HourlyRanking(msgspec.Struct, kw_only=True):
    """Hourly ranking data model."""
    
    site_id: int
    date: date
    hour: int
    query: str
    page: str
    position: float
    clicks: int
    impressions: int
    ctr: float


class RankingDataRequest(msgspec.Struct, kw_only=True):
    """API request for ranking data."""
    
    site_id: Optional[int] = None
    hostname: Optional[str] = None
    date_from: str
    date_to: str
    queries: Optional[list[str]] = None
    pages: Optional[list[str]] = None
    group_by: list[str] = msgspec.field(default_factory=lambda: ["query"])
    limit: int = 1000
    exact_match: bool = True


class PerformanceMetrics(msgspec.Struct, kw_only=True):
    """Aggregated performance metrics."""
    
    clicks: int
    impressions: int
    ctr: float
    position: float
    unique_queries: Optional[int] = None
    unique_pages: Optional[int] = None


class RankingDataItem(msgspec.Struct, kw_only=True):
    """Individual ranking data item."""
    
    query: Optional[str] = None
    page: Optional[str] = None
    clicks: int
    impressions: int
    ctr: float
    position: float
    rank_by_clicks: Optional[int] = None
    percentile_clicks: Optional[float] = None


class RankingDataResponse(msgspec.Struct, kw_only=True):
    """API response for ranking data."""
    
    data: list[RankingDataItem]
    total: int
    aggregations: PerformanceMetrics
    metadata: Optional[dict] = None


class SyncStatusResponse(msgspec.Struct, kw_only=True):
    """Sync status response."""
    
    site_id: int
    site_name: str
    daily_coverage: dict[str, bool]
    hourly_coverage: dict[str, dict[str, bool]]
    last_sync: Optional[datetime] = None
    total_records: int


class QuerySearchResult(msgspec.Struct, kw_only=True):
    """Query search result model."""
    
    query: str
    total_clicks: int
    total_impressions: int
    avg_ctr: float
    avg_position: float
    days_appeared: int


class PerformanceTrendData(msgspec.Struct, kw_only=True):
    """Daily performance trend data."""
    
    date: str
    total_clicks: float
    total_impressions: float
    avg_position: float
    unique_queries: int
    clicks_7d_avg: Optional[float] = None
    clicks_wow_change: Optional[float] = None
    cumulative_clicks: float


class PerformanceTrendSummary(msgspec.Struct, kw_only=True):
    """Performance trend summary statistics."""
    
    total_clicks: int
    avg_position: float
    unique_queries: int


class PerformanceTrendsResponse(msgspec.Struct, kw_only=True):
    """Response for performance trends analysis."""
    
    data: list[PerformanceTrendData]
    summary: PerformanceTrendSummary


class PageKeywordPerformanceRequest(msgspec.Struct, kw_only=True):
    """Request for page-keyword performance data."""
    
    site_id: Optional[int] = None
    hostname: Optional[str] = None
    days: Optional[int] = None
    query: Optional[str] = None


class PageKeywordPerformanceData(msgspec.Struct, kw_only=True):
    """Page-keyword performance data item."""
    
    url: str
    total_clicks: int
    total_impressions: int
    avg_ctr: float
    avg_position: float
    keywords: list[str]
    keyword_count: int


class PageKeywordPerformanceResponse(msgspec.Struct, kw_only=True):
    """Response for page-keyword performance data."""
    
    site_id: int
    data: list[PageKeywordPerformanceData]
    total_pages: int
    total_keywords: int


class SyncTestRequest(msgspec.Struct, kw_only=True):
    """Request for sync timing test."""
    
    site_ids: list[int]
    days: int = 5


class SyncRequest(msgspec.Struct, kw_only=True):
    """Request for triggering GSC data sync."""
    
    site_id: Optional[int] = None
    hostname: Optional[str] = None
    days: int = 7
    sync_mode: SyncMode = SyncMode.SKIP
    force: bool = False  # Skip date availability checks