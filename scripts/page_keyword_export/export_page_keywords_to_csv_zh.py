#!/usr/bin/env python3
"""
將頁面關鍵字成效數據導出為 CSV 文件（支持中文）
"""

import csv
from datetime import datetime
from pathlib import Path

import requests

# 配置
BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/v1/page-keyword-performance/"
OUTPUT_DIR = Path(__file__).parent / "exports"


def fetch_page_keyword_data(site_id=None, hostname=None, days=None, max_results=1000):
    """從 API 端點獲取數據"""

    # 構建請求數據
    payload = {"max_results": max_results}

    if site_id:
        payload["site_id"] = site_id
    elif hostname:
        payload["hostname"] = hostname
    else:
        raise ValueError("必須提供 site_id 或 hostname")

    if days:
        payload["days"] = days

    # 發送 API 請求
    try:
        response = requests.post(
            f"{BASE_URL}{ENDPOINT}", json=payload, headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"錯誤：API 返回狀態碼 {response.status_code}")
            print(f"響應：{response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("錯誤：無法連接到 API 服務器")
        print("請確保服務器正在運行：just dev-server")
        return None
    except Exception as e:
        print(f"錯誤：{str(e)}")
        return None


def export_to_csv(data, output_filename):
    """將 API 響應數據導出為 CSV 文件"""

    if not data or not data.get("data"):
        print("沒有數據可以導出")
        return False

    # 創建輸出目錄（如果不存在）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / output_filename

    try:
        # 使用 utf-8-sig 編碼以確保 Excel 正確顯示中文
        with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
            # 定義 CSV 列
            fieldnames = [
                "網址",
                "總點擊數",
                "總曝光數",
                "平均點擊率",
                "平均排名",
                "關鍵字數量",
                "關鍵字列表",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # 寫入數據行
            for item in data["data"]:
                row = {
                    "網址": item["url"],
                    "總點擊數": item["total_clicks"],
                    "總曝光數": item["total_impressions"],
                    "平均點擊率": f"{item['avg_ctr']:.2f}%",
                    "平均排名": f"{item['avg_position']:.1f}",
                    "關鍵字數量": item["keyword_count"],
                    "關鍵字列表": " | ".join(item["keywords"]),  # 用分隔符連接關鍵字
                }
                writer.writerow(row)

        print(f"✅ 數據成功導出到：{output_path}")
        return True

    except Exception as e:
        print(f"寫入 CSV 文件時出錯：{str(e)}")
        return False


def main():
    """主函數：獲取並導出數據"""

    print("頁面關鍵字成效數據導出工具")
    print("=" * 50)

    # 配置 - 根據需要調整這些值
    SITE_ID = 14  # 更改為您的網站 ID (holidaysmart.io)
    DAYS = 30  # 最近 30 天，設為 None 表示所有時間
    MAX_RESULTS = 5000  # 最多獲取的結果數

    # 生成帶時間戳的輸出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"頁面關鍵字_網站{SITE_ID}_{timestamp}.csv"

    print(f"獲取網站 ID：{SITE_ID} 的數據")
    print(f"時間範圍：最近 {DAYS} 天" if DAYS else "時間範圍：所有時間")
    print(f"最大結果數：{MAX_RESULTS}")
    print()

    # 從 API 獲取數據
    print("正在從 API 獲取數據...")
    data = fetch_page_keyword_data(site_id=SITE_ID, days=DAYS, max_results=MAX_RESULTS)

    if data:
        print(f"✅ 收到 {data['total_results']} 條結果")
        print(f"時間範圍：{data['time_range']}")

        # 顯示前 5 個結果的預覽
        if data["data"]:
            print("\n點擊數最高的前 5 個頁面：")
            for i, item in enumerate(data["data"][:5], 1):
                print(f"{i}. {item['url'][:60]}...")
                print(f"   點擊數：{item['total_clicks']:,} | 關鍵字數：{item['keyword_count']}")
                # 顯示前 5 個關鍵字
                if item["keywords"]:
                    keywords_preview = ", ".join(item["keywords"][:5])
                    if item["keyword_count"] > 5:
                        keywords_preview += f" 等 {item['keyword_count']} 個關鍵字"
                    print(f"   關鍵字：{keywords_preview}")

        # 導出為 CSV
        print("\n正在導出為 CSV...")
        export_to_csv(data, output_filename)

        # 統計摘要
        if data["data"]:
            total_clicks = sum(item["total_clicks"] for item in data["data"])
            total_impressions = sum(item["total_impressions"] for item in data["data"])
            print("\n數據摘要：")
            print(f"  總頁面數：{len(data['data'])}")
            print(f"  總點擊數：{total_clicks:,}")
            print(f"  總曝光數：{total_impressions:,}")
            if total_impressions > 0:
                print(f"  總體點擊率：{(total_clicks / total_impressions * 100):.2f}%")
    else:
        print("❌ 無法從 API 獲取數據")


def export_by_hostname(hostname, days=30):
    """根據域名導出數據"""

    print(f"\n使用域名導出：{hostname}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"頁面關鍵字_{hostname.replace(':', '_')}_{timestamp}.csv"

    data = fetch_page_keyword_data(hostname=hostname, days=days, max_results=2000)

    if data:
        export_to_csv(data, output_filename)
    else:
        print(f"❌ 無法獲取 {hostname} 的數據")


if __name__ == "__main__":
    # 單個網站導出
    main()

    # 使用域名導出示例（取消註釋以使用）
    # export_by_hostname("example.com", days=30)
    # export_by_hostname("sc-domain:example.com", days=90)
