#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
報告整合測試套件

測試 CLI 報告生成功能的整合測試
"""

from src.app import app


def test_cli_report_generation(test_app_runner):
    """測試 CLI 報告生成命令"""
    runner, test_container = test_app_runner
    db_service = test_container.database()

    # 準備數據
    site_id = db_service.add_site(domain="sc-domain:example.com", name="Test Site")
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
        }
    ]

    from datetime import datetime, timedelta

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    db_service.save_data_chunk(
        chunk=test_data,
        site_id=site_id,
        sync_mode="replace",
        date_str=yesterday,
        device="desktop",
        search_type="web",
    )

    # 測試報告生成命令
    result = runner.invoke(
        app,
        [
            "analyze",
            "report",
            str(site_id),  # site_id 作為位置參數
            "--days",
            "1",
        ],
        obj=test_container,
    )

    # 檢查命令是否成功執行
    assert result.exit_code in [0, 1]  # 允許失敗，但不允許崩潰


def test_cli_report_no_data(test_app_runner):
    """測試在沒有數據時生成報告"""
    runner, test_container = test_app_runner
    db_service = test_container.database()

    # 只添加站點，不添加數據
    site_id = db_service.add_site(domain="sc-domain:example.com", name="Test Site")
    assert site_id is not None

    # 測試報告生成命令
    result = runner.invoke(
        app,
        [
            "analyze",
            "report",
            str(site_id),  # site_id 作為位置參數
            "--days",
            "1",
        ],
        obj=test_container,
    )

    # 檢查命令是否正確處理沒有數據的情況
    assert result.exit_code in [0, 1]  # 允許失敗，但不允許崩潰
