# GSC Database Update History

## Version 2.4.0 - Sync Performance Diagnostics & API Improvements (2025-07-24)

### 🎯 同步效能診斷工具與 API 優化

新增診斷端點以測試和分析同步效能，並優化 API 結構。

#### 主要變更

1. **新增診斷路由**
   - 新檔案：`src/web/api/routers/diagnostics.py`
   - 提供同步效能測試和分析工具
   - 幫助識別效能瓶頸

2. **診斷端點**
   - `GET /api/v1/diagnostics/test-db-connection` - 測試資料庫連線效能
   - `POST /api/v1/diagnostics/test-sync` - 執行批量同步並測量時間
   - `GET /api/v1/diagnostics/check-locks` - 檢查資料庫鎖定狀態

3. **效能分析結果**
   - GSC API 調用佔用 95%+ 的同步時間
   - 資料庫操作僅佔 < 5% 時間
   - 平均每個站點每天需要 1.5-2 秒同步時間
   - 瓶頸在於 Google API 回應速度，非系統問題

4. **API 優化**
   - 移除冗餘的 GET 端點（ranking-data、page-keyword-performance）
   - 保留功能更強大的 POST 端點
   - 新增 `matching_mode` 參數到 ranking-data 端點
   - 支援完全匹配（exact）和部分匹配（partial）模式

5. **匹配模式增強**
   - **完全匹配**（預設）：`matching_mode="exact"`
     - "男士 理髮" 只匹配 "男士 理髮"
   - **部分匹配**：`matching_mode="partial"`
     - "理髮" 匹配所有包含 "理髮" 的查詢

#### 同步測試結果

測試 2 個站點，各同步 5 天的數據：
- **總時間**：14.46 秒（10 個任務）
- **平均每任務**：1.45 秒
- **API 時間**：13.78 秒（95.3%）
- **資料庫時間**：0.67 秒（4.6%）
- **瓶頸**：GSC API 調用

#### 使用範例

```bash
# 測試同步效能
POST /api/v1/diagnostics/test-sync
{
  "site_ids": [4, 5],
  "days": 5
}

# 使用部分匹配模式
POST /api/v1/analytics/ranking-data
{
  "site_id": 4,
  "queries": ["理髮"],
  "matching_mode": "partial",
  "start_date": "2025-07-01",
  "end_date": "2025-07-15"
}
```

---

## Version 2.3.0 - API Modularization & Query Search (2025-07-24)

### 🎯 API 模組化重構與查詢搜尋功能

將龐大的 API 檔案重構為模組化結構，並新增支援部分匹配的查詢搜尋功能。

#### 主要變更

1. **API 模組化**
   - 將 800+ 行的 `api.py` 拆分為模組化結構
   - 新目錄結構：
     ```
     src/web/api/
     ├── main.py              # 主應用程式
     ├── dependencies/        # 共享依賴
     └── routers/            # 各領域路由
         ├── analytics.py    # 分析端點
         ├── health.py       # 健康檢查
         ├── performance.py  # 效能數據
         ├── queries.py      # 查詢相關
         ├── sites.py        # 站點管理
         └── sync.py         # 同步狀態
     ```

2. **新增查詢搜尋端點**
   - 端點：`GET /api/v1/sites/{site_id}/queries/search`
   - 支援部分匹配（LIKE 查詢）
   - 範例：搜尋 "是" 會找到 "什麼是"、"是不是" 等
   - 解決了原本只有完全匹配的限制

3. **保持向後相容**
   - 原始 `src/web/api.py` 作為相容層
   - 所有現有 import 繼續運作
   - API 路徑保持不變

4. **改進的文件**
   - 新增 `src/web/api/README.md` 說明架構
   - 更清楚的查詢匹配行為說明
   - 區分完全匹配與部分匹配端點

#### 新功能詳解

##### 查詢搜尋端點
```bash
# 搜尋包含 "理髮" 的所有查詢
GET /api/v1/sites/1/queries/search?search_term=理髮&start_date=2025-07-01&end_date=2025-07-15

# 回傳結果包含：
- "男士理髮"
- "男士 理髮"
- "理髮店"
- "哪裡理髮好"
```

##### 與原有端點的差異
- **ranking-data** (POST)：使用完全匹配
  - `queries: ["男士 理髮"]` 只會找到完全等於 "男士 理髮" 的查詢
- **queries/search** (GET)：使用部分匹配
  - `search_term=理髮` 會找到所有包含 "理髮" 的查詢

#### 技術改進
- 更好的關注點分離
- 易於維護和擴展
- 每個路由處理特定領域
- 統一的依賴注入管理

---

## Version 2.2.0 - Standardized Multi-Process Support (2025-07-24)

### 🎯 標準化多程序支援

將多程序支援標準化為預設實作，移除了 `_multiprocess` 後綴檔案。

#### 主要變更

1. **統一的容器實作**
   - `containers.py` 現在預設使用 `ProcessSafeDatabase`
   - 移除了 `containers_multiprocess.py`（功能已整合）
   - 所有應用都使用相同的 import：`from src.containers import Container`

2. **統一的 API 實作**
   - `api.py` 現在包含多程序支援功能
   - 新增了 startup/shutdown 事件處理
   - 新增了 `/health` 端點顯示程序資訊
   - 移除了 `api_multiprocess.py`（功能已整合）

3. **簡化的使用方式**
   - 不再需要選擇不同的容器版本
   - 多程序功能自動啟用
   - 保持向後相容性

4. **更新的文件**
   - 更新了所有範例程式碼
   - 簡化了部署指南
   - 統一了 import 路徑

#### 升級指南

如果你的程式碼使用了舊的 import：
```python
# 舊的方式
from src.containers_multiprocess import MultiProcessContainer as Container
```

請更新為：
```python
# 新的方式
from src.containers import Container
```

---

## Version 2.1.0 - Multi-Process Support (2025-07-24)

### 🎯 主要更新：解決 SQLite 多程序鎖定問題

#### 問題背景
- 多個程序同時存取 SQLite 資料庫時出現 "database is locked" 錯誤
- 原本的實作只支援單程序內的多執行緒存取

#### 解決方案實作

##### 1. **啟用 WAL 模式**
- 在 `src/services/database.py` 的 `init_db()` 方法中新增 PRAGMA 設定：
  ```python
  cursor.execute("PRAGMA journal_mode=WAL")
  cursor.execute("PRAGMA synchronous=NORMAL")
  cursor.execute("PRAGMA busy_timeout=30000")  # 30 秒超時
  cursor.execute("PRAGMA cache_size=-64000")   # 64MB 快取
  ```
- 在 `src/containers.py` 中增加連線超時設定：
  ```python
  timeout=30.0  # 增加超時時間以避免鎖定錯誤
  ```

##### 2. **新增程序安全的資料庫包裝器**
- 新檔案：`src/services/process_safe_database.py`
  - `ProcessSafeDatabase` 類別：自動為每個程序管理獨立連線
  - `ConnectionPool` 類別：提供連線池功能以支援高並發讀取
  - 自動偵測 process fork 並重建連線

##### 3. **多程序容器配置**
- 新檔案：`src/containers_multiprocess.py`
  - 使用 `ProcessSafeDatabase` 取代原本的 `Database`
  - 保持與原有 API 相容

##### 4. **多程序 Web API**
- 新檔案：`src/web/api_multiprocess.py`
  - 支援 Gunicorn 多 worker 部署
  - 新增程序資訊的健康檢查端點
  - 自動清理連線的 shutdown 事件

##### 5. **測試套件**
- 新檔案：`tests/test_multiprocess_database.py`
  - 測試並發讀取
  - 測試並發寫入
  - 測試混合讀寫操作
  - 測試 process fork 偵測
  - 測試連線池功能
  - 驗證 WAL 模式啟用

##### 6. **使用範例與文件**
- 新檔案：`examples/multiprocess_usage.py`
  - 展示各種多程序使用情境
  - 模擬 Web 伺服器多 worker 環境
- 新檔案：`docs/MULTIPROCESS_GUIDE.md`
  - 詳細的部署指南
  - 最佳實踐建議
  - 常見問題解答

#### 使用方式

所有應用現在都使用標準的 Container，它已內建多程序支援：
```python
from src.containers import Container
```

多程序功能會自動啟用，無需額外配置。

##### 部署範例
```bash
# Gunicorn 多 worker
gunicorn -w 4 "src.web.api:app"

# Uvicorn 多程序
uvicorn src.web.api:app --workers 4
```

#### 效能改善
- WAL 模式允許多個讀取者同時存取
- 減少寫入時的鎖定範圍
- 30 秒的 busy timeout 減少暫時性錯誤
- 64MB 快取提升查詢效能

#### 相容性
- 完全向後相容
- 原有的單程序應用不受影響
- API 介面保持不變

#### 測試執行
```bash
# 執行多程序測試
pytest tests/test_multiprocess_database.py -v

# 執行使用範例
python examples/multiprocess_usage.py
```

---

## Version 2.0.0 - Previous Release

[之前的版本資訊...]
