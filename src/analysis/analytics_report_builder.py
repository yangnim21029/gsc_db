#!/usr/bin/env python3
"""
GSC 分析報告構建器
重構為可調用函數，支持 CLI 整合
"""

import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import argparse
from datetime import datetime, timedelta
import os
import seaborn as sns
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# 專案模組導入
from .. import config

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設置現代化視覺風格 - 參考 Uber/Duolingo 設計
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#f8f9fa'
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['axes.spines.left'] = False
plt.rcParams['axes.spines.bottom'] = False
plt.rcParams['grid.color'] = '#e9ecef'
plt.rcParams['grid.linewidth'] = 0.8
plt.rcParams['grid.alpha'] = 0.7

# Uber/Duolingo 風格的配色方案
UBER_COLORS = {
    'primary': '#000000',
    'secondary': '#5c6ac4',
    'success': '#06d6a0',
    'warning': '#ffd166',
    'danger': '#ef476f',
    'info': '#118ab2',
    'light': '#f8f9fa',
    'dark': '#343a40'
}

DUOLINGO_COLORS = {
    'green': '#58cc02',
    'blue': '#1cb0f6',
    'red': '#ff4b4b',
    'yellow': '#ffc800',
    'purple': '#ce82ff',
    'orange': '#ff9600'
}


class GSCVisualizer:
    """GSC 數據可視化器"""

    def __init__(self, db_path: str = str(config.DB_PATH)):
        self.db_path = db_path or str(config.DB_PATH)

    def get_daily_stats(self, days=30):
        """獲取每日統計數據"""
        try:
            conn = sqlite3.connect(self.db_path)

            # 先獲取數據庫中的實際日期範圍
            cursor = conn.execute("SELECT MAX(date) FROM daily_rankings")
            latest_date_str = cursor.fetchone()[0]

            if not latest_date_str:
                print("數據庫中沒有數據")
                conn.close()
                return None

            # 以數據庫中的最新日期為基準計算範圍
            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=days - 1)

            query = """
            SELECT date,
                   SUM(clicks) as total_clicks,
                   SUM(impressions) as total_impressions,
                   AVG(position) as avg_position,
                   COUNT(*) as keyword_count
            FROM daily_rankings
            WHERE date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
            """

            df = pd.read_sql_query(
                query, conn, params=(
                    start_date, latest_date))
            conn.close()

            # 轉換日期格式
            df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            logger.error(f"獲取數據錯誤: {e}")
            return None

    def get_top_keywords(self, limit=20, days=7):
        """獲取表現最佳的關鍵字"""
        try:
            conn = sqlite3.connect(self.db_path)

            # 獲取數據庫中的最新日期
            cursor = conn.execute("SELECT MAX(date) FROM daily_rankings")
            latest_date_str = cursor.fetchone()[0]
            if not latest_date_str:
                conn.close()
                return None

            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=days - 1)

            query = """
            SELECT query as keyword,
                   SUM(clicks) as total_clicks,
                   SUM(impressions) as total_impressions,
                   AVG(position) as avg_position,
                   AVG(ctr) as avg_ctr
            FROM daily_rankings
            WHERE date >= ? AND date <= ?
            GROUP BY query
            ORDER BY total_clicks DESC
            LIMIT ?
            """

            df = pd.read_sql_query(
                query, conn, params=(
                    start_date, latest_date, limit))
            conn.close()

            return df

        except Exception as e:
            logger.error(f"獲取關鍵字數據錯誤: {e}")
            return None

    def get_page_performance(self, limit=15, days=7):
        """獲取頁面表現數據"""
        try:
            conn = sqlite3.connect(self.db_path)

            # 獲取數據庫中的最新日期
            cursor = conn.execute("SELECT MAX(date) FROM page_data")
            latest_date_str = cursor.fetchone()[0]
            if not latest_date_str:
                conn.close()
                return None

            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=days - 1)

            query = """
            SELECT page,
                   SUM(clicks) as total_clicks,
                   SUM(impressions) as total_impressions,
                   AVG(position) as avg_position,
                   AVG(ctr) as avg_ctr
            FROM page_data
            WHERE date >= ? AND date <= ?
            GROUP BY page
            ORDER BY total_clicks DESC
            LIMIT ?
            """

            df = pd.read_sql_query(
                query, conn, params=(
                    start_date, latest_date, limit))
            conn.close()

            # 簡化頁面路徑以便顯示
            def clean_page_url(url):
                import urllib.parse
                try:
                    # URL decode 處理中文
                    decoded_url = urllib.parse.unquote(url, encoding='utf-8')

                    # 提取有意義的部分
                    if '/' in decoded_url:
                        # 取最後一個路徑段
                        last_part = decoded_url.split('/')[-1]
                        # 如果是空的，取倒數第二個
                        if not last_part and len(decoded_url.split('/')) > 1:
                            last_part = decoded_url.split('/')[-2]
                    else:
                        last_part = decoded_url

                    # 移除查詢參數
                    if '?' in last_part:
                        last_part = last_part.split('?')[0]

                    # 限制長度
                    if len(last_part) > 35:
                        last_part = last_part[:32] + '...'

                    return last_part if last_part else '首頁'
                except BaseException:
                    # 如果解碼失敗，使用原始方法
                    short = url.split('/')[-1] if '/' in url else url
                    return short[:35] if len(short) > 35 else short

            df['page_short'] = df['page'].apply(clean_page_url)
            return df

        except Exception as e:
            logger.error(f"獲取頁面數據錯誤: {e}")
            return None

    def plot_daily_trends(self, days=30, save_path=None):
        """繪製每日趨勢圖"""
        df = self.get_daily_stats(days)
        if df is None or df.empty:
            print("沒有數據可供繪製")
            return None

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'GSC 數據趨勢分析 ({days} 天)', fontsize=16, fontweight='bold')

        # 點擊數趨勢
        axes[0, 0].plot(df['date'], df['total_clicks'], 
                       color=DUOLINGO_COLORS['blue'], linewidth=2.5, marker='o')
        axes[0, 0].set_title('每日點擊數', fontweight='bold')
        axes[0, 0].set_ylabel('點擊數')
        axes[0, 0].grid(True, alpha=0.3)

        # 展示數趨勢
        axes[0, 1].plot(df['date'], df['total_impressions'], 
                       color=DUOLINGO_COLORS['green'], linewidth=2.5, marker='s')
        axes[0, 1].set_title('每日展示數', fontweight='bold')
        axes[0, 1].set_ylabel('展示數')
        axes[0, 1].grid(True, alpha=0.3)

        # 平均排名趨勢
        axes[1, 0].plot(df['date'], df['avg_position'], 
                       color=DUOLINGO_COLORS['orange'], linewidth=2.5, marker='^')
        axes[1, 0].set_title('平均排名', fontweight='bold')
        axes[1, 0].set_ylabel('排名')
        axes[1, 0].invert_yaxis()  # 排名越小越好
        axes[1, 0].grid(True, alpha=0.3)

        # 關鍵字數量趨勢
        axes[1, 1].plot(df['date'], df['keyword_count'], 
                       color=DUOLINGO_COLORS['purple'], linewidth=2.5, marker='d')
        axes[1, 1].set_title('關鍵字數量', fontweight='bold')
        axes[1, 1].set_ylabel('關鍵字數')
        axes[1, 1].grid(True, alpha=0.3)

        # 格式化日期軸
        for ax in axes.flat:
            ax.tick_params(axis='x', rotation=45)
            ax.set_xlabel('日期')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"圖表已保存到: {save_path}")
        else:
            plt.show()

        return fig

    def plot_top_keywords(self, limit=20, days=7, save_path=None):
        """繪製頂級關鍵字圖表"""
        df = self.get_top_keywords(limit, days)
        if df is None or df.empty:
            print("沒有關鍵字數據可供繪製")
            return None

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'頂級關鍵字分析 (前 {limit} 名)', fontsize=16, fontweight='bold')

        # 點擊數前10名
        top_clicks = df.head(10)
        axes[0, 0].barh(range(len(top_clicks)), top_clicks['total_clicks'], 
                       color=DUOLINGO_COLORS['blue'])
        axes[0, 0].set_yticks(range(len(top_clicks)))
        axes[0, 0].set_yticklabels(top_clicks['keyword'])
        axes[0, 0].set_title('點擊數 Top 10', fontweight='bold')
        axes[0, 0].set_xlabel('點擊數')

        # 展示數前10名
        top_impressions = df.nlargest(10, 'total_impressions')
        axes[0, 1].barh(range(len(top_impressions)), top_impressions['total_impressions'], 
                       color=DUOLINGO_COLORS['green'])
        axes[0, 1].set_yticks(range(len(top_impressions)))
        axes[0, 1].set_yticklabels(top_impressions['keyword'])
        axes[0, 1].set_title('展示數 Top 10', fontweight='bold')
        axes[0, 1].set_xlabel('展示數')

        # 平均排名前10名（排名越小越好）
        top_position = df.nsmallest(10, 'avg_position')
        axes[1, 0].barh(range(len(top_position)), top_position['avg_position'], 
                       color=DUOLINGO_COLORS['orange'])
        axes[1, 0].set_yticks(range(len(top_position)))
        axes[1, 0].set_yticklabels(top_position['keyword'])
        axes[1, 0].set_title('平均排名 Top 10', fontweight='bold')
        axes[1, 0].set_xlabel('平均排名')

        # CTR 前10名
        top_ctr = df.nlargest(10, 'avg_ctr')
        axes[1, 1].barh(range(len(top_ctr)), top_ctr['avg_ctr'] * 100, 
                       color=DUOLINGO_COLORS['purple'])
        axes[1, 1].set_yticks(range(len(top_ctr)))
        axes[1, 1].set_yticklabels(top_ctr['keyword'])
        axes[1, 1].set_title('CTR Top 10', fontweight='bold')
        axes[1, 1].set_xlabel('CTR (%)')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"圖表已保存到: {save_path}")
        else:
            plt.show()

        return fig

    def plot_page_performance(self, limit=15, days=7, save_path=None):
        """繪製頁面表現圖表"""
        df = self.get_page_performance(limit, days)
        if df is None or df.empty:
            print("沒有頁面數據可供繪製")
            return None

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'頁面表現分析 (前 {limit} 名)', fontsize=16, fontweight='bold')

        # 點擊數前10名
        top_clicks = df.head(10)
        axes[0, 0].barh(range(len(top_clicks)), top_clicks['total_clicks'], 
                       color=DUOLINGO_COLORS['blue'])
        axes[0, 0].set_yticks(range(len(top_clicks)))
        axes[0, 0].set_yticklabels(top_clicks['page_short'])
        axes[0, 0].set_title('頁面點擊數 Top 10', fontweight='bold')
        axes[0, 0].set_xlabel('點擊數')

        # 展示數前10名
        top_impressions = df.nlargest(10, 'total_impressions')
        axes[0, 1].barh(range(len(top_impressions)), top_impressions['total_impressions'], 
                       color=DUOLINGO_COLORS['green'])
        axes[0, 1].set_yticks(range(len(top_impressions)))
        axes[0, 1].set_yticklabels(top_impressions['page_short'])
        axes[0, 1].set_title('頁面展示數 Top 10', fontweight='bold')
        axes[0, 1].set_xlabel('展示數')

        # 平均排名前10名
        top_position = df.nsmallest(10, 'avg_position')
        axes[1, 0].barh(range(len(top_position)), top_position['avg_position'], 
                       color=DUOLINGO_COLORS['orange'])
        axes[1, 0].set_yticks(range(len(top_position)))
        axes[1, 0].set_yticklabels(top_position['page_short'])
        axes[1, 0].set_title('頁面平均排名 Top 10', fontweight='bold')
        axes[1, 0].set_xlabel('平均排名')

        # CTR 前10名
        top_ctr = df.nlargest(10, 'avg_ctr')
        axes[1, 1].barh(range(len(top_ctr)), top_ctr['avg_ctr'] * 100, 
                       color=DUOLINGO_COLORS['purple'])
        axes[1, 1].set_yticks(range(len(top_ctr)))
        axes[1, 1].set_yticklabels(top_ctr['page_short'])
        axes[1, 1].set_title('頁面 CTR Top 10', fontweight='bold')
        axes[1, 1].set_xlabel('CTR (%)')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"圖表已保存到: {save_path}")
        else:
            plt.show()

        return fig

    def data_summary(self):
        """生成數據摘要"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 基本統計
            cursor = conn.execute("SELECT COUNT(*) FROM daily_rankings")
            total_records = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT date) FROM daily_rankings")
            total_days = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT query) FROM daily_rankings")
            total_keywords = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT page) FROM page_data")
            total_pages = cursor.fetchone()[0]
            
            # 最新數據日期
            cursor = conn.execute("SELECT MAX(date) FROM daily_rankings")
            latest_date = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_records': total_records,
                'total_days': total_days,
                'total_keywords': total_keywords,
                'total_pages': total_pages,
                'latest_date': latest_date
            }
            
        except Exception as e:
            logger.error(f"生成數據摘要錯誤: {e}")
            return None


def _generate_summary_plot(visualizer: GSCVisualizer, days: int = 30, save_path: Optional[str] = None) -> Optional[plt.Figure]:
    """生成摘要圖表"""
    try:
        return visualizer.plot_daily_trends(days=days, save_path=save_path)
    except Exception as e:
        logger.error(f"生成摘要圖表失敗: {e}")
        return None


def _create_markdown_report(visualizer: GSCVisualizer, days: int = 30, output_path: str = "gsc_report.md") -> bool:
    """創建 Markdown 報告"""
    try:
        # 獲取數據摘要
        summary = visualizer.data_summary()
        if not summary:
            logger.error("無法獲取數據摘要")
            return False

        # 獲取關鍵字數據
        keywords_df = visualizer.get_top_keywords(limit=20, days=days)
        pages_df = visualizer.get_page_performance(limit=15, days=days)

        # 生成報告內容
        report_content = f"""# Google Search Console 數據分析報告

## 📊 數據概覽

- **總記錄數**: {summary['total_records']:,}
- **數據天數**: {summary['total_days']} 天
- **關鍵字數量**: {summary['total_keywords']:,}
- **頁面數量**: {summary['total_pages']:,}
- **最新數據日期**: {summary['latest_date']}

## 🎯 分析期間

本報告分析最近 **{days} 天** 的數據表現。

## 📈 關鍵字表現 Top 20

| 排名 | 關鍵字 | 點擊數 | 展示數 | 平均排名 | CTR |
|------|--------|--------|--------|----------|-----|
"""

        if keywords_df is not None and not keywords_df.empty:
            for i, row in keywords_df.head(20).iterrows():
                report_content += f"| {i+1} | {row['keyword']} | {row['total_clicks']:,} | {row['total_impressions']:,} | {row['avg_position']:.1f} | {row['avg_ctr']:.2%} |\n"
        else:
            report_content += "| - | 無數據 | - | - | - | - |\n"

        report_content += f"""

## 📄 頁面表現 Top 15

| 排名 | 頁面 | 點擊數 | 展示數 | 平均排名 | CTR |
|------|------|--------|--------|----------|-----|
"""

        if pages_df is not None and not pages_df.empty:
            for i, row in pages_df.head(15).iterrows():
                report_content += f"| {i+1} | {row['page_short']} | {row['total_clicks']:,} | {row['total_impressions']:,} | {row['avg_position']:.1f} | {row['avg_ctr']:.2%} |\n"
        else:
            report_content += "| - | 無數據 | - | - | - | - |\n"

        report_content += f"""

## 📅 報告生成時間

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

*此報告由 GSC 數據分析工具自動生成*
"""

        # 保存報告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"Markdown 報告已保存到: {output_path}")
        return True

    except Exception as e:
        logger.error(f"創建 Markdown 報告失敗: {e}")
        return False


def build_report(
    output_path: str = "gsc_report.md",
    days: int = 30,
    include_plots: bool = True,
    plot_save_dir: Optional[str] = None,
    db_path: str = str(config.DB_PATH)
) -> Dict[str, Any]:
    """
    構建 GSC 數據分析報告
    
    Args:
        output_path: 報告輸出路徑
        days: 分析天數
        include_plots: 是否包含圖表
        plot_save_dir: 圖表保存目錄
        db_path: 數據庫路徑
    
    Returns:
        包含報告生成結果的字典
    """
    result = {
        'success': False,
        'report_path': output_path,
        'plots_generated': [],
        'errors': []
    }
    
    try:
        logger.info(f"開始生成 GSC 數據分析報告，分析 {days} 天數據...")
        
        # 初始化可視化器
        visualizer = GSCVisualizer(db_path)
        
        # 檢查數據庫是否存在
        if not Path(db_path).exists():
            error_msg = f"數據庫文件不存在: {db_path}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result
        
        # 生成 Markdown 報告
        if not _create_markdown_report(visualizer, days, output_path):
            error_msg = "生成 Markdown 報告失敗"
            result['errors'].append(error_msg)
            return result
        
        # 生成圖表
        if include_plots:
            plot_dir = Path(plot_save_dir) if plot_save_dir else config.ASSETS_DIR
            plot_dir.mkdir(exist_ok=True)
            
            # 生成摘要圖表
            summary_plot_path = plot_dir / "daily_trends.png"
            if _generate_summary_plot(visualizer, days, str(summary_plot_path)):
                result['plots_generated'].append(str(summary_plot_path))
            
            # 生成關鍵字圖表
            keywords_plot_path = plot_dir / "top_keywords.png"
            try:
                visualizer.plot_top_keywords(limit=20, days=days, save_path=str(keywords_plot_path))
                result['plots_generated'].append(str(keywords_plot_path))
            except Exception as e:
                logger.error(f"生成關鍵字圖表失敗: {e}")
                result['errors'].append(f"關鍵字圖表生成失敗: {e}")
            
            # 生成頁面表現圖表
            pages_plot_path = plot_dir / "page_performance.png"
            try:
                visualizer.plot_page_performance(limit=15, days=days, save_path=str(pages_plot_path))
                result['plots_generated'].append(str(pages_plot_path))
            except Exception as e:
                logger.error(f"生成頁面表現圖表失敗: {e}")
                result['errors'].append(f"頁面表現圖表生成失敗: {e}")
        
        result['success'] = True
        logger.info(f"報告生成完成: {output_path}")
        
        # 添加數據摘要
        summary = visualizer.data_summary()
        if summary:
            result['summary'] = summary
        
        return result
        
    except Exception as e:
        error_msg = f"生成報告時發生錯誤: {e}"
        logger.error(error_msg)
        result['errors'].append(error_msg)
        return result


def main():
    """主函數 - 用於直接運行腳本"""
    parser = argparse.ArgumentParser(description='GSC 數據分析報告生成器')
    parser.add_argument('--output', '-o', default='gsc_report.md', 
                       help='輸出報告文件路徑')
    parser.add_argument('--days', '-d', type=int, default=30, 
                       help='分析天數 (默認: 30)')
    parser.add_argument('--no-plots', action='store_true', 
                       help='不生成圖表')
    parser.add_argument('--plot-dir', default='assets', 
                       help='圖表保存目錄')
    parser.add_argument('--db', default='gsc_data.db', 
                       help='數據庫文件路徑')
    
    args = parser.parse_args()
    
    # 調用主函數
    result = build_report(
        output_path=args.output,
        days=args.days,
        include_plots=not args.no_plots,
        plot_save_dir=args.plot_dir,
        db_path=args.db
    )
    
    if result['success']:
        print(f"✅ 報告生成成功: {result['report_path']}")
        if result['plots_generated']:
            print(f"📊 生成的圖表: {', '.join(result['plots_generated'])}")
        if 'summary' in result:
            summary = result['summary']
            print(f"📈 數據摘要: {summary['total_records']:,} 記錄, {summary['total_days']} 天, {summary['total_keywords']:,} 關鍵字")
    else:
        print("❌ 報告生成失敗")
        for error in result['errors']:
            print(f"  - {error}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
