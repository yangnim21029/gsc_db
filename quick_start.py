#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC 數據導出工具 - 快速啟動腳本
這是一個簡化版本，專注於核心功能
"""

import sys
from datetime import datetime, timedelta

try:
    from services.gsc_client import GSCClient
    from services.database import Database
except ImportError as e:
    print(f"❌ 導入模塊失敗: {e}")
    print("請確保所有依賴模塊都存在")
    sys.exit(1)

def main():
    print("🚀 GSC 數據導出工具 - 快速啟動")
    print("=" * 50)
    
    # 檢查認證狀態
    gsc_client = GSCClient()
    if not gsc_client.is_authenticated():
        print("❌ 未認證 GSC API")
        print("\n請先完成認證:")
        print("1. 運行: python gsc_simple.py auth")
        print("2. 或使用現有的 Web 界面進行認證")
        return
    
    print("✅ GSC API 已認證")
    
    # 初始化組件
    database = Database()
    
    # 獲取站點列表
    try:
        sites = database.get_sites()
        if not sites:
            print("\n❌ 數據庫中沒有站點")
            print("請先添加站點:")
            print("python gsc_simple.py add-site 'https://example.com/'")
            return
        
        print(f"\n📋 找到 {len(sites)} 個站點:")
        for site in sites:
            print(f"  - {site['name']} (ID: {site['id']})")
        
    except Exception as e:
        print(f"❌ 獲取站點失敗: {e}")
        return
    
    # 檢查數據覆蓋情況 (簡化版本)
    try:
        print("\n📊 檢查數據覆蓋情況...")
        
        for site in sites:
            # 獲取該站點的排名數據統計
            rankings = database.get_rankings(site_id=site['id'])
            
            if not rankings:
                print(f"\n站點: {site['name']}")
                print("  📭 尚無數據，建議先同步一些數據")
            else:
                # 獲取最新日期
                latest_ranking = max(rankings, key=lambda x: x.get('date', ''))
                latest_date = latest_ranking.get('date', '無')
                
                print(f"\n站點: {site['name']}")
                print(f"  數據記錄: {len(rankings)}")
                print(f"  最新數據: {latest_date}")
        
    except Exception as e:
        print(f"❌ 檢查數據覆蓋失敗: {e}")
    
    # 檢查最近的任務 (簡化版本)
    try:
        recent_tasks = database.get_recent_tasks(limit=5)
        if recent_tasks:
            print(f"\n📝 最近 {len(recent_tasks)} 個任務:")
            for task in recent_tasks:
                print(f"  - 任務類型: {task.get('task_type', 'N/A')}")
                print(f"    站點: {task.get('site_name', 'N/A')}")
                print(f"    狀態: {task.get('status', 'N/A')}")
                print(f"    記錄數: {task.get('total_records', 0)}")
        else:
            print("\n📝 暫無任務記錄")
    except Exception as e:
        print(f"⚠️  檢查任務狀態失敗: {e}")
    
    # 提供快速操作建議
    print("\n💡 快速操作建議:")
    
    # 計算最近7天的日期範圍
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"1. 同步最近7天數據: python gsc_simple.py sync --all-sites --start-date {start_date} --end-date {end_date}")
    print("2. 查看數據覆蓋: python gsc_simple.py coverage")
    print("3. 查看進度: python gsc_simple.py progress")
    print("4. 同步每小時數據: python gsc_simple.py hourly-sync --site-id 1")
    print("5. 查看所有命令: python gsc_simple.py --help")
    
    print("\n📚 詳細說明請查看: README_CLI.md")

if __name__ == '__main__':
    main() 