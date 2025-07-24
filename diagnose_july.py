#!/usr/bin/env python3
"""
July 版本整合診斷工具 - 診斷 Windows 同步掛起問題
整合 diagnose_generator.py 和 diagnose_sync_hang.py 的功能
"""

import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# 確保 logs 目錄存在
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"diagnose_july_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Windows 編碼修復
if sys.platform == "win32":
    import io

    # 強制 stdout 和 stderr 使用 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 設置最詳細的日誌
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ],
)

# 設置所有相關模組的日誌級別
logging.getLogger("src.services.gsc_client").setLevel(logging.DEBUG)
logging.getLogger("src.services.database").setLevel(logging.DEBUG)
logging.getLogger("googleapiclient.discovery").setLevel(logging.INFO)
logging.getLogger("googleapiclient.http").setLevel(logging.INFO)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
logging.getLogger("google.auth").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


class DiagnosticTool:
    """整合診斷工具類"""

    def __init__(self):
        self.db = None
        self.gsc_client = None
        self.site = None
        self.results = {}

    def initialize(self):
        """初始化服務"""
        logger.info("=== July 診斷工具啟動 ===")
        logger.info(f"Python: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"PID: {os.getpid()}")

        try:
            # Windows 特定設置
            if sys.platform == "win32":
                import signal

                signal.signal(signal.SIGINT, signal.default_int_handler)
                logger.info("Windows 平台: 已設置信號處理器")

            # 導入必要模組
            logger.info("\n步驟 1: 導入模組...")
            from src.config import settings
            from src.services.gsc_client import GSCClient
            from src.services.process_safe_database import ProcessSafeDatabase

            # 初始化服務
            logger.info("\n步驟 2: 初始化資料庫...")
            database_path = str(settings.paths.database_path)
            logger.info(f"  資料庫路徑: {database_path}")

            self.db = ProcessSafeDatabase(database_path)
            logger.info("  [OK] 資料庫初始化成功")

            # 初始化 GSC Client
            logger.info("\n步驟 3: 初始化 GSC Client...")
            self.gsc_client = GSCClient(self.db)
            logger.info("  [OK] GSC Client 初始化成功")

            # 獲取測試站點
            logger.info("\n步驟 4: 獲取測試站點...")
            sites = self.db.get_sites(active_only=True)
            logger.info(f"  找到 {len(sites)} 個活躍站點")

            # 優先使用 site_id = 4，或第一個可用站點
            self.site = next((s for s in sites if s["id"] == 4), sites[0] if sites else None)
            if not self.site:
                raise Exception("沒有找到可用的站點")

            logger.info(f"  [OK] 使用站點: {self.site['name']} (ID: {self.site['id']})")

            return True

        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            traceback.print_exc()
            return False

    def test_gsc_auth(self):
        """測試 GSC 認證狀態"""
        logger.info("\n=== 測試 1: GSC 認證狀態 ===")
        try:
            logger.info(f"  is_authenticated: {self.gsc_client.is_authenticated()}")
            logger.info(f"  service 存在: {self.gsc_client.service is not None}")

            if self.gsc_client.credentials:
                logger.info(f"  credentials 有效: {self.gsc_client.credentials.valid}")
                logger.info(f"  credentials 過期: {self.gsc_client.credentials.expired}")
            else:
                logger.warning("  沒有 credentials")

            self.results["auth"] = self.gsc_client.is_authenticated()
            logger.info("  [OK] 認證測試完成")

        except Exception as e:
            logger.error(f"認證測試失敗: {e}")
            self.results["auth"] = False

    def test_simple_api_call(self):
        """測試簡單的 API 調用"""
        logger.info("\n=== 測試 2: 簡單 API 調用 (10筆資料) ===")

        try:
            test_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            logger.info(f"  測試日期: {test_date}")

            # 使用超時機制
            api_result = {"success": False, "data": None, "error": None}
            api_done = threading.Event()

            def make_api_call():
                try:
                    start_time = time.time()
                    logger.info("  開始 API 調用...")

                    if hasattr(self.gsc_client, "service") and self.gsc_client.service:
                        request_body = {
                            "startDate": test_date,
                            "endDate": test_date,
                            "dimensions": ["query", "page", "device"],
                            "searchType": "web",
                            "rowLimit": 10,
                            "startRow": 0,
                        }

                        response = (
                            self.gsc_client.service.searchanalytics()
                            .query(siteUrl=self.site["domain"], body=request_body)
                            .execute()
                        )

                        rows = response.get("rows", [])
                        elapsed = time.time() - start_time

                        logger.info("  [OK] API 調用成功")
                        logger.info(f"  返回 {len(rows)} 筆資料")
                        logger.info(f"  耗時: {elapsed:.2f} 秒")

                        if rows:
                            logger.info(f"  第一筆資料: {rows[0]}")

                        api_result["success"] = True
                        api_result["data"] = rows

                    else:
                        api_result["error"] = "GSC service 未初始化"

                except Exception as e:
                    api_result["error"] = str(e)
                    logger.error(f"  [ERROR] API 調用失敗: {e}")

                finally:
                    api_done.set()

            # 在線程中執行
            api_thread = threading.Thread(target=make_api_call)
            api_thread.start()

            # 等待完成或超時
            if not api_done.wait(timeout=30):
                logger.error("  [ERROR] API 調用超時 (30秒)")
                self.results["simple_api"] = False
            else:
                self.results["simple_api"] = api_result["success"]

        except Exception as e:
            logger.error(f"簡單 API 測試失敗: {e}")
            self.results["simple_api"] = False

    def test_stream_generator(self):
        """測試 stream_site_data 生成器"""
        logger.info("\n=== 測試 3: stream_site_data 生成器 ===")

        test_days = [1, 3, 7]  # 測試不同天數

        for days in test_days:
            try:
                test_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                logger.info(f"\n  測試日期: {test_date} ({days} 天前)")

                # 使用超時機制
                stream_done = threading.Event()
                stream_result = {"chunks": 0, "rows": 0, "error": None}

                def test_stream():
                    try:
                        start_time = time.time()

                        # 調用 stream_site_data
                        data_stream = self.gsc_client.stream_site_data(
                            site_url=self.site["domain"], start_date=test_date, end_date=test_date
                        )

                        logger.info("  生成器創建成功，開始迭代...")

                        # 迭代數據
                        for device, search_type, chunk in data_stream:
                            stream_result["chunks"] += 1
                            stream_result["rows"] += len(chunk)

                            elapsed = time.time() - start_time
                            logger.info(
                                f"  收到 chunk #{stream_result['chunks']}: "
                                f"device={device}, search_type={search_type}, "
                                f"rows={len(chunk)}, 累計耗時={elapsed:.2f}秒"
                            )

                            # Windows 保持活躍
                            if sys.platform == "win32" and stream_result["chunks"] % 10 == 0:
                                sys.stdout.write(".")
                                sys.stdout.flush()

                            # 測試前幾個 chunks
                            if stream_result["chunks"] >= 3:
                                logger.info("  已收到足夠測試數據")
                                break

                    except Exception as e:
                        stream_result["error"] = str(e)
                        logger.error(f"  [ERROR] Stream 錯誤: {e}")
                        traceback.print_exc()

                    finally:
                        stream_done.set()

                # 在線程中執行
                stream_thread = threading.Thread(target=test_stream)
                stream_thread.start()

                # 等待完成或超時
                timeout = 60 if days > 3 else 30
                if not stream_done.wait(timeout=timeout):
                    logger.error(f"  [ERROR] Stream 超時 ({timeout}秒)")
                    self.results[f"stream_day_{days}"] = False
                else:
                    if stream_result["error"]:
                        logger.error(f"  [ERROR] Stream 失敗: {stream_result['error']}")
                        self.results[f"stream_day_{days}"] = False
                    else:
                        logger.info(
                            f"  [OK] Stream 成功: "
                            f"{stream_result['chunks']} chunks, "
                            f"{stream_result['rows']} rows"
                        )
                        self.results[f"stream_day_{days}"] = True

            except Exception as e:
                logger.error(f"Stream 測試失敗 (day {days}): {e}")
                self.results[f"stream_day_{days}"] = False

    def test_database_operations(self):
        """測試資料庫操作"""
        logger.info("\n=== 測試 4: 資料庫操作 ===")

        try:
            # 測試讀取
            logger.info("  測試讀取操作...")
            sites_count = len(self.db.get_sites())
            logger.info(f"  [OK] 讀取成功: {sites_count} 個站點")

            # 測試寫入（使用測試表）
            logger.info("  測試寫入操作...")
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # 創建測試表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_table (
                        id INTEGER PRIMARY KEY,
                        test_time TEXT,
                        platform TEXT
                    )
                """)

                # 插入測試數據
                cursor.execute(
                    """
                    INSERT INTO test_table (test_time, platform)
                    VALUES (?, ?)
                """,
                    (datetime.now().isoformat(), sys.platform),
                )

                conn.commit()

                # 驗證寫入
                cursor.execute("SELECT COUNT(*) FROM test_table")
                count = cursor.fetchone()[0]
                logger.info(f"  [OK] 寫入成功: test_table 有 {count} 筆記錄")

                # 清理測試表
                cursor.execute("DROP TABLE IF EXISTS test_table")
                conn.commit()

            self.results["database"] = True

        except Exception as e:
            logger.error(f"資料庫測試失敗: {e}")
            self.results["database"] = False

    def test_batch_processing(self):
        """測試批量處理 (Windows 重點測試)"""
        logger.info("\n=== 測試 5: 批量處理測試 ===")

        try:
            test_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            logger.info(f"  測試日期: {test_date}")

            # Windows 特定: 測試不同批量大小
            if sys.platform == "win32":
                logger.info("  Windows 平台: 使用較小批量大小")
                batch_sizes = [10, 50, 100]
            else:
                batch_sizes = [100, 500, 1000]

            for batch_size in batch_sizes:
                logger.info(f"\n  測試批量大小: {batch_size}")

                try:
                    # 獲取測試數據
                    data_stream = self.gsc_client.stream_site_data(
                        site_url=self.site["domain"], start_date=test_date, end_date=test_date
                    )

                    batch_count = 0
                    total_rows = 0
                    start_time = time.time()

                    for device, search_type, chunk in data_stream:
                        batch_count += 1
                        rows_in_chunk = len(chunk)
                        total_rows += rows_in_chunk

                        # 模擬批量處理
                        if sys.platform == "win32":
                            # Windows: 更頻繁的進度更新
                            if batch_count % 5 == 0:
                                elapsed = time.time() - start_time
                                logger.info(
                                    f"    處理中... 批次={batch_count}, 總行數={total_rows}, 耗時={elapsed:.2f}秒"
                                )
                                sys.stdout.flush()

                        # 測試批量寫入
                        if rows_in_chunk > 0:
                            # 模擬數據庫批量寫入
                            time.sleep(0.01 * (rows_in_chunk / batch_size))

                        if batch_count >= 3:
                            break

                    elapsed = time.time() - start_time
                    logger.info(
                        f"  [OK] 批量大小 {batch_size}: 成功處理 {batch_count} 批次, {total_rows} 行, 耗時 {elapsed:.2f}秒"
                    )

                except Exception as e:
                    logger.error(f"  [ERROR] 批量大小 {batch_size} 失敗: {e}")

            self.results["batch_processing"] = True

        except Exception as e:
            logger.error(f"批量處理測試失敗: {e}")
            self.results["batch_processing"] = False

    def test_windows_specific(self):
        """Windows 特定測試"""
        if sys.platform != "win32":
            logger.info("\n=== 跳過 Windows 特定測試 (非 Windows 平台) ===")
            return

        logger.info("\n=== 測試 6: Windows 特定問題 ===")

        try:
            # 測試控制台編碼
            logger.info("  測試控制台編碼...")
            logger.info(f"  stdout 編碼: {sys.stdout.encoding}")
            logger.info(f"  stderr 編碼: {sys.stderr.encoding}")

            # 測試文件系統編碼
            logger.info("  測試文件系統...")
            test_path = Path(self.db._db_path).parent / "test_中文.tmp"
            try:
                test_path.write_text("測試中文", encoding="utf-8")
                test_path.read_text(encoding="utf-8")
                test_path.unlink()
                logger.info("  [OK] 文件系統支持 UTF-8")
            except Exception as e:
                logger.warning(f"  [WARNING] 文件系統編碼問題: {e}")

            # 測試網絡延遲
            logger.info("  測試網絡延遲...")
            import socket

            try:
                start = time.time()
                socket.gethostbyname("googleapis.com")
                latency = (time.time() - start) * 1000
                logger.info(f"  [OK] DNS 解析延遲: {latency:.2f}ms")

                if latency > 1000:
                    logger.warning("  [WARNING] 網絡延遲較高，可能影響同步")

            except Exception as e:
                logger.error(f"  [ERROR] 網絡測試失敗: {e}")

            # 測試進程優先級
            logger.info("  測試進程優先級...")
            try:
                import psutil

                process = psutil.Process(os.getpid())
                priority = process.nice()
                logger.info(f"  進程優先級: {priority}")

                # Windows 特定: 檢查內存使用
                memory_info = process.memory_info()
                logger.info(f"  內存使用: {memory_info.rss / 1024 / 1024:.2f} MB")

            except ImportError:
                logger.info("  psutil 未安裝，跳過進程測試")
            except Exception as e:
                logger.warning(f"  進程測試失敗: {e}")

            self.results["windows_specific"] = True

        except Exception as e:
            logger.error(f"Windows 特定測試失敗: {e}")
            self.results["windows_specific"] = False

    def test_sync_simulation(self):
        """模擬同步過程"""
        logger.info("\n=== 測試 7: 模擬同步過程 (1天資料) ===")

        try:
            from src.jobs.bulk_data_synchronizer import BulkDataSynchronizer
            from src.services.site_service import SiteService

            # 創建服務
            site_service = SiteService(self.db)
            synchronizer = BulkDataSynchronizer(
                db_service=self.db, gsc_client=self.gsc_client, site_service=site_service
            )

            # 測試同步
            sync_done = threading.Event()
            sync_result = {"success": False, "error": None}

            def run_sync():
                try:
                    logger.info("  開始同步測試...")

                    # Windows: 添加進度回調
                    if sys.platform == "win32":

                        def progress_callback(msg):
                            logger.info(f"  進度: {msg}")
                            sys.stdout.flush()

                        # 如果 synchronizer 支持回調
                        if hasattr(synchronizer, "set_progress_callback"):
                            synchronizer.set_progress_callback(progress_callback)

                    synchronizer.sync_sites(site_ids=[self.site["id"]], days=1, sync_mode="skip")
                    sync_result["success"] = True
                    logger.info("  [OK] 同步完成")

                except Exception as e:
                    sync_result["error"] = str(e)
                    logger.error(f"  [ERROR] 同步失敗: {e}")
                    traceback.print_exc()

                finally:
                    sync_done.set()

            # 在線程中執行
            sync_thread = threading.Thread(target=run_sync)
            sync_thread.start()

            # 等待完成或超時
            timeout = 180 if sys.platform == "win32" else 120
            if not sync_done.wait(timeout=timeout):
                logger.error(f"  [ERROR] 同步超時 ({timeout}秒)")
                logger.info("\n當前線程堆疊:")
                import faulthandler

                faulthandler.dump_traceback()
                self.results["sync"] = False

                # Windows: 嘗試分析掛起原因
                if sys.platform == "win32":
                    logger.info("\nWindows 掛起分析:")
                    logger.info("1. 可能是大量數據導致內存不足")
                    logger.info("2. 可能是網絡請求被防火牆阻擋")
                    logger.info("3. 可能是數據庫鎖定問題")

            else:
                self.results["sync"] = sync_result["success"]

        except Exception as e:
            logger.error(f"同步測試失敗: {e}")
            self.results["sync"] = False

    def print_summary(self):
        """打印診斷摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("診斷結果摘要")
        logger.info("=" * 60)

        for test, result in self.results.items():
            status = "[PASS]" if result else "[FAIL]"
            logger.info(f"  {test}: {status}")

        logger.info("=" * 60)

        # Windows 特定建議
        if sys.platform == "win32" and not all(self.results.values()):
            logger.info("\nWindows 特定建議:")
            logger.info("1. 嘗試以管理員身份運行")
            logger.info("2. 確保防火牆允許 Python 訪問網絡")
            logger.info("3. 嘗試使用較小的日期範圍 (如 1-3 天)")
            logger.info("4. 檢查 Windows Defender 是否阻擋了請求")

        logger.info(f"\n詳細日誌已保存到: {log_file}")


def main():
    """主函數"""
    tool = DiagnosticTool()

    try:
        # 初始化
        if not tool.initialize():
            logger.error("初始化失敗，退出診斷")
            return

        # 執行測試
        tool.test_gsc_auth()
        tool.test_simple_api_call()
        tool.test_stream_generator()
        tool.test_database_operations()
        tool.test_batch_processing()
        tool.test_windows_specific()
        tool.test_sync_simulation()

        # 打印摘要
        tool.print_summary()

    except KeyboardInterrupt:
        logger.info("\n用戶中斷診斷")
    except Exception as e:
        logger.error(f"診斷過程發生錯誤: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
