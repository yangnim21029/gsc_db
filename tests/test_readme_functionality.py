#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
README.md 功能驗證測試

這個測試套件確保 README.md 中提到的所有功能都能正常工作。
"""

from pathlib import Path

import pytest
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

        # 只測試容器類別能正常導入，不實際創建服務實例
        # 因為實際創建需要真實的資料庫檔案和配置
        assert Container is not None

        # 測試容器類別有預期的提供者
        container = Container()

        # 檢查提供者是否存在（不調用它們）
        assert hasattr(container, "database")
        assert hasattr(container, "gsc_client")
        assert hasattr(container, "site_service")
        assert hasattr(container, "analysis_service")
        assert hasattr(container, "bulk_data_synchronizer")

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

    def test_readme_just_commands_availability(self):
        """測試 README.md 中提到的 just 命令是否存在"""
        justfile_path = Path(__file__).parent.parent / "justfile"
        if not justfile_path.exists():
            pytest.skip("justfile 不存在，跳過 just 命令測試")

        justfile_content = justfile_path.read_text()

        # README.md 中提到的主要 just 命令
        expected_commands = [
            "bootstrap",
            "auth",
            "site-list",
            "site-add",
            "sync-site",
            "sync-multiple",
            "maintenance",
            "check",
            "test",
            "type-check",
            "lint",
            "dev-server",
            "prod-server",
            "setup",
        ]

        for cmd in expected_commands:
            # 檢查命令是否在 justfile 中定義
            assert f"{cmd}:" in justfile_content or f"{cmd} " in justfile_content, (
                f"just {cmd} 命令在 justfile 中未找到"
            )

    def test_python_module_execution_paths(self):
        """測試 README.md 中提到的 Python 模組執行路徑"""
        # 測試模組是否可以作為 Python 模組執行
        modules_to_test = [
            "src.analysis.interactive_data_visualizer",
            "src.analysis.hourly_performance_analyzer",
        ]

        for module in modules_to_test:
            try:
                # 嘗試導入模組以確保路徑正確
                __import__(module)
            except ImportError as e:
                pytest.fail(f"無法導入 README.md 中提到的模組 {module}: {e}")

    def test_gsc_cli_script_availability(self):
        """測試 gsc-cli 腳本是否可用（通過 poetry.scripts 定義）"""
        # 檢查 pyproject.toml 中是否定義了 gsc-cli 腳本
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            assert 'gsc-cli = "src.app:main"' in content, (
                "gsc-cli 腳本在 pyproject.toml 中未正確定義"
            )

    def test_api_endpoints_structure(self):
        """測試 API 端點結構"""
        from src.web.api import app as api_app

        # 檢查 FastAPI 應用是否正確創建
        assert api_app is not None
        assert hasattr(api_app, "routes"), "API 應用缺少路由"

        # 檢查是否有基本路由
        route_paths = [
            getattr(route, "path", None) for route in api_app.routes if hasattr(route, "path")
        ]
        route_paths = [path for path in route_paths if path is not None]
        assert len(route_paths) > 0, "API 應用沒有定義任何路由"

    def test_project_structure_requirements(self):
        """測試項目結構是否符合 README.md 描述"""
        project_root = Path(__file__).parent.parent

        # 檢查主要目錄結構
        required_dirs = [
            "src",
            "src/analysis",
            "src/cli",
            "src/services",
            "src/utils",
            "src/web",
            "tests",
            "cred",
            "data",
            "logs",
            "reports",
        ]

        for dir_path in required_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"必需的目錄 {dir_path} 不存在"

    def test_development_tools_integration(self):
        """測試開發工具集成"""
        project_root = Path(__file__).parent.parent

        # 檢查重要配置文件
        config_files = ["pyproject.toml", "justfile", ".pre-commit-config.yaml"]

        for config_file in config_files:
            file_path = project_root / config_file
            assert file_path.exists(), f"配置文件 {config_file} 不存在"

    def test_readme_command_examples_syntax(self, test_app_runner):
        """測試 README.md 中的命令示例語法"""
        runner, test_container = test_app_runner

        # 添加測試站點
        db_service = test_container.database()
        site_id = db_service.add_site(domain="sc-domain:test.com", name="Test Site")

        # 測試 README.md 中提到的命令格式
        test_commands = [
            # 站點管理
            ["site", "list"],
            ["site", "add", "sc-domain:example.com", "--name", "Example Site"],
            # 分析命令
            ["analyze", "report", str(site_id), "--days", "7"],
        ]

        for cmd in test_commands:
            result = runner.invoke(app, cmd, obj=test_container)
            # 確保命令不會因為語法錯誤而失敗（exit_code 2）
            assert result.exit_code != 2, f"命令語法錯誤: {' '.join(cmd)}"
