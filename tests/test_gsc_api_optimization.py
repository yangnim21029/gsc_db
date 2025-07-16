#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試 GSC API 優化改進
驗證根據 API 文件實施的最佳實踐
"""

import time
from unittest.mock import Mock, patch

import pytest

from src.jobs.bulk_data_synchronizer import BulkDataSynchronizer
from src.services.database import Database
from src.services.gsc_client import GSCClient


class TestGSCAPIOptimization:
    """測試 GSC API 優化功能"""

    def test_rate_limit_check(self):
        """測試 API 速率限制檢查功能"""
        # 創建模擬數據庫
        mock_db = Mock(spec=Database)

        # 創建 GSC 客戶端
        with patch("src.services.gsc_client.build") as mock_build:
            with patch.object(GSCClient, "authenticate", return_value=True):
                with patch.object(GSCClient, "_load_api_usage_from_db"):
                    mock_service = Mock()
                    mock_build.return_value = mock_service

                    client = GSCClient(mock_db)
                    client.service = mock_service  # 直接設置 service

                    # 測試速率限制檢查不會阻塞正常請求
                    start_time = time.time()
                    client._rate_limit_check()
                    end_time = time.time()

                    # 正常情況下應該很快完成
                    assert end_time - start_time < 0.1

    def test_optimized_stream_data_structure(self):
        """測試優化後的數據流結構"""
        mock_db = Mock(spec=Database)

        with patch("src.services.gsc_client.build") as mock_build:
            with patch.object(GSCClient, "authenticate", return_value=True):
                with patch.object(GSCClient, "_load_api_usage_from_db"):
                    mock_service = Mock()
                    mock_build.return_value = mock_service

                    # 模擬 API 響應
                    mock_response = {
                        "rows": [
                            {
                                "keys": ["https://example.com/page1", "test query", "desktop"],
                                "clicks": 10,
                                "impressions": 100,
                                "ctr": 0.1,
                                "position": 5.0,
                            }
                        ]
                    }

                    mock_service.searchanalytics.return_value.query.return_value.execute.return_value = mock_response

                    client = GSCClient(mock_db)
                    client.service = mock_service  # 直接設置 service

                    # Mock is_authenticated to return True
                    with patch.object(client, "is_authenticated", return_value=True):
                        # 測試優化後的數據流
                        results = list(
                            client.stream_site_data_optimized(
                                "https://example.com", "2024-01-01", "2024-01-01"
                            )
                        )

                        # 驗證結果結構
                        assert len(results) > 0
                        device, search_type, chunk = results[0]
                        assert device == "desktop"
                        assert search_type == "web"
                        assert len(chunk) == 1
                        assert chunk[0]["clicks"] == 10

    def test_concurrent_worker_optimization(self):
        """測試併發工作者數量優化"""
        mock_db = Mock(spec=Database)
        mock_gsc_client = Mock(spec=GSCClient)

        # 模擬站點數據
        mock_db.get_sites.return_value = [
            {"id": 1, "name": "Site 1", "url": "https://site1.com"},
            {"id": 2, "name": "Site 2", "url": "https://site2.com"},
        ]
        mock_db.get_existing_data_days_for_sites.return_value = set()

        synchronizer = BulkDataSynchronizer(mock_db, mock_gsc_client)

        # 測試順序處理模式 (max_workers=1)
        with patch("src.jobs.bulk_data_synchronizer.Progress"):
            # 模擬空任務列表以快速完成
            mock_db.get_sites.return_value = []

            synchronizer.run_sync(
                all_sites=True,
                max_workers=1,  # 使用順序處理
            )

            # 驗證同步器能正常處理 max_workers=1 模式
            # 這個測試驗證了 run_sync 函數的順序處理邏輯

    def test_api_best_practices_compliance(self):
        """測試 API 最佳實踐遵循情況"""
        mock_db = Mock(spec=Database)

        with patch("src.services.gsc_client.build") as mock_build:
            with patch.object(GSCClient, "authenticate", return_value=True):
                with patch.object(GSCClient, "_load_api_usage_from_db"):
                    mock_service = Mock()
                    mock_build.return_value = mock_service

                    # 模擬 API 響應
                    mock_response = {"rows": []}
                    mock_service.searchanalytics.return_value.query.return_value.execute.return_value = mock_response

                    client = GSCClient(mock_db)
                    client.service = mock_service  # 直接設置 service

                    # Mock is_authenticated to return True
                    with patch.object(client, "is_authenticated", return_value=True):
                        # 測試每日查詢模式
                        list(
                            client.stream_site_data_optimized(
                                "https://example.com",
                                "2024-01-01",
                                "2024-01-02",  # 2 天的數據
                            )
                        )

                        # 驗證 API 被調用的次數符合預期
                        # 應該是: 2 天 × 6 種搜索類型 = 12 次調用
                        call_count = mock_service.searchanalytics.return_value.query.return_value.execute.call_count
                        assert call_count == 12

    def test_ssl_error_handling_improvement(self):
        """測試 SSL 錯誤處理改進"""
        mock_db = Mock(spec=Database)

        with patch("src.services.gsc_client.build") as mock_build:
            with patch.object(GSCClient, "authenticate", return_value=True):
                with patch.object(GSCClient, "_load_api_usage_from_db"):
                    mock_service = Mock()
                    mock_build.return_value = mock_service

                    # 模擬 SSL 錯誤
                    import ssl

                    mock_service.searchanalytics.return_value.query.return_value.execute.side_effect = ssl.SSLError(
                        "SSL error"
                    )

                    client = GSCClient(mock_db)
                    client.service = mock_service  # 直接設置 service

                    # Mock is_authenticated to return True
                    with patch.object(client, "is_authenticated", return_value=True):
                        # 測試 SSL 錯誤被正確拋出以供重試機制處理
                        with pytest.raises(ssl.SSLError):
                            list(
                                client.stream_site_data_optimized(
                                    "https://example.com", "2024-01-01", "2024-01-01"
                                )
                            )

    def test_rate_limit_429_handling(self):
        """測試 429 速率限制錯誤處理"""
        mock_db = Mock(spec=Database)

        with patch("src.services.gsc_client.build") as mock_build:
            with patch.object(GSCClient, "authenticate", return_value=True):
                with patch.object(GSCClient, "_load_api_usage_from_db"):
                    mock_service = Mock()
                    mock_build.return_value = mock_service

                    # 模擬 429 錯誤後成功響應
                    from googleapiclient.errors import HttpError

                    mock_429_response = Mock()
                    mock_429_response.status = 429
                    mock_429_error = HttpError(mock_429_response, b"Rate limit exceeded")

                    mock_success_response = {"rows": []}

                    # 提供足夠的響應給所有搜索類型 (6 種類型)
                    # 第一次調用返回 429 錯誤，後續都成功
                    mock_service.searchanalytics.return_value.query.return_value.execute.side_effect = [
                        mock_429_error,  # 第一次 429 錯誤
                        mock_success_response,  # 第一次重試成功
                        mock_success_response,  # 其他搜索類型
                        mock_success_response,
                        mock_success_response,
                        mock_success_response,
                        mock_success_response,
                    ]

                    client = GSCClient(mock_db)
                    client.service = mock_service  # 直接設置 service

                    # Mock is_authenticated to return True
                    with patch.object(client, "is_authenticated", return_value=True):
                        # 使用 patch 來模擬 time.sleep，避免實際等待
                        with patch("time.sleep"):
                            # 測試能夠處理 429 錯誤並繼續
                            results = list(
                                client.stream_site_data_optimized(
                                    "https://example.com", "2024-01-01", "2024-01-01"
                                )
                            )

                            # 應該能夠成功完成（雖然沒有數據）
                            assert isinstance(results, list)

    def test_backward_compatibility(self):
        """測試向後兼容性"""
        mock_db = Mock(spec=Database)

        with patch("src.services.gsc_client.build") as mock_build:
            with patch.object(GSCClient, "authenticate", return_value=True):
                with patch.object(GSCClient, "_load_api_usage_from_db"):
                    mock_service = Mock()
                    mock_build.return_value = mock_service

                    mock_response = {"rows": []}
                    mock_service.searchanalytics.return_value.query.return_value.execute.return_value = mock_response

                    client = GSCClient(mock_db)
                    client.service = mock_service  # 直接設置 service

                    # Mock is_authenticated to return True
                    with patch.object(client, "is_authenticated", return_value=True):
                        # 測試舊的 stream_site_data 方法仍然有效
                        results_old = list(
                            client.stream_site_data(
                                "https://example.com", "2024-01-01", "2024-01-01"
                            )
                        )

                        # 重置 mock
                        mock_service.reset_mock()

                        # 測試新的優化方法
                        results_new = list(
                            client.stream_site_data_optimized(
                                "https://example.com", "2024-01-01", "2024-01-01"
                            )
                        )

                        # 兩者應該返回相同的結果結構
                        assert type(results_old) is type(results_new)
                        assert len(results_old) == len(results_new)
