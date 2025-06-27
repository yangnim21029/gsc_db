#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC 數據管理工具 - 主程序
提供互動式選單，方便用戶選擇和執行各種功能
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta

try:
    from services.gsc_client import GSCClient
    from services.database import Database
except ImportError as e:
    print(f"❌ 導入模塊失敗: {e}")
    print("請確保所有依賴模塊都存在")
    sys.exit(1)


class GSCMain:
    def __init__(self):
        self.gsc_client = GSCClient()
        self.database = Database()

    def main_menu(self):
        """主選單"""
        while True:
            print("\n" + "=" * 60)
            print("🚀 Google Search Console 數據分析平台")
            print("=" * 60)

            print("1. Google 帳號連接設定 (第一次使用必須)")
            print("2. 網站管理 (添加要分析的網站)")
            print("3. 批次下載設定 (智能檢查並下載最新資料)")
            print("4. 生成分析報告 (製作圖表和統計資料)")
            print("5. 製作互動圖表 (網頁版互動式圖表)")
            print("6. API 使用監控 (查看配額和使用量)")
            print("7. 系統工具 (日誌、健康檢查等)")
            print("0. 退出")

            choice = input("\n請選擇功能: ").strip()

            if choice == '1':
                self.auth_menu()
            elif choice == '2':
                self.site_menu()
            elif choice == '3':
                self.sync_menu()
            elif choice == '4':
                self.analysis_menu()
            elif choice == '5':
                self.chart_menu()
            elif choice == '6':
                self.api_monitor_menu()
            elif choice == '7':
                self.system_tools_menu()
            elif choice == '0':
                print("👋 再見！")
                break
            else:
                print("❌ 無效選擇，請重新輸入")

    def auth_menu(self):
        """認證管理選單"""
        print("\n🔑 Google 帳號連接設定")
        print("-" * 30)

        if self.gsc_client.is_authenticated():
            print("✅ 已成功連接 Google 帳號")
            print("1. 重新連接帳號")
            print("2. 測試連接狀態")
            print("0. 返回主選單")

            choice = input("請選擇: ").strip()
            if choice == '1':
                self.run_script('console_commands.py', ['auth'])
            elif choice == '2':
                self.test_gsc_connection()
        else:
            print("❌ 尚未連接 Google 帳號")
            print("正在啟動 Google 帳號連接程序...")
            self.run_script('console_commands.py', ['auth'])

    def site_menu(self):
        """網站管理選單"""
        print("\n🌐 網站管理")
        print("-" * 30)

        print("1. 查看已添加的網站")
        print("2. 從 Google 帳號添加新網站")
        print("3. 查看網站數據完整度")
        print("0. 返回主選單")

        choice = input("請選擇: ").strip()

        if choice == '1':
            self.run_script('console_commands.py', ['sites'])
        elif choice == '2':
            self.add_sites_from_gsc()
        elif choice == '3':
            sites = self.get_sites_with_selection()
            if sites:
                site_id = self.select_site(sites)
                if site_id:
                    self.run_script(
                        'console_commands.py', [
                            'coverage', '--site-id', str(site_id)])

    def add_sites_from_gsc(self):
        """從 Google Search Console 添加網站"""
        print("\n📋 從 Google Search Console 添加網站")
        print("-" * 40)
        
        if not self.gsc_client.is_authenticated():
            print("❌ 請先完成 Google 認證")
            return
            
        try:
            # 獲取 GSC 中的所有網站
            print("🔍 正在獲取您的 Google Search Console 網站...")
            gsc_sites = self.gsc_client.get_sites()
            
            if not gsc_sites:
                print("❌ 在您的 Google Search Console 中沒有找到任何網站")
                return
                
            # 獲取數據庫中已有的網站
            db_sites = self.database.get_sites()
            existing_domains = {site['domain'] for site in db_sites}
            
            print(f"\n📊 找到 {len(gsc_sites)} 個 Google Search Console 網站:")
            print("\n" + "=" * 60)
            
            available_sites = []
            for i, site_url in enumerate(gsc_sites, 1):
                # 清理網站名稱用於顯示
                display_name = site_url.replace('sc-domain:', '').replace('https://', '').replace('http://', '')
                
                if site_url in existing_domains:
                    print(f"{i:2d}. {display_name} (已添加) ✅")
                else:
                    print(f"{i:2d}. {display_name} (未添加)")
                    available_sites.append((i, site_url, display_name))
            
            if not available_sites:
                print("\n✅ 所有 Google Search Console 網站都已添加到數據庫中！")
                return
                
            print("\n可添加的網站:")
            for i, site_url, display_name in available_sites:
                print(f"  {i}. {display_name}")
                
            print("\n選項:")
            print("  輸入網站編號添加單個網站")
            print("  輸入 'all' 添加所有未添加的網站")
            print("  直接按 Enter 返回")
            
            choice = input("\n請選擇: ").strip()
            
            if choice.lower() == 'all':
                # 添加所有未添加的網站
                print("\n🚀 開始添加所有未添加的網站...")
                for i, site_url, display_name in available_sites:
                    try:
                        site_id = self.database.add_site(site_url, display_name)
                        print(f"✅ 已添加: {display_name} (ID: {site_id})")
                    except Exception as e:
                        print(f"❌ 添加失敗 {display_name}: {e}")
                        
                print(f"\n🎉 完成！已添加 {len(available_sites)} 個網站")
                
            elif choice.isdigit():
                # 添加單個網站
                choice_num = int(choice)
                selected_site = next((item for item in available_sites if item[0] == choice_num), None)
                
                if selected_site:
                    i, site_url, display_name = selected_site
                    try:
                        site_id = self.database.add_site(site_url, display_name)
                        print(f"\n✅ 已添加: {display_name} (ID: {site_id})")
                    except Exception as e:
                        print(f"\n❌ 添加失敗: {e}")
                else:
                    print("❌ 無效的網站編號")
            elif choice == '':
                return
            else:
                print("❌ 無效的選擇")
                
        except Exception as e:
            print(f"❌ 獲取網站列表失敗: {e}")

    def sync_menu(self):
        """數據同步選單"""
        print("\n📊 批次下載設定")
        print("-" * 30)

        print("1. 智能快速下載 (自動檢查缺失數據，考慮Google延遲)")
        print("2. 自定義日期範圍下載 (手動設定日期)")
        print("3. 選擇單一網站下載")
        print("4. 整月數據下載 (選擇年月，下載該月所有日期)")
        print("0. 返回主選單")

        choice = input("請選擇: ").strip()

        if choice == '1':
            self.quick_sync()
        elif choice == '2':
            self.custom_date_sync()
        elif choice == '3':
            self.single_site_sync()
        elif choice == '4':
            self.bulk_month_sync()

    def analysis_menu(self):
        """數據分析與報告選單"""
        print("\n📈 生成分析報告")
        print("-" * 30)

        print("1. 製作月度完整報告")
        print("2. 關鍵字搜尋趨勢分析")
        print("3. 網頁流量效能分析")
        print("4. 每小時時段分析")
        print("5. 自定義分析圖表")
        print("0. 返回主選單")

        choice = input("請選擇: ").strip()

        if choice == '1':
            self.generate_monthly_report()
        elif choice == '2':
            self.keyword_analysis()
        elif choice == '3':
            self.page_analysis()
        elif choice == '4':
            self.hourly_analysis_menu()
        elif choice == '5':
            self.custom_chart()

    def hourly_analysis_menu(self):
        """每小時分析子選單"""
        print("\n⏰ 每小時時段分析")
        print("-" * 30)

        print("1. 智能下載每小時數據 (檢查缺失，僅限10天)")
        print("2. 查看時段流量統計")
        print("3. 檢查小時數據完整度")
        print("4. 製作時段趨勢圖表")
        print("0. 返回上一層選單")

        choice = input("請選擇: ").strip()

        if choice == '1':
            self.smart_hourly_sync()
        elif choice == '2':
            self.hourly_summary()
        elif choice == '3':
            self.hourly_coverage()
        elif choice == '4':
            self.run_script('hourly_performance_analyzer.py')

    def smart_hourly_sync(self):
        """智能每小時數據同步"""
        # Google 每小時數據只提供最近10天，且有更多延遲
        available_end_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        print("🔍 檢查每小時數據覆蓋情況...")
        print(f"⚠️  每小時數據僅提供最近10天，且有5天延遲")
        print(f"⚠️  檢查範圍: {start_date} 至 {available_end_date}")
        
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if not site_id:
            return
            
        site = next(s for s in sites if s['id'] == site_id)
        
        # 檢查該站點的每小時數據覆蓋
        try:
            with self.database.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT MIN(date) as first_date, MAX(date) as last_date, COUNT(DISTINCT date) as date_count
                    FROM hourly_rankings 
                    WHERE site_id = ? AND date BETWEEN ? AND ?
                ''', (site_id, start_date, available_end_date))
                
                result = cursor.fetchone()
                if result and result['last_date']:
                    print(f"✅ 現有每小時數據: {result['first_date']} 至 {result['last_date']} ({result['date_count']} 天)")
                    
                    # 計算缺少的日期
                    last_date = datetime.strptime(result['last_date'], '%Y-%m-%d')
                    end_datetime = datetime.strptime(available_end_date, '%Y-%m-%d')
                    
                    if last_date >= end_datetime:
                        print("✅ 每小時數據已是最新，無需下載！")
                        return
                    else:
                        missing_start = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
                        print(f"📅 需要補充: {missing_start} 至 {available_end_date}")
                else:
                    print(f"📅 沒有每小時數據，建議下載: {start_date} 至 {available_end_date}")
                    
        except Exception as e:
            print(f"⚠️  檢查數據時出錯: {e}")
        
        confirm = input("確定要下載每小時數據嗎？ (y/N): ").strip().lower()
        if confirm == 'y':
            args = ['hourly-sync', '--site-url', site['domain']]
            args.extend(['--start-date', start_date, '--end-date', available_end_date])
            self.run_script('console_commands.py', args)

    def hourly_summary(self):
        """每小時總結"""
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if site_id:
            args = ['hourly-summary', '--site-id', str(site_id)]

            date = input("日期 (YYYY-MM-DD，可選): ").strip()
            if date:
                args.extend(['--date', date])

            self.run_script('console_commands.py', args)

    def hourly_coverage(self):
        """每小時數據覆蓋"""
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if site_id:
            self.run_script(
                'console_commands.py', [
                    'hourly-coverage', '--site-id', str(site_id)])

    def chart_menu(self):
        """互動式圖表選單"""
        print("\n🎯 製作互動圖表")
        print("-" * 30)

        print("1. 關鍵字效能氣泡圖")
        print("2. 多網站比較圖表")
        print("3. 網頁效能象限分析")
        print("4. 生成所有互動圖表")
        print("0. 返回主選單")

        choice = input("請選擇: ").strip()

        if choice in ['1', '2', '3', '4']:
            self.run_script('interactive_data_visualizer.py')

    def api_monitor_menu(self):
        """API 使用監控選單"""
        print("\n📊 API 使用監控")
        print("-" * 30)
        
        self.run_script('console_commands.py', ['api-status'])

    def system_tools_menu(self):
        """系統工具選單"""
        print("\n🛠️  系統工具")
        print("-" * 30)

        print("1. 查看系統運作日誌")
        print("2. 檢查系統健康狀態")
        print("3. 查看數據庫統計")
        print("0. 返回主選單")

        choice = input("請選擇: ").strip()

        if choice == '1':
            lines = input("顯示行數 (默認50): ").strip()
            lines = lines if lines.isdigit() else '50'
            self.run_script('console_commands.py', ['logs', '--lines', lines])
        elif choice == '2':
            self.run_script('system_health_check.py')
        elif choice == '3':
            self.run_script('console_commands.py', ['coverage'])

    def quick_sync(self):
        """快速同步最近7天"""
        # 考慮 Google Search Console 2-3天延遲
        available_end_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        # 先檢查數據庫中的覆蓋情況
        print("🔍 檢查現有數據覆蓋情況...")
        print(f"⚠️  考慮到 Google 數據延遲，檢查到 {available_end_date}")
        
        try:
            sites = self.database.get_sites()
            missing_dates = self.check_missing_dates(sites, start_date, available_end_date)
            
            if not missing_dates:
                print("✅ 所有網站的數據都是最新的，無需下載！")
                print(f"💡 Google 通常有2-3天數據延遲，{available_end_date}之後的數據可能還未提供")
                return
                
            print(f"📅 發現需要補充的日期: {len(missing_dates)} 個日期範圍")
            for site_name, dates in missing_dates.items():
                print(f"  • {site_name}: {dates['start']} 至 {dates['end']}")
                
        except Exception as e:
            print(f"⚠️  檢查數據時出錯，將進行完整同步: {e}")
        
        print(f"📅 建議同步日期範圍: {start_date} 至 {available_end_date}")
        print(f"💡 跳過 {available_end_date} 之後的日期（Google 數據延遲）")
        confirm = input("確定要開始下載嗎？ (y/N): ").strip().lower()

        if confirm == 'y':
            self.run_script('console_commands.py', [
                'sync', '--all-sites',
                '--start-date', start_date,
                '--end-date', available_end_date
            ])

    def check_missing_dates(self, sites, start_date, end_date):
        """檢查各站點缺少的日期範圍"""
        missing_dates = {}
        
        for site in sites:
            try:
                # 檢查該站點的數據覆蓋情況
                with self.database.get_connection() as conn:
                    cursor = conn.execute('''
                        SELECT MIN(date) as first_date, MAX(date) as last_date
                        FROM daily_rankings 
                        WHERE site_id = ? AND date BETWEEN ? AND ?
                    ''', (site['id'], start_date, end_date))
                    
                    result = cursor.fetchone()
                    if result and result['last_date']:
                        # 計算缺少的日期範圍
                        last_date = datetime.strptime(result['last_date'], '%Y-%m-%d')
                        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                        
                        if last_date < end_datetime:
                            missing_start = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
                            missing_dates[site['name']] = {
                                'start': missing_start,
                                'end': end_date
                            }
                    else:
                        # 沒有任何數據
                        missing_dates[site['name']] = {
                            'start': start_date,
                            'end': end_date
                        }
                        
            except Exception as e:
                print(f"⚠️  檢查 {site['name']} 數據時出錯: {e}")
                
        return missing_dates

    def custom_date_sync(self):
        """自定義日期範圍同步"""
        # 計算建議的最新日期
        suggested_end = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        print("💡 Google Search Console 數據延遲提醒:")
        print(f"   建議結束日期不晚於: {suggested_end} (考慮2-3天延遲)")
        print()
        
        start_date = input("開始日期 (YYYY-MM-DD): ").strip()
        end_date = input(f"結束日期 (YYYY-MM-DD，建議 <= {suggested_end}): ").strip()

        if start_date and end_date:
            # 檢查是否超過建議日期
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                suggested_dt = datetime.strptime(suggested_end, '%Y-%m-%d')
                
                if end_dt > suggested_dt:
                    print(f"⚠️  警告: 結束日期 {end_date} 可能超過 Google 數據可用範圍")
                    confirm = input("   仍要繼續嗎？ (y/N): ").strip().lower()
                    if confirm != 'y':
                        return
            except ValueError:
                print("⚠️  日期格式錯誤，請使用 YYYY-MM-DD 格式")
                return
                
            args = [
                'sync',
                '--all-sites',
                '--start-date',
                start_date,
                '--end-date',
                end_date]

            force = input("是否強制重建數據？ (y/N): ").strip().lower()
            if force == 'y':
                args.append('--force')

            self.run_script('console_commands.py', args)

    def single_site_sync(self):
        """單一站點同步"""
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if site_id:
            start_date = input("開始日期 (YYYY-MM-DD，可選): ").strip()
            end_date = input("結束日期 (YYYY-MM-DD，可選): ").strip()

            args = ['sync', '--site-id', str(site_id)]
            if start_date:
                args.extend(['--start-date', start_date])
            if end_date:
                args.extend(['--end-date', end_date])

            self.run_script('console_commands.py', args)

    def generate_monthly_report(self):
        """生成月度報告"""
        print("選擇報告類型:")
        print("1. 所有站點月度報告")
        print("2. 單一站點月度報告")

        choice = input("請選擇: ").strip()

        if choice == '1':
            self.run_script('analytics_report_builder.py')
        elif choice == '2':
            sites = self.get_sites_with_selection()
            if sites:
                site_id = self.select_site(sites)
                if site_id:
                    site = next(s for s in sites if s['id'] == site_id)
                    # 傳遞站點信息給報告生成器
                    os.environ['GSC_SITE_ID'] = str(site_id)
                    os.environ['GSC_SITE_NAME'] = site['name']
                    self.run_script('analytics_report_builder.py')

    def keyword_analysis(self):
        """關鍵字分析"""
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if site_id:
            args = ['plot', '--site-id', str(site_id), '--type', 'clicks']
            self.run_script('console_commands.py', args)

    def page_analysis(self):
        """頁面分析"""
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if site_id:
            args = ['plot', '--site-id', str(site_id), '--type', 'rankings']
            self.run_script('console_commands.py', args)

    def custom_chart(self):
        """自定義圖表"""
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if site_id:
            print("圖表類型:")
            print("1. 點擊量趨勢")
            print("2. 排名趨勢")
            print("3. 數據覆蓋情況")

            chart_choice = input("請選擇: ").strip()
            chart_types = {'1': 'clicks', '2': 'rankings', '3': 'coverage'}

            if chart_choice in chart_types:
                days = input("天數範圍 (默認30): ").strip()
                days = days if days.isdigit() else '30'

                args = [
                    'plot', '--site-id', str(site_id),
                    '--type', chart_types[chart_choice],
                    '--days', days
                ]

                self.run_script('console_commands.py', args)

    def get_sites_with_selection(self):
        """獲取站點列表並提供選擇"""
        try:
            sites = self.database.get_sites()
            if not sites:
                print("❌ 數據庫中沒有站點")
                print("請先添加站點")
                return None
            return sites
        except Exception as e:
            print(f"❌ 獲取站點失敗: {e}")
            return None

    def select_site(self, sites):
        """讓用戶選擇站點"""
        print("\n📋 可用站點:")
        for i, site in enumerate(sites, 1):
            print(f"  {i}. {site['name']} (ID: {site['id']})")

        try:
            choice = int(input(f"請選擇站點 (1-{len(sites)}): ").strip())
            if 1 <= choice <= len(sites):
                return sites[choice - 1]['id']
            else:
                print("❌ 無效選擇")
                return None
        except ValueError:
            print("❌ 請輸入數字")
            return None

    def test_gsc_connection(self):
        """測試 GSC 連接"""
        try:
            sites = self.gsc_client.get_sites()
            print(f"✅ 連接成功！找到 {len(sites)} 個站點")
        except Exception as e:
            print(f"❌ 連接失敗: {e}")

    def run_script(self, script_name, args=None):
        """運行指定的腳本"""
        cmd = ['python', script_name]
        if args:
            cmd.extend(args)

        try:
            print(f"🚀 執行: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ 執行失敗: {e}")
        except FileNotFoundError:
            print(f"❌ 找不到文件: {script_name}")

    def hourly_sync(self):
        """每小時數據同步（原版）"""
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if site_id:
            site = next(s for s in sites if s['id'] == site_id)
            args = ['hourly-sync', '--site-url', site['domain']]

            start_date = input("開始日期 (YYYY-MM-DD，默認昨天): ").strip()
            if start_date:
                args.extend(['--start-date', start_date])

            self.run_script('console_commands.py', args)

    def bulk_month_sync(self):
        """批量月份同步"""
        print("\n📅 整月數據下載工具")
        print("-" * 30)
        print("此工具會下載指定月份的完整數據 (整個月每一天)")
        print("採用逐日下載方式，避免大量數據導致API超時")
        print()
        
        # 選擇站點
        sites = self.get_sites_with_selection()
        if not sites:
            return

        site_id = self.select_site(sites)
        if not site_id:
            return
            
        site = next(s for s in sites if s['id'] == site_id)
        print(f"已選擇站點: {site['name']}")
        
        # 輸入年月
        try:
            year = int(input("輸入年份 (例如: 2025): ").strip())
            month = int(input("輸入月份 (1-12，例如: 6 代表6月): ").strip())
            
            if not (1 <= month <= 12):
                print("❌ 月份必須在 1-12 之間")
                return
                
            if year < 2020 or year > 2030:
                print("❌ 年份範圍不合理")
                return
                
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        # 計算該月有多少天
        from calendar import monthrange
        _, days_in_month = monthrange(year, month)
        
        print(f"\n即將下載: {site['name']} - {year}年{month}月 (共{days_in_month}天)")
        print(f"日期範圍: {year}-{month:02d}-01 至 {year}-{month:02d}-{days_in_month}")
        print("⚠️  此過程可能需要較長時間，建議在網絡穩定時執行")
        print("💡 系統會跳過已存在的數據，只下載缺失的日期")
        
        confirm = input("\n確定要開始嗎？ (y/N): ").strip().lower()
        if confirm == 'y':
            self.run_script('bulk_data_synchronizer.py', [str(site_id), str(year), str(month)])


def main():
    """主程序入口"""
    try:
        app = GSCMain()
        app.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 用戶中斷，再見！")
    except Exception as e:
        print(f"❌ 程序錯誤: {e}")


if __name__ == '__main__':
    main()
