#!/usr/bin/env python3
"""
GSC 分析報告構建器
重構為可調用函數，支持 CLI 整合
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.font_manager as fm
from pathlib import Path
import logging
from typing import Optional, Dict, Any, List
import datetime
import sqlite3

# 專案模組導入
from .. import config
from ..services.database import Database
from ..services.analysis_service import AnalysisService
from ..utils.matplotlib_utils import set_chinese_font, DUOLINGO_COLORS

logger = logging.getLogger(__name__)


class GSCVisualizer:
    """GSC 數據可視化器，完全依賴 AnalysisService"""

    def __init__(self, analysis_service: AnalysisService):
        """初始化可視化器，完全依賴於分析服務"""
        self.analysis_service = analysis_service

    def get_daily_stats(self, site_id: int, days: int = 30) -> Optional[pd.DataFrame]:
        """獲取每日統計數據"""
        try:
            stats_data = self.analysis_service.get_daily_performance_summary(
                site_id=site_id, days=days
            )
            if not stats_data:
                return None
            df = pd.DataFrame(stats_data)
            df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            logger.error(f"獲取每日統計數據錯誤: {e}", exc_info=True)
            return None

    def get_top_keywords(self, site_id: int, limit: int = 20, days: int = 7) -> Optional[pd.DataFrame]:
        """獲取表現最佳的關鍵字"""
        try:
            keywords_data = self.analysis_service.get_top_keywords(
                site_id=site_id, days=days, limit=limit
            )
            return pd.DataFrame(keywords_data) if keywords_data else None
        except Exception as e:
            logger.error(f"獲取熱門關鍵字數據錯誤: {e}", exc_info=True)
            return None

    def get_page_performance(self, site_id: int, limit: int = 15, days: int = 7) -> Optional[pd.DataFrame]:
        """獲取頁面表現數據"""
        try:
            pages_data = self.analysis_service.get_top_pages(
                site_id=site_id, days=days, limit=limit
            )
            if not pages_data:
                return None
            df = pd.DataFrame(pages_data)
            # 確保指標是數字類型
            for col in ['total_clicks', 'total_impressions', 'avg_position', 'avg_ctr']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        except Exception as e:
            logger.error(f"獲取頁面表現數據錯誤: {e}", exc_info=True)
            return None

    def get_summary_stats(self, site_id: int, days: int = 30) -> Optional[Dict[str, Any]]:
        """獲取數據摘要統計信息"""
        try:
            return self.analysis_service.get_overall_summary(
                site_id=site_id, days=days
            )
        except Exception as e:
            logger.error(f"獲取摘要數據錯誤: {e}", exc_info=True)
            return None

    def plot_daily_trends(self, site_id: int, days: int = 30, save_path: Optional[str] = None) -> Optional[Figure]:
        """繪製每日趨勢圖"""
        df = self.get_daily_stats(site_id, days)
        if df is None or df.empty:
            logger.warning("沒有每日趨勢數據可供繪圖。")
            return None

        set_chinese_font()
        fig, axes = plt.subplots(2, 2, figsize=(20, 16))
        fig.suptitle(f'{days} 天 GSC 數據趨勢概覽', fontsize=22, fontweight='bold')

        # Clicks, Impressions, Position, Keyword Count
        axes[0, 0].plot(df['date'], df['total_clicks'], color=DUOLINGO_COLORS['blue'], linewidth=2.5, marker='o')
        axes[0, 0].set_title('總點擊量', fontweight='bold')
        axes[0, 0].set_ylabel('點擊次數')

        axes[0, 1].plot(df['date'], df['total_impressions'], color=DUOLINGO_COLORS['orange'], linewidth=2.5, marker='s')
        axes[0, 1].set_title('總曝光量', fontweight='bold')
        axes[0, 1].set_ylabel('曝光量')

        axes[1, 0].plot(df['date'], df['avg_position'], color=DUOLINGO_COLORS['green'], linewidth=2.5, marker='^')
        axes[1, 0].set_title('平均排名', fontweight='bold')
        axes[1, 0].set_ylabel('排名 (越小越好)')
        axes[1, 0].invert_yaxis()

        axes[1, 1].plot(df['date'], df['keyword_count'], color=DUOLINGO_COLORS['purple'], linewidth=2.5, marker='d')
        axes[1, 1].set_title('獨立關鍵字數量', fontweight='bold')
        axes[1, 1].set_ylabel('關鍵字數')

        for ax in axes.flat:
            ax.grid(True, alpha=0.3)
            for label in ax.get_xticklabels():
                label.set_rotation(30)
                label.set_ha('right')

        plt.tight_layout(rect=(0, 0, 1, 0.96))
        if save_path:
            plt.savefig(save_path)
            logger.info(f"圖表已保存至: {save_path}")
            plt.close()

        return fig

    def plot_top_keywords(self, site_id: int, limit: int = 20, days: int = 7, save_path: Optional[str] = None) -> Optional[Figure]:
        """繪製頂級關鍵字圖表"""
        df = self.get_top_keywords(site_id, limit, days)
        if df is None or df.empty:
            logger.warning("沒有關鍵字數據可供繪製。")
            return None

        set_chinese_font()
        fig, axes = plt.subplots(2, 2, figsize=(20, 18))
        fig.suptitle(f'最近 {days} 天 Top 關鍵字表現', fontsize=22, fontweight='bold')

        # Clicks, Impressions, Position, CTR
        top_clicks = df.nlargest(10, 'total_clicks').sort_values('total_clicks', ascending=True)
        axes[0, 0].barh(top_clicks['query'], top_clicks['total_clicks'], color=DUOLINGO_COLORS['blue'], zorder=3)
        axes[0, 0].set_title('點擊數 Top 10', fontweight='bold')

        top_impressions = df.nlargest(10, 'total_impressions').sort_values('total_impressions', ascending=True)
        axes[0, 1].barh(top_impressions['query'], top_impressions['total_impressions'], color=DUOLINGO_COLORS['green'], zorder=3)
        axes[0, 1].set_title('曝光量 Top 10', fontweight='bold')

        top_position = df[df['avg_position'].notna()].nsmallest(10, 'avg_position').sort_values('avg_position', ascending=False)
        axes[1, 0].barh(top_position['query'], top_position['avg_position'], color=DUOLINGO_COLORS['orange'], zorder=3)
        axes[1, 0].set_title('平均排名 Top 10 (越小越好)', fontweight='bold')

        top_ctr = df[df['avg_ctr'].notna()].nlargest(10, 'avg_ctr').sort_values('avg_ctr', ascending=True)
        axes[1, 1].barh(top_ctr['query'], top_ctr['avg_ctr'] * 100, color=DUOLINGO_COLORS['red'], zorder=3)
        axes[1, 1].set_title('點閱率 (CTR) Top 10', fontweight='bold')
        axes[1, 1].set_xlabel('平均點閱率 (%)')

        for ax in axes.flat:
            ax.grid(axis='x', linestyle='--', alpha=0.6)

        plt.tight_layout(rect=(0, 0, 1, 0.96))
        if save_path:
            plt.savefig(save_path)
            logger.info(f"圖表已保存至: {save_path}")
            plt.close()

        return fig

    def plot_page_performance(self, site_id: int, limit: int = 15, days: int = 7, save_path: Optional[str] = None) -> Optional[Figure]:
        """繪製頁面表現圖表"""
        df = self.get_page_performance(site_id, limit, days)
        if df is None or df.empty:
            logger.warning("沒有頁面數據可供繪製。")
            return None

        set_chinese_font()
        fig, axes = plt.subplots(1, 2, figsize=(20, 12))
        fig.suptitle(f'最近 {days} 天 Top {limit} 頁面表現', fontsize=18, fontweight='bold')

        # Clicks and Impressions
        top_clicks = df.nlargest(limit, 'total_clicks').sort_values('total_clicks', ascending=True)
        axes[0].barh(top_clicks['page_short'], top_clicks['total_clicks'], color=DUOLINGO_COLORS['blue'], zorder=3)
        axes[0].set_title('點擊數 Top Pages', fontweight='bold')

        top_impressions = df.nlargest(limit, 'total_impressions').sort_values('total_impressions', ascending=True)
        axes[1].barh(top_impressions['page_short'], top_impressions['total_impressions'], color=DUOLINGO_COLORS['green'], zorder=3)
        axes[1].set_title('曝光量 Top Pages', fontweight='bold')
        
        for ax in axes.flat:
            ax.grid(axis='x', linestyle='--', alpha=0.6)

        plt.tight_layout(rect=(0, 0, 1, 0.95))
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"頁面表現圖表已保存: {save_path}")
            plt.close()

        return fig


def _generate_summary_plot(visualizer: GSCVisualizer, site_id: int, days: int = 30, save_path: Optional[str] = None) -> Optional[Figure]:
    """生成摘要圖表"""
    try:
        return visualizer.plot_daily_trends(site_id=site_id, days=days, save_path=save_path)
    except Exception as e:
        logger.error(f"生成摘要圖表失敗: {e}", exc_info=True)
        return None


def _create_markdown_report(
    visualizer: "GSCVisualizer",
    site_id: int,
    days: int,
    output_path: str,
    include_plots: bool,
    plot_save_dir: Optional[str] = None,
) -> bool:
    """創建 Markdown 報告"""
    try:
        summary = visualizer.get_summary_stats(site_id, days)
        if not summary:
            logger.error("無法獲取數據摘要")
            return False

        keywords_df = visualizer.get_top_keywords(site_id, limit=20, days=days)
        pages_df = visualizer.get_page_performance(site_id, limit=15, days=days)

        if keywords_df is None or pages_df is None:
            logger.warning("關鍵字或頁面數據為空，報告內容不完整。")

        report_content = f"""# GSC 網站表現報告 ({datetime.datetime.now().strftime('%Y-%m-%d')})

## 📊 數據概覽 (最近 {days} 天)

- **報告生成時間**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **數據起點**: {summary.get('first_date', 'N/A')}
- **數據終點**: {summary.get('last_date', 'N/A')}
- **總記錄數**: {summary.get('total_records', 'N/A'):,}
- **獨立關鍵字數量**: {summary.get('total_keywords', 'N/A'):,}
- **獨立頁面數量**: {summary.get('total_pages', 'N/A'):,}

## 📈 關鍵字表現 Top 20

{keywords_df.to_markdown(index=False) if keywords_df is not None else '無數據'}

## 📄 頁面表現 Top 15

{pages_df[['page', 'total_clicks', 'total_impressions', 'avg_position', 'avg_ctr']].to_markdown(index=False) if pages_df is not None else '無數據'}
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return True
    except Exception as e:
        logger.error(f"創建 Markdown 報告失敗: {e}", exc_info=True)
        return False


def build_report(
    analysis_service: "AnalysisService",
    site_id: int,
    output_path: str = "gsc_report.md",
    days: int = 30,
    include_plots: bool = True,
    plot_save_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成 GSC 數據分析報告。
    """
    logger.info(f"開始為站點 ID {site_id} 生成報告...")
    
    # 創建可視化器實例
    visualizer = GSCVisualizer(analysis_service)

    # 確保繪圖目錄存在
    if include_plots:
        save_dir: Path
        if plot_save_dir:
            save_dir = Path(plot_save_dir)
        else:
            save_dir = Path(output_path).parent / "plots"
        
        save_dir.mkdir(parents=True, exist_ok=True)
    
        # 生成並保存圖表
        try:
            visualizer.plot_daily_trends(site_id, days, save_path=str(save_dir / "daily_trends.png"))
            visualizer.plot_top_keywords(site_id, days=days, save_path=str(save_dir / "top_keywords.png"))
            visualizer.plot_page_performance(site_id, days=days, save_path=str(save_dir / "page_performance.png"))
        except Exception as e:
            logger.error(f"生成圖表時發生錯誤: {e}", exc_info=True)

    # 生成 Markdown 報告
    try:
        report_created = _create_markdown_report(
            visualizer=visualizer,
            site_id=site_id,
            days=days,
            output_path=output_path,
            include_plots=include_plots,
            plot_save_dir=plot_save_dir
        )
        if report_created:
            logger.info(f"報告已成功生成於: {output_path}")
            return {"success": True, "output_path": output_path}
        else:
            return {"success": False, "errors": ["Markdown 報告創建失敗"]}
    except Exception as e:
        logger.error(f"生成報告時發生嚴重錯誤: {e}", exc_info=True)
        return {"success": False, "errors": [str(e)]}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="生成 GSC 表現報告")
    parser.add_argument("--site-id", type=int, required=True, help="要分析的網站 ID")
    parser.add_argument("--output", default="gsc_report.md", help="報告輸出路徑")
    parser.add_argument("--days", type=int, default=30, help="分析天數")
    parser.add_argument("--no-plots", action="store_true", help="不生成圖表")
    parser.add_argument("--plot-dir", help="圖表保存目錄")
    parser.add_argument("--db-path", help="數據庫文件路徑")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Assuming config.DB_PATH is accessible or passed via --db-path
    db_path = args.db_path if args.db_path else str(config.DB_PATH)
    db_service = Database(db_path)
    analysis_service = AnalysisService(db_service)

    result = build_report(
        analysis_service=analysis_service,
        site_id=args.site_id,
        output_path=args.output,
        days=args.days,
        include_plots=not args.no_plots,
        plot_save_dir=args.plot_dir
    )
    
    if result['success']:
        print(f"報告成功生成: {result['output_path']}")
        if result['plots_generated']:
            print("生成的圖表:")
            for plot in result['plots_generated']:
                print(f"- {plot}")
    else:
        print("報告生成失敗:")
        for error in result['errors']:
            print(f"- {error}")
