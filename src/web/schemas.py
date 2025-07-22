"""
Pydantic Schemas for the Web API

These models define the data structures for API requests and responses.
Using Pydantic ensures that the data conforms to a specific structure
and provides automatic validation and documentation.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class Site(BaseModel):
    """
    Represents a single site record as returned by the API.
    """

    id: int
    domain: str
    name: str
    category: Optional[str] = None
    is_active: bool

    class Config:
        """
        Pydantic configuration.
        `from_attributes = True` allows the model to be created from ORM objects
        or other objects with attributes, not just dictionaries.
        """

        from_attributes = True


class RankingDataRequest(BaseModel):
    """
    Request model for ranking data query.
    Supports both site_id and hostname for site identification.
    """

    site_id: Optional[int] = Field(None, description="Site ID to query", examples=[4])
    hostname: Optional[str] = Field(
        None,
        description="Site hostname (e.g., 'example.com' or 'sc-domain:example.com')",
        examples=["hkg.hankyu-hanshin-dept.co.jp", "sc-domain:example.com"],
    )
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)", examples=["2025-07-01"])
    end_date: str = Field(..., description="End date (YYYY-MM-DD)", examples=["2025-07-01"])
    queries: Optional[List[str]] = Field(
        default=None,
        description="Specific queries/keywords to filter (support spaces)",
        examples=[["阪急百貨香港", "日本阪急百貨 香港"]],
    )
    pages: Optional[List[str]] = Field(
        default=None,
        description="Specific pages/URLs to filter",
        examples=[
            [
                "https://hkg.hankyu-hanshin-dept.co.jp/",
                "https://hkg.hankyu-hanshin-dept.co.jp/about",
            ]
        ],
    )
    group_by: str = Field(
        default="query", description="Group results by 'query' or 'page'", examples=["query"]
    )
    max_results: Optional[int] = Field(
        default=1000,
        description="Maximum number of results to return (default: 1000, max: 10000)",
        examples=[10],
    )
    aggregation_mode: Optional[str] = Field(
        default="raw",
        description="Data aggregation mode: 'raw' (original data) or 'daily' (aggregated by day)",
        examples=["daily"],
    )


class RankingDataItem(BaseModel):
    """
    Single ranking data item.
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    query: Optional[str] = Field(None, description="Search query/keyword")
    page: Optional[str] = Field(None, description="Page URL")
    clicks: int = Field(..., description="Number of clicks")
    impressions: int = Field(..., description="Number of impressions")
    ctr: float = Field(..., description="Click-through rate")
    position: float = Field(..., description="Average position in search results")


class RankingDataResponse(BaseModel):
    """
    Response model for ranking data query.
    """

    site_id: int = Field(..., description="Site ID")
    start_date: str = Field(..., description="Query start date")
    end_date: str = Field(..., description="Query end date")
    group_by: str = Field(..., description="Grouping method used")
    total_results: int = Field(..., description="Total number of results")
    data: List[RankingDataItem] = Field(..., description="Ranking data items")


class DailyDataRequest(BaseModel):
    """
    Request model for daily aggregated data query.
    Similar to RankingDataRequest but returns daily averages.
    """

    site_id: Optional[int] = Field(None, description="Site ID to query", examples=[4])
    hostname: Optional[str] = Field(
        None,
        description="Site hostname (e.g., 'example.com' or 'sc-domain:example.com')",
        examples=["hkg.hankyu-hanshin-dept.co.jp", "sc-domain:example.com"],
    )
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)", examples=["2025-07-01"])
    end_date: str = Field(..., description="End date (YYYY-MM-DD)", examples=["2025-07-31"])
    queries: Optional[List[str]] = Field(
        default=None,
        description="Specific queries/keywords to filter (optional)",
        examples=[["阪急百貨香港", "日本阪急百貨 香港"]],
    )
    pages: Optional[List[str]] = Field(
        default=None,
        description="Specific pages/URLs to filter (optional)",
        examples=[["https://hkg.hankyu-hanshin-dept.co.jp/"]],
    )
    group_by: str = Field(
        default="query", description="Group results by 'query' or 'page'", examples=["query"]
    )
    max_results: Optional[int] = Field(
        default=365,
        description="Maximum number of daily records to return (default: 365, max: 1000)",
        examples=[30],
    )


class DailyDataItem(BaseModel):
    """
    Daily data item - same as RankingDataItem but aggregated by day.
    Each query/page has one record per day with averaged metrics.
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    query: Optional[str] = Field(None, description="Search query/keyword")
    page: Optional[str] = Field(None, description="Page URL")
    clicks: int = Field(..., description="Total clicks for this query/page on this day")
    impressions: int = Field(..., description="Total impressions for this query/page on this day")
    ctr: float = Field(..., description="Click-through rate")
    position: float = Field(..., description="Average position (rounded to integer)")


class DailyDataResponse(BaseModel):
    """
    Response model for daily aggregated data query.
    """

    site_id: int = Field(..., description="Site ID")
    start_date: str = Field(..., description="Query start date")
    end_date: str = Field(..., description="Query end date")
    group_by: str = Field(..., description="Grouping method used")
    total_results: int = Field(..., description="Total number of results")
    data: List[DailyDataItem] = Field(..., description="Daily aggregated data items")


class HourlyRankingRequest(BaseModel):
    """
    Request model for hourly ranking data query.
    Similar to RankingDataRequest but for hourly data.
    """

    site_id: Optional[int] = Field(None, description="Site ID to query", examples=[4])
    hostname: Optional[str] = Field(
        None,
        description="Site hostname (e.g., 'example.com' or 'sc-domain:example.com')",
        examples=["hkg.hankyu-hanshin-dept.co.jp", "sc-domain:example.com"],
    )
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)", examples=["2025-07-15"])
    end_date: str = Field(..., description="End date (YYYY-MM-DD)", examples=["2025-07-17"])
    queries: Optional[List[str]] = Field(
        default=None,
        description="Specific queries/keywords to filter",
        examples=[["阪急百貨香港", "日本阪急百貨 香港"]],
    )
    pages: Optional[List[str]] = Field(
        default=None,
        description="Specific pages/URLs to filter",
        examples=[["https://hkg.hankyu-hanshin-dept.co.jp/"]],
    )
    group_by: str = Field(
        default="query", description="Group results by 'query' or 'page'", examples=["query"]
    )
    max_results: Optional[int] = Field(
        default=1000,
        description="Maximum number of hourly records to return (default: 1000, max: 10000)",
        examples=[500],
    )


class HourlyRankingItem(BaseModel):
    """
    Single hourly ranking data item.
    """

    datetime: str = Field(..., description="Date and hour (YYYY-MM-DD HH:00)")
    query: Optional[str] = Field(None, description="Search query/keyword")
    page: Optional[str] = Field(None, description="Page URL")
    clicks: int = Field(..., description="Number of clicks in this hour")
    impressions: int = Field(..., description="Number of impressions in this hour")
    ctr: float = Field(..., description="Click-through rate")
    position: float = Field(..., description="Average position")


class HourlyRankingResponse(BaseModel):
    """
    Response model for hourly ranking data query.
    """

    site_id: int = Field(..., description="Site ID")
    start_date: str = Field(..., description="Query start date")
    end_date: str = Field(..., description="Query end date")
    group_by: str = Field(..., description="Grouping method used")
    total_results: int = Field(..., description="Total number of results")
    data: List[HourlyRankingItem] = Field(..., description="Hourly ranking data items")


class PageKeywordPerformanceRequest(BaseModel):
    """
    Request model for page keyword performance data.
    """

    site_id: Optional[int] = Field(None, description="Site ID to query", examples=[4])
    hostname: Optional[str] = Field(
        None,
        description="Site hostname (e.g., 'example.com' or 'sc-domain:example.com')",
        examples=["hkg.hankyu-hanshin-dept.co.jp", "sc-domain:example.com"],
    )
    days: Optional[int] = Field(
        None,
        description="Number of days to look back from today (default: all time)",
        examples=[30, 90],
    )
    max_results: Optional[int] = Field(
        default=1000,
        description="Maximum number of results to return (default: 1000, max: 10000)",
        examples=[100],
    )


class PageKeywordPerformanceItem(BaseModel):
    """
    Single page keyword performance item.
    """

    url: str = Field(..., description="Page URL")
    total_clicks: int = Field(..., description="Total clicks for this URL")
    total_impressions: int = Field(..., description="Total impressions for this URL")
    avg_ctr: float = Field(..., description="Average click-through rate")
    avg_position: float = Field(..., description="Average position in search results")
    keywords: List[str] = Field(..., description="List of keywords for this URL")
    keyword_count: int = Field(..., description="Number of distinct keywords")


class PageKeywordPerformanceResponse(BaseModel):
    """
    Response model for page keyword performance data.
    """

    site_id: int = Field(..., description="Site ID")
    time_range: str = Field(..., description="Time range for the data")
    total_results: int = Field(..., description="Total number of results")
    data: List[PageKeywordPerformanceItem] = Field(..., description="Page performance data items")
