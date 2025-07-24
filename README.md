# GSC Database Manager (Modernized 2025)

<p align="center">
  <strong>現代化的 Google Search Console 數據管理系統</strong>
</p>
<p align="center">
    <a href="https://python.org"><img alt="Python Version" src="https://img.shields.io/badge/python-3.12+-blue?style=flat-square"></a>
    <a href="https://github.com/astral-sh/ruff"><img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square"></a>
    <a href="https://litestar.dev/"><img alt="Litestar" src="https://img.shields.io/badge/framework-Litestar-purple?style=flat-square"></a>
</p>

**🚀 2025 年全面重構版本** - 採用最新技術棧，實現突破性性能提升：
- **3x API 性能**：808 RPS 峰值處理能力
- **10x 查詢速度**：DuckDB 分析引擎
- **100% GSC 同步可靠性**：經測試證實的順序處理架構

打破 GSC 16 個月數據限制，建立您專屬的高性能數據倉庫。

## 🎯 為什麼選擇現代化版本？

<table>
<tr>
<td width="50%">

**⚡ 極致性能**
- 808 RPS API 處理能力
- SQLite + DuckDB 混合架構
- msgspec 超快序列化

**🔒 數據安全與可靠性**
- 100% GSC API 同步成功率
- 永久本地數據保存
- 智能錯誤恢復機制

</td>
<td width="50%">

**🤖 現代化技術棧**
- Litestar 高性能 Web 框架
- 全異步架構支持
- OpenAPI/Swagger 文檔

**🛠️ 開發者體驗**
- 簡化的部署流程
- 完整的 API 測試工具
- 詳細的性能基準測試

</td>
</tr>
</table>

## 🆕 重構亮點

### 性能測試結果
```
並發用戶數    成功率    每秒請求數(RPS)    平均響應時間
1 用戶       100%      80.78 RPS         12.26ms
10 用戶      100%      499.05 RPS        15.84ms
30 用戶      100%      808.36 RPS        23.78ms  ← 最佳性能點
50 用戶      100%      611.4 RPS         55.46ms
```

### GSC API 並發限制發現
**經實測證實（2025-07-25）**：
- ✅ **順序執行**：100% 成功率
- ❌ **並發執行**：0% 成功率
- ⚠️ **批次執行**：62.5% 成功率

### 技術棧升級
| 組件 | 原版本 | 現代化版本 | 性能提升 |
|-----|-------|-----------|----------|
| Web 框架 | FastAPI | Litestar ^2.8.0 | 2-3x |
| 序列化 | Pydantic | msgspec ^0.18.0 | 5-10x |
| 數據處理 | pandas | Polars ^0.20.0 | 50-70% 記憶體減少 |
| 資料庫 | SQLite | SQLite + DuckDB | 10-100x 分析查詢 |

## 📋 Requirements

- Python 3.12+
- Poetry (dependency management)
- Google Search Console API credentials
- Redis (optional, for caching)

## 🛠️ Installation

### 快速安裝

1. **安裝 Poetry**
   ```bash
   # macOS
   brew install poetry

   # Linux
   curl -sSL https://install.python-poetry.org | python3 -

   # Windows
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```

2. **克隆並安裝**
   ```bash
   git clone <repository-url>
   cd gsc-db-refactor
   poetry install
   ```

3. **設置 Google API 憑證**
   ```bash
   # 將 Google Cloud Console 下載的憑證放入 cred/ 目錄
   cp ~/Downloads/client_secret_xxxxx.json cred/client_secret.json
   ```

## 🔧 Configuration

配置透過環境變數管理（可選）：

```env
# Database
GSC_DATABASE_PATH=./data/gsc_data.db
GSC_ENABLE_DUCKDB=true

# API
GSC_API_HOST=0.0.0.0
GSC_API_PORT=8000

# Cache (optional - 可選的 Redis 快取)
GSC_ENABLE_CACHE=false
GSC_REDIS_URL=redis://localhost:6379
```

大多數設置使用預設值即可正常運作。

## 🚀 Quick Start

### 1. 查看所有站點
```bash
# 使用 justfile (推薦)
just site-list

# 直接使用 Python 腳本
poetry run python sync.py list
```

### 2. 同步單個站點
```bash
# 使用 justfile
just sync-site 17 7 skip          # 站點ID 17，7天，skip模式

# 直接使用腳本
poetry run python sync.py sync 17 7 skip
```

### 3. 批次同步多個站點（順序處理）
```bash
# 使用 justfile
just sync-multiple "1,3,17" 7 skip

# 直接使用腳本
poetry run python sync_multiple.py "1,3,17" 7 skip
```

### 4. 啟動 API 服務
```bash
# 開發模式（自動重載）
just dev-server

# 生產模式
just prod-server
```

## 🌐 高性能 API 服務

### API 文檔與測試
- **Swagger UI**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/schema

### 主要端點

#### Sites Management
- `GET /api/v1/sites` - 列出所有站點
- `GET /api/v1/sites/{site_id}` - 獲取站點詳情
- `POST /api/v1/sites` - 添加新站點

#### Analytics (支援 hostname 和 site_id)
- `POST /api/v1/analytics/ranking-data` - 獲取排名數據（支援彈性篩選）
- `GET /api/v1/page-keyword-performance/` - 頁面關鍵字效果數據
- `GET /api/v1/page-keyword-performance/csv/` - CSV 格式下載

#### Sync Management
- `GET /api/v1/sync/status` - 檢查同步覆蓋狀態
- `POST /api/v1/sync/trigger` - 觸發異步同步任務

#### Monitoring
- `GET /health` - 健康檢查
- `GET /docs` - Swagger 文檔

### API 測試命令

```bash
# 健康檢查
just api-health

# 查看所有站點
just api-sites

# 測試查詢搜索（支援 hostname）
just api-query-search test.com keyword

# 測試頁面效果數據
just api-page-performance test.com

# 同步狀態檢查
just api-sync-status-hostname test.com
```

### API 特色功能

**支援 hostname 和 site_id 雙模式**：
```bash
# 使用 hostname（用戶友好）
curl -X POST http://localhost:8000/api/v1/analytics/ranking-data \
  -H "Content-Type: application/json" \
  -d '{"hostname": "test.com", "date_from": "2025-07-20", "date_to": "2025-07-25"}'

# 使用 site_id（高效能）
curl -X POST http://localhost:8000/api/v1/analytics/ranking-data \
  -H "Content-Type: application/json" \
  -d '{"site_id": 3, "date_from": "2025-07-20", "date_to": "2025-07-25"}'
```

## 🎯 同步模式說明

### 支援的同步模式
- **skip** (預設)：跳過已存在記錄，只插入新數據
- **overwrite**：覆蓋已存在記錄（用於數據修正）

### 使用建議
```bash
# 日常更新使用 skip 模式
just sync-site 1 7 skip

# 數據修正使用 overwrite 模式
just sync-site 1 14 overwrite

# 批次同步（自動順序處理）
just sync-multiple "1,2,5" 7 skip
```

## 🏗️ 現代化架構

### 項目結構
```
gsc-db-refactor/
├── src/
│   ├── api/              # Litestar Web 應用
│   ├── database/         # 混合資料庫層 (SQLite + DuckDB)
│   ├── services/         # 核心服務
│   ├── models.py         # msgspec 數據模型
│   └── config.py         # Pydantic 配置管理
├── sync.py               # 直接同步腳本
├── sync_multiple.py      # 多站點順序同步
├── test_results/         # 測試結果歸檔
├── docs/                 # 文檔
├── justfile             # 任務執行器
└── pyproject.toml        # 項目配置
```

### 混合資料庫設計
```python
# SQLite (OLTP) + DuckDB (OLAP)
class HybridDataStore:
    async def analyze_performance_trends(self):
        # 使用 DuckDB 的窗口函數進行趨勢分析
        query = """
        SELECT *,
            AVG(clicks) OVER (
                ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) as clicks_7d_avg
        FROM performance_data
        """
```

### 順序同步架構
```python
# 確保 GSC API 穩定性的關鍵設計
class ModernGSCClient:
    """
    CRITICAL: GSC API does NOT support concurrent access!
    - Concurrent requests result in 100% failure rate
    - Sequential execution required: 100% success rate
    """
    def __init__(self):
        self.semaphore = asyncio.Semaphore(1)  # 強制順序執行
```

## 🔥 性能提升對比

相比原始實現的性能改進：

| 指標 | 原版本 | 現代化版本 | 提升幅度 |
|-----|-------|-----------|----------|
| API 響應速度 | ~200 RPS | 808 RPS | **4x** |
| 查詢效能 | 基礎 SQLite | DuckDB 分析 | **10-100x** |
| 記憶體使用 | pandas | Polars | **-50-70%** |
| 序列化速度 | Pydantic | msgspec | **5-10x** |
| 同步成功率 | 不穩定 | 100% | **穩定可靠** |

## 🧪 性能測試

### 負載測試
```bash
# API 負載測試
poetry run python load_test.py

# API 壓力測試
poetry run python stress_test.py

# GSC API 並發限制測試
poetry run python test_gsc_limits.py
```

### 測試結果歸檔
所有測試結果已歸檔在 `test_results/` 目錄：
- 負載測試結果：`load_test_results_*.json`
- 壓力測試結果：`stress_test_results_*.json`
- GSC 並發測試：`gsc_concurrency_test_*.json`

### 單元測試
```bash
# 執行所有測試
just test

# 特定測試
poetry run pytest tests/test_database.py -v

# 類型檢查
just type-check
```

## ⚠️ 重要注意事項

### GSC API 限制
1. **絕對不可並發**：經測試證實並發請求 100% 失敗
2. **必須順序處理**：所有同步操作使用 `max_workers=1`
3. **請求間隔**：建議 200-500ms 間隔以確保穩定性

### 同步模式選擇
- **日常更新**：使用 `skip` 模式
- **數據修正**：使用 `overwrite` 模式
- **大量數據**：建議分批進行，避免超時

### 性能優化建議
1. **API 查詢**：支援高並發（測試達 808 RPS）
2. **數據同步**：必須順序執行
3. **大型分析**：使用 DuckDB 的分析功能

## 📈 監控功能

系統包含完整的監控功能：

- **OpenTelemetry**: 分佈式追蹤（可選，預設關閉）
- **健康檢查**: `/health` 端點用於運行狀態監控
- **Swagger 文檔**: `/docs` 提供完整的 API 文檔
- **性能測試**: 內建負載和壓力測試工具

監控重點：
- API 請求速率和延遲
- 同步操作統計
- 資料庫連接狀態

## 🛠️ 開發環境

### 程式碼品質工具
```bash
# 完整品質檢查
just check

# 個別檢查
just lint        # Ruff 程式碼格式化
just type-check  # mypy 類型檢查
just test        # pytest 測試套件
```

## 📚 文檔資源

- **CHEATSHEET.md**: 無 `just` 工具的命令參考
- **CLAUDE.md**: Claude Code 專用開發指引
- **IMPLEMENTATION_REVIEW.md**: 現代化實施詳細回顧
- **API 文檔**: http://localhost:8000/docs

## 🤝 貢獻指南

1. Fork 此倉庫
2. 創建功能分支
3. 執行所有品質檢查：`just check`
4. 提交 Pull Request

### 開發前檢查
```bash
# 確保所有檢查通過
just check

# 執行性能測試
poetry run python tests/performance/load_test.py

# 清理測試數據
poetry run python tests/clean_test_data.py
```

## ⚠️ 測試數據管理

### 重要提醒
- **測試網站**：使用 site_id: 3 (test.com) 進行測試
- **生產網站**：避免在測試中使用生產 site_id（如 17 為 urbanlifehk.com）
- **數據清理**：測試完成後務必清理測試數據

### 清理測試數據
```bash
# 清理最近 7 天的測試數據
python tests/clean_test_data.py --site-id 3 --days 7

# 清理所有測試數據（謹慎使用）
python tests/clean_test_data.py --site-id 3 --all

# 清理未來日期的數據（可能是測試數據）
python tests/clean_test_data.py --future
```

## 📊 效能基準

| 指標 | 原版本 | 現代化版本 | 提升幅度 |
|-----|-------|-----------|----------|
| API 響應速度 | ~200 RPS | 808 RPS | **4x** |
| 查詢效能 | 基礎 SQLite | DuckDB 分析 | **10-100x** |
| 記憶體使用 | pandas | Polars | **-50-70%** |
| 同步成功率 | 不穩定 | 100% | **穩定可靠** |

## 🔄 從原版遷移

如需從原始 GSC Database Manager 遷移：

1. 所有數據保持兼容 - 現有的 `gsc_data.db` 文件可直接使用
2. API 端點保持向後兼容，但性能大幅提升
3. 原有的同步腳本可透過新的 `sync.py` 和 `sync_multiple.py` 替代

## 🚧 發展藍圖

### 已完成的現代化功能 ✅
- [x] Litestar 高性能 Web 框架
- [x] msgspec 超快序列化
- [x] SQLite + DuckDB 混合架構
- [x] 完整的 GSC API 順序同步
- [x] hostname 支援的 API 端點
- [x] 808 RPS 的 API 性能

### 未來改進方向 🔮
- [ ] GraphQL API 支援
- [ ] 即時同步與 webhooks
- [ ] 進階警報系統
- [ ] 機器學習洞察功能
- [ ] Kubernetes 部署支援

## 📄 授權條款

MIT License - 詳見 [LICENSE](LICENSE) 文件

---

<p align="center">
  <strong>現代化的 GSC 數據管理，為 2025 年的 SEO 工具而設計 🚀</strong>
</p>
