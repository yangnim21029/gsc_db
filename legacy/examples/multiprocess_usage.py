#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Process Database Usage Examples

This file demonstrates how to use the GSC database in multi-process scenarios.
"""

import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor

# 使用標準容器（已支援多程序）
from src.containers import Container


def worker_read_sites(worker_id: int):
    """模擬讀取站點資料的工作程序"""
    container = Container()
    db = container.database()

    print(f"Worker {worker_id} (PID: {multiprocessing.current_process().pid}) starting...")

    try:
        sites = db.get_sites()
        print(f"Worker {worker_id} found {len(sites)} sites")

        # 模擬一些處理
        time.sleep(0.5)

        for site in sites[:3]:  # 只處理前3個
            coverage = db.get_daily_data_coverage(site["id"])
            print(f"Worker {worker_id}: Site {site['name']} has {len(coverage)} days of data")

    except Exception as e:
        print(f"Worker {worker_id} error: {e}")

    return f"Worker {worker_id} completed"


def worker_write_data(worker_id: int, site_id: int):
    """模擬寫入資料的工作程序"""
    container = Container()
    db = container.database()

    print(f"Writer {worker_id} (PID: {multiprocessing.current_process().pid}) starting...")

    try:
        # 模擬寫入操作
        task_id = db.start_sync_task(
            site_id=site_id,
            task_type=f"test_worker_{worker_id}",
            start_date="2024-01-01",
            end_date="2024-01-01",
        )

        time.sleep(0.3)  # 模擬處理

        db.complete_sync_task(task_id, total_records=100)
        print(f"Writer {worker_id} completed task {task_id}")

    except Exception as e:
        print(f"Writer {worker_id} error: {e}")

    return f"Writer {worker_id} completed"


def test_concurrent_reads():
    """測試並發讀取"""
    print("\n=== Testing Concurrent Reads ===")

    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(4):
            future = executor.submit(worker_read_sites, i)
            futures.append(future)

        for future in futures:
            print(future.result())


def test_concurrent_writes():
    """測試並發寫入"""
    print("\n=== Testing Concurrent Writes ===")

    # 先獲取一個有效的 site_id
    container = Container()
    db = container.database()
    sites = db.get_sites()

    if not sites:
        print("No sites found. Please add some sites first.")
        return

    site_id = sites[0]["id"]

    with ProcessPoolExecutor(max_workers=2) as executor:
        futures = []
        for i in range(2):
            future = executor.submit(worker_write_data, i, site_id)
            futures.append(future)

        for future in futures:
            print(future.result())


def test_mixed_operations():
    """測試混合讀寫操作"""
    print("\n=== Testing Mixed Read/Write Operations ===")

    container = Container()
    db = container.database()
    sites = db.get_sites()

    if not sites:
        print("No sites found. Please add some sites first.")
        return

    site_id = sites[0]["id"]

    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = []

        # 4個讀取工作
        for i in range(4):
            future = executor.submit(worker_read_sites, i)
            futures.append(future)

        # 2個寫入工作
        for i in range(2):
            future = executor.submit(worker_write_data, i + 10, site_id)
            futures.append(future)

        for future in futures:
            print(future.result())


def test_web_server_simulation():
    """模擬 Web 伺服器場景（如 Gunicorn with multiple workers）"""
    print("\n=== Simulating Web Server with Multiple Workers ===")

    def handle_request(request_id: int):
        """模擬處理 HTTP 請求"""
        container = Container()
        db = container.database()

        # 模擬不同類型的請求
        if request_id % 3 == 0:
            # 讀取請求
            sites = db.get_sites()
            return f"Request {request_id}: Found {len(sites)} sites"
        elif request_id % 3 == 1:
            # 分析請求
            sites = db.get_sites()
            if sites:
                coverage = db.get_daily_data_coverage(sites[0]["id"])
                return f"Request {request_id}: Site has {len(coverage)} days"
        else:
            # 寫入請求
            sites = db.get_sites()
            if sites:
                task_id = db.start_sync_task(
                    site_id=sites[0]["id"],
                    task_type=f"api_request_{request_id}",
                    start_date="2024-01-01",
                    end_date="2024-01-01",
                )
                db.complete_sync_task(task_id, total_records=50)
                return f"Request {request_id}: Completed task {task_id}"

        return f"Request {request_id}: No operation"

    # 模擬 20 個並發請求
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(20):
            future = executor.submit(handle_request, i)
            futures.append(future)
            time.sleep(0.1)  # 模擬請求間隔

        for future in futures:
            try:
                print(future.result())
            except Exception as e:
                print(f"Request failed: {e}")


if __name__ == "__main__":
    print("Multi-Process Database Usage Examples")
    print("=====================================")

    # 確保使用 spawn 方法（對 macOS 特別重要）
    multiprocessing.set_start_method("spawn", force=True)

    # 執行測試
    test_concurrent_reads()
    test_concurrent_writes()
    test_mixed_operations()
    test_web_server_simulation()

    print("\n=== All tests completed ===")

    # 顯示連接資訊
    container = Container()
    db = container.database()
    if hasattr(db, "get_connection_info"):
        info = db.get_connection_info()
        print(f"\nConnection info: {info}")
