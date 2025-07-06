#!/usr/bin/env python3
"""
GSC CLI - Google Search Console 數據管理工具
主應用程式入口點
"""

# -*- coding: utf-8 -*-

import typer

from src.cli import commands
from src.config import setup_logging
from src.containers import Container
from src.web import api as web_api

# 1. 建立主 Typer 應用程式
app = typer.Typer(
    help="GSC-DB: 一個用於從 Google Search Console 下載數據並儲存到本地資料庫的 CLI 工具。",
    no_args_is_help=True,
)

# 2. 建立全域依賴注入容器
# 注意：這個 container 實例主要用於 @app.callback 中進行初始化。
# 命令本身應該從 ctx.obj 中獲取容器，以確保在測試中可以被替換。
container = Container()
# 將 web_api 的容器指向同一個，以共享服務實例
web_api.container = container


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """
    應用程式主入口點和回呼函數。

    在任何子命令執行之前，這個函數會被呼叫。
    它的主要職責是：
    1. 執行全域設定，例如初始化日誌。
    2. 建立並配置依賴注入容器。
    3. 將容器實例附加到 Typer 的上下文 (context) 中，
       以便所有子命令都可以透過 `ctx.obj` 存取共享的服務。
    """
    # 如果 ctx.invoked_subcommand 為 None，表示使用者只運行了主命令而沒有子命令
    # 在這種情況下，我們可以選擇顯示幫助訊息或執行預設行為。
    if ctx.invoked_subcommand is None:
        # 如果使用者只是運行 `gsc-cli` 而沒有任何參數，顯示幫助訊息
        pass

    setup_logging()

    # 如果 ctx.obj 已經被 runner (在測試中) 填充，則使用它
    # 否則，創建一個新的容器。
    # 這使得測試時注入模擬容器變得異常簡單。
    if ctx.obj is None:
        ctx.obj = container


# 3. 將其他子應用程式 (sub-apps) 添加到主應用程式中
app.add_typer(commands.auth_app, name="auth")
app.add_typer(commands.site_app, name="site")
app.add_typer(commands.sync_app, name="sync")
app.add_typer(commands.analyze_app, name="analyze")


def main():
    """Entry point for the gsc-cli command."""
    app()


if __name__ == "__main__":
    main()
