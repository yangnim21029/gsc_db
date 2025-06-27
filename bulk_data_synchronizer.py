#!/usr/bin/env python3
"""
批次同步腳本 - 逐日同步避免超時
"""
import subprocess
import time
from datetime import datetime, timedelta
import sys


def check_data_exists(site_id, date_str):
    """檢查指定日期的數據是否已存在"""
    import sqlite3
    try:
        conn = sqlite3.connect('gsc_data.db')
        cursor = conn.execute(
            'SELECT COUNT(*) FROM daily_rankings WHERE site_id = ? AND date = ?',
            (site_id, date_str)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def sync_single_day(site_id, date_str):
    """同步單日數據"""
    print(f"🔄 同步 Site {site_id} - {date_str}")

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


def sync_month(site_id, year, month):
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

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')

        # 先檢查是否已存在
        if check_data_exists(site_id, date_str):
            print(f"⏭️  {date_str} 已存在，跳過")
            skip_count += 1
        else:
            if sync_single_day(site_id, date_str):
                success_count += 1
                # 成功後間隔一下避免API限制
                time.sleep(2)
            else:
                fail_count += 1

        current_date += timedelta(days=1)

    print("\n📊 同步結果:")
    print(f"✅ 成功: {success_count} 天")
    print(f"⏭️  跳過: {skip_count} 天")
    print(f"❌ 失敗: {fail_count} 天")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("使用方法: python batch_sync.py <site_id> <year> <month>")
        print("例如: python batch_sync.py 3 2025 6")
        sys.exit(1)

    site_id = int(sys.argv[1])
    year = int(sys.argv[2])
    month = int(sys.argv[3])

    sync_month(site_id, year, month)
