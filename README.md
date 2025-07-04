# 🚀 GSC CLI - Google Search Console 數據管理工具

> **企業級 GSC 數據分析工具** | **18 個專業命令** | **自動化報告生成** | **每小時數據分析**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Typer](https://img.shields.io/badge/Typer-0.9.0-green.svg)](https://typer.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 目錄

- [🚀 新手快速開始](#-新手快速開始)
- [⚡ 常用命令速查](#-常用命令速查)
- [📊 功能特色](#-功能特色)
- [📈 基礎使用範例](#-基礎使用範例)
- [🐛 常見問題解決](#-常見問題解決)
- [🔧 進階配置](#-進階配置)
- [🏗️ 專案架構](#️-專案架構)
- [📚 深度指南](#-深度指南)

## 🚀 新手快速開始

### 第一步：安裝環境

```bash
git clone <your-repo-url>
cd gsc_db
pip install -r requirements.txt
```

### 第二步：設置認證

```bash
python main.py auth
```

### 第三步：查看可用站點

```bash
python main.py sites
```

### 第四步：同步數據

```bash
python main.py sync
```

### 第五步：生成分析報告

```bash
python main.py report
```

**🎉 恭喜！您已成功設置並開始使用 GSC CLI 進行數據分析**

## ⚡ 常用命令速查

| 功能           | 命令                            | 說明                  |
| -------------- | ------------------------------- | --------------------- |
| **認證設置**   | `python main.py auth`           | 進行 Google API 認證  |
| **站點管理**   | `python main.py sites`          | 列出所有可用的站點    |
| **數據同步**   | `python main.py sync`           | 從 GSC 同步數據到本地 |
| **報告生成**   | `python main.py report`         | 生成數據分析報告      |
| **每小時分析** | `python main.py analyze-hourly` | 分析每小時數據趨勢    |
| **查看進度**   | `python main.py progress`       | 查看同步任務進度      |
| **查看日誌**   | `python main.py logs`           | 查看系統運行日誌      |

## 📊 功能特色

### 🎯 核心功能

- ✅ **18 個專業命令** - 完整的 GSC 數據管理解決方案
- ✅ **自動化數據同步** - 批量獲取和處理 GSC 數據
- ✅ **智能報告生成** - 多種報告類型和自定義選項
- ✅ **每小時數據分析** - 精細化時間維度數據分析
- ✅ **美觀的輸出界面** - Rich 庫提供的彩色表格和進度條

### 🛠️ 技術特色

- 🎨 **現代化命令行界面** - 基於 Typer 框架的專業體驗
- 🔍 **智能命令提示** - 自動補全和詳細的幫助信息
- 🛡️ **類型安全保障** - 完整的類型提示和參數驗證
- 📊 **內建數據可視化** - 自動生成圖表和報告
- ⚡ **高性能處理** - 優化的數據處理和存儲流程

## 📈 基礎使用範例

### 🔄 數據同步操作

```bash
# 同步最近7天的數據
python main.py sync

# 同步特定站點的數據
python main.py sync --site-url "https://example.com"
```

### 📊 報告生成操作

```bash
# 生成月度分析報告（默認選項）
python main.py report

# 生成週度分析報告
python main.py report weekly

# 生成關鍵字專項分析報告
python main.py report keyword
```

### ⏰ 每小時數據分析

```bash
# 生成每小時趨勢分析圖（默認選項）
python main.py analyze-hourly

# 生成每日每小時熱力圖分析
python main.py analyze-hourly --type heatmap
```

### 📊 圖表生成操作

```bash
# 生成點擊趨勢圖表
python main.py plot --type clicks --days 30

# 將圖表保存到指定文件
python main.py plot --type clicks --save "clicks_trend.png"
```

## 🐛 常見問題解決

### 1. 認證失敗問題

```bash
# 解決方案：重新進行認證設置
python main.py auth
```

### 2. 數據庫連接錯誤

```bash
# 解決方案：檢查 API 狀態和連接
python main.py api-status
```

### 3. 內存不足問題

```bash
# 解決方案：減少分析數據量，不生成圖表
python main.py report --days 7 --no-plots
```

### 4. 找不到站點問題

```bash
# 解決方案：檢查站點列表和權限
python main.py sites
```

## 🔧 進階配置

### 系統環境要求

- Python 3.8 或更高版本
- Google Search Console API 訪問權限
- 至少 100MB 可用磁盤空間

### 環境變量配置

```bash
# 設置 Google API 憑證文件路徑
export GOOGLE_APPLICATION_CREDENTIALS="config/client_secret.json"

# 設置數據庫文件路徑
export GSC_DB_PATH="data/gsc_data.db"
```

### 開發工具安裝（可選）

```bash
pip install flake8 black pytest
```

## 🏗️ 專案架構

```
gsc_db/
├── 📄 核心檔案
│   ├── main.py              # 命令行工具入口點
│   ├── README.md            # 項目主要文檔
│   ├── requirements.txt     # Python 依賴包列表
│   └── .gitignore          # Git 版本控制忽略規則
├── 📁 配置和數據
│   ├── config/             # 敏感配置檔案目錄
│   └── data/               # 數據庫檔案存儲目錄
├── 📁 文檔
│   ├── EXECUTIVE_SUMMARY.md        # 高階主管摘要報告
│   ├── DEVELOPMENT_GUIDE.md        # 開發者指南
│   └── PROJECT_STRUCTURE_DETAILED.md # 詳細架構說明
├── 📁 報告輸出
│   ├── 生成的報告檔案 (.md)
│   └── assets/             # 圖表檔案存儲目錄
├── 📁 源碼 (src/)
│   ├── analysis/           # 數據分析模組
│   ├── cli/               # 命令行界面模組
│   ├── jobs/              # 批量作業處理模組
│   ├── services/          # 核心服務層模組
│   ├── utils/             # 工具函數模組
│   └── config.py          # 集中配置管理
└── 📁 測試和日誌
    ├── tests/             # 測試檔案目錄
    └── logs/              # 系統日誌目錄
```

## 📚 深度指南

### 批量數據操作

```bash
# 批量同步多個站點的月度數據
python main.py bulk-sync --site-id 1 2 3 4 --year 2024 --month 6

# 為多個站點生成月度報告
for site_id in 1 2 3; do
    python main.py report monthly --site-url "site$site_id.com" --output "site${site_id}_report.md"
done
```

### 自動化腳本示例

```bash
#!/bin/bash
# 每日自動化數據同步和報告生成腳本

# 同步最新一天的數據
python main.py sync --days 1

# 生成每日分析報告
python main.py report daily --days 1 --output "daily_report_$(date +%Y%m%d).md"

# 生成每小時趨勢分析
python main.py analyze-hourly --type trends --days 1
```

### 自定義配置選項

```bash
# 使用自定義數據庫文件
python main.py sync --db "custom_data.db"

# 自定義圖表輸出目錄
python main.py report --plot-dir "my_plots"

# 自定義報告輸出路徑
python main.py report --output "reports/my_report.md"
```

### 性能優化建議

```bash
# 分批處理大量數據以優化內存使用
python main.py sync --days 30 --batch-size 1000

# 生成報告時不包含圖表以節省處理時間
python main.py report --no-plots

# 限制每小時分析的數據範圍以提升性能
python main.py analyze-hourly --days 3
```

### 日誌監控和分析

```bash
# 查看系統錯誤日誌
python main.py logs --error-only --lines 50

# 實時監控特定時間段的錯誤日誌
tail -f logs/gsc_simple.log | grep "ERROR"
```

### 數據庫結構說明

#### 主要數據表格

- `daily_rankings`: 每日關鍵字排名數據存儲
- `hourly_rankings`: 每小時關鍵字排名數據存儲
- `page_data`: 頁面表現數據存儲
- `sites`: 站點基本信息存儲

#### 數據類型分類

- **點擊數據**: 頁面點擊次數統計和趨勢分析
- **排名數據**: 關鍵字在搜索引擎中的排名變化
- **覆蓋數據**: 頁面在搜索引擎中的索引覆蓋情況
- **每小時數據**: 精細化時間維度的數據分析

### 最佳實踐建議

#### 1. 定期數據同步

```bash
# 建議每日進行數據同步以保持數據最新
python main.py sync --days 1
```

#### 2. 定期報告生成

```bash
# 生成週度分析報告
python main.py report weekly

# 生成月度分析報告
python main.py report monthly
```

#### 3. 數據備份策略

```bash
# 定期備份數據庫文件
cp data/gsc_data.db data/gsc_data_backup_$(date +%Y%m%d).db
```

#### 4. 系統監控

```bash
# 監控數據同步任務進度
python main.py progress
```

### 開發者指南

#### 開發環境設置

```bash
# 安裝項目依賴包
pip install -r requirements.txt

# 運行測試套件
python -m pytest tests/

# 檢查代碼質量和風格
python -m flake8 src/
```

#### 代碼提交規範

- 使用清晰明確的提交信息
- 包含相應的測試用例
- 及時更新相關文檔

## 📄 許可證

本項目採用 MIT 許可證 - 詳見 [LICENSE](LICENSE) 文件。

## 🆘 技術支持

### 獲取幫助的方式

1. 查看 [常見問題解決](#-常見問題解決) 部分
2. 運行 `python main.py --help` 查看所有可用命令
3. 查看 [深度指南](#-深度指南) 獲取更多使用範例

### 聯繫和支持渠道

- 提交問題報告: [GitHub Issues](../../issues)
- 查詢技術文檔: [docs/](docs/) 目錄
- 開發者指南: [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md)

---

**🎉 開始使用 GSC CLI 進行專業的數據分析！**

> 💡 **溫馨提示**: 首次使用時，請先運行 `python main.py auth` 進行認證設置。
