#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""交互式數據可視化工具，已重構為使用 AnalysisService"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from typing import List, Dict, Any, Optional
import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ..services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

class InteractiveVisualizer:
    """交互式數據趨勢可視化工具"""

    def __init__(self, analysis_service: AnalysisService):
        """初始化可視化工具"""
        self.analysis_service = analysis_service
        self.db = analysis_service.db  # 仍然需要 db 來獲取站點和關鍵字列表
        self.console = Console()

    def get_sites(self) -> List[Dict[str, Any]]:
        """獲取所有站點"""
        return self.db.get_sites()

    def get_keywords_for_site(self, site_id: int) -> List[Dict[str, Any]]:
        """獲取指定站點的關鍵字列表"""
        return self.db.get_keywords(site_id=site_id)

    def get_pages_for_site(self, site_id: int) -> List[str]:
        """獲取指定站點的頁面列表"""
        return self.db.get_distinct_pages_for_site(site_id=site_id)

    def get_performance_data(
        self, site_id: int, start_date: str, end_date: str,
        group_by: str, filter_term: str
    ) -> pd.DataFrame:
        """從 AnalysisService 獲取性能數據"""
        try:
            data = self.analysis_service.get_performance_data_for_visualization(
                site_id=site_id,
                start_date=start_date,
                end_date=end_date,
                group_by=group_by,
                filter_term=filter_term
            )
            return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"獲取性能數據時出錯: {e}", exc_info=True)
            return pd.DataFrame()

    def _select_site_interactive(self, console: Console) -> Optional[int]:
        """交互式選擇站點"""
        sites = self.get_sites()
        if not sites:
            console.print("[red]數據庫中沒有站點。[/red]")
            return None

        table = Table(title="站點列表")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("名稱", style="green")

        for site in sites:
            table.add_row(str(site['id']), site['name'])

        console.print(table)

        site_id_str = Prompt.ask(
            "請輸入要進行可視化分析的網站 ID",
            choices=[str(s['id']) for s in sites],
            show_choices=True
        )
        return int(site_id_str)

    def run(self, site_id: Optional[int] = None, days: int = 30):
        console = Console()
        if site_id is None:
            site_id = self._select_site_interactive(console)
            if site_id is None:
                return

        console.print(f"🔄 正在為站點 ID: {site_id} 生成交互式儀表板...", style="bold cyan")
        
        while True:
            group_by = Prompt.ask("您想分析 '關鍵字 (query)' 還是 '頁面 (page)'?", choices=['query', 'page'])
            
            end_date = datetime.date.today()
            start_date = end_date - datetime.timedelta(days=days - 1)

            all_data = self.analysis_service.get_performance_data_for_visualization(
                site_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), group_by
            )

            if not all_data:
                console.print(f"[yellow]在最近 {days} 天內找不到任何數據。[/yellow]")
                if not Prompt.ask("是否嘗試其他分析?", choices=["y", "n"], default="y") == "y":
                    break
                continue

            df = pd.DataFrame(all_data)
            available_items = df[group_by].unique().tolist()
            if not available_items:
                console.print(f"[yellow]在數據中找不到任何可用的 {group_by}。[/yellow]")
                if not Prompt.ask("是否嘗試其他分析?", choices=["y", "n"], default="y") == "y":
                    break
                continue
            
            filter_term = Prompt.ask(f"請選擇要查詢的 {group_by}", choices=available_items)
            filtered_df = df[df[group_by] == filter_term]

            if filtered_df.empty:
                console.print(f"[yellow]找不到關於 '{filter_term}' 的數據。[/yellow]")
            else:
                title = f"站點 {site_id} - {group_by.capitalize()}: {filter_term} ({days} 天趨勢)"
                fig = self.plot_trends(filtered_df, title)
                fig.show()

            if not Prompt.ask("是否繼續分析?", choices=["y", "n"], default="n") == "y":
                break

    def plot_trends(self, df: pd.DataFrame, title: str) -> go.Figure:
        """繪製趨勢圖"""
        import plotly.graph_objects as go
        if df.empty:
            logger.warning("數據為空，無法繪製圖表。")
            return go.Figure()

        df['date'] = pd.to_datetime(df['date'])
        fig = make_subplots(rows=2, cols=2, subplot_titles=('排名趨勢', '點擊趨勢', '曝光趨勢', '點擊率(CTR)趨勢'),
                              vertical_spacing=0.3, horizontal_spacing=0.1)

        fig.add_trace(go.Scatter(x=df['date'], y=df['position'].astype(float).round(2), name='排名', yaxis='y1'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['clicks'].astype(int), name='點擊', yaxis='y2'), row=1, col=2)
        fig.add_trace(go.Scatter(x=df['date'], y=df['impressions'].astype(int), name='曝光', yaxis='y3'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['ctr'].astype(float).round(4), name='CTR', yaxis='y4'), row=2, col=2)

        fig.update_layout(
            title_text=title,
            height=800,
            xaxis_title='日期',
            yaxis=dict(title='排名', autorange='reversed'),
            yaxis2=dict(title='點擊數'),
            yaxis3=dict(title='曝光數'),
            yaxis4=dict(title='CTR', tickformat='.2%'),
            showlegend=False,
            template='plotly_white'
        )
        return fig
