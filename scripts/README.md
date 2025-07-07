# GSC 業務腳本

> **專為特定業務需求設計的一次性分析工具**

這個資料夾包含了一次性的業務腳本，用於處理特定的分析需求，讓您能夠快速獲得所需的數據洞察。

## 🚀 快速開始

最簡單的使用方式：

```bash
# 1. 查看可用站點
just site-list

# 2. 執行 Sitemap 分析（以站點 ID 1 為例）
just sitemap-analysis --site-id 1 --output-file scripts/reports/my_analysis.csv

# 3. 查看結果
head -5 scripts/reports/my_analysis.csv
```

## 🔍 Sitemap URL 成效分析工具

### 功能說明

`sitemap_url_performance_exporter.py` 是一個強大的一次性腳本，專門用於：

1. **從 Sitemap 提取 URL**：自動解析站點的 Sitemap XML 文件，支持 Sitemap 索引
2. **查詢成效資料**：從 GSC 資料庫中查詢這些 URL 的成效數據
3. **生成 CSV 報告**：輸出詳細的成效分析報告

### 使用方法

#### 基本用法

```bash
# 使用站點 ID
just sitemap-analysis --site-id 1 --output-file scripts/reports/site1_analysis.csv

# 使用站點 URL (自動查找 ID)
just sitemap-analysis --site-url "https://example.com" --output-file scripts/reports/example_analysis.csv

# 指定查詢天數
just sitemap-analysis --site-id 1 --output-file scripts/reports/site1_analysis.csv --days 60

# 手動指定 Sitemap URL
just sitemap-analysis --site-id 1 --sitemap-url "https://example.com/sitemap.xml" --output-file scripts/reports/site1_analysis.csv
```

#### 直接使用 Python 腳本

```bash
# 完整命令
poetry run python scripts/sitemap_url_performance_exporter.py \
    --site-id 1 \
    --sitemap-url "https://example.com/sitemap.xml" \
    --output-file "scripts/reports/example_analysis.csv" \
    --days 30
```

### 參數說明

| 參數            | 必需     | 說明                                       |
| --------------- | -------- | ------------------------------------------ |
| `--site-id`     | 選擇性\* | 要查詢的網站的本地資料庫 ID                |
| `--site-url`    | 選擇性\* | 要查詢的網站 URL（自動查找站點 ID）        |
| `--sitemap-url` | 選擇性   | 指定 Sitemap URL（如果未提供，會自動發現） |
| `--output-file` | 必需     | 導出的 CSV 檔案路徑                        |
| `--days`        | 選擇性   | 查詢過去多少天的數據（預設：30 天）        |

\*註：`--site-id` 和 `--site-url` 必須提供其中一個

### 輸出格式

生成的 CSV 報告包含以下欄位：

- **URL**：從 Sitemap 中提取的網址
- **總點擊量**：該 URL 的總點擊數
- **總曝光量**：該 URL 的總曝光數
- **平均點閱率(%)**：平均點閱率百分比
- **平均排名**：平均搜尋排名
- **獨特查詢數**：觸發該 URL 的不同查詢數量
- **數據天數**：有數據的天數
- **最早日期**：最早的數據日期
- **最新日期**：最新的數據日期
- **在資料庫中**：該 URL 是否在資料庫中有成效數據

### 範例輸出

```csv
URL,總點擊量,總曝光量,平均點閱率(%),平均排名,獨特查詢數,數據天數,最早日期,最新日期,在資料庫中
https://example.com/page1,150,2500,6.0,12.5,25,30,2024-01-01,2024-01-30,是
https://example.com/page2,89,1800,4.94,18.2,18,28,2024-01-03,2024-01-30,是
https://example.com/page3,0,0,0,0,0,0,,,否
```

### 實際執行範例

以下是一個真實的執行結果：

```bash
$ just sitemap-analysis --site-id 5 --output-file scripts/reports/businessfocus_analysis.csv --days 7

🔍 正在執行 Sitemap URL 成效分析...
📊 站點資訊: BusinessFocus (businessfocus.io)
🌐 自動發現的 Sitemap URL: https://businessfocus.io/businessfocus_urlset.xml
📄 檢測到 Sitemap 索引，正在解析子 Sitemap...
✅ 成功提取 173,804 個 URL
🔍 正在查詢資料庫中的成效數據...
📈 找到 460 個 URL 有成效數據 (0.3% 覆蓋率)
💾 報告已儲存至: scripts/reports/businessfocus_analysis.csv
```

### 查看可用站點

```bash
# 查看所有站點列表
poetry run python -c "
from src.containers import Container
db = Container().database()
sites = db.get_sites()
print('可用站點:')
for s in sites:
    print(f'  ID: {s[\"id\"]}, 名稱: {s[\"name\"]}, 域名: {s[\"domain\"]}')
"
```

### 注意事項

1. **輸出目錄**：腳本會自動創建輸出目錄（如果不存在）
2. **Sitemap 自動發現**：如果未指定 Sitemap URL，腳本會嘗試從 `{domain}/sitemap.xml` 自動發現
3. **支援 Sitemap 索引**：腳本支援遞歸解析 Sitemap 索引文件
4. **數據覆蓋率**：腳本會顯示 Sitemap URL 與資料庫數據的覆蓋率統計
5. **Git 忽略**：生成的報告會被 Git 忽略，不會被提交到版本控制

### 故障排除

#### 常見問題

1. **找不到站點**：確認站點 ID 或 URL 是否正確
2. **Sitemap 無法訪問**：檢查 Sitemap URL 是否可訪問
3. **無成效數據**：確認該站點是否有同步過 GSC 數據

#### 獲取幫助

```bash
# 查看完整幫助
just sitemap-help

# 查看腳本幫助
poetry run python scripts/sitemap_url_performance_exporter.py --help
```

## 📁 檔案結構

```
scripts/
├── README.md                           # 本文件
├── sitemap_url_performance_exporter.py # Sitemap 成效分析工具
└── reports/                            # 生成的報告 (Git 忽略)
    └── *.csv                           # CSV 報告檔案
```

## 🔧 開發說明

這些腳本是為了處理特定的業務需求而創建的一次性工具。它們：

- 使用項目的現有服務和資料庫連接
- 遵循項目的程式碼風格和結構
- 輸出檔案會被 Git 忽略
- 可以通過 `just` 命令方便地使用

如果需要新的業務腳本，可以參考現有腳本的結構和模式。

---

<p align="center">
  <strong>💡 提示：</strong> 這些業務腳本與主專案的核心功能（analyze, sync）分離，專注於特定的一次性分析需求。
</p>
