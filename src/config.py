#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GSC CLI 設定管理 - 使用 Pydantic Settings 和 TOML 配置

這個模組提供了一個統一的設定管理系統，支援：
- 環境變數覆蓋
- TOML 配置檔案
- 型別驗證和轉換
- 嵌套設定結構
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import toml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .utils.rich_console import console

# --- 常數 ---
GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters"]

# --- 路徑設定 ---
CONFIG_DIR = Path.home() / ".config" / "gsc-db"
CONFIG_FILE_PATH = CONFIG_DIR / "config.toml"

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
    """日誌相關設定"""

    file_path: str = "gsc-cli.log"
    level_file: str = "DEBUG"
    level_console: str = "INFO"
    max_bytes: int = 5 * 1024 * 1024  # 每個日誌檔案最大 5 MB
    backup_count: int = 3


class RetrySettings(BaseModel):
    """API 請求重試相關設定"""

    attempts: int = 3
    wait_min_seconds: int = 4
    wait_max_seconds: int = 10


class SyncSettings(BaseModel):
    """資料同步相關設定"""

    max_workers: int = 4


class GscSettings(BaseModel):
    scopes: list[str] = Field(default=["https://www.googleapis.com/auth/webmasters.readonly"])


class Settings(BaseSettings):
    """
    定義應用程式的所有設定。
    Pydantic 會自動從 .env 檔案或環境變數中讀取這些值。
    """

    # 應用程式環境
    APP_ENV: str = "development"

    # 日誌設定
    log: LogSettings = LogSettings()
    retry: RetrySettings = RetrySettings()
    sync: SyncSettings = SyncSettings()

    # 路徑設定 (從 toml 載入)
    paths: PathSettings

    # 告訴 Pydantic 從名為 .env 的檔案中讀取設定
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_nested_delimiter="__"
    )


# --- 3. 載入並合併設定的函式 ---
def load_toml_config(config_file: str | Path = "config.toml") -> dict:
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
    return config_data


def initialize_settings() -> Settings:
    """初始化並載入所有設定。"""
    toml_config = load_toml_config()
    return Settings(paths=PathSettings(**toml_config["paths"]))


# 創建一個全域可用的設定實例
settings = initialize_settings()


# --- 日誌設定 ---
def setup_logging():
    """
    根據設定檔配置日誌系統，將日誌同時輸出到 Rich Console 和一個可輪替的日誌檔案中。
    """
    from pathlib import Path

    # 1. 檔案處理器 (File Handler)
    # 確保日誌目錄存在
    log_file = Path(settings.log.file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=settings.log.max_bytes,
        backupCount=settings.log.backup_count,
        encoding="utf-8",
    )
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(settings.log.level_file.upper())

    # 2. Rich 終端處理器 (Console Handler)
    from rich.logging import RichHandler

    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=False,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(settings.log.level_console.upper())

    # 3. 獲取根 logger，設定最低級別並添加 handlers
    # 清除任何可能由 uvicorn 等庫預先配置的 handlers
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.setLevel(logging.DEBUG)  # 根 logger 級別設為 DEBUG，由 handlers 各自過濾
    root_logger.addHandler(file_handler)
    root_logger.addHandler(rich_handler)


# --- 為了向後相容，保留舊的變數名稱 ---
CLIENT_SECRET_PATH = settings.paths.config_dir / "client_secret.json"


def get_db_path() -> Path:
    """獲取資料庫檔案的路徑。"""
    return settings.paths.database_path


def get_credentials_path() -> Path:
    """獲取憑證檔案的路徑。"""
    return settings.paths.config_dir / "credentials.json"
