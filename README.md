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

### ✅ Windows 完全兼容支援

- **解決 Windows 多站點同步問題**: 修復了 bash 命令錯誤，現在 Windows 用戶可以正常進行批次同步
- **Windows 優化命令**: 新增 `batch-sync` 命令，專為 Windows 環境優化，包含詳細日誌記錄
- **跨平台進程管理**: 智能檢測作業系統，在 Windows 使用 PowerShell，Unix 系統使用 bash

### 📊 進度監控與狀態追蹤

- **實時同步狀態**: `just sync-status` 命令顯示所有站點的同步狀態和進度
- **進度指示器**: 批次同步時顯示 "站點 X / Y" 進度，包含耗時統計
- **智能錯誤恢復**: 失敗時提供具體的故障排除建議和下一步行動

### 🛡️ 增強的網路穩定性

- **多種同步模式**: `smart-sync`、`conservative-sync`、`adaptive-sync`、`turbo-sync`
- **自動 SSL 錯誤處理**: 智能檢測網路問題並自動調整同步策略
- **網路診斷工具**: `network-check` 命令協助診斷連接問題

### 📝 詳細日誌與追蹤

- **Windows 批次同步日誌**: 自動保存到 `data/logs/` 目錄，包含時間戳和詳細狀態
- **成功/失敗統計**: 批次操作完成後顯示詳細的成功率和失敗站點列表

## ✨ 核心功能

**📚 永久保存您的數據**

- 🏆 **再也不怕數據消失**: Google 只保留 16 個月，我們幫您永久保存
  _→ 採用 SQLite 資料庫存在您的電腦，檔案大小僅數 MB_
- 📈 **完整的歷史趨勢**: 看到網站 2-3 年的成長變化
  _→ 每日自動備份，壓縮存檔，佔用空間極小_
- 💾 **數據完全屬於您**: 存在您的電腦，隨時可用
  _→ 標準檔案格式，可匯出 Excel/CSV，無廠商綁定_

**⚡ 自動化讓工作更輕鬆**

- 🔄 **每日自動更新**: 設定一次，數據自動同步，無需手動操作
  _→ 內建排程系統，智能避開重複下載，節省時間_
- ⏰ **精確到小時**: 看到每個小時的流量變化，掌握最佳發布時機
  _→ 使用 Google 官方每小時 API，提供最細緻的數據_
- 🛡️ **智能錯誤處理**: 網路問題？沒關係，系統會自動重試
  _→ 指數退避重試機制，SSL 錯誤自動恢復_

**🚀 一鍵開始使用**

- 📱 **簡單命令**: 不需複雜設定，幾個指令就能開始
  _→ 封裝複雜邏輯為 `just` 命令，如 `just sync-site 1 7`_
- 📊 **現成報告**: 立即生成 Excel 報告，直接用於分析
  _→ 內建 pandas 處理，自動格式化，支援中文檔名_
- 🤖 **為 AI 分析準備**: 數據格式標準化，方便餵給 AI 工具分析
  _→ RESTful API 接口，JSON 格式，可直接對接 ChatGPT/Claude_

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

#### Windows 系統安裝指南

**Step 1: 安裝 Python 3.11+**

- 前往 [Python 官網](https://www.python.org/downloads/) 下載 Python 3.11 或更新版本
- 安裝時請勾選「Add Python to PATH」

**Step 2: 安裝 Poetry**

```powershell
# 使用 PowerShell 安裝 Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# 或使用 pip 安裝
pip install poetry
```

**Step 3: 安裝 Just (任務執行器)**

選擇以下其中一種方法安裝 Just：

```powershell
# 方法 1: 使用 Scoop (推薦)
# 先安裝 Scoop
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
# 然後安裝 Just
scoop install just

# 方法 2: 使用 Chocolatey
choco install just

# 方法 3: 使用 Cargo (如果已安裝 Rust)
cargo install just

# 方法 4: 手動下載 (如果其他方法都不行)
# 前往 https://github.com/casey/just/releases
# 下載 just-*-x86_64-pc-windows-msvc.zip
# 解壓並將 just.exe 放入 PATH 目錄
```

**Step 4: 驗證安裝**

```powershell
# 檢查所有工具是否正確安裝
python --version    # 應顯示 Python 3.11+
poetry --version    # 應顯示 Poetry 版本
just --version      # 應顯示 Just 版本
```

#### Linux 系統安裝指南

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3-pip
pip3 install poetry

# 安裝 Just
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin
# 或使用 Cargo
cargo install just

# CentOS/RHEL/Fedora
dnf install python3.11 python3-pip
pip3 install poetry
cargo install just
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
    # macOS / Linux / Windows (如果已安裝 Just)
    just bootstrap

    # Windows 替代方案 (如果 Just 安裝有問題)
    # 雙擊 setup.bat 檔案，或在 PowerShell/CMD 中執行：
    setup.bat
    ```

3.  **設定 Google API 認證**

    ### 步驟 3.1：在 Google Cloud Console 設置專案

    1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
    2. 建立新專案或選擇現有專案
    3. 啟用 **Google Search Console API**：
       - 前往「APIs & Services」→「Library」
       - 搜尋「Google Search Console API」或「Search Console API」
       - 點擊「Google Search Console API」結果
       - 點擊「啟用 (Enable)」按鈕
       - ⚠️ **重要**：請確保 API 狀態顯示為「已啟用」
       - 如果找不到 API，請確認您已選擇正確的 Google Cloud 專案
    4. **設定 OAuth 同意畫面** (必要步驟)：
       - 前往「APIs & Services」→「OAuth consent screen」
       - 選擇「External」用戶類型 (個人使用者) 或「Internal」(組織內部)
       - 填寫必要資訊：
         - **App name**: GSC Database Manager (或您偏好的名稱)
         - **User support email**: 您的 Gmail 地址
         - **Developer contact information**: 您的 Gmail 地址
       - 在「Scopes」頁面，無需新增額外範圍 (使用預設即可)
       - 在「Test users」頁面，添加您要使用此應用的 Gmail 帳號
       - 完成設定並儲存
    5. 建立 OAuth 2.0 憑證：
       - 前往「APIs & Services」→「Credentials」
       - 點擊「+ CREATE CREDENTIALS」→「OAuth client ID」
       - 選擇「Desktop application」
       - 填入應用程式名稱（例如：GSC Database Manager）
       - 下載 JSON 文件

    ### 步驟 3.2：設置本地憑證

    ```bash
    # 將下載的憑證文件重新命名並放入 cred/ 目錄
    cp ~/Downloads/client_secret_xxxxx.json cred/client_secret.json

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

### 🔧 常見設定問題與解決方案

#### Windows 系統特別注意事項

1. **PowerShell 執行政策問題**

   ```powershell
   # 如果遇到執行政策錯誤，執行以下命令
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **路徑分隔符號**
   ```powershell
   # Windows 使用反斜線，設定憑證時使用以下路徑格式
   cp "C:\Users\YourName\Downloads\client_secret_xxxxx.json" "cred\client_secret.json"
   ```

#### 🆕 Windows 同步問題解決方案

**❌ 錯誤：多站點同步 bash 命令失敗**

- **原因**：Windows 不支援 bash 腳本
- **解決方案**：使用新的 Windows 優化命令

  ```powershell
  # 使用 Windows 優化的批次同步
  just batch-sync "1 3 5" 7

  # 或使用 PowerShell 相容的進階同步
  just smart-sync 5 7
  ```

**❌ 錯誤：無法查看同步進度**

- **原因**：缺少進度監控命令
- **解決方案**：使用新的狀態監控功能

  ```powershell
  # 查看實時同步狀態
  just sync-status

  # 監控特定站點進度
  just sync-status 5

  # 檢查運行中的進程
  just check-processes
  ```

**⚠️ 注意：避免使用不當指令**

- ❌ **錯誤做法**：`just sync daily --day1 --all-sites` (這不是狀態查詢命令)
- ✅ **正確做法**：`just sync-status` (專門的狀態監控命令)

#### 常見錯誤與解決方法

**❌ 錯誤：「API 未啟用」**

- **解決方案**：確認已在 Google Cloud Console 啟用 Google Search Console API
- 檢查步驟：前往 APIs & Services → Dashboard，確認 API 顯示在已啟用列表中

**❌ 錯誤：「憑證檔案不存在」**

- **解決方案**：確認 `client_secret.json` 位於 `cred/` 目錄下
- 檢查命令：`ls cred/` (macOS/Linux) 或 `dir cred` (Windows)

**❌ 錯誤：「OAuth 同意畫面未設定」**

- **解決方案**：完成 OAuth consent screen 設定 (見上方步驟 4)
- 確認您的 Gmail 帳號已添加為測試使用者

**❌ 錯誤：「權限被拒絕」**

- **解決方案**：確認您的 Google 帳號有權存取要同步的網站
- 在 Google Search Console 中確認該網站的擁有者或使用者權限

**❌ Just 命令不存在 (Windows)**

- **解決方案**：
  1. 重新安裝 Just (參考上方 Windows 安裝指南)
  2. 使用 Windows 批次檔案：雙擊 `setup.bat` 進行初始化
  3. 或使用替代命令：`poetry run python -m src.app [參數]`

**❌ SSL/網路連接問題**

- **解決方案**：使用智能同步模式自動處理

  ```bash
  # 檢查網路狀態
  just network-check

  # 根據網路狀況選擇合適的同步模式
  just conservative-sync 5 7    # 網路不穩定時使用
  just smart-sync 5 7          # 一般推薦使用
  just turbo-sync 5 7          # 網路穩定時使用
  ```

#### 驗證設定是否正確

完成設定後，執行以下命令驗證：

```bash
# 1. 檢查專案結構
just init

# 2. 驗證認證
just site-list

# 3. 測試同步功能
just sync-status

# 4. 如果一切正常，應該會看到您 GSC 帳號中的網站列表
```

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

#### 基本同步操作

```bash
# 同步站點 ID 為 1 的最近 7 天數據
just sync-site 1 7

# 同步站點 ID 為 1 的最近 14 天數據
just sync-site 1 14

# 執行完整的每日維護程序（同步所有站點、備份資料庫、清理舊備份）
just maintenance
```

#### 🆕 增強批次同步 (支援 Windows)

```bash
# 批次同步多個站點，包含進度追蹤和錯誤處理
just sync-multiple "1 3 5" 7

# Windows 優化的批次同步，包含詳細日誌記錄
just batch-sync "1 3 5" 14

# 查看同步狀態和進度監控
just sync-status              # 查看所有站點狀態
just sync-status 5            # 查看特定站點狀態
```

#### 🛡️ 智能同步模式 (自動處理網路問題)

```bash
# 智能同步 - 自動處理 SSL 錯誤
just smart-sync 5 7

# 保守同步 - 單線程模式，適用於網路不穩定環境
just conservative-sync 5 7

# 自適應同步 - 根據網路狀況自動調整併發數
just adaptive-sync 5 7

# 高性能同步 - 適用於穩定網路環境
just turbo-sync 5 7
```

#### 🔧 進程管理和故障排除

```bash
# 檢查正在運行的同步進程
just check-processes

# 停止所有 GSC 相關進程
just kill-processes

# 檢查網路連接狀態
just network-check
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

本專案具有全面的測試套件，包括單元測試、整合測試和 README 功能驗證測試，確保所有功能的穩定性和可靠性。

```bash
# 執行所有測試（已解決並發死鎖問題，穩定運行）
just test

# 執行特定測試
poetry run pytest tests/test_integration.py -v

# 執行並行測試（可選，在某些情況下可能需要更多資源）
just test-parallel

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

本專案支援多種數據分析功能：

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

- [ ] **整合 AI Agent**: 開發一個對話式 AI 代理，能用自然語言回答關於您 GSC 數據的問題
- [ ] **進階數據分析**: 新增更多內建的分析腳本與報告（趨勢偵測、異常警報）
- [ ] **支援更多數據源**: 整合其他數據來源，如 Google Analytics, Ahrefs 或 Semrush
- [ ] **Web 儀表板**: 建立一個簡單的網頁介面，用以視覺化數據並與 AI Agent 互動
- [ ] **插件系統**: 允許使用者輕鬆地加入自訂的數據擷取器或分析模組

## 🚀 Windows 用戶快速開始指南

如果您是 Windows 用戶且希望快速開始使用本工具，可以按照以下步驟：

### 快速安裝 (Windows)

1. **下載並安裝 Python 3.11+**
   - 前往 [Python 官網](https://www.python.org/downloads/) 下載安裝
   - ✅ 記得勾選「Add Python to PATH」

2. **安裝 Poetry**
   ```powershell
   pip install poetry
   ```

3. **克隆專案並設置**
   ```powershell
   git clone <repository-url>
   cd gsc_db
   
   # 使用 Windows 批次檔案進行設置（如果 Just 安裝有問題）
   .\setup.bat
   
   # 或使用 Python 設置腳本
   python setup.py
   ```

4. **安裝依賴並認證**
   ```powershell
   poetry install
   poetry run gsc-cli auth login
   ```

5. **開始使用 Windows 優化命令**
   ```powershell
   # 添加第一個站點
   poetry run gsc-cli site add "sc-domain:your-site.com"
   
   # 查看同步狀態
   poetry run gsc-cli sync status
   
   # Windows 優化的批次同步
   poetry run python -m src.app sync daily --site-id 1 --days 7 --max-workers 1
   ```

### Windows 專用故障排除

如果遇到問題，請嘗試：

```powershell
# 檢查網路連接
poetry run python -c "from src.utils.system_health_check import check_network_connectivity; print(check_network_connectivity())"

# 查看詳細錯誤信息
poetry run gsc-cli --help
```

**💡 提示**: Windows 用戶建議使用 `batch-sync` 命令而非 `sync-multiple`，因為前者針對 Windows 環境做了特別優化。

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
