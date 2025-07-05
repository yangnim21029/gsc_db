#!/usr/bin/env python3
"""
性能基準測試
測試每小時數據保存的優化效果
"""

import time
import random
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_test_hourly_data(count: int) -> List[Dict[str, Any]]:
    """生成測試用的每小時數據"""
    data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(count):
        date = base_date + timedelta(days=i % 30)
        hour = i % 24
        
        data.append({
            'site_id': random.randint(1, 5),
            'keyword_id': random.randint(1, 100),
            'date': date.strftime('%Y-%m-%d'),
            'hour': hour,
            'hour_timestamp': f"{date.strftime('%Y-%m-%d')}T{hour:02d}:00:00Z",
            'query': f"test keyword {i % 50}",
            'position': random.uniform(1.0, 100.0),
            'clicks': random.randint(0, 1000),
            'impressions': random.randint(0, 10000),
            'ctr': random.uniform(0.0, 0.1),
            'page': f"https://example.com/page-{i % 20}.html",
            'country': 'TWN',
            'device': 'ALL'
        })
    
    return data

def benchmark_old_method(data: List[Dict[str, Any]], db_connection_func) -> float:
    """測試舊的逐行插入方法"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    from src.services.hourly_database import HourlyDatabase
    
    hourly_db = HourlyDatabase(db_connection_func)
    
    # 模擬舊的逐行插入方法
    start_time = time.time()
    
    with db_connection_func() as conn:
        for ranking in data:
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO hourly_rankings
                    (site_id, keyword_id, date, hour, hour_timestamp, query, position, clicks, impressions, ctr, page, country, device)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ranking['site_id'],
                    ranking.get('keyword_id'),
                    ranking['date'],
                    ranking['hour'],
                    ranking['hour_timestamp'],
                    ranking['query'],
                    ranking.get('position'),
                    ranking.get('clicks', 0),
                    ranking.get('impressions', 0),
                    ranking.get('ctr', 0),
                    ranking.get('page'),
                    ranking.get('country', 'TWN'),
                    ranking.get('device', 'ALL')
                ))
            except Exception as e:
                logger.error(f"Failed to save hourly ranking: {e}")
        
        conn.commit()
    
    end_time = time.time()
    return end_time - start_time

def benchmark_new_method(data: List[Dict[str, Any]], db_connection_func) -> float:
    """測試新的批量插入方法"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    from src.services.hourly_database import HourlyDatabase
    
    hourly_db = HourlyDatabase(db_connection_func)
    
    start_time = time.time()
    saved_count = hourly_db.save_hourly_ranking_data(data)
    end_time = time.time()
    
    return end_time - start_time

def run_performance_benchmark():
    """運行性能基準測試"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    from src.services.database import Database
    
    # 初始化數據庫
    db = Database()
    
    # 測試不同大小的數據集
    test_sizes = [100, 500, 1000, 5000]
    
    print("🚀 每小時數據保存性能基準測試")
    print("=" * 60)
    
    results = []
    
    for size in test_sizes:
        print(f"\n📊 測試數據集大小: {size:,} 條記錄")
        
        # 生成測試數據
        test_data = generate_test_hourly_data(size)
        
        # 清理測試表
        with db.get_connection() as conn:
            conn.execute("DELETE FROM hourly_rankings WHERE query LIKE 'test keyword%'")
            conn.commit()
        
        # 測試新方法
        new_time = benchmark_new_method(test_data, db.get_connection)
        
        # 清理測試表
        with db.get_connection() as conn:
            conn.execute("DELETE FROM hourly_rankings WHERE query LIKE 'test keyword%'")
            conn.commit()
        
        # 測試舊方法
        old_time = benchmark_old_method(test_data, db.get_connection)
        
        # 計算性能提升
        speedup = old_time / new_time if new_time > 0 else float('inf')
        
        results.append({
            'size': size,
            'old_time': old_time,
            'new_time': new_time,
            'speedup': speedup
        })
        
        print(f"  舊方法時間: {old_time:.3f} 秒")
        print(f"  新方法時間: {new_time:.3f} 秒")
        print(f"  性能提升: {speedup:.1f}x")
    
    # 總結
    print("\n" + "=" * 60)
    print("📈 性能測試總結")
    print("=" * 60)
    
    for result in results:
        print(f"數據集 {result['size']:,} 條記錄:")
        print(f"  性能提升: {result['speedup']:.1f}x")
        print(f"  時間節省: {result['old_time'] - result['new_time']:.3f} 秒")
    
    # 計算平均性能提升
    avg_speedup = sum(r['speedup'] for r in results) / len(results)
    print(f"\n🎯 平均性能提升: {avg_speedup:.1f}x")
    
    return results

if __name__ == "__main__":
    run_performance_benchmark() 