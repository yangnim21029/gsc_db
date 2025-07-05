#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全站數據自動化同步腳本

功能:
1. 自動確保所有主要站點存在於數據庫中。
2. 同步所有 GSC 網站的每日數據 (最近30天)。
3. 同步所有 GSC 網站的每小時數據 (最近10天)。

此腳本設計為可由 cron 等排程工具自動調用。
"""

import sys
import os
import traceback
from datetime import datetime, timedelta

# --- 環境設定 ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.containers import Container
from src.jobs.bulk_data_synchronizer import run_sync
from src.services.database import SyncMode
from rich.console import Console
from rich.table import Table

console = Console()

# 清理和整合後的站點列表，優先使用 sc-domain 屬性
SITES_TO_ENSURE = [
    "sc-domain:businessfocus.io",
    "sc-domain:girlstyle.com",
    "sc-domain:holidaysmart.io",
    "sc-domain:mamidaily.com",
    "sc-domain:petcutecute.com",
    "sc-domain:poplady-mag.com",
    "sc-domain:pretty.presslogic.com",
    "sc-domain:thekdaily.com",
    "sc-domain:thepetcity.co",
    "sc-domain:topbeautyhk.com",
    "sc-domain:urbanlifehk.com",
    "https://hkg.hankyu-hanshin-dept.co.jp/", # 這個沒有domain屬性，保留原樣
    "https://www.phytomehk.com/",             # 這個沒有domain屬性，保留原樣
]

def main():
    """主函式，用於執行全站數據同步任務。"""
    console.print("[bold green]🚀 開始全站數據同步任務...[/bold green]", style="bold white on blue")

    container = Container()
    db = container.db_service()
    gsc_client = container.gsc_client()
    
    try:
        # --- 步驟 0: 確保所有站點都已在數據庫中 ---
        console.print("\n[cyan]▶️ 步驟 0: 正在檢查並確保所有站點都已添加到數據庫...[/cyan]")
        added_count = db.batch_add_sites(SITES_TO_ENSURE)
        console.print(f"   [green]✅ 站點檢查完成。新增了 {added_count} 個新站點。[/green]")

        # 顯示將要同步的所有站點
        all_db_sites = db.get_sites(active_only=True)
        if all_db_sites:
            table = Table(title=f"📊 將對以下 {len(all_db_sites)} 個活動站點進行同步")
            table.add_column("ID", style="cyan")
            table.add_column("站點 Domain", style="magenta")
            for site in all_db_sites:
                table.add_row(str(site['id']), site['domain'])
            console.print(table)
        else:
            console.print("[yellow]   ⚠️ 數據庫中沒有找到任何活動站點，後續同步將被跳過。[/yellow]")


        # --- 步驟 1: 同步所有網站的每日數據 ---
        console.print("\n[cyan]▶️ 步驟 1: 同步所有網站的每日數據 (最近30天)...[/cyan]")
        
        # 不再使用 all_sites=True，而是遍歷我們確保要同步的列表
        console.print(f"   [dim]將精確同步 {len(SITES_TO_ENSURE)} 個在 SITES_TO_ENSURE 列表中的站點...[/dim]")
        for i, site_url in enumerate(SITES_TO_ENSURE):
            console.print(f"\n   ({i+1}/{len(SITES_TO_ENSURE)}) [bold]正在同步每日數據: {site_url}[/bold]")
            run_sync(
                db=db,
                client=gsc_client,
                all_sites=False, # 明確設置為 False
                site_id=None,
                site_url=site_url, # 傳入單一站點
                start_date=None,
                end_date=None,
                days=30,
                retries=3,
                retry_delay=10,
                sync_mode=SyncMode.SKIP,
                resume=True # 仍然可以對單一站點任務進行恢復
            )
        console.print("[green]✅ 每日數據同步完成。[/green]")

        # --- 步驟 2: 同步所有網站的每小時數據 ---
        console.print("\n[cyan]▶️ 步驟 2: 同步所有網站的每小時數據 (過去10天)...[/cyan]")

        # 直接使用 SITES_TO_ENSURE 列表，而不是從 DB 讀取所有站點
        if not SITES_TO_ENSURE:
            console.print("[yellow]   ⚠️ SITES_TO_ENSURE 列表為空，跳過每小時同步。[/yellow]")
        else:
            end_date = datetime.now()
            # API 最多回傳 10 天前的資料，所以我們抓 9 天前的資料到今天
            start_date = end_date - timedelta(days=9)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')

            console.print(f"   [dim]時間範圍: {start_date_str} 到 {end_date_str}[/dim]")

            for i, site_url in enumerate(SITES_TO_ENSURE):
                console.print(f"\n   ({i+1}/{len(SITES_TO_ENSURE)}) [bold]正在同步站點: {site_url}[/bold]")
                try:
                    from src.services.hourly_database import HourlyDatabase
                    hourly_db = HourlyDatabase(db.get_connection, site_url)
                    
                    inserted_count = hourly_db.sync_data(gsc_client, start_date_str, end_date_str)
                    console.print(f"   [green]✅ 同步成功！新增 {inserted_count} 條記錄。[/green]")

                except Exception as e:
                    console.print(f"   [red]❌ 同步站點 {site_url} 失敗: {e}[/red]")
                    console.print(f"   [dim]{traceback.format_exc()}[/dim]")

            console.print("\n[green]✅ 每小時數據同步完成。[/green]")

        console.print("\n[bold green]🎉 全站數據同步任務圓滿結束！[/bold green]", style="bold white on blue")

    except Exception as e:
        console.print(f"\n[bold red]❌ 腳本執行期間發生嚴重錯誤: {e}[/bold red]")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")

if __name__ == "__main__":
    main() 