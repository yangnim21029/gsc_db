# GSC-CLI

<p align="center">
  您的個人 Google Search Console 數據倉庫與 AI 分析平台
</p>
<p align="center">
    <a href="https://github.com/your-username/gsc-cli/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/your-username/gsc-cli?style=flat-square"></a>
    <a href="https://github.com/your-username/gsc-cli/actions/workflows/ci.yml"><img alt="CI Status" src="https://img.shields.io/github/actions/workflow/status/your-username/gsc-cli/ci.yml?branch=main&style=flat-square"></a>
    <a href="https://python.org"><img alt="Python Version" src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square"></a>
</p>

> **我們的使命：** 賦予開發者、行銷人員與網站主完全掌控其 Google Search Console 數據的能力。我們相信，長期的數據所有權是解鎖深度洞察、並為網站優化建構下一代 AI 驅動工具的關鍵。

本專案提供了一個強大的命令列介面 (CLI) 和 API，用以自動化擷取、儲存和備份您的 GSC 數據，為您打造一個由您自己控制的、永久的個人數據倉庫。

## ✨ 核心功能

- **長期數據所有權**: 打破 GSC 16 個月的數據保留限制，建立您自己的歷史數據檔案庫。
- **自動化數據同步**: 定期擷取 GSC 數據（搜尋分析、網站地圖等）並儲存於本地 SQLite 資料庫。
- **穩健的備份機制**: 自動建立資料庫的壓縮備份，並清理舊的備份。
- **強大的命令列介面**: 易於使用的指令，涵蓋身份驗證、數據同步與日常維護。
- **API 就緒**: 內建 FastAPI 伺服器，為您的 AI Agent 或 Web UI 提供數據接口。
- **整合任務執行器**: 附帶預先配置好的 `justfile`，簡化開發與操作流程。

## 🚀 快速開始

### 前提條件

本專案使用 `just` 作為指令執行器，以簡化常見任務。請先確保您已安裝 `just`。

- **macOS (使用 Homebrew):**
  ```bash
  brew install just
  ```
- **其他系統:**
  請參考 [Just 官方安裝說明](https://just.systems/man/en/chapter_4.html)。

### 安裝步驟

1.  **複製倉庫**

    ```bash
    git clone https://github.com/your-username/gsc-cli.git
    cd gsc-cli
    ```

2.  **一鍵安裝與設定 (推薦)**
    此指令將使用 Poetry 安裝所有依賴，並引導您完成首次 Google API 身份驗證。
    ```bash
    just bootstrap
    ```

## 🎯 基本用法

所有常用操作都已封裝為 `just` 任務。執行 `just --list` 可以查看所有可用的指令。

### 1. 站點管理

```bash
# 列出所有已配置的站點
just site-list

# 新增一個站點
just site-add "sc-domain:your-site.com"
```

### 2. 同步數據

```bash
# 同步站點 ID 為 1 的最近 14 天數據
just sync-site 1 14

# 執行完整的每日維護 (同步所有站點、備份資料庫、清理舊備份)
just maintenance
```

### 3. 數據分析

```bash
# 檢查站點 ID 為 1 的數據覆蓋情況
poetry run gsc-cli analyze coverage 1

# 比較站點 ID 為 1 在兩個時間段的表現
poetry run gsc-cli analyze compare 1 2023-01-01 2023-01-07 2023-01-08 2023-01-14
```

## 🤖 API 服務 (為 AI Agent 準備)

本專案包含一個 FastAPI 伺服器，可作為未來 AI Agent 或 Web 儀表板的數據後端。

1.  **啟動開發伺服器 (具備自動重載功能):**

    ```bash
    just dev server
    ```

2.  **查看 API 文檔:**
    伺服器運行後，請在瀏覽器中打開 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)，您將看到一個由 Swagger UI 生成的互動式 API 文檔。

## 🛣️ 發展藍圖 (Roadmap)

我們為這個專案規劃了激動人心的未來！我們的目標是將此工具發展為一個全面的網站數據分析平台。歡迎您從以下方向貢獻您的才華：

- [ ] **整合 AI Agent**: 開發一個對話式 AI 代理 (使用 LangChain, LlamaIndex 等)，能用自然語言回答關於您 GSC 數據的問題。
- [ ] **進階數據分析**：新增更多內建的分析腳本與報告（例如：趨勢偵測、異常警報）。
- [ ] **支援更多數據源**：整合其他數據來源，如 Google Analytics, Ahrefs 或 Semrush。
- [ ] **Web 儀表板**：建立一個簡單的網頁介面，用以視覺化數據並與 AI Agent 互動。
- [ ] **插件系統**：允許使用者輕鬆地加入自訂的數據擷取器或分析模組。

## 🤝 如何貢獻 (Contributing)

我們深信開源的力量，並誠摯歡迎任何形式的貢獻，無論是回報問題、建議新功能，還是直接提交程式碼。

一份好的貢獻開始於良好的溝通。您可以從查看 Issues 列表或我們上方的 **發展藍圖** 來尋找靈感。

在您開始動手前，請務必閱讀我們詳細的 **貢獻指南 (CONTRIBUTING.md)**，它包含了完整的開發流程、程式碼風格和 Pull Request 指南。

```bash
# 運行所有品質檢查 (格式化、類型檢查、測試)
just check
```

## 📄 授權條款 (License)

本專案採用 MIT 授權條款。詳情請見 [LICENSE](LICENSE) 文件。
