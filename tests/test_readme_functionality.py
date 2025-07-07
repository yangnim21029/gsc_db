#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
README.md 功能驗證測試

這個測試套件確保 README.md 中提到的所有功能都能正常工作。
"""

from typer.testing import CliRunner

from src.app import app


class TestREADMEFunctionality:
    """測試 README.md 中提到的所有功能"""

    def test_cli_help_commands(self):
        """測試所有 CLI 幫助命令"""
        runner = CliRunner()

        # 測試主命令幫助
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "GSC-DB" in result.stdout

        # 測試子命令幫助
        subcommands = ["auth", "site", "sync", "analyze"]
        for cmd in subcommands:
            result = runner.invoke(app, [cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} --help 失敗"

    def test_site_management_commands(self, test_app_runner):
        """測試站點管理命令"""
        runner, test_container = test_app_runner

        # 測試 site list
        result = runner.invoke(app, ["site", "list"], obj=test_container)
        assert result.exit_code == 0

        # 測試 site add
        result = runner.invoke(
            app,
            ["site", "add", "sc-domain:test-site.com", "--name", "Test Site"],
            obj=test_container,
        )
        assert result.exit_code == 0
        assert "添加成功" in result.stdout

    def test_sync_commands_structure(self, test_app_runner):
        """測試同步命令的結構（不執行實際同步）"""
        runner, test_container = test_app_runner

        # 測試 sync daily 幫助
        result = runner.invoke(app, ["sync", "daily", "--help"], obj=test_container)
        assert result.exit_code == 0
        assert "執行每日數據同步" in result.stdout

    def test_analyze_commands_structure(self, test_app_runner):
        """測試分析命令的結構"""
        runner, test_container = test_app_runner

        # 測試 analyze report 幫助
        result = runner.invoke(app, ["analyze", "report", "--help"], obj=test_container)
        assert result.exit_code == 0
        assert "為指定站點生成性能摘要報告" in result.stdout

    def test_analysis_modules_import(self):
        """測試 README.md 中提到的分析模組能正常導入"""
        # 測試互動式數據視覺化
        from src.analysis.interactive_data_visualizer import InteractiveVisualizer

        assert InteractiveVisualizer is not None

        # 測試每小時性能分析器
        from src.analysis.hourly_performance_analyzer import HourlyAnalyzer

        assert HourlyAnalyzer is not None

        # 測試分析服務
        from src.services.analysis_service import AnalysisService

        assert AnalysisService is not None

    def test_api_module_import(self):
        """測試 API 模組能正常導入"""
        from src.web.api import app as api_app

        assert api_app is not None

    def test_core_services_import(self):
        """測試核心服務能正常導入"""
        from src.jobs.bulk_data_synchronizer import BulkDataSynchronizer
        from src.services.database import Database
        from src.services.gsc_client import GSCClient
        from src.services.site_service import SiteService

        assert Database is not None
        assert GSCClient is not None
        assert SiteService is not None
        assert BulkDataSynchronizer is not None

    def test_dependency_injection_container(self):
        """測試依賴注入容器"""
        from src.containers import Container

        container = Container()

        # 測試所有服務都能正常創建
        db_service = container.database()
        assert db_service is not None

        gsc_client = container.gsc_client()
        assert gsc_client is not None

        site_service = container.site_service()
        assert site_service is not None

        analysis_service = container.analysis_service()
        assert analysis_service is not None

        bulk_synchronizer = container.bulk_data_synchronizer()
        assert bulk_synchronizer is not None

    def test_cli_error_handling(self, test_app_runner):
        """測試 CLI 錯誤處理"""
        runner, test_container = test_app_runner

        # 測試無效的站點 ID
        result = runner.invoke(
            app, ["sync", "daily", "--site-id", "999", "--days", "1"], obj=test_container
        )
        # 應該優雅地處理錯誤，而不是崩潰
        assert result.exit_code != 2  # 2 表示參數錯誤

        # 測試缺少必要參數
        result = runner.invoke(
            app,
            ["sync", "daily"],  # 缺少 site-id 或 all-sites
            obj=test_container,
        )
        assert result.exit_code == 1
        assert "錯誤" in result.stdout
