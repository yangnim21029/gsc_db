# GSC 業務腳本

> **專為特定業務需求設計的一次性分析工具**

這個資料夾包含了一次性的業務腳本，用於處理特定的分析需求，讓您能夠快速獲得所需的數據洞察。

## 🚀 快速開始

最簡單的使用方式：

```bash
# 1. 查看可用站點
just site-list

# 2. 執行 Sitemap 冗餘分析（以站點 ID 14 為例）
just sitemap-redundancy --site-id 14

# 3. 查看結果
ls -la data/  # 查看生成的 Excel 報告
```

## 🔍 Sitemap 冗餘分析工具

### 功能說明

`sitemap_redundancy_analyzer.py` 是一個強大的分析工具，專門用於：

1. **智能 Sitemap 發現**：自動從 robots.txt 和常見路徑發現所有有效的 Sitemaps
2. **高效 URL 提取**：並發處理 Sitemap 索引，快速提取所有 URL
3. **數據覆蓋分析**：分析 Sitemap URL 與 GSC 數據的覆蓋情況
4. **多工作表 Excel 報告**：生成包含詳細分析的 Excel 報告

### 使用方法

#### 基本用法

```bash
# 使用 just 命令（推薦）
just sitemap-redundancy --site-id 14

# 或者直接使用 Python
poetry run python scripts/sitemap_redundancy_analyzer.py --site-id 14

# 指定查詢天數範圍
just sitemap-redundancy --site-id 14 --days 30

# 指定自訂輸出路徑（Excel格式）
just sitemap-redundancy --site-id 14 --output-csv "reports/analysis.xlsx"

# 手動指定 sitemap URL
just sitemap-redundancy --site-id 14 --sitemap-url "https://example.com/sitemap.xml"
```

#### 直接使用 Python 腳本

```bash
# 完整命令
poetry run python scripts/sitemap_redundancy_analyzer.py \
    --site-id 14 \
    --sitemap-url "https://example.com/sitemap.xml" \
    --output-csv "reports/analysis.xlsx" \
    --days 30
```

### 參數說明

| 參數                      | 必需   | 說明                                                                |
| ------------------------- | ------ | ------------------------------------------------------------------- |
| `--site-id`               | 必需   | 要分析的網站 ID                                                     |
| `--sitemap-url`           | 選擇性 | 手動指定 Sitemap URL（可多次使用）                                  |
| `--days`                  | 選擇性 | 查詢天數範圍（預設查詢全部時間）                                    |
| `--output-csv`            | 選擇性 | 輸出檔案路徑（.xlsx=Excel 多工作表，預設輸出 Excel 到 data/資料夾） |
| `--interactive-discovery` | 選擇性 | 強制進行交互式 Sitemap 選擇                                         |
| `--single-sitemap`        | 選擇性 | 只使用第一個發現的 sitemap                                          |
| `--no-smart-discovery`    | 選擇性 | 暫停智能 Sitemap 發現功能，需要手動指定 --sitemap-url               |

### 輸出格式

生成的 Excel 報告包含以下工作表：

#### 1. 分析報告

包含完整的統計摘要：

- 網站名稱、網站 ID
- Sitemap 總 URL 數、去重後獨立 URL 數
- GSC performace 中的獨立 URL 數
- 擁有/沒有 GSC performace 的 URL 數量
- 冗餘率、覆蓋率
- 查詢時間範圍、實際有數據天數

#### 2. 有 GSC performace 的 URL

列出所有在 GSC 資料庫中有數據的 URL（已進行 URL 編碼）

#### 3. 無 GSC performace URL

列出所有在 Sitemap 中但 GSC 資料庫無數據的 URL（冗餘 URL）

#### 4. 每月平均表現表

包含有數據 URL 的詳細月度表現：

- URL（已編碼）、月份
- **總點擊數**、**總曝光數**（加總，非平均）
- 平均點擊率、平均排名
- 記錄數
- **該月份所有關鍵字**（換行分隔）
- **該月份關鍵字數**

### 實際執行範例

```bash
$ just sitemap-redundancy --site-id 14

🔍 智能 Sitemap 發現
目標域名: https://holidaysmart.io

✅ 找到有效 Sitemap: https://holidaysmart.io/sitemap.xml
📄 檢測到 Sitemap 索引，包含 3 個子 sitemap，開始並發處理...
✅ 成功提取 72,439 個 URL
🔄 去重後: 49,317 個 URL

📊 GSC 資料庫統計 (全部時間)
🎯 有數據的獨立頁面URL數: 41,434 個

🔍 正在進行冗餘分析...
✅ 有數據的 Sitemap URL: 3,142
❌ 無數據的 Sitemap URL: 46,175
冗餘率: 93.6%
覆蓋率: 6.4%

📈 正在獲取每月平均表現數據...
✅ 獲取 1,250 條月度表現記錄

💾 詳細分析報告已儲存至: data/sitemap_redundancy_holidaysmart_20241201_143022.xlsx
```

### 查看可用站點

```bash
# 查看所有站點列表
just site-list

# 或使用 Python
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
2. **Sitemap 自動發現**：如果未指定 Sitemap URL，腳本會智能發現所有可用的 Sitemaps
3. **支援 Sitemap 索引**：腳本支援遞歸解析 Sitemap 索引文件，並發處理提高效率
4. **數據覆蓋率**：腳本會顯示 Sitemap URL 與資料庫數據的詳細覆蓋率統計
5. **Excel 格式**：關鍵字欄位支持自動換行，URL 已進行編碼便於使用
6. **Git 忽略**：生成的報告會被 Git 忽略，不會被提交到版本控制

### 故障排除

#### 常見問題

1. **找不到站點**：確認站點 ID 是否正確，使用 `just site-list` 查看可用站點
2. **Sitemap 無法訪問**：檢查網站的 Sitemap URL 是否可訪問
3. **無成效數據**：確認該站點是否有同步過 GSC 數據

#### 獲取幫助

```bash
# 查看完整幫助
just sitemap-help

# 查看腳本幫助
poetry run python scripts/sitemap_redundancy_analyzer.py --help
```

## 📁 檔案結構

```
scripts/
├── README.md                           # 本文件
├── sitemap_redundancy_analyzer.py      # Sitemap 冗餘分析工具
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
  <strong>💡 提示：</strong> 這個工具提供了全面的 Sitemap 分析功能，包括冗餘率分析、每月表現統計、關鍵字分析等，是 GSC 數據分析的強大助手。
</p>
