<p align="center">
  <img src="gsc_service_banner.jpg" alt="GSC Database Manager Banner" width="100%">
</p>

# GSC Database Manager

<p align="center">
  企業級 Google Search Console 數據管理與分析工具
</p>
<p align="center">
    <a href="https://github.com/your-username/gsc_db/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/your-username/gsc_db?style=flat-square"></a>
    <a href="https://python.org"><img alt="Python Version" src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square"></a>
    <a href="https://github.com/astral-sh/ruff"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square"></a>
</p>

> **我們的使命：** 賦予開發者、行銷人員與網站主完全掌控其 Google Search Console 數據的能力。我們相信，長期的數據所有權是解鎖深度洞察、並為網站優化建構下一代 AI 驅動工具的關鍵。

本專案提供了一個強大的命令列介面 (CLI) 和 API，用以自動化擷取、儲存和備份您的 GSC 數據，為您打造一個由您自己控制的、永久的個人數據倉庫。

## ✨ 核心功能

- **長期數據所有權**: 打破 GSC 16 個月的數據保留限制，建立您自己的歷史數據檔案庫
- **自動化數據同步**: 定期擷取 GSC 數據（搜尋分析、每小時數據、網站地圖等）並儲存於本地 SQLite 資料庫
- **每小時精細數據**: 支援 GSC 的每小時數據 API，提供更精細的時間粒度分析
- **穩健的備份機制**: 自動建立資料庫的壓縮備份，並清理舊的備份
- **強大的命令列介面**: 易於使用的指令，涵蓋身份驗證、數據同步與日常維護
- **API 就緒**: 內建 FastAPI 伺服器，為您的 AI Agent 或 Web UI 提供數據接口
- **現代化開發工具**: 整合 Ruff、mypy、pytest、pre-commit hooks 等最佳實踐
- **整合任務執行器**: 附帶預先配置好的 `justfile`，簡化開發與操作流程

## 🚀 快速開始

### 前提條件

本專案使用現代化的 Python 開發工具鏈：

- **Python 3.11+**
- **Poetry** (依賴管理)
- **Just** (任務執行器)

安裝必要工具：

```bash
# macOS (使用 Homebrew)
brew install just poetry

# 或者使用 pipx 安裝 Poetry
pipx install poetry
```

### 安裝步驟

1.  **複製倉庫**

    ```bash
    git clone https://github.com/your-username/gsc_db.git
    cd gsc_db
    ```

2.  **一鍵安裝與設定 (推薦)**

    此指令將使用 Poetry 安裝所有依賴，並引導您完成首次 Google API 身份驗證：

    ```bash
    just bootstrap
    ```

3.  **設定 Google API 認證**

    您需要在 Google Cloud Console 中建立專案並下載 OAuth2 憑證文件：

    ```bash
    # 將您的 client_secret.json 放在 cred/ 目錄下
    cp path/to/your/client_secret.json cred/

    # 執行認證流程
    just auth
    ```

    **⚠️ 重要提醒：OAuth 認證流程說明**

    當您執行 `just auth` 時，系統會：

    1. 提供一個 Google 授權 URL，請在瀏覽器中打開
    2. 完成授權後，Google 會重定向到 `http://localhost:8000/auth/callback`
    3. **這個頁面會顯示「無法連上這個網站」- 這是正常的！**
    4. 請從瀏覽器地址欄複製 `code=` 後面的完整授權碼
    5. 將授權碼貼回終端機以完成認證

    這是一個**手動複製授權碼**的認證流程，不需要啟動本地服務器。

## 🎯 基本用法

所有常用操作都已封裝為 `just` 任務。執行 `just --list` 可以查看所有可用的指令。

### 1. 查看可用指令

```bash
# 列出所有可用的 just 任務
just --list
```

### 2. 站點管理

```bash
# 列出所有已配置的站點（本地數據庫 + 遠程 GSC 帳戶）
just site-list

# 新增一個站點到本地數據庫
just site-add "sc-domain:your-site.com"
```

### 3. 數據同步

```bash
# 同步站點 ID 為 1 的最近 7 天數據
just sync-site 1 7

# 同步站點 ID 為 1 的最近 14 天數據
just sync-site 1 14

# 批次同步多個站點（站點 ID: 1, 3, 5）
just sync-multiple "1 3 5"

# 執行完整的每日維護程序（同步所有站點、備份資料庫、清理舊備份）
just maintenance
```

### 4. 開發與測試

```bash
# 執行所有品質檢查（程式碼風格、類型檢查、測試）
just check

# 只執行測試
just test

# 只執行類型檢查
just type-check

# 程式碼格式化
just lint
```

## 🤖 API 服務

本專案包含一個 FastAPI 伺服器，可作為未來 AI Agent 或 Web 儀表板的數據後端。

### 啟動服務

```bash
# 啟動開發伺服器（具備自動重載功能）
just dev-server

# 啟動生產伺服器
just prod-server
```

### API 文檔

伺服器運行後，請在瀏覽器中打開：

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 🛠️ 開發環境

### 設定開發環境

```bash
# 安裝依賴（包括開發依賴）
just setup

# 安裝 pre-commit hooks
poetry run pre-commit install

# 執行完整檢查
just check
```

### 專案結構

```
gsc_db/
├── src/                    # 主要源碼
│   ├── analysis/          # 數據分析模組
│   ├── cli/               # CLI 指令
│   ├── services/          # 核心服務（GSC 客戶端、數據庫等）
│   ├── utils/             # 工具函數
│   └── web/               # FastAPI Web 服務
├── tests/                 # 測試文件
├── cred/                  # 認證文件（不包含在版本控制中）
├── data/                  # 數據庫文件
├── logs/                  # 日誌文件
├── reports/               # 分析報告
└── justfile              # 任務定義
```

### 品質保證

本專案採用現代化的 Python 開發最佳實踐：

- **Ruff**: 快速的 linting 和格式化
- **mypy**: 靜態類型檢查
- **pytest**: 測試框架（支援並行執行）
- **pre-commit**: Git hooks 自動檢查
- **Poetry**: 依賴管理和虛擬環境

## 🧪 測試

```bash
# 執行所有測試
just test

# 執行特定測試
poetry run pytest tests/test_integration.py -v

# 執行測試並生成覆蓋率報告
poetry run pytest --cov=src tests/
```

## 📊 數據分析功能

本專案支援多種數據分析功能：

```bash
# 使用 CLI 進行數據分析
poetry run gsc-cli analyze coverage 1
poetry run gsc-cli analyze compare 1 2023-01-01 2023-01-07 2023-01-08 2023-01-14

# 互動式數據視覺化
poetry run python -m src.analysis.interactive_data_visualizer

# 每小時性能分析
poetry run python -m src.analysis.hourly_performance_analyzer
```

## 🛣️ 發展藍圖

- [ ] **整合 AI Agent**: 開發一個對話式 AI 代理，能用自然語言回答關於您 GSC 數據的問題
- [ ] **進階數據分析**: 新增更多內建的分析腳本與報告（趨勢偵測、異常警報）
- [ ] **支援更多數據源**: 整合其他數據來源，如 Google Analytics, Ahrefs 或 Semrush
- [ ] **Web 儀表板**: 建立一個簡單的網頁介面，用以視覺化數據並與 AI Agent 互動
- [ ] **插件系統**: 允許使用者輕鬆地加入自訂的數據擷取器或分析模組

## 🤝 如何貢獻

我們誠摯歡迎任何形式的貢獻！請查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解詳細的貢獻指南。

### 開發流程

1. Fork 此倉庫
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的修改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

### 程式碼品質

在提交 PR 之前，請確保：

```bash
# 所有檢查都通過
just check

# 測試覆蓋率良好
just test
```

## 📄 授權條款

本專案採用 MIT 授權條款。詳情請見 [LICENSE](LICENSE) 文件。

---

<p align="center">
  如果這個專案對您有幫助，請給我們一個 ⭐️！
</p>
