#!/usr/bin/env python3
"""
GSC 數據同步作業
- 已重構為可直接調用的函數。
- 包含進度條、重試、斷點續傳和多種同步模式。
"""

import concurrent.futures
import logging
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings
from ..services.database import Database, SyncMode
from ..services.gsc_client import GSCClient
from ..utils.rich_console import console

logger = logging.getLogger(__name__)


def _check_existing_data(db: Database, site_id: int, date: str) -> bool:
    """檢查指定站點和日期是否已有數據"""
    with db._lock:
        result = db._connection.execute(
            "SELECT COUNT(*) as count FROM gsc_performance_data WHERE site_id = ? AND date = ?",
            (site_id, date),
        ).fetchone()
        return bool(result and result["count"] > 0)


@retry(
    wait=wait_exponential(
        multiplier=1,
        min=settings.retry.wait_min_seconds,
        max=settings.retry.wait_max_seconds,
    ),
    stop=stop_after_attempt(settings.retry.attempts),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _sync_single_day(
    db: Database,
    client: GSCClient,
    site: Dict[str, Any],
    date: str,
    sync_mode: SyncMode,
) -> Dict[str, int]:
    """同步單日數據，使用 tenacity 進行重試。"""
    site_name = site["name"]

    if sync_mode == SyncMode.OVERWRITE:
        db.delete_performance_data_for_day(site["id"], date)

    day_stats = {"inserted": 0, "updated": 0, "skipped": 0}
    data_stream = client.stream_site_data(site_url=site["domain"], start_date=date, end_date=date)

    for device, search_type, chunk in data_stream:
        chunk_stats = db.save_data_chunk(
            chunk=chunk,
            site_id=site["id"],
            sync_mode=sync_mode.value,
            date_str=date,
            device=device,
            search_type=search_type,
        )
        for key in day_stats:
            day_stats[key] += chunk_stats.get(key, 0)

    logger.info(
        f"站點 [bold cyan]{site_name}[/bold cyan] 日期 [bold]{date}[/bold] - "
        f"[green]同步成功[/green]"
    )
    return day_stats


def _print_final_summary(total_stats: Dict[str, int]):
    """打印最終的同步結果摘要。"""
    table = Table(title="📊 同步結果摘要", show_header=True, header_style="bold magenta")
    table.add_column("項目", style="dim")
    table.add_column("數量", justify="right")

    table.add_row("插入記錄", f"[green]{total_stats.get('inserted', 0):,}[/green]")
    table.add_row("更新記錄", f"[blue]{total_stats.get('updated', 0):,}[/blue]")
    table.add_row("跳過記錄", f"[yellow]{total_stats.get('skipped', 0):,}[/yellow]")
    table.add_row("失敗任務", f"[red]{total_stats.get('failed', 0):,}[/red]")

    console.print(table)


def run_sync(
    db: Database,
    client: GSCClient,
    all_sites: bool,
    site_id: Optional[int],
    start_date: Optional[str],
    end_date: Optional[str],
    days: int,
    sync_mode: SyncMode,
    max_workers: int,
):
    """執行 GSC 數據的每日同步作業，採用計劃-執行模式。"""
    # ================= 1. 準備階段 =================
    logger.info("正在準備同步作業...")

    # 獲取要同步的網站列表
    sites_to_sync: List[Dict[str, Any]] = []
    if all_sites:
        sites_to_sync = db.get_sites(active_only=True)
    elif site_id:
        site = db.get_site_by_id(site_id)
        if site:
            sites_to_sync.append(site)

    if not sites_to_sync:
        logger.warning("找不到任何要同步的活動站點。")
        return

    # 確定日期範圍
    if start_date and end_date:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        today = datetime.now().date()
        e_date = today - timedelta(days=2)  # GSC數據延遲約2天
        s_date = e_date - timedelta(days=days - 1)

    date_list = [
        (s_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((e_date - s_date).days + 1)
    ]

    # ================= 2. 計劃階段 =================
    all_possible_tasks = [(site, date) for site in sites_to_sync for date in date_list]
    tasks_to_run = all_possible_tasks
    all_possible_task_count = len(sites_to_sync) * len(date_list)

    if sync_mode == SyncMode.SKIP:
        logger.info("SKIP 模式：正在檢查數據庫中已存在的數據...")
        site_ids = [s["id"] for s in sites_to_sync]
        existing_data_days = db.get_existing_data_days_for_sites(
            site_ids, date_list[0], date_list[-1]
        )
        tasks_to_run = [
            (site, date)
            for site, date in all_possible_tasks
            if (site["id"], date) not in existing_data_days
        ]

    logger.info(
        f"計劃同步 {len(sites_to_sync)} 個站點， {len(date_list)} 天。"
        f"將要執行: {len(tasks_to_run)} 個同步任務。"
    )

    if not tasks_to_run:
        logger.info("所有計劃的數據都已存在，無需同步。")
        _print_final_summary(
            {"inserted": 0, "updated": 0, "skipped": all_possible_task_count, "failed": 0}
        )
        return

    # ================= 3. 執行階段 =================
    total_stats = {
        "inserted": 0,
        "updated": 0,
        "skipped": all_possible_task_count - len(tasks_to_run),
        "failed": 0,
    }

    progress_columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ]

    with Progress(*progress_columns, console=console) as progress:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            task_id = progress.add_task("[bold green]並行同步中...", total=len(tasks_to_run))

            future_to_task = {
                executor.submit(_sync_single_day, db, client, site, date, sync_mode): (site, date)
                for site, date in tasks_to_run
            }

            for future in concurrent.futures.as_completed(future_to_task):
                site, date = future_to_task[future]
                try:
                    day_stats = future.result()
                    for key in total_stats:
                        if key in day_stats:
                            total_stats[key] += day_stats[key]
                except RetryError as e:
                    logger.error(
                        f"同步失敗 [站點: {site['name']}, 日期: {date}]: "
                        f"多次嘗試後仍然失敗。最後一次錯誤: {e.last_attempt.exception()}"
                    )
                    total_stats["failed"] += 1
                except Exception as exc:
                    logger.error(f"任務 {site['name']}-{date} 產生未預期的例外: {exc}")
                    logger.debug(traceback.format_exc())
                    total_stats["failed"] += 1

                progress.update(task_id, advance=1)

    _print_final_summary(total_stats)


class BulkDataSynchronizer:
    """Bulk data synchronizer wrapper class for dependency injection."""

    def __init__(self, db: Database, gsc_client: GSCClient):
        self.db = db
        self.gsc_client = gsc_client

    def run_sync(
        self,
        all_sites: bool = False,
        site_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 2,
        sync_mode: SyncMode = SyncMode.OVERWRITE,
        max_workers: int = 4,
    ):
        """Run the synchronization process."""
        return run_sync(
            db=self.db,
            client=self.gsc_client,
            all_sites=all_sites,
            site_id=site_id,
            start_date=start_date,
            end_date=end_date,
            days=days,
            sync_mode=sync_mode,
            max_workers=max_workers,
        )
