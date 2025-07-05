#!/usr/bin/env python3
"""
GSC 每小時表現分析工具
專門用於分析搜索流量的時段分佈和表現趨勢
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
import warnings

# 專案模組導入
from .. import config

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 完全抑制所有 matplotlib 相關警告
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.backends')
warnings.filterwarnings('ignore', category=RuntimeWarning, module='matplotlib')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.text')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.rcsetup')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.cbook')

# 設置現代化視覺風格
plt.style.use('seaborn-v0_8-whitegrid')

# 更強健的字體配置，完全處理 emoji 和中文顯示問題
def configure_matplotlib_fonts():
    """配置 matplotlib 字體以支持 emoji 和中文，完全抑制警告"""
    import platform
    import matplotlib.font_manager as fm
    import matplotlib
    import matplotlib.pyplot as plt
    
    # 完全抑制字體相關警告
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    # 根據操作系統選擇合適的字體
    system = platform.system()
    
    if system == "Darwin":  # macOS
        font_list = [
            'Arial Unicode MS',  # 最兼容的字體，支持 emoji 和中文
            'Helvetica Neue',
            'Helvetica',
            'Arial',
            'DejaVu Sans'
        ]
    elif system == "Windows":
        font_list = [
            'Arial Unicode MS',  # 最兼容的字體
            'Segoe UI',
            'Arial',
            'DejaVu Sans'
        ]
    else:  # Linux and others
        font_list = [
            'DejaVu Sans',  # Linux 最可靠的字體
            'Liberation Sans',
            'Arial',
            'Helvetica'
        ]
    
    # 檢查字體可用性並設置
    available_fonts = []
    
    for font in font_list:
        try:
            # 更嚴格的字體檢查
            font_path = fm.findfont(font)
            if font_path and font_path != matplotlib.rcParams['font.sans-serif'][0]:
                available_fonts.append(font)
        except Exception:
            continue
    
    # 如果沒有找到合適字體，使用基本字體
    if not available_fonts:
        available_fonts = ['DejaVu Sans', 'Arial', 'Helvetica']
    
    # 設置字體參數
    plt.rcParams['font.sans-serif'] = available_fonts
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = '#f8f9fa'
    
    # 使用更可靠的方法設置 unicode_minus
    plt.rc('axes', unicode_minus=False)
    
    # 清除字體緩存以確保新配置生效
    try:
        # 嘗試清除字體緩存
        if hasattr(fm.findfont, 'cache_clear'):
            fm.findfont.cache_clear()
    except Exception:
        pass
    
    # 設置全局警告過濾
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.backends')
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='matplotlib')
    
    return True, True

# 配置字體並獲取支持狀態
EMOJI_SUPPORTED, CHINESE_SUPPORTED = configure_matplotlib_fonts()

# 專業配色方案
HOURLY_COLORS = {
    'morning': '#ffbe0b',    # 早晨 6-11
    'noon': '#fb5607',       # 中午 12-17
    'evening': '#8338ec',    # 晚上 18-23
    'night': '#3a86ff',      # 深夜 0-5
    'primary': '#06d6a0',
    'secondary': '#f77f00',
    'accent': '#fcbf49'
}


class HourlyAnalyzer:
    """每小時數據分析器"""

    def __init__(self, db_path: str = str(config.DB_PATH)):
        self.db_path = db_path or str(config.DB_PATH)

    def get_hourly_summary(self, days=7):
        """獲取每小時數據摘要"""
        try:
            conn = sqlite3.connect(self.db_path)

            # 獲取最新日期
            cursor = conn.execute("SELECT MAX(date) FROM hourly_rankings")
            latest_date_str = cursor.fetchone()[0]
            if not latest_date_str:
                return None

            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=days - 1)

            query = """
            SELECT
                hour,
                COUNT(*) as total_records,
                COUNT(DISTINCT query) as unique_queries,
                COUNT(DISTINCT date) as days_active,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                AVG(ctr) as avg_ctr
            FROM hourly_rankings
            WHERE date >= ? AND date <= ?
            GROUP BY hour
            ORDER BY hour
            """

            df = pd.read_sql_query(
                query, conn, params=(
                    start_date, latest_date))
            conn.close()

            return df

        except Exception as e:
            logger.error(f"獲取每小時摘要錯誤: {e}")
            return None

    def get_daily_hourly_heatmap(self, days=7):
        """獲取每日每小時熱力圖數據"""
        try:
            conn = sqlite3.connect(self.db_path)

            cursor = conn.execute("SELECT MAX(date) FROM hourly_rankings")
            latest_date_str = cursor.fetchone()[0]
            if not latest_date_str:
                return None

            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=days - 1)

            query = """
            SELECT
                date,
                hour,
                COUNT(*) as records,
                SUM(clicks) as clicks,
                SUM(impressions) as impressions,
                AVG(position) as avg_position
            FROM hourly_rankings
            WHERE date >= ? AND date <= ?
            GROUP BY date, hour
            ORDER BY date, hour
            """

            df = pd.read_sql_query(
                query, conn, params=(
                    start_date, latest_date))
            conn.close()

            return df

        except Exception as e:
            logger.error(f"獲取熱力圖數據錯誤: {e}")
            return None

    def get_peak_hours_analysis(self, days=7):
        """分析高峰時段"""
        df = self.get_hourly_summary(days)
        if df is None or df.empty:
            return None

        # 定義時段
        df['time_period'] = df['hour'].apply(self._categorize_hour)

        # 按時段聚合
        period_stats = df.groupby('time_period').agg({
            'total_clicks': 'sum',
            'total_impressions': 'sum',
            'unique_queries': 'sum',
            'avg_position': 'mean'
        }).reset_index()

        return df, period_stats

    def _categorize_hour(self, hour):
        """將小時分類為時段"""
        if 6 <= hour <= 11:
            return '早晨 (6-11)'
        elif 12 <= hour <= 17:
            return '中午 (12-17)'
        elif 18 <= hour <= 23:
            return '晚上 (18-23)'
        else:
            return '深夜 (0-5)'

    def plot_hourly_trends(self, days=7, save_path=None):
        """繪製每小時趨勢圖"""
        df = self.get_hourly_summary(days)
        if df is None or df.empty:
            logger.error("無法獲取每小時數據")
            return None

        fig = plt.figure(figsize=(16, 12), constrained_layout=True)
        gs = fig.add_gridspec(3, 2, height_ratios=[2, 2, 1])

        # 主要趨勢圖
        ax1 = fig.add_subplot(gs[0, :])

        # 雙軸：點擊量和曝光量
        ax1_twin = ax1.twinx()

        # 點擊量線條
        ax1.plot(
            df['hour'],
            df['total_clicks'],
            color=HOURLY_COLORS['primary'],
            linewidth=4,
            marker='o',
            markersize=8,
            markerfacecolor='white',
            markeredgewidth=3,
            markeredgecolor=HOURLY_COLORS['primary'],
            label='點擊量')

        # 曝光量區域圖
        ax1_twin.fill_between(df['hour'], df['total_impressions'],
                              color=HOURLY_COLORS['secondary'], alpha=0.3)
        ax1_twin.plot(df['hour'], df['total_impressions'],
                      color=HOURLY_COLORS['secondary'], linewidth=2,
                      linestyle='--', label='曝光量')

        # 美化主圖
        ax1.set_title(f'24小時搜索表現趨勢 (近{days}天)',
                      fontsize=18, fontweight='bold', pad=20)
        ax1.set_xlabel('小時', fontsize=12, fontweight='bold')
        ax1.set_ylabel(
            '點擊量',
            fontsize=12,
            color=HOURLY_COLORS['primary'],
            fontweight='bold')
        ax1_twin.set_ylabel(
            '曝光量',
            fontsize=12,
            color=HOURLY_COLORS['secondary'],
            fontweight='bold')

        # 設置刻度
        ax1.set_xticks(range(0, 24, 2))
        ax1.grid(True, alpha=0.3)

        # 添加圖例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        # 子圖1：每小時關鍵字數量
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.bar(df['hour'], df['unique_queries'],
                color=HOURLY_COLORS['accent'], alpha=0.8, edgecolor='white', linewidth=1)
        ax2.set_title('每小時關鍵字數量', fontsize=14, fontweight='bold')
        ax2.set_xlabel('小時')
        ax2.set_ylabel('關鍵字數量')
        ax2.set_xticks(range(0, 24, 2))
        ax2.grid(True, alpha=0.3)

        # 子圖2：每小時平均排名
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(df['hour'], df['avg_position'],
                 color='#e74c3c', linewidth=3, marker='s', markersize=6)
        ax3.fill_between(df['hour'], df['avg_position'],
                         color='#e74c3c', alpha=0.3)
        ax3.set_title('每小時平均排名', fontsize=14, fontweight='bold')
        ax3.set_xlabel('小時')
        ax3.set_ylabel('平均排名')
        ax3.set_xticks(range(0, 24, 2))
        ax3.invert_yaxis()
        ax3.grid(True, alpha=0.3)

        # 統計摘要
        ax4 = fig.add_subplot(gs[2, :])
        ax4.axis('off')

        # 計算統計數據
        peak_hour = df.loc[df['total_clicks'].idxmax()]
        low_hour = df.loc[df['total_clicks'].idxmin()]
        total_clicks = df['total_clicks'].sum()
        total_impressions = df['total_impressions'].sum()

        # 使用純文字格式，避免 emoji 字體問題
        stats_text = f"""
        統計摘要 (近{days}天)
        
        [高峰] 高峰時段: {peak_hour['hour']}點 ({peak_hour['total_clicks']:,}次點擊)
        [低谷] 低谷時段: {low_hour['hour']}點 ({low_hour['total_clicks']:,}次點擊)
        [趨勢] 點擊總量: {total_clicks:,}
        [曝光] 曝光總量: {total_impressions:,}
        [關鍵字] 關鍵字總數: {df['unique_queries'].sum():,}
        """

        ax4.text(0.05, 0.5, stats_text, transform=ax4.transAxes,
                 fontsize=12, verticalalignment='center',
                 bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.8))

        # Using constrained_layout instead of tight_layout for better compatibility

        if save_path:
            if not save_path.endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                save_path += '.png'

            save_path_obj = Path(save_path)
            if not save_path_obj.parent.exists():
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path_obj, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            logger.info(f"📈 每小時趨勢圖已保存到: {save_path}")
            return save_path
        else:
            plt.show()
            return None

    def plot_heatmap(self, days=7, save_path=None):
        """繪製每日每小時熱力圖"""
        df = self.get_daily_hourly_heatmap(days)
        if df is None or df.empty:
            logger.error("無法獲取熱力圖數據")
            return None

        # 創建透視表
        pivot_clicks = df.pivot(
            index='date',
            columns='hour',
            values='clicks').fillna(0)
        pivot_impressions = df.pivot(
            index='date',
            columns='hour',
            values='impressions').fillna(0)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), constrained_layout=True)

        # 點擊量熱力圖
        sns.heatmap(pivot_clicks, annot=True, fmt='.0f', cmap='YlOrRd',
                    ax=ax1, cbar_kws={'label': '點擊量'})
        ax1.set_title('每日每小時點擊量分布', fontsize=16, fontweight='bold', pad=20)
        ax1.set_xlabel('小時', fontsize=12)
        ax1.set_ylabel('日期', fontsize=12)

        # 曝光量熱力圖
        sns.heatmap(pivot_impressions, annot=True, fmt='.0f', cmap='Blues',
                    ax=ax2, cbar_kws={'label': '曝光量'})
        ax2.set_title('每日每小時曝光量分布', fontsize=16, fontweight='bold', pad=20)
        ax2.set_xlabel('小時', fontsize=12)
        ax2.set_ylabel('日期', fontsize=12)

        # Using constrained_layout instead of tight_layout for better compatibility

        if save_path:
            if not save_path.endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                save_path += '.png'

            save_path_obj = Path(save_path)
            if not save_path_obj.parent.exists():
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path_obj, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            logger.info(f"🔥 熱力圖已保存到: {save_path}")
            return save_path
        else:
            plt.show()
            return None

    def plot_peak_analysis(self, days=7, save_path=None):
        """繪製高峰時段分析"""
        hourly_df, period_df = self.get_peak_hours_analysis(days)
        if hourly_df is None or period_df is None:
            logger.error("無法獲取高峰分析數據")
            return None

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12), constrained_layout=True)

        # 時段點擊量分布
        colors = [HOURLY_COLORS['night'], HOURLY_COLORS['morning'],
                  HOURLY_COLORS['noon'], HOURLY_COLORS['evening']]

        wedges, texts, autotexts = ax1.pie(period_df['total_clicks'],
                                           labels=period_df['time_period'],
                                           colors=colors, autopct='%1.1f%%',
                                           startangle=90)
        ax1.set_title('各時段點擊量分布', fontsize=14, fontweight='bold')

        # 時段曝光量對比
        bars = ax2.bar(range(len(period_df)), period_df['total_impressions'],
                       color=colors, alpha=0.8, edgecolor='white', linewidth=2)
        ax2.set_title('各時段曝光量對比', fontsize=14, fontweight='bold')
        ax2.set_xticks(range(len(period_df)))
        ax2.set_xticklabels(period_df['time_period'], rotation=45)
        ax2.set_ylabel('曝光量')

        # 添加數值標籤
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(f'{int(height):,}',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3), textcoords="offset points",
                         ha='center', va='bottom', fontweight='bold')

        # 每小時點擊趨勢（彩虹圖）
        for i, hour in enumerate(hourly_df['hour']):
            color = (colors[0] if hour < 6 else
                     colors[1] if hour < 12 else
                     colors[2] if hour < 18 else
                     colors[3])
            ax3.bar(hour, hourly_df.iloc[i]['total_clicks'],
                    color=color, alpha=0.8, width=0.8)

        ax3.set_title('24小時點擊量分布', fontsize=14, fontweight='bold')
        ax3.set_xlabel('小時')
        ax3.set_ylabel('點擊量')
        ax3.set_xticks(range(0, 24, 2))

        # 排名表現
        ax4.plot(hourly_df['hour'], hourly_df['avg_position'],
                 color='#e74c3c', linewidth=3, marker='o', markersize=5)
        ax4.fill_between(hourly_df['hour'], hourly_df['avg_position'],
                         color='#e74c3c', alpha=0.3)
        ax4.set_title('24小時平均排名變化', fontsize=14, fontweight='bold')
        ax4.set_xlabel('小時')
        ax4.set_ylabel('平均排名')
        ax4.set_xticks(range(0, 24, 2))
        ax4.invert_yaxis()

        # Using constrained_layout instead of tight_layout for better compatibility

        if save_path:
            if not save_path.endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                save_path += '.png'

            save_path_obj = Path(save_path)
            if not save_path_obj.parent.exists():
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path_obj, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            logger.info(f"⏰ 高峰分析圖已保存到: {save_path}")
            return save_path
        else:
            plt.show()
            return None

    def generate_hourly_report(self, days=7, output_path="hourly_report.md"):
        """生成每小時數據報告"""
        try:
            # 基本統計
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM hourly_rankings")
            total_records = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(DISTINCT date) FROM hourly_rankings")
            total_days = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(DISTINCT query) FROM hourly_rankings")
            unique_queries = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT MIN(date), MAX(date) FROM hourly_rankings")
            date_range = cursor.fetchone()

            # 每小時摘要
            df = self.get_hourly_summary(days)
            
            # 生成報告內容
            report_content = f"""# GSC 每小時數據分析報告

## 📊 數據概覽

- **總記錄數**: {total_records:,}
- **覆蓋天數**: {total_days}
- **獨特關鍵字**: {unique_queries:,}
- **日期範圍**: {date_range[0]} 至 {date_range[1]}

## 🎯 分析期間

本報告分析最近 **{days} 天** 的每小時表現。

## 📈 每小時表現摘要

| 小時 | 點擊數 | 展示數 | 關鍵字數 | 平均排名 | CTR |
|------|--------|--------|----------|----------|-----|
"""

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    hour_val = row['hour']
                    try:
                        hour_val = int(round(float(hour_val)))
                    except Exception:
                        hour_val = 0
                    report_content += f"| {hour_val:02d}:00 | {int(row['total_clicks']):,} | {int(row['total_impressions']):,} | {int(row['unique_queries']):,} | {row['avg_position']:.1f} | {row['avg_ctr']:.2%} |\n"
                
                # 添加統計摘要
                peak_hour = df.loc[df['total_clicks'].idxmax()]
                low_hour = df.loc[df['total_clicks'].idxmin()]
                
                report_content += f"""

## 🏆 高峰時段分析

- **高峰時段**: {peak_hour['hour']:02d}:00 ({peak_hour['total_clicks']:,}次點擊)
- **低谷時段**: {low_hour['hour']:02d}:00 ({low_hour['total_clicks']:,}次點擊)
- **點擊總量**: {df['total_clicks'].sum():,}
- **曝光總量**: {df['total_impressions'].sum():,}
- **關鍵字總數**: {df['unique_queries'].sum():,}
"""
            else:
                report_content += "| - | 無數據 | - | - | - | - |\n"

            report_content += f"""

## 📅 報告生成時間

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

*此報告由 GSC 每小時數據分析工具自動生成*
"""

            # 保存報告
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            conn.close()
            logger.info(f"📄 每小時報告已保存到: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成每小時報告失敗: {e}")
            return None


def _generate_hourly_trends_plot(analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None) -> Optional[str]:
    """生成每小時趨勢圖"""
    try:
        return analyzer.plot_hourly_trends(days=days, save_path=save_path)
    except Exception as e:
        logger.error(f"生成每小時趨勢圖失敗: {e}")
        return None


def _generate_hourly_heatmap(analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None) -> Optional[str]:
    """生成每小時熱力圖"""
    try:
        return analyzer.plot_heatmap(days=days, save_path=save_path)
    except Exception as e:
        logger.error(f"生成每小時熱力圖失敗: {e}")
        return None


def _generate_peak_analysis_plot(analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None) -> Optional[str]:
    """生成高峰分析圖"""
    try:
        return analyzer.plot_peak_analysis(days=days, save_path=save_path)
    except Exception as e:
        logger.error(f"生成高峰分析圖失敗: {e}")
        return None

def _generate_hourly_report(analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None) -> Optional[str]:
    """生成每小時報告"""
    try:
        # The analyzer method expects output_path, so we pass save_path to it.
        if save_path is None:
            return None
        return analyzer.generate_hourly_report(days=days, output_path=save_path)
    except Exception as e:
        logger.error(f"生成每小時報告失敗: {e}")
        return None

# 分析任務註冊表，方便擴展
ANALYSIS_REGISTRY = {
    'trends': {
        'function': _generate_hourly_trends_plot,
        'type': 'plot',
        'filename': 'hourly_trends.png'
    },
    'heatmap': {
        'function': _generate_hourly_heatmap,
        'type': 'plot',
        'filename': 'hourly_heatmap.png'
    },
    'peaks': {
        'function': _generate_peak_analysis_plot,
        'type': 'plot',
        'filename': 'peak_analysis.png'
    },
    'report': {
        'function': _generate_hourly_report,
        'type': 'report',
        'filename': 'hourly_report.md'
    }
}

def _fetch_hourly_data_gemini(conn, days: int, site_url: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches and aggregates performance data by hour from the database (Gemini style).
    This query assumes the 'date' column is a format that SQLite's strftime can parse (e.g., 'YYYY-MM-DD HH:MM:SS').
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    query = """
    SELECT
        CAST(strftime('%H', date) AS INTEGER) as hour,
        SUM(clicks) as total_clicks,
        SUM(impressions) as total_impressions
    FROM gsc_data
    WHERE date(date) >= ? AND date(date) <= ?
    """
    params = [str(start_date), str(end_date)]
    if site_url:
        query += " AND site_url = ?"
        params.append(site_url)
    query += " GROUP BY hour ORDER BY hour ASC"
    return pd.read_sql_query(query, conn, params=params)


def _generate_hourly_plot_gemini(df: pd.DataFrame, output_dir: Path, filename_prefix: str) -> Optional[Path]:
    """Generates and saves a plot of clicks by hour of the day (Gemini style)."""
    if df.empty:
        return None
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(14, 7), constrained_layout=True)
    sns.barplot(x='hour', y='total_clicks', data=df, palette='plasma', hue='hour', dodge=False, legend=False)
    plt.title(f'{filename_prefix} - Clicks by Hour of Day (UTC)', fontsize=16, pad=20)
    plt.xlabel('Hour of Day', fontsize=12)
    plt.ylabel('Total Clicks', fontsize=12)
    plt.xticks(range(0, 24))
    # Using constrained_layout instead of tight_layout for better compatibility
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_path = output_dir / f"{filename_prefix}_Hourly_Trends.png"
    plt.savefig(plot_path)
    plt.close()
    return plot_path


def run_hourly_analysis(
    analysis_type: str = "trends",
    days: int = 7,
    output_path: Optional[str] = None,
    include_plots: bool = True,
    plot_save_dir: Optional[str] = None,
    db_path: str = str(config.DB_PATH)
) -> Dict[str, Any]:
    """
    運行每小時數據分析
    
    Args:
        analysis_type: 分析類型 ('trends', 'heatmap', 'peaks', 'report', 'all')
        days: 分析天數
        output_path: 報告輸出路徑
        include_plots: 是否包含圖表
        plot_save_dir: 圖表保存目錄
        db_path: 數據庫路徑
    
    Returns:
        包含分析結果的字典
    """
    result = {
        'success': False,
        'analysis_type': analysis_type,
        'plots_generated': [],
        'report_path': None,
        'errors': []
    }
    
    try:
        logger.info(f"開始每小時數據分析，類型: {analysis_type}，天數: {days}")
        
        # 初始化分析器
        analyzer = HourlyAnalyzer(db_path)
        
        # 檢查數據庫是否存在
        if not Path(db_path).exists():
            error_msg = f"數據庫文件不存在: {db_path}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result
        
        # 檢查每小時數據表是否存在
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hourly_rankings'")
            if not cursor.fetchone():
                error_msg = "每小時數據表 'hourly_rankings' 不存在"
                logger.error(error_msg)
                result['errors'].append(error_msg)
                conn.close()
                return result
            conn.close()
        except Exception as e:
            error_msg = f"檢查數據庫結構失敗: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result
        
        # 確定要運行的分析任務
        analyses_to_run = []
        if analysis_type == 'all':
            analyses_to_run = list(ANALYSIS_REGISTRY.keys())
        elif analysis_type in ANALYSIS_REGISTRY:
            analyses_to_run = [analysis_type]
        else:
            error_msg = f"無效的分析類型: {analysis_type}. 可用類型: {list(ANALYSIS_REGISTRY.keys()) + ['all']}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result

        # 執行分析任務
        for name in analyses_to_run:
            task = ANALYSIS_REGISTRY[name]
            
            if task['type'] == 'plot' and include_plots:
                plot_dir = Path(plot_save_dir) if plot_save_dir else config.ASSETS_DIR
                plot_dir.mkdir(exist_ok=True)
                save_path = plot_dir / task['filename']
                
                if task['function'](analyzer, days, str(save_path)):
                    result['plots_generated'].append(str(save_path))

            elif task['type'] == 'report':
                report_save_path = output_path
                if not report_save_path:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_save_path = config.REPORTS_DIR / f"hourly_report_{timestamp}.md"
                
                if task['function'](analyzer, days, str(report_save_path)):
                    result['report_path'] = str(report_save_path)
        
        result['success'] = True
        logger.info(f"每小時分析完成: {analysis_type}")
        
        # 添加數據摘要
        df = analyzer.get_hourly_summary(days)
        if df is not None and not df.empty:
            result['summary'] = {
                'total_clicks': int(df['total_clicks'].sum()),
                'total_impressions': int(df['total_impressions'].sum()),
                'unique_queries': int(df['unique_queries'].sum()),
                'peak_hour': int(df.loc[df['total_clicks'].idxmax()]['hour']),
                'low_hour': int(df.loc[df['total_clicks'].idxmin()]['hour'])
            }
        
        return result
        
    except Exception as e:
        error_msg = f"每小時分析時發生錯誤: {e}"
        logger.error(error_msg)
        result['errors'].append(error_msg)
        return result


def run_hourly_analysis_gemini(site_url: Optional[str] = None, days: int = 30):
    print(f"Running hourly analysis for site: {site_url or 'All Sites'} for the last {days} days...")
    from services.database import Database
    conn = Database().get_connection()
    try:
        hourly_data = _fetch_hourly_data_gemini(conn, days, site_url)
        if hourly_data.empty:
            print("⚠️ No hourly data found for the specified period.")
            return
        assets_dir = Path("assets")
        timestamp = datetime.now().strftime("%Y_%B")
        site_name = Path(site_url).stem if site_url else "Overall"
        filename_prefix = f"{timestamp}_{site_name}"
        plot_path = _generate_hourly_plot_gemini(hourly_data, assets_dir, filename_prefix)
        print(f"✅ Hourly trends plot saved to: {plot_path}")
        peak_hour_data = hourly_data.loc[hourly_data['total_clicks'].idxmax()]
        print(f"📈 Peak Performance Hour: {int(peak_hour_data['hour']):02d}:00 UTC with {int(peak_hour_data['total_clicks']):,} clicks.")
    except Exception as e:
        print(f"❌ An error occurred during hourly analysis: {e}")
    finally:
        if conn:
            conn.close()


def main():
    """主函數 - 用於直接運行腳本"""
    parser = argparse.ArgumentParser(description='GSC 每小時數據分析工具')
    parser.add_argument(
        '--type',
        choices=[
            'trends',
            'heatmap',
            'peaks',
            'report',
            'all'],
        default='trends',
        help='分析類型')
    parser.add_argument('--days', type=int, default=7, help='分析天數')
    parser.add_argument('--output', help='報告輸出路徑')
    parser.add_argument('--no-plots', action='store_true', help='不生成圖表')
    parser.add_argument('--plot-dir', default='assets', help='圖表保存目錄')
    parser.add_argument('--db', default='gsc_data.db', help='數據庫文件路徑')
    
    args = parser.parse_args()
    
    # 調用主函數
    result = run_hourly_analysis(
        analysis_type=args.type,
        days=args.days,
        output_path=args.output,
        include_plots=not args.no_plots,
        plot_save_dir=args.plot_dir,
        db_path=args.db
    )
    
    if result['success']:
        print(f"✅ 每小時分析成功: {result['analysis_type']}")
        if result['plots_generated']:
            print(f"📊 生成的圖表: {', '.join(result['plots_generated'])}")
        if result['report_path']:
            print(f"📄 報告路徑: {result['report_path']}")
        if 'summary' in result:
            summary = result['summary']
            print(f"📈 數據摘要: {summary['total_clicks']:,} 點擊, {summary['total_impressions']:,} 曝光")
            print(f"⏰ 高峰時段: {summary['peak_hour']}:00, 低谷時段: {summary['low_hour']}:00")
    else:
        print("❌ 每小時分析失敗")
        for error in result['errors']:
            print(f"  - {error}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
