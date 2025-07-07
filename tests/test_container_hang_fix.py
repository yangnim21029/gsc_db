#!/usr/bin/env python3
"""
測試容器掛起問題修復

這個測試文件專門驗證之前遇到的容器掛起問題已經被解決，
並確保所有相關功能都能正常工作。
"""

import signal
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from unittest.mock import patch

import pytest

from src.containers import Container
from src.services.gsc_client import GSCClient


class TestContainerHangFix:
    """測試容器掛起問題修復"""

    def test_container_creation_with_timeout(self):
        """測試容器創建不會掛起（帶超時保護）"""

        def create_container():
            container = Container()
            return container

        # 使用線程池執行器來設置超時
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(create_container)
            try:
                # 5秒超時，如果掛起會拋出異常
                container = future.result(timeout=5.0)
                assert container is not None
                print("✅ 容器創建成功，沒有掛起")
            except FutureTimeoutError:
                pytest.fail("容器創建超時，可能存在掛起問題")

    def test_gsc_client_creation_with_timeout(self):
        """測試 GSC 客戶端創建不會掛起"""

        def create_gsc_client():
            container = Container()
            gsc_client = container.gsc_client()
            return gsc_client

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(create_gsc_client)
            try:
                gsc_client = future.result(timeout=10.0)  # GSC 客戶端可能需要更多時間（認證）
                assert gsc_client is not None
                assert isinstance(gsc_client, GSCClient)
                print("✅ GSC 客戶端創建成功，沒有掛起")
            except FutureTimeoutError:
                pytest.fail("GSC 客戶端創建超時，可能存在掛起問題")

    def test_site_service_get_all_sites_with_timeout(self):
        """測試 site service 的 get_all_sites_with_status 方法不會掛起"""

        def get_sites():
            container = Container()
            site_service = container.site_service()
            sites = site_service.get_all_sites_with_status()
            return sites

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_sites)
            try:
                sites = future.result(timeout=15.0)  # 包含遠程 API 調用，需要更多時間
                assert isinstance(sites, list)
                print(f"✅ 獲取站點列表成功，找到 {len(sites)} 個站點")

                # 驗證站點數據結構
                for site in sites[:3]:  # 檢查前3個站點
                    assert "id" in site or site.get("id") == "N/A"
                    assert "name" in site
                    assert "domain" in site
                    assert "source" in site
                    assert site["source"] in ["local", "remote"]

            except FutureTimeoutError:
                pytest.fail("獲取站點列表超時，可能存在掛起問題")

    def test_database_lock_type_is_rlock(self):
        """測試數據庫使用的是 RLock 而不是普通 Lock"""
        container = Container()
        db = container.database()

        # 檢查鎖的類型
        lock_type_name = type(db._lock).__name__
        assert lock_type_name == "RLock", f"期望 RLock，但得到 {lock_type_name}"
        print("✅ 數據庫使用 RLock，支持可重入鎖定")

    def test_database_row_factory_is_set(self):
        """測試數據庫連接設置了正確的 row_factory"""
        container = Container()
        db = container.database()

        # 檢查 row_factory 是否設置
        assert db._connection.row_factory == sqlite3.Row, (
            "數據庫連接應該設置 row_factory 為 sqlite3.Row"
        )
        print("✅ 數據庫連接設置了正確的 row_factory")

    def test_concurrent_database_access(self):
        """測試並發數據庫訪問不會死鎖"""
        container = Container()
        db = container.database()

        results = []
        errors = []

        def worker(worker_id):
            try:
                # 執行一些數據庫操作
                sites = db.get_sites()
                results.append(f"Worker {worker_id}: {len(sites)} sites")
                time.sleep(0.1)  # 模擬一些處理時間
                sites_again = db.get_sites()
                results.append(f"Worker {worker_id}: {len(sites_again)} sites (second call)")
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")

        # 創建多個線程並發訪問數據庫
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有線程完成，設置超時
        for thread in threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                pytest.fail(f"線程 {thread.name} 超時，可能存在死鎖")

        # 檢查結果
        assert len(errors) == 0, f"並發訪問出現錯誤: {errors}"
        assert len(results) == 10, f"期望 10 個結果，但得到 {len(results)} 個"
        print("✅ 並發數據庫訪問成功，沒有死鎖")

    def test_reentrant_lock_behavior(self):
        """測試可重入鎖的行為"""
        container = Container()
        db = container.database()

        def nested_lock_operation():
            with db._lock:
                # 第一層鎖定
                sites = db.get_sites()
                with db._lock:
                    # 第二層鎖定（可重入）
                    sites_again = db.get_sites()
                    return len(sites), len(sites_again)

        # 這個操作應該成功，不會死鎖
        try:
            count1, count2 = nested_lock_operation()
            assert count1 == count2
            print("✅ 可重入鎖正常工作，支持嵌套鎖定")
        except Exception as e:
            pytest.fail(f"可重入鎖測試失敗: {str(e)}")

    def test_container_services_integration(self):
        """測試容器中各服務的集成"""
        container = Container()

        # 測試所有主要服務都能正常創建
        services = {}
        service_names = [
            "database",
            "gsc_client",
            "site_service",
            "analysis_service",
            "bulk_data_synchronizer",
            "hourly_data_service",
            "hourly_performance_analyzer",
        ]

        for service_name in service_names:
            try:
                service = getattr(container, service_name)()
                services[service_name] = service
                print(f"✅ {service_name} 服務創建成功")
            except Exception as e:
                pytest.fail(f"創建 {service_name} 服務失敗: {str(e)}")

        # 驗證服務之間的依賴關係
        assert services["site_service"]._db is services["database"]
        assert services["site_service"]._gsc_client is services["gsc_client"]
        print("✅ 服務依賴關係正確")

    @patch("src.services.gsc_client.GSCClient._load_credentials")
    def test_gsc_client_without_network(self, mock_load_creds):
        """測試在沒有網絡連接時 GSC 客戶端的行為"""
        # 模擬沒有憑證的情況
        mock_load_creds.return_value = False

        def create_gsc_client_no_network():
            container = Container()
            gsc_client = container.gsc_client()
            return gsc_client

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(create_gsc_client_no_network)
            try:
                gsc_client = future.result(timeout=5.0)
                assert gsc_client is not None
                assert not gsc_client.is_authenticated()
                print("✅ GSC 客戶端在無網絡情況下正常創建")
            except FutureTimeoutError:
                pytest.fail("GSC 客戶端在無網絡情況下創建超時")

    def test_signal_handling_during_operations(self):
        """測試操作過程中的信號處理（模擬中斷情況）"""
        container = Container()
        site_service = container.site_service()

        interrupted = False

        def signal_handler(signum, frame):
            nonlocal interrupted
            interrupted = True
            print("收到中斷信號")

        # 設置信號處理器
        old_handler = signal.signal(signal.SIGALRM, signal_handler)

        try:
            # 設置 1 秒後發送信號
            signal.alarm(1)

            # 執行一個可能較慢的操作
            start_time = time.time()
            try:
                sites = site_service.get_all_sites_with_status()
                operation_time = time.time() - start_time
                print(f"操作完成，耗時 {operation_time:.2f} 秒，找到 {len(sites)} 個站點")
            except Exception as e:
                # 如果操作被中斷，這是正常的
                print(f"操作被中斷或出錯: {str(e)}")

            # 取消信號
            signal.alarm(0)

            # 驗證系統仍然響應
            db_sites = site_service.get_all_sites()
            assert isinstance(db_sites, list)
            print("✅ 中斷後系統仍然響應正常")

        finally:
            # 恢復原來的信號處理器
            signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)


if __name__ == "__main__":
    # 如果直接運行這個文件，執行所有測試
    test_instance = TestContainerHangFix()

    print("🧪 開始執行容器掛起問題修復測試...")
    print("=" * 60)

    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    for method_name in test_methods:
        print(f"\n📋 執行測試: {method_name}")
        try:
            method = getattr(test_instance, method_name)
            method()
            print(f"✅ {method_name} - 通過")
        except Exception as e:
            print(f"❌ {method_name} - 失敗: {str(e)}")

    print("\n" + "=" * 60)
    print("🎉 容器掛起問題修復測試完成！")
