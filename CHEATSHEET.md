# GSC Database Manager - Command Cheatsheet

> 如果你沒有安裝 `just` 工具，可以使用這些直接的 Python 命令

## 🚀 快速開始

### 安裝依賴
```bash
poetry install
```

### 查看所有網站
```bash
poetry run python sync.py list
```

## 📊 數據同步

### 單站點同步
```bash
# 基本同步（預設 skip 模式，7天）
poetry run python sync.py sync <site_id>

# 指定天數
poetry run python sync.py sync <site_id> <days>

# 指定同步模式
poetry run python sync.py sync <site_id> <days> <sync_mode>
```

**同步模式說明：**
- `skip` (預設): 跳過已存在的記錄，只插入新數據
- `overwrite`: 覆蓋已存在的記錄（用於數據修正）

**範例：**
```bash
# Urban Life 網站同步 7 天，skip 模式
poetry run python sync.py sync 17 7 skip

# Urban Life 網站同步 14 天，overwrite 模式（覆蓋現有數據）
poetry run python sync.py sync 17 14 overwrite

# Business Focus 網站同步 3 天，預設 skip 模式
poetry run python sync.py sync 1 3
```

### 多站點順序同步
```bash
# 基本多站點同步
poetry run python sync_multiple.py "1,2,17" 7

# 指定同步模式
poetry run python sync_multiple.py "1,2,17" 7 skip
poetry run python sync_multiple.py "1,2,17" 7 overwrite

# 支援空格分隔
poetry run python sync_multiple.py "1 2 17" 7 overwrite
```

**重要提醒：**
- ⚠️ GSC API 不支持並發！多站點同步會自動使用順序處理
- 🕐 每個站點間會有 2 秒延遲以遵守 API 限制

## 🌐 API 服務

### 啟動開發服務器
```bash
poetry run uvicorn src.api.app:app --reload --host 127.0.0.1 --port 8000
```

### 啟動生產服務器
```bash
poetry run uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

### API 文檔
- Swagger UI: http://localhost:8000/docs
- OpenAPI Schema: http://localhost:8000/schema

## 🔧 API 測試

### 健康檢查
```bash
curl -s http://localhost:8000/health | jq .
```

### 查看所有站點
```bash
curl -s http://localhost:8000/api/v1/sites | jq .
```

### 獲取站點排名數據
```bash
curl -s -X POST http://localhost:8000/api/v1/analytics/ranking-data \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 17,
    "date_from": "2025-07-20",
    "date_to": "2025-07-25",
    "group_by": ["query"],
    "limit": 10
  }' | jq .
```

### 使用 hostname 查詢
```bash
curl -s -X POST http://localhost:8000/api/v1/analytics/ranking-data \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "urbanlifehk.com",
    "date_from": "2025-07-20", 
    "date_to": "2025-07-25",
    "queries": ["美容", "護膚"],
    "exact_match": false,
    "group_by": ["query"]
  }' | jq .
```

### 觸發同步任務（API）
```bash
# 基本同步觸發
curl -s -X POST http://localhost:8000/api/v1/sync/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 17,
    "days": 7,
    "sync_mode": "skip"
  }' | jq .

# 使用 hostname 和 overwrite 模式
curl -s -X POST http://localhost:8000/api/v1/sync/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "urbanlifehk.com",
    "days": 14,
    "sync_mode": "overwrite",
    "force": true
  }' | jq .
```

### 下載 CSV 數據
```bash
# 頁面關鍵字效果數據
curl -s "http://localhost:8000/api/v1/page-keyword-performance/csv/?site_id=17&days=30" \
  -o performance_data.csv

# 使用 hostname
curl -s "http://localhost:8000/api/v1/page-keyword-performance/csv/?hostname=urbanlifehk.com&days=30" \
  -o performance_data.csv
```

### 查看同步狀態
```bash
# 使用 site_id
curl -s "http://localhost:8000/api/v1/sync/status?site_id=17&days=30" | jq .

# 使用 hostname
curl -s "http://localhost:8000/api/v1/sync/status?hostname=urbanlifehk.com&days=30" | jq .
```

## 🧪 測試和診斷

### 運行 API 負載測試
```bash
poetry run python load_test.py
```

### 運行 API 壓力測試
```bash
poetry run python stress_test.py
```

### 測試 GSC API 並發限制
```bash
poetry run python test_gsc_limits.py
poetry run python test_real_gsc_auth.py
```

### 數據庫查詢
```bash
# 檢查特定站點的記錄數
sqlite3 data/gsc_data.db "SELECT COUNT(*) FROM gsc_performance_data WHERE site_id = 17;"

# 查看最近的數據
sqlite3 data/gsc_data.db "SELECT date, COUNT(*) as records FROM gsc_performance_data WHERE site_id = 17 GROUP BY date ORDER BY date DESC LIMIT 10;"

# 查看同步覆蓋範圍
sqlite3 data/gsc_data.db "SELECT DISTINCT date FROM gsc_performance_data WHERE site_id = 17 ORDER BY date DESC;"
```

## 🛠️ 開發工作流程

### 代碼質量檢查
```bash
# 格式化代碼
poetry run ruff check . --fix
poetry run ruff format .

# 類型檢查
poetry run mypy src/

# 運行測試
poetry run pytest
```

### 常見站點 ID
根據你的 `just site-list` 輸出：
- `1`: businessfocus.io
- `2`: mamidaily.com
- `17`: urbanlifehk.com
- `7`: petcutecute.com
- `8`: topbeautyhk.com

## ⚠️ 重要提醒

1. **GSC API 限制**：
   - 不支持並發請求（會導致 100% 失敗率）
   - 必須使用順序同步
   - 建議請求間隔 200-500ms

2. **同步模式選擇**：
   - 日常更新使用 `skip` 模式
   - 數據修正使用 `overwrite` 模式
   - Overwrite 模式會覆蓋現有數據，請謹慎使用

3. **性能考量**：
   - API 查詢支持高並發（測試達 808 RPS）
   - 數據同步必須順序執行
   - 大量數據同步建議分批進行

## 🔗 相關文件

- `README.md`: 項目完整說明
- `CLAUDE.md`: Claude Code 專用指引
- `justfile`: Just 工具的任務定義
- API 文檔: http://localhost:8000/docs （需要先啟動服務）