# Multi-Process SQLite Access Guide

## 問題概述

當多個程序嘗試存取同一個 SQLite 資料庫時，可能會遇到 "database is locked" 錯誤。這是因為 SQLite 的預設設定不適合多程序並發存取。

## 解決方案

### 1. WAL 模式（已實作）

我們已經在資料庫初始化時啟用了 WAL (Write-Ahead Logging) 模式：

```python
cursor.execute("PRAGMA journal_mode=WAL")
cursor.execute("PRAGMA synchronous=NORMAL")
cursor.execute("PRAGMA busy_timeout=30000")  # 30 秒超時
cursor.execute("PRAGMA cache_size=-64000")   # 64MB 快取
```

WAL 模式的優點：
- 允許多個讀取者同時存取資料庫
- 寫入時只鎖定必要的部分
- 提高並發效能

### 2. 程序安全的連線管理

使用 `ProcessSafeDatabase` 類別來自動管理每個程序的連線：

```python
# 單程序應用（CLI、單一 worker）
from src.containers import Container

# 多程序應用（Gunicorn、多 worker）
from src.containers_multiprocess import MultiProcessContainer as Container
```

### 3. 部署配置

#### Gunicorn 配置

```bash
# gunicorn_config.py
workers = 4  # 根據 CPU 核心數調整
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
timeout = 120
keepalive = 5

# 啟動 Gunicorn
gunicorn -c gunicorn_config.py "src.web.api_multiprocess:app"
```

#### Uvicorn 配置

```bash
# 單一程序（開發環境）
uvicorn src.web.api:app --reload

# 多程序（生產環境）
uvicorn src.web.api_multiprocess:app --workers 4 --host 0.0.0.0 --port 8000
```

### 4. 程式碼範例

#### 在 Web API 中使用

```python
# src/web/api_multiprocess.py
from src.containers_multiprocess import MultiProcessContainer as Container

container = Container()
app = FastAPI()

def get_database():
    return container.database()

@app.get("/api/v1/sites")
async def list_sites(db = Depends(get_database)):
    return db.get_sites()
```

#### 在背景任務中使用

```python
from multiprocessing import Process
from src.containers_multiprocess import MultiProcessContainer as Container

def background_sync(site_id):
    container = Container()
    db = container.database()
    # 執行同步任務
    db.start_sync_task(site_id, "daily_sync")
    # ...

# 啟動背景程序
p = Process(target=background_sync, args=(1,))
p.start()
```

### 5. 最佳實踐

1. **避免長時間交易**：使用自動提交模式或儘快提交交易
2. **處理鎖定錯誤**：實作重試邏輯處理暫時的鎖定情況
3. **監控連線**：使用 `get_connection_info()` 追蹤連線狀態
4. **清理連線**：在程序結束時呼叫 `close_all_connections()`

### 6. 常見問題

#### Q: 還是遇到 "database is locked" 錯誤？

A: 檢查以下項目：
- 確認使用了多程序版本的容器
- 增加 `busy_timeout` 值
- 檢查是否有長時間執行的交易
- 考慮使用連線池進行大量並發讀取

#### Q: 效能變慢了？

A: WAL 模式通常會提升效能，但如果變慢，可以：
- 調整 `cache_size` 參數
- 使用 SSD 儲存資料庫檔案
- 考慮使用 PostgreSQL 等更適合高並發的資料庫

#### Q: 如何測試多程序存取？

A: 使用提供的測試腳本：
```bash
python examples/multiprocess_usage.py
```

### 7. 進階配置

如果需要更高的並發效能，可以考慮：

1. **使用連線池**：在同一程序內使用多個連線進行並發讀取
2. **讀寫分離**：使用主從架構，寫入主庫，從庫讀取
3. **遷移到 PostgreSQL**：對於需要真正高並發的應用

### 8. 監控與除錯

```python
# 檢查連線狀態
db = container.database()
info = db.get_connection_info()
print(f"Current process: {info['current_pid']}")
print(f"Active connections: {info['connection_pids']}")
```

## 總結

透過以上配置，你的應用程式應該能夠支援多程序並發存取 SQLite 資料庫。如果仍然遇到問題，請考慮升級到更適合高並發的資料庫系統。
