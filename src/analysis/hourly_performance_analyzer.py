#!/usr/bin/env python3
"""
GSC 每小時表現分析工具
專門用於分析搜索流量的時段分佈和表現趨勢
重構為可調用函數，支持 CLI 整合
"""

import argparse
import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# 專案模組導入
from .. import config
from ..services.database import Database

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 完全抑制所有 matplotlib 相關警告
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.font_manager")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.backends")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="matplotlib")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.text")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.rcsetup")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.cbook")

# 設置現代化視覺風格
plt.style.use("seaborn-v0_8-whitegrid")


# 更強健的字體配置，完全處理 emoji 和中文顯示問題
def configure_matplotlib_fonts():
    """配置 matplotlib 字體以支持 emoji 和中文，完全抑制警告"""
    import platform

    # 完全抑制字體相關警告
    import warnings

    import matplotlib
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt

    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    # 根據操作系統選擇合適的字體
    system = platform.system()

    if system == "Darwin":  # macOS
        font_list = [
            "Arial Unicode MS",  # 最兼容的字體，支持 emoji 和中文
            "Helvetica Neue",
            "Helvetica",
            "Arial",
            "DejaVu Sans",
        ]
    elif system == "Windows":
        font_list = [
            "Arial Unicode MS",  # 最兼容的字體
            "Segoe UI",
            "Arial",
            "DejaVu Sans",
        ]
    else:  # Linux and others
        font_list = [
            "DejaVu Sans",  # Linux 最可靠的字體
            "Liberation Sans",
            "Arial",
            "Helvetica",
        ]

    # 檢查字體可用性並設置
    available_fonts = []

    for font in font_list:
        try:
            # 更嚴格的字體檢查
            font_path = fm.findfont(font)
            if font_path and font_path != matplotlib.rcParams["font.sans-serif"][0]:
                available_fonts.append(font)
        except Exception:
            continue

    # 如果沒有找到合適字體，使用基本字體
    if not available_fonts:
        available_fonts = ["DejaVu Sans", "Arial", "Helvetica"]

    # 設置字體參數
    plt.rcParams["font.sans-serif"] = available_fonts
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "#f8f9fa"

    # 使用更可靠的方法設置 unicode_minus
    plt.rc("axes", unicode_minus=False)

    # 清除字體緩存以確保新配置生效
    try:
        # 嘗試清除字體緩存
        if hasattr(fm.findfont, "cache_clear"):
            fm.findfont.cache_clear()
    except Exception:
        pass

    # 設置全局警告過濾
    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.font_manager")
    warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.backends")
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="matplotlib")

    return True, True


# 配置字體並獲取支持狀態
EMOJI_SUPPORTED, CHINESE_SUPPORTED = configure_matplotlib_fonts()

# 專業配色方案
HOURLY_COLORS = {
    "morning": "#ffbe0b",  # 早晨 6-11
    "noon": "#fb5607",  # 中午 12-17
    "evening": "#8338ec",  # 晚上 18-23
    "night": "#3a86ff",  # 深夜 0-5
    "primary": "#06d6a0",
    "secondary": "#f77f00",
    "accent": "#fcbf49",
}


class HourlyAnalyzer:
    """每小時數據分析器"""

    def __init__(self, db: Database):
        self.db = db

    def get_hourly_summary(self, days=7):
        """獲取每小時數據摘要"""
        try:
            latest_date = self.db.get_latest_date_from_table("hourly_rankings")
            if not latest_date:
                logger.warning("No hourly data found to analyze.")
                return None

            start_date = latest_date - timedelta(days=days - 1)

            data = self.db.get_hourly_rankings(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=latest_date.strftime("%Y-%m-%d"),
            )

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            # Perform aggregation in pandas
            summary_df = (
                df.groupby("hour")
                .agg(
                    total_records=("hour", "size"),
                    unique_queries=("query", "nunique"),
                    days_active=("date", "nunique"),
                    total_clicks=("clicks", "sum"),
                    total_impressions=("impressions", "sum"),
                    avg_position=("position", "mean"),
                    avg_ctr=("ctr", "mean"),
                )
                .reset_index()
            )
            return summary_df

        except Exception as e:
            logger.error(f"獲取每小時摘要錯誤: {e}")
            return None

    def get_daily_hourly_heatmap(self, days=7):
        """獲取每日每小時熱力圖數據"""
        try:
            latest_date = self.db.get_latest_date_from_table("hourly_rankings")
            if not latest_date:
                return None

            start_date = latest_date - timedelta(days=days - 1)

            data = self.db.get_hourly_rankings(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=latest_date.strftime("%Y-%m-%d"),
            )

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            heatmap_df = (
                df.groupby(["date", "hour"])
                .agg(
                    records=("hour", "size"),
                    clicks=("clicks", "sum"),
                    impressions=("impressions", "sum"),
                    avg_position=("position", "mean"),
                )
                .reset_index()
            )
            return heatmap_df

        except Exception as e:
            logger.error(f"獲取熱力圖數據錯誤: {e}")
            return None

    def get_peak_hours_analysis(self, days=7):
        """分析高峰時段"""
        df = self.get_hourly_summary(days)
        if df is None or df.empty:
            return None

        # 定義時段
        df["time_period"] = df["hour"].apply(self._categorize_hour)

        # 按時段聚合
        period_stats = (
            df.groupby("time_period")
            .agg(
                {
                    "total_clicks": "sum",
                    "total_impressions": "sum",
                    "unique_queries": "sum",
                    "avg_position": "mean",
                }
            )
            .reset_index()
        )

        return df, period_stats

    def _categorize_hour(self, hour):
        """將小時分類為時段"""
        if 6 <= hour <= 11:
            return "早晨 (6-11)"
        elif 12 <= hour <= 17:
            return "中午 (12-17)"
        elif 18 <= hour <= 23:
            return "晚上 (18-23)"
        else:  # 0-5
            return "深夜 (0-5)"

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
            df["hour"],
            df["total_clicks"],
            color=HOURLY_COLORS["primary"],
            linewidth=4,
            marker="o",
            markersize=8,
            markerfacecolor="white",
            markeredgewidth=3,
            markeredgecolor=HOURLY_COLORS["primary"],
            label="點擊量",
        )

        # 曝光量區域圖
        ax1_twin.fill_between(
            df["hour"],
            df["total_impressions"],
            color=HOURLY_COLORS["secondary"],
            alpha=0.3,
        )
        ax1_twin.plot(
            df["hour"],
            df["total_impressions"],
            color=HOURLY_COLORS["secondary"],
            linewidth=2,
            linestyle="--",
            label="曝光量",
        )

        # 美化主圖
        ax1.set_title(f"24小時搜索表現趨勢 (近{days}天)", fontsize=18, fontweight="bold", pad=20)
        ax1.set_xlabel("小時", fontsize=12, fontweight="bold")
        ax1.set_ylabel("點擊量", fontsize=12, color=HOURLY_COLORS["primary"], fontweight="bold")
        ax1_twin.set_ylabel(
            "曝光量", fontsize=12, color=HOURLY_COLORS["secondary"], fontweight="bold"
        )

        # 設置刻度
        ax1.set_xticks(range(0, 24, 2))
        ax1.grid(True, alpha=0.3)

        # 添加圖例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        # 子圖1：每小時關鍵字數量
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.bar(
            df["hour"],
            df["unique_queries"],
            color=HOURLY_COLORS["accent"],
            alpha=0.8,
            edgecolor="white",
            linewidth=1,
        )
        ax2.set_title("每小時關鍵字數量", fontsize=14, fontweight="bold")
        ax2.set_xlabel("小時")
        ax2.set_ylabel("關鍵字數量")
        ax2.set_xticks(range(0, 24, 2))
        ax2.grid(True, alpha=0.3)

        # 子圖2：每小時平均排名
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(
            df["hour"],
            df["avg_position"],
            color="#e74c3c",
            linewidth=3,
            marker="s",
            markersize=6,
        )
        ax3.fill_between(df["hour"], df["avg_position"], color="#e74c3c", alpha=0.3)
        ax3.set_title("每小時平均排名", fontsize=14, fontweight="bold")
        ax3.set_xlabel("小時")
        ax3.set_ylabel("平均排名")
        ax3.set_xticks(range(0, 24, 2))
        ax3.invert_yaxis()
        ax3.grid(True, alpha=0.3)

        # 統計摘要
        ax4 = fig.add_subplot(gs[2, :])
        ax4.axis("off")

        # 計算統計數據
        peak_hour = df.loc[df["total_clicks"].idxmax()]
        low_hour = df.loc[df["total_clicks"].idxmin()]
        total_clicks = df["total_clicks"].sum()
        total_impressions = df["total_impressions"].sum()

        # 使用純文字格式，避免 emoji 字體問題
        stats_text = f"""
        統計摘要 (近{days}天)

        [高峰] 高峰時段: {peak_hour["hour"]}點 ({peak_hour["total_clicks"]:,}次點擊)
        [低谷] 低谷時段: {low_hour["hour"]}點 ({low_hour["total_clicks"]:,}次點擊)
        [趨勢] 點擊總量: {total_clicks:,}
        [曝光] 曝光總量: {total_impressions:,}
        [關鍵字] 關鍵字總數: {df["unique_queries"].sum():,}
        """

        ax4.text(
            0.05,
            0.5,
            stats_text,
            transform=ax4.transAxes,
            fontsize=12,
            verticalalignment="center",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8),
        )

        # Using constrained_layout instead of tight_layout for better compatibility

        if save_path:
            if not save_path.endswith((".png", ".jpg", ".jpeg", ".pdf")):
                save_path += ".png"

            save_path_obj = Path(save_path)
            if not save_path_obj.parent.exists():
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(
                save_path_obj,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
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
        pivot_clicks = df.pivot(index="date", columns="hour", values="clicks").fillna(0)
        pivot_impressions = df.pivot(index="date", columns="hour", values="impressions").fillna(0)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), constrained_layout=True)

        # 點擊量熱力圖
        sns.heatmap(
            pivot_clicks,
            annot=True,
            fmt=".0f",
            cmap="YlOrRd",
            ax=ax1,
            cbar_kws={"label": "點擊量"},
        )
        ax1.set_title("每日每小時點擊量分布", fontsize=16, fontweight="bold", pad=20)
        ax1.set_xlabel("小時", fontsize=12)
        ax1.set_ylabel("日期", fontsize=12)

        # 曝光量熱力圖
        sns.heatmap(
            pivot_impressions,
            annot=True,
            fmt=".0f",
            cmap="Blues",
            ax=ax2,
            cbar_kws={"label": "曝光量"},
        )
        ax2.set_title("每日每小時曝光量分布", fontsize=16, fontweight="bold", pad=20)
        ax2.set_xlabel("小時", fontsize=12)
        ax2.set_ylabel("日期", fontsize=12)

        # Using constrained_layout instead of tight_layout for better compatibility

        if save_path:
            if not save_path.endswith((".png", ".jpg", ".jpeg", ".pdf")):
                save_path += ".png"

            save_path_obj = Path(save_path)
            if not save_path_obj.parent.exists():
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(
                save_path_obj,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            logger.info(f"🔥 熱力圖已保存到: {save_path}")
            return save_path
        else:
            plt.show()
            return None

    def plot_peak_analysis(self, days=7, save_path=None):
        """繪製高峰時段分析"""
        result = self.get_peak_hours_analysis(days)
        if result is None:
            logger.error("無法獲取高峰分析數據")
            return None

        hourly_df, period_df = result
        if hourly_df is None or period_df is None:
            logger.error("無法獲取高峰分析數據")
            return None

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
            2, 2, figsize=(16, 12), constrained_layout=True
        )

        # 時段點擊量分布
        colors = [
            HOURLY_COLORS["night"],
            HOURLY_COLORS["morning"],
            HOURLY_COLORS["noon"],
            HOURLY_COLORS["evening"],
        ]

        wedges, texts, autotexts = ax1.pie(
            period_df["total_clicks"],
            labels=period_df["time_period"],
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
        )
        ax1.set_title("各時段點擊量分布", fontsize=14, fontweight="bold")

        # 時段曝光量對比
        bars = ax2.bar(
            range(len(period_df)),
            period_df["total_impressions"],
            color=colors,
            alpha=0.8,
            edgecolor="white",
            linewidth=2,
        )
        ax2.set_title("各時段曝光量對比", fontsize=14, fontweight="bold")
        ax2.set_xticks(range(len(period_df)))
        ax2.set_xticklabels(period_df["time_period"], rotation=45)
        ax2.set_ylabel("曝光量")

        # 添加數值標籤
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(
                f"{int(height):,}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # 每小時點擊趨勢（彩虹圖）
        for i, hour in enumerate(hourly_df["hour"]):
            color = (
                colors[0]
                if hour < 6
                else colors[1]
                if hour < 12
                else colors[2]
                if hour < 18
                else colors[3]
            )
            ax3.bar(
                hour,
                hourly_df.iloc[i]["total_clicks"],
                color=color,
                alpha=0.8,
                width=0.8,
            )

        ax3.set_title("24小時點擊量分布", fontsize=14, fontweight="bold")
        ax3.set_xlabel("小時")
        ax3.set_ylabel("點擊量")
        ax3.set_xticks(range(0, 24, 2))

        # 排名表現
        ax4.plot(
            hourly_df["hour"],
            hourly_df["avg_position"],
            color="#e74c3c",
            linewidth=3,
            marker="o",
            markersize=5,
        )
        ax4.fill_between(hourly_df["hour"], hourly_df["avg_position"], color="#e74c3c", alpha=0.3)
        ax4.set_title("24小時平均排名變化", fontsize=14, fontweight="bold")
        ax4.set_xlabel("小時")
        ax4.set_ylabel("平均排名")
        ax4.set_xticks(range(0, 24, 2))
        ax4.invert_yaxis()

        # Using constrained_layout instead of tight_layout for better compatibility

        if save_path:
            if not save_path.endswith((".png", ".jpg", ".jpeg", ".pdf")):
                save_path += ".png"

            save_path_obj = Path(save_path)
            if not save_path_obj.parent.exists():
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(
                save_path_obj,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            logger.info(f"⏰ 高峰分析圖已保存到: {save_path}")
            return save_path
        else:
            plt.show()
            return None

    def generate_hourly_report(self, days=7, output_path="hourly_report.md"):
        """生成每小時數據分析報告"""
        report_parts = []
        summary_df = self.get_hourly_summary(days)

        report_parts.append(f"# 每小時數據分析報告 (最近 {days} 天)")
        report_parts.append(f"報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if summary_df is None or summary_df.empty:
            report_parts.append("\n**沒有足夠的數據生成報告。**")
            Path(output_path).write_text("\n".join(report_parts), encoding="utf-8")
            return

        # 基本統計
        total_records = summary_df["total_records"].sum()
        total_clicks = summary_df["total_clicks"].sum()
        total_impressions = summary_df["total_impressions"].sum()

        report_parts.append("\n## 總體摘要")
        report_parts.append(f"- 總記錄數: {total_records:,}")
        report_parts.append(f"- 總點擊數: {total_clicks:,}")
        report_parts.append(f"- 總曝光數: {total_impressions:,}")

        # 表格數據
        report_parts.append("\n## 每小時詳細數據")
        report_parts.append(summary_df.to_markdown(index=False))

        # 高峰時段分析
        _, period_stats = self.get_peak_hours_analysis(days)
        if period_stats is not None:
            report_parts.append("\n## 高峰時段分析")
            report_parts.append(period_stats.to_markdown(index=False))

        # 寫入文件
        Path(output_path).write_text("\n".join(report_parts), encoding="utf-8")
        logger.info(f"報告已生成: {output_path}")

    def analyze_and_display_coverage(
        self, all_sites: bool = False, site_id: Optional[int] = None, output_csv: bool = False
    ):
        """分析並顯示數據覆蓋率"""

        from ..utils.rich_console import console

        console.print("[bold cyan]🔍 開始分析數據覆蓋率...[/bold cyan]")

        sites_to_check = []
        if all_sites:
            sites_to_check = self.db.get_sites(active_only=True)
        elif site_id:
            site = self.db.get_site_by_id(site_id)
            if site:
                sites_to_check.append(site)

        if not sites_to_check:
            console.print("[yellow]⚠️ 未找到要分析的站點。[/yellow]")
            return

        for site in sites_to_check:
            self._print_coverage_for_site(self.db, site)
            # Future: add data to coverage_results for CSV export

    def _print_coverage_for_site(self, db: Database, site: Dict[str, Any]):
        """為單個站點打印數據覆蓋情況。"""

        from rich.panel import Panel
        from rich.table import Table

        from ..utils.rich_console import console

        console.print(Panel(f"[bold]站點: {site['name']} (ID: {site['id']})[/bold]", expand=False))

        daily_coverage = db.get_daily_data_coverage(site["id"])
        hourly_coverage = db.get_hourly_data_coverage(site["id"])

        table = Table(title="數據覆蓋情況")
        table.add_column("數據類型", style="cyan")
        table.add_column("總記錄數", style="magenta")
        table.add_column("最早日期", style="green")
        table.add_column("最晚日期", style="green")
        table.add_column("覆蓋率", style="yellow")

        if daily_coverage:
            table.add_row(
                "每日數據",
                str(daily_coverage.get("total_records", "N/A")),
                str(daily_coverage.get("first_date", "N/A")),
                str(daily_coverage.get("last_date", "N/A")),
                self._calculate_coverage_percentage(daily_coverage) or "N/A",
            )
        else:
            table.add_row("每日數據", "[red]無[/red]", "N/A", "N/A", "N/A")

        if hourly_coverage:
            table.add_row(
                "每小時數據",
                str(hourly_coverage.get("total_records", "N/A")),
                str(hourly_coverage.get("first_date", "N/A")),
                str(hourly_coverage.get("last_date", "N/A")),
                self._calculate_coverage_percentage(hourly_coverage) or "N/A",
            )
        else:
            table.add_row("每小時數據", "[red]無[/red]", "N/A", "N/A", "N/A")

        console.print(table)

    def _calculate_coverage_percentage(self, coverage_data: Dict[str, Any]) -> Optional[str]:
        """計算並格式化數據覆蓋率百分比"""
        first_date_str = coverage_data.get("first_date")
        last_date_str = coverage_data.get("last_date")
        unique_dates = coverage_data.get("unique_dates", 0)

        if first_date_str and last_date_str and unique_dates > 0:
            try:
                first_date = datetime.strptime(first_date_str, "%Y-%m-%d").date()
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                total_days = (last_date - first_date).days + 1
                percentage = (unique_dates / total_days) * 100 if total_days > 0 else 0
                return f"{percentage:.1f}% ({unique_dates} / {total_days} 天)"
            except (ValueError, TypeError):
                return None
        return None


def _generate_hourly_trends_plot(
    analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None
) -> Optional[str]:
    """生成每小時趨勢圖"""
    try:
        result = analyzer.plot_hourly_trends(days=days, save_path=save_path)
        return result if isinstance(result, str) else None
    except Exception as e:
        logger.error(f"生成每小時趨勢圖失敗: {e}")
        return None


def _generate_hourly_heatmap(
    analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None
) -> Optional[str]:
    """生成每小時熱力圖"""
    try:
        result = analyzer.plot_heatmap(days=days, save_path=save_path)
        return result if isinstance(result, str) else None
    except Exception as e:
        logger.error(f"生成每小時熱力圖失敗: {e}")
        return None


def _generate_peak_analysis_plot(
    analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None
) -> Optional[str]:
    """生成高峰分析圖"""
    try:
        result = analyzer.plot_peak_analysis(days=days, save_path=save_path)
        return result if isinstance(result, str) else None
    except Exception as e:
        logger.error(f"生成高峰分析圖失敗: {e}")
        return None


def _generate_hourly_report(
    analyzer: HourlyAnalyzer, days: int = 7, save_path: Optional[str] = None
) -> Optional[str]:
    """生成每小時報告"""
    try:
        # The analyzer method expects output_path, so we pass save_path to it.
        if save_path is None:
            return None
        result = analyzer.generate_hourly_report(days=days, output_path=save_path)
        return result if isinstance(result, str) else None
    except Exception as e:
        logger.error(f"生成每小時報告失敗: {e}")
        return None


# 分析任務註冊表，方便擴展
ANALYSIS_REGISTRY = {
    "trends": {
        "function": _generate_hourly_trends_plot,
        "type": "plot",
        "filename": "hourly_trends.png",
    },
    "heatmap": {
        "function": _generate_hourly_heatmap,
        "type": "plot",
        "filename": "hourly_heatmap.png",
    },
    "peaks": {
        "function": _generate_peak_analysis_plot,
        "type": "plot",
        "filename": "peak_analysis.png",
    },
    "report": {
        "function": _generate_hourly_report,
        "type": "report",
        "filename": "hourly_report.md",
    },
}


def _fetch_hourly_data_gemini(
    db: Database, days: int, site_url: Optional[str] = None
) -> pd.DataFrame:
    """使用 Database 服務從資料庫獲取每小時數據。"""

    site_id = None
    if site_url:
        site = db.get_site_by_domain(site_url)
        if site:
            site_id = site["id"]
        else:
            logger.warning(f"Gemini Analysis: Site not found for URL {site_url}")
            return pd.DataFrame()

    latest_date = db.get_latest_date_from_table("hourly_rankings", site_id=site_id)
    if not latest_date:
        logger.warning("Gemini Analysis: No hourly data found.")
        return pd.DataFrame()

    start_date = latest_date - timedelta(days=days - 1)

    data = db.get_hourly_rankings(
        site_id=site_id,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=latest_date.strftime("%Y-%m-%d"),
    )

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)


def _generate_hourly_plot_gemini(
    df: pd.DataFrame, output_dir: Path, filename_prefix: str
) -> Optional[Path]:
    """Generates and saves a plot of clicks by hour of the day (Gemini style)."""
    if df.empty:
        return None
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.figure(figsize=(14, 7), constrained_layout=True)
    sns.barplot(
        x="hour",
        y="total_clicks",
        data=df,
        palette="plasma",
        hue="hour",
        dodge=False,
        legend=False,
    )
    plt.title(f"{filename_prefix} - Clicks by Hour of Day (UTC)", fontsize=16, pad=20)
    plt.xlabel("Hour of Day", fontsize=12)
    plt.ylabel("Total Clicks", fontsize=12)
    plt.xticks(range(0, 24))
    # Using constrained_layout instead of tight_layout for better compatibility
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_path = output_dir / f"{filename_prefix}_Hourly_Trends.png"
    plt.savefig(plot_path)
    plt.close()
    return plot_path


def run_hourly_analysis(
    analyzer: HourlyAnalyzer,
    analysis_type: str = "trends",
    days: int = 7,
    output_path: Optional[str] = None,
    include_plots: bool = True,
    plot_save_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    執行每小時數據分析的核心函數。
    :param analyzer: 已經初始化的 HourlyAnalyzer 實例。
    :param analysis_type: 要執行的分析類型 ('trends', 'heatmap', 'peak', 'report', 'coverage')。
    :param days: 分析涵蓋的天數。
    :param output_path: 報告或CSV的輸出路徑。
    :param include_plots: 是否生成圖表。
    :param plot_save_dir: 圖表保存目錄。
    :return: 分析結果字典。
    """
    result: Dict[str, Any] = {"status": "success", "files": [], "errors": []}

    logger.info(f"執行分析類型: {analysis_type}, 最近 {days} 天")

    if analysis_type == "coverage":
        analyzer.analyze_and_display_coverage(all_sites=True)
        return result

    # 檢查數據
    summary_df = analyzer.get_hourly_summary(days=days)
    if summary_df is None or summary_df.empty:
        error_msg = "沒有足夠的每小時數據進行分析。"
        logger.warning(error_msg)
        result["status"] = "failed"
        result["errors"].append(error_msg)
        return result

    if include_plots:
        save_dir = Path(plot_save_dir or config.settings.paths.report_dir)
        save_dir.mkdir(exist_ok=True)

        # 統一文件名前綴
        filename_prefix = f"hourly_{datetime.now().strftime('%Y%m%d')}"

        plot_functions: Dict[str, Callable] = {
            "trends": _generate_hourly_trends_plot,
            "heatmap": _generate_hourly_heatmap,
            "peak": _generate_peak_analysis_plot,
        }

        if analysis_type in plot_functions:
            plot_path = plot_functions[analysis_type](
                analyzer, days, str(save_dir / f"{filename_prefix}_{analysis_type}.png")
            )
            if plot_path:
                result["files"].append(plot_path)
        elif analysis_type == "report":
            # 報告也可能包含圖表
            trends_path = _generate_hourly_trends_plot(
                analyzer, days, str(save_dir / f"{filename_prefix}_trends.png")
            )
            heatmap_path = _generate_hourly_heatmap(
                analyzer, days, str(save_dir / f"{filename_prefix}_heatmap.png")
            )
            if trends_path:
                result["files"].append(trends_path)
            if heatmap_path:
                result["files"].append(heatmap_path)

    if analysis_type == "report":
        report_path = output_path or str(config.settings.paths.report_dir / "hourly_report.md")
        _generate_hourly_report(analyzer, days, report_path)
        result["files"].append(report_path)

    logger.info("分析完成。")
    return result


def run_hourly_analysis_gemini(db: Database, site_url: Optional[str] = None, days: int = 30):
    """
    執行一個簡化的、由 Gemini 啟發的每小時數據分析。
    :param db: Database 服務實例。
    :param site_url: 要分析的單個站點 URL (可選)。
    :param days: 分析天數。
    """

    from ..utils.rich_console import console

    console.print(
        f"[bold blue]🚀 Starting Gemini Hourly Analysis for "
        f"{site_url or 'all sites'}...[/bold blue]"
    )

    # 1. Fetch data using the refactored function
    df = _fetch_hourly_data_gemini(db, days, site_url)

    if df.empty:
        console.print("[yellow]No data to analyze. Exiting.[/yellow]")
        return

    # 2. Generate Plot
    output_dir = config.settings.paths.report_dir
    output_dir.mkdir(exist_ok=True)
    filename_prefix = f"gemini_hourly_{site_url.replace('.', '_') if site_url else 'all'}"
    plot_path = _generate_hourly_plot_gemini(df, output_dir, filename_prefix)

    if plot_path:
        console.print(f"[green]✔ Plot generated successfully at: {plot_path}[/green]")
    else:
        console.print("[red]❌ Failed to generate plot.[/red]")

    # 3. Print summary
    console.print("\n[bold]Data Summary:[/bold]")
    console.print(df.head())


def main():
    """CLI 入口點"""
    parser = argparse.ArgumentParser(description="GSC 每小時數據分析工具")
    parser.add_argument(
        "analysis_type",
        nargs="?",
        default="trends",
        choices=["trends", "heatmap", "peak", "report", "coverage", "gemini"],
        help="要執行的分析類型 (預設: trends)",
    )
    parser.add_argument("--days", type=int, default=7, help="分析最近 N 天的數據 (預設: 7)")
    parser.add_argument("--output", type=str, help="報告或圖表的輸出路徑")
    parser.add_argument("--site-url", type=str, help="針對特定站點URL運行分析 (主要用於 gemini)")
    args = parser.parse_args()

    try:
        from ..containers import Container

        container = Container()
        container.wire(modules=[__name__])

        # For gemini analysis, we pass the db service directly
        if args.analysis_type == "gemini":
            db_service = container.database()
            run_hourly_analysis_gemini(db=db_service, site_url=args.site_url, days=args.days)
            return

        analyzer = container.hourly_performance_analyzer()

        result = run_hourly_analysis(
            analyzer=analyzer,
            analysis_type=args.analysis_type,
            days=args.days,
            output_path=args.output,
        )

        if result["status"] == "success":
            print("\n[bold green]✅ 分析成功完成！[/bold green]")
            if result.get("files"):
                print("生成文件:")
                for f in result["files"]:
                    print(f"- {f}")
        else:
            print("\n[bold red]❌ 分析過程中出現錯誤:[/bold red]")
            if result.get("errors"):
                for err in result["errors"]:
                    print(f"- {err}")

    except Exception as e:
        logger.error(f"分析過程中發生未預期錯誤: {e}", exc_info=True)


if __name__ == "__main__":
    main()
