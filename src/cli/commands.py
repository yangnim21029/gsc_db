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
):
    """
    執行每日數據同步。

    注意：此命令使用順序處理模式，確保 GSC API 調用的穩定性。
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


@sync_app.command("hourly")
def sync_hourly(
    ctx: typer.Context,
    site_id: int = typer.Argument(..., help="要同步小時數據的網站 ID。"),
    days: int = typer.Option(1, help="要回溯同步的天數（默認：1）。"),
    force_overwrite: bool = typer.Option(False, "--force", help="強制覆蓋已存在的小時數據。"),
):
    """
    執行小時級數據同步。

    這個命令會同步指定網站的小時級性能數據，提供更精細的數據分析。
    注意：小時數據通常只有最近幾天的數據可用。
    """
    console.print(f"🔄 開始同步網站 ID {site_id} 的小時級數據（過去 {days} 天）...")

    # 從容器中獲取服務
    hourly_service = ctx.obj.hourly_data_service()
    site_service = ctx.obj.site_service()

    # 驗證網站是否存在
    sites = site_service.get_all_sites()
    site_exists = any(site["id"] == site_id for site in sites)
    if not site_exists:
        console.print(f"❌ 錯誤：找不到 ID 為 {site_id} 的網站。")
        console.print("💡 使用 'gsc-cli site list' 查看可用的網站。")
        raise typer.Exit(code=1)

    # 獲取網站信息
    site_info = next(site for site in sites if site["id"] == site_id)
    site_url = site_info["domain"]

    console.print(f"📊 同步網站：{site_info['name']} ({site_url})")

    try:
        # 計算日期範圍
        from datetime import datetime, timedelta

        end_date = datetime.now() - timedelta(days=1)  # 昨天
        start_date = end_date - timedelta(days=days - 1)

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        console.print(f"📅 日期範圍：{start_date_str} 到 {end_date_str}")

        # 執行小時數據同步
        from src.services.database import SyncMode

        sync_mode = SyncMode.OVERWRITE if force_overwrite else SyncMode.SKIP

        result = hourly_service.sync_hourly_data(
            site_url=site_url, start_date=start_date_str, end_date=end_date_str, sync_mode=sync_mode
        )

        if result and result.get("inserted", 0) > 0:
            console.print("✅ 小時級數據同步完成！")
            console.print(f"📈 同步的記錄數：{result.get('inserted', 0)}")
        else:
            console.print("⚠️ 小時級數據同步完成，但沒有新數據。")

    except Exception as e:
        console.print(f"❌ 小時級數據同步失敗：{str(e)}")
        console.print("💡 建議：")
        console.print("  1. 檢查網絡連接：just network-check")
        console.print("  2. 驗證 Google API 認證：just auth")
        console.print("  3. 嘗試更小的日期範圍（--days 1）")
        raise typer.Exit(code=1)


@sync_app.command("multiple")
def sync_multiple(
    ctx: typer.Context,
    site_ids: str = typer.Argument(..., help="要同步的網站 ID 列表，以空格分隔，例如 '1 2 3'"),
    days: int = typer.Option(7, help="要回溯同步的天數。"),
    sync_mode: SyncMode = typer.Option(
        SyncMode.SKIP.value, help="同步模式：'skip' (跳過已存在) 或 'overwrite' (覆蓋)。"
    ),
):
    """
    批次同步多個網站。

    此命令會依序同步指定的多個網站，提供詳細的進度報告和錯誤處理。
    由於 GSC API 的限制，所有同步都是順序進行的。

    範例：
        gsc-cli sync multiple "1 2 3" --days 7
        gsc-cli sync multiple "1 3 5" --days 14 --sync-mode overwrite
    """
    import time
    from datetime import datetime

    # 解析網站 ID 列表
    try:
        site_id_list = [int(site_id.strip()) for site_id in site_ids.split() if site_id.strip()]
    except ValueError:
        console.print("❌ [red]錯誤：網站 ID 必須是數字[/red]")
        console.print("💡 正確格式：gsc-cli sync multiple '1 2 3' --days 7")
        raise typer.Exit(code=1)

    if not site_id_list:
        console.print("❌ [red]錯誤：必須提供至少一個網站 ID[/red]")
        raise typer.Exit(code=1)

    # 驗證所有網站 ID 是否存在
    site_service = ctx.obj.site_service()
    all_sites = site_service.get_all_sites()
    site_dict = {site["id"]: site for site in all_sites}

    invalid_ids = [site_id for site_id in site_id_list if site_id not in site_dict]
    if invalid_ids:
        console.print(f"❌ [red]錯誤：以下網站 ID 不存在：{invalid_ids}[/red]")
        console.print("💡 使用 'gsc-cli site list' 查看可用的網站")
        raise typer.Exit(code=1)

    # 開始批次同步
    console.print(f"🚀 [bold blue]開始批次同步網站：{site_id_list} (過去 {days} 天)[/bold blue]")
    console.print(f"📊 [cyan]共需同步 {len(site_id_list)} 個網站[/cyan]")
    console.print(f"⚙️ [yellow]同步模式：{sync_mode.value}[/yellow]")
    console.print()

    # 統計變數
    success_count = 0
    failure_count = 0
    failed_sites = []
    start_time = time.time()

    # 獲取同步服務
    synchronizer = ctx.obj.bulk_data_synchronizer()

    # 逐個同步網站
    for i, site_id in enumerate(site_id_list, 1):
        site_info = site_dict[site_id]
        current_time = datetime.now().strftime("%H:%M:%S")

        console.print(
            f"--- [bold cyan]正在同步網站 ID: {site_id} (進度: {i}/{len(site_id_list)})[/bold cyan] ---"
        )
        console.print(
            f"📅 [dim]{current_time}[/dim] 🌐 [green]{site_info['name']}[/green] ([blue]{site_info['domain']}[/blue])"
        )

        site_start_time = time.time()

        try:
            # 執行同步
            synchronizer.run_sync(
                all_sites=False,
                site_id=site_id,
                days=days,
                sync_mode=sync_mode,
            )

            # 計算耗時
            site_end_time = time.time()
            duration = int(site_end_time - site_start_time)
            success_count += 1

            console.print(
                f"✅ [bold green]網站 ID {site_id} 同步成功[/bold green] [dim](耗時: {duration}秒)[/dim]"
            )

        except Exception as e:
            # 計算耗時
            site_end_time = time.time()
            duration = int(site_end_time - site_start_time)
            failure_count += 1
            failed_sites.append(site_id)

            console.print(
                f"❌ [bold red]網站 ID {site_id} 同步失敗[/bold red] [dim](耗時: {duration}秒)[/dim]"
            )
            console.print(f"   [red]錯誤：{str(e)}[/red]")

        console.print()

        # 在網站間添加小延遲，避免 API 限制
        if i < len(site_id_list):
            time.sleep(1)

    # 總結報告
    total_time = int(time.time() - start_time)
    console.print("=" * 60)
    console.print(f"📈 [bold blue]批次同步完成！[/bold blue] [dim](總耗時: {total_time}秒)[/dim]")
    console.print(f"  ✅ [bold green]成功: {success_count} 個網站[/bold green]")
    console.print(f"  ❌ [bold red]失敗: {failure_count} 個網站[/bold red]")

    if failed_sites:
        console.print(f"  🔧 [yellow]失敗的網站ID: {failed_sites}[/yellow]")
        console.print()
        console.print("💡 [bold green]建議處理失敗的網站:[/bold green]")
        console.print("  gsc-cli network-check                    # 檢查網絡連接")
        console.print("  gsc-cli sync daily --site-id <ID>       # 重試單個網站")
        console.print("  gsc-cli sync status --site-id <ID>      # 檢查具體狀態")
        console.print('  gsc-cli sync multiple "<失敗的ID>"      # 重試失敗的網站')

    # 設定退出碼
    if failure_count > 0:
        raise typer.Exit(code=1)


@sync_app.command("status")
def sync_status(
    ctx: typer.Context,
    site_id: int = typer.Option(None, help="查看特定網站的同步狀態"),
    show_recent: int = typer.Option(10, help="顯示最近的同步記錄數量"),
):
    """
    查看同步狀態和進度監控。

    顯示正在運行的同步進程、最近的同步記錄以及各網站的同步狀態概覽。
    """
    import subprocess
    import sys
    from datetime import datetime

    console.print("🔍 [bold blue]正在檢查同步狀態...[/bold blue]\n")

    # 1. 檢查正在運行的同步進程
    try:
        if sys.platform == "win32":
            # Windows PowerShell 命令
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-Process | Where-Object {$_.ProcessName -match 'python|gsc-cli|poetry'} | Where-Object {$_.CommandLine -match 'sync'} | Format-Table -AutoSize",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            # Unix/Linux/macOS 命令
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            if sys.platform == "win32":
                processes = result.stdout.strip()
            else:
                processes = [
                    line
                    for line in result.stdout.split("\n")
                    if any(keyword in line for keyword in ["gsc-cli", "sync", "poetry"])
                    and "sync status" not in line
                    and "grep" not in line
                ]

            if (sys.platform == "win32" and processes) or (sys.platform != "win32" and processes):
                console.print("🔄 [bold yellow]正在運行的同步進程:[/bold yellow]")
                if sys.platform == "win32":
                    console.print(processes)
                else:
                    for proc in processes[:5]:  # 限制顯示前5個
                        console.print(f"  {proc}")
                console.print()
            else:
                console.print("✅ [bold green]目前沒有正在運行的同步進程[/bold green]\n")
        else:
            console.print("⚠️ [yellow]無法檢查運行中的進程[/yellow]\n")
    except Exception as e:
        console.print(f"⚠️ [yellow]進程檢查失敗: {str(e)}[/yellow]\n")

    # 2. 獲取資料庫連接並查詢同步狀態
    try:
        database_service = ctx.obj.database()

        # 獲取最近的同步記錄
        query = """
        SELECT
            s.name as site_name,
            s.domain as site_domain,
            MAX(pd.date) as last_sync_date,
            COUNT(pd.id) as total_records,
            COUNT(CASE WHEN pd.date >= date('now', '-7 days') THEN 1 END) as recent_records
        FROM sites s
        LEFT JOIN gsc_performance_data pd ON s.id = pd.site_id
        WHERE s.id = ? OR ? IS NULL
        GROUP BY s.id, s.name, s.domain
        ORDER BY last_sync_date DESC
        """

        with database_service._lock:
            results = database_service._connection.execute(query, (site_id, site_id)).fetchall()

        if results:
            # 創建狀態表格
            table = Table(title="網站同步狀態概覽", show_header=True, header_style="bold magenta")
            table.add_column("網站名稱", style="cyan")
            table.add_column("域名", style="green")
            table.add_column("最後同步", style="yellow")
            table.add_column("總記錄數", justify="right", style="blue")
            table.add_column("近7天記錄", justify="right", style="magenta")
            table.add_column("狀態", justify="center")

            for row in results:
                last_sync = row[2] if row[2] else "從未同步"
                total_records = row[3] if row[3] else 0
                recent_records = row[4] if row[4] else 0

                # 判斷同步狀態
                if not row[2]:
                    status = "[red]未同步[/red]"
                else:
                    last_date = datetime.strptime(row[2], "%Y-%m-%d")
                    days_ago = (datetime.now() - last_date).days
                    if days_ago <= 1:
                        status = "[green]最新[/green]"
                    elif days_ago <= 3:
                        status = "[yellow]較新[/yellow]"
                    else:
                        status = "[red]過舊[/red]"

                table.add_row(
                    row[0] or "未命名",
                    row[1] or "N/A",
                    last_sync,
                    str(total_records),
                    str(recent_records),
                    status,
                )

            console.print(table)
        else:
            console.print("⚠️ [yellow]未找到網站記錄[/yellow]")

        # 3. 顯示最近的詳細同步活動（如果要求顯示）
        if show_recent > 0:
            console.print(f"\n📊 [bold blue]最近 {show_recent} 條同步記錄:[/bold blue]")

            recent_query = """
            SELECT
                pd.date,
                COUNT(*) as records_count,
                AVG(pd.clicks) as avg_clicks,
                AVG(pd.impressions) as avg_impressions
            FROM gsc_performance_data pd
            WHERE pd.site_id = ?
            AND pd.date >= date('now', '-30 days')
            GROUP BY pd.date
            ORDER BY pd.date DESC
            LIMIT ?
            """

            with database_service._lock:
                recent_results = database_service._connection.execute(
                    recent_query, (site_id, site_id, show_recent)
                ).fetchall()

            if recent_results:
                recent_table = Table(show_header=True, header_style="bold cyan")
                recent_table.add_column("網站", style="cyan")
                recent_table.add_column("日期", style="yellow")
                recent_table.add_column("記錄數", justify="right", style="blue")
                recent_table.add_column("平均點擊", justify="right", style="green")
                recent_table.add_column("平均曝光", justify="right", style="magenta")

                for row in recent_results:
                    recent_table.add_row(
                        row[0] or "未命名",
                        row[1],
                        str(row[2]),
                        f"{row[3]:.1f}" if row[3] else "0",
                        f"{row[4]:.1f}" if row[4] else "0",
                    )

                console.print(recent_table)
            else:
                console.print("沒有找到最近的同步記錄")

    except Exception as e:
        console.print(f"❌ [red]查詢資料庫時發生錯誤: {str(e)}[/red]")

    # 4. 提供實用的下一步建議
    console.print("\n💡 [bold green]實用命令:[/bold green]")
    console.print("  gsc-cli sync daily --site-id <ID>      # 同步特定網站")
    console.print('  gsc-cli sync multiple "1 2 3"          # 批次同步多個網站')
    console.print("  gsc-cli sync daily --all-sites         # 同步所有網站")
    console.print("  gsc-cli network-check                  # 檢查網絡連接")
    console.print("  gsc-cli sync status --site-id <ID>     # 查看特定網站狀態")


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
        console.print("3. 如果問題持續，請使用 'just conservative-sync' 命令")
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
