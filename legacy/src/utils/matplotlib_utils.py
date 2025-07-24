import logging

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Duolingo Inspired Colors
DUOLINGO_COLORS = {
    "blue": "#1cb0f6",
    "green": "#58a700",
    "red": "#ff4b4b",
    "orange": "#ff9600",
    "purple": "#885dd8",
    "yellow": "#ffc800",
    "gray": "#afafaf",
}


def set_chinese_font():
    """
    設置 Matplotlib 以支持中文顯示。
    會嘗試查找系統中的中文字體，如果找不到，則會發出警告。
    """
    try:
        # 優先級高的字體列表
        font_preferences = [
            "PingFang HK",
            "PingFang SC",
            "PingFang TC",
            "Microsoft YaHei",
            "Heiti TC",
            "Heiti SC",
            "SimHei",
            "Arial Unicode MS",
        ]

        system_fonts = fm.findSystemFonts(fontpaths=None, fontext="ttf")

        for font_name in font_preferences:
            for font_path in system_fonts:
                if font_name in font_path:
                    fm.fontManager.addfont(font_path)
                    plt.rcParams["font.family"] = font_name
                    plt.rcParams["axes.unicode_minus"] = False  # 解決負號顯示問題
                    logger.info(f"成功設置中文字體: {font_name}")
                    return

        logger.warning(
            "未找到推薦的中文字體 (如 PingFang, Microsoft YaHei)。圖表中的中文可能無法正常顯示。"
        )

    except Exception as e:
        logger.error(f"設置中文字體時發生錯誤: {e}")
