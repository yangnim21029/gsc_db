#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC 報告生成整合測試
展示新的報告生成功能和 CLI 整合
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_command(command: list, description: str = "") -> bool:
    """執行命令並顯示結果，優化了錯誤處理和命令解析"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"💻 執行命令: {' '.join(command)}")
    print('='*60)
    
    try:
        # 使用 check=True 會在返回碼非零時拋出 CalledProcessError
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # 自動檢查返回碼
            cwd=Path(__file__).parent.parent  # 運行在項目根目錄
        )
        
        if result.stdout:
            print("✅ 輸出:")
            print(result.stdout)
        
        # stderr 仍然可以打印，用於警告等
        if result.stderr:
            print("ℹ️  標準錯誤輸出:")
            print(result.stderr)
            
        return True
        
    except FileNotFoundError:
        print(f"❌ 命令未找到: {command[0]}. 請確保 python 在您的 PATH 中。")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令執行失敗，返回碼: {e.returncode}")
        if e.stdout:
            print("✅ 輸出:")
            print(e.stdout)
        if e.stderr:
            print("⚠️  錯誤輸出:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"❌ 發生未知錯誤: {e}")
        return False


def test_report_commands():
    """測試報告生成命令"""
    print("📊 開始測試報告生成命令")
    
    # 1. 顯示報告命令幫助
    run_command(["python", "main.py", "report", "--help"], "顯示報告命令幫助")
    
    # 2. 測試生成簡單報告（不包含圖表）
    run_command(["python", "main.py", "report", "--days", "7", "--no-plots"], "生成7天報告（無圖表）")
    
    # 3. 測試生成完整報告
    run_command(["python", "main.py", "report", "--days", "14", "--output", "test_report.md"], "生成14天完整報告")
    
    # 4. 測試自定義圖表目錄
    run_command(["python", "main.py", "report", "--days", "3", "--plot-dir", "test_plots"], "生成3天報告到自定義目錄")


def test_analytics_module():
    """測試分析模塊功能"""
    print("\n🧪 開始測試分析模塊功能")
    
    try:
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        from src.analysis.analytics_report_builder import build_report, GSCVisualizer
        
        # 測試模塊導入
        print("✅ analytics_report_builder 模塊導入成功")
        
        # 測試 GSCVisualizer 類
        visualizer = GSCVisualizer()
        print("✅ GSCVisualizer 實例化成功")
        
        # 測試數據摘要
        summary = visualizer.data_summary()
        if summary:
            print("✅ 數據摘要獲取成功")
            print(f"   - 總記錄數: {summary['total_records']:,}")
            print(f"   - 數據天數: {summary['total_days']}")
            print(f"   - 關鍵字數量: {summary['total_keywords']:,}")
        else:
            print("❌ 數據摘要獲取失敗")
        
        # 測試 build_report 函數
        print("\n🧪 測試 build_report 函數")
        result = build_report(
            output_path="test_module_report.md",
            days=5,
            include_plots=False
        )
        
        if result['success']:
            print("✅ build_report 函數測試成功")
            print(f"   - 報告路徑: {result['report_path']}")
            if 'summary' in result:
                print(f"   - 包含數據摘要")
        else:
            print("❌ build_report 函數測試失敗")
            for error in result['errors']:
                print(f"   - 錯誤: {error}")
        
    except ImportError as e:
        print(f"❌ 導入失敗: {e}")
    except Exception as e:
        print(f"❌ 測試失敗: {e}")


def test_report_content():
    """測試報告內容"""
    print("\n📄 開始測試報告內容")
    
    # 檢查生成的報告文件
    report_files = ["gsc_report.md", "test_report.md", "test_module_report.md"]
    
    for report_file in report_files:
        if Path(report_file).exists():
            print(f"✅ 報告文件存在: {report_file}")
            
            # 讀取報告內容的前幾行
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                    print(f"   前10行內容:")
                    for line in lines:
                        print(f"   {line.rstrip()}")
            except Exception as e:
                print(f"   ❌ 讀取文件失敗: {e}")
        else:
            print(f"❌ 報告文件不存在: {report_file}")


def test_plot_generation():
    """測試圖表生成"""
    print("\n📊 開始測試圖表生成")
    
    # 檢查圖表目錄
    plot_dirs = ["assets", "test_plots"]
    
    for plot_dir in plot_dirs:
        plot_path = Path(plot_dir)
        if plot_path.exists():
            print(f"✅ 圖表目錄存在: {plot_dir}")
            
            # 列出生成的圖表文件
            plot_files = list(plot_path.glob("*.png"))
            if plot_files:
                print(f"   生成的圖表:")
                for plot_file in plot_files:
                    print(f"   - {plot_file.name}")
            else:
                print(f"   目錄中沒有圖表文件")
        else:
            print(f"❌ 圖表目錄不存在: {plot_dir}")


def main():
    """主測試函數"""
    print("🧪 GSC 報告生成整合測試")
    print("="*60)
    print(f"📅 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 檢查依賴
    print("\n📦 檢查依賴...")
    try:
        import matplotlib
        print("✅ matplotlib 已安裝")
    except ImportError:
        print("❌ matplotlib 未安裝，請運行: pip install matplotlib")
        return
    
    try:
        import pandas
        print("✅ pandas 已安裝")
    except ImportError:
        print("❌ pandas 未安裝，請運行: pip install pandas")
        return
    
    # 執行測試
    test_report_commands()
    test_analytics_module()
    test_report_content()
    test_plot_generation()
    
    print("\n" + "="*60)
    print("🎉 報告生成整合測試完成！")
    print("="*60)
    print("\n📚 使用建議:")
    print("1. 生成簡單報告: python main.py report --days 7 --no-plots")
    print("2. 生成完整報告: python main.py report --days 30")
    print("3. 自定義輸出: python main.py report --output my_report.md --days 14")
    print("4. 自定義圖表目錄: python main.py report --plot-dir my_plots")
    print("\n📖 更多信息請參考 README_CLI.md")


if __name__ == "__main__":
    main() 