#!/usr/bin/env python3
"""
GSC 數據同步作業
- 已重構為可直接調用的函數。
- 包含進度條、重試、斷點續傳和多種同步模式。
"""

import logging
import ssl
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from googleapiclient.errors import HttpError
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
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings
from ..services.database import Database, SyncMode
from ..services.gsc_client import GSCClient
from ..utils.console_utils import (
    format_error_message,
    format_success_message,
    format_warning_message,
)
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


def _is_retryable_error(exception: Exception) -> bool:
    """判斷是否為可重試的錯誤"""
    # SSL 錯誤
    if isinstance(exception, ssl.SSLError):
        return True

    # 網絡連接錯誤
    if isinstance(
        exception,
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ),
    ):
        return True

    # HTTP 錯誤中的臨時錯誤
    if isinstance(exception, HttpError):
        # 5xx 伺服器錯誤和 429 限流錯誤通常可以重試
        if exception.resp.status >= 500 or exception.resp.status == 429:
            return True
        # 403 可能是臨時的配額限制
        if exception.resp.status == 403:
            return True

    # 其他網絡相關錯誤
    if "SSLError" in str(exception) or "record layer failure" in str(exception):
        return True

    if "length mismatch" in str(exception) or "SSL" in str(exception):
        return True

    # Connection cleanup errors (Google API client)
    if "'NoneType' object has no attribute 'close'" in str(exception):
        return True

    return False


@retry(
    wait=wait_exponential(
        multiplier=1,
        min=settings.retry.wait_min_seconds,
        max=settings.retry.wait_max_seconds,
    ),
    stop=stop_after_attempt(settings.retry.attempts),
    retry=retry_if_exception_type((ssl.SSLError, requests.exceptions.RequestException, HttpError)),
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
    # --- 優化：在執行 API 請求前，先進行最終檢查 ---
    # 即使 run_sync 已經過濾，這裡作為雙重保險，確保任務的獨立性和健壯性。
    if sync_mode == SyncMode.SKIP and _check_existing_data(db, site["id"], date):
        logger.info(f"數據已存在，跳過 API 同步 [站點: {site['name']}, 日期: {date}]")
        return {"inserted": 0, "updated": 0, "skipped": 0, "tasks_skipped_runtime": 1}

    site_name = site["name"]

    if sync_mode == SyncMode.OVERWRITE:
        db.delete_performance_data_for_day(site["id"], date)

    day_stats = {"inserted": 0, "updated": 0, "skipped": 0}

    try:
        logger.info(f"開始呼叫 GSC API：{site['name']} - {date}")
        data_stream = client.stream_site_data(
            site_url=site["domain"], start_date=date, end_date=date
        )
        logger.info(f"GSC API 回應成功：{site['name']} - {date}")

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

    except ssl.SSLError as e:
        logger.warning(f"SSL 錯誤，將重試: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.warning(f"網絡請求錯誤，將重試: {e}")
        raise
    except HttpError as e:
        if e.resp.status >= 500 or e.resp.status in [429, 403]:
            logger.warning(f"HTTP 錯誤 {e.resp.status}，將重試: {e}")
            raise
        else:
            logger.error(f"不可重試的 HTTP 錯誤 {e.resp.status}: {e}")
            raise
    except Exception as e:
        # Handle specific NoneType close() errors
        if "'NoneType' object has no attribute 'close'" in str(e):
            logger.warning(f"Connection cleanup error (will retry): {e}")
            raise  # This is retryable
        elif _is_retryable_error(e):
            logger.warning(f"可重試的錯誤: {e}")
            raise
        else:
            logger.error(f"不可重試的錯誤: {e}")
            raise


def _print_final_summary(total_stats: Dict[str, int]):
    """打印最終的同步結果摘要。"""
    table = Table(title="📊 同步作業摘要", show_header=True, header_style="bold magenta")
    table.add_column("項目", style="dim")
    table.add_column("數量", justify="right")

    table.add_row(
        "計劃前跳過的任務", f"[yellow]{total_stats.get('tasks_pre_skipped', 0):,}[/yellow]"
    )
    table.add_row(
        "執行中跳過的任務", f"[yellow]{total_stats.get('tasks_skipped_runtime', 0):,}[/yellow]"
    )
    table.add_row("插入記錄", f"[green]{total_stats.get('inserted', 0):,}[/green]")
    table.add_row("更新記錄", f"[blue]{total_stats.get('updated', 0):,}[/blue]")
    # 'skipped' 現在只代表在保存數據塊時跳過的記錄，通常為 0
    # table.add_row("跳過記錄 (儲存層)", f"[yellow]{total_stats.get('skipped', 0):,}[/yellow]")
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

    tasks_pre_skipped = all_possible_task_count - len(tasks_to_run)
    logger.info(
        f"計劃同步 {len(sites_to_sync)} 個站點， {len(date_list)} 天。"
        f"總任務數: {all_possible_task_count}, 已跳過: {tasks_pre_skipped}, 將執行: {len(tasks_to_run)}。"
    )

    if not tasks_to_run:
        logger.info("所有計劃的數據都已存在，無需同步。")
        _print_final_summary(
            {
                "tasks_pre_skipped": all_possible_task_count,
                "tasks_skipped_runtime": 0,
                "inserted": 0,
                "updated": 0,
                "failed": 0,
            }
        )
        return

    # ================= 3. 執行階段 =================
    # 根據 GSC API 最佳實踐，使用順序處理避免並行問題
    # API 文件建議避免過度併發以防止 SSL 和速率限制問題
    logger.info("使用順序處理模式，確保 GSC API 調用的穩定性")

    total_stats = {
        "inserted": 0,
        "updated": 0,
        "skipped": 0,  # 用於記錄儲存層的跳過，通常為 0
        "failed": 0,
        "tasks_pre_skipped": tasks_pre_skipped,
        "tasks_skipped_runtime": 0,
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
        task_id = progress.add_task("[bold green]順序同步中...", total=len(tasks_to_run))

        # 順序處理每個任務，避免並行導致的 API 限制和 SSL 錯誤
        for idx, (site, date) in enumerate(tasks_to_run):
            # 更新任務描述，顯示當前正在處理的網站和日期
            progress.update(
                task_id,
                description=f"[bold green]同步中... [cyan]{site['name']}[/cyan] - [yellow]{date}[/yellow]",
            )

            try:
                # 在控制台顯示即時狀態
                console.print(
                    f"[dim]開始同步:[/dim] {site['name']} ({site['domain']}) - {date}",
                    highlight=False,
                )

                day_stats = _sync_single_day(db, client, site, date, sync_mode)
                for key in total_stats:
                    if key in day_stats:
                        total_stats[key] += day_stats[key]

                # 顯示本次同步結果
                if day_stats.get("inserted", 0) > 0 or day_stats.get("updated", 0) > 0:
                    console.print(
                        format_success_message(
                            f"完成: 新增 {day_stats.get('inserted', 0)} 筆, "
                            f"更新 {day_stats.get('updated', 0)} 筆"
                        ),
                        highlight=False,
                    )
                else:
                    console.print(format_warning_message("已存在或無數據"), highlight=False)

            except RetryError as e:
                logger.error(
                    f"同步失敗 [站點: {site['name']}, 日期: {date}]: "
                    f"多次嘗試後仍然失敗。最後一次錯誤: {e.last_attempt.exception()}"
                )
                console.print(
                    format_error_message(f"失敗: {str(e.last_attempt.exception())}"),
                    highlight=False,
                )
                total_stats["failed"] += 1
            except Exception as exc:
                logger.error(f"任務 {site['name']}-{date} 產生未預期的例外: {exc}")
                logger.debug(traceback.format_exc())
                console.print(format_error_message(f"錯誤: {str(exc)}"), highlight=False)
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
        max_workers: Optional[int] = None,  # 保留參數以保持向後兼容性，但不再使用
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
            max_workers=1,  # 強制使用順序處理
        )
