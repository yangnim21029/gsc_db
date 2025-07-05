#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC 報告生成整合測試
展示新的報告生成功能和 CLI 整合
"""

import pytest
from typer.testing import CliRunner
import sqlite3
from pathlib import Path
import pandas as pd

# 將項目根目錄添加到 Python 路徑
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app  # 導入 Typer app
from src.services.database import Database
from src.analysis.analytics_report_builder import build_report

runner = CliRunner()

@pytest.fixture(scope="module")
def test_db():
    """創建一個隔離的、結構正確的測試數據庫"""
    db_path = Path("test_integration.db")
    if db_path.exists():
        db_path.unlink()

    # [FIX] 使用 Database 類來初始化正確的表結構
    db = Database(db_path=str(db_path))
    with db.get_connection() as conn:
        # 插入符合新結構的站點數據
        conn.execute(
            "INSERT INTO sites (id, domain, name) VALUES (?, ?, ?)",
            (1, "https://example.com", "example.com")
        )
        
        # 插入符合新結構的性能數據
        performance_df = pd.DataFrame({
            'site_id': 1,
            'date': ['2023-01-01', '2023-01-01', '2023-01-02'],
            'query': ['keyword a', 'keyword b', 'keyword a'],
            'page': ['/page1', '/page1', '/page2'],
            'device': ['desktop', 'mobile', 'desktop'],
            'search_type': ['web', 'web', 'web'],  # 補上缺少的欄位
            'clicks': [10, 5, 12],
            'impressions': [100, 80, 150],
            'ctr': [0.1, 0.0625, 0.08],
            'position': [5.5, 10.2, 4.8]
        })
        performance_df.to_sql('gsc_performance_data', conn, if_exists='append', index=False)
        conn.commit()

    yield db_path

    # 清理測試數據庫
    db_path.unlink()


def test_cli_report_generation(test_db):
    """測試 CLI 報告生成命令"""
    report_path = Path("cli_test_report.md")
    if report_path.exists():
        report_path.unlink()
        
    result = runner.invoke(app, [
        "analyze", "report",
        "--site-id", "1",
        "--output-path", str(report_path),
        "--no-plots",
        "--db-path", str(test_db)
    ])
    
    assert result.exit_code == 0
    assert "報告成功生成" in result.stdout
    assert report_path.exists()
    
    content = report_path.read_text()
    assert "GSC 網站表現報告" in content
    assert "keyword a" in content
    report_path.unlink()


def test_build_report_functionality(test_db):
    """直接測試 build_report 函數的功能"""
    report_path = Path("module_test_report.md")
    plot_dir = Path("test_plots_dir")
    
        result = build_report(
        site_id=1,
        output_path=str(report_path),
        db_path=str(test_db),
        include_plots=True,
        plot_save_dir=str(plot_dir)
    )

    assert result["success"] is True
    assert report_path.exists()
    
    # 檢查圖表是否生成
    assert plot_dir.exists()
    plot_files = list(plot_dir.glob("*.png"))
    assert len(plot_files) > 0, "應該生成圖表文件"
    
    # 清理
    report_path.unlink()
    for f in plot_files:
        f.unlink()
    plot_dir.rmdir()


def test_cli_report_help():
    """測試報告命令的 --help 標誌"""
    result = runner.invoke(app, ["analyze", "report", "--help"])
    assert result.exit_code == 0
    assert "生成指定站點的 GSC 綜合表現報告" in result.stdout
    assert "--site-id" in result.stdout 