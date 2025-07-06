#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest 設定檔 (fixtures)

這個檔案為所有測試提供共享的、可重用的設定和資源。
"""

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from src.containers import Container
from src.services.database import Database


@pytest.fixture(scope="function")
def test_db():
    """
    建立一個在記憶體中的 SQLite 資料庫。
    作用域 (scope) 設定為 'function'，以確保每個測試函數都獲得一個
    獨立、乾淨的資料庫實例，這對於並行測試 (pytest-xdist) 至關重要。
    """
    # --- Setup ---
    db = Database(db_path=":memory:")
    db.init_db()  # 確保所有表都已建立
    yield db
    # --- Teardown (no action needed for in-memory db) ---


@pytest.fixture
def test_app_runner(test_db, monkeypatch):
    """
    一個功能強大的 fixture，它提供了一個 CLI runner 和一個預先配置好的
    測試依賴容器 (test container)，以便在測試中注入。
    """
    runner = CliRunner()

    # 1. 建立一個模擬的 GSC 客戶端
    mock_gsc_client = MagicMock()
    mock_gsc_client.get_sites.return_value = ["sc-domain:example.com"]

    # 2. 直接創建測試服務實例
    from src.services.analysis_service import AnalysisService
    from src.services.site_service import SiteService

    test_site_service = SiteService(test_db)
    test_analysis_service = AnalysisService(test_db)

    # 3. 建立一個測試用的依賴注入容器，並覆寫其服務
    test_container = Container()
    test_container.db_service.override(test_db)
    test_container.site_service.override(test_site_service)
    test_container.analysis_service.override(test_analysis_service)
    test_container.gsc_client.override(mock_gsc_client)

    # 4. [關鍵] 使用 monkeypatch 將全域的 container 實例替換為我們的測試容器。
    #    這樣，所有使用 @Depends(container.some_service) 的命令都會從
    #    test_container 中獲取它們的依賴。
    monkeypatch.setattr("src.app.container", test_container)

    # 5. 將 runner 和 container 交給測試函數，以便進行額外的模擬或斷言
    yield runner, test_container
