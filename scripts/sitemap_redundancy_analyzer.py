#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速 Sitemap 冗餘分析工具

專為快速、完整地分析 sitemap URL 冗餘情況而設計，優化了資料庫查詢和結果呈現。

核心功能：
1. 智能 Sitemap 發現（可選，或自動檢測）。
2. 高效獲取 Sitemap 中的所有 URL（支持 sitemap 索引，並發處理）。
3. 一次性查詢資料庫中所有相關頁面，避免多次查詢。
4. 清晰的數據覆蓋情況和冗餘分析報告。

使用方法：
# 自動發現 sitemap 並進行分析
poetry run python scripts/sitemap_redundancy_analyzer.py --site-id 14 --days 30

# 手動指定 sitemap URL
poetry run python scripts/sitemap_redundancy_analyzer.py --site-id 14 --sitemap-url "https://example.com/sitemap.xml" --days 30
"""

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
from lxml import etree
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, track
from rich.prompt import Prompt
from rich.table import Table

# 將專案根目錄添加到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from src.containers import Container
from src.services.database import Database

console = Console()

SITEMAP_NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
COMMON_SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemaps.xml"]
REQUEST_TIMEOUT_SHORT = 5
REQUEST_TIMEOUT_LONG = 30
MAX_WORKERS = 10  # 並發下載的線程數


class SitemapAnalyzer:
    """快速冗餘分析器"""

    def __init__(self, db: Database):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; SitemapAnalyzer/1.0; +https://github.com/user/repo)"
            }
        )

    def discover_and_select_sitemap(self, domain: str, auto_select: bool = True) -> Optional[str]:
        """從 robots.txt 和常見路徑發現並選擇 sitemap"""
        if not domain.startswith(("http://", "https://")):
            domain = f"https://{domain}"

        console.print(Panel.fit(f"[bold blue]智能 Sitemap 發現[/bold blue]\n目標域名: {domain}"))

        # 1. 從 robots.txt 發現
        robots_url = urljoin(domain, "/robots.txt")
        sitemaps = []
        try:
            response = self.session.get(robots_url, timeout=REQUEST_TIMEOUT_SHORT)
            if response.status_code == 200:
                sitemap_pattern = re.compile(r"sitemap:\s*(.+)", re.IGNORECASE)
                sitemaps.extend([match.strip() for match in sitemap_pattern.findall(response.text)])
        except requests.RequestException as e:
            console.log(f"[yellow]無法讀取 {robots_url}: {e}[/yellow]")

        # 2. 檢查常見路徑
        for path in COMMON_SITEMAP_PATHS:
            sitemaps.append(urljoin(domain, path))

        # 3. 驗證並選擇
        validated_sitemaps = []
        for url in track(set(sitemaps), description="驗證 Sitemap..."):
            try:
                response = self.session.head(
                    url, timeout=REQUEST_TIMEOUT_SHORT, allow_redirects=True
                )
                if (
                    response.status_code == 200
                    and "xml" in response.headers.get("content-type", "").lower()
                ):
                    validated_sitemaps.append(str(response.url))  # 使用重定向後的最終 URL
                    console.print(f"✅ 找到有效 Sitemap: {response.url}")
            except requests.RequestException:
                continue

        if not validated_sitemaps:
            console.print("[bold red]❌ 未找到任何有效的 sitemap[/bold red]")
            return None

        if auto_select or len(validated_sitemaps) == 1:
            selected = validated_sitemaps[0]
            console.print(f"[bold green]自動選擇: {selected}[/bold green]")
            return selected

        # 讓用戶選擇
        table = Table(title="發現的有效 Sitemap")
        table.add_column("序號", style="cyan")
        table.add_column("URL", style="blue")
        for i, sitemap_url in enumerate(validated_sitemaps, 1):
            table.add_row(str(i), sitemap_url)
        console.print(table)

        choice = Prompt.ask(
            "選擇要使用的 sitemap (輸入序號)",
            choices=[str(i) for i in range(1, len(validated_sitemaps) + 1)],
            default="1",
        )
        return validated_sitemaps[int(choice) - 1]

    def _fetch_and_parse_single_sitemap(self, url: str) -> List[str]:
        """獲取並解析單個 sitemap 或 sitemap 索引，返回 URL 列表"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT_LONG)
            response.raise_for_status()  # 拋出 HTTP 錯誤
            root = etree.fromstring(response.content, parser=etree.XMLParser(recover=True))

            # 檢查是 sitemap 索引還是 url 集合
            if root.tag.endswith("sitemapindex"):
                xpath_expr = "//ns:sitemap/ns:loc"
            elif root.tag.endswith("urlset"):
                xpath_expr = "//ns:url/ns:loc"
            else:
                # 可能是沒有 namespace 的 sitemap
                if root.tag == "sitemapindex":
                    xpath_expr = "//sitemap/loc"
                else:
                    xpath_expr = "//url/loc"

            # 提取文本並過濾掉 None 或空字串
            return [
                elem.text for elem in root.xpath(xpath_expr, namespaces=SITEMAP_NS) if elem.text
            ]

        except requests.HTTPError as e:
            console.log(f"[red]HTTP 錯誤 {e.response.status_code} 於 {url}[/red]")
        except Exception as e:
            console.log(f"[red]處理 {url} 失敗: {e}[/red]")
        return []

    def fetch_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """高效獲取並解析 Sitemap，提取所有 URL，支持並發處理索引"""
        console.print(f"\n🔍 正在獲取 Sitemap: {sitemap_url}")

        initial_urls = self._fetch_and_parse_single_sitemap(sitemap_url)
        if not initial_urls:
            return []

        # 判斷是 sitemap 索引還是普通的 sitemap
        if initial_urls[0].endswith(".xml"):
            console.print(
                f"📄 檢測到 Sitemap 索引，包含 {len(initial_urls)} 個子 sitemap，開始並發處理..."
            )
            all_urls = []
            with Progress(console=console) as progress:
                task = progress.add_task("[cyan]解析子 Sitemap...", total=len(initial_urls))
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_url = {
                        executor.submit(self._fetch_and_parse_single_sitemap, url): url
                        for url in initial_urls
                    }
                    for future in as_completed(future_to_url):
                        try:
                            urls_from_sub = future.result()
                            all_urls.extend(urls_from_sub)
                        except Exception as e:
                            url = future_to_url[future]
                            console.log(f"[red]獲取子 sitemap {url} 時發生嚴重錯誤: {e}[/red]")
                        progress.update(task, advance=1)
            urls = all_urls
        else:
            urls = initial_urls

        console.print("\n📊 [bold]Sitemap URL 提取結果[/bold]")
        console.print(f"   🎯 Sitemap 總 URL 數: {len(urls):,} 個")
        console.print(f"   📄 來源: {sitemap_url}")
        return urls

    def get_db_pages_and_coverage(self, site_id: int, days: Optional[int]) -> Tuple[Set[str], dict]:
        """一次性獲取資料庫中的不重複頁面及數據覆蓋情況"""

        console.print("\n🔍 正在查詢資料庫...")

        date_clause = ""
        time_range_text = "全部時間"

        if days:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_clause = "AND date BETWEEN ? AND ?"
            params = [site_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]
            time_range_text = f"最近 {days} 天"
        else:
            params = [site_id]

        # 查詢數據覆蓋情況
        coverage_query = f"""
            SELECT date, COUNT(*) FROM gsc_performance_data
            WHERE site_id = ? {date_clause}
            GROUP BY date ORDER BY date DESC
        """
        with self.db._lock:
            coverage_results = self.db._connection.execute(coverage_query, params).fetchall()

        actual_days = len(coverage_results)
        total_records = sum(row[1] for row in coverage_results)

        console.print(f"📊 [bold]資料庫數據覆蓋情況[/bold] (查詢範圍: {time_range_text})")
        if days and days > 0:
            console.print(
                f"   ✅ 實際有數據天數: {actual_days} 天 ({actual_days / days * 100:.1f}%)"
            )
        else:
            console.print(f"   ✅ 實際有數據天數: {actual_days} 天")

        if actual_days > 0:
            console.print(
                f"   📅 數據日期範圍: {coverage_results[-1][0]} 到 {coverage_results[0][0]}"
            )
        console.print(f"   📈 總數據點記錄數: {total_records:,} 筆")

        # 查詢不重複頁面
        pages_query = (
            f"SELECT DISTINCT page FROM gsc_performance_data WHERE site_id = ? {date_clause}"
        )
        with self.db._lock:
            page_results = self.db._connection.execute(pages_query, params).fetchall()

        db_pages = {row[0] for row in page_results}
        console.print(f"   🎯 有數據的獨立頁面URL數: {len(db_pages):,} 個")

        coverage_info = {
            "queried_days": time_range_text,
            "actual_days": actual_days,
            "db_unique_pages": len(db_pages),
        }
        return db_pages, coverage_info

    def analyze_and_display(
        self, sitemap_urls: List[str], db_pages: Set[str], site_info: Dict, coverage_info: Dict
    ):
        """分析冗餘並顯示結果"""
        console.print("\n🔍 正在進行冗餘分析...")

        sitemap_set = set(sitemap_urls)

        urls_in_db = sitemap_set.intersection(db_pages)
        urls_not_in_db = sitemap_set - db_pages

        # 創建結果面板
        title = f"[bold]Sitemap 冗餘分析報告 for {site_info.get('name', '未知')}[/bold]"
        table = Table(title=title, show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="magenta")

        table.add_row("\n[bold]Sitemap 統計[/bold]", "")
        table.add_row("Sitemap 總 URL 數", f"{len(sitemap_urls):,}")
        table.add_row("去重後獨立 URL 數", f"{len(sitemap_set):,}")

        table.add_row("\n[bold]資料庫統計[/bold]", f"({coverage_info['queried_days']})")
        table.add_row("有數據的獨立 URL 數", f"{coverage_info['db_unique_pages']:,}")

        table.add_row("\n[bold]冗餘分析 (Sitemap vs 資料庫)[/bold]", "")
        table.add_row("✅ 有數據的 Sitemap URL", f"{len(urls_in_db):,}")
        table.add_row("❌ 無數據的 Sitemap URL", f"{len(urls_not_in_db):,}")

        if len(sitemap_set) > 0:
            redundancy_rate = len(urls_not_in_db) / len(sitemap_set) * 100
            coverage_rate = len(urls_in_db) / len(sitemap_set) * 100

            # 根據冗餘率顯示不同顏色的結果
            color = "green"
            if redundancy_rate > 50:
                color = "red"
            elif redundancy_rate > 20:
                color = "yellow"

            table.add_row(
                f"[{color}]冗餘率 (無數據的 URL 佔比)[/{color}]",
                f"[{color}]{redundancy_rate:.1f}%[/{color}]",
            )
            table.add_row(
                "[green]覆蓋率 (有數據的 URL 佔比)[/green]", f"[green]{coverage_rate:.1f}%[/green]"
            )

        console.print(Panel(table, expand=False))


def main():
    """主執行函數"""
    parser = argparse.ArgumentParser(description="快速 Sitemap 冗餘分析工具")
    parser.add_argument("--site-id", type=int, required=True, help="要分析的網站 ID")
    parser.add_argument(
        "--sitemap-url", type=str, action="append", help="手動指定 Sitemap URL（可多次使用）"
    )
    parser.add_argument("--days", type=int, help="查詢天數範圍（可選，預設查詢全部時間）")
    parser.add_argument(
        "--interactive-discovery", action="store_true", help="強制進行交互式 Sitemap 選擇"
    )

    args = parser.parse_args()

    console.print(Panel.fit("[bold blue]快速 Sitemap 冗餘分析工具[/bold blue]"))

    try:
        container = Container()
        db = container.database()
        console.print("✅ 資料庫連接成功")
    except Exception as e:
        console.print(f"[bold red]錯誤：無法連接資料庫: {e}[/bold red]")
        sys.exit(1)

    site_info = db.get_site_by_id(args.site_id)
    if not site_info:
        console.print(f"[bold red]錯誤：找不到 ID 為 {args.site_id} 的站點[/bold red]")
        sys.exit(1)

    analyzer = SitemapAnalyzer(db)

    # 獲取 Sitemap URL
    sitemap_urls_to_fetch = args.sitemap_url
    if not sitemap_urls_to_fetch:
        domain = site_info["domain"].replace("sc-domain:", "")
        # 如果使用 --interactive-discovery，則 auto_select 為 False
        discovered_url = analyzer.discover_and_select_sitemap(
            domain, auto_select=not args.interactive_discovery
        )
        if discovered_url:
            sitemap_urls_to_fetch = [discovered_url]
        else:
            sys.exit(1)

    all_sitemap_urls = []
    for url in sitemap_urls_to_fetch:
        all_sitemap_urls.extend(analyzer.fetch_sitemap_urls(url))

    if not all_sitemap_urls:
        console.print("[bold yellow]未能從指定的 Sitemap 中提取任何 URL。[/bold yellow]")
        sys.exit(0)

    db_pages, coverage_info = analyzer.get_db_pages_and_coverage(args.site_id, args.days)

    analyzer.analyze_and_display(all_sitemap_urls, db_pages, site_info, coverage_info)


if __name__ == "__main__":
    main()
