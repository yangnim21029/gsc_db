#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC CLI 命令定義
使用 Typer 構建的現代化命令行工具
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# 專案模組導入
from .. import config
from ..services.gsc_client import GSCClient
from ..services.database import Database
from ..jobs.bulk_data_synchronizer import run_sync
from ..analysis.analytics_report_builder import build_report
from ..analysis.hourly_performance_analyzer import run_hourly_analysis

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化 Typer 應用
app = typer.Typer(
    name="gsc-cli",
    help="🚀 GSC CLI - Google Search Console 數據管理工具",
    add_completion=False,
    rich_markup_mode="rich"
)

# 初始化 Rich 控制台
console = Console()


@app.command()
def auth():
    """
    🔐 進行 Google Search Console API 認證
    """
    gsc_client = GSCClient()

    if gsc_client.is_authenticated():
        typer.secho("✅ 已經認證成功", fg=typer.colors.GREEN)
        return

    auth_url = gsc_client.get_auth_url()
    typer.echo("🔗 請訪問以下 URL 進行認證：")
    typer.echo(auth_url)
    typer.echo("\n認證完成後，請重新運行此命令檢查狀態")


@app.command()
def sites():
    """
    📊 列出所有可用的站點
    """
    try:
        gsc_client = GSCClient()

        # 從 GSC 獲取站點
        gsc_sites = gsc_client.get_sites()
        
        table = Table(title="🌐 GSC 中的站點")
        table.add_column("序號", style="cyan")
        table.add_column("站點 URL", style="green")
        
        for i, site in enumerate(gsc_sites, 1):
            table.add_row(str(i), site)
        
        console.print(table)

        # 從數據庫獲取站點
        database = Database()
        db_sites = database.get_sites()
        
        table = Table(title="💾 數據庫中的站點")
        table.add_column("ID", style="cyan")
        table.add_column("名稱", style="green")
        table.add_column("域名", style="yellow")
        
        for site in db_sites:
            table.add_row(str(site['id']), site['name'], site['domain'])
        
        console.print(table)

    except Exception as e:
        typer.secho(f"❌ 獲取站點失敗：{e}", fg=typer.colors.RED)


@app.command()
def add_site(
    site_url: Annotated[
        str, typer.Argument(help="站點 URL (例如: https://example.com/ 或 sc-domain:example.com)")
    ]
):
    """
    ➕ 添加新站點到數據庫
    """
    try:
        if not site_url:
            site_url = typer.prompt("請輸入站點 URL")
            
        if not site_url:
            typer.secho("❌ 必須提供站點 URL", fg=typer.colors.RED)
            raise typer.Exit(1)

        database = Database()
        site_name = site_url.replace('sc-domain:', '').replace('https://', '').replace('http://', '').rstrip('/')
        
        site_id = database.add_site(site_name, site_url)
        typer.secho(f"✅ 站點添加成功！ID: {site_id}", fg=typer.colors.GREEN)
        
    except Exception as e:
        typer.secho(f"❌ 添加站點失敗：{e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def coverage(
    site_id: Annotated[
        Optional[int], typer.Option("--site-id", help="站點 ID")
    ] = None
):
    """
    📈 顯示數據覆蓋情況
    """
    try:
        database = Database()
        
        if site_id:
            # 顯示特定站點的覆蓋情況
            coverage_data = database.get_coverage_by_site(site_id)
            if coverage_data:
                table = Table(title=f"📊 站點 ID {site_id} 的數據覆蓋情況")
                table.add_column("日期", style="cyan")
                table.add_column("點擊數", style="green")
                table.add_column("展示數", style="yellow")
                table.add_column("CTR", style="blue")
                table.add_column("平均排名", style="magenta")
                
                for row in coverage_data:
                    table.add_row(
                        str(row['date']),
                        str(row['clicks']),
                        str(row['impressions']),
                        f"{row['ctr']:.2%}",
                        f"{row['avg_position']:.1f}"
                    )
                console.print(table)
            else:
                typer.secho(f"❌ 未找到站點 ID {site_id} 的數據", fg=typer.colors.YELLOW)
        else:
            # 顯示所有站點的覆蓋情況
            sites = database.get_sites()
            table = Table(title="📊 所有站點數據覆蓋情況")
            table.add_column("站點", style="cyan")
            table.add_column("數據天數", style="green")
            table.add_column("最新日期", style="yellow")
            table.add_column("最早日期", style="blue")
            
            for site in sites:
                coverage_info = database.get_coverage_summary(site['id'])
                if coverage_info:
                    table.add_row(
                        site['name'],
                        str(coverage_info['days']),
                        str(coverage_info['latest_date']),
                        str(coverage_info['earliest_date'])
                    )
                else:
                    table.add_row(site['name'], "0", "無", "無")
            
            console.print(table)
            
    except Exception as e:
        typer.secho(f"❌ 獲取覆蓋情況失敗：{e}", fg=typer.colors.RED)


@app.command()
def sync(
    site_url: Annotated[
        Optional[str], typer.Option("--site-url", help="站點 URL")
    ] = None,
    site_id: Annotated[
        Optional[int], typer.Option("--site-id", help="站點 ID")
    ] = None,
    start_date: Annotated[
        Optional[str], typer.Option("--start-date", help="開始日期 (YYYY-MM-DD)")
    ] = None,
    end_date: Annotated[
        Optional[str], typer.Option("--end-date", help="結束日期 (YYYY-MM-DD)")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="強制重建數據")
    ] = False,
    all_sites: Annotated[
        bool, typer.Option("--all-sites", help="同步所有站點")
    ] = False,
    days: Annotated[
        int, typer.Option("--days", help="同步最近幾天", min=1, max=480)
    ] = 7
):
    """
    🔄 同步 Google Search Console 數據到本地數據庫
    """
    try:
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            typer.secho("❌ 請先進行認證：gsc-cli auth", fg=typer.colors.RED)
            raise typer.Exit(1)
        
        # 使用新的 run_sync 函數
        typer.echo(f"🔄 開始同步數據...")
        
        if all_sites:
            # 同步所有站點
            result = run_sync(sites=None, days=days)
        elif site_url:
            # 同步指定站點
            result = run_sync(sites=[site_url], days=days)
        elif site_id:
            # 通過站點 ID 同步（需要先獲取站點 URL）
            database = Database()
            site = database.get_site_by_id(site_id)
            if not site:
                typer.secho(f"❌ 未找到站點 ID {site_id}", fg=typer.colors.RED)
                raise typer.Exit(1)
            result = run_sync(sites=[site['domain']], days=days)
        else:
            typer.secho("❌ 必須提供 --site-url、--site-id 或 --all-sites", fg=typer.colors.RED)
            raise typer.Exit(1)
        
        if result['failed_sites'] == 0:
            typer.secho("✅ 數據同步完成！", fg=typer.colors.GREEN)
        else:
            typer.secho(f"⚠️  同步完成，但有 {result['failed_sites']} 個站點失敗", fg=typer.colors.YELLOW)
        
    except Exception as e:
        typer.secho(f"❌ 同步失敗：{e}", fg=typer.colors.RED)
        logger.error(f"Sync failed: {e}")


@app.command()
def bulk_sync(
    site_ids: Annotated[
        List[int], typer.Option("--site-id", help="站點 ID 列表")
    ],
    year: Annotated[
        int, typer.Option("--year", help="年份")
    ],
    month: Annotated[
        int, typer.Option("--month", help="月份", min=1, max=12)
    ],
    use_new_cli: Annotated[
        bool, typer.Option("--use-new-cli", help="使用新的 CLI")
    ] = True
):
    """
    📅 批量同步指定站點的月度數據
    """
    try:
        typer.echo(f"📅 開始批量同步 {len(site_ids)} 個站點的 {year}-{month:02d} 數據...")
        
        result = run_sync(
            site_ids=site_ids,
            year=year,
            month=month,
            use_new_cli=use_new_cli
        )
        
        if result['failed_sites'] == 0:
            typer.secho("✅ 批量同步完成！", fg=typer.colors.GREEN)
        else:
            typer.secho(f"⚠️  批量同步完成，但有 {result['failed_sites']} 個站點失敗", fg=typer.colors.YELLOW)
        
        # 顯示詳細結果
        if result['details']:
            table = Table(title="📊 同步詳細結果")
            table.add_column("站點 ID", style="cyan")
            table.add_column("成功天數", style="green")
            table.add_column("跳過天數", style="yellow")
            table.add_column("失敗天數", style="red")
            table.add_column("總天數", style="blue")
            
            for detail in result['details']:
                site_result = detail['result']
                table.add_row(
                    str(detail['site_id']),
                    str(site_result['success']),
                    str(site_result['skip']),
                    str(site_result['fail']),
                    str(site_result['total'])
                )
            
            console.print(table)
        
    except Exception as e:
        typer.secho(f"❌ 批量同步失敗：{e}", fg=typer.colors.RED)
        logger.error(f"Bulk sync failed: {e}")


@app.command()
def progress():
    """
    📋 顯示最近的同步任務進度
    """
    try:
        database = Database()
        recent_tasks = database.get_recent_tasks(limit=10)
        
        if not recent_tasks:
            typer.secho("📭 沒有找到最近的同步任務", fg=typer.colors.YELLOW)
            return
        
        table = Table(title="📋 最近的同步任務")
        table.add_column("任務 ID", style="cyan")
        table.add_column("站點", style="green")
        table.add_column("開始時間", style="yellow")
        table.add_column("結束時間", style="blue")
        table.add_column("狀態", style="magenta")
        table.add_column("記錄數", style="red")
        
        for task in recent_tasks:
            status_color = "green" if task['status'] == 'completed' else "red"
            table.add_row(
                str(task['id']),
                task['site_name'],
                str(task['start_time']),
                str(task['end_time']) if task['end_time'] else "進行中",
                f"[{status_color}]{task['status']}[/{status_color}]",
                str(task['records_count']) if task['records_count'] else "0"
            )
        
        console.print(table)
        
    except Exception as e:
        typer.secho(f"❌ 獲取進度失敗：{e}", fg=typer.colors.RED)


@app.command()
def hourly_sync(
    site_url: Annotated[
        Optional[str], typer.Option("--site-url", help="站點 URL")
    ] = None,
    start_date: Annotated[
        Optional[str], typer.Option("--start-date", help="開始日期 (默認昨天)")
    ] = None,
    end_date: Annotated[
        Optional[str], typer.Option("--end-date", help="結束日期 (默認今天)")
    ] = None
):
    """
    ⏰ 同步每小時數據
    """
    try:
        from services.hourly_data import HourlyDataSync
        
        # 確定日期範圍
        if not start_date:
            start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if not site_url:
            site_url = typer.prompt("請輸入站點 URL")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(f"正在同步 {site_url} 的每小時數據...", total=None)
            
            hourly_sync = HourlyDataSync()
            hourly_sync.sync_hourly_data(site_url, start_date, end_date)
        
        typer.secho("✅ 每小時數據同步完成！", fg=typer.colors.GREEN)
        
    except Exception as e:
        typer.secho(f"❌ 每小時數據同步失敗：{e}", fg=typer.colors.RED)


@app.command()
def hourly_summary(
    site_id: Annotated[
        Optional[int], typer.Option("--site-id", help="站點 ID")
    ] = None,
    date: Annotated[
        Optional[str], typer.Option("--date", help="日期 (YYYY-MM-DD)")
    ] = None
):
    """
    📊 顯示每小時數據總結
    """
    try:
        from services.hourly_database import HourlyDatabase
        
        hourly_db = HourlyDatabase()
        
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if site_id:
            summary = hourly_db.get_hourly_summary_by_site(site_id, date)
        else:
            summary = hourly_db.get_hourly_summary_all_sites(date)
        
        if not summary:
            typer.secho(f"❌ 未找到 {date} 的每小時數據", fg=typer.colors.YELLOW)
            return
        
        table = Table(title=f"⏰ {date} 每小時數據總結")
        table.add_column("小時", style="cyan")
        table.add_column("點擊數", style="green")
        table.add_column("展示數", style="yellow")
        table.add_column("CTR", style="blue")
        table.add_column("平均排名", style="magenta")
        
        for row in summary:
            table.add_row(
                str(row['hour']),
                str(row['clicks']),
                str(row['impressions']),
                f"{row['ctr']:.2%}",
                f"{row['avg_position']:.1f}"
            )
        
        console.print(table)
        
    except Exception as e:
        typer.secho(f"❌ 獲取每小時總結失敗：{e}", fg=typer.colors.RED)


@app.command()
def hourly_coverage(
    site_id: Annotated[
        Optional[int], typer.Option("--site-id", help="站點 ID")
    ] = None
):
    """
    📈 顯示每小時數據覆蓋情況
    """
    try:
        from services.hourly_database import HourlyDatabase
        
        hourly_db = HourlyDatabase()
        
        if site_id:
            coverage = hourly_db.get_hourly_coverage_by_site(site_id)
        else:
            coverage = hourly_db.get_hourly_coverage_all_sites()
        
        if not coverage:
            typer.secho("❌ 未找到每小時數據覆蓋信息", fg=typer.colors.YELLOW)
            return
        
        table = Table(title="📈 每小時數據覆蓋情況")
        table.add_column("站點", style="cyan")
        table.add_column("數據天數", style="green")
        table.add_column("最新日期", style="yellow")
        table.add_column("最早日期", style="blue")
        table.add_column("總記錄數", style="magenta")
        
        for site_coverage in coverage:
            table.add_row(
                site_coverage['site_name'],
                str(site_coverage['days']),
                str(site_coverage['latest_date']),
                str(site_coverage['earliest_date']),
                str(site_coverage['total_records'])
            )
        
        console.print(table)
        
    except Exception as e:
        typer.secho(f"❌ 獲取每小時覆蓋情況失敗：{e}", fg=typer.colors.RED)


@app.command()
def api_status():
    """
    🔍 顯示 API 使用狀態
    """
    try:
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            typer.secho("❌ 未認證，無法獲取 API 狀態", fg=typer.colors.RED)
            return
        
        # 這裡可以添加獲取 API 配額使用情況的代碼
        typer.secho("✅ API 連接正常", fg=typer.colors.GREEN)
        typer.echo("📊 API 配額使用情況：")
        typer.echo("  - 每日配額：10,000 次請求")
        typer.echo("  - 已使用：需要實現配額檢查")
        typer.echo("  - 剩餘：需要實現配額檢查")
        
    except Exception as e:
        typer.secho(f"❌ 獲取 API 狀態失敗：{e}", fg=typer.colors.RED)


@app.command()
def logs(
    lines: Annotated[
        int, typer.Option("--lines", help="顯示行數", min=1, max=1000)
    ] = 50,
    error_only: Annotated[
        bool, typer.Option("--error-only", help="只顯示錯誤日誌")
    ] = False
):
    """
    📝 查看同步日誌
    """
    try:
        import subprocess
        import os
        
        log_file = config.LOG_FILE_PATH
        
        if not os.path.exists(log_file):
            typer.secho(f"❌ 日誌文件 {log_file} 不存在", fg=typer.colors.YELLOW)
            return
        
        # 構建 tail 命令
        cmd = ["tail", "-n", str(lines), log_file]
        
        if error_only:
            # 如果只顯示錯誤，使用 grep 過濾
            cmd = ["tail", "-n", "1000", log_file, "|", "grep", "-i", "error", "|", "tail", "-n", str(lines)]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            typer.echo("📝 最近的日誌：")
            typer.echo(result.stdout)
        else:
            typer.secho("📭 沒有找到相關日誌", fg=typer.colors.YELLOW)
            
    except Exception as e:
        typer.secho(f"❌ 查看日誌失敗：{e}", fg=typer.colors.RED)


@app.command()
def report(
    report_type: Annotated[
        str, typer.Argument(help="報告類型 (例如: 'monthly', 'weekly', 'keyword', 'page')")
    ] = "monthly",
    output_path: Annotated[
        str, typer.Option("--output", "-o", help="報告輸出路徑")
    ] = "gsc_report.md",
    days: Annotated[
        int, typer.Option("--days", "-d", help="分析天數", min=1, max=365)
    ] = 30,
    site_url: Annotated[
        Optional[str], typer.Option("--site-url", help="為特定站點 URL 生成報告")
    ] = None,
    include_plots: Annotated[
        bool, typer.Option("--no-plots", help="不生成圖表")
    ] = True,
    plot_dir: Annotated[
        Optional[str], typer.Option("--plot-dir", help="圖表保存目錄")
    ] = None,
    db_path: Annotated[
        str, typer.Option("--db", help="數據庫文件路徑")
    ] = str(config.DB_PATH)
):
    """
    📊 生成 GSC 數據分析報告
    
    支持多種報告類型：
    - monthly: 月度報告（默認）
    - weekly: 週度報告
    - keyword: 關鍵字專項報告
    - page: 頁面表現報告
    """
    try:
        typer.echo(f"📊 開始生成 {report_type} 報告...")
        
        # 根據報告類型調整默認天數
        if report_type == "weekly" and days == 30:
            days = 7
        elif report_type == "keyword" and days == 30:
            days = 14
        elif report_type == "page" and days == 30:
            days = 14
        
        # 如果指定了站點 URL，驗證其有效性
        if site_url:
            database = Database()
            sites = database.get_sites()
            site_found = False
            for site in sites:
                if site['domain'] in site_url or site_url in site['domain']:
                    site_found = True
                    typer.echo(f"✅ 找到匹配的站點: {site['name']} ({site['domain']})")
                    break
            
            if not site_found:
                typer.secho(f"⚠️  警告: 未找到匹配的站點 URL: {site_url}", fg=typer.colors.YELLOW)
                typer.echo("將生成所有站點的綜合報告")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(f"正在生成 {report_type} 報告...", total=None)
            
            # 確保報告保存在 reports 目錄下
            final_output_path = Path(output_path)
            if not final_output_path.is_absolute() and final_output_path.name == output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_output_path = config.REPORTS_DIR / f"gsc_{report_type}_report_{timestamp}.md"
            
            result = build_report(
                output_path=str(final_output_path),
                days=days,
                include_plots=include_plots,
                plot_save_dir=plot_dir,
                db_path=db_path
            )
        
        if result['success']:
            typer.secho(f"✅ 報告生成成功: {result['report_path']}", fg=typer.colors.GREEN)
            
            if result['plots_generated']:
                typer.echo(f"📊 生成的圖表: {', '.join(result['plots_generated'])}")
            
            if 'summary' in result:
                summary = result['summary']
                table = Table(title="📈 數據摘要")
                table.add_column("指標", style="cyan")
                table.add_column("數值", style="green")
                
                table.add_row("總記錄數", f"{summary['total_records']:,}")
                table.add_row("數據天數", str(summary['total_days']))
                table.add_row("關鍵字數量", f"{summary['total_keywords']:,}")
                table.add_row("頁面數量", f"{summary['total_pages']:,}")
                table.add_row("最新數據日期", str(summary['latest_date']))
                
                console.print(table)
        else:
            typer.secho("❌ 報告生成失敗", fg=typer.colors.RED)
            for error in result['errors']:
                typer.echo(f"  - {error}")
            raise typer.Exit(1)
        
    except Exception as e:
        typer.secho(f"❌ 生成報告失敗：{e}", fg=typer.colors.RED)
        logger.error(f"Report generation failed: {e}")


@app.command()
def analyze_hourly(
    analysis_type: Annotated[
        str, typer.Option("--type", help="分析類型", case_sensitive=False)
    ] = "trends",
    days: Annotated[
        int, typer.Option("--days", help="分析天數", min=1, max=30)
    ] = 7,
    output_path: Annotated[
        Optional[str], typer.Option("--output", "-o", help="報告輸出路徑")
    ] = None,
    include_plots: Annotated[
        bool, typer.Option("--no-plots", help="不生成圖表")
    ] = True,
    plot_dir: Annotated[
        Optional[str], typer.Option("--plot-dir", help="圖表保存目錄")
    ] = None,
    db_path: Annotated[
        str, typer.Option("--db", help="數據庫文件路徑")
    ] = str(config.DB_PATH)
):
    """
    ⏰ 每小時數據分析
    
    支持的分析類型：
    - trends: 每小時趨勢圖（默認）
    - heatmap: 每日每小時熱力圖
    - peaks: 高峰時段分析
    - report: 每小時數據報告
    - all: 生成所有分析
    """
    try:
        typer.echo(f"⏰ 開始每小時數據分析，類型: {analysis_type}...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(f"正在進行 {analysis_type} 分析...", total=None)
            
            final_output_path = None
            if output_path:
                final_output_path = Path(output_path)
                if not final_output_path.is_absolute() and final_output_path.name == output_path:
                    final_output_path = config.REPORTS_DIR / final_output_path
            
            result = run_hourly_analysis(
                analysis_type=analysis_type,
                days=days,
                output_path=str(final_output_path) if final_output_path else None,
                include_plots=include_plots,
                plot_save_dir=plot_dir,
                db_path=db_path
            )
        
        if result['success']:
            typer.secho(f"✅ 每小時分析成功: {result['analysis_type']}", fg=typer.colors.GREEN)
            
            if result['plots_generated']:
                typer.echo(f"📊 生成的圖表: {', '.join(result['plots_generated'])}")
            
            if result['report_path']:
                typer.echo(f"📄 報告路徑: {result['report_path']}")
            
            if 'summary' in result:
                summary = result['summary']
                table = Table(title="⏰ 每小時數據摘要")
                table.add_column("指標", style="cyan")
                table.add_column("數值", style="green")
                
                table.add_row("點擊總量", f"{summary['total_clicks']:,}")
                table.add_row("曝光總量", f"{summary['total_impressions']:,}")
                table.add_row("關鍵字總數", f"{summary['unique_queries']:,}")
                table.add_row("高峰時段", f"{summary['peak_hour']:02d}:00")
                table.add_row("低谷時段", f"{summary['low_hour']:02d}:00")
                
                console.print(table)
        else:
            typer.secho("❌ 每小時分析失敗", fg=typer.colors.RED)
            for error in result['errors']:
                typer.echo(f"  - {error}")
            raise typer.Exit(1)
        
    except Exception as e:
        typer.secho(f"❌ 每小時分析失敗：{e}", fg=typer.colors.RED)
        logger.error(f"Hourly analysis failed: {e}")


@app.command(name="analyze-hourly-gemini")
def analyze_hourly_gemini_command(
    site_url: Annotated[Optional[str], typer.Option("--site-url", help="Analyze a specific site URL.")] = None,
    days: Annotated[int, typer.Option(help="Number of past days to analyze.", min=1)] = 30,
):
    """
    [Gemini] Analyze hourly performance trends from the database (simple version).
    """
    typer.echo("[Gemini] Analyzing hourly performance data...")
    from hourly_performance_analyzer import run_hourly_analysis_gemini
    run_hourly_analysis_gemini(site_url=site_url, days=days)
    typer.secho("✅ [Gemini] Hourly analysis complete.", fg=typer.colors.GREEN)


@app.command()
def plot(
    site_id: Annotated[
        Optional[int], typer.Option("--site-id", help="站點 ID")
    ] = None,
    plot_type: Annotated[
        str, typer.Option("--type", help="圖表類型", case_sensitive=False)
    ] = "clicks",
    days: Annotated[
        int, typer.Option("--days", help="天數範圍", min=1, max=365)
    ] = 30,
    save: Annotated[
        Optional[str], typer.Option("--save", help="保存圖片路徑")
    ] = None
):
    """
    📊 繪製數據圖表
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime, timedelta
        
        database = Database()
        
        if not site_id:
            sites = database.get_sites()
            if not sites:
                typer.secho("❌ 沒有可用的站點", fg=typer.colors.RED)
                return
            
            site_id = sites[0]['id']
            typer.echo(f"使用第一個站點 ID: {site_id}")
        
        # 確定日期範圍
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        conn = database.get_connection()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(f"正在生成 {plot_type} 圖表...", total=None)
            
            if plot_type.lower() == "clicks":
                plot_clicks_trend(conn, site_id, start_date, end_date, save)
            elif plot_type.lower() == "rankings":
                plot_rankings_trend(conn, site_id, start_date, end_date, save)
            elif plot_type.lower() == "coverage":
                plot_data_coverage(conn, site_id, save)
            else:
                typer.secho(f"❌ 不支持的圖表類型：{plot_type}", fg=typer.colors.RED)
                return
        
        typer.secho("✅ 圖表生成完成！", fg=typer.colors.GREEN)
        if save:
            typer.echo(f"📁 圖片已保存到：{save}")
        
    except Exception as e:
        typer.secho(f"❌ 生成圖表失敗：{e}", fg=typer.colors.RED)


def plot_clicks_trend(conn, site_id, start_date, end_date, save_path=None):
    """繪製點擊趨勢圖"""
    import matplotlib.pyplot as plt
    import pandas as pd
    
    query = """
    SELECT date, SUM(clicks) as total_clicks, SUM(impressions) as total_impressions
    FROM gsc_data 
    WHERE site_id = ? AND date BETWEEN ? AND ?
    GROUP BY date 
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=[site_id, start_date, end_date])
    
    if df.empty:
        raise ValueError("沒有找到數據")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # 點擊數趨勢
    ax1.plot(df['date'], df['total_clicks'], marker='o', linewidth=2, markersize=4)
    ax1.set_title('點擊數趨勢', fontsize=14, fontweight='bold')
    ax1.set_ylabel('點擊數')
    ax1.grid(True, alpha=0.3)
    
    # 展示數趨勢
    ax2.plot(df['date'], df['total_impressions'], marker='s', linewidth=2, markersize=4, color='orange')
    ax2.set_title('展示數趨勢', fontsize=14, fontweight='bold')
    ax2.set_ylabel('展示數')
    ax2.set_xlabel('日期')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()


def plot_rankings_trend(conn, site_id, start_date, end_date, save_path=None):
    """繪製排名趨勢圖"""
    import matplotlib.pyplot as plt
    import pandas as pd
    
    query = """
    SELECT date, AVG(avg_position) as avg_ranking
    FROM gsc_data 
    WHERE site_id = ? AND date BETWEEN ? AND ?
    GROUP BY date 
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=[site_id, start_date, end_date])
    
    if df.empty:
        raise ValueError("沒有找到數據")
    
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['avg_ranking'], marker='o', linewidth=2, markersize=4, color='red')
    plt.title('平均排名趨勢', fontsize=14, fontweight='bold')
    plt.ylabel('平均排名')
    plt.xlabel('日期')
    plt.grid(True, alpha=0.3)
    
    # 排名越低越好，所以反轉 Y 軸
    plt.gca().invert_yaxis()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()


def plot_data_coverage(conn, site_id, save_path=None):
    """繪製數據覆蓋圖"""
    import matplotlib.pyplot as plt
    import pandas as pd
    
    query = """
    SELECT date, COUNT(*) as record_count
    FROM gsc_data 
    WHERE site_id = ?
    GROUP BY date 
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=[site_id])
    
    if df.empty:
        raise ValueError("沒有找到數據")
    
    plt.figure(figsize=(12, 6))
    plt.bar(df['date'], df['record_count'], alpha=0.7, color='green')
    plt.title('數據覆蓋情況', fontsize=14, fontweight='bold')
    plt.ylabel('記錄數')
    plt.xlabel('日期')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()


if __name__ == "__main__":
    app()
