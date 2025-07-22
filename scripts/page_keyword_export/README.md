# 頁面關鍵字成效導出工具

這個工具用於從 GSC 數據庫 API 導出頁面成效數據，包含每個 URL 的關鍵字列表和成效指標。

## 功能特點

- 獲取所有有成效的 URL 及其關鍵字數據
- 按總點擊數降序排序
- 支持通過 site_id 或 hostname 識別網站
- 可選的時間範圍過濾
- 導出為 CSV 格式（支持中文）
- 每個 URL 一行，包含該頁面的所有關鍵字

## 檔案說明

- `export_page_keywords_to_csv_zh.py` - 中文版本（推薦使用）
- `export_page_keywords_to_csv.py` - 英文版本
- `exports/` - 導出文件存放目錄

## 使用方法

### 1. 確保 API 服務器正在運行

```bash
# 在項目根目錄執行
just dev-server
```

### 2. 執行導出腳本

```bash
# 在項目根目錄執行
python3 scripts/page_keyword_export/export_page_keywords_to_csv_zh.py
```

### 3. 自定義參數

編輯腳本中的配置部分：

```python
SITE_ID = 14      # 更改為您的網站 ID
DAYS = 30         # 最近 30 天，設為 None 表示所有時間
MAX_RESULTS = 5000  # 最多獲取的結果數
```

### 4. 使用域名導出

腳本底部提供了使用域名導出的示例函數：

```python
# 取消註釋以使用
export_by_hostname("example.com", days=30)
export_by_hostname("sc-domain:example.com", days=90)
```

## 輸出格式

- 文件名：`頁面關鍵字_網站{ID}_{時間戳}.csv`
- 每個 URL 一行
- 關鍵字以 ` | ` 分隔顯示在同一格

## 輸出欄位

- **網址**：頁面 URL
- **總點擊數**：該頁面的總點擊次數
- **總曝光數**：該頁面的總曝光次數
- **平均點擊率**：點擊率百分比
- **平均排名**：在搜索結果中的平均位置
- **關鍵字數量**：驅動流量到該頁面的關鍵字總數
- **關鍵字列表**：所有關鍵字（不再限制數量）

## 注意事項

1. API 響應時間可能較長（30-60秒），特別是處理大量數據時
2. 使用 utf-8-sig 編碼確保 Excel 正確顯示中文
3. 確保網站 ID 存在且有數據

## 故障排除

### API 連接失敗

- 確認服務器正在運行
- 檢查 BASE_URL 是否正確（默認 http://localhost:8000）

### 網站 ID 不存在

- 使用 `curl http://localhost:8000/api/v1/sites/` 查看可用網站列表

### 導出文件亂碼

- 使用支持 UTF-8 的編輯器打開
- 在 Excel 中通過「數據」->「從文本」導入並選擇 UTF-8 編碼
