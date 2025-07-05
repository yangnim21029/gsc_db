#!/usr/bin/env python3
"""
GSC CLI - Google Search Console 數據管理工具
主入口點
"""

import sys
from pathlib import Path
import typer
from src.cli import commands
from src.containers import Container

# 添加 src 目錄到 Python 路徑
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# 導入並運行 CLI 應用
# from src.cli.commands import app

def main():
    container = Container()
    
    app = typer.Typer(
        name="gsc-db",
        help="一個用於從 Google Search Console 下載數據並儲存到本地資料庫的 CLI 工具。",
        no_args_is_help=True,
        context_settings={"obj": container}
    )

    app.add_typer(commands.site_app, name="site")
    app.add_typer(commands.sync_app, name="sync")
    app.add_typer(commands.analyze_app, name="analyze")
    app.add_typer(commands.auth_app, name="auth")
    
    app()

if __name__ == "__main__":
    main() 