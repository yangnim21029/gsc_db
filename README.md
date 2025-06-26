# GSC 數據管理工具

一個功能完整的 Google Search Console (GSC) 數據分析和管理工具，提供命令行和互動式操作界面。

## 📁 文件結構

### 主要工具

- **`gsc_main.py`** - 🚀 **主程序** (推薦使用)

  - 提供友好的互動式選單
  - 適合新手用戶
  - 整合所有功能

- **`gsc_cli_manager.py`** - 🛠️ **CLI 管理器**
  - 命令行工具，支援所有基本操作
  - 支援批次處理和腳本化
  - 有參數時直接執行，無參數時提供互動模式

### 分析工具

- **`gsc_report_generator.py`** - 📈 **報告生成器**

  - 生成月度分析報告
  - 關鍵字和頁面效能分析
  - 自動生成圖表和統計

- **`gsc_hourly_analyzer.py`** - ⏰ **小時分析器**

  - 每小時數據趨勢分析
  - 時段效能比較
  - 峰值時間識別

- **`gsc_interactive_charts.py`** - 🎯 **互動圖表生成器**
  - 關鍵字氣泡圖
  - 多站點比較圖
  - 互動式 HTML 圖表

### 數據管理

- **`gsc_batch_syncer.py`** - 📊 **批量同步工具**

  - 多站點批量數據同步
  - 自動錯誤重試
  - 進度監控

- **`gsc_status_checker.py`** - 📋 **狀態檢查器**
  - 系統狀態總覽
  - 數據覆蓋檢查
  - API 連接測試

## 🚀 快速開始

### 1. 最簡單的方式 (推薦)

```bash
python gsc_main.py
```

啟動互動式主選單，跟隨提示操作即可。

### 2. 命令行方式

```bash
# 查看所有可用命令
python gsc_cli_manager.py --help

# 開始認證
python gsc_cli_manager.py auth

# 查看站點
python gsc_cli_manager.py sites

# 同步數據
python gsc_cli_manager.py sync --all-sites --start-date 2024-01-01 --end-date 2024-01-31
```

### 3. 無參數互動模式

如果你忘記了參數，直接運行命令，工具會引導你輸入：

```bash
python gsc_cli_manager.py add-site
# 會提示你輸入站點 URL

python gsc_cli_manager.py plot
# 會讓你選擇站點和圖表類型
```

## 📊 主要功能

### 🔑 API 認證管理

- GSC API 認證設置
- 連接狀態測試
- 重新認證

### 🌐 站點管理

- 查看所有可用站點
- 添加新站點到數據庫
- 檢查站點數據覆蓋情況

### 📊 數據同步

- **快速同步**: 最近 7 天所有站點
- **自定義同步**: 指定日期範圍和站點
- **批量同步**: 智能批量處理
- **每小時數據**: 更精細的時間分析

### 📈 數據分析與報告

- 月度綜合報告
- 關鍵字趨勢分析
- 頁面效能分析
- 自定義圖表生成

### 🎯 互動式圖表

- 關鍵字氣泡圖
- 多站點比較圖
- 頁面效能象限圖
- HTML 互動圖表

### 🛠️ 系統工具

- API 使用狀態監控
- 系統日誌查看
- 數據庫維護
- 狀態健康檢查

## 📱 使用場景

### 日常監控

```bash
# 每日檢查
python gsc_status_checker.py

# 查看最近趨勢
python gsc_cli_manager.py plot --site-id 1 --type clicks --days 7
```

### 月度報告

```bash
# 生成完整報告
python gsc_report_generator.py

# 互動式報告生成
python gsc_main.py
# 選擇 "4. 📈 數據分析與報告" -> "1. 生成月度報告"
```

### 數據同步

```bash
# 快速同步最近一週
python gsc_cli_manager.py sync --all-sites --start-date 2024-12-01 --end-date 2024-12-07

# 或使用互動模式
python gsc_main.py
# 選擇 "3. 📊 數據同步" -> "1. 快速同步"
```

### 深度分析

```bash
# 每小時趨勢分析
python gsc_hourly_analyzer.py

# 生成互動圖表
python gsc_interactive_charts.py
```

## 🔧 設置需求

### 依賴安裝

```bash
pip install -r requirements.txt
```

### API 認證

1. 獲取 Google Search Console API 憑證
2. 將憑證文件命名為 `client_secret.json`
3. 運行認證流程：
   ```bash
   python gsc_cli_manager.py auth
   ```

## 📁 輸出文件

- **報告**: Markdown 格式的分析報告
- **圖表**: PNG 格式的靜態圖表 (保存在 `assets/` 目錄)
- **互動圖表**: HTML 格式的互動圖表
- **日誌**: 系統運行日誌 (`*.log` 文件)

## 💡 貼心提示

1. **新手推薦**: 使用 `python gsc_main.py` 開始，有完整的引導界面
2. **自動化**: 使用 `gsc_cli_manager.py` 配合 cron 進行定期數據同步
3. **忘記參數**: 所有主要命令都支援無參數互動模式
4. **錯誤處理**: 工具會自動重試和錯誤恢復
5. **數據安全**: 資料庫文件已被 .gitignore 排除，不會被意外提交

## 🎯 最佳實踐

1. **每日運行狀態檢查**: `python gsc_status_checker.py`
2. **週度數據同步**: 使用快速同步功能
3. **月度深度分析**: 生成完整報告和互動圖表
4. **問題排查**: 查看系統日誌了解詳細信息

---

如有問題，請查看 `docs/` 目錄中的詳細文檔或運行 `python gsc_main.py` 使用互動式幫助。
