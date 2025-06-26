# GSC CLI 工具 - 項目結構

## 🗂️ 當前文件結構

```
gsc_db/
├── 📋 核心工具
│   ├── gsc_simple.py             # ⭐ 主要 CLI 工具
│   └── quick_start.py            # 快速狀態檢查腳本
│
├── 📚 文檔
│   ├── docs/
│   │   ├── README_CLI.md             # 使用說明文檔
│   │   ├── DATABASE_SETUP_AND_QUOTA_ANALYSIS.md  # 數據庫建置與配額分析
│   │   ├── OPTIMIZATION_SUMMARY.md   # 優化總結
│   │   ├── PROJECT_STRUCTURE.md      # 此文檔
│   │   └── CODE_QUALITY_IMPROVEMENTS.md  # 代碼質量改善
│
├── ⚙️ 核心服務模塊
│   └── services/
│       ├── __init__.py           # 模塊初始化
│       ├── gsc_client.py         # GSC API 客戶端
│       └── database.py           # 數據庫操作
│
├── 📦 配置和依賴
│   └── requirements.txt          # Python 依賴包
│
└── 💾 數據文件（運行時生成）
    ├── gsc_data.db              # SQLite 數據庫
    ├── gsc_credentials.json     # GSC 認證信息
    ├── client_secret.json       # Google OAuth 憑證
    ├── gsc_simple.log           # 運行日誌
    └── app.log                  # 舊的日誌文件
```

## 🚀 主要工具

### `gsc_simple.py` - 主要 CLI 工具

這是核心工具，包含所有功能：

- GSC API 認證
- 站點管理
- 數據同步（包含每小時數據）
- 進度監控
- 任務管理

### `quick_start.py` - 快速檢查

快速狀態檢查腳本：

- 認證狀態確認
- 站點列表顯示
- 數據覆蓋概覽
- 運行中任務檢查

## 🗃️ 數據庫結構

SQLite 數據庫 (`gsc_data.db`) 包含以下表：

### 主要數據表

- **`sites`** - 站點信息
- **`keywords`** - 關鍵字信息
- **`daily_rankings`** - 每日排名數據
- **`page_data`** - 頁面數據
- **`hourly_rankings`** - 每小時排名數據 (2025 年新功能)

### 管理表

- **`sync_tasks`** - 同步任務追蹤

## 🔧 核心服務模塊

### `services/gsc_client.py`

GSC API 客戶端，負責：

- Google Search Console API 呼叫
- OAuth 2.0 認證處理
- 每小時數據支援
- API 請求管理

### `services/database.py`

數據庫操作，負責：

- SQLite 數據庫管理
- 表結構維護
- 數據存儲和查詢
- 簡化的任務追蹤

### `services/__init__.py`

模塊初始化文件，確保正確的包導入。

## 📚 文檔結構

### 核心文檔

- **`README_CLI.md`** - 使用說明和快速入門
- **`DATABASE_SETUP_AND_QUOTA_ANALYSIS.md`** - 數據庫建置策略和 API 配額分析
- **`OPTIMIZATION_SUMMARY.md`** - 項目優化過程總結
- **`PROJECT_STRUCTURE.md`** - 此文檔，項目結構說明
- **`CODE_QUALITY_IMPROVEMENTS.md`** - 代碼質量改善記錄

### 文檔分工

- **使用指南** → `README_CLI.md`
- **技術細節** → `DATABASE_SETUP_AND_QUOTA_ANALYSIS.md`
- **架構說明** → `PROJECT_STRUCTURE.md`
- **優化過程** → `OPTIMIZATION_SUMMARY.md`
- **代碼改善** → `CODE_QUALITY_IMPROVEMENTS.md`

## 🗑️ 已清理的舊文件

以下文件已被移除（簡化項目結構）：

### 前端相關（已刪除）

- ❌ `app.py` - Flask 應用主文件
- ❌ `templates/` - 前端模板目錄
- ❌ `routes/` - Web 路由目錄

### 冗餘模塊（已刪除）

- ❌ `services/data_builder.py` - 數據建構服務（與 gsc_client 重複）
- ❌ `services/build_progress.py` - 複雜進度追蹤（簡化整合到 database.py）
- ❌ `services/semantic_search.py` - 語義搜索（對 CLI 工具過於複雜）

### 錯誤版本（已刪除）

- ❌ `gsc_cli.py` - 有錯誤的 CLI 版本
- ❌ `gsc_export.py` - 有錯誤的導出版本

## 🚀 快速開始

1. **安裝依賴**

```bash
pip install -r requirements.txt
```

2. **認證**

```bash
python gsc_simple.py auth
```

3. **開始使用**

```bash
python gsc_simple.py sites
python gsc_simple.py add-site "https://example.com/"
python gsc_simple.py sync --recent-days 30
```

## 📦 依賴管理

### `requirements.txt`

包含所有必要的 Python 依賴包，主要有：

- Google API 相關包
- 數據處理包 (pandas, numpy)
- 其他輔助包

### `client_secret.json`

Google OAuth 憑證文件（需要自行準備）

## 💾 數據文件

### 運行時生成的文件

- **`gsc_data.db`** - SQLite 數據庫，存儲所有 GSC 數據
- **`gsc_credentials.json`** - GSC 認證信息
- **`gsc_simple.log`** - 運行日誌
- **`app.log`** - 舊版日誌文件

## 🔄 項目演進

### 從 Web 應用到 CLI 工具

1. **簡化架構** - 移除前端和 Web 服務器
2. **聚焦功能** - 專注於數據同步和管理
3. **提升穩定性** - 簡化依賴和錯誤處理
4. **新增功能** - 支援 2025 年每小時數據

### 模塊化設計

- **核心邏輯分離** - API 客戶端與數據庫操作分開
- **功能獨立** - 每個模塊職責明確
- **易於維護** - 代碼結構清晰，文檔完整

## 📖 更多信息

查看各文檔了解詳細信息：

- **使用說明**：`docs/README_CLI.md`
- **配額分析**：`docs/DATABASE_SETUP_AND_QUOTA_ANALYSIS.md`
- **優化過程**：`docs/OPTIMIZATION_SUMMARY.md`
- **代碼改善**：`docs/CODE_QUALITY_IMPROVEMENTS.md`
