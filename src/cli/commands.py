"""
CLI 命令模組

這個檔案定義了所有 gsc-cli 的子命令。
所有的命令都遵循依賴注入模式，從 Typer 的上下文 (ctx.obj) 中獲取服務實例，
而不是手動創建它們。這確保了服務的單例性、配置的一致性，並使得測試變得簡單。
"""

import typer
from rich.table import Table

from src.services.database import SyncMode
from src.utils.rich_console import console
from src.utils.system_health_check import (
    check_network_connectivity,
    diagnose_ssl_issues,
    wait_for_network_recovery,
)

# 建立子應用程式
auth_app = typer.Typer()
site_app = typer.Typer()
sync_app = typer.Typer()
analyze_app = typer.Typer()

app = typer.Typer()


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
    max_workers: int = typer.Option(2, help="最大併發工作者數量（建議：1-2）。"),
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
        max_workers=max_workers,
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


@app.command()
def network_check():
    """檢查網絡連接狀態和 SSL 健康狀況"""
    console.print("🔍 [bold blue]正在檢查網絡連接狀態...[/bold blue]")

    # 檢查網絡連接
    connectivity = check_network_connectivity()

    # 創建結果表格
    table = Table(title="網絡連接檢查結果", show_header=True, header_style="bold magenta")
    table.add_column("檢查項目", style="dim")
    table.add_column("狀態", justify="center")
    table.add_column("說明")

    status_items = [
        ("DNS 解析", connectivity["dns_resolution"], "域名解析是否正常"),
        ("HTTP 連接", connectivity["http_connection"], "基本 HTTP 連接"),
        ("HTTPS 連接", connectivity["https_connection"], "安全 HTTPS 連接"),
        ("Google API", connectivity["google_api_connection"], "Google API 可達性"),
        ("SSL 握手", connectivity["ssl_handshake"], "SSL/TLS 握手過程"),
    ]

    for item, status, description in status_items:
        status_icon = "✅" if status else "❌"
        status_color = "green" if status else "red"
        table.add_row(item, f"[{status_color}]{status_icon}[/{status_color}]", description)

    console.print(table)

    # 如果有 SSL 相關問題，提供診斷信息
    if not connectivity["ssl_handshake"] or not connectivity["google_api_connection"]:
        console.print("\n🔧 [bold yellow]SSL 診斷信息:[/bold yellow]")
        diagnosis = diagnose_ssl_issues()

        diag_table = Table(show_header=True, header_style="bold cyan")
        diag_table.add_column("項目", style="dim")
        diag_table.add_column("詳情")

        for key, value in diagnosis.items():
            if key == "recommendations":
                # 將建議分行顯示
                recommendations = value.split("; ")
                diag_table.add_row("建議", "\n".join(f"• {rec}" for rec in recommendations))
            else:
                diag_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(diag_table)

        # 提供修復建議
        console.print("\n💡 [bold green]修復建議:[/bold green]")
        console.print("1. 檢查網絡連接是否穩定")
        console.print("2. 嘗試重新運行同步命令")
        console.print("3. 如果問題持續，請使用 'gsc sync --max-workers 1' 降低並發數")
        console.print("4. 檢查防火牆和代理設定")
    else:
        console.print("\n✅ [bold green]網絡連接正常！[/bold green]")


@app.command()
def wait_network(
    max_wait: int = typer.Option(60, help="最大等待時間（秒）"),
    interval: int = typer.Option(5, help="檢查間隔（秒）"),
):
    """等待網絡連接恢復"""
    console.print(f"⏳ [bold blue]等待網絡恢復（最多 {max_wait} 秒）...[/bold blue]")

    if wait_for_network_recovery(max_wait, interval):
        console.print("✅ [bold green]網絡連接已恢復！[/bold green]")
    else:
        console.print("❌ [bold red]網絡連接在指定時間內未恢復[/bold red]")
        console.print("請檢查網絡設定或聯繫網絡管理員")
