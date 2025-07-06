#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC CLI 命令定義 - 已重構

- 將複雜邏輯委託給後端服務和作業 (jobs)。
- 修復了所有不匹配的方法調用。
- 統一了依賴注入模式。
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from src.config import settings
from src.containers import Container
from src.utils.rich_console import console

from ..analysis.interactive_data_visualizer import InteractiveVisualizer
from ..services.database import SyncMode

app = typer.Typer(help="GSC CLI - 企業級 Google Search Console 數據管理工具")
# --- 1. 認證 (Auth) App ---
auth_app = typer.Typer(help="管理 Google API 認證。")


@auth_app.command("login", help="執行 OAuth 2.0 流程以取得 Google API 的授權。")
def auth_login(
    ctx: typer.Context,
):
    container: Container = ctx.obj
    gsc_client = container.gsc_client()
    if gsc_client.authenticate():
        console.print("✅ 認證流程成功完成。")
    else:
        console.print("❌ 認證流程失敗或被取消。")
        raise typer.Exit(code=1)


# --- 2. 網站 (Site) App ---
site_app = typer.Typer(help="管理 GSC 網站資源。")


@site_app.command("list", help="列出所有可用的 GSC 網站。")
def site_list(
    ctx: typer.Context,
):
    container: Container = ctx.obj
    site_service = container.site_service()
    gsc_client = container.gsc_client()

    # --- 顯示遠程站點 ---
    console.print("\n[bold cyan]--- 🌏 遠程 GSC 帳戶站點 ---[/bold cyan]")
    try:
        remote_sites = gsc_client.get_sites()
        if not remote_sites:
            console.print("[yellow]在您的 GSC 帳戶中找不到任何站點。[/yellow]")
        else:
            remote_table = Table(title="GSC 遠程站點")
            remote_table.add_column("站點 URL", style="green")
            for site_url in remote_sites:
                remote_table.add_row(site_url)
            console.print(remote_table)
    except Exception as e:
        console.print(f"[red]❌ 無法從 Google API 獲取站點列表: {e}[/red]")

    # --- 顯示本地站點 ---
    console.print("\n[bold blue]--- 💾 本地數據庫站點 ---[/bold blue]")
    local_sites = site_service.get_all_sites(active_only=False)
    if not local_sites:
        console.print("[yellow]數據庫中沒有任何站點。[/yellow]")
    else:
        local_table = Table(title="本地數據庫站點")
        local_table.add_column("ID", style="cyan")
        local_table.add_column("名稱", style="magenta")
        local_table.add_column("網域", style="green")
        local_table.add_column("狀態", style="yellow")
        for site_dict in local_sites:
            status = "✅ 有效" if site_dict["is_active"] else "❌ 無效"
            local_table.add_row(
                str(site_dict["id"]), site_dict["name"], site_dict["domain"], status
            )
        console.print(local_table)


@site_app.command("add", help="新增一個網站到資料庫。")
def site_add(
    ctx: typer.Context,
    site_url: str = typer.Argument(..., help="要新增的網站 URL，例如 'sc-domain:example.com'"),
    name: str = typer.Option(None, "--name", "-n", help="網站的自訂名稱。"),
):
    container: Container = ctx.obj
    site_service = container.site_service()
    new_site_id = site_service.add_site(domain=site_url, name=name)
    if new_site_id:
        # 如果提供了 name，就用它，否則用 site_url
        display_name = name if name else site_url
        console.print(
            f"✅ 站點 '[bold green]{display_name}[/bold green]' 添加成功，ID: {new_site_id}"
        )
    else:
        console.print(f"⚠️ 站點 '[yellow]{site_url}[/yellow]' 可能已存在，未進行添加。")


@site_app.command("cleanup-duplicates", help="清理因 bug 產生的重複站點名稱。")
def cleanup_duplicate_sites(
    ctx: typer.Context,
):
    """
    清理數據庫中 'sc-domain:sc-domain:...' 形式的重複站點。
    """
    container: Container = ctx.obj
    db_service = container.db_service()
    console.print("[yellow]正在開始清理重複站點...[/yellow]")
    cleaned_count = db_service.cleanup_duplicate_domains()
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
    db_service = container.db_service()
    console.print("[yellow]🔍 正在查找已存在對應 sc-domain 的前綴站點...[/yellow]")

    result = db_service.deactivate_prefix_sites(dry_run=True)

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
        deactivated_count = db_service.deactivate_prefix_sites(dry_run=False)
        console.print(f"\n[bold green]✅ 成功停用了 {deactivated_count} 個站點。[/bold green]")
    else:
        console.print("[bold red]操作已取消。[/bold red]")


# --- 3. 同步 (Sync) App ---
sync_app = typer.Typer(help="與 GSC API 同步數據。")


@sync_app.command("daily", help="執行每日數據同步。")
def sync_daily(
    ctx: typer.Context,
    all_sites: bool = typer.Option(
        False, "--all-sites", help="為資料庫中所有已啟用的網站進行同步。"
    ),
    site_id: int = typer.Option(None, "--site-id", help="指定要同步的網站 ID。"),
    days: int = typer.Option(
        2,
        "--days",
        "-d",
        help="要回溯同步的天數 (預設為 2，即昨天和前天)。",
        min=1,
    ),
    max_workers: int = typer.Option(
        settings.sync.max_workers,
        "--max-workers",
        help="並行處理的最大線程數。",
        min=1,
    ),
    sync_mode: SyncMode = typer.Option(
        SyncMode.replace,
        "--sync-mode",
        help="同步模式：replace (覆蓋) 或 skip (跳過)。",
        case_sensitive=False,
    ),
    start_date: Optional[datetime] = typer.Option(
        None,
        "--start-date",
        formats=["%Y-%m-%d"],
        help="同步的開始日期 (YYYY-MM-DD)。",
    ),
    end_date: Optional[datetime] = typer.Option(
        None,
        "--end-date",
        formats=["%Y-%m-%d"],
        help="同步的結束日期 (YYYY-MM-DD)。",
    ),
):
    container: Container = ctx.obj
    synchronizer = container.bulk_data_synchronizer()
    synchronizer.run_sync(
        all_sites=all_sites,
        site_id=site_id,
        days=days,
        start_date=start_date.date() if start_date else None,
        end_date=end_date.date() if end_date else None,
        sync_mode=sync_mode,
        max_workers=max_workers,
    )


# --- 4. 分析 (Analyze) App ---
analyze_app = typer.Typer(help="分析已同步的 GSC 數據。")


@analyze_app.command("coverage", help="計算並顯示指定網站的數據覆蓋率。")
def analyze_coverage(
    ctx: typer.Context,
    all_sites: bool = typer.Option(False, "--all", help="分析所有站點的覆蓋率。"),
    site_id: int = typer.Option(None, "--site-id", help="要分析的單個站點 ID。"),
    output_csv: bool = typer.Option(False, "--csv", help="將結果輸出為 CSV 檔案。"),
):
    container: Container = ctx.obj
    analyzer = container.hourly_performance_analyzer()

    if not any([all_sites, site_id]):
        console.print("錯誤：請提供一個站點 ID 或使用 --all 選項。")
        raise typer.Exit(code=1)

    analyzer.analyze_and_display_coverage(
        all_sites=all_sites, site_id=site_id, output_csv=output_csv
    )


@analyze_app.command("report", help="生成指定站點的 GSC 綜合表現報告。")
def analyze_report(
    ctx: typer.Context,
    site_id: int = typer.Option(..., "--site-id", help="要生成報告的網站 ID。"),
    output_path: Path = typer.Option("report.md", "--output-path", help="報告的輸出檔案路徑。"),
    include_plots: bool = typer.Option(True, "--plots/--no-plots", help="是否在報告中包含圖表。"),
    plot_save_dir: Optional[Path] = typer.Option(
        None, "--plot-dir", help="圖表檔案的儲存目錄 (預設為輸出路徑的同級目錄)。"
    ),
):
    container: Container = ctx.obj
    analysis_service = container.analysis_service()

    if not plot_save_dir:
        plot_save_dir = output_path.parent

    console.print(f"🚀 開始為網站 ID {site_id} 生成報告...")
    # 注意：我們現在從 analysis_service 中調用 build_report
    result = analysis_service.build_report(
        site_id=site_id,
        output_path=str(output_path),
        include_plots=include_plots,
        plot_save_dir=str(plot_save_dir),
    )

    if result["success"]:
        console.print(f"✅ 報告成功生成於: [cyan]{result['path']}[/cyan]")
    else:
        console.print(f"❌ 報告生成失敗: {result['error']}")
        raise typer.Exit(code=1)


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
