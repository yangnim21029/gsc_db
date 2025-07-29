# GSC Data - Parquet + DuckDB 極簡版

最簡單的 Google Search Console 資料儲存和查詢方案。

## 架構

- **sync.py** - 同步 GSC 資料到 Parquet 檔案
- **app.py** - Flask API 提供查詢端點
- **gsc_mcp.py** - MCP 工具給 Claude 使用（包含所有查詢函數）
- **test.py** - 測試腳本

## 安裝

使用 Poetry 管理套件：

```bash
# 安裝 Poetry（如果還沒安裝）
curl -sSL https://install.python-poetry.org | python3 -

# 安裝專案套件
poetry install

# 進入虛擬環境
poetry shell
```

或使用傳統 pip：

```bash
pip install -r requirements.txt
```

## 設定認證

1. 到 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立或選擇專案
3. 啟用 Google Search Console API
4. 建立 OAuth 2.0 用戶端 ID（類型選「桌面應用程式」）
5. 下載憑證並命名為 `client_secret.json`

第一次執行時會開啟瀏覽器要求授權，之後會自動使用儲存的 token。

## 使用方式

### 1. 同步資料

```bash
# 同步網站的所有歷史資料（最多 16 個月）
poetry run python sync.py https://example.com
poetry run python sync.py sc-domain:example.com

# 或使用安裝的指令（如果已經 poetry install）
poetry run gsc-sync https://example.com
```

特點：
- 從最舊的資料開始同步
- 已存在的檔案會自動跳過
- 支援多站點（資料按站點分資料夾）
- 自動處理超過 25,000 筆的資料（分批抓取）
- 配額管理（每 10 個請求休息，自動重試配額錯誤）

資料結構：
```
data/
├── sc-domain_example.com/
│   ├── 2024-01/
│   │   ├── 2024-01-01.parquet
│   │   └── 2024-01-02.parquet
│   └── 2024-02/
└── https___example.com_/
    └── 2024-01/
```

### 2. 查詢資料

#### Flask API

```bash
# 啟動 API 伺服器
poetry run python app.py 5000

# 或使用安裝的指令
poetry run gsc-api 5000

# 追蹤特定頁面和關鍵字
curl -X POST http://localhost:5000/track_pages \
  -H "Content-Type: application/json" \
  -d '{
    "site": "sc-domain:example.com",
    "pages": ["/blog/python-guide", "/tutorial/"],
    "keywords": ["python", "tutorial"],
    "days": 7
  }'

# 比較時間段（本週 vs 上週）
curl -X POST http://localhost:5000/compare_periods \
  -H "Content-Type: application/json" \
  -d '{
    "site": "sc-domain:example.com",
    "period_type": "week"
  }'

# 查詢頁面實際排名的關鍵字
curl -X POST http://localhost:5000/pages_queries \
  -H "Content-Type: application/json" \
  -d '{
    "site": "sc-domain:example.com",
    "pages": ["/blog/python-guide", "/tutorial/"]
  }'
```

#### Python 直接查詢

```python
from gsc_mcp import track_pages, compare_periods, pages_queries

# 追蹤頁面
results = track_pages(
    site="sc-domain:example.com",
    pages=["/blog/", "/tutorial/"],
    keywords=["python"],
    days=30
)

# 比較時間段
result = compare_periods(site="sc-domain:example.com", period_type="week")
print(f"點擊變化: {result['clicks_change_pct']:.1f}%")

# 查詢頁面的關鍵字
results = pages_queries(
    site="sc-domain:example.com",
    pages=["/blog/python-guide", "/tutorial/"]
)
```

#### DuckDB SQL 查詢

```python
import duckdb

conn = duckdb.connect()
df = conn.execute("""
    SELECT * FROM 'data/*/*/*/*.parquet' 
    WHERE query ILIKE '%python%' 
    AND clicks > 10
    ORDER BY date DESC
""").fetchdf()
```

### 3. MCP 工具（給 Claude）

```bash
# 啟動 MCP 服務
poetry run python gsc_mcp.py

# 或使用安裝的指令
poetry run gsc-mcp

# 在 Claude Desktop 設定檔加入：
{
  "mcpServers": {
    "gsc": {
      "command": "python",
      "args": ["/path/to/gsc_mcp.py"]
    }
  }
}
```

提供的工具：
- `query` - 執行任意 SQL（AI 可自由撰寫）
- `show_page_queries` - 查看頁面的搜尋詞
- `show_keyword_pages` - 查看關鍵字的排名頁面
- `search_keywords` - 查詢包含特定模式的關鍵字
- `best_pages` - 查詢時間段內表現最好的頁面
- `track_pages` - 追蹤一組頁面和關鍵字
- `pages_queries` - 查詢頁面實際排名的關鍵字
- `compare_periods` - 比較時間段（本週vs上週、本月vs上月）

## 測試

```bash
# 執行測試腳本
poetry run python test.py
```

會測試：
1. OAuth 認證和資料同步
2. DuckDB 查詢
3. API 服務

## 就這樣

極簡設計，先跑起來再說。有問題再優化。