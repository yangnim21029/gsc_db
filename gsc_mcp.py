#!/usr/bin/env python3
"""
GSC MCP 服務 - 提供 GSC 資料查詢工具給 Claude
"""
from datetime import datetime, timedelta
import duckdb

# Only import MCP when running as main module
if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("gsc")
else:
    # Create a dummy decorator for when imported as module
    class DummyMCP:
        def tool(self):
            def decorator(func):
                return func

            return decorator

    mcp = DummyMCP()


def escape_sql_string(value):
    """轉義 SQL 字串中的特殊字元"""
    if value is None:
        return None
    return str(value).replace("'", "''")


def get_parquet_path(site_url=None, data_type="daily"):
    """取得 parquet 檔案路徑
    
    Args:
        site_url: 網站 URL
        data_type: 資料類型 ("daily" 或 "hourly")
    """
    if site_url:
        folder_name = site_url.replace(":", "_").replace("/", "_")
        if data_type == "hourly":
            return f"data/{folder_name}/hourly/*.parquet"
        else:
            return f"data/{folder_name}/*/*.parquet"
    else:
        if data_type == "hourly":
            return "data/*/hourly/*.parquet"
        else:
            return "data/*/*/*.parquet"


@mcp.tool()
def query(site: str, sql: str, data_type: str = "daily"):
    """執行 SQL 查詢 GSC 數據

    Args:
        site: 網站名稱（會轉換成資料夾名稱）
        sql: SQL 查詢，使用 {site} 作為資料表佔位符
        data_type: 資料類型 ("daily" 或 "hourly"，預設 "daily")

    Returns:
        查詢結果的字典列表

    Example:
        sql = "SELECT * FROM {site} WHERE clicks > 100 ORDER BY date DESC LIMIT 10"
        
    Note:
        Hourly data 包含額外的 hour 欄位 (0-23)
    """
    conn = duckdb.connect()
    parquet_path = get_parquet_path(site, data_type)
    sql = sql.replace("{site}", f"'{parquet_path}'")
    return conn.execute(sql).fetchdf().to_dict("records")


@mcp.tool()
def show_page_queries(site: str, page: str, days: int = 30):
    """看頁面的搜尋詞

    Args:
        site: 網站 URL
        page: 頁面 URL
        days: 查詢最近幾天的資料（預設 30）

    Returns:
        該頁面的搜尋詞列表，包含點擊、曝光、排名
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    return query(
        site,
        f"""
        SELECT 
            query,
            SUM(clicks) as clicks,
            SUM(impressions) as impressions,
            AVG(position) as avg_position
        FROM {{site}}
        WHERE page = '{escape_sql_string(page)}' 
          AND date >= '{date_from}'
        GROUP BY query
        ORDER BY impressions DESC
        LIMIT 50
    """,
    )


@mcp.tool()
def show_keyword_pages(site: str, keyword: str, days: int = 30):
    """看關鍵字排哪些頁

    Args:
        site: 網站 URL
        keyword: 搜尋關鍵字
        days: 查詢最近幾天的資料（預設 30）

    Returns:
        該關鍵字的頁面列表，包含平均排名和點擊數
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    return query(
        site,
        f"""
        SELECT 
            page,
            AVG(position) as avg_position,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions
        FROM {{site}}
        WHERE query = '{escape_sql_string(keyword)}' 
          AND date >= '{date_from}'
        GROUP BY page
        ORDER BY total_clicks DESC
    """,
    )


@mcp.tool()
def search_keywords(site: str, pattern: str, days: int = 30):
    """查詢包含特定模式的關鍵字

    Args:
        site: 網站 URL
        pattern: 關鍵字模式（使用 SQL LIKE 語法，例如 "%python%"）
        days: 查詢最近幾天的資料（預設 30）

    Returns:
        符合模式的關鍵字列表，包含點擊、曝光、平均排名
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    return query(
        site,
        f"""
        SELECT 
            query,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            AVG(position) as avg_position
        FROM {{site}}
        WHERE query LIKE '{escape_sql_string(pattern)}'
          AND date >= '{date_from}'
        GROUP BY query
        ORDER BY total_impressions DESC
        LIMIT 100
    """,
    )


@mcp.tool()
def best_pages(site: str, days: int = 30, limit: int = 20):
    """查詢一個時間段內表現最好的頁面

    Args:
        site: 網站 URL
        days: 查詢最近幾天的資料（預設 30）
        limit: 返回頁面數量（預設 20）

    Returns:
        表現最好的頁面列表，按點擊數排序
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    return query(
        site,
        f"""
        SELECT 
            page,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            AVG(position) as avg_position,
            CASE WHEN SUM(impressions) > 0 
                THEN CAST(SUM(clicks) AS FLOAT) / SUM(impressions) * 100 
                ELSE 0 
            END as ctr
        FROM {{site}}
        WHERE date >= '{date_from}'
        GROUP BY page
        ORDER BY total_clicks DESC
        LIMIT {limit}
    """,
    )


@mcp.tool()
def track_pages(site: str, pages: list[str], keywords: list[str] | None = None, days: int = 30):
    """追蹤一組頁面和關鍵字

    Args:
        site: 網站 URL
        pages: 要追蹤的頁面列表
        keywords: 要追蹤的關鍵字列表（可選）
        days: 查詢最近幾天的資料（預設 30）

    Returns:
        頁面和關鍵字的效能資料
    """
    conn = duckdb.connect()

    # 處理站點路徑
    folder_name = site.replace(":", "_").replace("/", "_")
    parquet_path = f"data/{folder_name}/*/*.parquet"

    # 轉義並建立 IN 條件
    escaped_pages = [escape_sql_string(p) for p in pages]
    pages_list = "','".join([p for p in escaped_pages if p is not None])

    # 如果有指定關鍵字就加條件
    keyword_filter = ""
    if keywords and len(keywords) > 0:
        escaped_keywords = [escape_sql_string(k) for k in keywords]
        keywords_list = "','".join([k for k in escaped_keywords if k is not None])
        keyword_filter = f"AND query IN ('{keywords_list}')"

    query_sql = f"""
    SELECT 
        date,
        page,
        query,
        SUM(clicks) as clicks,
        SUM(impressions) as impressions,
        AVG(position) as position
    FROM '{parquet_path}'
    WHERE 
        page IN ('{pages_list}')
        {keyword_filter}
        AND date >= '{escape_sql_string((datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"))}'
    GROUP BY date, page, query
    ORDER BY date DESC, clicks DESC
    """

    return conn.execute(query_sql).fetchdf().to_dict("records")


@mcp.tool()
def pages_queries(site: str, pages: list[str]):
    """查詢頁面實際排名的關鍵字

    Args:
        site: 網站 URL
        pages: 要查詢的頁面列表

    Returns:
        每個頁面的關鍵字列表
    """
    conn = duckdb.connect()

    # 處理站點路徑
    folder_name = site.replace(":", "_").replace("/", "_")
    parquet_path = f"data/{folder_name}/*/*.parquet"

    # 轉義並建立 IN 條件
    escaped_pages = [escape_sql_string(p) for p in pages]
    pages_list = "','".join([p for p in escaped_pages if p is not None])

    query_sql = f"""
    SELECT 
        page, 
        query, 
        SUM(clicks) as clicks, 
        SUM(impressions) as impressions,
        AVG(position) as avg_position
    FROM '{parquet_path}'
    WHERE page IN ('{pages_list}')
    GROUP BY page, query
    ORDER BY page, impressions DESC
    """

    return conn.execute(query_sql).fetchdf().to_dict("records")


@mcp.tool()
def compare_periods(site: str, period_type: str = "week", custom_periods: dict = {}):
    """比較兩個時期的 GSC 表現

    Args:
        site: 站點名稱
        period_type: 比較類型 - "week"（本週vs上週）、"month"（本月vs上月）、"custom"（自訂）
        custom_periods: 自訂時期 {"period1": {"start": "2024-01-01", "end": "2024-01-07"}, ...}

    Returns:
        時期比較的結果
    """
    conn = duckdb.connect()
    folder_name = site.replace(":", "_").replace("/", "_")
    parquet_path = f"data/{folder_name}/*/*.parquet"

    # 決定時間段
    if period_type == "week":
        # 本週 vs 上週
        today = datetime.now().date()
        # 本週一
        this_monday = today - timedelta(days=today.weekday())
        # 上週一
        last_monday = this_monday - timedelta(days=7)

        period1_start = last_monday.strftime("%Y-%m-%d")
        period1_end = (this_monday - timedelta(days=1)).strftime("%Y-%m-%d")
        period2_start = this_monday.strftime("%Y-%m-%d")
        period2_end = today.strftime("%Y-%m-%d")

    elif period_type == "month":
        # 本月 vs 上月
        today = datetime.now().date()
        this_month_start = today.replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        period1_start = last_month_start.strftime("%Y-%m-%d")
        period1_end = last_month_end.strftime("%Y-%m-%d")
        period2_start = this_month_start.strftime("%Y-%m-%d")
        period2_end = today.strftime("%Y-%m-%d")

    elif period_type == "custom" and len(custom_periods) > 0:
        period1_start = custom_periods["period1"]["start"]
        period1_end = custom_periods["period1"]["end"]
        period2_start = custom_periods["period2"]["start"]
        period2_end = custom_periods["period2"]["end"]
    else:
        raise ValueError("Invalid period_type or missing custom_periods")

    query_sql = f"""
    WITH period1 AS (
        SELECT 
            SUM(clicks) as clicks,
            SUM(impressions) as impressions,
            AVG(position) as avg_position,
            COUNT(DISTINCT query) as unique_queries,
            COUNT(DISTINCT page) as unique_pages
        FROM '{parquet_path}'
        WHERE date BETWEEN '{escape_sql_string(period1_start)}' AND '{escape_sql_string(period1_end)}'
    ),
    period2 AS (
        SELECT 
            SUM(clicks) as clicks,
            SUM(impressions) as impressions,
            AVG(position) as avg_position,
            COUNT(DISTINCT query) as unique_queries,
            COUNT(DISTINCT page) as unique_pages
        FROM '{parquet_path}'
        WHERE date BETWEEN '{escape_sql_string(period2_start)}' AND '{escape_sql_string(period2_end)}'
    )
    SELECT 
        '{period1_start}' as period1_start,
        '{period1_end}' as period1_end,
        '{period2_start}' as period2_start,
        '{period2_end}' as period2_end,
        p1.clicks as period1_clicks,
        p2.clicks as period2_clicks,
        p2.clicks - p1.clicks as clicks_change,
        CASE WHEN p1.clicks > 0 THEN ((p2.clicks - p1.clicks) / CAST(p1.clicks AS FLOAT) * 100) ELSE 0 END as clicks_change_pct,
        p1.impressions as period1_impressions,
        p2.impressions as period2_impressions,
        p2.impressions - p1.impressions as impressions_change,
        CASE WHEN p1.impressions > 0 THEN ((p2.impressions - p1.impressions) / CAST(p1.impressions AS FLOAT) * 100) ELSE 0 END as impressions_change_pct,
        p1.avg_position as period1_position,
        p2.avg_position as period2_position,
        p2.avg_position - p1.avg_position as position_change,
        p1.unique_queries as period1_queries,
        p2.unique_queries as period2_queries,
        p1.unique_pages as period1_pages,
        p2.unique_pages as period2_pages
    FROM period1 p1, period2 p2
    """

    result = conn.execute(query_sql).fetchdf()
    return result.to_dict("records")[0] if len(result) > 0 else {}


def main():
    from mcp.server.fastmcp import FastMCP

    real_mcp = FastMCP("gsc")

    # Re-register all tools with the real MCP instance
    real_mcp.tool()(query)
    real_mcp.tool()(show_page_queries)
    real_mcp.tool()(show_keyword_pages)
    real_mcp.tool()(search_keywords)
    real_mcp.tool()(best_pages)
    real_mcp.tool()(track_pages)
    real_mcp.tool()(pages_queries)
    real_mcp.tool()(compare_periods)

    real_mcp.run()


if __name__ == "__main__":
    main()
