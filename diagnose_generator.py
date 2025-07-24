#!/usr/bin/env python3
"""深入診斷 stream_site_data 生成器問題"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 確保 logs 目錄存在
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "diagnose_generator.log"

# 設置最詳細的日誌
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(str(log_file))],
)

# 設置所有相關模組的日誌級別為 DEBUG
logging.getLogger("src.services.gsc_client").setLevel(logging.DEBUG)
logging.getLogger("src.services.database").setLevel(logging.DEBUG)
logging.getLogger("googleapiclient.discovery").setLevel(logging.DEBUG)
logging.getLogger("googleapiclient.http").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def main():
    logger.info("=== 深入診斷 stream_site_data 生成器問題 ===")

    try:
        # 使用 ProcessSafeDatabase 來正確初始化
        from src.config import settings
        from src.services.gsc_client import GSCClient
        from src.services.process_safe_database import ProcessSafeDatabase

        # 初始化服務
        database_path = str(settings.paths.database_path)
        logger.info(f"使用資料庫路徑: {database_path}")
        db = ProcessSafeDatabase(database_path)  # ProcessSafeDatabase 本身就是 Database 的代理
        gsc_client = GSCClient(db)

        # 獲取站點
        sites = db.get_sites(active_only=True)
        site = next((s for s in sites if s["id"] == 4), None)
        if not site:
            logger.error("找不到 site_id = 4")
            return

        logger.info(f"使用站點: {site['name']} ({site['domain']})")

        # 測試不同的日期範圍
        test_dates = [
            (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            for days in [3, 5, 7, 14, 30]
        ]

        for test_date in test_dates:
            logger.info(f"\n=== 測試日期: {test_date} ===")

            try:
                # 調用 stream_site_data
                logger.info(f"調用 stream_site_data({site['domain']}, {test_date}, {test_date})")
                data_stream = gsc_client.stream_site_data(
                    site_url=site["domain"], start_date=test_date, end_date=test_date
                )

                # 嘗試獲取數據
                chunk_count = 0
                total_rows = 0

                for device, search_type, chunk in data_stream:
                    chunk_count += 1
                    total_rows += len(chunk)
                    logger.info(
                        f"收到 chunk #{chunk_count}: "
                        f"device={device}, search_type={search_type}, "
                        f"rows={len(chunk)}"
                    )

                    # 顯示前幾筆數據作為範例
                    if chunk and chunk_count == 1:
                        logger.info(f"範例數據: {chunk[0]}")

                    # 只處理前 5 個 chunks
                    if chunk_count >= 5:
                        logger.info("已收到足夠測試數據，停止")
                        break

                if chunk_count == 0:
                    logger.warning(f"日期 {test_date} 沒有收到任何數據")
                else:
                    logger.info(f"日期 {test_date} 總計: {chunk_count} chunks, {total_rows} rows")

            except Exception as e:
                logger.error(f"日期 {test_date} 發生錯誤: {type(e).__name__}: {str(e)}")
                import traceback

                traceback.print_exc()

        # 測試直接調用 API（繞過 stream 方法）
        logger.info("\n=== 測試直接 API 調用 ===")
        if hasattr(gsc_client, "service") and gsc_client.service:
            try:
                test_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                request_body = {
                    "startDate": test_date,
                    "endDate": test_date,
                    "dimensions": ["query", "page", "device"],
                    "searchType": "web",
                    "rowLimit": 10,
                    "startRow": 0,
                }

                logger.info(f"直接調用 searchanalytics.query with: {request_body}")

                response = (
                    gsc_client.service.searchanalytics()
                    .query(siteUrl=site["domain"], body=request_body)
                    .execute()
                )

                rows = response.get("rows", [])
                logger.info(f"API 直接返回 {len(rows)} 筆數據")
                if rows:
                    logger.info(f"第一筆數據: {rows[0]}")

            except Exception as e:
                logger.error(f"直接 API 調用失敗: {e}")
                import traceback

                traceback.print_exc()

    except Exception as e:
        logger.error(f"診斷過程出錯: {e}")
        import traceback

        traceback.print_exc()

    logger.info("\n=== 診斷結束 ===")
    logger.info(f"詳細日誌已保存到: {log_file}")


if __name__ == "__main__":
    main()
