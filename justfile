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

DB_PATH := `poetry run python -c "from src.config import get_settings; print(get_settings().database_path)"`
BACKUP_DIR := "data/backups"

# --- 安裝與核心任務 ---

# # 列出所有可用的指令及其描述。
default:
    @just --list

# # 初始化專案目錄結構和環境檢查。
init:
    @echo "🔧 正在初始化專案環境..."
    @mkdir -p data logs cred
    @echo "✅ 目錄結構已創建"

# # 使用 Poetry 安裝所有專案依賴。
setup:
    @echo "📦 正在安裝專案依賴..."
    @poetry install

# # 首次設定專案 (初始化環境、安裝依賴並進行認證)。
bootstrap: init setup auth
    @echo "🚀 專案設定與認證完成！一切準備就緒。"

# # 執行 Google API 認証流程。
auth:
    @echo "🔐 正在向 Google 進行認證..."
    @echo "⚠️ 請手動設置 Google API 認證憑證到 cred/ 目錄"

# --- 開發環境 ---

# # [別名] 啟動開發伺服器。
dev-server:
    @echo "🧑‍💻 啟動 Litestar 開發模式伺服器 (自動重載) 於 http://127.0.0.1:8000"
    @echo "📊 使用測試數據庫: data/gsc_data.db"
    @GSC_DEV_MODE=1 poetry run uvicorn src.api.app:app --reload --host 127.0.0.1 --port 8000 --log-level debug

# # [別名] 啟動生產伺服器。
prod-server:
    @echo "🚀 啟動 Litestar 生產模式伺服器於 http://0.0.0.0:8000"
    @poetry run uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# --- 網站與資料同步 ---

# # 從本地資料庫列出所有網站。
site-list:
    @poetry run python sync.py list

# # 為特定網站在指定天數內同步資料。 用法: `just sync-site <site_id> [days] [sync_mode]`
# # sync_mode: skip (預設，跳過已存在) | overwrite (覆蓋已存在，用於修正)
sync-site site_id days='7' sync_mode='skip':
    @poetry run python sync.py sync {{ site_id }} {{ days }} {{ sync_mode }}

# # 批次同步多個網站 (順序執行)。 用法: `just sync-multiple "1,2,3" [days] [sync_mode]`
# # sync_mode: skip (預設) | overwrite (覆蓋模式)
# # 注意：GSC API 不支持並發，必須順序執行
sync-multiple site_ids days='7' sync_mode='skip':
    @poetry run python sync_multiple.py "{{ site_ids }}" {{ days }} {{ sync_mode }}

# # 為特定網站同步每小時資料。 用法: `just sync-hourly <site_id> [days] [sync_mode]`
# # 注意：GSC API 限制每小時資料只能取得最近 10 天
sync-hourly site_id days='2' sync_mode='skip':
    @poetry run python sync_hourly.py sync {{ site_id }} {{ days }} {{ sync_mode }}

# # 批次同步多個網站的每小時資料。 用法: `just sync-hourly-multiple "1,2,3" [days] [sync_mode]`
# # days: 1-10 (預設: 2)
# # sync_mode: skip (預設) | overwrite (覆蓋模式)
sync-hourly-multiple site_ids days='2' sync_mode='skip':
    @poetry run python sync_hourly_multiple.py "{{ site_ids }}" {{ days }} {{ sync_mode }}

# # 查看網站同步狀態。 用法: `just sync-status [site_id]`
sync-status site_id='':
    @if [ -z "{{ site_id }}" ]; then \
        echo "📊 所有網站同步狀態:"; \
        poetry run python -c "import asyncio; from src.database.hybrid import HybridDataStore; async def main(): db = HybridDataStore(); await db.initialize(); sites = await db.get_sites(); print('\\n網站列表:'); [print(f'{s.id:3d}: {s.name} ({s.domain})') for s in sites]; await db.close(); asyncio.run(main())"; \
    else \
        echo "📊 網站 {{ site_id }} 同步狀態:"; \
        poetry run python -c "import asyncio; from src.database.hybrid import HybridDataStore; from datetime import datetime, timedelta; async def main(): db = HybridDataStore(); await db.initialize(); site = await db.get_site_by_id({{ site_id }}); print(f'\\n網站: {site.name if site else \"未找到\"}'); coverage = await db.get_sync_coverage({{ site_id }}, 30) if site else {}; synced = sum(1 for v in coverage.values() if v); print(f'最近 30 天已同步: {synced}/30 天'); await db.close(); asyncio.run(main())"; \
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
    @poetry run ruff check . --fix
    @poetry run ruff format .

# # 使用 pytest 執行測試套件。
test:
    @echo "🧪 正在使用 pytest 執行測試..."
    @poetry run pytest

# # 使用 pytest 並行執行測試套件（可能在某些情況下會卡住）。
test-parallel:
    @echo "🧪 正在使用 pytest 並行執行測試..."
    # -n auto: 使用 pytest-xdist 並行執行
    @poetry run pytest -n auto

# # 執行 mypy 類型檢查器。
type-check:
    @echo "🔍 正在執行 mypy 類型檢查..."
    @poetry run mypy src/

# --- 工具與危險任務 ---

# # 列出最大的備份檔案。 用法: `just list-large-backups [count]`
list-large-backups count='5':
    @echo "📊 正在列出 '{{ BACKUP_DIR }}' 中最大的 {{ count }} 個備份檔案..."
    @# du: 磁碟使用量, -h: 人類可讀。 sort: -r 反向, -h 人類數字。 head: 前 N 個。
    @du -h "{{ BACKUP_DIR }}"/gsc_data_backup_*.db.gz 2>/dev/null | sort -rh | head -n {{ count }}

# --- API 測試 ---

# # 測試 API 健康檢查端點
api-health:
    @curl -s http://localhost:8000/health | jq .

# # 列出所有站點
api-sites:
    @curl -s http://localhost:8000/api/v1/sites | jq .

# # 獲取特定站點資訊。用法: `just api-site 1`
api-site site_id:
    @curl -s http://localhost:8000/api/v1/sites/{{ site_id }} | jq .

# # 查看站點同步狀態（使用 hostname）。用法: `just api-sync-status-hostname businessfocus.io`
api-sync-status-hostname hostname:
    @curl -s "http://localhost:8000/api/v1/sync/status?hostname={{ hostname }}&days=30" | jq .

# # 查看站點同步狀態（使用 site_id）。用法: `just api-sync-status-id 1`
api-sync-status-id site_id:
    @curl -s "http://localhost:8000/api/v1/sync/status?site_id={{ site_id }}&days=30" | jq .

# # 測試查詢搜索（使用 hostname）。用法: `just api-query-search businessfocus.io 理髮`
api-query-search hostname search_term:
    @curl -s -X POST http://localhost:8000/api/v1/analytics/ranking-data \
        -H "Content-Type: application/json" \
        -d '{"hostname": "{{ hostname }}", "date_from": "2025-01-01", "date_to": "2025-07-25", "queries": ["{{ search_term }}"], "exact_match": false, "group_by": ["query"], "limit": 10}' | jq .

# # 測試頁面關鍵詞性能（使用 hostname）。用法: `just api-page-performance businessfocus.io`
api-page-performance hostname:
    @curl -s -X POST http://localhost:8000/api/v1/page-keyword-performance/ \
        -H "Content-Type: application/json" \
        -d '{"hostname": "{{ hostname }}", "days": 30}' | jq .

just-check:
    @echo "🔍 正在檢查 justfile 格式..."
    # @just --unstable --fmt
