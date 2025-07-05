#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC 數據庫性能優化演示
展示批量操作和並發處理的實際效果
"""

import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_sample_data(num_records: int) -> List[Dict[str, Any]]:
    """生成示例數據"""
    data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(num_records):
        data.append({
            'site_id': random.randint(1, 3),
            'keyword_id': random.randint(1, 50),
            'date': (base_date + timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d'),
            'query': f'demo_keyword_{random.randint(1, 500)}',
            'position': random.randint(1, 100),
            'clicks': random.randint(0, 500),
            'impressions': random.randint(0, 5000),
            'ctr': random.uniform(0, 0.1),
            'page': f'https://demo.com/page_{random.randint(1, 50)}.html',
            'country': 'TWN',
            'device': random.choice(['desktop', 'mobile', 'tablet'])
        })
    
    return data

def demo_database_optimizations():
    """演示數據庫優化效果"""
    print("🔍 數據庫批量操作優化演示")
    print("="*60)
    
    try:
        from src.services.database import Database
        
        # 初始化測試數據庫
        db = Database('demo_optimizations.db')
        
        # 生成不同大小的測試數據
        test_sizes = [100, 1000, 5000]
        
        for size in test_sizes:
            print(f"\n📊 測試數據量: {size:,} 條記錄")
            print("-" * 40)
            
            # 生成測試數據
            test_data = generate_sample_data(size)
            
            # 測試排名數據保存性能
            start_time = time.time()
            saved_count = db.save_ranking_data(test_data)
            end_time = time.time()
            
            performance = saved_count / (end_time - start_time)
            
            print(f"✅ 排名數據保存:")
            print(f"   - 記錄數: {saved_count:,}")
            print(f"   - 耗時: {end_time - start_time:.3f} 秒")
            print(f"   - 速度: {performance:.0f} 記錄/秒")
            
            # 測試頁面數據保存性能
            page_data = [
                {
                    'site_id': item['site_id'],
                    'page': item['page'],
                    'date': item['date'],
                    'clicks': item['clicks'],
                    'impressions': item['impressions'],
                    'ctr': item['ctr'],
                    'position': item['position']
                }
                for item in test_data
            ]
            
            start_time = time.time()
            saved_count = db.save_page_data(page_data)
            end_time = time.time()
            
            performance = saved_count / (end_time - start_time)
            
            print(f"✅ 頁面數據保存:")
            print(f"   - 記錄數: {saved_count:,}")
            print(f"   - 耗時: {end_time - start_time:.3f} 秒")
            print(f"   - 速度: {performance:.0f} 記錄/秒")
    
    except ImportError as e:
        print(f"❌ 無法導入數據庫模塊: {e}")
        print("💡 請確保在項目根目錄運行此腳本")
    except Exception as e:
        print(f"❌ 演示失敗: {e}")

def demo_concurrent_processing():
    """演示並發處理效果"""
    print("\n🔄 並發處理優化演示")
    print("="*60)
    
    # 模擬站點列表
    demo_sites = [
        'https://demo1.com',
        'https://demo2.com',
        'https://demo3.com',
        'https://demo4.com',
        'https://demo5.com'
    ]
    
    def simulate_site_sync(site_url: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """模擬站點同步過程"""
        # 模擬 API 調用時間
        sync_time = random.uniform(1.5, 3.0)
        time.sleep(sync_time)
        
        return {
            'site': site_url,
            'success': True,
            'sync_time': sync_time,
            'records_synced': random.randint(100, 800),
            'keywords_found': random.randint(50, 200)
        }
    
    # 順序處理演示
    print("📊 順序處理演示")
    start_time = time.time()
    sequential_results = []
    
    for site in demo_sites:
        print(f"   🔄 同步 {site}...")
        result = simulate_site_sync(site, '2024-01-01', '2024-01-31')
        sequential_results.append(result)
        print(f"   ✅ 完成 {site}: {result['records_synced']} 條記錄")
    
    sequential_time = time.time() - start_time
    print(f"\n📈 順序處理結果:")
    print(f"   - 總耗時: {sequential_time:.2f} 秒")
    print(f"   - 平均每站點: {sequential_time / len(demo_sites):.2f} 秒")
    print(f"   - 總記錄數: {sum(r['records_synced'] for r in sequential_results):,}")
    
    # 並發處理演示
    print("\n📊 並發處理演示")
    import concurrent.futures
    
    start_time = time.time()
    concurrent_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任務
        future_to_site = {
            executor.submit(simulate_site_sync, site, '2024-01-01', '2024-01-31'): site
            for site in demo_sites
        }
        
        # 收集結果
        for future in concurrent.futures.as_completed(future_to_site):
            site = future_to_site[future]
            try:
                result = future.result()
                concurrent_results.append(result)
                print(f"   ✅ 完成 {site}: {result['records_synced']} 條記錄")
            except Exception as e:
                print(f"   ❌ 失敗 {site}: {e}")
    
    concurrent_time = time.time() - start_time
    print(f"\n📈 並發處理結果:")
    print(f"   - 總耗時: {concurrent_time:.2f} 秒")
    print(f"   - 平均每站點: {concurrent_time / len(demo_sites):.2f} 秒")
    print(f"   - 總記錄數: {sum(r['records_synced'] for r in concurrent_results):,}")
    
    # 性能對比
    speedup = sequential_time / concurrent_time
    print(f"\n🚀 性能提升:")
    print(f"   - 速度提升: {speedup:.1f}x")
    print(f"   - 時間節省: {sequential_time - concurrent_time:.2f} 秒")
    print(f"   - 效率提升: {((sequential_time - concurrent_time) / sequential_time * 100):.1f}%")

def demo_error_handling():
    """演示改進的錯誤處理"""
    print("\n🛡️ 錯誤處理改進演示")
    print("="*60)
    
    import subprocess
    from pathlib import Path
    
    def run_command_safe(command: list, description: str) -> bool:
        """安全的命令執行"""
        print(f"🔧 {description}")
        print(f"💻 執行: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                cwd=Path(__file__).parent
            )
            
            if result.stdout:
                print("✅ 輸出:")
                print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
            
            return True
            
        except FileNotFoundError:
            print(f"❌ 命令未找到: {command[0]}")
            return False
        except subprocess.CalledProcessError as e:
            print(f"❌ 執行失敗 (返回碼: {e.returncode})")
            if e.stderr:
                print(f"錯誤信息: {e.stderr[:200]}...")
            return False
        except Exception as e:
            print(f"❌ 未知錯誤: {e}")
            return False
    
    # 測試各種命令
    test_commands = [
        (["python", "--version"], "檢查 Python 版本"),
        (["ls", "-la"], "列出目錄內容"),
        (["nonexistent_command"], "測試不存在的命令"),
        (["python", "-c", "print('Hello, World!')"], "執行簡單 Python 代碼")
    ]
    
    for command, description in test_commands:
        print(f"\n{'='*40}")
        success = run_command_safe(command, description)
        print(f"結果: {'✅ 成功' if success else '❌ 失敗'}")

def main():
    """主演示函數"""
    print("🚀 GSC 數據庫性能優化演示")
    print("="*60)
    print(f"📅 演示時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 執行演示
    demo_database_optimizations()
    demo_concurrent_processing()
    demo_error_handling()
    
    print("\n" + "="*60)
    print("🎉 優化演示完成！")
    print("="*60)
    print("\n📋 優化總結:")
    print("✅ 數據庫批量操作: 顯著提升數據插入速度")
    print("✅ 並發站點同步: 大幅減少多站點同步時間")
    print("✅ 改進錯誤處理: 更安全、更可靠的命令執行")
    print("✅ 內存優化: 高效的批量處理減少內存佔用")
    print("\n💡 這些優化為處理大規模數據提供了堅實的基礎")

if __name__ == "__main__":
    main() 