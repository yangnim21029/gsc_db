# 📁 專案結構詳細說明

## 🏗️ 整體架構

```
gsc_db/
├── 📄 根目錄檔案
├── 📁 配置和數據
├── 📁 文檔和報告
├── 📁 源碼
└── 📁 測試和日誌
```

## 📄 根目錄檔案

### 核心檔案

- `main.py` - 專案入口點，CLI 主程序
- `README.md` - 專案主要文檔，包含使用說明和功能介紹
- `requirements.txt` - Python 依賴包列表，按功能分組

### 開發工具配置

- `.gitignore` - Git 忽略規則，確保敏感檔案不被提交
- `.vscode/settings.json` - VS Code 編輯器配置
- `.cursor/rules/` - Cursor AI 編輯器規則配置

## 📁 配置和數據目錄

### `config/` - 配置檔案

```
config/
├── client_secret.json      # Google API 客戶端密鑰
└── gsc_credentials.json    # GSC API 認證檔案
```

- 存放所有敏感配置檔案
- 被 `.gitignore` 忽略，不會提交到版本控制

### `data/` - 數據檔案

```
data/
└── gsc_data.db            # SQLite 數據庫檔案
```

- 存放所有 GSC 數據
- 包含站點信息、每日排名、每小時數據等

## 📁 文檔和報告目錄

### `docs/` - 文檔目錄

```
docs/
├── README_CLI.md                    # CLI 使用說明
├── CLI_MIGRATION_GUIDE.md           # CLI 遷移指南
├── CLI_REFACTORING_SUMMARY.md       # CLI 重構總結
├── ANALYTICS_REFACTORING_SUMMARY.md # 分析模組重構總結
├── HOURLY_ANALYZER_REFACTORING.md  # 每小時分析重構總結
├── REPORT_COMMAND_ENHANCEMENT.md    # 報告命令增強總結
├── PROJECT_STRUCTURE_REFACTORING.md # 專案結構重構總結
├── PROJECT_CLEANUP_SUMMARY.md       # 專案清理總結
├── CODE_QUALITY_IMPROVEMENTS.md     # 代碼質量改進總結
├── OPTIMIZATION_SUMMARY.md          # 優化總結
├── DATABASE_SETUP_AND_QUOTA_ANALYSIS.md # 數據庫設置和配額分析
├── PROJECT_STRUCTURE.md             # 專案結構說明
└── example_usage.py                 # CLI 使用範例腳本
```

### `reports/` - 生成的報告和圖表

```
reports/
├── assets/                          # 圖表檔案目錄
│   ├── *.png                       # 靜態圖表
│   ├── *.html                      # 互動式圖表
│   └── *.md                        # 站點特定報告
├── 2025_June_GSC_Report.md         # 月度報告
├── 2025_June_Hourly_Report.md      # 每小時報告
├── gsc_report.md                   # 默認報告
└── gsc_weekly_report_*.md          # 週度報告
```

## 📁 源碼目錄 (`src/`)

### `src/config.py` - 集中配置管理

- 定義所有路徑常量
- 數據庫連接配置
- 日誌配置
- 圖表保存路徑

### `src/analysis/` - 分析模組

```
src/analysis/
├── __init__.py
├── analytics_report_builder.py      # 分析報告構建器
├── hourly_performance_analyzer.py   # 每小時表現分析器
└── interactive_data_visualizer.py   # 互動式數據可視化器
```

### `src/cli/` - 命令行界面

```
src/cli/
├── __init__.py
└── commands.py                      # 所有 CLI 命令定義
```

### `src/jobs/` - 批量作業

```
src/jobs/
├── __init__.py
└── bulk_data_synchronizer.py        # 批量數據同步器
```

### `src/services/` - 服務層

```
src/services/
├── __init__.py
├── database.py                      # 數據庫操作服務
├── gsc_client.py                    # GSC API 客戶端
├── hourly_data.py                   # 每小時數據服務
└── hourly_database.py               # 每小時數據庫操作
```

### `src/utils/` - 工具函數

```
src/utils/
├── __init__.py
└── system_health_check.py           # 系統健康檢查
```

## 📁 測試和日誌目錄

### `tests/` - 測試檔案

```
tests/
├── __init__.py
├── test_integration.py              # 整合測試
└── test_report_integration.py       # 報告整合測試
```

### `logs/` - 日誌檔案

```
logs/
├── app.log                          # 應用程序日誌
└── gsc_simple.log                   # GSC 操作日誌
```

## 🔄 數據流

### 1. 數據同步流程

```
GSC API → gsc_client.py → database.py → gsc_data.db
```

### 2. 報告生成流程

```
gsc_data.db → analytics_report_builder.py → reports/
```

### 3. 每小時分析流程

```
gsc_data.db → hourly_performance_analyzer.py → reports/assets/
```

### 4. CLI 命令流程

```
main.py → cli/commands.py → 相應服務模組 → 結果輸出
```

## 🛡️ 安全考慮

### 敏感檔案保護

- `config/` 目錄被 `.gitignore` 忽略
- 認證檔案不會提交到版本控制
- 數據庫檔案在本地管理

### 路徑管理

- 所有路徑通過 `src/config.py` 統一管理
- 避免硬編碼路徑
- 支持跨平台兼容

## 📊 檔案統計

- **總檔案數**: 79 個
- **目錄數**: 17 個
- **Python 檔案**: 約 20 個
- **文檔檔案**: 約 15 個
- **配置檔案**: 2 個
- **數據檔案**: 1 個
- **圖表檔案**: 約 30 個

## 🎯 設計原則

### 1. 模組化設計

- 每個模組職責單一
- 清晰的依賴關係
- 易於測試和維護

### 2. 配置集中化

- 所有配置在 `src/config.py` 中管理
- 支持環境變數覆蓋
- 便於部署和配置

### 3. 文檔完整性

- 每個重要變更都有文檔記錄
- 使用範例和最佳實踐
- 清晰的 API 文檔

### 4. 版本控制友好

- 合理的 `.gitignore` 規則
- 清晰的提交歷史
- 分支管理策略

## 🚀 擴展指南

### 添加新功能

1. 在相應模組中實現功能
2. 在 `src/cli/commands.py` 中添加命令
3. 更新文檔和測試
4. 更新 `requirements.txt`（如需要）

### 添加新分析類型

1. 在 `src/analysis/` 中創建新模組
2. 實現分析邏輯
3. 在 CLI 中添加對應命令
4. 添加測試用例

### 添加新數據源

1. 在 `src/services/` 中創建新的客戶端
2. 更新數據庫結構
3. 添加數據同步邏輯
4. 更新相關分析模組
