#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集中化配置管理模塊。
支持多環境配置 (development, production)。
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# 從 .env 文件加載環境變量 (如果存在)
load_dotenv()

# --- 核心路徑 ---
# 專案根目錄 (src 的上一層)
BASE_DIR = Path(__file__).resolve().parents[1]

# --- 環境配置 ---
# 獲取應用環境，默認為 'development'
APP_ENV = os.getenv('APP_ENV', 'development')

# --- GSC API 配置 ---
# 修正：使其與 credentials.json 中已授權的範圍完全一致，以解決 invalid_scope 錯誤
GSC_SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# --- 根據環境設置路徑 ---
if APP_ENV == 'production':
    # 生產環境路徑 (例如，在 /var/data 中)
    DATA_DIR = Path(os.getenv('GSC_DATA_DIR', '/var/data/gsc_db'))
    LOGS_DIR = Path(os.getenv('GSC_LOGS_DIR', '/var/log/gsc_db'))
else:
    # 開發環境路徑 (在專案目錄內)
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"

# --- 確保核心目錄存在 ---
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# --- 靜態路徑配置 ---
CONFIG_DIR = BASE_DIR / "config"
ASSETS_DIR = BASE_DIR / "assets"
REPORTS_DIR = BASE_DIR / "reports"

DB_PATH = DATA_DIR / "gsc_data.db"
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"

# --- 動態路徑函數 (保持向後兼容) ---
def get_db_path() -> Path:
    """返回數據庫文件的完整路徑。"""
    return Path(os.getenv('GSC_DB_PATH', DB_PATH))

def get_credentials_path() -> Path:
    """返回存儲憑證文件的路徑。"""
    return Path(os.getenv('GSC_CREDENTIALS_PATH', CREDENTIALS_PATH))

# 默認設定
DEFAULT_DAYS = 7
DEFAULT_SITEMAP_URL = None
DEFAULT_REPORTS_DIR = REPORTS_DIR

# API 相關
GSC_API_VERSION = 'v1'
GSC_DISCOVERY_URL = 'https://www.googleapis.com/discovery/v1/apis/webmasters/v3/rest'

# 系統健康檢查相關
HEALTH_CHECK_URLS = [
    "https://www.google.com",
    "https://analytics.google.com",
]
HEALTH_CHECK_TIMEOUT = 10

# 日誌設定
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# 圖表設定
DEFAULT_DPI = 300
DEFAULT_FIGSIZE = (12, 8)
DEFAULT_COLORMAP = 'viridis'

# 數據庫設定
DB_TIMEOUT = 30
DB_CHECK_SAME_THREAD = False

# 報告設定
REPORT_TEMPLATES = {
    'monthly': {'days': 30, 'title': '月度報告'},
    'weekly': {'days': 7, 'title': '週度報告'},
    'daily': {'days': 1, 'title': '日度報告'},
    'keyword': {'days': 30, 'title': '關鍵字專項報告'},
    'page': {'days': 30, 'title': '頁面表現報告'}
}

# 每小時分析設定
HOURLY_ANALYSIS_TYPES = ['trends', 'heatmap', 'peaks', 'report', 'all']