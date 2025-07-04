#!/usr/bin/env python3
"""
GSC CLI 配置管理模組
集中管理所有路徑、設定和常量
"""

from pathlib import Path
import os

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 目錄路徑
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGS_DIR = PROJECT_ROOT / "logs"
ASSETS_DIR = REPORTS_DIR / "assets"

# 確保目錄存在
DATA_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# 檔案路徑
DB_PATH = DATA_DIR / "gsc_data.db"
LOG_FILE_PATH = LOGS_DIR / "gsc_simple.log"
APP_LOG_PATH = LOGS_DIR / "app.log"
CREDENTIALS_PATH = CONFIG_DIR / "gsc_credentials.json"
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"

# 默認設定
DEFAULT_DAYS = 30
DEFAULT_SITE_URL = None
DEFAULT_OUTPUT_FORMAT = "markdown"

# API 設定
GSC_SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

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

# 環境變量
def get_env_var(key: str, default: str = None) -> str:
    """獲取環境變量，如果不存在則返回默認值"""
    return os.getenv(key, default)

# 動態配置
def get_db_path() -> Path:
    """獲取數據庫路徑，支持環境變量覆蓋"""
    env_db_path = get_env_var('GSC_DB_PATH')
    if env_db_path:
        return Path(env_db_path)
    return DB_PATH

def get_log_path() -> Path:
    """獲取日誌路徑，支持環境變量覆蓋"""
    env_log_path = get_env_var('GSC_LOG_PATH')
    if env_log_path:
        return Path(env_log_path)
    return LOG_FILE_PATH

def get_credentials_path() -> Path:
    """獲取憑證路徑，支持環境變量覆蓋"""
    env_creds_path = get_env_var('GSC_CREDENTIALS_PATH')
    if env_creds_path:
        return Path(env_creds_path)
    return CREDENTIALS_PATH

# 驗證配置
def validate_config() -> bool:
    """驗證配置是否正確"""
    try:
        # 檢查必要目錄
        for dir_path in [DATA_DIR, CONFIG_DIR, REPORTS_DIR, LOGS_DIR]:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
        
        # 檢查數據庫目錄
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        print(f"配置驗證失敗: {e}")
        return False

# 初始化時驗證配置
if __name__ == "__main__":
    validate_config() 