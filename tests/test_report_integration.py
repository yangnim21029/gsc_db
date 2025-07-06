#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC 報告生成整合測試
"""

from src.app import app


def test_cli_report_generation(test_app_runner):
    """測試 CLI 報告生成命令"""
    runner, test_container = test_app_runner
    db_service = test_container.db_service()

    # 準備數據
    site_id = db_service.add_site(domain="https://example.com", name="example.com")
    assert site_id is not None

    # 插入一些測試數據
    test_data = [
        {
            "page": "https://example.com/page1",
            "query": "test query",
            "clicks": 10,
            "impressions": 100,
            "ctr": 0.1,
            "position": 5.0,
        },
        {
            "page": "https://example.com/page2",
            "query": "another query",
            "clicks": 5,
            "impressions": 50,
            "ctr": 0.1,
            "position": 3.0,
        },
    ]

    # 使用 save_data_chunk 方法插入數據
    for data in test_data:
        db_service.save_data_chunk(
            chunk=[data],
            site_id=site_id,
            sync_mode="replace",
            date_str="2024-01-01",
            device="desktop",
            search_type="web",
        )

    # 運行報告生成命令
    result = runner.invoke(
        app,
        [
            "analyze",
            "report",
            "--site-id",
            str(site_id),
            "--output-path",
            "test_report.md",
            "--no-plots",
        ],
        obj=test_container,
    )

    # 檢查命令是否成功
    assert result.exit_code == 0
    assert "報告成功生成" in result.stdout or "報告已生成" in result.stdout


def test_cli_report_help(test_app_runner):
    """測試報告命令的 --help 標誌"""
    runner, test_container = test_app_runner
    result = runner.invoke(app, ["analyze", "report", "--help"], obj=test_container)
    assert result.exit_code == 0
    assert "生成指定站點的 GSC 綜合表現報告" in result.stdout
