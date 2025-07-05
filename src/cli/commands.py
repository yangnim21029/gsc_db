#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC CLI 命令定義 - 已重構

- 將複雜邏輯委託給後端服務和作業 (jobs)。
- 修復了所有不匹配的方法調用。
- 統一了依賴注入模式。
"""

from datetime import datetime
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from src.containers import Container

from ..analysis.analytics_report_builder import build_report
from ..analysis.interactive_data_visualizer import InteractiveVisualizer
from ..jobs.bulk_data_synchronizer import run_sync
from ..services.database import SyncMode

console = Console()
app = typer.Typer(help="GSC CLI - 企業級 Google Search Console 數據管理工具")
site_app = typer.Typer(help="管理 GSC 網站屬性")
sync_app = typer.Typer(name="sync", help="數據同步相關命令")
analyze_app = typer.Typer(name="analyze", help="數據分析相關命令")
auth_app = typer.Typer(name="auth", help="認證管理相關命令")

# 移除這幾行，我們將在 main.py 中進行註冊
# site_app.add_typer(sync_app)
# site_app.add_typer(analyze_app)


@auth_app.command("login")
def auth_login(ctx: typer.Context):
    """
    執行一次性的 OAuth 認證流程以獲取憑證。
    """
    container: Container = ctx.obj
    console.print("🚀 [bold yellow]啟動 OAuth2 認證流程...[/bold yellow]")
    gsc_client = container.gsc_client()

    auth_url = gsc_client.get_auth_url()

    console.print("\n1. 請將以下 URL 複製到您的瀏覽器中打開，並登入您的 Google 帳戶進行授權：")
    console.print(f"\n[link={auth_url}]{auth_url}[/link]\n")

    console.print(
        "2. 授權後，您將被重定向到一個無法打開的頁面 (這是正常的)。"
        "請從該頁面的瀏覽器地址欄中，複製 `code=` 後面的所有內容。"
    )

    auth_code = typer.prompt("3. 請在此處貼上您複製的授權碼 (code)")

    if not auth_code:
        console.print("[bold red]❌ 未提供授權碼，認證已取消。[/bold red]")
        raise typer.Exit(code=1)

    console.print("\n⏳ [cyan]正在使用授權碼換取憑證...[/cyan]")
    if gsc_client.handle_oauth_callback(auth_code.strip()):
        console.print(
            "[bold green]✅ 認證成功！憑證已保存至 token.json。"
            "您現在可以運行非互動式腳本了。[/bold green]"
        )
    else:
        console.print("[bold red]❌ 認證失敗。請檢查您的授權碼或配置。[/bold red]")
        raise typer.Exit(code=1)


@site_app.command("list")
def list_sites(ctx: typer.Context):
    """列出所有本地數據庫和遠程 GSC 帳戶中的站點。"""
    container: Container = ctx.obj
    site_service = container.site_service()
    gsc_client = container.gsc_client()
    console.print("[bold cyan]--- 遠程 GSC 帳戶站點 ---[/bold cyan]")
    try:
        gsc_sites = gsc_client.get_sites()
        if not gsc_sites:
            console.print("[yellow]在您的 GSC 帳戶中找不到任何站點。[/yellow]")
        else:
            remote_table = Table(title="GSC 遠程站點")
            remote_table.add_column("站點 URL", style="green")
            for site in gsc_sites:
                remote_table.add_row(site)
            console.print(remote_table)
    except Exception as e:
        console.print(f"[red]❌ 無法從 Google API 獲取站點列表: {e}[/red]")

    console.print("\n[bold cyan]--- 本地數據庫站點 ---[/bold cyan]")
    db_sites = site_service.get_all_sites(active_only=False)
    if not db_sites:
        console.print("[yellow]數據庫中沒有任何站點。[/yellow]")
    else:
        local_table = Table(title="本地數據庫站點")
        local_table.add_column("ID", style="cyan")
        local_table.add_column("名稱", style="magenta")
        local_table.add_column("網域", style="green")
        local_table.add_column("狀態", style="yellow")
        for site in db_sites:
            status = "有效" if site["is_active"] else "無效"
            local_table.add_row(str(site["id"]), site["name"], site["domain"], status)
        console.print(local_table)


@site_app.command("add")
def add_site(
    ctx: typer.Context,
    site_url: Annotated[str, typer.Argument(help="要添加的 GSC 網站 URL。")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", help="網站的自定義名稱。如果未提供，將從 URL 生成。"),
    ] = None,
):
    """手動添加一個 GSC 站點到數據庫。"""
    container: Container = ctx.obj
    site_service = container.site_service()
    try:
        site_id = site_service.add_site(domain=site_url, name=name)
        if site_id:
            console.print(f"[green]✅ 站點 '{site_url}' 添加成功，ID: {site_id}[/green]")
        else:
            console.print(f"[yellow]⚠️ 站點 '{site_url}' 可能已存在，未進行添加。[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 添加站點失敗: {e}[/red]")


@site_app.command("cleanup-duplicates", help="清理因 bug 產生的重複站點名稱。")
def cleanup_duplicate_sites(
    ctx: typer.Context,
):
    """
    清理數據庫中 'sc-domain:sc-domain:...' 形式的重複站點。
    """
    container: Container = ctx.obj
    db = container.db_service()
    console.print("[yellow]正在開始清理重複站點...[/yellow]")
    cleaned_count = db.cleanup_duplicate_domains()
    console.print(f"[green]✅ 清理完成！共更新了 {cleaned_count} 個站點。[/green]")


@site_app.command("deactivate-prefixes", help="停用已存在對應 sc-domain 版本的網址前置字元站點。")
def deactivate_prefix_sites(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", help="只顯示將被停用的站點，不執行任何操作。"),
):
    """
    將所有已存在對應 sc-domain 版本的網址前置字元站點設置為 is_active = False。
    這有助於清理數據庫，避免同步多餘的資源。
    """
    container: Container = ctx.obj
    db = container.db_service()
    console.print("[yellow]🔍 正在查找已存在對應 sc-domain 的前綴站點...[/yellow]")

    result = db.deactivate_prefix_sites(dry_run=True)

    # 進行類型檢查和斷言，以解決 linter 錯誤
    import typing

    if not isinstance(result, list):
        console.print(
            f"[bold red]錯誤：預期從數據庫獲取列表，但得到了意外的類型: {type(result)}[/bold red]"
        )
        raise typer.Exit(1)

    sites_to_deactivate: typing.List[typing.Dict[str, typing.Any]] = result

    if not sites_to_deactivate:
        console.print("[green]✅ 沒有找到任何需要停用的網址前置字元站點。[/green]")
        return

    table = Table(title="將被停用的站點")
    table.add_column("ID", style="cyan")
    table.add_column("Domain", style="magenta")
    for site in sites_to_deactivate:
        table.add_row(str(site["id"]), site["domain"])
    console.print(table)

    if dry_run:
        console.print("\n[bold yellow]--dry-run 模式，未執行任何操作。[/bold yellow]")
        return

    if typer.confirm("\n你確定要停用以上所有站點嗎？"):
        deactivated_count = db.deactivate_prefix_sites(dry_run=False)
        console.print(f"\n[bold green]✅ 成功停用了 {deactivated_count} 個站點。[/bold green]")
    else:
        console.print("[bold red]操作已取消。[/bold red]")


@sync_app.command("daily")
def sync_daily(
    ctx: typer.Context,
    site_url: Annotated[Optional[str], typer.Option("--site-url")] = None,
    site_id: Annotated[Optional[int], typer.Option("--site-id")] = None,
    all_sites: Annotated[bool, typer.Option("--all-sites")] = False,
    start_date: Annotated[Optional[str], typer.Option("--start-date")] = None,
    end_date: Annotated[Optional[str], typer.Option("--end-date")] = None,
    days: Annotated[int, typer.Option("--days")] = 7,
    retries: Annotated[int, typer.Option()] = 3,
    retry_delay: Annotated[int, typer.Option()] = 5,
    sync_mode: Annotated[SyncMode, typer.Option()] = SyncMode.SKIP,
    resume: Annotated[bool, typer.Option("--resume")] = False,
):
    """從 GSC 同步每日數據到本地數據庫。"""
    container: Container = ctx.obj
    db = container.db_service()
    client = container.gsc_client()
    run_sync(
        db=db,
        client=client,
        site_url=site_url,
        site_id=site_id,
        all_sites=all_sites,
        start_date=start_date,
        end_date=end_date,
        days=days,
        retries=retries,
        retry_delay=retry_delay,
        sync_mode=sync_mode,
        resume=resume,
    )


@analyze_app.command("report")
def analyze_report(
    ctx: typer.Context,
    site_id: Annotated[int, typer.Option(help="要生成報告的網站 ID。")],
    output_path: Annotated[str, typer.Option()] = "gsc_report.md",
    days: Annotated[int, typer.Option()] = 30,
    no_plots: Annotated[bool, typer.Option("--no-plots")] = False,
    plot_dir: Annotated[Optional[str], typer.Option()] = None,
):
    """生成 GSC 數據分析報告。"""
    container: Container = ctx.obj
    analysis_service = container.analysis_service()
    console.print(f"🚀 開始為站點 ID {site_id} 生成報告...")
    result = build_report(
        analysis_service=analysis_service,
        site_id=site_id,
        output_path=output_path,
        days=days,
        include_plots=not no_plots,
        plot_save_dir=plot_dir,
    )
    if result.get("success"):
        console.print(f"[green]✅ 報告已成功生成於: {result.get('output_path')}[/green]")
    else:
        errors = result.get("errors", ["未知錯誤"])
        console.print(f"[red]❌ 報告生成失敗: {', '.join(map(str, errors))}[/red]")


@analyze_app.command("interactive")
def analyze_interactive(
    ctx: typer.Context,
    site_id: Annotated[
        Optional[int],
        typer.Option("--site-id", help="要進行可視化分析的網站 ID。如果未提供，將會提示選擇。"),
    ] = None,
    days: Annotated[int, typer.Option("--days", help="要分析的過去天數。")] = 30,
):
    """🎨 啟動交互式數據可視化儀表板。"""
    container: Container = ctx.obj
    analysis_service = container.analysis_service()
    console.print("🎨 啟動交互式可視化...", style="cyan")
    visualizer = InteractiveVisualizer(analysis_service)
    visualizer.run(site_id=site_id, days=days)


def _calculate_coverage_percentage(coverage_data: Dict[str, Any]) -> Optional[str]:
    """計算並格式化數據覆蓋率百分比"""
    first_date_str = coverage_data.get("first_date")
    last_date_str = coverage_data.get("last_date")
    unique_dates = coverage_data.get("unique_dates", 0)

    if first_date_str and last_date_str and unique_dates > 0:
        try:
            first_date = datetime.strptime(first_date_str, "%Y-%m-%d").date()
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            total_days = (last_date - first_date).days + 1
            percentage = (unique_dates / total_days) * 100 if total_days > 0 else 0
            return f"{percentage:.1f}% ({unique_dates} / {total_days} 天)"
        except (ValueError, TypeError):
            return None
    return None


def _print_coverage_for_site(db, site: Dict[str, Any]):
    """為單個站點打印數據覆蓋情況。"""
    console.print(Panel(f"[bold]站點: {site['name']} (ID: {site['id']})[/bold]", expand=False))

    daily_coverage = db.get_daily_data_coverage(site["id"])
    hourly_coverage = db.get_hourly_data_coverage(site["id"])

    table = Table(title="數據覆蓋情況")
    table.add_column("數據類型", style="cyan")
    table.add_column("總記錄數", style="magenta")
    table.add_column("最早日期", style="green")
    table.add_column("最晚日期", style="green")
    table.add_column("覆蓋率", style="yellow")

    if daily_coverage:
        table.add_row(
            "每日數據",
            str(daily_coverage.get("total_records", "N/A")),
            str(daily_coverage.get("first_date", "N/A")),
            str(daily_coverage.get("last_date", "N/A")),
            _calculate_coverage_percentage(daily_coverage) or "N/A",
        )
    else:
        table.add_row("每日數據", "[red]無[/red]", "N/A", "N/A", "N/A")

    if hourly_coverage:
        table.add_row(
            "每小時數據",
            str(hourly_coverage.get("total_records", "N/A")),
            str(hourly_coverage.get("first_date", "N/A")),
            str(hourly_coverage.get("last_date", "N/A")),
            _calculate_coverage_percentage(hourly_coverage) or "N/A",
        )
    else:
        table.add_row("每小時數據", "[red]無[/red]", "N/A", "N/A", "N/A")

    console.print(table)


@analyze_app.command("coverage")
def analyze_coverage(
    ctx: typer.Context,
    site_id: Annotated[Optional[int], typer.Argument(help="要檢查數據覆蓋率的站點 ID。")] = None,
    all_sites: Annotated[
        bool, typer.Option("--all", "-a", help="檢查所有站點的數據覆蓋率。")
    ] = False,
):
    """檢查一個或所有站點的數據覆蓋率。"""
    container: Container = ctx.obj
    db = container.db_service()
    site_service = container.site_service()

    if site_id is None and not all_sites:
        console.print("[bold red]錯誤：請提供一個站點 ID 或使用 --all 選項。[/bold red]")
        raise typer.Exit(code=1)

    if site_id:
        site = site_service.get_site_by_id(site_id)
        if not site:
            console.print(f"[bold red]錯誤：找不到 ID 為 {site_id} 的站點。[/bold red]")
            raise typer.Exit(code=1)
        sites_to_check = [site]
    else:  # all_sites is True
        sites_to_check = site_service.get_all_sites(active_only=False)

    for site in sites_to_check:
        _print_coverage_for_site(db, site)
        console.print()


@analyze_app.command("compare")
def compare_performance(
    ctx: typer.Context,
    site_id: Annotated[int, typer.Argument(help="要比較的站點 ID。")],
    period1_start: Annotated[str, typer.Argument(help="第一時段開始日期 (YYYY-MM-DD)。")],
    period1_end: Annotated[str, typer.Argument(help="第一時段結束日期 (YYYY-MM-DD)。")],
    period2_start: Annotated[str, typer.Argument(help="第二時段開始日期 (YYYY-MM-DD)。")],
    period2_end: Annotated[str, typer.Argument(help="第二時段結束日期 (YYYY-MM-DD)。")],
    group_by: Annotated[str, typer.Option(help="分組依據 ('query' 或 'page')")] = "query",
    limit: Annotated[int, typer.Option()] = 10,
):
    """比較兩個時間段的性能數據。"""
    container: Container = ctx.obj
    analysis_service = container.analysis_service()
    try:
        comparison_data = analysis_service.compare_performance_periods(
            site_id=site_id,
            period1_start=period1_start,
            period1_end=period1_end,
            period2_start=period2_start,
            period2_end=period2_end,
            group_by=group_by,
            limit=limit,
        )

        if not comparison_data:
            console.print("[yellow]沒有找到可用於比較的數據。[/yellow]")
            return

        table = Table(title=f"性能對比: {group_by.capitalize()} 表現 Top {limit}")
        table.add_column("排名", style="cyan")
        table.add_column(group_by.capitalize(), style="magenta", max_width=50, overflow="ellipsis")
        table.add_column("點擊變化 (Δ)", style="green", justify="right")
        table.add_column("曝光變化 (Δ)", style="blue", justify="right")
        table.add_column("排名變化 (Δ)", style="red", justify="right")
        table.add_column("詳情 (時段1 -> 時段2)", style="dim")

        for i, item in enumerate(comparison_data):
            pos_change = item["position_change"]
            pos_str = f"{pos_change:+.2f}" if pos_change is not None else "N/A"

            table.add_row(
                str(i + 1),
                item["item"],
                f"{item['clicks_change']:+.0f}",
                f"{item['impressions_change']:+.0f}",
                pos_str,
                f"點擊: {item['period1_clicks'] or 0:.0f} -> {item['period2_clicks'] or 0:.0f}",
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]❌ 比較性能數據失敗: {e}[/red]")
