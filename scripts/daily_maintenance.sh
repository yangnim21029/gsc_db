#!/bin/bash

# ==============================================================================
# GSC-CLI Daily Maintenance Script
#
# 功能:
# 1. 運行每日數據同步 (最近2天, 所有站點)
# 2. 安全備份 SQLite 數據庫並壓縮
# 3. 清理超過30天的舊備份
#
# 使用方法:
# 1. 將此腳本放置在專案根目錄的 `scripts/` 文件夾下
# 2. 確保 Python 虛擬環境路徑正確 (VENV_PYTHON)
# 3. 賦予執行權限: chmod +x scripts/daily_maintenance.sh
# 4. 設置 cron job 每日運行, 例如:
#    0 3 * * * /path/to/your/project/scripts/daily_maintenance.sh
# ==============================================================================

# 如果任何命令失敗，立即退出
set -e

# --- 配置 (Configuration) ---

# 設置環境為 'production'，讓 config.py 使用正式環境路徑
export APP_ENV=production

# 專案根目錄 (假設此腳本在 `scripts/` 子目錄中)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Python 虛擬環境中的 Python 可執行文件路徑 (請根據你的情況修改)
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"

# 主應用程式腳本
MAIN_SCRIPT="$PROJECT_DIR/main.py"

# 正式環境的數據庫路徑 (僅為清晰起見，應用會自動讀取)
DB_PATH="/var/data/gsc_db/gsc_data.db"

# 備份文件夾路徑
BACKUP_DIR="/var/backups/gsc_db"

# 日誌文件路徑
LOG_FILE="/var/log/gsc_db/daily_maintenance.log"

# --- 日誌函數 (Logging Function) ---
log() {
    # 將日誌同時輸出到控制台和日誌文件
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# --- 主程序 (Main Logic) ---

log "--- [START] GSC 每日同步與備份任務 ---"

# 1. 確保備份和日誌目錄存在
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# 2. 檢查 Python 虛擬環境是否存在
if [ ! -f "$VENV_PYTHON" ]; then
    log "❌ 錯誤：找不到 Python 虛擬環境: $VENV_PYTHON"
    exit 1
fi

# 3. 運行每日數據同步
log "🔄 正在為所有站點同步最近2天的數據..."
if ! "$VENV_PYTHON" "$MAIN_SCRIPT" sync daily --all-sites --days 2 --resume; then
    log "❌ 錯誤：每日同步失敗。中止任務。"
    exit 1
fi
log "✅ 每日同步成功完成。"

# 4. 備份數據庫
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/gsc_data_backup_$TIMESTAMP.db.gz"
log "📦 正在備份數據庫到 $BACKUP_FILE..."

# 使用 sqlite3 的 .backup 命令更安全，並通過管道壓縮
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/temp_backup.db'" && gzip -c "$BACKUP_DIR/temp_backup.db" > "$BACKUP_FILE" && rm "$BACKUP_DIR/temp_backup.db"
log "✅ 數據庫備份成功。"

# 5. 清理舊備份 (保留最近30天)
log "🧹 正在清理30天前的舊備份..."
find "$BACKUP_DIR" -name "gsc_data_backup_*.db.gz" -mtime +30 -exec rm {} \;
log "✅ 舊備份清理完成。"

log "--- [END] GSC 每日同步與備份任務圓滿結束 ---"
exit 0 