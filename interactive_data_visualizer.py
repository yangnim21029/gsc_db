#!/usr/bin/env python3
"""
GSC 互動式數據可視化工具
專門用於生成互動式圖表和分析儀表板
"""

import sqlite3
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import argparse
import urllib.parse


class InteractiveBubbleChart:
    def __init__(self, db_path="gsc_data.db"):
        self.db_path = db_path

    def get_keyword_bubble_data(self, days=30, limit=50):
        """獲取關鍵字氣泡圖數據"""
        try:
            conn = sqlite3.connect(self.db_path)

            # 獲取最新日期
            cursor = conn.execute("SELECT MAX(date) FROM daily_rankings")
            latest_date_str = cursor.fetchone()[0]
            if not latest_date_str:
                conn.close()
                return None

            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=days - 1)

            query = """
            SELECT
                dr.query,
                SUM(dr.clicks) as total_clicks,
                SUM(dr.impressions) as total_impressions,
                AVG(dr.position) as avg_position,
                AVG(dr.ctr) as avg_ctr,
                COUNT(DISTINCT dr.date) as active_days,
                s.name as site_name,
                s.id as site_id
            FROM daily_rankings dr
            JOIN sites s ON dr.site_id = s.id
            WHERE dr.date >= ? AND dr.date <= ?
            GROUP BY dr.query, s.id, s.name
            HAVING total_clicks > 0
            ORDER BY total_clicks DESC
            LIMIT ?
            """

            df = pd.read_sql_query(
                query, conn, params=(
                    start_date, latest_date, limit))
            conn.close()

            # 清理關鍵字名稱
            df['query_clean'] = df['query'].apply(
                lambda x: x[:50] + '...' if len(x) > 50 else x)

            # 計算額外指標
            df['ctr_percent'] = df['avg_ctr'] * 100
            df['efficiency'] = df['total_clicks'] / df['avg_position']  # 點擊效率

            return df

        except Exception as e:
            print(f"獲取數據錯誤: {e}")
            return None

    def get_page_bubble_data(self, days=30, limit=30):
        """獲取頁面氣泡圖數據"""
        try:
            conn = sqlite3.connect(self.db_path)

            # 獲取最新日期
            cursor = conn.execute("SELECT MAX(date) FROM page_data")
            latest_date_str = cursor.fetchone()[0]
            if not latest_date_str:
                conn.close()
                return None

            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
            start_date = latest_date - timedelta(days=days - 1)

            query = """
            SELECT
                pd.page,
                SUM(pd.clicks) as total_clicks,
                SUM(pd.impressions) as total_impressions,
                AVG(pd.position) as avg_position,
                AVG(pd.ctr) as avg_ctr,
                s.name as site_name,
                s.id as site_id
            FROM page_data pd
            JOIN sites s ON pd.site_id = s.id
            WHERE pd.date >= ? AND pd.date <= ?
            GROUP BY pd.page, s.id, s.name
            HAVING total_clicks > 0
            ORDER BY total_clicks DESC
            LIMIT ?
            """

            df = pd.read_sql_query(
                query, conn, params=(
                    start_date, latest_date, limit))
            conn.close()

            # 清理頁面URL
            def clean_page_url(url):
                try:
                    # URL decode 處理中文
                    decoded_url = urllib.parse.unquote(url, encoding='utf-8')

                    # 提取有意義的部分
                    if '/' in decoded_url:
                        last_part = decoded_url.split('/')[-1]
                        if not last_part and len(decoded_url.split('/')) > 1:
                            last_part = decoded_url.split('/')[-2]
                    else:
                        last_part = decoded_url

                    # 移除查詢參數
                    if '?' in last_part:
                        last_part = last_part.split('?')[0]

                    # 限制長度
                    if len(last_part) > 40:
                        last_part = last_part[:37] + '...'

                    return last_part if last_part else '首頁'
                except BaseException:
                    short = url.split('/')[-1] if '/' in url else url
                    return (short[:37] + '...') if len(short) > 40 else short

            df['page_clean'] = df['page'].apply(clean_page_url)
            df['ctr_percent'] = df['avg_ctr'] * 100

            return df

        except Exception as e:
            print(f"獲取頁面數據錯誤: {e}")
            return None

    def create_keyword_bubble_chart(self, days=30, limit=50, save_path=None):
        """創建關鍵字互動氣泡圖"""
        df = self.get_keyword_bubble_data(days, limit)
        if df is None or df.empty:
            print("無法獲取關鍵字數據")
            return

        # 創建氣泡圖
        fig = px.scatter(
            df,
            x="avg_position",
            y="ctr_percent",
            size="total_clicks",
            color="total_impressions",
            hover_name="query_clean",
            hover_data={
                "total_clicks": True,
                "total_impressions": True,
                "avg_position": ":.1f",
                "ctr_percent": ":.2f",
                "site_name": True,
                "active_days": True},
            color_continuous_scale="Viridis",
            title=f"關鍵字表現氣泡圖 (近 {days} 天)<br><sub>X軸=排名位置, Y軸=CTR%, 氣泡大小=點擊量, 顏色=曝光量</sub>",
            labels={
                "avg_position": "平均排名位置",
                "ctr_percent": "點擊率 CTR (%)",
                "total_clicks": "總點擊量",
                "total_impressions": "總曝光量"})

        # 美化圖表
        fig.update_layout(
            width=1200,
            height=800,
            font=dict(size=12),
            title_font_size=18,
            coloraxis_colorbar=dict(
                title="總曝光量"
            ),
            xaxis=dict(
                title="平均排名位置 (越小越好)",
                autorange="reversed",  # 反轉 X 軸，排名小的在右邊
                gridcolor="lightgray",
                showgrid=True
            ),
            yaxis=dict(
                title="點擊率 CTR (%)",
                gridcolor="lightgray",
                showgrid=True
            ),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )

        # 添加四象限分隔線和象限標籤
        ctr_median = df['ctr_percent'].median()
        position_median = df['avg_position'].median()

        # CTR中位數線（水平線）- 更明顯的分隔線
        fig.add_hline(y=ctr_median, line_dash="solid",
                      line_color="red", line_width=3, opacity=0.9,
                      annotation_text=f"四象限分隔線 - CTR中位數: {ctr_median:.2f}%",
                      annotation_position="bottom right",
                      annotation_font_size=14, annotation_font_color="red")

        # 排名中位數線（垂直線）- 更明顯的分隔線
        fig.add_vline(x=position_median, line_dash="solid",
                      line_color="blue", line_width=3, opacity=0.9,
                      annotation_text=f"四象限分隔線 - 排名中位數: {position_median:.1f}",
                      annotation_position="top left",
                      annotation_font_size=14, annotation_font_color="blue")

        # 添加四象限背景色和標籤
        y_range = df['ctr_percent'].max() - df['ctr_percent'].min()
        x_range = df['avg_position'].max() - df['avg_position'].min()

        # 優秀表現象限 (左上角)
        fig.add_annotation(
            x=df['avg_position'].min() + x_range * 0.1,
            y=df['ctr_percent'].max() - y_range * 0.1,
            text="🏆 優秀表現<br>高CTR + 好排名",
            showarrow=False,
            font=dict(
                size=16,
                color="green",
                family="Arial Black"),
            bgcolor="rgba(76,175,80,0.1)",
            bordercolor="green",
            borderwidth=2,
            width=120,
            height=60)

        # 潛力關鍵字象限 (右上角)
        fig.add_annotation(
            x=df['avg_position'].max() - x_range * 0.15,
            y=df['ctr_percent'].max() - y_range * 0.1,
            text="⭐ 潛力關鍵字<br>高CTR + 低排名",
            showarrow=False,
            font=dict(
                size=16,
                color="orange",
                family="Arial Black"),
            bgcolor="rgba(255,152,0,0.1)",
            bordercolor="orange",
            borderwidth=2,
            width=120,
            height=60)

        # 需要優化象限 (左下角)
        fig.add_annotation(
            x=df['avg_position'].min() + x_range * 0.1,
            y=df['ctr_percent'].min() + y_range * 0.15,
            text="📈 需要優化<br>低CTR + 好排名",
            showarrow=False,
            font=dict(
                size=16,
                color="blue",
                family="Arial Black"),
            bgcolor="rgba(33,150,243,0.1)",
            bordercolor="blue",
            borderwidth=2,
            width=120,
            height=60)

        # 重點改善象限 (右下角)
        fig.add_annotation(
            x=df['avg_position'].max() -
            x_range *
            0.15,
            y=df['ctr_percent'].min() +
            y_range *
            0.15,
            text="🔧 重點改善<br>低CTR + 低排名",
            showarrow=False,
            font=dict(
                size=16,
                color="red",
                family="Arial Black"),
            bgcolor="rgba(244,67,54,0.1)",
            bordercolor="red",
            borderwidth=2,
            width=120,
            height=60)

        # 保存或顯示
        if save_path:
            # 生成四象限分析
            quadrant_analysis = self.generate_quadrant_analysis(df)

            # 將氣泡圖和四象限分析結合到一個 HTML 頁面
            self.save_bubble_with_analysis(
                fig, quadrant_analysis, save_path, "關鍵字")
            print(f"🎨 互動式關鍵字氣泡圖（含四象限分析）已保存到: {save_path}")
        else:
            fig.show()

    def create_page_bubble_chart(self, days=30, limit=30, save_path=None):
        """創建頁面互動氣泡圖"""
        df = self.get_page_bubble_data(days, limit)
        if df is None or df.empty:
            print("無法獲取頁面數據")
            return

        # 創建氣泡圖
        fig = px.scatter(
            df,
            x="avg_position",
            y="ctr_percent",
            size="total_clicks",
            color="total_impressions",
            hover_name="page_clean",
            hover_data={
                "total_clicks": True,
                "total_impressions": True,
                "avg_position": ":.1f",
                "ctr_percent": ":.2f",
                "site_name": True,
                "page": True},
            color_continuous_scale="Plasma",
            title=f"頁面表現氣泡圖 (近 {days} 天)<br><sub>X軸=排名位置, Y軸=CTR%, 氣泡大小=點擊量, 顏色=曝光量</sub>",
            labels={
                "avg_position": "平均排名位置",
                "ctr_percent": "點擊率 CTR (%)",
                "total_clicks": "總點擊量",
                "total_impressions": "總曝光量"})

        # 美化圖表
        fig.update_layout(
            width=1200,
            height=800,
            font=dict(size=12),
            title_font_size=18,
            coloraxis_colorbar=dict(
                title="總曝光量"
            ),
            xaxis=dict(
                title="平均排名位置 (越小越好)",
                autorange="reversed",  # 反轉 X 軸
                gridcolor="lightgray",
                showgrid=True
            ),
            yaxis=dict(
                title="點擊率 CTR (%)",
                gridcolor="lightgray",
                showgrid=True
            ),
            plot_bgcolor="white",
            paper_bgcolor="white"
        )

        # 添加四象限分隔線和象限標籤
        ctr_median = df['ctr_percent'].median()
        position_median = df['avg_position'].median()

        # CTR中位數線（水平線）- 更明顯的分隔線
        fig.add_hline(y=ctr_median, line_dash="solid",
                      line_color="red", line_width=3, opacity=0.9,
                      annotation_text=f"四象限分隔線 - CTR中位數: {ctr_median:.2f}%",
                      annotation_position="bottom right",
                      annotation_font_size=14, annotation_font_color="red")

        # 排名中位數線（垂直線）- 更明顯的分隔線
        fig.add_vline(x=position_median, line_dash="solid",
                      line_color="blue", line_width=3, opacity=0.9,
                      annotation_text=f"四象限分隔線 - 排名中位數: {position_median:.1f}",
                      annotation_position="top left",
                      annotation_font_size=14, annotation_font_color="blue")

        # 添加四象限背景色和標籤
        y_range = df['ctr_percent'].max() - df['ctr_percent'].min()
        x_range = df['avg_position'].max() - df['avg_position'].min()

        # 優秀表現象限 (左上角)
        fig.add_annotation(
            x=df['avg_position'].min() + x_range * 0.1,
            y=df['ctr_percent'].max() - y_range * 0.1,
            text="🏆 優秀表現<br>高CTR + 好排名",
            showarrow=False,
            font=dict(
                size=16,
                color="green",
                family="Arial Black"),
            bgcolor="rgba(76,175,80,0.1)",
            bordercolor="green",
            borderwidth=2,
            width=120,
            height=60)

        # 潛力關鍵字象限 (右上角)
        fig.add_annotation(
            x=df['avg_position'].max() - x_range * 0.15,
            y=df['ctr_percent'].max() - y_range * 0.1,
            text="⭐ 潛力關鍵字<br>高CTR + 低排名",
            showarrow=False,
            font=dict(
                size=16,
                color="orange",
                family="Arial Black"),
            bgcolor="rgba(255,152,0,0.1)",
            bordercolor="orange",
            borderwidth=2,
            width=120,
            height=60)

        # 需要優化象限 (左下角)
        fig.add_annotation(
            x=df['avg_position'].min() + x_range * 0.1,
            y=df['ctr_percent'].min() + y_range * 0.15,
            text="📈 需要優化<br>低CTR + 好排名",
            showarrow=False,
            font=dict(
                size=16,
                color="blue",
                family="Arial Black"),
            bgcolor="rgba(33,150,243,0.1)",
            bordercolor="blue",
            borderwidth=2,
            width=120,
            height=60)

        # 重點改善象限 (右下角)
        fig.add_annotation(
            x=df['avg_position'].max() -
            x_range *
            0.15,
            y=df['ctr_percent'].min() +
            y_range *
            0.15,
            text="🔧 重點改善<br>低CTR + 低排名",
            showarrow=False,
            font=dict(
                size=16,
                color="red",
                family="Arial Black"),
            bgcolor="rgba(244,67,54,0.1)",
            bordercolor="red",
            borderwidth=2,
            width=120,
            height=60)

        # 保存或顯示
        if save_path:
            fig.write_html(save_path, include_plotlyjs='cdn')
            print(f"🎨 互動式頁面氣泡圖已保存到: {save_path}")
        else:
            fig.show()

    def generate_quadrant_analysis(self, df):
        """生成四象限分析"""
        if df.empty:
            return {"quadrants": {}, "summary": "無數據可分析"}

        # 計算中位數作為分界線
        ctr_median = df['ctr_percent'].median()
        position_median = df['avg_position'].median()

        # 分類到四個象限
        quadrants = {
            "優秀表現 (高CTR + 好排名)": [],  # 左上
            "潛力關鍵字 (高CTR + 低排名)": [],  # 右上
            "需要優化 (低CTR + 好排名)": [],  # 左下
            "重點改善 (低CTR + 低排名)": []   # 右下
        }

        for _, row in df.iterrows():
            keyword = row['query_clean']
            clicks = int(row['total_clicks'])
            impressions = int(row['total_impressions'])
            ctr = row['ctr_percent']
            position = row['avg_position']
            site = row['site_name']

            item = {
                'keyword': keyword,
                'clicks': clicks,
                'impressions': impressions,
                'ctr': ctr,
                'position': position,
                'site': site
            }

            if ctr >= ctr_median and position <= position_median:
                quadrants["優秀表現 (高CTR + 好排名)"].append(item)
            elif ctr >= ctr_median and position > position_median:
                quadrants["潛力關鍵字 (高CTR + 低排名)"].append(item)
            elif ctr < ctr_median and position <= position_median:
                quadrants["需要優化 (低CTR + 好排名)"].append(item)
            else:
                quadrants["重點改善 (低CTR + 低排名)"].append(item)

        # 每個象限只顯示前10名
        for quadrant in quadrants:
            quadrants[quadrant] = sorted(
                quadrants[quadrant],
                key=lambda x: x['clicks'],
                reverse=True)[
                :10]

        summary = f"分析基準：CTR中位數 {ctr_median:.2f}%, 排名中位數 {position_median:.1f}"

        return {
            "quadrants": quadrants,
            "summary": summary,
            "ctr_median": ctr_median,
            "position_median": position_median
        }

    def save_bubble_with_analysis(self, fig, analysis, save_path, chart_type):
        """保存包含四象限分析和動態篩選功能的 HTML 頁面"""
        import plotly.offline as pyo

        # 獲取原始數據（用於動態篩選）
        if chart_type == "關鍵字":
            raw_data = self.get_keyword_bubble_data(days=30, limit=50)
        else:
            raw_data = self.get_page_bubble_data(days=30, limit=30)

        # 將數據轉換為 JSON 格式供 JavaScript 使用
        data_json = raw_data.to_json(
            orient='records') if raw_data is not None else "[]"

        # 獲取圖表的 HTML
        plot_html = pyo.plot(fig, output_type='div', include_plotlyjs=True)

        # 生成四象限分析的 HTML
        analysis_html = self.generate_analysis_html(analysis, chart_type)

        # 組合完整的 HTML 頁面
        full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>GSC {chart_type}互動式分析</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .chart-container {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        .analysis-container {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .quadrant-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
        .quadrant {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; }}
        .quadrant h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 8px; }}
        .keyword-item {{ margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 5px; font-size: 14px; }}
        .keyword-name {{ font-weight: bold; color: #007bff; }}
        .keyword-stats {{ color: #666; font-size: 12px; }}
        .summary {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-weight: bold; }}
        .q1 {{ border-left: 4px solid #4caf50; }} /* 綠色 - 優秀 */
        .q2 {{ border-left: 4px solid #ff9800; }} /* 橙色 - 潛力 */
        .q3 {{ border-left: 4px solid #2196f3; }} /* 藍色 - 需優化 */
        .q4 {{ border-left: 4px solid #f44336; }} /* 紅色 - 重點改善 */
        .filter-info {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .reset-btn {{ background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 10px 0; }}
        .reset-btn:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 GSC {chart_type}互動式分析報告</h1>
            <p>結合互動式氣泡圖與四象限策略分析</p>
        </div>

        <div class="chart-container">
            <h2>📊 互動式氣泡圖</h2>
            <p>💡 <strong>使用提示：</strong>滑鼠懸停查看詳細資訊，拖拽縮放，點擊圖例篩選數據</p>
            <p>🎯 <strong>動態篩選：</strong>在圖表上拖拽框選區域，下方四象限分析會即時更新顯示框選範圍內的數據</p>
            <div class="filter-info" id="filterInfo" style="display:none;">
                <strong>🔍 已篩選範圍：</strong><span id="filterRange"></span>
                <button class="reset-btn" onclick="resetFilter()">重置篩選</button>
            </div>
            {plot_html}
        </div>

        <div class="analysis-container">
            <h2>🎯 四象限策略分析</h2>
            {analysis_html}
        </div>
    </div>

    <script>
        // 原始數據
        const originalData = {data_json};
        let currentData = originalData;
        const chartType = "{chart_type}";

        // 監聽 Plotly 選擇事件
        document.addEventListener('DOMContentLoaded', function() {{
            const plotDiv = document.querySelector('[id^="plotly-div-"]');
            if (plotDiv) {{
                plotDiv.on('plotly_selected', function(eventData) {{
                    if (eventData && eventData.points && eventData.points.length > 0) {{
                        handleSelection(eventData.points);
                    }}
                }});

                plotDiv.on('plotly_deselect', function() {{
                    resetFilter();
                }});
            }}
        }});

        function handleSelection(selectedPoints) {{
            // 提取選中點的索引
            const selectedIndices = selectedPoints.map(point => point.pointIndex);

            // 過濾數據
            const filteredData = originalData.filter((item, index) => selectedIndices.includes(index));

            if (filteredData.length === 0) return;

            // 更新四象限分析
            updateQuadrantAnalysis(filteredData);

            // 顯示篩選資訊
            showFilterInfo(filteredData.length, originalData.length);
        }}

        function updateQuadrantAnalysis(data) {{
            // 計算中位數
            const ctrValues = data.map(d => d.ctr_percent).sort((a, b) => a - b);
            const positionValues = data.map(d => d.avg_position).sort((a, b) => a - b);

            const ctrMedian = getMedian(ctrValues);
            const positionMedian = getMedian(positionValues);

            // 分類到四象限
            const quadrants = {{
                "優秀表現 (高CTR + 好排名)": [],
                "潛力關鍵字 (高CTR + 低排名)": [],
                "需要優化 (低CTR + 好排名)": [],
                "重點改善 (低CTR + 低排名)": []
            }};

            data.forEach(item => {{
                const dataItem = {{
                    keyword: item.query_clean || item.page_clean,
                    clicks: item.total_clicks,
                    impressions: item.total_impressions,
                    ctr: item.ctr_percent,
                    position: item.avg_position,
                    site: item.site_name
                }};

                if (item.ctr_percent >= ctrMedian && item.avg_position <= positionMedian) {{
                    quadrants["優秀表現 (高CTR + 好排名)"].push(dataItem);
                }} else if (item.ctr_percent >= ctrMedian && item.avg_position > positionMedian) {{
                    quadrants["潛力關鍵字 (高CTR + 低排名)"].push(dataItem);
                }} else if (item.ctr_percent < ctrMedian && item.avg_position <= positionMedian) {{
                    quadrants["需要優化 (低CTR + 好排名)"].push(dataItem);
                }} else {{
                    quadrants["重點改善 (低CTR + 低排名)"].push(dataItem);
                }}
            }});

            // 更新 DOM
            updateQuadrantDOM(quadrants, ctrMedian, positionMedian);
        }}

        function updateQuadrantDOM(quadrants, ctrMedian, positionMedian) {{
            // 更新摘要
            const summary = `篩選後分析基準：CTR中位數 ${{ctrMedian.toFixed(2)}}%, 排名中位數 ${{positionMedian.toFixed(1)}}`;
            document.querySelector('.summary').textContent = summary;

            // 更新四象限
            const quadrantNames = ["優秀表現 (高CTR + 好排名)", "潛力關鍵字 (高CTR + 低排名)", "需要優化 (低CTR + 好排名)", "重點改善 (低CTR + 低排名)"];
            const quadrantIcons = ["🏆", "⭐", "📈", "🔧"];

            document.querySelectorAll('.quadrant').forEach((quadrantDiv, i) => {{
                const quadrantName = quadrantNames[i];
                const items = quadrants[quadrantName];

                // 更新標題
                const h3 = quadrantDiv.querySelector('h3');
                h3.textContent = `${{quadrantIcons[i]}} ${{quadrantName}} (${{items.length}})`;

                // 清除舊內容
                const existingItems = quadrantDiv.querySelectorAll('.keyword-item');
                existingItems.forEach(item => item.remove());

                // 添加新內容
                if (items.length === 0) {{
                    const noData = document.createElement('p');
                    noData.style.color = '#999';
                    noData.style.fontStyle = 'italic';
                    noData.textContent = '篩選範圍內無數據';
                    quadrantDiv.appendChild(noData);
                }} else {{
                    // 按點擊量排序並取前10名
                    const sortedItems = items.sort((a, b) => b.clicks - a.clicks).slice(0, 10);

                    sortedItems.forEach(item => {{
                        const itemDiv = document.createElement('div');
                        itemDiv.className = 'keyword-item';
                        itemDiv.innerHTML = `
                            <div class="keyword-name">${{item.keyword}}</div>
                            <div class="keyword-stats">
                                點擊: ${{item.clicks}} | 曝光: ${{item.impressions.toLocaleString()}} | CTR: ${{item.ctr.toFixed(2)}}% | 排名: ${{item.position.toFixed(1)}} | ${{item.site}}
                            </div>
                        `;
                        quadrantDiv.appendChild(itemDiv);
                    }});
                }}
            }});
        }}

        function showFilterInfo(filteredCount, totalCount) {{
            const filterInfo = document.getElementById('filterInfo');
            const filterRange = document.getElementById('filterRange');

            filterRange.textContent = `已選中 ${{filteredCount}} 個數據點（總共 ${{totalCount}} 個）`;
            filterInfo.style.display = 'block';
        }}

        function resetFilter() {{
            // 隱藏篩選資訊
            document.getElementById('filterInfo').style.display = 'none';

            // 重新載入原始四象限分析
            location.reload();
        }}

        function getMedian(arr) {{
            const sorted = [...arr].sort((a, b) => a - b);
            const mid = Math.floor(sorted.length / 2);
            return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
        }}
    </script>
</body>
</html>
"""

        # 保存到文件
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(full_html)

    def generate_analysis_html(self, analysis, chart_type):
        """生成四象限分析的 HTML"""
        if not analysis["quadrants"]:
            return "<p>無足夠數據進行四象限分析</p>"

        html_parts = [f'<div class="summary">{analysis["summary"]}</div>']
        html_parts.append('<div class="quadrant-grid">')

        quadrant_classes = ["q1", "q2", "q3", "q4"]
        quadrant_icons = ["🏆", "⭐", "📈", "🔧"]

        for i, (quadrant_name, items) in enumerate(
                analysis["quadrants"].items()):
            html_parts.append(f'<div class="quadrant {quadrant_classes[i]}">')
            html_parts.append(
                f'<h3>{quadrant_icons[i]} {quadrant_name} ({len(items)})</h3>')

            if not items:
                html_parts.append(
                    '<p style="color: #999; font-style: italic;">暫無數據</p>')
            else:
                for item in items:
                    html_parts.append(f'''
                    <div class="keyword-item">
                        <div class="keyword-name">{item["keyword"]}</div>
                        <div class="keyword-stats">
                            點擊: {item["clicks"]} | 曝光: {item["impressions"]:,} | CTR: {item["ctr"]:.2f}% | 排名: {item["position"]:.1f} | {item["site"]}
                        </div>
                    </div>
                    ''')

            html_parts.append('</div>')

        html_parts.append('</div>')

        # 添加策略建議
        html_parts.append('''
        <div style="margin-top: 30px; padding: 20px; background: #f0f8ff; border-radius: 8px;">
            <h3>💡 四象限策略建議</h3>
            <ul style="line-height: 1.6;">
                <li><strong>🏆 優秀表現：</strong>維持現有策略，可考慮增加預算或擴展相關關鍵字</li>
                <li><strong>⭐ 潛力關鍵字：</strong>優化頁面SEO，提高排名以獲得更多曝光</li>
                <li><strong>📈 需要優化：</strong>改善標題和描述，提高點擊吸引力</li>
                <li><strong>🔧 重點改善：</strong>全面檢視關鍵字策略，考慮調整或替換</li>
            </ul>
        </div>
        ''')

        return ''.join(html_parts)

    def create_multi_site_comparison(self, days=30, save_path=None):
        """創建多站點對比氣泡圖"""
        df = self.get_keyword_bubble_data(days, 100)  # 獲取更多數據
        if df is None or df.empty:
            print("無法獲取對比數據")
            return

        # 創建多站點對比圖
        fig = px.scatter(
            df,
            x="avg_position",
            y="ctr_percent",
            size="total_clicks",
            color="site_name",
            hover_name="query_clean",
            hover_data={
                "total_clicks": True,
                "total_impressions": True,
                "avg_position": ":.1f",
                "ctr_percent": ":.2f",
                "active_days": True},
            title=f"多站點關鍵字表現對比 (近 {days} 天)<br><sub>X軸=排名位置, Y軸=CTR%, 氣泡大小=點擊量, 顏色=站點</sub>",
            labels={
                "avg_position": "平均排名位置",
                "ctr_percent": "點擊率 CTR (%)",
                "total_clicks": "總點擊量",
                "site_name": "站點名稱"})

        # 美化圖表
        fig.update_layout(
            width=1400,
            height=800,
            font=dict(size=12),
            title_font_size=18,
            xaxis=dict(
                title="平均排名位置 (越小越好)",
                autorange="reversed",
                gridcolor="lightgray",
                showgrid=True
            ),
            yaxis=dict(
                title="點擊率 CTR (%)",
                gridcolor="lightgray",
                showgrid=True
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )

        # 添加四象限分隔線和象限標籤
        ctr_median = df['ctr_percent'].median()
        position_median = df['avg_position'].median()

        # CTR中位數線（水平線）- 更明顯的分隔線
        fig.add_hline(y=ctr_median, line_dash="solid",
                      line_color="red", line_width=3, opacity=0.9,
                      annotation_text=f"四象限分隔線 - CTR中位數: {ctr_median:.2f}%",
                      annotation_position="bottom right",
                      annotation_font_size=14, annotation_font_color="red")

        # 排名中位數線（垂直線）- 更明顯的分隔線
        fig.add_vline(x=position_median, line_dash="solid",
                      line_color="blue", line_width=3, opacity=0.9,
                      annotation_text=f"四象限分隔線 - 排名中位數: {position_median:.1f}",
                      annotation_position="top left",
                      annotation_font_size=14, annotation_font_color="blue")

        # 添加四象限背景色和標籤
        y_range = df['ctr_percent'].max() - df['ctr_percent'].min()
        x_range = df['avg_position'].max() - df['avg_position'].min()

        # 優秀表現象限 (左上角)
        fig.add_annotation(
            x=df['avg_position'].min() + x_range * 0.1,
            y=df['ctr_percent'].max() - y_range * 0.1,
            text="🏆 優秀表現<br>高CTR + 好排名",
            showarrow=False,
            font=dict(
                size=16,
                color="green",
                family="Arial Black"),
            bgcolor="rgba(76,175,80,0.1)",
            bordercolor="green",
            borderwidth=2,
            width=120,
            height=60)

        # 潛力關鍵字象限 (右上角)
        fig.add_annotation(
            x=df['avg_position'].max() - x_range * 0.15,
            y=df['ctr_percent'].max() - y_range * 0.1,
            text="⭐ 潛力關鍵字<br>高CTR + 低排名",
            showarrow=False,
            font=dict(
                size=16,
                color="orange",
                family="Arial Black"),
            bgcolor="rgba(255,152,0,0.1)",
            bordercolor="orange",
            borderwidth=2,
            width=120,
            height=60)

        # 需要優化象限 (左下角)
        fig.add_annotation(
            x=df['avg_position'].min() + x_range * 0.1,
            y=df['ctr_percent'].min() + y_range * 0.15,
            text="📈 需要優化<br>低CTR + 好排名",
            showarrow=False,
            font=dict(
                size=16,
                color="blue",
                family="Arial Black"),
            bgcolor="rgba(33,150,243,0.1)",
            bordercolor="blue",
            borderwidth=2,
            width=120,
            height=60)

        # 重點改善象限 (右下角)
        fig.add_annotation(
            x=df['avg_position'].max() -
            x_range *
            0.15,
            y=df['ctr_percent'].min() +
            y_range *
            0.15,
            text="🔧 重點改善<br>低CTR + 低排名",
            showarrow=False,
            font=dict(
                size=16,
                color="red",
                family="Arial Black"),
            bgcolor="rgba(244,67,54,0.1)",
            bordercolor="red",
            borderwidth=2,
            width=120,
            height=60)

        # 保存或顯示
        if save_path:
            # 生成四象限分析
            quadrant_analysis = self.generate_quadrant_analysis(df)

            # 將氣泡圖和四象限分析結合到一個 HTML 頁面
            self.save_bubble_with_analysis(
                fig, quadrant_analysis, save_path, "多站點對比")
            print(f"🎨 互動式多站點對比氣泡圖（含四象限分析）已保存到: {save_path}")
        else:
            fig.show()


def main():
    parser = argparse.ArgumentParser(description='互動式氣泡圖生成器')
    parser.add_argument('--type', choices=['keywords', 'pages', 'comparison'],
                        default='keywords', help='圖表類型')
    parser.add_argument('--days', type=int, default=30, help='數據天數')
    parser.add_argument('--limit', type=int, default=50, help='顯示數量限制')
    parser.add_argument('--save', type=str, help='保存 HTML 文件路徑')
    parser.add_argument('--db', type=str, default='gsc_data.db', help='數據庫路徑')

    args = parser.parse_args()

    bubble_chart = InteractiveBubbleChart(args.db)

    if args.type == 'keywords':
        bubble_chart.create_keyword_bubble_chart(
            args.days, args.limit, args.save)
    elif args.type == 'pages':
        bubble_chart.create_page_bubble_chart(args.days, args.limit, args.save)
    elif args.type == 'comparison':
        bubble_chart.create_multi_site_comparison(args.days, args.save)


if __name__ == "__main__":
    main()
