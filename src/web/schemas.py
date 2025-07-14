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
    """

    site_id: int = Field(description="Site ID to query", example=4)
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)", example="2025-07-01")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)", example="2025-07-01")
    queries: Optional[List[str]] = Field(
        None,
        description="Specific queries/keywords to filter (support spaces)",
        example=["阪急百貨香港", "日本阪急百貨 香港"],
    )
    pages: Optional[List[str]] = Field(
        None,
        description="Specific pages/URLs to filter",
        example=[
            "https://hkg.hankyu-hanshin-dept.co.jp/",
            "https://hkg.hankyu-hanshin-dept.co.jp/about",
        ],
    )
    group_by: str = Field(
        "query", description="Group results by 'query' or 'page'", example="query"
    )
    max_results: Optional[int] = Field(
        1000,
        description="Maximum number of results to return (default: 1000, max: 10000)",
        example=10,
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
