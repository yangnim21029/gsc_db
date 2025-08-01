#!/usr/bin/env python3
"""
最簡單的 GSC 資料同步到 Parquet
"""

import os
import pandas as pd
import time
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import argparse

# 設定
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"
DATA_DIR = "data"


def get_gsc_client():
    """取得 GSC client"""
    creds = None

    # 嘗試載入已存的 token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # 如果沒有認證或已過期
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token 已過期，正在更新...")
            creds.refresh(Request())
        else:
            print("需要授權，將開啟瀏覽器...")
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"找不到 {CLIENT_SECRET_FILE}！\n"
                    "請從 Google Console 下載 OAuth 2.0 用戶端 ID 並命名為 client_secret.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 儲存認證以供下次使用
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
        print("認證成功！")

    return build("searchconsole", "v1", credentials=creds)


def sync_site(site_url):
    """同步網站資料（從最舊到最新）"""
    client = get_gsc_client()

    # 將 site_url 轉換成安全的資料夾名稱
    folder_name = site_url.replace(":", "_").replace("/", "_")

    # 從最舊的資料開始（GSC 最多 16 個月）
    start_date = datetime.now().date() - timedelta(days=480)
    end_date = datetime.now().date() - timedelta(days=1)  # 昨天

    current_date = start_date
    requests_count = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")

        # 檢查檔案是否已存在
        year_month = current_date.strftime("%Y-%m")
        file_path = f"{DATA_DIR}/{folder_name}/{year_month}/{date_str}.parquet"

        if os.path.exists(file_path):
            print(f"⏭ {date_str} 已存在")
            current_date += timedelta(days=1)
            continue

        try:
            # 分批抓取資料（每批最多 25000 筆）
            all_rows = []
            start_row = 0
            batch_num = 0

            while True:
                response = (
                    client.searchanalytics()
                    .query(
                        siteUrl=site_url,
                        body={
                            "startDate": date_str,
                            "endDate": date_str,
                            "dimensions": ["query", "page", "device", "country"],
                            "rowLimit": 25000,
                            "startRow": start_row,
                        },
                    )
                    .execute()
                )

                rows = response.get("rows", [])
                if not rows:
                    break

                all_rows.extend(rows)
                start_row += len(rows)
                batch_num += 1

                if len(rows) < 25000:
                    break

            if not all_rows:
                print(f"○ {date_str} 沒有資料")
                current_date += timedelta(days=1)
                continue

            # 轉換成 DataFrame
            data_list = []
            for row in all_rows:
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

            # 存成 Parquet
            os.makedirs(f"{DATA_DIR}/{folder_name}/{year_month}", exist_ok=True)
            df.to_parquet(file_path, engine="pyarrow", compression="snappy")

            print(f"✓ {date_str} ({len(df)} 筆)")

            requests_count += 1

            # 每 10 個請求休息一下（避免短期 quota）
            if requests_count % 10 == 0:
                print("休息 10 秒...")
                time.sleep(10)

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate limit" in error_msg:
                print(f"Quota 超過，休息 15 分鐘...")
                time.sleep(900)  # 15 分鐘
                # 重試這一天，不要增加日期
                continue
            else:
                print(f"✗ {date_str}: {str(e)}")

        current_date += timedelta(days=1)


def sync_hourly(site_url):
    """同步最近 10 天的 hourly data"""
    client = get_gsc_client()
    
    # 將 site_url 轉換成安全的資料夾名稱
    folder_name = site_url.replace(":", "_").replace("/", "_")
    
    # GSC API 只提供最近 10 天的 hourly data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=9)  # 10 天包含今天
    
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        file_path = f"{DATA_DIR}/{folder_name}/hourly/{date_str}.parquet"
        
        # 檢查現有檔案是否已完整（包含 23 點的資料）
        if os.path.exists(file_path):
            try:
                existing_df = pd.read_parquet(file_path)
                if not existing_df.empty and existing_df['hour'].max() == 23:
                    print(f"⏭ {date_str} hourly 已完整 (0-23 時)")
                    current_date += timedelta(days=1)
                    continue
                else:
                    print(f"↻ {date_str} hourly 不完整，重新抓取")
            except Exception as e:
                print(f"! {date_str} 讀取失敗，重新抓取: {str(e)}")
        
        try:
            # 分批抓取資料（每批最多 25000 筆）
            all_rows = []
            start_row = 0
            batch_num = 0
            
            while True:
                response = (
                    client.searchanalytics()
                    .query(
                        siteUrl=site_url,
                        body={
                            "startDate": date_str,
                            "endDate": date_str,
                            "dimensions": ["HOUR", "query", "page", "device", "country"],
                            "dataState": "HOURLY_ALL",
                            "rowLimit": 25000,
                            "startRow": start_row,
                        },
                    )
                    .execute()
                )
                
                rows = response.get("rows", [])
                if not rows:
                    break
                
                all_rows.extend(rows)
                start_row += len(rows)
                batch_num += 1
                
                if len(rows) < 25000:
                    break
                else:
                    print(f"  批次 {batch_num + 1}: +{len(rows)} 筆，總計 {start_row} 筆")
            
            if not all_rows:
                print(f"○ {date_str} 沒有 hourly 資料")
                current_date += timedelta(days=1)
                continue
            
            # 轉換成 DataFrame
            data_list = []
            for row in all_rows:
                # 解析 HOUR dimension 的 timestamp (例如: '2025-07-23T03:00:00-07:00')
                hour_timestamp = row["keys"][0]
                hour = int(hour_timestamp.split('T')[1].split(':')[0])
                
                data_list.append(
                    {
                        "site_url": site_url,
                        "date": date_str,
                        "hour": hour,  # 提取小時 (0-23)
                        "query": row["keys"][1],
                        "page": row["keys"][2],
                        "device": row["keys"][3],
                        "country": row["keys"][4],
                        "clicks": row["clicks"],
                        "impressions": row["impressions"],
                        "ctr": row["ctr"],
                        "position": row["position"],
                    }
                )
            
            df = pd.DataFrame(data_list)
            
            # 存成 Parquet
            os.makedirs(f"{DATA_DIR}/{folder_name}/hourly", exist_ok=True)
            df.to_parquet(file_path, engine="pyarrow", compression="snappy")
            
            print(f"✓ {date_str} hourly ({len(df)} 筆)")
            
        except Exception as e:
            print(f"✗ {date_str} hourly: {str(e)}")
        
        current_date += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description="同步 GSC 資料到 Parquet")
    parser.add_argument("site_url", help="網站 URL (例如: https://example.com)")

    args = parser.parse_args()

    sync_site(args.site_url)
    sync_hourly(args.site_url)


if __name__ == "__main__":
    main()
