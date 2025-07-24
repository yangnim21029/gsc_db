# GSC Database Update History

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

##### 單程序應用（保持原有行為）
```python
from src.containers import Container
```

##### 多程序應用（新功能）
```python
from src.containers_multiprocess import MultiProcessContainer as Container
```

##### 部署範例
```bash
# Gunicorn 多 worker
gunicorn -w 4 "src.web.api_multiprocess:app"

# Uvicorn 多程序
uvicorn src.web.api_multiprocess:app --workers 4
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
