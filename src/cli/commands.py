"""
CLI 命令模組

這個檔案定義了所有 gsc-cli 的子命令。
所有的命令都遵循依賴注入模式，從 Typer 的上下文 (ctx.obj) 中獲取服務實例，
而不是手動創建它們。這確保了服務的單例性、配置的一致性，並使得測試變得簡單。
"""

import typer
from rich.console import Console
from rich.table import Table

from src.services.database import SyncMode

# 建立子應用程式
auth_app = typer.Typer()
site_app = typer.Typer()
sync_app = typer.Typer()
analyze_app = typer.Typer()

console = Console()


@auth_app.command("login")
def login(ctx: typer.Context):
    """執行 Google API 認證流程。"""
    gsc_client = ctx.obj.gsc_client()
    gsc_client.authenticate()
    console.print("✅ 認證成功！憑證已儲存。")


@site_app.command("list")
def list_sites(ctx: typer.Context):
    """從本地資料庫和遠端 GSC 列出所有網站。"""
    site_service = ctx.obj.site_service()
    sites = site_service.get_all_sites_with_status()

    table = Table(title="網站列表")
    table.add_column("ID", style="cyan")
    table.add_column("名稱", style="magenta")
    table.add_column("URL / 網域", style="green")
    table.add_column("來源", style="yellow")

    for site in sites:
        table.add_row(
            str(site.get("id", "N/A")),
            site.get("name", "N/A"),
            site.get("domain", "N/A"),
            site.get("source", "N/A"),
        )
    console.print(table)


@site_app.command("add")
def add_site(
    ctx: typer.Context,
    site_url: str = typer.Argument(..., help="要添加的網站 URL 或 sc-domain:domain.com"),
    name: str = typer.Option(None, "--name", "-n", help="網站的自訂名稱"),
):
    """將一個新網站添加到本地資料庫。"""
    site_service = ctx.obj.site_service()
    display_name = name if name else site_url
    site_id = site_service.add_site(domain=site_url, name=display_name)
    if site_id:
        console.print(f"✅ 站點 '{display_name}' 添加成功，ID 為 {site_id}。")
    else:
        console.print(f"⚠️ 站點 '{display_name}' 可能已存在或添加失敗。")


@sync_app.command("daily")
def sync_daily(
    ctx: typer.Context,
    site_id: int = typer.Option(None, help="要同步的單一網站 ID。"),
    all_sites: bool = typer.Option(False, "--all-sites", help="同步所有已啟用的網站。"),
    days: int = typer.Option(7, help="要回溯同步的天數。"),
    sync_mode: SyncMode = typer.Option(
        SyncMode.SKIP.value, help="同步模式：'skip' (跳過已存在) 或 'overwrite' (覆蓋)。"
    ),
):
    """
    執行每日數據同步。
    """
    if not site_id and not all_sites:
        console.print("錯誤：必須提供 --site-id 或 --all-sites 其中一個選項。")
        raise typer.Exit(code=1)

    # 從容器中獲取 bulk_data_synchronizer 服務
    synchronizer = ctx.obj.bulk_data_synchronizer()

    # 直接使用 BulkDataSynchronizer 的 run_sync 方法
    # 它內部已經處理了 all_sites 和 site_id 的邏輯
    synchronizer.run_sync(
        all_sites=all_sites,
        site_id=site_id,
        days=days,
        sync_mode=sync_mode,
    )


@analyze_app.command("report")
def analyze_report(
    ctx: typer.Context,
    site_id: int = typer.Argument(..., help="要分析的網站 ID。"),
    days: int = typer.Option(7, help="要分析的數據天數。"),
):
    """為指定站點生成性能摘要報告。"""
    # 從容器中獲取 analysis_service
    analysis_service = ctx.obj.analysis_service()
    report = analysis_service.generate_performance_summary(site_id, days)

    console.print(f"--- 過去 {days} 天網站 ID {site_id} 的性能報告 ---")
    console.print(report)
