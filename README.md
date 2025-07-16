<p align="center">
  <img src="gsc_service_banner.jpg" alt="GSC Database Manager Banner" width="100%">
</p>

# GSC Database Manager

<p align="center">
  <strong>完全掌控您的 Google Search Console 數據</strong>
</p>
<p align="center">
    <a href="https://github.com/your-username/gsc_db/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/your-username/gsc_db?style=flat-square"></a>
    <a href="https://python.org"><img alt="Python Version" src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square"></a>
    <a href="https://github.com/astral-sh/ruff"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square"></a>
</p>

打破 GSC 16 個月數據限制，建立您專屬的永久數據倉庫。支援自動同步、每小時精細數據、API 服務，為 SEO 分析和 AI 驅動工具提供完整的數據基礎。

## 🎯 為什麼選擇 GSC Database Manager？

<table>
<tr>
<td width="50%">

**🔒 完全的數據所有權**

- 永久保存歷史數據
- 本地 SQLite 資料庫
- 無第三方依賴風險

**⚡ 自動化 & 高效能**

- 智能增量同步
- 每小時精細數據
- 企業級錯誤處理

</td>
<td width="50%">

**🤖 AI/API 就緒**

- 內建 FastAPI 服務
- 標準化數據格式
- 支援批量分析

**🛠️ 開發者友好**

- 現代 Python 工具鏈
- 完整測試覆蓋
- 詳細文檔指南

</td>
</tr>
</table>

## 🆕 最新更新亮點

- **多站點同步系統**: 支援日級和小時級數據的批次同步，序列化處理確保 GSC API 穩定性
- **進度監控**: 實時同步狀態 `poetry run gsc-cli sync status` 和進度指示器
- **智能錯誤恢復**: 自動重試、SSL 錯誤處理和故障排除建議
- **靈活同步模式**: 支援 skip 和 overwrite 模式，滿足不同需求

## ✨ 核心功能

- **永久數據保存**: 突破 Google 16 個月限制，使用 SQLite 本地儲存
- **每小時精細數據**: 使用 Google 官方 API 獲取最細緻的流量數據
- **智能自動同步**: 排程系統，避免重複下載，支援斷點續傳
- **企業級錯誤處理**: 指數退避重試機制，SSL 錯誤自動恢復
- **標準化 API 接口**: RESTful API，JSON 格式，支援 AI 工具集成
- **多格式匯出**: 支援 Excel/CSV 匯出，無廠商綁定

## 🚀 快速開始

### 📋 5 分鐘快速上手

1. **安裝工具**: `Python 3.11+` + `Poetry`
2. **克隆專案**: `git clone <repo-url> && cd gsc_db`
3. **一鍵設定**: `poetry install && poetry run gsc-cli auth login`
4. **開始同步**: `poetry run gsc-cli sync daily --site-id 1 --days 7`
5. **查看狀態**: `poetry run gsc-cli sync status`

### 前提條件

- **Python 3.11+**
- **Poetry** (依賴管理)

```bash
# macOS (使用 Homebrew)
brew install poetry

# 或者使用 pipx 安裝 Poetry
pipx install poetry
```

#### Windows 系統安裝指南

1. **安裝 Python 3.11+**: 前往 [Python 官網](https://www.python.org/downloads/) 下載並安裝（勾選「Add Python to PATH」）

2. **安裝 Poetry**:
   ```powershell
   # 使用 PowerShell 安裝 Poetry
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

   # 或使用 pip 安裝
   pip install poetry
   ```

3. **驗證安裝**:
   ```powershell
   python --version    # 應顯示 Python 3.11+
   poetry --version    # 應顯示 Poetry 版本
   ```

#### Linux 系統安裝指南

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3-pip
pip3 install poetry

# CentOS/RHEL/Fedora
dnf install python3.11 python3-pip
pip3 install poetry
```

### 安裝步驟

1. **複製倉庫**
   ```bash
   git clone https://github.com/your-username/gsc_db.git
   cd gsc_db
   ```

2. **一鍵安裝與設定**
   ```bash
   poetry install
   poetry run gsc-cli auth login
   ```

3. **設定 Google API 認證**

   **在 Google Cloud Console 設置專案**：

   1. 前往 [Google Cloud Console](https://console.cloud.google.com/) 建立新專案
   2. 啟用 **Google Search Console API**
   3. 設定 OAuth 同意畫面：
      - 選擇用戶類型（External 或 Internal）
      - 填寫應用名稱和聯絡資訊
      - 添加測試使用者
   4. 建立 OAuth 2.0 憑證：
      - 選擇「Desktop application」
      - 下載 JSON 文件

   **設置本地憑證**：
   ```bash
   # 將下載的憑證文件重新命名並放入 cred/ 目錄
   cp ~/Downloads/client_secret_xxxxx.json cred/client_secret.json

   # 執行認證流程
   poetry run gsc-cli auth login
   ```

### 🔧 常見問題與解決方案

#### Windows 系統特別注意事項

```powershell
# 執行政策問題
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 路徑分隔符號
cp "C:\Users\YourName\Downloads\client_secret_xxxxx.json" "cred\client_secret.json"
```

#### 常見錯誤與解決方法

- **API 未啟用**：確認已在 Google Cloud Console 啟用 Google Search Console API
- **憑證檔案不存在**：確認 `client_secret.json` 位於 `cred/` 目錄下
- **權限被拒絕**：確認您的 Google 帳號有權存取要同步的網站
- **SSL/網路連接問題**：系統會自動重試和處理網路錯誤

#### 驗證設定

```bash
# 驗證認證
poetry run gsc-cli site list

# 測試同步功能
poetry run gsc-cli sync status
```

## 🎯 基本用法

### 最常用的 5 個指令

#### macOS/Linux:
```bash
# 1. 查看所有站點狀態 (最重要!)
poetry run gsc-cli sync status

# 2. 同步單個站點
poetry run gsc-cli sync daily --site-id 1 --days 7

# 3. 批次同步多個站點
poetry run gsc-cli sync multiple "1 3 5" --days 7

# 4. 小時級批次同步
poetry run gsc-cli sync hourly-multiple "1 3 5" --days 2

# 5. 查看所有可用指令
poetry run gsc-cli --help
```

#### Windows （如果上面命令不工作）:
```powershell
# 1-5. 相同指令，但改用：
poetry run python -m src.app sync status
poetry run python -m src.app sync daily --site-id 1 --days 7
# ... 其他指令類似替換
```

### 站點管理

```bash
# 列出所有已配置的站點
poetry run gsc-cli site list

# 新增一個站點到本地數據庫
poetry run gsc-cli site add "sc-domain:your-site.com"
```

### 數據同步

#### 基本同步操作
```bash
# 同步單個站點最近 7 天數據
poetry run gsc-cli sync daily --site-id 1 --days 7

# 批次同步多個站點 (日級數據)
poetry run gsc-cli sync multiple "1 3 5" --days 7

# 批次同步多個站點 (小時級數據)
poetry run gsc-cli sync hourly-multiple "1 3 5" --days 2

# 查看同步狀態和進度監控
poetry run gsc-cli sync status              # 查看所有站點狀態
poetry run gsc-cli sync status 5            # 查看特定站點狀態
```

#### 同步模式選擇
```bash
# Skip 模式 (預設) - 跳過已存在的數據
poetry run gsc-cli sync daily --site-id 5 --days 7 --sync-mode skip

# Overwrite 模式 - 強制更新所有數據
poetry run gsc-cli sync daily --site-id 5 --days 7 --sync-mode overwrite

# 小時級數據強制覆蓋
poetry run gsc-cli sync hourly-multiple "4 5 6" --days 1 --force
```

### 開發與測試

```bash
# 執行所有品質檢查
poetry run ruff check . && poetry run mypy . && poetry run pytest

# 只執行測試
poetry run pytest

# 程式碼格式化
poetry run ruff format .
```

## 🤖 API 服務

本專案包含一個 FastAPI 伺服器，可作為 AI Agent 或 Web 儀表板的數據後端。

### 啟動服務

```bash
# 啟動開發伺服器（具備自動重載功能）
poetry run uvicorn src.web.api:app --reload

# 啟動生產伺服器
poetry run uvicorn src.web.api:app
```

### API 文檔

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 🛠️ 開發環境

### 設定開發環境

```bash
# 安裝依賴（包括開發依賴）
poetry install

# 安裝 pre-commit hooks
poetry run pre-commit install

# 執行完整檢查
poetry run ruff check . && poetry run mypy . && poetry run pytest
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
└── pyproject.toml        # Poetry 依賴定義
```

### 品質保證

- **Ruff**: 快速的 linting 和格式化
- **mypy**: 靜態類型檢查
- **pytest**: 測試框架（支援並行執行）
- **pre-commit**: Git hooks 自動檢查
- **Poetry**: 依賴管理和虛擬環境

## 🧪 測試

本專案具有全面的測試套件，包括單元測試、整合測試和 README 功能驗證測試。

```bash
# 執行所有測試
poetry run pytest

# 執行特定測試
poetry run pytest tests/test_integration.py -v

# 執行測試並生成覆蓋率報告
poetry run pytest --cov=src tests/

# 驗證 README.md 中所有功能的可用性
poetry run pytest tests/test_readme_functionality.py -v
```

**測試特色：**
- ✅ **無掛起問題**：已解決 SQLite 事務死鎖，測試穩定運行
- ✅ **全面覆蓋**：包括 CLI 命令、API 端點、數據庫操作和並發處理
- ✅ **README 驗證**：自動驗證文檔中提到的所有功能都能正常工作

## 📊 數據分析功能

```bash
# 使用 CLI 進行數據分析
poetry run gsc-cli analyze report 1 --days 7
poetry run gsc-cli analyze compare 1 2023-01-01 2023-01-07 2023-01-08 2023-01-14

# 互動式數據視覺化
poetry run python -m src.analysis.interactive_data_visualizer

# 每小時性能分析
poetry run python -m src.analysis.hourly_performance_analyzer
```

## 🛣️ 發展藍圖

- [ ] **整合 AI Agent**: 開發對話式 AI 代理，用自然語言回答 GSC 數據問題
- [ ] **進階數據分析**: 新增內建分析腳本與報告（趨勢偵測、異常警報）
- [ ] **支援更多數據源**: 整合 Google Analytics、Ahrefs 或 Semrush
- [ ] **Web 儀表板**: 建立網頁介面，視覺化數據並與 AI Agent 互動
- [ ] **插件系統**: 允許使用者輕鬆加入自訂的數據擷取器或分析模組

## 🤝 如何貢獻

歡迎任何形式的貢獻！請查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解詳細的貢獻指南。

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
poetry run ruff check . && poetry run mypy . && poetry run pytest

# 測試覆蓋率良好
poetry run pytest --cov=src
```

## 📄 授權條款

本專案採用 MIT 授權條款。詳情請見 [LICENSE](LICENSE) 文件。

---

<p align="center">
  如果這個專案對您有幫助，請給我們一個 ⭐️！
</p>
