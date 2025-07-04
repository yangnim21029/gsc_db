#!/usr/bin/env python3
"""
GSC 批量數據同步器
重構為可調用函數，支持 CLI 整合
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import time

# 專案模組導入
from .. import config
from ..services.gsc_client import GSCClient
from ..services.database import Database

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_data_exists(site_id: int, date_str: str) -> bool:
    """檢查指定日期的數據是否已存在"""
    import sqlite3
    try:
        conn = sqlite3.connect(str(config.DB_PATH))
        cursor = conn.execute(
            'SELECT COUNT(*) FROM daily_rankings WHERE site_id = ? AND date = ?',
            (site_id, date_str)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def sync_single_day(site_id: int, date_str: str, use_new_cli: bool = True) -> bool:
    """同步單日數據"""
    print(f"🔄 同步 Site {site_id} - {date_str}")

    if use_new_cli:
        cmd = [
            'python', 'main.py', 'sync',
            '--site-id', str(site_id),
            '--start-date', date_str,
            '--end-date', date_str
        ]
    else:
        cmd = [
            'python', 'console_commands.py', 'sync',
            '--site-id', str(site_id),
            '--start-date', date_str,
            '--end-date', date_str
        ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300)  # 5分鐘超時
        if result.returncode == 0:
            print(f"✅ {date_str} 完成")
            return True
        else:
            print(f"❌ {date_str} 失敗: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {date_str} 超時")
        return False
    except Exception as e:
        print(f"💥 {date_str} 錯誤: {e}")
        return False


def sync_month(site_id: int, year: int, month: int, use_new_cli: bool = True) -> Dict[str, int]:
    """同步整月數據"""
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    print(f"📅 開始同步 Site {site_id} - {year}-{month:02d}")
    print(
        f"日期範圍: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")

    success_count = 0
    fail_count = 0
    skip_count = 0

    # 計算總天數用於進度條
    total_days = (end_date - start_date).days + 1
    
    current_date = start_date
    with tqdm(total=total_days, desc=f"同步 {year}-{month:02d}", unit="天") as pbar:
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')

            # 先檢查是否已存在
            if check_data_exists(site_id, date_str):
                print(f"⏭️  {date_str} 已存在，跳過")
                skip_count += 1
            else:
                if sync_single_day(site_id, date_str, use_new_cli):
                    success_count += 1
                    # 成功後間隔一下避免API限制
                    time.sleep(2)
                else:
                    fail_count += 1

            current_date += timedelta(days=1)
            pbar.update(1)

    print("\n📊 同步結果:")
    print(f"✅ 成功: {success_count} 天")
    print(f"⏭️  跳過: {skip_count} 天")
    print(f"❌ 失敗: {fail_count} 天")
    
    return {
        'success': success_count,
        'skip': skip_count,
        'fail': fail_count,
        'total': total_days
    }


def run_sync(
    sites: Optional[List[str]] = None, 
    days: int = 7,
    site_ids: Optional[List[int]] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    use_new_cli: bool = True
) -> Dict[str, Any]:
    """
    同步 Google Search Console 數據的主函數
    
    Args:
        sites: 站點 URL 列表（用於新的 CLI 同步）
        days: 同步最近幾天（用於新的 CLI 同步）
        site_ids: 站點 ID 列表（用於批量同步）
        year: 年份（用於月度同步）
        month: 月份（用於月度同步）
        use_new_cli: 是否使用新的 CLI (main.py)
    
    Returns:
        同步結果統計
    """
    results = {
        'total_sites': 0,
        'successful_sites': 0,
        'failed_sites': 0,
        'details': []
    }
    
    # 新的 CLI 同步方式
    if sites is not None or (site_ids is None and year is None and month is None):
        print(f"🔄 使用新 CLI 同步 {days} 天數據...")
        
        if sites:
            for site in sites:
                print(f"📊 同步站點: {site}")
                cmd = ['python', 'main.py', 'sync', '--site-url', site, '--days', str(days)]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    if result.returncode == 0:
                        print(f"✅ {site} 同步成功")
                        results['successful_sites'] += 1
                    else:
                        print(f"❌ {site} 同步失敗: {result.stderr}")
                        results['failed_sites'] += 1
                except Exception as e:
                    print(f"💥 {site} 同步錯誤: {e}")
                    results['failed_sites'] += 1
                results['total_sites'] += 1
        else:
            # 同步所有站點
            print("🌐 同步所有站點...")
            cmd = ['python', 'main.py', 'sync', '--all-sites', '--days', str(days)]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                if result.returncode == 0:
                    print("✅ 所有站點同步成功")
                    results['successful_sites'] = 1
                else:
                    print(f"❌ 同步失敗: {result.stderr}")
                    results['failed_sites'] = 1
            except Exception as e:
                print(f"💥 同步錯誤: {e}")
                results['failed_sites'] = 1
            results['total_sites'] = 1
    
    # 批量同步方式（月度同步）
    elif site_ids and year and month:
        print(f"📅 批量同步 {len(site_ids)} 個站點的 {year}-{month:02d} 數據...")
        
        for site_id in tqdm(site_ids, desc="處理站點", unit="站點"):
            try:
                result = sync_month(site_id, year, month, use_new_cli)
                results['details'].append({
                    'site_id': site_id,
                    'result': result
                })
                if result['fail'] == 0:
                    results['successful_sites'] += 1
                else:
                    results['failed_sites'] += 1
            except Exception as e:
                print(f"💥 站點 {site_id} 同步錯誤: {e}")
                results['failed_sites'] += 1
            results['total_sites'] += 1
    
    else:
        raise ValueError("請提供有效的參數組合：sites+days 或 site_ids+year+month")
    
    print(f"\n🎉 同步完成！")
    print(f"📊 總站點: {results['total_sites']}")
    print(f"✅ 成功: {results['successful_sites']}")
    print(f"❌ 失敗: {results['failed_sites']}")
    
    return results


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("使用方法: python bulk_data_synchronizer.py <site_id> <year> <month>")
        print("例如: python bulk_data_synchronizer.py 3 2025 6")
        print("\n或者使用新的 CLI 同步:")
        print("python main.py sync --site-url 'https://example.com' --days 30")
        sys.exit(1)

    site_id = int(sys.argv[1])
    year = int(sys.argv[2])
    month = int(sys.argv[3])

    sync_month(site_id, year, month)
