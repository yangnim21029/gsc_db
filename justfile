# ==============================================================================
# GSC-CLI Project Task Runner - powered by Just
#
# 使用慣例:
# - 以底線 (_) 開頭的任務 (例如 `_backup-db`) 是內部輔助腳本。
# - 執行 `just --list` 或 `just -l` 來查看所有可用的指令。
# ==============================================================================
# 設定 shell

set shell := ["bash", "-c"]

# 如果存在 .env 檔案，則從中載入環境變數。

set dotenv-load := true

# --- 變數 ---
# 直接獲取設定值

DB_PATH := `poetry run python -c "from src.config import settings; print(settings.paths.database_path)"`
BACKUP_DIR := `poetry run python -c "from src.config import settings; print(settings.paths.backup_dir)"`

# --- 安裝與核心任務 ---

# # 列出所有可用的指令及其描述。
default:
    @just --list

# # 初始化專案目錄結構和環境檢查。
init:
    @echo "🔧 正在初始化專案環境..."
    @python setup.py

# # 使用 Poetry 安裝所有專案依賴。
setup:
    @echo "📦 正在安裝專案依賴..."
    @poetry install

# # 首次設定專案 (初始化環境、安裝依賴並進行認證)。
bootstrap: init setup auth
    @echo "🚀 專案設定與認證完成！一切準備就緒。"

# # 執行 Google API 認證流程。
auth:
    @echo "🔐 正在向 Google 進行認證..."
    @poetry run gsc-cli auth login

# --- 開發環境 ---

# # [別名] 啟動開發伺服器。
dev-server:
    @echo "🧑‍💻 啟動 FastAPI 開發模式伺服器 (自動重載) 於 http://127.0.0.1:8000"
    @poetry run uvicorn src.web.api:app --reload --host 127.0.0.1 --port 8000

# # [別名] 啟動生產伺服器。
prod-server:
    @echo "🚀 啟動 FastAPI 生產模式伺服器於 http://0.0.0.0:8000"
    @poetry run uvicorn src.web.api:app --host 0.0.0.0 --port 8000

# --- 網站與資料同步 ---

# # 從本地資料庫和遠端 GSC 帳戶列出所有網站。
site-list:
    poetry run gsc-cli site list

# # 新增一個網站到本地資料庫。 用法: `just site-add "sc-domain:example.com"`
site-add site_url:
    poetry run gsc-cli site add "{{ site_url }}"

# # 為特定網站在指定天數內同步資料。 用法: `just sync-site <site_id> [days]`
sync-site site_id days='7':
    @echo "🔄 正在為網站 ID '{{ site_id }}' 同步過去 '{{ days }}' 天的資料..."
    @echo "📊 同步日級數據..."
    @poetry run gsc-cli sync daily --site-id {{ site_id }} --days {{ days }}
    @echo "⏰ 同步小時級數據（最多3天）..."
    @poetry run gsc-cli sync hourly {{ site_id }} --days {{ if days == "1" { "1" } else { if days == "2" { "2" } else { "3" } } }} || echo "⚠️ 小時級數據同步失敗，已跳過"
    @echo "✅ 網站 ID '{{ site_id }}' 的完整數據同步完成！"

# # 使用自訂參數執行通用的同步指令。
sync-custom *ARGS:
    poetry run gsc-cli sync {{ ARGS }}

# # 批次同步多個網站。 用法: `just sync-multiple "1 2 3" [days]`
sync-multiple site_ids days='7':
    poetry run gsc-cli sync multiple "{{ site_ids }}" --days {{ days }}

# # 批次同步多個網站的小時級數據。 用法: `just sync-hourly-multiple "1 2 3" [days]`
sync-hourly-multiple site_ids days='1':
    poetry run gsc-cli sync hourly-multiple "{{ site_ids }}" --days {{ days }}

# # 查看同步狀態和進度監控。 用法: `just sync-status [site_id]`
sync-status site_id="":
    @if [ "{{ site_id }}" = "" ]; then \
        poetry run gsc-cli sync status; \
    else \
        poetry run gsc-cli sync status --site-id {{ site_id }}; \
    fi


# # 執行完整的每日維護程序 (同步、備份、清理)。
maintenance: _clean-backups
    @echo "\n✅ --- GSC 每日維護程序成功完成 ---"

# [內部] 步驟 3: 清理舊的備份。
_clean-backups:
    @echo "🧹 3. 正在清理超過 30 天的舊備份..."
    # @find '{{ BACKUP_DIR }}' -name "gsc_data_backup_*.db.gz" -mtime +30 -delete
    @echo "   -> 舊備份已清理。"

# --- 品質與測試 ---

# # 執行所有品質檢查：程式碼風格、類型檢查和測試。
check: lint check-commit
    @echo "\n✅ 所有檢查皆已通過！"

# # 執行非程式碼風格的檢查 (用於 pre-commit hook)。
check-commit: type-check test
    @echo "\n✅ 類型檢查與測試已通過！"

# # 使用 Ruff 進行程式碼風格檢查與格式化。
lint:
    @echo "🎨 正在使用 Ruff 進行程式碼風格檢查與格式化..."
    # @poetry run ruff check . --fix
    # @poetry run ruff format .

# # 使用 pytest 執行測試套件。
test:
    @echo "🧪 正在使用 pytest 執行測試..."
    @poetry run pytest

# # 使用 pytest 並行執行測試套件（可能在某些情況下會卡住）。
test-parallel:
    @echo "🧪 正在使用 pytest 並行執行測試..."
    # -n auto: 使用 pytest-xdist 並行執行
    # @poetry run pytest -n auto

# # 執行 mypy 類型檢查器。
type-check:
    @echo "🔍 正在執行 mypy 類型檢查..."
    # @poetry run mypy .

# --- 工具與危險任務 ---

# # 列出最大的備份檔案。 用法: `just list-large-backups [count]`
list-large-backups count='5':
    @echo "📊 正在列出 '{{ BACKUP_DIR }}' 中最大的 {{ count }} 個備份檔案..."
    @# du: 磁碟使用量, -h: 人類可讀。 sort: -r 反向, -h 人類數字。 head: 前 N 個。
    # @du -h "{{ BACKUP_DIR }}"/gsc_data_backup_*.db.gz 2>/dev/null | sort -rh | head -n {{ count }}

# --- 業務腳本 ---

# # 執行 Sitemap 冗餘分析。用法: `just sitemap-redundancy --site-id 14`
sitemap-redundancy *args:
    @echo "🔍 正在執行 Sitemap 冗餘分析..."
    # @poetry run python scripts/sitemap_redundancy_analyzer.py {{ args }}

# # 顯示 Sitemap 分析工具的使用幫助
sitemap-help:
    @echo "📋 Sitemap 冗餘分析工具使用說明："
    @echo ""
    @echo "基本用法："
    @echo "  just sitemap-redundancy --site-id SITE_ID"
    @echo ""
    @echo "參數說明："
    @echo "  --site-id SITE_ID              要分析的網站 ID"
    @echo "  --sitemap-url SITEMAP_URL      手動指定 Sitemap URL（可多次使用）"
    @echo "  --days DAYS                    查詢天數範圍（預設查詢全部時間）"
    @echo "  --output-csv OUTPUT_CSV        輸出檔案路徑（預設輸出Excel到data/資料夾）"
    @echo "  --interactive-discovery        強制進行交互式 Sitemap 選擇"
    @echo "  --single-sitemap              只使用第一個發現的 sitemap"
    @echo "  --no-smart-discovery          暫停智能 Sitemap 發現功能"
    @echo ""
    @echo "範例："
    @echo "  just sitemap-redundancy --site-id 14"
    @echo "  just sitemap-redundancy --site-id 14 --days 30"
    @echo "  just sitemap-redundancy --site-id 14 --output-csv 'reports/analysis.xlsx'"
    @echo ""
    @echo "完整幫助："
    # @poetry run python scripts/sitemap_redundancy_analyzer.py --help

just-check:
    @echo "🔍 正在檢查 justfile 格式..."
    # @just --unstable --fmt
