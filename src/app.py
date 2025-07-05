#!/usr/bin/env python3
"""
GSC CLI - Google Search Console 數據管理工具
主應用程式入口點
"""

import typer

from src.cli import commands
from src.containers import Container


def main():
    """
    初始化並運行 Typer CLI 應用程式。
    """
    container = Container()

    app = typer.Typer(
        name="gsc-cli",
        help="一個用於從 Google Search Console 下載數據並儲存到本地資料庫的 CLI 工具。",
        no_args_is_help=True,
        context_settings={"obj": container},
    )

    app.add_typer(commands.site_app, name="site")
    app.add_typer(commands.sync_app, name="sync")
    app.add_typer(commands.analyze_app, name="analyze")
    app.add_typer(commands.auth_app, name="auth")

    try:
        app()
    finally:
        # 確保在程式結束時關閉所有資源 (例如資料庫連接)
        container.shutdown_resources()


if __name__ == "__main__":
    main()
