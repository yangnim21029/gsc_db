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
        """顯示主選單"""
        while True:
            print("\n" + "="*60)
            print("🚀 GSC 數據管理工具")
            print("="*60)
            
            # 檢查認證狀態
            auth_status = "✅ 已認證" if self.gsc_client.is_authenticated() else "❌ 未認證"
            print(f"認證狀態: {auth_status}")
            
            # 獲取站點數量
            try:
                sites = self.database.get_sites()
                site_count = len(sites)
            except:
                site_count = 0
            print(f"已註冊站點: {site_count} 個")
            
            print("\n請選擇功能:")
            print("1. 🔑 API 認證管理")
            print("2. 🌐 站點管理")
            print("3. 📊 數據同步")
            print("4. 📈 數據分析與報告")
            print("5. ⏰ 每小時數據分析")
            print("6. 🎯 互動式圖表")
            print("7. 📋 系統狀態檢查")
            print("8. 🛠️  高級工具")
            print("0. 退出")
            
            choice = input("\n請輸入選項 (0-8): ").strip()
            
            if choice == '0':
                print("👋 再見！")
                break
            elif choice == '1':
                self.auth_menu()
            elif choice == '2':
                self.site_menu()
            elif choice == '3':
                self.sync_menu()
            elif choice == '4':
                self.analysis_menu()
            elif choice == '5':
                self.hourly_menu()
            elif choice == '6':
                self.chart_menu()
            elif choice == '7':
                self.status_menu()
            elif choice == '8':
                self.advanced_menu()
            else:
                print("❌ 無效選項，請重新選擇")
    
    def auth_menu(self):
        """認證管理選單"""
        print("\n🔑 API 認證管理")
        print("-"*30)
        
        if self.gsc_client.is_authenticated():
            print("✅ 目前已認證")
            print("1. 重新認證")
            print("2. 測試連接")
            print("0. 返回主選單")
            
            choice = input("請選擇: ").strip()
            if choice == '1':
                self.run_script('gsc_cli_manager.py', ['auth'])
            elif choice == '2':
                self.test_gsc_connection()
        else:
            print("❌ 尚未認證")
            print("正在啟動認證流程...")
            self.run_script('gsc_cli_manager.py', ['auth'])
    
    def site_menu(self):
        """站點管理選單"""
        print("\n🌐 站點管理")
        print("-"*30)
        
        print("1. 查看所有站點")
        print("2. 添加站點")
        print("3. 查看站點數據覆蓋")
        print("0. 返回主選單")
        
        choice = input("請選擇: ").strip()
        
        if choice == '1':
            self.run_script('gsc_cli_manager.py', ['sites'])
        elif choice == '2':
            site_url = input("請輸入站點 URL (例如: https://example.com/): ").strip()
            if site_url:
                self.run_script('gsc_cli_manager.py', ['add-site', site_url])
        elif choice == '3':
            sites = self.get_sites_with_selection()
            if sites:
                site_id = self.select_site(sites)
                if site_id:
                    self.run_script('gsc_cli_manager.py', ['coverage', '--site-id', str(site_id)])
    
    def sync_menu(self):
        """數據同步選單"""
        print("\n📊 數據同步")
        print("-"*30)
        
        print("1. 快速同步 (最近7天，所有站點)")
        print("2. 自定義日期範圍同步")
        print("3. 單一站點同步")
        print("4. 批量同步")
        print("5. 查看同步進度")
        print("0. 返回主選單")
        
        choice = input("請選擇: ").strip()
        
        if choice == '1':
            self.quick_sync()
        elif choice == '2':
            self.custom_date_sync()
        elif choice == '3':
            self.single_site_sync()
        elif choice == '4':
            self.run_script('gsc_batch_syncer.py')
        elif choice == '5':
            self.run_script('gsc_cli_manager.py', ['progress'])
    
    def analysis_menu(self):
        """數據分析與報告選單"""
        print("\n📈 數據分析與報告")
        print("-"*30)
        
        print("1. 生成月度報告")
        print("2. 關鍵字趨勢分析")
        print("3. 頁面效能分析")
        print("4. 自定義圖表")
        print("0. 返回主選單")
        
        choice = input("請選擇: ").strip()
        
        if choice == '1':
            self.generate_monthly_report()
        elif choice == '2':
            self.keyword_analysis()
        elif choice == '3':
            self.page_analysis()
        elif choice == '4':
            self.custom_chart()
    
    def hourly_menu(self):
        """每小時數據分析選單"""
        print("\n⏰ 每小時數據分析")
        print("-"*30)
        
        print("1. 同步每小時數據")
        print("2. 查看每小時總結")
        print("3. 每小時數據覆蓋情況")
        print("4. 生成每小時趨勢圖")
        print("0. 返回主選單")
        
        choice = input("請選擇: ").strip()
        
        if choice == '1':
            self.hourly_sync()
        elif choice == '2':
            self.hourly_summary()
        elif choice == '3':
            self.hourly_coverage()
        elif choice == '4':
            self.run_script('gsc_hourly_analyzer.py')
    
    def chart_menu(self):
        """互動式圖表選單"""
        print("\n🎯 互動式圖表")
        print("-"*30)
        
        print("1. 關鍵字氣泡圖")
        print("2. 多站點比較圖")
        print("3. 頁面效能象限圖")
        print("4. 生成所有互動圖表")
        print("0. 返回主選單")
        
        choice = input("請選擇: ").strip()
        
        if choice in ['1', '2', '3', '4']:
            self.run_script('gsc_interactive_charts.py')
    
    def status_menu(self):
        """系統狀態檢查選單"""
        print("\n📋 系統狀態檢查")
        print("-"*30)
        
        self.run_script('gsc_status_checker.py')
    
    def advanced_menu(self):
        """高級工具選單"""
        print("\n🛠️  高級工具")
        print("-"*30)
        
        print("1. API 使用狀態")
        print("2. 查看系統日誌")
        print("3. 數據庫維護")
        print("4. 導出數據")
        print("0. 返回主選單")
        
        choice = input("請選擇: ").strip()
        
        if choice == '1':
            self.run_script('gsc_cli_manager.py', ['api-status'])
        elif choice == '2':
            lines = input("顯示行數 (默認50): ").strip()
            lines = lines if lines.isdigit() else '50'
            self.run_script('gsc_cli_manager.py', ['logs', '--lines', lines])
        elif choice == '3':
            print("數據庫維護功能開發中...")
        elif choice == '4':
            print("數據導出功能開發中...")
    
    def quick_sync(self):
        """快速同步最近7天"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        print(f"📅 同步日期範圍: {start_date} 至 {end_date}")
        confirm = input("確定要開始同步嗎？ (y/N): ").strip().lower()
        
        if confirm == 'y':
            self.run_script('gsc_cli_manager.py', [
                'sync', '--all-sites', 
                '--start-date', start_date, 
                '--end-date', end_date
            ])
    
    def custom_date_sync(self):
        """自定義日期範圍同步"""
        start_date = input("開始日期 (YYYY-MM-DD): ").strip()
        end_date = input("結束日期 (YYYY-MM-DD): ").strip()
        
        if start_date and end_date:
            args = ['sync', '--all-sites', '--start-date', start_date, '--end-date', end_date]
            
            force = input("是否強制重建數據？ (y/N): ").strip().lower()
            if force == 'y':
                args.append('--force')
            
            self.run_script('gsc_cli_manager.py', args)
    
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
            
            self.run_script('gsc_cli_manager.py', args)
    
    def hourly_sync(self):
        """每小時數據同步"""
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
            
            self.run_script('gsc_cli_manager.py', args)
    
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
            
            self.run_script('gsc_cli_manager.py', args)
    
    def hourly_coverage(self):
        """每小時數據覆蓋"""
        sites = self.get_sites_with_selection()
        if not sites:
            return
        
        site_id = self.select_site(sites)
        if site_id:
            self.run_script('gsc_cli_manager.py', ['hourly-coverage', '--site-id', str(site_id)])
    
    def generate_monthly_report(self):
        """生成月度報告"""
        print("選擇報告類型:")
        print("1. 所有站點月度報告")
        print("2. 單一站點月度報告")
        
        choice = input("請選擇: ").strip()
        
        if choice == '1':
            self.run_script('gsc_report_generator.py')
        elif choice == '2':
            sites = self.get_sites_with_selection()
            if sites:
                site_id = self.select_site(sites)
                if site_id:
                    site = next(s for s in sites if s['id'] == site_id)
                    # 傳遞站點信息給報告生成器
                    os.environ['GSC_SITE_ID'] = str(site_id)
                    os.environ['GSC_SITE_NAME'] = site['name']
                    self.run_script('gsc_report_generator.py')
    
    def keyword_analysis(self):
        """關鍵字分析"""
        sites = self.get_sites_with_selection()
        if not sites:
            return
        
        site_id = self.select_site(sites)
        if site_id:
            args = ['plot', '--site-id', str(site_id), '--type', 'clicks']
            self.run_script('gsc_cli_manager.py', args)
    
    def page_analysis(self):
        """頁面分析"""
        sites = self.get_sites_with_selection()
        if not sites:
            return
        
        site_id = self.select_site(sites)
        if site_id:
            args = ['plot', '--site-id', str(site_id), '--type', 'rankings']
            self.run_script('gsc_cli_manager.py', args)
    
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
                
                self.run_script('gsc_cli_manager.py', args)
    
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
                return sites[choice-1]['id']
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