"""
Queries Router

API endpoints for query/keyword related operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.services.database import Database

from ..dependencies import get_database

router = APIRouter(
    prefix="/sites/{site_id}/queries",
    tags=["Queries"],
)


@router.get("/search")
async def search_site_queries(
    site_id: int,
    search_term: str = Query(..., description="Keyword to search for in queries"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Maximum results to return"),
    db: Database = Depends(get_database),
):
    """
    Search for queries containing specific keywords for a site.

    Example: /api/v1/sites/1/queries/search?search_term=是&start_date=2025-07-01&end_date=2025-07-15

    This will find all queries containing "是" such as:
    - "什麼是"
    - "是不是"
    - "台北是"
    - "男士 理髮" (if searching for "理髮")
    - "男士理髮" (if searching for "理髮")

    This endpoint uses PARTIAL MATCHING with SQL LIKE operator,
    unlike the ranking-data endpoint which uses EXACT MATCH.
    """
    query = """
        SELECT query,
               SUM(clicks) as total_clicks,
               SUM(impressions) as total_impressions,
               AVG(ctr) as avg_ctr,
               AVG(position) as avg_position,
               COUNT(DISTINCT date) as days_appeared
        FROM gsc_performance_data
        WHERE site_id = ?
        AND date BETWEEN ? AND ?
        AND query LIKE ?
        GROUP BY query
        ORDER BY total_impressions DESC
        LIMIT ?
    """

    params = [site_id, start_date, end_date, f"%{search_term}%", limit]

    try:
        with db._lock:
            results = db._connection.execute(query, params).fetchall()
            data = [dict(row) for row in results]

        return {
            "site_id": site_id,
            "search_term": search_term,
            "date_range": f"{start_date} to {end_date}",
            "total_queries_found": len(data),
            "queries": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query search failed: {str(e)}")
