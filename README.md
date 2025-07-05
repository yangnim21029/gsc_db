# GSC CLI - Google Search Console 數據管理工具

GSC CLI 是一個功能強大的命令行工具，旨在簡化 Google Search Console (GSC) 數據的獲取、存儲、分析和報告流程。

## 🚀 功能特色

- ✅ **流式處理架構** - 以極低的記憶體佔用處理海量數據，解決單次請求大量數據導致的崩潰問題。
- ✅ **自動化數據同步** - 批量獲取和處理 GSC 數據，支持多站點、多日期範圍。
- ✅ **斷點續傳** - 在同步中斷後，可從上次成功的位置無縫繼續。
- ✅ **靈活的同步模式** - 支持 `upsert`, `skip`, `replace` 等多種數據寫入策略。
- ✅ **時段對比分析** - 比較兩個不同時間段的關鍵字或頁面表現。
- ✅ **美觀的輸出界面** - Rich 庫提供的彩色表格和進度條。
- ✅ **每小時數據分析** - 精細化時間維度數據分析。

## 🛠️ 技術特色

- **現代化 CLI 框架**: 使用 [Typer](https://typer.tiangolo.com/) 構建，提供類型提示和自動文檔生成。
- **高性能數據庫**: 使用 SQLite 進行本地數據存儲，並通過優化查詢和索引保證性能。
- **異步與並發**: 利用 `concurrent.futures` 進行並發處理，提高數據同步效率。
- **專業級日誌**: 集成 `rich.logging`，提供結構化、易於閱讀的日誌輸出。
- **模塊化設計**: 清晰的服務分層 (`services`, `jobs`, `analysis`)，易於擴展和維護。

## 📦 安裝

```bash
# 1. 克隆倉庫
git clone https://github.com/your-username/gsc-cli.git
cd gsc-cli

# 2. 創建虛擬環境 (推薦)
python -m venv venv
source venv/bin/activate  # on Windows, use `venv\Scripts\activate`

# 3. 安裝依賴
pip install -r requirements.txt
```

## 🎯 基本用法

### 1. 認證

首次使用時，需要進行 Google API 認證。

```bash
python main.py site auth
```

### 2. 同步數據

同步指定站點最近 7 天的數據。

```bash
python main.py sync daily --site-url "sc-domain:your-site.com" --days 7
```

## 深度指南

### 報告生成

您可以通過 `report` 命令生成一份詳細的 GSC 表現報告，支持 Markdown 格式輸出和圖表生成。

```bash
# 為指定站點 ID 生成報告
python main.py analyze report --site-id 1 --output-path "reports/my_site_report.md" --days 30
```

### 時段對比分析

您可以直接使用 `AnalysisService` 來比較兩個不同時間段的數據表現，找出增長或衰退的項目。

```python
#!/usr/bin/env python
# 示例：比較本週與上週的關鍵字點擊變化

from src.services.database import Database
from src.services.analysis_service import AnalysisService
from datetime import date, timedelta

# 1. 初始化服務
db = Database()
analysis_service = AnalysisService(db)

# 2. 定義時間段
today = date.today()
# 本週 (最近7天)
period2_end = today
period2_start = today - timedelta(days=6)
# 上週 (再往前7天)
period1_end = period2_start - timedelta(days=1)
period1_start = period1_end - timedelta(days=6)

# 3. 執行比較
comparison_data = analysis_service.compare_performance_periods(
    site_id=1, # 替換為您的站點 ID
    period1_start=period1_start.strftime('%Y-%m-%d'),
    period1_end=period1_end.strftime('%Y-%m-%d'),
    period2_start=period2_start.strftime('%Y-%m-%d'),
    period2_end=period2_end.strftime('%Y-%m-%d'),
    group_by='query', # 或 'page'
    limit=10 # 找出變化最大的前10名
)

# 4. 打印結果
print(f"比較 {period1_start} ~ {period1_end} 與 {period2_start} ~ {period2_end} 的關鍵字表現：")
for item in comparison_data:
    print(
        f"關鍵字: {item['item']:<40} | "
        f"點擊變化: {item['clicks_change']:+5.0f} "
        f"({item['period1_clicks']} -> {item['period2_clicks']})"
    )
```

## 自動化腳本示例

您可以使用 `scripts/daily_maintenance.sh` 腳本來自動化每日的數據同步、備份和清理工作。

```bash
bash scripts/daily_maintenance.sh
```

## 數據庫結構說明

#### 主要數據表

- `gsc_performance_data`: 核心性能數據表，包含點擊、曝光、排名等綜合維度。
- `hourly_rankings`: 每小時關鍵字排名數據存儲。
- `sites`: 站點基本信息存儲。
- `keywords`: 關鍵字基本信息存儲。

## 貢獻

歡迎提交 Pull Requests 或開 Issues！

## 許可證

[MIT](LICENSE)

---

## ⚙️ 核心概念與使用說明

### 首次使用：認證流程

本工具需要獲取您的授權才能訪問 Google Search Console (GSC) 數據。首次使用或憑證失效時，您需要進行一次性手動認證。

1.  **啟動認證**：在終端機中運行以下指令：
    ```bash
    gsc-db auth login
    ```
2.  **瀏覽器授權**：
    - 指令會輸出一串 URL。請將此 URL 複製並貼到您的網頁瀏覽器中打開。
    - 登入您要管理的 GSC 所屬的 Google 帳戶。
    - 在 Google 的授權頁面，點擊「允許」，以授權本工具訪問您的 GSC 數據。
3.  **獲取授權碼**：
    - 授權後，瀏覽器會跳轉到一個本地地址（例如 `http://localhost:8000/...`），頁面可能會顯示無法連線。**這是正常現象**。
    - 請從瀏覽器頂部的地址欄中，找到 `code=` 後面的那串長長的代碼，並將其**完整**複製下來。它看起來像這樣：`4/0AVHEtkbJ...`
4.  **完成認證**：
    - 回到您的終端機，將剛剛複製的授權碼貼上，然後按下 Enter。
    - 程式會自動用此授權碼換取永久有效的憑證，並將其儲存於專案根目錄下的 `token.json` 檔案中。

完成以上步驟後，您就可以在任何地方（包括 crontab 等非互動式環境中）運行 `scripts/full_sync.py` 等腳本，程式將會自動刷新憑證，無需再次手動登入。

### GSC 資源使用策略：域名屬性 vs. URL 字首屬性

在 GSC 中，有兩種主要的網站屬性類型，了解它們的區別對於數據的準確性至關重要。

- **域名屬性 (Domain Property)**

  - **格式**：`sc-domain:example.com`
  - **涵蓋範圍**：包含該域名下**所有**的子網域（如 `www.example.com`, `m.example.com`）和所有協定（`http://`, `https://`）。
  - **優點**：提供了一個網站最全面、最完整的數據視圖，避免了數據的分散和遺漏。
  - **推薦用法**：**這是我們強烈推薦使用的屬性類型。** 只要您在 GSC 中驗證了域名屬性，就應該只使用它來進行數據同步。

- **URL 字首屬性 (URL-prefix Property)**
  - **格式**：`https://example.com/` 或 `http://www.example.com/blog/`
  - **涵蓋範圍**：僅限於您所指定的、完全匹配的 URL 字首。例如，`http://example.com/` 的數據**不包含** `https://example.com/` 的數據。
  - **使用時機**：
    1.  當您因為某些原因**無法**在 GSC 中驗證整個域名時。
    2.  當您只想針對網站的某個特定部分（例如某個國家的子目錄）進行獨立分析時。

**核心原則**：為了避免數據重複計算和儲存冗餘，如果一個網站的**域名屬性**（如 `sc-domain:girlstyle.com`）已經存在，則**不應該**再單獨添加其下的任何**URL 字首屬性**（如 `https://girlstyle.com/tw/` 或 `https://girlstyle.com/sg/`）。我們的 `full_sync.py` 腳本中的站點列表已根據此原則進行了清理。
