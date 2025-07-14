# ==============================================================================
# GSC-CLI Project Task Runner - powered by Just
#
# 使用慣例:
# - 以底線 (_) 開頭的任務 (例如 `_backup-db`) 是內部輔助腳本。
# - 執行 `just --list` 或 `just -l` 來查看所有可用的指令。
# ==============================================================================

# 設定 shell，對 Windows 和 Unix 系統提供相容性
set shell := ["bash", "-c"]

# 如果存在 .env 檔案，則從中載入環境變數。
set dotenv-load

# --- 變數 ---
# 直接獲取設定值
DB_PATH    := `poetry run python -c "from src.config import settings; print(settings.paths.database_path)"`
BACKUP_DIR := `poetry run python -c "from src.config import settings; print(settings.paths.backup_dir)"`


# --- 安裝與核心任務 ---

## 列出所有可用的指令及其描述。
default:
    @just --list

## 初始化專案目錄結構和環境檢查。
init:
    @echo "🔧 正在初始化專案環境..."
    @python setup.py

## 使用 Poetry 安裝所有專案依賴。
setup:
    @echo "📦 正在安裝專案依賴..."
    @poetry install

## 首次設定專案 (初始化環境、安裝依賴並進行認證)。
bootstrap: init setup auth
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
    @echo "📊 第1步：同步日級數據..."
    @poetry run gsc-cli sync daily --site-id {{site_id}} --days {{days}} --max-workers 2
    @{{ if os() == "windows" { `
        $hourlyDays = [Math]::Min([int]"{{days}}", 3);
        Write-Host "⏰ 第2步：同步小時級數據（過去 $hourlyDays 天）...";
        try {
            poetry run gsc-cli sync hourly {{site_id}} --days $hourlyDays;
        } catch {
            Write-Host "⚠️ 小時級數據同步失敗，已跳過";
        }
    ` } else { `
        HOURLY_DAYS=$([ "{{days}}" -gt "3" ] && echo "3" || echo "{{days}}")
        echo "⏰ 第2步：同步小時級數據（過去 $HOURLY_DAYS 天）..."
        poetry run gsc-cli sync hourly {{site_id}} --days $HOURLY_DAYS || echo "⚠️ 小時級數據同步失敗，已跳過"
    ` } }}
    @echo "✅ 網站 ID '{{site_id}}' 的完整數據同步完成！"

## 迴圈同步多個網站。 用法: `just sync-multiple "1 3 5" [days]`
sync-multiple site_list days='7':
    #!/usr/bin/env bash
    echo "🚀 開始批次同步網站: [{{site_list}}] ({{days}} 天)"
    sites=({{site_list}})
    success_count=0
    failure_count=0
    failed_sites=()

    echo "📊 共需同步 ${#sites[@]} 個網站"
    echo ""

    for i in "${!sites[@]}"; do
        site="${sites[$i]}"
        if [ ! -z "$site" ]; then
            current_index=$((i + 1))
            echo "--- 正在同步網站 ID: $site (進度: $current_index/${#sites[@]}) ---"

            # 執行同步
            start_time=$(date +%s)
            if just sync-site "$site" {{days}}; then
                end_time=$(date +%s)
                duration=$((end_time - start_time))
                success_count=$((success_count + 1))
                echo "✅ 網站 ID $site 同步成功 (耗時: ${duration}秒)"
            else
                end_time=$(date +%s)
                duration=$((end_time - start_time))
                failure_count=$((failure_count + 1))
                failed_sites+=("$site")
                echo "❌ 網站 ID $site 同步失敗 (耗時: ${duration}秒)"
            fi
            echo ""
        fi
    done

    echo "📈 批次同步完成！"
    echo "  ✅ 成功: $success_count 個網站"
    echo "  ❌ 失敗: $failure_count 個網站"

    if [ $failure_count -gt 0 ]; then
        echo "  🔧 失敗的網站ID: ${failed_sites[*]}"
        echo ""
        echo "💡 建議處理失敗的網站:"
        echo "  just network-check                    # 檢查網絡連接"
        echo "  just conservative-sync <site_id>      # 使用保守模式重試"
        echo "  just sync-status <site_id>            # 檢查具體狀態"
    fi

## 使用自訂參數執行通用的同步指令。
sync-custom *ARGS:
    poetry run gsc-cli sync {{ARGS}}

## 查看同步狀態和進度監控。 用法: `just sync-status [site_id]`
sync-status site_id="":
    #!/usr/bin/env bash
    if [ "{{site_id}}" != "" ]; then
        poetry run gsc-cli sync status --site-id {{site_id}}
    else
        poetry run gsc-cli sync status
    fi

## Windows 優化的批次同步命令，更好的錯誤處理。用法: `just batch-sync "1 2 3" [days]`
batch-sync site_list days='7':
    @{{ if os() == "windows" { `
        Write-Host "🚀 Windows 優化批次同步開始: [{{site_list}}] ({{days}} 天)" -ForegroundColor Green;
        $sites = "{{site_list}}".Split(" ") | Where-Object { $_.Trim() -ne "" };
        $logFile = "data/logs/batch_sync_$(Get-Date -Format 'yyyyMMdd_HHmmss').log";
        New-Item -Path (Split-Path $logFile -Parent) -ItemType Directory -Force | Out-Null;

        Write-Host "📝 同步日誌將保存到: $logFile";
        "批次同步開始: $(Get-Date)" | Out-File -FilePath $logFile -Encoding UTF8;

        foreach ($site in $sites) {
            $siteId = $site.Trim();
            if ($siteId -ne "") {
                Write-Host "🔄 開始同步網站 ID: $siteId" -ForegroundColor Cyan;
                "開始同步網站 ID: $siteId - $(Get-Date)" | Out-File -FilePath $logFile -Append -Encoding UTF8;

                try {
                    poetry run gsc-cli sync daily --site-id $siteId --days {{days}} --max-workers 1;
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "✅ 網站 ID $siteId 同步成功" -ForegroundColor Green;
                        "成功: 網站 ID $siteId - $(Get-Date)" | Out-File -FilePath $logFile -Append -Encoding UTF8;
                    } else {
                        Write-Host "❌ 網站 ID $siteId 同步失敗 (退出碼: $LASTEXITCODE)" -ForegroundColor Red;
                        "失敗: 網站 ID $siteId (退出碼: $LASTEXITCODE) - $(Get-Date)" | Out-File -FilePath $logFile -Append -Encoding UTF8;
                    }
                } catch {
                    Write-Host "❌ 網站 ID $siteId 同步異常: $($_.Exception.Message)" -ForegroundColor Red;
                    "異常: 網站 ID $siteId - $($_.Exception.Message) - $(Get-Date)" | Out-File -FilePath $logFile -Append -Encoding UTF8;
                }

                Start-Sleep -Seconds 2;  # 防止 API 限制
            }
        }

        "批次同步完成: $(Get-Date)" | Out-File -FilePath $logFile -Append -Encoding UTF8;
        Write-Host "📋 完整日誌已保存到: $logFile" -ForegroundColor Blue;
        Write-Host "✅ Windows 批次同步完成！" -ForegroundColor Green;
    ` } else { `
        echo "🚀 批次同步開始: [{{site_list}}] ({{days}} 天)"
        log_file="data/logs/batch_sync_$(date +%Y%m%d_%H%M%S).log"
        mkdir -p "$(dirname "$log_file")"

        echo "📝 同步日誌將保存到: $log_file"
        echo "批次同步開始: $(date)" > "$log_file"

        for site in {{site_list}}; do
            if [ ! -z "$site" ]; then
                echo "🔄 開始同步網站 ID: $site"
                echo "開始同步網站 ID: $site - $(date)" >> "$log_file"

                if poetry run gsc-cli sync daily --site-id "$site" --days {{days}} --max-workers 1; then
                    echo "✅ 網站 ID $site 同步成功"
                    echo "成功: 網站 ID $site - $(date)" >> "$log_file"
                else
                    echo "❌ 網站 ID $site 同步失敗 (退出碼: $?)"
                    echo "失敗: 網站 ID $site (退出碼: $?) - $(date)" >> "$log_file"
                fi

                sleep 2  # 防止 API 限制
            fi
        done

        echo "批次同步完成: $(date)" >> "$log_file"
        echo "📋 完整日誌已保存到: $log_file"
        echo "✅ 批次同步完成！"
    ` } }}

## 智能同步命令，自動處理 SSL 錯誤
smart-sync site_id="all" days="7":
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🚀 開始智能同步..."

    # 檢查網絡連接
    echo "🔍 檢查網絡連接狀態..."
    if ! poetry run python -c "from src.utils.system_health_check import check_network_connectivity; import sys; result = check_network_connectivity(); sys.exit(0 if result['google_api_connection'] and result['ssl_handshake'] else 1)"; then
        echo "❌ 網絡連接有問題，正在等待恢復..."
        poetry run python -c "from src.utils.system_health_check import wait_for_network_recovery; wait_for_network_recovery(60, 5)"
    fi

    # 執行同步
    echo "📡 開始數據同步..."
    if [ "{{site_id}}" = "all" ]; then
        poetry run python -m src.app sync daily --all-sites --days {{days}} --sync-mode skip --max-workers 2
    else
        poetry run python -m src.app sync daily --site-id {{site_id}} --days {{days}} --sync-mode skip --max-workers 2
    fi

    echo "✅ 智能同步完成！"

## 保守同步命令，使用最低併發數 (適用於 SSL 錯誤頻繁的環境)
conservative-sync site_id="all" days="7":
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🐌 開始保守同步 (單線程，更長延遲)..."

    # 檢查網絡連接
    echo "🔍 檢查網絡連接狀態..."
    if ! poetry run python -c "from src.utils.system_health_check import check_network_connectivity; import sys; result = check_network_connectivity(); sys.exit(0 if result['google_api_connection'] and result['ssl_handshake'] else 1)"; then
        echo "❌ 網絡連接有問題，正在等待恢復..."
        poetry run python -c "from src.utils.system_health_check import wait_for_network_recovery; wait_for_network_recovery(60, 5)"
    fi

    # 執行單線程同步
    echo "📡 開始單線程數據同步..."
    if [ "{{site_id}}" = "all" ]; then
        poetry run python -m src.app sync daily --all-sites --days {{days}} --sync-mode skip --max-workers 1
    else
        poetry run python -m src.app sync daily --site-id {{site_id}} --days {{days}} --sync-mode skip --max-workers 1
    fi

    echo "✅ 保守同步完成！"

## 自適應同步命令，根據網絡狀況自動調整併發數
adaptive-sync site_id="all" days="7":
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🤖 開始自適應同步 (智能調整併發數)..."

    # 檢查網絡連接品質
    echo "🔍 檢查網絡連接品質..."
    if ! poetry run python -c "from src.utils.system_health_check import check_network_connectivity; import sys; result = check_network_connectivity(); sys.exit(0 if result['google_api_connection'] and result['ssl_handshake'] else 1)"; then
        echo "❌ 網絡連接有問題，使用單線程模式..."
        MAX_WORKERS=1
    else
        echo "✅ 網絡連接良好，使用標準併發模式..."
        MAX_WORKERS=2
    fi

    # 檢查是否有其他 GSC 進程在運行
    if ps aux | grep -E "(gsc-cli|python.*sync|poetry.*sync)" | grep -v grep | grep -v "adaptive-sync" > /dev/null; then
        echo "⚠️ 檢測到其他 GSC 進程，降低併發數..."
        MAX_WORKERS=1
    fi

    # 執行同步
    echo "📡 開始數據同步 (使用 $MAX_WORKERS 個工作線程)..."
    if [ "{{site_id}}" = "all" ]; then
        poetry run python -m src.app sync daily --all-sites --days {{days}} --sync-mode skip --max-workers $MAX_WORKERS
    else
        poetry run python -m src.app sync daily --site-id {{site_id}} --days {{days}} --sync-mode skip --max-workers $MAX_WORKERS
    fi

    echo "✅ 自適應同步完成！"

## 高性能同步命令，使用最大安全併發數 (適用於良好網絡環境)
turbo-sync site_id="all" days="7":
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🚀 開始高性能同步 (最大安全併發數)..."

    # 檢查網絡連接
    echo "🔍 檢查網絡連接狀態..."
    if ! poetry run python -c "from src.utils.system_health_check import check_network_connectivity; import sys; result = check_network_connectivity(); sys.exit(0 if result['google_api_connection'] and result['ssl_handshake'] else 1)"; then
        echo "❌ 網絡連接不穩定，建議使用 conservative-sync 或 adaptive-sync"
        exit 1
    fi

    # 檢查是否有其他 GSC 進程
    if ps aux | grep -E "(gsc-cli|python.*sync|poetry.*sync)" | grep -v grep | grep -v "turbo-sync" > /dev/null; then
        echo "❌ 檢測到其他 GSC 進程，請先停止其他進程或使用 adaptive-sync"
        exit 1
    fi

    # 執行高性能同步
    echo "📡 開始高性能數據同步 (使用 3 個工作線程)..."
    if [ "{{site_id}}" = "all" ]; then
        poetry run python -m src.app sync daily --all-sites --days {{days}} --sync-mode skip --max-workers 3
    else
        poetry run python -m src.app sync daily --site-id {{site_id}} --days {{days}} --sync-mode skip --max-workers 3
    fi

    echo "✅ 高性能同步完成！"

## 網絡診斷命令
network-check:
    poetry run python -c "from src.utils.system_health_check import check_network_connectivity, diagnose_ssl_issues; from rich.console import Console; from rich.table import Table; console = Console(); connectivity = check_network_connectivity(); table = Table(title='網絡連接檢查結果', show_header=True, header_style='bold magenta'); table.add_column('檢查項目', style='dim'); table.add_column('狀態', justify='center'); table.add_column('說明'); status_items = [('DNS 解析', connectivity['dns_resolution'], '域名解析是否正常'), ('HTTP 連接', connectivity['http_connection'], '基本 HTTP 連接'), ('HTTPS 連接', connectivity['https_connection'], '安全 HTTPS 連接'), ('Google API', connectivity['google_api_connection'], 'Google API 可達性'), ('SSL 握手', connectivity['ssl_handshake'], 'SSL/TLS 握手過程')]; [table.add_row(item, f'[green]✅[/green]' if status else f'[red]❌[/red]', description) for item, status, description in status_items]; console.print(table); print('\\n✅ 網絡連接正常！' if all(connectivity.values()) else '\\n⚠️ 發現網絡問題，請檢查連接設定')"

## 檢查正在運行的 GSC 相關進程
check-processes:
    #!/usr/bin/env bash
    echo "🔍 檢查正在運行的 GSC 相關進程..."

    # 檢查 GSC 相關進程
    GSC_PROCESSES=$(ps aux | grep -E "(gsc-cli|python.*sync|poetry.*sync)" | grep -v grep | grep -v "check-processes")

    if [ -z "$GSC_PROCESSES" ]; then
        echo "✅ 沒有發現正在運行的 GSC 進程"
    else
        echo "⚠️ 發現正在運行的 GSC 進程："
        echo "$GSC_PROCESSES"
        echo ""
        echo "💡 如果需要停止這些進程，請運行: just kill-processes"
    fi

## 停止所有 GSC 相關進程 (小心使用)
kill-processes:
    #!/usr/bin/env bash
    echo "⚠️ 正在停止所有 GSC 相關進程..."

    # 獲取 GSC 相關進程的 PID
    PIDS=$(ps aux | grep -E "(gsc-cli|python.*sync|poetry.*sync)" | grep -v grep | grep -v "kill-processes" | awk '{print $2}')

    if [ -z "$PIDS" ]; then
        echo "✅ 沒有發現需要停止的 GSC 進程"
    else
        echo "🔄 正在停止進程: $PIDS"
        for pid in $PIDS; do
            echo "  - 停止進程 $pid"
            kill $pid 2>/dev/null || echo "    (進程 $pid 可能已經停止)"
        done

        # 等待 2 秒後檢查
        sleep 2

        # 檢查是否還有殘留進程
        REMAINING=$(ps aux | grep -E "(gsc-cli|python.*sync|poetry.*sync)" | grep -v grep | grep -v "kill-processes")
        if [ -z "$REMAINING" ]; then
            echo "✅ 所有 GSC 進程已成功停止"
        else
            echo "⚠️ 仍有進程在運行，可能需要強制停止"
        fi
    fi


# --- 維護程序 ---

## 執行完整的每日維護程序 (同步、備份、清理)。
maintenance: _sync-daily _backup-db _clean-backups
    @echo "\n✅ --- GSC 每日維護程序成功完成 ---"

# [內部] 步驟 1: 為所有網站執行每日資料同步 (最近 2 天)。
_sync-daily:
    @echo "🔄 1. 正在為所有網站執行每日資料同步 (最近 2 天)..."
    @# 使用單線程確保穩定性，避免 SSL 錯誤
    @script -q /dev/null poetry run gsc-cli sync daily --all-sites --days 2 --max-workers 1

# [內部] 步驟 2: 備份資料庫。
_backup-db:
    #!/usr/bin/env bash
    echo "📦 2. 正在備份資料庫..."
    mkdir -p '{{BACKUP_DIR}}'
    TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
    TEMP_BACKUP="{{BACKUP_DIR}}/temp_backup.db"
    BACKUP_FILE="{{BACKUP_DIR}}/gsc_data_backup_$TIMESTAMP.db.gz"
    echo "   -> 正在建立臨時備份檔..."
    sqlite3 '{{DB_PATH}}' ".backup '$TEMP_BACKUP'"
    echo "   -> 正在將備份壓縮至 $BACKUP_FILE..."
    gzip -c "$TEMP_BACKUP" > "$BACKUP_FILE"
    echo "   -> 正在清理臨時檔案..."
    rm -f "$TEMP_BACKUP"
    echo "✅ 備份完成: $BACKUP_FILE"

# [內部] 步驟 3: 清理舊的備份。
_clean-backups:
    @echo "🧹 3. 正在清理超過 30 天的舊備份..."
    @find '{{BACKUP_DIR}}' -name "gsc_data_backup_*.db.gz" -mtime +30 -delete
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
    @du -h "{{BACKUP_DIR}}"/gsc_data_backup_*.db.gz 2>/dev/null | sort -rh | head -n {{count}}

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


# --- 業務腳本 ---

## 執行 Sitemap 冗餘分析。用法: `just sitemap-redundancy --site-id 14`
sitemap-redundancy *args:
    @echo "🔍 正在執行 Sitemap 冗餘分析..."
    @poetry run python scripts/sitemap_redundancy_analyzer.py {{args}}

## 顯示 Sitemap 分析工具的使用幫助
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
    @poetry run python scripts/sitemap_redundancy_analyzer.py --help
