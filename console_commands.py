#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC 數據導出工具 (簡化版)
純命令行操作，支援數據同步、每小時數據等功能
"""

import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional

# 正確的模塊導入
from services.gsc_client import GSCClient
from services.database import Database

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gsc_simple.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='GSC 數據導出工具 (CLI)')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 認證
    subparsers.add_parser('auth', help='進行 GSC API 認證')

    # 站點管理
    subparsers.add_parser('sites', help='列出所有站點')

    add_site_parser = subparsers.add_parser('add-site', help='添加站點到數據庫')
    add_site_parser.add_argument('site_url', nargs='?', help='站點 URL')

    # 數據覆蓋
    coverage_parser = subparsers.add_parser('coverage', help='顯示數據覆蓋情況')
    coverage_parser.add_argument('--site-id', type=int, help='站點 ID')

    # 數據同步
    sync_parser = subparsers.add_parser('sync', help='同步數據')
    sync_parser.add_argument('--site-url', help='站點 URL')
    sync_parser.add_argument('--site-id', type=int, help='站點 ID')
    sync_parser.add_argument('--start-date', help='開始日期 (YYYY-MM-DD)')
    sync_parser.add_argument('--end-date', help='結束日期 (YYYY-MM-DD)')
    sync_parser.add_argument('--force', action='store_true', help='強制重建數據')
    sync_parser.add_argument('--all-sites', action='store_true', help='同步所有站點')

    # 進度監控 (簡化版)
    subparsers.add_parser('progress', help='顯示最近任務')

    # 每小時數據相關命令
    hourly_sync_parser = subparsers.add_parser('hourly-sync', help='同步每小時數據')
    hourly_sync_parser.add_argument('--site-url', help='站點 URL')
    hourly_sync_parser.add_argument('--start-date', help='開始日期 (默認昨天)')
    hourly_sync_parser.add_argument('--end-date', help='結束日期 (默認今天)')

    hourly_summary_parser = subparsers.add_parser(
        'hourly-summary', help='顯示每小時數據總結')
    hourly_summary_parser.add_argument('--site-id', type=int, help='站點 ID')
    hourly_summary_parser.add_argument('--date', help='日期 (可選)')

    hourly_coverage_parser = subparsers.add_parser(
        'hourly-coverage', help='顯示每小時數據覆蓋情況')
    hourly_coverage_parser.add_argument('--site-id', type=int, help='站點 ID')

    # API 狀態
    subparsers.add_parser('api-status', help='顯示 API 使用狀態')

    # 日誌查看
    logs_parser = subparsers.add_parser('logs', help='查看同步日誌')
    logs_parser.add_argument(
        '--lines',
        type=int,
        default=50,
        help='顯示行數 (默認50行)')
    logs_parser.add_argument(
        '--error-only',
        action='store_true',
        help='只顯示錯誤日誌')

    # 數據可視化
    plot_parser = subparsers.add_parser('plot', help='繪製數據圖表')
    plot_parser.add_argument('--site-id', type=int, help='站點 ID')
    plot_parser.add_argument(
        '--type',
        choices=[
            'clicks',
            'rankings',
            'coverage'],
        default='clicks',
        help='圖表類型')
    plot_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='天數範圍 (默認30天)')
    plot_parser.add_argument('--save', help='保存圖片路徑 (可選)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\n💡 提示: 使用 'python search_console_manager.py' 來啟動互動式選單")
        return

    try:
        if args.command == 'auth':
            handle_auth()
        elif args.command == 'sites':
            show_sites()
        elif args.command == 'add-site':
            add_site(args.site_url)
        elif args.command == 'coverage':
            show_coverage(args.site_id)
        elif args.command == 'sync':
            handle_sync(args)
        elif args.command == 'progress':
            show_progress()
        elif args.command == 'hourly-sync':
            handle_hourly_sync(args)
        elif args.command == 'hourly-summary':
            show_hourly_summary(args.site_id, args.date)
        elif args.command == 'hourly-coverage':
            show_hourly_coverage(args.site_id)
        elif args.command == 'api-status':
            show_api_status()
        elif args.command == 'logs':
            show_logs(args)
        elif args.command == 'plot':
            plot_data(args)
        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ 執行失敗：{e}")
        logger.error(f"Command execution failed: {e}")


def handle_auth():
    """處理認證"""
    gsc_client = GSCClient()

    if gsc_client.is_authenticated():
        print("✅ 已經認證成功")
        return

    auth_url = gsc_client.get_auth_url()
    print("🔗 請訪問以下 URL 進行認證：")
    print(auth_url)
    print("\n認證完成後，請重新運行此命令檢查狀態")


def show_sites():
    """顯示站點列表"""
    try:
        gsc_client = GSCClient()

        # 從 GSC 獲取站點
        gsc_sites = gsc_client.get_sites()
        print(f"📊 GSC 中的站點 ({len(gsc_sites)} 個)：")
        for i, site in enumerate(gsc_sites, 1):
            print(f"  {i}. {site}")

        # 從數據庫獲取站點
        database = Database()
        db_sites = database.get_sites()
        print(f"\n💾 數據庫中的站點 ({len(db_sites)} 個)：")
        for site in db_sites:
            print(f"  ID: {site['id']} - {site['name']} ({site['domain']})")

    except Exception as e:
        print(f"❌ 獲取站點失敗：{e}")


def add_site(site_url: Optional[str] = None):
    """添加站點"""
    try:
        # 如果沒有提供 URL，互動式詢問
        if not site_url:
            print("\n🌐 添加新站點")
            print("請輸入站點 URL (例如: https://example.com/ 或 sc-domain:example.com)")
            site_url = input("站點 URL: ").strip()

            if not site_url:
                print("❌ 必須提供站點 URL")
                return

        database = Database()
        site_name = site_url.replace(
            'sc-domain:',
            '').replace(
            'https://',
            '').replace(
            'http://',
            '')
        site_id = database.add_site(site_url, site_name)
        print(f"✅ 站點已添加：ID {site_id}, URL: {site_url}")

    except Exception as e:
        print(f"❌ 添加站點失敗：{e}")


def show_coverage(site_id: Optional[int] = None):
    """顯示數據覆蓋情況"""
    try:
        database = Database()

        with database.get_connection() as conn:
            if site_id:
                # 特定站點覆蓋情況
                query = '''
                    SELECT
                        s.id, s.name, s.domain,
                        MIN(dr.date) as earliest_date,
                        MAX(dr.date) as latest_date,
                        COUNT(DISTINCT dr.date) as total_days,
                        COUNT(dr.id) as total_records
                    FROM sites s
                    LEFT JOIN daily_rankings dr ON s.id = dr.site_id
                    WHERE s.id = ?
                    GROUP BY s.id
                '''
                result = conn.execute(query, (site_id,)).fetchone()

                if result:
                    site = dict(result)
                    print(f"📊 站點數據覆蓋情況：{site['name']}")
                    print("-" * 50)
                    print(f"站點 ID：{site['id']}")
                    print(f"域名：{site['domain']}")
                    print(
                        f"數據範圍：{site['earliest_date']} 至 {site['latest_date']}")
                    print(f"涵蓋天數：{site['total_days']}")
                    print(f"總記錄數：{site['total_records']:,}")
                else:
                    print(f"❌ 找不到站點 ID {site_id}")
            else:
                # 所有站點概況
                query = '''
                    SELECT
                        s.id, s.name, s.domain,
                        MIN(dr.date) as earliest_date,
                        MAX(dr.date) as latest_date,
                        COUNT(DISTINCT dr.date) as total_days,
                        COUNT(dr.id) as total_records
                    FROM sites s
                    LEFT JOIN daily_rankings dr ON s.id = dr.site_id
                    GROUP BY s.id
                    ORDER BY s.name
                '''
                sites = [dict(row) for row in conn.execute(query).fetchall()]

                print_coverage_table(sites)

    except Exception as e:
        print(f"❌ 查詢失敗：{e}")


def print_coverage_table(sites: list):
    """打印覆蓋情況表格 - 提取重複代碼"""
    print("📊 所有站點數據覆蓋情況：")
    print("-" * 80)
    print(f"{'ID':<4} {'站點名稱':<20} {'最早日期':<12} {'最新日期':<12} {'天數':<6} {'記錄數':<10}")
    print("-" * 80)

    for site in sites:
        records = f"{site['total_records']:,}" if site['total_records'] else "0"
        print(
            f"{site['id']:<4} {site['name'][:19]:<20} {site['earliest_date'] or 'N/A':<12} "
            f"{site['latest_date'] or 'N/A':<12} {site['total_days'] or 0:<6} {records:<10}")


def handle_sync(args):
    """處理數據同步"""
    try:
        gsc_client = GSCClient()
        database = Database()

        # 設置日期範圍
        end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')
        start_date = args.start_date or (
            datetime.now() -
            timedelta(
                days=7)).strftime('%Y-%m-%d')

        if args.all_sites:
            # 同步所有站點
            sites = database.get_sites()
            for site in sites:
                print(f"🔄 同步站點：{site['name']}")
                result = gsc_client.sync_site_data_enhanced(
                    site['domain'], start_date, end_date)
                print(
                    f"✅ 完成：關鍵字 {result['keyword_count']} 條，頁面 {result['page_count']} 條")

        elif args.site_url:
            # 同步指定 URL 的站點
            print(f"🔄 同步站點：{args.site_url}")
            result = gsc_client.sync_site_data_enhanced(
                args.site_url, start_date, end_date)
            print(
                f"✅ 完成：關鍵字 {result['keyword_count']} 條，頁面 {result['page_count']} 條")

        elif args.site_id:
            # 同步指定 ID 的站點
            sites = database.get_sites()
            site = next((s for s in sites if s['id'] == args.site_id), None)
            if site:
                print(f"🔄 同步站點：{site['name']}")
                result = gsc_client.sync_site_data_enhanced(
                    site['domain'], start_date, end_date)
                print(
                    f"✅ 完成：關鍵字 {result['keyword_count']} 條，頁面 {result['page_count']} 條")
            else:
                print(f"❌ 找不到站點 ID {args.site_id}")
        else:
            print("❌ 請指定要同步的站點 (--site-url, --site-id, 或 --all-sites)")

    except Exception as e:
        print(f"❌ 同步失敗：{e}")


def show_progress():
    """顯示最近任務 (簡化版)"""
    try:
        database = Database()
        tasks = database.get_recent_tasks(10)

        if not tasks:
            print("📊 沒有任務記錄")
            return

        print("📊 最近任務：")
        print("-" * 80)
        print(f"{'ID':<4} {'站點':<20} {'任務類型':<15} {'狀態':<10} {'記錄數':<8} {'創建時間':<20}")
        print("-" * 80)

        for task in tasks:
            created_at = task['created_at'][:19] if task['created_at'] else 'N/A'
            site_name = task['site_name'][:19] if task['site_name'] else 'N/A'
            print(
                f"{task['id']:<4} {site_name:<20} {task['task_type']:<15} "
                f"{task['status']:<10} {task['total_records']:<8} {created_at:<20}")

    except Exception as e:
        print(f"❌ 查詢失敗：{e}")


def handle_hourly_sync(args):
    """處理每小時數據同步"""
    site_url = args.site_url
    start_date = args.start_date or (
        datetime.now() -
        timedelta(
            days=1)).strftime('%Y-%m-%d')
    end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')

    if not site_url:
        print("❌ 需要指定站點 URL")
        return

    print(f"📊 開始同步每小時數據：{site_url}")
    print(f"日期範圍：{start_date} 至 {end_date}")
    print("⚠️  每小時數據僅提供最近 10 天的資料")

    try:
        gsc_client = GSCClient()
        result = gsc_client.sync_hourly_data(site_url, start_date, end_date)
        print("✅ 完成同步！")
        print(f"   - 保存記錄數：{result['hourly_count']}")
        print(f"   - 獨特項目數：{result['unique_items']}")
    except Exception as e:
        print(f"❌ 同步失敗：{e}")


def show_hourly_summary(site_id: Optional[int], date: Optional[str] = None):
    """顯示每小時數據總結"""
    if site_id is None:
        print("❌ 需要指定站點 ID (使用 sites 命令查看)")
        return

    try:
        database = Database()
        summary = database.get_hourly_summary(site_id, date)

        if not summary:
            print("📊 沒有找到每小時數據")
            return

        print(f"📊 每小時數據總結 (站點 ID: {site_id})")
        if date:
            print(f"日期：{date}")
        else:
            print("顯示最近 3 天的數據")

        print_hourly_summary_table(summary)

    except Exception as e:
        print(f"❌ 查詢失敗：{e}")


def print_hourly_summary_table(summary: list):
    """打印每小時總結表格 - 提取重複代碼"""
    print("-" * 80)
    print(f"{'日期':<12} {'小時':<4} {'查詢數':<8} {'點擊':<8} {'展示':<10} {'平均排名':<8} {'CTR':<8}")
    print("-" * 80)

    for row in summary:
        ctr_percent = f"{row['avg_ctr']*100:.2f}%" if row['avg_ctr'] else "0%"
        avg_pos = f"{row['avg_position']:.1f}" if row['avg_position'] else "N/A"

        print(f"{row['date']:<12} {row['hour']:>2}h {row['query_count']:>6} "
              f"{row['total_clicks']:>6} {row['total_impressions']:>8} "
              f"{avg_pos:>7} {ctr_percent:>7}")


def show_hourly_coverage(site_id: Optional[int]):
    """顯示每小時數據覆蓋情況"""
    if site_id is None:
        print("❌ 需要指定站點 ID (使用 sites 命令查看)")
        return

    try:
        database = Database()
        coverage = database.get_hourly_coverage(site_id)

        print(f"📊 每小時數據覆蓋情況 (站點 ID: {site_id})")
        print("-" * 50)

        if coverage.get('total_records', 0) > 0:
            print_hourly_coverage_details(coverage)
        else:
            print("❌ 沒有每小時數據")
            print("💡 使用 'hourly-sync' 命令開始收集每小時數據")

    except Exception as e:
        print(f"❌ 查詢失敗：{e}")


def print_hourly_coverage_details(coverage: dict):
    """打印每小時覆蓋詳情 - 提取重複代碼"""
    print(f"總記錄數：{coverage['total_records']:,}")
    print(f"數據範圍：{coverage['first_date']} 至 {coverage['last_date']}")
    print(f"涵蓋天數：{coverage['unique_dates']}")
    print(f"涵蓋小時數：{coverage['unique_hours']}")

    print("\n最近 24 小時的數據點：")
    print(f"{'日期':<12} {'小時':<6} {'記錄數':<8}")
    print("-" * 26)

    for data in coverage.get('recent_data', []):
        print(f"{data['date']:<12} {data['hour']:>2}h {data['records']:>6}")


def show_api_status():
    """顯示 API 使用狀態"""
    print("📊 GSC API 使用狀態")
    print("-" * 40)
    
    try:
        gsc_client = GSCClient()
        stats = gsc_client.get_api_usage_stats()
        
        print("📈 當前使用情況：")
        print(f"  • 今日請求：{stats['requests_today']:,} / {stats['daily_limit']:,} ({stats['daily_usage_percent']:.2f}%)")
        print(f"  • 本分鐘請求：{stats['requests_this_minute']} / {stats['minute_limit']} ({stats['minute_usage_percent']:.2f}%)")
        print(f"  • 今日剩餘：{stats['daily_remaining']:,} 次請求")
        print(f"  • 本分鐘剩餘：{stats['minute_remaining']} 次請求")
        print()
        
        # 使用量警告
        if stats['daily_usage_percent'] > 80:
            print("🚨 警告：今日API使用量已超過80%！")
        elif stats['daily_usage_percent'] > 50:
            print("⚠️  注意：今日API使用量已超過50%")
        else:
            print("✅ API使用量正常")
        print()
        
        # 顯示最近7天的使用統計
        print("📅 最近7天使用統計：")
        try:
            with gsc_client.database.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT date, requests_count 
                    FROM api_usage_stats 
                    WHERE date >= date('now', '-7 days')
                    ORDER BY date DESC
                ''')
                history = cursor.fetchall()
                
                if history:
                    for row in history:
                        percentage = (row['requests_count'] / 100000) * 100
                        print(f"  • {row['date']}: {row['requests_count']:,} 次 ({percentage:.2f}%)")
                else:
                    print("  • 暫無歷史記錄")
        except Exception as e:
            print(f"  • 無法載入歷史統計: {e}")
        print()
        
    except Exception as e:
        print(f"⚠️  無法獲取API使用統計：{e}")
        print()
        
    print("📋 API 限制：")
    print("  • 每日請求：100,000 次")
    print("  • 每分鐘請求：1,200 次")
    print("  • 每次請求最大行數：1,000 行")
    print("  • 數據延遲：2-3 天")
    print("  • 每小時數據範圍：最多 10 天")
    print()
    print("💡 最佳實踐：")
    print("  • 避免重複抓取相同數據")
    print("  • 使用增量同步")
    print("  • 批次處理大量請求")
    print("  • 每小時數據建議等待 2-3 天後查詢")


def show_logs(args):
    """顯示同步日誌"""
    import os

    try:
        log_files = ['gsc_simple.log', 'app.log']
        found_logs = [f for f in log_files if os.path.exists(f)]

        if not found_logs:
            print("❌ 找不到日誌文件")
            print("💡 可用的日誌文件：gsc_simple.log, app.log")
            return

        log_file = found_logs[0]
        print(f"📋 查看日誌文件：{log_file}")
        print("-" * 80)

        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 只顯示錯誤日誌
        if args.error_only:
            error_lines = []
            for line in lines:
                if any(
                    keyword in line for keyword in [
                        'ERROR',
                        'Failed',
                        'failed',
                        '❌']):
                    error_lines.append(line)

            if not error_lines:
                print("✅ 沒有發現錯誤日誌")
                return
            else:
                print(f"🚨 找到 {len(error_lines)} 條錯誤日誌：")
                lines = error_lines

        # 顯示最後N行
        display_lines = lines[-args.lines:] if len(
            lines) > args.lines else lines

        for line in display_lines:
            print(line.rstrip())

        print("\n📊 日誌統計：")
        if args.error_only:
            print(f"  • 錯誤行數：{len(display_lines)}")
        else:
            print(f"  • 總行數：{len(lines)}")
            error_count = len([line for line in lines if any(
                keyword in line for keyword in ['ERROR', 'Failed', 'failed'])])
            print(f"  • 錯誤行數：{error_count}")
            print(f"  • 顯示行數：{len(display_lines)}")

    except Exception as e:
        print(f"❌ 讀取日誌失敗：{e}")


def plot_data(args):
    """繪製數據圖表"""
    try:
        import matplotlib.pyplot as plt
        from datetime import datetime, timedelta

        # 設置中文字體
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS',
                                           'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        database = Database()
        site_id = args.site_id

        # 如果沒有提供站點 ID，互動式選擇
        if not site_id:
            sites = database.get_sites()
            if not sites:
                print("❌ 數據庫中沒有站點，請先添加站點")
                return

            print("\n📊 選擇要分析的站點:")
            for i, site in enumerate(sites, 1):
                print(f"  {i}. {site['name']} (ID: {site['id']})")

            try:
                choice = int(input(f"請選擇站點 (1-{len(sites)}): ").strip())
                if 1 <= choice <= len(sites):
                    site_id = sites[choice - 1]['id']
                else:
                    print("❌ 無效選擇")
                    return
            except ValueError:
                print("❌ 請輸入數字")
                return

        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        with database.get_connection() as conn:
            if args.type == 'clicks':
                plot_clicks_trend(conn, site_id, start_str, end_str, args.save)
            elif args.type == 'rankings':
                plot_rankings_trend(
                    conn, site_id, start_str, end_str, args.save)
            elif args.type == 'coverage':
                plot_data_coverage(conn, site_id, args.save)

    except ImportError:
        print("❌ 需要安裝 matplotlib：pip install matplotlib")
    except Exception as e:
        print(f"❌ 繪圖失敗：{e}")


def plot_clicks_trend(conn, site_id, start_date, end_date, save_path=None):
    """繪製點擊量趨勢圖"""
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime

    # 查詢每日點擊量數據
    query = '''
        SELECT date, SUM(clicks) as total_clicks, SUM(impressions) as total_impressions
        FROM daily_rankings
        WHERE site_id = ? AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date
    '''

    results = conn.execute(query, (site_id, start_date, end_date)).fetchall()

    if not results:
        print("❌ 沒有找到數據")
        return

    dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in results]
    clicks = [row[1] for row in results]
    impressions = [row[2] for row in results]

    # 創建圖表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # 點擊量趨勢
    ax1.plot(dates, clicks, marker='o', linewidth=2, color='#1f77b4')
    ax1.set_title(
        f'每日點擊量趨勢 (站點 ID: {site_id})',
        fontsize=14,
        fontweight='bold')
    ax1.set_ylabel('點擊量', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

    # 展示量趨勢
    ax2.plot(dates, impressions, marker='s', linewidth=2, color='#ff7f0e')
    ax2.set_title('每日展示量趨勢', fontsize=14, fontweight='bold')
    ax2.set_xlabel('日期', fontsize=12)
    ax2.set_ylabel('展示量', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 圖表已保存到：{save_path}")
    else:
        plt.show()


def plot_rankings_trend(conn, site_id, start_date, end_date, save_path=None):
    """繪製排名趨勢圖"""
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime

    # 查詢平均排名數據
    query = '''
        SELECT date, AVG(position) as avg_position, COUNT(*) as keyword_count
        FROM daily_rankings
        WHERE site_id = ? AND date BETWEEN ? AND ? AND position > 0
        GROUP BY date
        ORDER BY date
    '''

    results = conn.execute(query, (site_id, start_date, end_date)).fetchall()

    if not results:
        print("❌ 沒有找到排名數據")
        return

    dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in results]
    avg_positions = [row[1] for row in results]
    keyword_counts = [row[2] for row in results]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # 平均排名趨勢 (排名越低越好，所以Y軸反轉)
    ax1.plot(dates, avg_positions, marker='o', linewidth=2, color='#2ca02c')
    ax1.set_title(f'平均排名趨勢 (站點 ID: {site_id})', fontsize=14, fontweight='bold')
    ax1.set_ylabel('平均排名', fontsize=12)
    ax1.invert_yaxis()  # 反轉Y軸，排名1在頂部
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

    # 關鍵字數量趨勢
    ax2.plot(dates, keyword_counts, marker='s', linewidth=2, color='#d62728')
    ax2.set_title('每日關鍵字數量', fontsize=14, fontweight='bold')
    ax2.set_xlabel('日期', fontsize=12)
    ax2.set_ylabel('關鍵字數量', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 圖表已保存到：{save_path}")
    else:
        plt.show()


def plot_data_coverage(conn, site_id, save_path=None):
    """繪製數據覆蓋情況"""
    import matplotlib.pyplot as plt
    from datetime import datetime

    # 查詢數據覆蓋情況
    query = '''
        SELECT date, COUNT(*) as record_count
        FROM daily_rankings
        WHERE site_id = ?
        GROUP BY date
        ORDER BY date
    '''

    results = conn.execute(query, (site_id,)).fetchall()

    if not results:
        print("❌ 沒有找到數據")
        return

    dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in results]
    record_counts = [row[1] for row in results]

    plt.figure(figsize=(12, 6))
    plt.bar(dates, record_counts, alpha=0.7, color='#9467bd')
    plt.title(f'數據覆蓋情況 (站點 ID: {site_id})', fontsize=14, fontweight='bold')
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('記錄數量', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 圖表已保存到：{save_path}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
