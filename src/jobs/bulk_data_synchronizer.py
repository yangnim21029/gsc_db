#!/usr/bin/env python3
"""
GSC 數據同步作業
- 已重構為可直接調用的函數。
- 包含進度條、重試、斷點續傳和多種同步模式。
"""
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
import typer

from ..services.gsc_client import GSCClient
from ..services.database import Database, SyncMode
from ..utils.state_manager import StateManager

logger = logging.getLogger("rich")
console = Console()

def run_sync(
    db: Database,
    client: GSCClient,
    site_url: Optional[str],
    site_id: Optional[int],
    all_sites: bool,
    start_date: Optional[str],
    end_date: Optional[str],
    days: int,
    retries: int,
    retry_delay: int,
    sync_mode: SyncMode,
    resume: bool,
):
    """
    執行 GSC 數據的每日同步作業。
    """
    date_list = _get_sync_dates(start_date, end_date, days)
    sites_to_sync = _get_sites_to_sync(db, site_url, site_id, all_sites)

    start_site_index, start_date_index = 0, 0
    
    if resume:
        state = StateManager.load_sync_state()
        if state:
            current_site_ids = [s['id'] for s in sites_to_sync]
            if state.get('sites_to_sync_ids') == current_site_ids:
                try:
                    last_site_id = state.get('last_successful_site_id')
                    last_date = state.get('last_successful_date')
                    
                    if last_site_id is not None:
                        start_site_index = next(i for i, s in enumerate(sites_to_sync) if s['id'] == last_site_id)
                    
                    if last_date is not None and last_date != "start":
                        start_date_index = date_list.index(last_date) + 1
                    
                    if start_date_index >= len(date_list):
                        start_site_index += 1
                        start_date_index = 0

                    if start_site_index < len(sites_to_sync):
                        resume_site_name = sites_to_sync[start_site_index]['name']
                        resume_date = date_list[start_date_index]
                        logger.info(f"[bold yellow]🔄 任務恢復中...[/bold yellow] 將從站點 '{resume_site_name}' 的日期 '{resume_date}' 開始。")
                    else:
                        logger.info("[bold green]✅ 所有任務都已在之前的會話中完成。[/bold green]")
                        return
                except (ValueError, StopIteration):
                    logger.warning("[bold yellow]⚠️ 無法解析恢復狀態，將從頭開始。[/bold yellow]")
                    start_site_index, start_date_index = 0, 0
        else:
                logger.info("[bold yellow]⚠️ 同步目標已改變，恢復狀態已重置。[/bold yellow]")

    total_days_to_sync = len(date_list) * len(sites_to_sync)
    completed_days = start_site_index * len(date_list) + start_date_index
    
    progress = Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeElapsedColumn(), TimeRemainingColumn(),
        console=console
    )
    
    total_stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'failed': 0}

    try:
        with progress:
            task = progress.add_task("[green]同步進度...", total=total_days_to_sync, completed=completed_days)
            for i in range(start_site_index, len(sites_to_sync)):
                site = sites_to_sync[i]
                current_site_stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'failed': 0}
                site_name = site['name']
                
                start_j = start_date_index if i == start_site_index else 0
                for j in range(start_j, len(date_list)):
                    date = date_list[j]
                    progress.update(task, description=f"同步 [{site_name}] 日期 [{date}]")
                    
                    if sync_mode.value == "replace":
                        db.delete_performance_data_for_day(site['id'], date)

                    for attempt in range(retries):
                        try:
                            day_stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
                            data_stream = client.stream_site_data(
                                site_url=site['domain'],
                                start_date=date,
                                end_date=date
                            )
                            
                            for device, search_type, chunk in data_stream:
                                chunk_stats = db.save_data_chunk(
                                    chunk=chunk,
                                    site_id=site['id'],
                                    sync_mode=sync_mode.value,
                                    date_str=date,
                                    device=device,
                                    search_type=search_type
                                )
                                for key in day_stats:
                                    day_stats[key] += chunk_stats.get(key, 0)

                            for key in total_stats:
                                total_stats[key] += day_stats.get(key, 0)
                                current_site_stats[key] += day_stats.get(key, 0)
                            
                            logger.info(
                                f"站點 [bold cyan]{site_name}[/bold cyan] 日期 [bold]{date}[/bold] "
                                f"- [green]插入: {day_stats.get('inserted', 0)}[/green], "
                                f"[blue]更新: {day_stats.get('updated', 0)}[/blue], "
                                f"[yellow]跳過: {day_stats.get('skipped', 0)}[/yellow]"
                            )
                            StateManager.save_sync_state({
                                'last_successful_site_id': site['id'],
                                'last_successful_date': date,
                                'sites_to_sync_ids': [s['id'] for s in sites_to_sync]
                            })
                            break
                        except Exception as e:
                            logger.error(f"同步站點 {site_name} 日期 {date} 第 {attempt + 1} 次嘗試失敗: {e}")
                            if attempt == retries - 1:
                                total_stats['failed'] += 1
                                current_site_stats['failed'] += 1
                                logger.error(f"站點 [bold red]{site_name}[/bold red] 日期 [bold red]{date}[/bold red] 在 {retries} 次重試後最終失敗。")
                                logger.debug(traceback.format_exc())
                            else:
                                time.sleep(retry_delay)
                    progress.advance(task)

    except Exception as e:
        logger.error(f"同步過程中發生意外錯誤: {e}")
    finally:
        console.print(Panel("[bold green]同步任務完成[/bold green]", title="總結"))
        summary_table = Table(title="同步結果統計")
        summary_table.add_column("項目", style="cyan")
        summary_table.add_column("數量", style="magenta", justify="right")
        summary_table.add_row("插入記錄", str(total_stats['inserted']))
        summary_table.add_row("更新記錄", str(total_stats['updated']))
        summary_table.add_row("跳過記錄", str(total_stats['skipped']))
        summary_table.add_row("失敗天數", str(total_stats['failed']))
        console.print(summary_table)


def _get_sync_dates(start_date: Optional[str], end_date: Optional[str], days: int) -> List[str]:
    """根據輸入參數生成日期列表"""
    try:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now() - timedelta(days=1)
        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else end_dt - timedelta(days=days - 1)
    except ValueError:
        logger.error("❌ 日期格式錯誤，請使用 YYYY-MM-DD")
        raise typer.Exit(1)

    if start_dt > end_dt:
        logger.error(f"❌ 開始日期 ({start_dt.date()}) 不能晚於結束日期 ({end_dt.date()})")
        raise typer.Exit(1)
        
    return [(start_dt + timedelta(days=x)).strftime('%Y-%m-%d') for x in range((end_dt - start_dt).days + 1)]


def _get_sites_to_sync(
    database: Database,
    site_url: Optional[str],
    site_id: Optional[int],
    all_sites: bool
) -> List[Dict[str, Any]]:
    """根據輸入參數獲取要同步的站點列表"""
    sites_to_sync: List[Dict[str, Any]] = []
    all_db_sites = database.get_sites(active_only=True)

    if all_sites:
        sites_to_sync = all_db_sites
    elif site_id:
        site = next((s for s in all_db_sites if s['id'] == site_id), None)
        if site:
            sites_to_sync.append(site)
    elif site_url:
        site = next((s for s in all_db_sites if s['domain'] == site_url), None)
        if not site:
            logger.info(f"站點 {site_url} 不在數據庫中，嘗試自動添加...")
            site_name = site_url.replace('sc-domain:', '').replace('https://', '').replace('http://', '').rstrip('/')
            try:
                new_site_id = database.add_site(domain=site_url, name=site_name)
                all_db_sites = database.get_sites(active_only=True)
                site = next((s for s in all_db_sites if s['id'] == new_site_id), None)
                if site:
                    logger.info(f"✅ 站點自動添加成功！ID: {new_site_id}")
            except Exception as e:
                logger.error(f"自動添加站點 {site_url} 失敗: {e}")
                site = None
        if site:
            sites_to_sync.append(site)

    if not sites_to_sync:
        logger.error("❌ 未找到或指定任何要同步的站點")
        raise typer.Exit(1)
    return sites_to_sync
