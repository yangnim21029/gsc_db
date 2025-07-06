#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用 typer.testing.CliRunner 進行的整合測試。
這種方法比 subprocess 更快、更可靠。
"""

from typer.testing import CliRunner

from src.app import app  # 導入主 Typer 應用程式

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
