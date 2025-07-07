# ==============================================================================
# GSC-CLI Project Task Runner - powered by Just
#
# 使用慣例:
# - 以底線 (_) 開頭的任務 (例如 `_backup-db`) 是內部輔助腳本。
# - 執行 `just --list` 或 `just -l` 來查看所有可用的指令。
# ==============================================================================

# 設定 shell 為 bash，以獲得更強大且一致的腳本功能。
set shell := ["bash", "-c"]

# 如果存在 .env 檔案，則從中載入環境變數。
set dotenv-load

# --- 變數 ---
# 透過一次 Python 呼叫獲取所有設定值，以減少 `poetry run` 的開銷。
_CONFIG       := `poetry run python -c "from src.config import settings; print(f'{settings.paths.database_path}\\n{settings.paths.backup_dir}')"`
DB_PATH       := `echo "{{_CONFIG}}" | head -n 1`
BACKUP_DIR    := `echo "{{_CONFIG}}" | tail -n 1`
BACKUP_PREFIX := "gsc_data_backup"


# --- 安裝與核心任務 ---

## 列出所有可用的指令及其描述。
default:
    @just --list

## 使用 Poetry 安裝所有專案依賴。
setup:
    @echo "📦 正在安裝專案依賴..."
    @poetry install

## 首次設定專案 (安裝依賴並進行認證)。
bootstrap: setup auth
    @echo "🚀 專案設定與認證完成！一切準備就緒。"

## 執行 Google API 認證流程。
auth:
    @echo "🔐 正在向 Google 進行認證..."
    @poetry run gsc-cli auth login


# --- 開發環境 ---

## [別名] 啟動開發伺服器。
dev-server:
    @echo "🧑‍💻 啟動 FastAPI 開發模式伺服器 (自動重載) 於 http://127.0.0.1:8000"
    @poetry run uvicorn src.web.api:app --reload --host 127.0.0.1 --port 8000

## [別名] 啟動生產伺服器。
prod-server:
    @echo "🚀 啟動 FastAPI 生產模式伺服器於 http://0.0.0.0:8000"
    @poetry run uvicorn src.web.api:app --host 0.0.0.0 --port 8000


# --- 網站與資料同步 ---

## 從本地資料庫和遠端 GSC 帳戶列出所有網站。
site-list:
    poetry run gsc-cli site list

## 新增一個網站到本地資料庫。 用法: `just site-add "sc-domain:example.com"`
site-add site_url:
    poetry run gsc-cli site add "{{site_url}}"

## 為特定網站在指定天數內同步資料。 用法: `just sync-site <site_id> [days]`
sync-site site_id days='7':
    @echo "🔄 正在為網站 ID '{{site_id}}' 同步過去 '{{days}}' 天的資料..."
    poetry run gsc-cli sync daily --site-id {{site_id}} --days {{days}}

## 迴圈同步多個網站。 用法: `just sync-multiple "1 3 5"`
sync-multiple site_list:
    #!/bin/bash
    echo "🚀 開始批次同步網站: [{{site_list}}]"
    for site in {{site_list}}; do
        echo "---"
        echo "🔄 正在為網站 ID '$site' 同步過去 '7' 天的資料..."
        poetry run gsc-cli sync daily --site-id $site --days 7
    done
    echo "✅ 所有指定網站的批次同步已完成。"

## 使用自訂參數執行通用的同步指令。
sync-custom *ARGS:
    poetry run gsc-cli sync {{ARGS}}


# --- 維護程序 ---

## 執行完整的每日維護程序 (同步、備份、清理)。
maintenance: _sync-daily _backup-db _clean-backups
    @echo "\n✅ --- GSC 每日維護程序成功完成 ---"

# [內部] 步驟 1: 為所有網站執行每日資料同步 (最近 2 天)。
_sync-daily:
    @echo "🔄 1. 正在為所有網站執行每日資料同步 (最近 2 天)..."
    @poetry run gsc-cli sync daily --all-sites --days 2

# [內部] 步驟 2: 備份資料庫。
_backup-db:
    @echo "📦 2. 正在備份資料庫..."
    @mkdir -p '{{BACKUP_DIR}}'
    @# 為此腳本的執行定義和使用 shell 變數
    @TIMESTAMP=$$(date +"%Y-%m-%d_%H%M%S"); \
    TEMP_BACKUP="{{BACKUP_DIR}}/temp_backup.db"; \
    BACKUP_FILE="{{BACKUP_DIR}}/{{BACKUP_PREFIX}}_$$TIMESTAMP.db.gz"; \
    ( \
        echo "   -> 正在建立臨時備份檔..."; \
        sqlite3 '{{DB_PATH}}' ".backup '$$TEMP_BACKUP'" && \
        echo "   -> 正在將備份壓縮至 $$BACKUP_FILE..."; \
        gzip -c "$$TEMP_BACKUP" > "$$BACKUP_FILE" \
    ) || (echo "❌ 錯誤：資料庫備份失敗。" >&2; exit 1); \
    echo "   -> 正在清理臨時檔案..."; \
    rm -f "$$TEMP_BACKUP"

# [內部] 步驟 3: 清理舊的備份。
_clean-backups:
    @echo "🧹 3. 正在清理超過 30 天的舊備份..."
    @find '{{BACKUP_DIR}}' -name "{{BACKUP_PREFIX}}_*.db.gz" -mtime +30 -delete
    @echo "   -> 舊備份已清理。"


# --- 品質與測試 ---

## 執行所有品質檢查：程式碼風格、類型檢查和測試。
check: lint check-commit
    @echo "\n✅ 所有檢查皆已通過！"

## 執行非程式碼風格的檢查 (用於 pre-commit hook)。
check-commit: type-check test
    @echo "\n✅ 類型檢查與測試已通過！"

## 使用 Ruff 進行程式碼風格檢查與格式化。
lint:
    @echo "🎨 正在使用 Ruff 進行程式碼風格檢查與格式化..."
    @poetry run ruff check . --fix
    @poetry run ruff format .

## 使用 pytest 執行測試套件。
test:
    @echo "🧪 正在使用 pytest 執行測試..."
    @poetry run pytest

## 使用 pytest 並行執行測試套件（可能在某些情況下會卡住）。
test-parallel:
    @echo "🧪 正在使用 pytest 並行執行測試..."
    # -n auto: 使用 pytest-xdist 並行執行
    @poetry run pytest -n auto

## 執行 mypy 類型檢查器。
type-check:
    @echo "🔍 正在執行 mypy 類型檢查..."
    @poetry run mypy .


# --- 工具與危險任務 ---

## 列出最大的備份檔案。 用法: `just list-large-backups [count]`
list-large-backups count='5':
    @echo "📊 正在列出 '{{BACKUP_DIR}}' 中最大的 {{count}} 個備份檔案..."
    @# du: 磁碟使用量, -h: 人類可讀。 sort: -r 反向, -h 人類數字。 head: 前 N 個。
    @du -h "{{BACKUP_DIR}}"/{{BACKUP_PREFIX}}_*.db.gz 2>/dev/null | sort -rh | head -n {{count}}

## [危險] 清除整個專案 (刪除資料庫與所有備份)。 別名: `nuke`
clean-all:
    @echo "⚠️ 警告：此操作將永久刪除資料庫 ('{{DB_PATH}}') 以及 '{{BACKUP_DIR}}' 中的所有備份。"
    @read -p "您確定要繼續嗎？ (y/N) " -n 1 -r
    @echo # 換行
    @if [[ $REPLY =~ ^[Yy]$ ]]; then \
        echo "正在執行清理作業..."; \
        rm -f '{{DB_PATH}}'; \
        rm -rf '{{BACKUP_DIR}}'; \
        echo "✅ 所有專案資料已被清除。"; \
    else \
        echo "操作已被使用者中止。"; \
        exit 1; \
    fi

## [別名] `clean-all` 任務的另一個名稱。
nuke: clean-all
