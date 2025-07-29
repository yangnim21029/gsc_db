#!/usr/bin/env python3
"""
簡單測試腳本
"""
import os
import sys
from datetime import datetime, timedelta


# 測試同步單天資料
def test_sync_single_day():
    print("=== 測試同步單天資料 ===")

    # 匯入 sync 模組的函數
    from sync import get_gsc_client
    import pandas as pd

    site_url = "sc-domain:urbanlifehk.com"  # 測試站點
    date_str = (datetime.now().date() - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"測試同步 {site_url} 的 {date_str} 資料...")

    try:
        client = get_gsc_client()

        # 單次 API 呼叫
        response = (
            client.searchanalytics()
            .query(
                siteUrl=site_url,
                body={
                    "startDate": date_str,
                    "endDate": date_str,
                    "dimensions": ["query", "page", "device", "country"],
                    "rowLimit": 10,  # 只抓 10 筆測試
                },
            )
            .execute()
        )

        rows = response.get("rows", [])
        print(f"✓ 成功！取得 {len(rows)} 筆資料")

        if rows:
            # 測試存檔
            folder_name = site_url.replace(":", "_").replace("/", "_")
            test_path = f"data/{folder_name}/test/{date_str}.parquet"
            os.makedirs(f"data/{folder_name}/test", exist_ok=True)

            data_list = []
            for row in rows[:5]:  # 只存前 5 筆
                data_list.append(
                    {
                        "site_url": site_url,
                        "date": date_str,
                        "query": row["keys"][0],
                        "page": row["keys"][1],
                        "device": row["keys"][2],
                        "country": row["keys"][3],
                        "clicks": row["clicks"],
                        "impressions": row["impressions"],
                        "ctr": row["ctr"],
                        "position": row["position"],
                    }
                )

            df = pd.DataFrame(data_list)
            df.to_parquet(test_path)
            print(f"✓ 測試檔案已存至: {test_path}")

    except Exception as e:
        print(f"✗ 錯誤: {e}")
        return False

    return True


# 測試查詢
def test_query():
    print("\n=== 測試 DuckDB 查詢 ===")

    try:
        import duckdb

        conn = duckdb.connect()

        # 測試查詢所有 parquet 檔案
        print("查詢所有 parquet 檔案...")
        df = conn.execute("SELECT * FROM 'data/*/*/*.parquet' LIMIT 10").fetchdf()

        if len(df) > 0:
            print(f"✓ 成功！找到 {len(df)} 筆資料")
            print("\n前 5 筆資料：")
            print(df.head())
        else:
            print("○ 沒有找到資料（可能還沒同步）")

    except Exception as e:
        print(f"✗ 查詢錯誤: {e}")
        return False

    return True


# 測試 API 服務
def test_api():
    print("\n=== 測試 API 服務 ===")

    try:
        import requests
        import json

        # 測試 track_pages endpoint
        response = requests.post(
            "http://localhost:5000/track_pages",
            json={
                "site": "sc-domain:urbanlifehk.com",
                "pages": ["/"],
                "days": 7,
            },
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ API 正常！返回 {len(data) if isinstance(data, list) else 0} 筆資料")
        else:
            print(f"✗ API 錯誤: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("! API 服務未啟動（執行 python app.py 5000 來啟動）")
    except Exception as e:
        print(f"✗ 錯誤: {e}")


def main():
    print("GSC Parquet 系統測試")
    print("=" * 40)

    # 1. 測試同步
    if test_sync_single_day():
        # 2. 測試查詢
        test_query()

    # 3. 測試 API（可選）
    test_api()

    print("\n測試完成！")


if __name__ == "__main__":
    main()
