#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
專責處理數據分析和報告生成的服務。
此服務依賴於 Database 服務來獲取數據。
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from .database import Database

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, db: Database):
        """
        初始化分析服務。
        :param db: Database 的一個實例，用於數據庫交互。
        """
        self.db = db

    def _get_date_range_from_days(self, site_id: int, days: int) -> Optional[tuple[str, str]]:
        """從數據庫獲取指定站點的最新日期並計算日期範圍"""
        try:
            latest_date = self.db.get_latest_date_from_table("gsc_performance_data", site_id)
            if not latest_date:
                logger.warning(
                    f"在 gsc_performance_data 中找不到站點 ID {site_id} 的數據，無法確定日期範圍。"
                )
                return None
            end_date = latest_date
            start_date = end_date - datetime.timedelta(days=days - 1)
            return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"獲取日期範圍時出錯: {e}", exc_info=True)
            return None

    def get_top_keywords(
        self, site_id: int, days: int, metric: str = "clicks", limit: int = 20
    ) -> List[Dict[str, Any]]:
        """獲取指定時間範圍內表現最佳的關鍵字"""
        if metric not in ["clicks", "impressions"]:
            raise ValueError("Metric must be 'clicks' or 'impressions'")

        date_range = self._get_date_range_from_days(site_id, days)
        if not date_range:
            return []
        start_date, end_date = date_range

        query = f"""
            SELECT query, page, SUM(clicks) as total_clicks,
                   SUM(impressions) as total_impressions, AVG(position) as avg_position
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
            GROUP BY query, page
            ORDER BY total_{metric} DESC
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            return [
                dict(row)
                for row in conn.execute(query, (site_id, start_date, end_date, limit)).fetchall()
            ]

    def get_site_performance_summary(self, site_id: int, days: int) -> Dict[str, Any]:
        """獲取站點在指定時間範圍內的整體表現摘要"""
        date_range = self._get_date_range_from_days(site_id, days)
        if not date_range:
            return {}
        start_date, end_date = date_range

        query = """
            SELECT
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
        """
        with self.db.get_connection() as conn:
            summary = conn.execute(query, (site_id, start_date, end_date)).fetchone()
            return dict(summary) if summary else {}

    def get_daily_performance_summary(self, site_id: int, days: int) -> List[Dict[str, Any]]:
        """獲取指定站點在時間範圍內的每日表現摘要"""
        date_range = self._get_date_range_from_days(site_id, days)
        if not date_range:
            return []
        start_date, end_date = date_range

        query = """
            SELECT
                date,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        """
        with self.db.get_connection() as conn:
            return [
                dict(row) for row in conn.execute(query, (site_id, start_date, end_date)).fetchall()
            ]

    def get_top_pages(
        self, site_id: int, days: int, metric: str = "clicks", limit: int = 20
    ) -> List[Dict[str, Any]]:
        """獲取指定時間範圍內表現最佳的頁面"""
        if metric not in ["clicks", "impressions"]:
            raise ValueError("Metric must be 'clicks' or 'impressions'")

        date_range = self._get_date_range_from_days(site_id, days)
        if not date_range:
            return []
        start_date, end_date = date_range

        query = f"""
            SELECT
                page,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
            GROUP BY page
            ORDER BY total_{metric} DESC
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            return [
                dict(row)
                for row in conn.execute(query, (site_id, start_date, end_date, limit)).fetchall()
            ]

    def get_overall_summary(self, site_id: int, days: int) -> Dict[str, Any]:
        """獲取指定站點在時間範圍內的整體數據摘要"""
        date_range = self._get_date_range_from_days(site_id, days)
        if not date_range:
            return {}
        start_date, end_date = date_range

        query = """
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT query) as total_keywords,
                COUNT(DISTINCT page) as total_pages,
                MIN(date) as earliest_date,
                MAX(date) as latest_date
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
        """
        with self.db.get_connection() as conn:
            summary = conn.execute(query, (site_id, start_date, end_date)).fetchone()
            return dict(summary) if summary else {}

    def get_keyword_trend(
        self, site_id: int, query_text: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        獲取單個關鍵字在一段時間內的表現趨勢。
        已重構為使用 gsc_performance_data 表。
        """
        query = """
            SELECT date, position, clicks, impressions, ctr
            FROM gsc_performance_data
            WHERE site_id = ? AND query = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """
        with self.db.get_connection() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    query, (site_id, query_text, start_date, end_date)
                ).fetchall()
            ]

    def get_performance_data_for_visualization(
        self,
        site_id: int,
        start_date: str,
        end_date: str,
        group_by: str = "query",
        filter_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        為交互式可視化獲取性能數據。
        此方法取代了舊的 get_rankings 和 get_page_data。
        """
        if group_by not in ["query", "page"]:
            raise ValueError("group_by 必須是 'query' 或 'page'")

        base_query = f"""
            SELECT
                date,
                {group_by},
                clicks,
                impressions,
                ctr,
                position
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
        """
        params: List[Any] = [site_id, start_date, end_date]

        if filter_term:
            base_query += f" AND {group_by} = ?"
            params.append(filter_term)

        base_query += " ORDER BY date"

        with self.db.get_connection() as conn:
            return [dict(row) for row in conn.execute(base_query, tuple(params)).fetchall()]

    def compare_performance_periods(
        self,
        site_id: int,
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        group_by: str = "query",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        比較兩個不同時間段的性能數據。

        :param site_id: 要分析的站點 ID。
        :param period1_start: 第一個時間段的開始日期 (YYYY-MM-DD)。
        :param period1_end: 第一個時間段的結束日期 (YYYY-MM-DD)。
        :param period2_start: 第二個時間段的開始日期 (YYYY-MM-DD)。
        :param period2_end: 第二個時間段的結束日期 (YYYY-MM-DD)。
        :param group_by: 分組依據，可以是 'query' 或 'page'。
        :param limit: 返回結果的數量，按點擊變化量降序排列。
        :return: 一個包含比較數據的字典列表。
        """
        if group_by not in ["query", "page"]:
            raise ValueError("group_by 必須是 'query' 或 'page'")

        query = f"""
            WITH
            period1_data AS (
                SELECT {group_by} AS item, SUM(clicks) AS p1_clicks,
                       SUM(impressions) AS p1_impressions, AVG(position) AS p1_position,
                       AVG(ctr) AS p1_ctr
                FROM gsc_performance_data WHERE site_id = ? AND date BETWEEN ? AND ? GROUP BY {group_by}
            ),
            period2_data AS (
                SELECT {group_by} AS item, SUM(clicks) AS p2_clicks,
                       SUM(impressions) AS p2_impressions, AVG(position) AS p2_position,
                       AVG(ctr) AS p2_ctr
                FROM gsc_performance_data WHERE site_id = ? AND date BETWEEN ? AND ? GROUP BY {group_by}
            )
            SELECT
                COALESCE(p1.item, p2.item) AS item,
                COALESCE(p1.p1_clicks, 0) AS period1_clicks,
                COALESCE(p2.p2_clicks, 0) AS period2_clicks,
                (COALESCE(p2.p2_clicks, 0) - COALESCE(p1.p1_clicks, 0)) AS clicks_change,
                COALESCE(p1.p1_impressions, 0) AS period1_impressions,
                COALESCE(p2.p2_impressions, 0) AS period2_impressions,
                (COALESCE(p2.p2_impressions, 0) - COALESCE(p1.p1_impressions, 0)) AS impressions_change,
                COALESCE(p1.p1_position, 0) AS period1_position,
                COALESCE(p2.p2_position, 0) AS period2_position,
                (COALESCE(p2.p2_position, 999) - COALESCE(p1.p1_position, 999)) AS position_change,
                COALESCE(p1.p1_ctr, 0) AS period1_ctr,
                COALESCE(p2.p2_ctr, 0) AS period2_ctr,
                (COALESCE(p2.p2_ctr, 0) - COALESCE(p1.p1_ctr, 0)) AS ctr_change
            FROM period1_data p1
            FULL OUTER JOIN period2_data p2 ON p1.item = p2.item
            ORDER BY clicks_change DESC
            LIMIT ?
        """
        params = (
            site_id,
            period1_start,
            period1_end,
            site_id,
            period2_start,
            period2_end,
            limit,
        )
        with self.db.get_connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_competitor_analysis(
        self, site_id: int, start_date: str, end_date: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """獲取競爭對手分析數據"""
        query = """
            SELECT query, COUNT(DISTINCT page) as competitor_count
            FROM gsc_performance_data
            WHERE site_id = ? AND date BETWEEN ? AND ?
            GROUP BY query
            HAVING competitor_count > 1
            ORDER BY competitor_count DESC
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            return [
                dict(row)
                for row in conn.execute(query, (site_id, start_date, end_date, limit)).fetchall()
            ]

    def get_seasonal_trends(
        self, site_id: int, year: int, metric: str = "clicks"
    ) -> List[Dict[str, Any]]:
        """分析指定年份的季節性趨勢（按月分組）"""
        if metric not in ["clicks", "impressions"]:
            raise ValueError("Metric must be 'clicks' or 'impressions'")

        query = f"""
            SELECT strftime('%m', date) as month, SUM({metric}) as total_metric
            FROM gsc_performance_data
            WHERE site_id = ? AND strftime('%Y', date) = ?
            GROUP BY month
            ORDER BY month
        """
        with self.db.get_connection() as conn:
            return [dict(row) for row in conn.execute(query, (site_id, str(year))).fetchall()]

    def get_keyword_growth_analysis(
        self,
        site_id: int,
        start_date: str,
        end_date: str,
        growth_threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        分析關鍵字的增長情況
        此實現較為複雜，此處僅為一個簡化的框架
        """
        logger.warning("Keyword growth analysis is a simplified implementation.")
        # 在真實場景中，需要比較兩個時間段的數據
        return []
