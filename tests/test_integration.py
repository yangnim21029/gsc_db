#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC CLI 整合測試腳本
展示新的 Typer CLI 和重構後的批量同步功能
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_command(command, description="", capture_output=True):
    """執行命令並顯示結果"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"💻 執行命令: {command}")
    print('='*60)
    
    try:
        if capture_output:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            
            if result.stdout:
                print("✅ 輸出:")
                print(result.stdout)
            
            if result.stderr:
                print("⚠️  警告/錯誤:")
                print(result.stderr)
                
            return result.returncode == 0
        else:
            # 直接執行，不捕獲輸出
            result = subprocess.run(command.split(), cwd=Path(__file__).parent)
            return result.returncode == 0
            
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        return False


def test_cli_commands():
    """測試基本的 CLI 命令"""
    print("🚀 開始測試 GSC CLI 命令")
    
    # 1. 顯示主幫助
    run_command("python main.py --help", "顯示主幫助信息")
    
    # 2. 測試認證命令
    run_command("python main.py auth --help", "顯示認證命令幫助")
    
    # 3. 測試站點命令
    run_command("python main.py sites", "列出所有站點")
    
    # 4. 測試同步命令幫助
    run_command("python main.py sync --help", "顯示同步命令幫助")
    
    # 5. 測試批量同步命令幫助
    run_command("python main.py bulk-sync --help", "顯示批量同步命令幫助")
    
    # 6. 測試圖表命令幫助
    run_command("python main.py plot --help", "顯示圖表命令幫助")


def test_bulk_synchronizer():
    """測試重構後的批量同步器"""
    print("\n🔄 開始測試批量同步器功能")
    
    # 1. 測試直接運行舊格式
    print("\n📅 測試舊格式的批量同步（直接運行 bulk_data_synchronizer.py）")
    print("注意：這需要提供有效的 site_id, year, month 參數")
    
    # 2. 測試新的 run_sync 函數
    print("\n🧪 測試新的 run_sync 函數")
    try:
        from bulk_data_synchronizer import run_sync
        
        # 測試函數導入
        print("✅ run_sync 函數導入成功")
        
        # 測試函數簽名
        import inspect
        sig = inspect.signature(run_sync)
        print(f"📋 函數簽名: {sig}")
        
        # 測試參數說明
        doc = run_sync.__doc__
        if doc:
            print("📚 函數文檔:")
            print(doc.strip())
        
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")


def test_integration_scenarios():
    """測試整合場景"""
    print("\n🎯 開始測試整合場景")
    
    # 1. 測試同步所有站點
    print("\n🌐 測試同步所有站點（模擬）")
    print("命令: python main.py sync --all-sites --days 7")
    print("這將使用新的 run_sync 函數")
    
    # 2. 測試同步特定站點
    print("\n🎯 測試同步特定站點（模擬）")
    print("命令: python main.py sync --site-url 'https://example.com' --days 30")
    
    # 3. 測試批量同步
    print("\n📅 測試批量同步（模擬）")
    print("命令: python main.py bulk-sync --site-id 1 2 3 --year 2025 --month 6")
    
    # 4. 測試進度查看
    run_command("python main.py progress", "查看同步進度")
    
    # 5. 測試 API 狀態
    run_command("python main.py api-status", "查看 API 狀態")


def test_error_handling():
    """測試錯誤處理"""
    print("\n🛡️ 開始測試錯誤處理")
    
    # 1. 測試無效參數
    print("\n❌ 測試無效參數")
    run_command("python main.py sync --days -5", "測試無效天數參數")
    
    # 2. 測試缺少必要參數
    print("\n❌ 測試缺少必要參數")
    run_command("python main.py sync", "測試缺少站點參數")
    
    # 3. 測試無效的批量同步參數
    print("\n❌ 測試無效的批量同步參數")
    run_command("python main.py bulk-sync --month 13", "測試無效月份")


def test_progress_features():
    """測試進度顯示功能"""
    print("\n⏳ 開始測試進度顯示功能")
    
    # 1. 測試日誌查看
    run_command("python main.py logs --lines 10", "查看最近10行日誌")
    
    # 2. 測試錯誤日誌過濾
    run_command("python main.py logs --error-only --lines 5", "查看最近5行錯誤日誌")


def main():
    """主測試函數"""
    print("🧪 GSC CLI 整合測試")
    print("="*60)
    print(f"📅 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 檢查依賴
    print("\n📦 檢查依賴...")
    try:
        import typer
        print("✅ Typer 已安裝")
    except ImportError:
        print("❌ Typer 未安裝，請運行: pip install typer[all]")
        return
    
    try:
        import tqdm
        print("✅ tqdm 已安裝")
    except ImportError:
        print("❌ tqdm 未安裝，請運行: pip install tqdm")
        return
    
    try:
        from rich.console import Console
        print("✅ Rich 已安裝")
    except ImportError:
        print("❌ Rich 未安裝，請運行: pip install rich")
        return
    
    # 執行測試
    test_cli_commands()
    test_bulk_synchronizer()
    test_integration_scenarios()
    test_error_handling()
    test_progress_features()
    
    print("\n" + "="*60)
    print("🎉 整合測試完成！")
    print("="*60)
    print("\n📚 使用建議:")
    print("1. 先運行認證: python main.py auth")
    print("2. 查看站點: python main.py sites")
    print("3. 同步數據: python main.py sync --all-sites --days 7")
    print("4. 批量同步: python main.py bulk-sync --site-id 1 2 3 --year 2025 --month 6")
    print("5. 生成圖表: python main.py plot --type clicks --days 30 --save chart.png")
    print("\n📖 更多信息請參考 README_CLI.md 和 CLI_MIGRATION_GUIDE.md")


if __name__ == "__main__":
    main() 