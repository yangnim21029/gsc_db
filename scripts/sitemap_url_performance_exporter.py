#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一次性腳本：從站點的 Sitemap 中提取 URL，查詢其在 GSC DB 中的表現數據，並導出為 CSV。

業務需求：為特定站點的 Sitemap URL 列表提供一份詳細的 SEO 表現報告。

使用方法：
在專案根目錄下執行：
poetry run python scripts/sitemap_url_performance_exporter.py \
    --site-id YOUR_SITE_ID \
    --sitemap-url "https://your-domain.com/sitemap.xml" \
    --output-file "scripts/reports/sitemap_performance.csv"

或者使用站點 URL 自動查找：
poetry run python scripts/sitemap_url_performance_exporter.py \
    --site-url "https://your-domain.com" \
    --output-file "scripts/reports/sitemap_performance.csv"
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from lxml import etree
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    track,
)
from rich.table import Table

# 將專案根目錄添加到 sys.path，以便導入 src 模組
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from src.containers import Container
from src.services.database import Database

console = Console()

# Sitemap XML 命名空間
SITEMAP_NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch_sitemap_urls(sitemap_url: str) -> List[str]:
    """
    遞歸獲取並解析 Sitemap，提取所有 URL。
    支持 Sitemap 索引文件。
    """
    urls = []
    try:
        console.log(f"正在獲取 Sitemap: {sitemap_url}")
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()
        xml_content = response.content
        root = etree.fromstring(xml_content, parser=etree.XMLParser(recover=True))

        # 檢查是 Sitemap 索引還是 URL 集合
        if root.tag.endswith("sitemapindex"):
            console.log("檢測到 Sitemap 索引，正在解析子 Sitemap...")
            sitemaps = root.xpath("//ns:sitemap/ns:loc", namespaces=SITEMAP_NS)
            for sitemap_loc in track(sitemaps, description="解析子 Sitemap..."):
                urls.extend(fetch_sitemap_urls(sitemap_loc.text))
        elif root.tag.endswith("urlset"):
            locations = root.xpath("//ns:url/ns:loc", namespaces=SITEMAP_NS)
            urls.extend([loc.text for loc in locations])
            console.log(f"從 Sitemap 中提取了 {len(locations)} 個 URL")
        else:
            console.log(f"[yellow]警告：未知的 Sitemap 根標籤: {root.tag}[/yellow]")

    except requests.RequestException as e:
        console.log(f"[red]錯誤：無法獲取 Sitemap {sitemap_url}: {e}[/red]")
    except etree.XMLSyntaxError as e:
        console.log(f"[red]錯誤：無法解析 XML {sitemap_url}: {e}[/red]")
    except Exception as e:
        console.log(f"[red]錯誤：處理 Sitemap 時發生未知錯誤: {e}[/red]")

    return urls


def get_performance_for_pages(
    db: Database, site_id: int, page_urls: List[str], days: int = 30
) -> Optional[List[Dict]]:
    """
    從資料庫中為指定的 URL 列表查詢匯總的性能數據。
    """
    if not page_urls:
        return None

    # 計算日期範圍
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # 將 URL 列表分塊以避免 SQL 查詢過長
    chunk_size = 500
    all_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("查詢資料庫...", total=len(page_urls))

        for i in range(0, len(page_urls), chunk_size):
            chunk = page_urls[i : i + chunk_size]
            placeholders = ", ".join("?" for _ in chunk)
            query = f"""
                SELECT
                    page,
                    SUM(clicks) as total_clicks,
                    SUM(impressions) as total_impressions,
                    AVG(ctr) as average_ctr,
                    AVG(position) as average_position,
                    COUNT(DISTINCT query) as unique_queries,
                    COUNT(DISTINCT date) as data_days,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM
                    gsc_performance_data
                WHERE
                    site_id = ? AND page IN ({placeholders})
                    AND date BETWEEN ? AND ?
                GROUP BY
                    page
            """
            params = [site_id] + chunk + [start_date, end_date]

            try:
                with db._lock:
                    cursor = db._connection.execute(query, params)
                    results = cursor.fetchall()
                    if results:
                        all_results.extend([dict(row) for row in results])
                progress.update(task, advance=len(chunk))
            except Exception as e:
                console.log(f"[red]資料庫查詢錯誤: {e}[/red]")
                return None

    return all_results


def get_site_by_url_or_id(
    db: Database, site_url: Optional[str] = None, site_id: Optional[int] = None
) -> Optional[Dict]:
    """
    根據 URL 或 ID 查找站點
    """
    if site_id:
        return db.get_site_by_id(site_id)
    elif site_url:
        return db.get_site_by_domain(site_url)
    return None


def create_performance_report(
    sitemap_urls: List[str], performance_data: List[Dict], site_info: Dict, output_file: str
) -> None:
    """
    創建性能報告並保存為 CSV
    """
    console.print("[bold blue]Step 3: 正在生成報告...[/bold blue]")

    # 創建 URL 到性能數據的映射
    performance_dict = {row["page"]: row for row in performance_data}

    # 準備報告數據
    report_data = []
    for url in sitemap_urls:
        perf = performance_dict.get(url, {})
        report_data.append(
            {
                "URL": url,
                "總點擊量": perf.get("total_clicks", 0),
                "總曝光量": perf.get("total_impressions", 0),
                "平均點閱率(%)": round(perf.get("average_ctr", 0) * 100, 2)
                if perf.get("average_ctr")
                else 0,
                "平均排名": round(perf.get("average_position", 0), 2)
                if perf.get("average_position")
                else 0,
                "獨特查詢數": perf.get("unique_queries", 0),
                "數據天數": perf.get("data_days", 0),
                "最早日期": perf.get("earliest_date", ""),
                "最新日期": perf.get("latest_date", ""),
                "在資料庫中": "是" if url in performance_dict else "否",
            }
        )

    # 創建 DataFrame 並排序
    df = pd.DataFrame(report_data)
    df = df.sort_values(["總點擊量", "總曝光量"], ascending=[False, False])

    # 確保輸出目錄存在
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存 CSV
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    # 顯示摘要統計
    display_summary_stats(df, sitemap_urls, performance_data, site_info, output_path)


def display_summary_stats(
    df: pd.DataFrame,
    sitemap_urls: List[str],
    performance_data: List[Dict],
    site_info: Dict,
    output_path: Path,
) -> None:
    """
    顯示摘要統計信息
    """
    # 創建摘要表格
    table = Table(title="Sitemap URL 成效分析摘要")
    table.add_column("項目", style="cyan")
    table.add_column("數值", style="magenta")

    total_sitemap_urls = len(sitemap_urls)
    performance_pages = {row["page"] for row in performance_data}
    urls_with_data = len([url for url in sitemap_urls if url in performance_pages])
    coverage_rate = (urls_with_data / total_sitemap_urls * 100) if total_sitemap_urls > 0 else 0

    table.add_row("站點名稱", site_info.get("name", "未知"))
    table.add_row("站點域名", site_info.get("domain", "未知"))
    table.add_row("Sitemap URL 總數", str(total_sitemap_urls))
    table.add_row("資料庫中有數據的 URL 數", str(urls_with_data))
    table.add_row("數據覆蓋率", f"{coverage_rate:.1f}%")

    if urls_with_data > 0:
        total_clicks = df["總點擊量"].sum()
        total_impressions = df["總曝光量"].sum()
        avg_ctr = df[df["總曝光量"] > 0]["平均點閱率(%)"].mean()
        avg_position = df[df["平均排名"] > 0]["平均排名"].mean()

        table.add_row("總點擊量", str(total_clicks))
        table.add_row("總曝光量", str(total_impressions))
        table.add_row("整體平均點閱率(%)", f"{avg_ctr:.2f}" if pd.notna(avg_ctr) else "N/A")
        table.add_row("整體平均排名", f"{avg_position:.2f}" if pd.notna(avg_position) else "N/A")

    console.print(table)
    console.print(f"[bold green]🚀 報告已成功生成: {output_path}[/bold green]")


def main():
    """主執行函數"""
    parser = argparse.ArgumentParser(description="從 Sitemap 提取 URL 並查詢其 GSC 表現數據。")
    parser.add_argument("--site-id", type=int, help="要查詢的網站的本地資料庫 ID。")
    parser.add_argument("--site-url", type=str, help="要查詢的網站 URL（自動查找站點 ID）。")
    parser.add_argument(
        "--sitemap-url", type=str, help="要解析的 Sitemap 的完整 URL。如果未提供，將嘗試自動發現。"
    )
    parser.add_argument("--output-file", type=str, required=True, help="導出的 CSV 檔案的路徑。")
    parser.add_argument("--days", type=int, default=30, help="查詢過去多少天的數據（預設：30天）。")

    args = parser.parse_args()

    # 驗證參數
    if not args.site_id and not args.site_url:
        console.print("[bold red]錯誤：必須提供 --site-id 或 --site-url 其中之一。[/bold red]")
        return

    console.print(
        Panel.fit(
            f"[bold blue]Sitemap URL 成效分析工具[/bold blue]\n"
            f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    )

    # 初始化資料庫連接
    try:
        container = Container()
        db = container.database()
        console.print("✅ 資料庫連接成功")
    except Exception as e:
        console.print(f"[bold red]錯誤：無法連接資料庫: {e}[/bold red]")
        return

    # 查找站點信息
    site_info = get_site_by_url_or_id(db, args.site_url, args.site_id)
    if not site_info:
        console.print("[bold red]錯誤：找不到指定的站點。[/bold red]")
        return

    site_id = site_info["id"]
    console.print(f"✅ 找到站點：{site_info['name']} (ID: {site_id})")

    # 確定 Sitemap URL
    sitemap_url = args.sitemap_url
    if not sitemap_url:
        # 嘗試自動發現 Sitemap
        domain = site_info["domain"]
        if domain.startswith("sc-domain:"):
            domain = domain.replace("sc-domain:", "")
            sitemap_url = f"https://{domain}/sitemap.xml"
        else:
            sitemap_url = f"{domain.rstrip('/')}/sitemap.xml"
        console.print(f"自動發現 Sitemap URL: {sitemap_url}")

    # Step 1: 獲取 Sitemap URL
    console.print(f"[bold blue]Step 1: 正在從 {sitemap_url} 獲取 URL...[/bold blue]")
    sitemap_urls = fetch_sitemap_urls(sitemap_url)
    if not sitemap_urls:
        console.print("[bold red]未能從 Sitemap 中獲取任何 URL。腳本終止。[/bold red]")
        return
    console.print(f"✅ 成功從 Sitemap 中找到 {len(sitemap_urls)} 個 URL。")

    # Step 2: 查詢性能數據
    console.print(f"[bold blue]Step 2: 正在查詢過去 {args.days} 天的性能數據...[/bold blue]")
    performance_data = get_performance_for_pages(db, site_id, sitemap_urls, args.days)

    if not performance_data:
        console.print("[yellow]在資料庫中未找到與 Sitemap URL 匹配的性能數據。[/yellow]")
        # 仍然創建報告，但所有數據都是 0
        performance_data = []
    else:
        console.print(f"✅ 成功查詢到 {len(performance_data)} 條 URL 的性能數據。")

    # Step 3: 生成報告
    create_performance_report(sitemap_urls, performance_data, site_info, args.output_file)


if __name__ == "__main__":
    main()
