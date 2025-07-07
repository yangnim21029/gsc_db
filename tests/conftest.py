#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest 設定檔 (fixtures)

這個檔案為所有測試提供共享的、可重用的設定和資源。
"""

import sqlite3
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.containers import Container
from src.services.database import Database


@pytest.fixture(scope="session")
def runner():
    """提供一個 Typer CliRunner 的實例，用於測試 CLI 命令。"""
    return CliRunner()


@pytest.fixture(scope="function")
def test_db(tmp_path: Path):
    """
    為每個測試函數建立一個獨立的、基於檔案的臨時 SQLite 資料庫。
    這確保了測試之間的隔離，並且與並行測試工具 (如 pytest-xdist) 完全相容，
    避免了使用 :memory: 資料庫在多進程環境下可能出現的問題。
    `tmp_path` fixture 會在測試結束後自動清理資料庫檔案。
    """
    # --- Setup ---
    db_path = tmp_path / "test.db"
    # Connect with check_same_thread=False to allow sharing the connection
    # across threads, which is essential for concurrency tests. The Database
    # service's internal lock will handle serializing writes.
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    connection.row_factory = sqlite3.Row  # 讓查詢結果可以像字典一樣使用
    # 使用可重入鎖 (RLock)，允許一個執行緒多次獲取同一個鎖。
    # 這對於複雜的操作更安全，因為一個持有鎖的函式可能需要在同一個執行緒中
    # 呼叫另一個也需要鎖的函式。
    lock = threading.RLock()
    db = Database(connection=connection, lock=lock)

    # --- Yield the db instance to the test ---
    yield db, connection, lock

    # --- Teardown ---
    # 雖然 tmp_path 會清理檔案，但明確關閉連線是個好習慣。
    db.close_connection()


@pytest.fixture
def test_app_runner(test_db, monkeypatch):
    """
    一個功能強大的 fixture，它提供了一個 CLI runner 和一個預先配置好的
    測試依賴容器 (test container)，以便在測試中注入。
    """
    db_service, _, _ = test_db  # Unpack the tuple from the enhanced test_db fixture
    runner = CliRunner()

    # 1. 建立一個模擬的 GSC 客戶端
    mock_gsc_client = MagicMock()
    mock_gsc_client.get_sites.return_value = ["sc-domain:example.com"]

    # 2. 直接創建測試服務實例
    from src.services.analysis_service import AnalysisService
    from src.services.site_service import SiteService

    test_site_service = SiteService(db_service, mock_gsc_client)  # 注入 GSC 客戶端
    test_analysis_service = AnalysisService(db_service)

    # 3. 建立一個測試用的依賴注入容器，並覆寫其服務
    test_container = Container()
    test_container.database.override(db_service)
    test_container.site_service.override(test_site_service)
    test_container.analysis_service.override(test_analysis_service)
    test_container.gsc_client.override(mock_gsc_client)

    # 4. [關鍵] 使用 monkeypatch 將全域的 container 實例替換為我們的測試容器。
    #    這樣，所有使用 @Depends(container.some_service) 的命令都會從
    #    test_container 中獲取它們的依賴。
    monkeypatch.setattr("src.app.container", test_container)

    # 5. 將 runner 和 container 交給測試函數，以便進行額外的模擬或斷言
    yield runner, test_container
