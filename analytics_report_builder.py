#!/usr/bin/env python3
"""
GSC Data Visualization Tool
專門用於 Google Search Console 數據的可視化分析
"""

import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import argparse
import sys
from datetime import datetime, timedelta
import seaborn as sns
import numpy as np

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
    
    def __init__(self, db_path="gsc_data.db"):
        self.db_path = db_path
        
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
            start_date = latest_date - timedelta(days=days-1)
            
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
            
            df = pd.read_sql_query(query, conn, params=(start_date, latest_date))
            conn.close()
            
            # 轉換日期格式
            df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except Exception as e:
            print(f"獲取數據錯誤: {e}")
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
            start_date = latest_date - timedelta(days=days-1)
            
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
            
            df = pd.read_sql_query(query, conn, params=(start_date, latest_date, limit))
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"獲取關鍵字數據錯誤: {e}")
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
            start_date = latest_date - timedelta(days=days-1)
            
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
            
            df = pd.read_sql_query(query, conn, params=(start_date, latest_date, limit))
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
                except:
                    # 如果解碼失敗，使用原始方法
                    short = url.split('/')[-1] if '/' in url else url
                    return (short[:32] + '...') if len(short) > 35 else short
            
            df['page_short'] = df['page'].apply(clean_page_url)
            
            return df
            
        except Exception as e:
            print(f"獲取頁面數據錯誤: {e}")
            return None
    
    def plot_daily_trends(self, days=30, save_path=None):
        """繪製每日趨勢圖 - Uber/Duolingo 風格"""
        df = self.get_daily_stats(days)
        if df is None or df.empty:
            print("無法獲取數據")
            return
        
        # 創建現代化的圖表佈局
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 2, height_ratios=[2, 2, 1], hspace=0.3, wspace=0.2)
        
        # 主要趨勢圖（佔用上半部分）
        ax_main = fig.add_subplot(gs[0, :])
        
        # 雙軸設計：點擊量和曝光量
        ax_main2 = ax_main.twinx()
        
        # 點擊量線條（左軸）
        line1 = ax_main.plot(df['date'], df['total_clicks'], 
                            color=DUOLINGO_COLORS['green'], linewidth=3, 
                            marker='o', markersize=6, markerfacecolor='white',
                            markeredgewidth=2, markeredgecolor=DUOLINGO_COLORS['green'],
                            label='點擊量', zorder=3)
        
        # 曝光量區域圖（右軸）
        ax_main2.fill_between(df['date'], df['total_impressions'], 
                             color=DUOLINGO_COLORS['blue'], alpha=0.3, label='曝光量')
        line2 = ax_main2.plot(df['date'], df['total_impressions'], 
                             color=DUOLINGO_COLORS['blue'], linewidth=2, 
                             linestyle='--', label='曝光量')
        
        # 美化主圖
        ax_main.set_title('🚀 GSC 搜索表現總覽', fontsize=20, fontweight='bold', 
                         color=UBER_COLORS['dark'], pad=20)
        ax_main.set_ylabel('點擊量', fontsize=12, color=DUOLINGO_COLORS['green'], fontweight='bold')
        ax_main2.set_ylabel('曝光量', fontsize=12, color=DUOLINGO_COLORS['blue'], fontweight='bold')
        
        # 設置軸顏色
        ax_main.tick_params(axis='y', labelcolor=DUOLINGO_COLORS['green'])
        ax_main2.tick_params(axis='y', labelcolor=DUOLINGO_COLORS['blue'])
        ax_main.tick_params(axis='x', rotation=45)
        
        # 添加圖例
        lines1, labels1 = ax_main.get_legend_handles_labels()
        lines2, labels2 = ax_main2.get_legend_handles_labels()
        ax_main.legend(lines1 + lines2, labels1 + labels2, 
                      loc='upper left', frameon=False, fontsize=10)
        
        # 左下：排名趨勢
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.fill_between(df['date'], df['avg_position'], 
                        color=DUOLINGO_COLORS['orange'], alpha=0.6)
        ax2.plot(df['date'], df['avg_position'], 
                color=DUOLINGO_COLORS['orange'], linewidth=3, marker='v', markersize=5)
        ax2.set_title('📈 平均排名趨勢', fontsize=14, fontweight='bold', color=UBER_COLORS['dark'])
        ax2.set_ylabel('排名位置', fontsize=10, fontweight='bold')
        ax2.invert_yaxis()  # 排名越小越好
        ax2.tick_params(axis='x', rotation=45)
        
        # 右下：關鍵字數量
        ax3 = fig.add_subplot(gs[1, 1])
        bars = ax3.bar(df['date'], df['keyword_count'], 
                      color=DUOLINGO_COLORS['purple'], alpha=0.8, 
                      edgecolor='white', linewidth=1)
        
        # 添加數值標籤
        for bar in bars:
            height = bar.get_height()
            ax3.annotate(f'{int(height):,}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax3.set_title('🔍 每日關鍵字數量', fontsize=14, fontweight='bold', color=UBER_COLORS['dark'])
        ax3.set_ylabel('關鍵字數量', fontsize=10, fontweight='bold')
        ax3.tick_params(axis='x', rotation=45)
        
        # 底部：數據摘要卡片
        ax4 = fig.add_subplot(gs[2, :])
        ax4.axis('off')
        
        # 計算統計數據
        total_clicks = df['total_clicks'].sum()
        total_impressions = df['total_impressions'].sum()
        avg_position = df['avg_position'].mean()
        total_keywords = df['keyword_count'].sum()
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # 創建統計卡片
        stats_text = f"""
        📊 數據總覽 ({days} 天)     🎯 總點擊量: {total_clicks:,}     👀 總曝光量: {total_impressions:,}     
        📍 平均排名: {avg_position:.1f}     🔤 總關鍵字: {total_keywords:,}     💡 平均CTR: {avg_ctr:.2f}%
        """
        
        ax4.text(0.5, 0.5, stats_text, transform=ax4.transAxes, 
                fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.5", facecolor=UBER_COLORS['light'], 
                         edgecolor=UBER_COLORS['secondary'], linewidth=2),
                fontweight='bold', color=UBER_COLORS['dark'])
        
        # 設置整體背景
        fig.patch.set_facecolor('white')
        
        if save_path:
            # 確保 assets 目錄存在
            import os
            if '/' in save_path and not save_path.startswith('assets/'):
                save_path = f"assets/{save_path}"
            elif '/' not in save_path:
                save_path = f"assets/{save_path}"
            
            os.makedirs('assets', exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"🎨 精美圖表已保存到: {save_path}")
        else:
            plt.show()
    
    def plot_top_keywords(self, limit=20, days=7, save_path=None):
        """繪製熱門關鍵字圖表 - 現代化設計"""
        df = self.get_top_keywords(limit, days)
        if df is None or df.empty:
            print("無法獲取關鍵字數據")
            return
        
        # 創建現代化佈局
        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(2, 3, height_ratios=[3, 2], width_ratios=[2, 2, 1], 
                             hspace=0.3, wspace=0.3)
        
        # 左上：點擊量排行榜（水平條形圖）
        ax1 = fig.add_subplot(gs[0, 0])
        top_clicks = df.head(12)
        
        # 創建漸變色彩
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(top_clicks)))
        bars1 = ax1.barh(range(len(top_clicks)), top_clicks['total_clicks'], 
                        color=colors, edgecolor='white', linewidth=1.5)
        
        # 美化 Y 軸標籤
        ax1.set_yticks(range(len(top_clicks)))
        ax1.set_yticklabels([k[:25] + '...' if len(k) > 25 else k for k in top_clicks['keyword']], 
                           fontsize=9, fontweight='bold')
        ax1.set_title('TOP 關鍵字點擊量', fontsize=16, fontweight='bold', 
                     color=UBER_COLORS['dark'], pad=15)
        ax1.set_xlabel('點擊量', fontsize=11, fontweight='bold')
        
        # 添加數值標籤
        for i, (bar, value) in enumerate(zip(bars1, top_clicks['total_clicks'])):
            ax1.text(bar.get_width() + max(top_clicks['total_clicks']) * 0.01, 
                    bar.get_y() + bar.get_height()/2, 
                    f'{int(value)}', va='center', fontweight='bold', fontsize=9)
        
        # 右上：曝光量排行榜
        ax2 = fig.add_subplot(gs[0, 1])
        top_impressions = df.nlargest(12, 'total_impressions')
        
        colors2 = plt.cm.plasma(np.linspace(0.2, 0.8, len(top_impressions)))
        bars2 = ax2.barh(range(len(top_impressions)), top_impressions['total_impressions'], 
                        color=colors2, edgecolor='white', linewidth=1.5)
        
        ax2.set_yticks(range(len(top_impressions)))
        ax2.set_yticklabels([k[:25] + '...' if len(k) > 25 else k for k in top_impressions['keyword']], 
                           fontsize=9, fontweight='bold')
        ax2.set_title('TOP 關鍵字曝光量', fontsize=16, fontweight='bold', 
                     color=UBER_COLORS['dark'], pad=15)
        ax2.set_xlabel('曝光量', fontsize=11, fontweight='bold')
        
        for i, (bar, value) in enumerate(zip(bars2, top_impressions['total_impressions'])):
            ax2.text(bar.get_width() + max(top_impressions['total_impressions']) * 0.01, 
                    bar.get_y() + bar.get_height()/2, 
                    f'{int(value):,}', va='center', fontweight='bold', fontsize=9)
        
        # 右側：統計卡片
        ax_stats = fig.add_subplot(gs[0, 2])
        ax_stats.axis('off')
        
        # 計算統計
        total_keywords = len(df)
        avg_clicks = df['total_clicks'].mean()
        avg_impressions = df['total_impressions'].mean()
        avg_ctr = df['avg_ctr'].mean() * 100
        avg_position = df['avg_position'].mean()
        
        stats_text = f"""
        總關鍵字數
        {total_keywords:,}
        
        平均點擊量
        {avg_clicks:.0f}
        
        平均曝光量
        {avg_impressions:,.0f}
        
        平均CTR
        {avg_ctr:.2f}%
        
        平均排名
        {avg_position:.1f}
        """
        
        ax_stats.text(0.1, 0.5, stats_text, transform=ax_stats.transAxes, 
                     fontsize=12, va='center', fontweight='bold',
                     bbox=dict(boxstyle="round,pad=0.5", facecolor=DUOLINGO_COLORS['blue'], 
                              alpha=0.1, edgecolor=DUOLINGO_COLORS['blue'], linewidth=2),
                     color=UBER_COLORS['dark'])
        
        # 左下：排名 vs CTR 散點圖
        ax3 = fig.add_subplot(gs[1, 0])
        
        # 創建氣泡圖
        scatter = ax3.scatter(df['avg_position'], df['avg_ctr']*100, 
                            s=df['total_clicks']*3, 
                            c=df['total_impressions'], 
                            cmap='viridis', alpha=0.7, 
                            edgecolors='white', linewidth=1)
        
        ax3.set_xlabel('平均排名位置', fontsize=11, fontweight='bold')
        ax3.set_ylabel('點擊率 CTR (%)', fontsize=11, fontweight='bold')
        ax3.set_title('關鍵字表現分析\n(氣泡大小=點擊量, 顏色=曝光量)', 
                     fontsize=14, fontweight='bold', color=UBER_COLORS['dark'])
        
        # 添加顏色條
        cbar = plt.colorbar(scatter, ax=ax3, shrink=0.8)
        cbar.set_label('曝光量', fontweight='bold')
        
        # 右下：排名分布直方圖
        ax4 = fig.add_subplot(gs[1, 1])
        
        n, bins, patches = ax4.hist(df['avg_position'], bins=15, 
                                   color=DUOLINGO_COLORS['green'], alpha=0.7, 
                                   edgecolor='white', linewidth=1.5)
        
        # 為不同排名範圍著色
        for i, patch in enumerate(patches):
            if bins[i] <= 3:  # 前3位 - 綠色
                patch.set_facecolor(DUOLINGO_COLORS['green'])
            elif bins[i] <= 10:  # 4-10位 - 黃色
                patch.set_facecolor(DUOLINGO_COLORS['yellow'])
            else:  # 10位以後 - 紅色
                patch.set_facecolor(DUOLINGO_COLORS['red'])
        
        ax4.set_xlabel('搜索排名位置', fontsize=11, fontweight='bold')
        ax4.set_ylabel('關鍵字數量', fontsize=11, fontweight='bold')
        ax4.set_title('排名分布圖', fontsize=14, fontweight='bold', color=UBER_COLORS['dark'])
        
        # 添加排名區間說明
        ax4.axvline(x=3, color='red', linestyle='--', alpha=0.7, label='首頁界線')
        ax4.axvline(x=10, color='orange', linestyle='--', alpha=0.7, label='第一頁界線')
        ax4.legend(fontsize=9)
        
        # 設置整體標題
        fig.suptitle(f'關鍵字表現分析報告 (近 {days} 天)', 
                    fontsize=20, fontweight='bold', y=0.98, color=UBER_COLORS['dark'])
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"精美關鍵字圖表已保存到: {save_path}")
        else:
            plt.show()
    
    def plot_page_performance(self, limit=15, days=7, save_path=None):
        """繪製頁面表現圖表"""
        df = self.get_page_performance(limit, days)
        if df is None or df.empty:
            print("無法獲取頁面數據")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 頁面點擊量排行
        y_pos = range(len(df))
        ax1.barh(y_pos, df['total_clicks'], color='#9467bd', alpha=0.8)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(df['page_short'], fontsize=8, ha='right')
        ax1.set_title(f'近 {days} 天熱門頁面 (按點擊量)', fontsize=14, fontweight='bold')
        ax1.set_xlabel('點擊量')
        # 調整左邊距以適應較長的標籤
        ax1.tick_params(axis='y', pad=5)
        
        # 頁面曝光量排行
        df_impressions = df.nlargest(12, 'total_impressions')
        y_pos = range(len(df_impressions))
        ax2.barh(y_pos, df_impressions['total_impressions'], color='#8c564b', alpha=0.8)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(df_impressions['page_short'], fontsize=8, ha='right')
        ax2.set_title(f'近 {days} 天曝光量最高頁面', fontsize=14, fontweight='bold')
        ax2.set_xlabel('曝光量')
        ax2.tick_params(axis='y', pad=5)
        
        # 頁面 CTR vs 排名
        ax3.scatter(df['avg_position'], df['avg_ctr'], alpha=0.6, s=df['total_clicks']*3, color='#17becf')
        ax3.set_xlabel('平均排名')
        ax3.set_ylabel('平均 CTR')
        ax3.set_title('頁面排名 vs CTR (氣泡大小=點擊量)', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # 頁面排名分布
        ax4.hist(df['avg_position'], bins=15, color='#bcbd22', alpha=0.7, edgecolor='black')
        ax4.set_xlabel('平均排名')
        ax4.set_ylabel('頁面數量')
        ax4.set_title('頁面排名分布', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"圖表已保存到: {save_path}")
        else:
            plt.show()
    
    def data_summary(self):
        """顯示數據摘要"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 基本統計
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM daily_rankings")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT query) FROM daily_rankings")
            unique_keywords = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT page) FROM page_data")
            unique_pages = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(date), MAX(date) FROM daily_rankings")
            date_range = cursor.fetchone()
            
            cursor.execute("SELECT SUM(clicks), SUM(impressions) FROM daily_rankings")
            totals = cursor.fetchone()
            
            conn.close()
            
            print("=" * 50)
            print("GSC 數據摘要")
            print("=" * 50)
            print(f"總記錄數: {total_records:,}")
            print(f"獨特關鍵字: {unique_keywords:,}")
            print(f"獨特頁面: {unique_pages:,}")
            print(f"數據範圍: {date_range[0]} 到 {date_range[1]}")
            print(f"總點擊量: {totals[0]:,}")
            print(f"總曝光量: {totals[1]:,}")
            print("=" * 50)
            
        except Exception as e:
            print(f"獲取數據摘要錯誤: {e}")

def main():
    parser = argparse.ArgumentParser(description='GSC Data Visualization Tool')
    parser.add_argument('--type', choices=['daily', 'keywords', 'pages', 'summary'], 
                       default='daily', help='圖表類型')
    parser.add_argument('--days', type=int, default=30, help='天數範圍')
    parser.add_argument('--limit', type=int, default=20, help='顯示數量限制')
    parser.add_argument('--save', type=str, help='保存圖片路徑')
    parser.add_argument('--db', type=str, default='gsc_data.db', help='數據庫路徑')
    
    args = parser.parse_args()
    
    visualizer = GSCVisualizer(args.db)
    
    if args.type == 'summary':
        visualizer.data_summary()
    elif args.type == 'daily':
        visualizer.plot_daily_trends(args.days, args.save)
    elif args.type == 'keywords':
        visualizer.plot_top_keywords(args.limit, args.days, args.save)
    elif args.type == 'pages':
        visualizer.plot_page_performance(args.limit, args.days, args.save)

if __name__ == "__main__":
    main() 