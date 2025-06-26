#!/usr/bin/env python3
"""
GSC 每小時數據分析工具
專門用於分析 Google Search Console 的每小時數據
"""

import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import datetime, timedelta
import argparse
import sys

# 設置現代化視覺風格
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#f8f9fa'

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
    
    def __init__(self, db_path="gsc_data.db"):
        self.db_path = db_path
        
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
            start_date = latest_date - timedelta(days=days-1)
            
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
            
            df = pd.read_sql_query(query, conn, params=(start_date, latest_date))
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"獲取每小時摘要錯誤: {e}")
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
            start_date = latest_date - timedelta(days=days-1)
            
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
            
            df = pd.read_sql_query(query, conn, params=(start_date, latest_date))
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"獲取熱力圖數據錯誤: {e}")
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
            print("無法獲取每小時數據")
            return
            
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 2, height_ratios=[2, 2, 1], hspace=0.3, wspace=0.3)
        
        # 主要趨勢圖
        ax1 = fig.add_subplot(gs[0, :])
        
        # 雙軸：點擊量和曝光量
        ax1_twin = ax1.twinx()
        
        # 點擊量線條
        line1 = ax1.plot(df['hour'], df['total_clicks'], 
                        color=HOURLY_COLORS['primary'], linewidth=4,
                        marker='o', markersize=8, markerfacecolor='white',
                        markeredgewidth=3, markeredgecolor=HOURLY_COLORS['primary'],
                        label='點擊量')
        
        # 曝光量區域圖
        ax1_twin.fill_between(df['hour'], df['total_impressions'], 
                             color=HOURLY_COLORS['secondary'], alpha=0.3)
        line2 = ax1_twin.plot(df['hour'], df['total_impressions'], 
                             color=HOURLY_COLORS['secondary'], linewidth=2, 
                             linestyle='--', label='曝光量')
        
        # 美化主圖
        ax1.set_title(f'24小時搜索表現趨勢 (近{days}天)', 
                     fontsize=18, fontweight='bold', pad=20)
        ax1.set_xlabel('小時', fontsize=12, fontweight='bold')
        ax1.set_ylabel('點擊量', fontsize=12, color=HOURLY_COLORS['primary'], fontweight='bold')
        ax1_twin.set_ylabel('曝光量', fontsize=12, color=HOURLY_COLORS['secondary'], fontweight='bold')
        
        # 設置 X 軸
        ax1.set_xticks(range(0, 24, 2))
        ax1.set_xlim(-0.5, 23.5)
        
        # 添加時段背景色
        ax1.axvspan(0, 5.5, alpha=0.1, color=HOURLY_COLORS['night'], label='深夜')
        ax1.axvspan(6, 11.5, alpha=0.1, color=HOURLY_COLORS['morning'], label='早晨')
        ax1.axvspan(12, 17.5, alpha=0.1, color=HOURLY_COLORS['noon'], label='中午') 
        ax1.axvspan(18, 23.5, alpha=0.1, color=HOURLY_COLORS['evening'], label='晚上')
        
        # 圖例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # 左下：排名趨勢
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.plot(df['hour'], df['avg_position'], 
                color=HOURLY_COLORS['accent'], linewidth=3, 
                marker='v', markersize=6)
        ax2.fill_between(df['hour'], df['avg_position'], 
                        color=HOURLY_COLORS['accent'], alpha=0.3)
        ax2.set_title('每小時平均排名', fontsize=14, fontweight='bold')
        ax2.set_xlabel('小時', fontsize=11)
        ax2.set_ylabel('平均排名', fontsize=11)
        ax2.set_xticks(range(0, 24, 4))
        ax2.invert_yaxis()  # 排名越小越好
        
        # 右下：關鍵字活躍度
        ax3 = fig.add_subplot(gs[1, 1])
        bars = ax3.bar(df['hour'], df['unique_queries'], 
                      color=[HOURLY_COLORS['night'] if h < 6 else
                            HOURLY_COLORS['morning'] if h < 12 else
                            HOURLY_COLORS['noon'] if h < 18 else
                            HOURLY_COLORS['evening'] for h in df['hour']],
                      alpha=0.8, edgecolor='white', linewidth=1)
        
        ax3.set_title('每小時活躍關鍵字數', fontsize=14, fontweight='bold')
        ax3.set_xlabel('小時', fontsize=11)
        ax3.set_ylabel('獨特關鍵字數', fontsize=11)
        ax3.set_xticks(range(0, 24, 4))
        
        # 底部：統計摘要
        ax4 = fig.add_subplot(gs[2, :])
        ax4.axis('off')
        
        total_clicks = df['total_clicks'].sum()
        total_impressions = df['total_impressions'].sum()
        peak_hour = df.loc[df['total_clicks'].idxmax(), 'hour']
        avg_queries = df['unique_queries'].mean()
        
        stats_text = f"""
        📊 {days}天每小時統計     🎯 總點擊: {total_clicks:,}     👀 總曝光: {total_impressions:,}     
        ⏰ 高峰時段: {peak_hour}點     🔤 平均關鍵字: {avg_queries:.0f}個/小時
        """
        
        ax4.text(0.5, 0.5, stats_text, transform=ax4.transAxes, 
                fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.5", facecolor='#f8f9fa', 
                         edgecolor=HOURLY_COLORS['primary'], linewidth=2),
                fontweight='bold')
        
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
            print(f"📈 每小時趨勢圖已保存到: {save_path}")
        else:
            plt.show()
    
    def plot_heatmap(self, days=7, save_path=None):
        """繪製每日每小時熱力圖"""
        df = self.get_daily_hourly_heatmap(days)
        if df is None or df.empty:
            print("無法獲取熱力圖數據")
            return
            
        # 創建透視表
        pivot_clicks = df.pivot(index='date', columns='hour', values='clicks').fillna(0)
        pivot_impressions = df.pivot(index='date', columns='hour', values='impressions').fillna(0)
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
        
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
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            print(f"🔥 熱力圖已保存到: {save_path}")
        else:
            plt.show()
    
    def plot_peak_analysis(self, days=7, save_path=None):
        """繪製高峰時段分析"""
        hourly_df, period_df = self.get_peak_hours_analysis(days)
        if hourly_df is None or period_df is None:
            print("無法獲取高峰分析數據")
            return
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
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
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            print(f"⏰ 高峰分析圖已保存到: {save_path}")
        else:
            plt.show()
    
    def generate_hourly_report(self, days=7):
        """生成每小時數據報告"""
        print("=" * 60)
        print("🕐 每小時數據分析報告")
        print("=" * 60)
        
        # 基本統計
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM hourly_rankings")
        total_records = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT date) FROM hourly_rankings")
        total_days = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT query) FROM hourly_rankings")
        unique_queries = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT MIN(date), MAX(date) FROM hourly_rankings")
        date_range = cursor.fetchone()
        
        print(f"總記錄數: {total_records:,}")
        print(f"覆蓋天數: {total_days}")
        print(f"獨特關鍵字: {unique_queries:,}")
        print(f"日期範圍: {date_range[0]} 至 {date_range[1]}")
        
        # 每小時摘要
        df = self.get_hourly_summary(days)
        if df is not None:
            print(f"\n近 {days} 天每小時表現:")
            print("-" * 40)
            peak_hour = df.loc[df['total_clicks'].idxmax()]
            low_hour = df.loc[df['total_clicks'].idxmin()]
            
            print(f"🏆 高峰時段: {peak_hour['hour']}點 ({peak_hour['total_clicks']}次點擊)")
            print(f"🌙 低谷時段: {low_hour['hour']}點 ({low_hour['total_clicks']}次點擊)")
            print(f"📈 點擊總量: {df['total_clicks'].sum():,}")
            print(f"👀 曝光總量: {df['total_impressions'].sum():,}")
            print(f"🔤 關鍵字總數: {df['unique_queries'].sum():,}")
        
        conn.close()
        print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='GSC 每小時數據分析工具')
    parser.add_argument('--type', choices=['trends', 'heatmap', 'peaks', 'report'], 
                       default='trends', help='分析類型')
    parser.add_argument('--days', type=int, default=7, help='分析天數')
    parser.add_argument('--save', help='保存圖表路徑')
    
    args = parser.parse_args()
    
    analyzer = HourlyAnalyzer()
    
    if args.type == 'trends':
        analyzer.plot_hourly_trends(args.days, args.save)
    elif args.type == 'heatmap':
        analyzer.plot_heatmap(args.days, args.save)
    elif args.type == 'peaks':
        analyzer.plot_peak_analysis(args.days, args.save)
    elif args.type == 'report':
        analyzer.generate_hourly_report(args.days)

if __name__ == "__main__":
    main() 