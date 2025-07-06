#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用 typer.testing.CliRunner 進行的整合測試。
這種方法比 subprocess 更快、更可靠。
"""

from typer.testing import CliRunner

from src.app import app  # 導入主 Typer 應用程式
from src.services.database import SyncMode

runner = CliRunner()


def test_app_help():
    """測試主應用的 --help 標誌。"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # 檢查關鍵詞，因為實際輸出包含換行符
    assert "GSC-DB" in result.stdout
    assert "Google Search Console" in result.stdout


def test_site_list_command(test_app_runner):
    """
    測試 `site list` 命令。
    這個測試使用了 `test_app_runner` fixture，它會提供一個配置好的 CliRunner
    以及一個被模擬 (mocked) 的 GSC 客戶端。
    """
    # test_app_runner 來自 conftest.py
    runner, test_container = test_app_runner
    site_service = test_container.site_service()
    mock_gsc_client = test_container.gsc_client()

    # 設置 GSC 客戶端的模擬返回值
    mock_gsc_client.get_sites.return_value = ["sc-domain:remote-example.com"]

    # 準備：在測試資料庫中預先插入一個站點
    site_service.add_site(domain="https://example.com", name="My Test Site")

    result = runner.invoke(app, ["site", "list"], obj=test_container)

    assert result.exit_code == 0
    assert "My Test Site" in result.stdout
    assert "https://example.com" in result.stdout
    # 驗證 GSC client 也被呼叫了
    mock_gsc_client.get_sites.assert_called_once()


def test_add_site_command(test_app_runner):
    """測試 `site add` 命令。"""
    runner, test_container = test_app_runner
    site_service = test_container.site_service()

    result = runner.invoke(
        app,
        ["site", "add", "sc-domain:new-site.com", "--name", "New Site"],
        obj=test_container,
    )

    assert result.exit_code == 0
    assert "站點 'New Site' 添加成功" in result.stdout

    # 驗證數據是否真的寫入了資料庫
    site = site_service.get_site_by_id(1)
    assert site is not None
    assert site["name"] == "New Site"
    assert site["domain"] == "sc-domain:new-site.com"


def test_sync_daily_command(test_app_runner, mocker):
    """測試 `sync daily` 命令。"""
    runner, test_container = test_app_runner

    # 模擬 BulkDataSynchronizer 的 run_sync 方法
    mock_run_sync = mocker.patch("src.jobs.bulk_data_synchronizer.BulkDataSynchronizer.run_sync")

    # 準備：在測試資料庫中預先插入一個站點
    site_service = test_container.site_service()
    site_service.add_site(domain="https://sync-test.com", name="Sync Test Site")

    result = runner.invoke(
        app,
        ["sync", "daily", "--site-id", "1", "--days", "3"],
        obj=test_container,
    )

    assert result.exit_code == 0
    # 驗證 run_sync 方法被以正確的參數呼叫了一次
    mock_run_sync.assert_called_once_with(
        all_sites=False,
        site_id=1,
        days=3,
        sync_mode=SyncMode.SKIP,  # 注意這裡是 SyncMode 枚舉，不是字串
    )


def test_analyze_report_command(test_app_runner, mocker):
    """測試 `analyze report` 命令。"""
    runner, test_container = test_app_runner

    # 模擬 AnalysisService 的方法
    mock_generate_summary = mocker.patch(
        "src.services.analysis_service.AnalysisService.generate_performance_summary"
    )
    # 讓被模擬的方法返回一個簡單的字串
    mock_generate_summary.return_value = "Mocked performance report"

    # 準備：在測試資料庫中預先插入一個站點
    site_service = test_container.site_service()
    site_service.add_site(domain="https://analysis-test.com", name="Analysis Test Site")

    result = runner.invoke(
        app,
        ["analyze", "report", "1", "--days", "14"],
        obj=test_container,
    )

    assert result.exit_code == 0
    # 驗證模擬的方法被正確呼叫
    mock_generate_summary.assert_called_once_with(1, 14)
    # 驗證 CLI 命令的輸出包含了模擬方法返回的內容
    assert "Mocked performance report" in result.stdout
