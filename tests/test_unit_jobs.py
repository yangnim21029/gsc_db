#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
對 jobs 模組的單元測試。

這些測試在隔離的環境中運行，不依賴真實的 API 或資料庫。
"""

from unittest.mock import MagicMock

from src.jobs.bulk_data_synchronizer import _sync_single_day
from src.services.database import SyncMode


def test_sync_single_day_in_skip_mode():
    """
    測試 _sync_single_day 在 SKIP 模式下的行為。
    - 驗證它正確地呼叫了 API。
    - 驗證它沒有刪除舊數據。
    - 驗證它正確地保存了數據塊。
    - 驗證它返回了正確的統計數據。
    """
    # 1. Arrange: 設定模擬物件和測試數據
    mock_db = MagicMock()
    mock_client = MagicMock()

    # 模擬 GSC 客戶端返回一個包含兩個數據塊的數據流
    mock_client.stream_site_data.return_value = [
        ("desktop", "web", [{"page": "/page1", "query": "q1"}]),
        ("mobile", "web", [{"page": "/page2", "query": "q2"}]),
    ]

    # 模擬資料庫在保存每個數據塊時返回的統計數據
    mock_db.save_data_chunk.return_value = {"inserted": 10, "updated": 0, "skipped": 0}

    site_info = {"id": 1, "name": "Test Site", "domain": "example.com"}
    date_str = "2024-01-01"

    # 2. Act: 呼叫被測試的函數
    result_stats = _sync_single_day(
        db=mock_db,
        client=mock_client,
        site=site_info,
        date=date_str,
        sync_mode=SyncMode.SKIP,
    )

    # 3. Assert: 驗證行為和結果
    # 驗證 API 是否被正確呼叫
    mock_client.stream_site_data.assert_called_once_with(
        site_url="example.com", start_date="2024-01-01", end_date="2024-01-01"
    )

    # 驗證在 SKIP 模式下，刪除函數沒有被呼叫
    mock_db.delete_performance_data_for_day.assert_not_called()

    # 驗證保存函數被呼叫了兩次（對應數據流中的兩個數據塊）
    assert mock_db.save_data_chunk.call_count == 2

    # 驗證返回的統計數據是兩次保存結果的總和
    assert result_stats == {"inserted": 20, "updated": 0, "skipped": 0}


def test_sync_single_day_in_overwrite_mode():
    """
    測試 _sync_single_day 在 OVERWRITE 模式下的行為。
    - 驗證它在同步前呼叫了刪除舊數據的方法。
    """
    # 1. Arrange
    mock_db = MagicMock()
    mock_client = MagicMock()
    # 模擬一個空的數據流， क्योंकि हम केवल डिलीट ऑपरेशन में रुचि रखते हैं
    mock_client.stream_site_data.return_value = []

    site_info = {"id": 1, "name": "Test Site", "domain": "example.com"}
    date_str = "2024-01-01"

    # 2. Act
    _sync_single_day(
        db=mock_db,
        client=mock_client,
        site=site_info,
        date=date_str,
        sync_mode=SyncMode.OVERWRITE,
    )

    # 3. Assert
    # 驗證在 OVERWRITE 模式下，刪除函數被正確地呼叫了一次
    mock_db.delete_performance_data_for_day.assert_called_once_with(1, "2024-01-01")
