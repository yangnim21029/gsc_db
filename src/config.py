"""
應用程式配置管理模組

使用 TOML 作為預設設定檔，並允許透過 .env 檔案進行覆寫。
使用 Pydantic 進行類型驗證和設定管理。
"""

import os
from pathlib import Path

import toml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# --- 1. 定義常數並載入 .env ---
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# --- 2. 定義 Pydantic 模型以進行驗證 ---
class PathSettings(BaseModel):
    data_dir: Path
    log_dir: Path
    report_dir: Path
    config_dir: Path
    backup_dir: Path  # 新增備份目錄
    database_path: Path


class LogSettings(BaseModel):
    level: str = "INFO"


class GscSettings(BaseModel):
    scopes: list[str] = Field(default=["https://www.googleapis.com/auth/webmasters.readonly"])


class AppConfig(BaseModel):
    paths: PathSettings
    logging: LogSettings
    gsc: GscSettings
    app_env: str = Field(default="production")

    @property
    def db_path(self) -> Path:
        return self.paths.database_path

    @property
    def backup_dir(self) -> Path:
        return self.paths.backup_dir

    @property
    def log_dir(self) -> Path:
        return self.paths.log_dir


# --- 3. 載入並合併設定的函式 ---
def load_config() -> AppConfig:
    """從 TOML 載入設定，用環境變數覆寫，並進行驗證。"""
    # 載入 TOML 預設設定
    config_path = BASE_DIR / "config.toml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = toml.load(f)

    # 將相對路徑解析為絕對路徑
    for key, value in config_data.get("paths", {}).items():
        config_data["paths"][key] = BASE_DIR / value

    # 從環境變數覆寫設定
    if env_app_env := os.getenv("APP_ENV"):
        config_data["app_env"] = env_app_env
    if env_log_level := os.getenv("LOG_LEVEL"):
        config_data["logging"]["level"] = env_log_level

    # 組合最終的資料庫路徑
    db_name = config_data.get("database", {}).get("default_db_name", "gsc.db")
    config_data["paths"]["database_path"] = config_data["paths"]["data_dir"] / db_name

    # 處理 GSC scopes
    if "gsc" not in config_data:
        config_data["gsc"] = {}

    # 使用 Pydantic 進行驗證
    validated_config = AppConfig(**config_data)

    # 確保所有目錄都存在
    for path in validated_config.paths.model_dump().values():
        if isinstance(path, Path) and not path.suffix:  # 檢查是否為目錄
            path.mkdir(parents=True, exist_ok=True)

    return validated_config


# --- 4. 建立一個全域單例，供應用程式其他部分匯入 ---
settings = load_config()

# --- 為了向後相容，保留舊的變數名稱 ---
DB_PATH = settings.db_path
LOG_DIR = settings.log_dir
DATA_DIR = settings.paths.data_dir
CONFIG_DIR = settings.paths.config_dir
GSC_SCOPES = settings.gsc.scopes


# --- 向後相容的函數 ---
def get_credentials_path() -> Path:
    """獲取憑證文件路徑"""
    return settings.paths.config_dir / "credentials.json"


def get_db_path() -> Path:
    """獲取資料庫路徑"""
    return settings.db_path


# --- 向後相容的常數 ---
CLIENT_SECRET_PATH = settings.paths.config_dir / "client_secret.json"
