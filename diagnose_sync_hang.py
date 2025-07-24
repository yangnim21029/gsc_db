#!/usr/bin/env python3
"""診斷同步卡住問題 - 詳細版"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 確保 logs 目錄存在
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "diagnose_sync.log"

# 設置最詳細的日誌
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(str(log_file))],
)

# 減少 Google API 的日誌噪音
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
logging.getLogger("google.auth").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


def main():
    logger.info("=== 開始診斷同步卡住問題 ===")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"PID: {os.getpid()}")

    try:
        # 1. 導入必要模組
        logger.info("步驟 1: 導入模組...")
        from src.containers import Container

        logger.info("✓ 模組導入成功")

        # 2. 初始化容器
        logger.info("步驟 2: 初始化容器...")
        container = Container()
        logger.info("✓ 容器初始化成功")

        # 3. 獲取服務
        logger.info("步驟 3: 獲取服務...")
        db = container.database()
        gsc_client = container.gsc_client()
        logger.info("✓ 服務獲取成功")

        # 4. 測試資料庫
        logger.info("步驟 4: 測試資料庫連接...")
        sites = db.get_sites(active_only=True)
        site = next((s for s in sites if s["id"] == 4), None)
        if not site:
            logger.error("找不到 site_id = 4")
            return
        logger.info(f"✓ 找到站點: {site['name']}")

        # 5. 測試 GSC Client 內部狀態
        logger.info("步驟 5: 檢查 GSC Client 狀態...")
        logger.info(f"  - is_authenticated: {gsc_client.is_authenticated()}")
        logger.info(f"  - service is None: {gsc_client.service is None}")
        logger.info(
            f"  - credentials valid: {gsc_client.credentials.valid if gsc_client.credentials else 'No credentials'}"
        )

        # 6. 直接測試 stream_site_data
        test_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        logger.info(f"步驟 6: 測試 stream_site_data (日期: {test_date})...")

        try:
            logger.info(f"呼叫 stream_site_data({site['domain']}, {test_date}, {test_date})...")

            # 設置計時器
            start_time = time.time()
            timeout = 30  # 30秒超時

            # 呼叫 stream_site_data
            data_stream = gsc_client.stream_site_data(
                site_url=site["domain"], start_date=test_date, end_date=test_date
            )

            logger.info(f"stream_site_data 返回了生成器對象: {data_stream}")

            # 嘗試獲取第一個 chunk
            logger.info("嘗試獲取第一個數據 chunk...")

            chunk_count = 0
            for device, search_type, chunk in data_stream:
                elapsed = time.time() - start_time
                logger.info(
                    f"✓ 收到 chunk #{chunk_count + 1}: device={device}, search_type={search_type}, 數據筆數={len(chunk)}, 耗時={elapsed:.2f}秒"
                )
                chunk_count += 1

                # 只測試前幾個 chunk
                if chunk_count >= 3:
                    logger.info("已收到足夠的測試數據，停止")
                    break

                if elapsed > timeout:
                    logger.warning(f"超時警告：已經過 {elapsed:.2f} 秒")
                    break

            if chunk_count == 0:
                logger.error("沒有收到任何數據 chunk！")
            else:
                logger.info(f"✓ 成功收到 {chunk_count} 個數據 chunk")

        except Exception as e:
            logger.error(f"stream_site_data 失敗: {type(e).__name__}: {str(e)}")
            import traceback

            traceback.print_exc()

        # 7. 測試原始 API 調用
        logger.info("步驟 7: 測試是否有 get_search_analytics 方法...")
        if hasattr(gsc_client, "get_search_analytics"):
            try:
                data = gsc_client.get_search_analytics(
                    site["domain"], test_date, test_date, row_limit=10
                )
                logger.info(f"✓ API 調用成功，返回 {len(data) if data else 0} 筆數據")
            except Exception as e:
                logger.error(f"API 調用失敗: {e}")
        else:
            logger.warning("GSCClient 沒有 get_search_analytics 方法，跳過此測試")

    except Exception as e:
        logger.error(f"診斷過程出錯: {e}")
        import traceback

        traceback.print_exc()

    logger.info("=== 診斷結束 ===")
    logger.info(f"詳細日誌已保存到: {log_file}")


if __name__ == "__main__":
    main()
