# GSC Database Manager 現代化提案 (2025)

## 概述

本提案採用 2025 年最新的 Python 生態系統和架構模式，徹底現代化 GSC Database Manager。重點是利用最新的異步框架、AI 輔助開發工具、邊緣計算能力，以及雲原生架構。

## 核心功能保留

### 必須保留的功能
1. **數據同步**：每日和每小時的 GSC 數據同步
2. **數據存儲**：超過 Google 16 個月限制的永久存儲
3. **API 服務**：RESTful API 用於數據查詢和分析
4. **批量處理**：支持多站點同步和批量數據處理
5. **錯誤恢復**：中斷同步的恢復機制
6. **順序處理**：GSC API 調用必須保持順序（max_workers=1）

## 2025 現代化架構方案

### 1. 向量資料庫 + AI 驅動的查詢系統

#### 現況問題
- 傳統 SQL 查詢無法理解語義
- 無法進行相似性搜索
- 缺乏 AI 整合能力

#### 2025 方案
```python
# 使用 LanceDB (2025 最流行的向量資料庫)
import lancedb
from sentence_transformers import SentenceTransformer
import polars as pl  # 取代 pandas，更快更省記憶體

class ModernDataStore:
    def __init__(self):
        self.db = lancedb.connect("./data/gsc_vectors")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

    async def store_performance_data(self, data: dict):
        # 自動生成查詢向量
        query_embedding = self.encoder.encode(data['query'])

        # 使用 Polars DataFrame（比 pandas 快 10x）
        df = pl.DataFrame({
            'query': data['query'],
            'query_vector': [query_embedding],
            'clicks': data['clicks'],
            'impressions': data['impressions'],
            'metadata': data  # JSON 儲存所有資料
        })

        # 存入向量資料庫
        table = self.db.open_table("performance_data")
        table.add(df)

    async def semantic_search(self, query: str, limit: int = 10):
        # 語義搜索相似查詢
        embedding = self.encoder.encode(query)
        results = table.search(embedding).limit(limit).to_polars()
        return results
```

**優點**：
- 支援語義搜索和相似性匹配
- AI-ready 架構
- 使用 Polars 獲得 10x 性能提升
- 自動索引和優化

### 2. 使用 Litestar 取代 FastAPI (2025 最快框架)

#### 現況問題
- FastAPI 在 2025 已經顯得老舊
- 性能不如新一代框架
- 依賴注入系統過於複雜

#### 2025 方案
```python
# Litestar - 2025 最快的 Python Web 框架
from litestar import Litestar, get, post, Request
from litestar.di import Provide
from litestar.contrib.sqlalchemy.plugins import SQLAlchemyPlugin
import msgspec  # 比 Pydantic 快 5x 的序列化庫

# 使用 msgspec 定義模型（超快序列化）
class QueryRequest(msgspec.Struct):
    query: str
    site_id: int
    date_range: tuple[str, str]

class PerformanceResponse(msgspec.Struct):
    data: list[dict]
    total: int
    semantic_similar: list[str]  # AI 推薦的相關查詢

# Litestar 應用
app = Litestar(
    route_handlers=[analytics_router],
    plugins=[
        SQLAlchemyPlugin(
            config=sqlalchemy_config,
            enable_async=True,
        ),
    ],
    # 內建 OpenTelemetry 支持
    opentelemetry_config=OpenTelemetryConfig(
        enable_logging=True,
        enable_metrics=True,
    ),
)

@get("/api/v1/analytics/search")
async def semantic_search(
    request: Request,
    query: str,
    ai_service: AIService,
) -> PerformanceResponse:
    # 使用 AI 增強搜索
    results = await ai_service.semantic_search(query)
    return PerformanceResponse(
        data=results,
        total=len(results),
        semantic_similar=await ai_service.get_similar_queries(query)
    )
```

**優點**：
- 比 FastAPI 快 3x
- 內建 OpenTelemetry 監控
- 使用 msgspec 獲得 5x 序列化性能
- 更簡潔的依賴注入

### 3. 配置管理簡化

#### 現況問題
- TOML 文件 + 環境變量的混合系統
- 複雜的路徑解析邏輯
- 嵌套配置結構

#### 建議方案
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__"
    )

    # 資料庫配置
    database_url: str = "sqlite+aiosqlite:///./data/gsc_data.db"

    # API 配置
    gsc_api_key_path: str = "./cred/client_secret.json"
    gsc_token_path: str = "./cred/token.json"

    # 同步配置
    sync_batch_size: int = 200
    sync_retry_attempts: int = 3
    sync_retry_delay: int = 1

    # 日誌配置
    log_level: str = "INFO"
    log_file: str = "./logs/gsc_app.log"
```

**優點**：
- 單一配置來源（.env 文件）
- 自動類型轉換和驗證
- 簡化的配置結構

### 4. 異步架構

#### 現況問題
- 同步阻塞 I/O 操作
- 複雜的線程管理
- 效能瓶頸

#### 建議方案
```python
# 使用 httpx 替代 requests
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class GSCClient:
    def __init__(self, credentials_path: str):
        self.client = httpx.AsyncClient(timeout=30.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch_data(self, site_url: str, date: str) -> dict:
        # 異步 API 調用
        response = await self.client.post(...)
        return response.json()
```

**優點**：
- 更好的並發性能
- 簡化的錯誤處理
- 現代化的異步模式

### 5. CLI 現代化

#### 現況問題
- 複雜的命令結構
- 依賴注入整合困難

#### 建議方案
```python
# 使用 Typer 的異步支持
import typer
from typing import Annotated

app = typer.Typer()

@app.command()
async def sync_daily(
    site_id: Annotated[int, typer.Argument()],
    days: Annotated[int, typer.Option()] = 7,
    sync_mode: Annotated[str, typer.Option()] = "skip"
):
    """同步指定站點的每日數據"""
    async with get_services() as services:
        await services.sync.sync_daily_data(site_id, days, sync_mode)
```

### 6. 簡化的專案結構

```
gsc_db/
├── src/
│   ├── __init__.py
│   ├── main.py           # FastAPI 應用入口
│   ├── cli.py            # Typer CLI 入口
│   ├── config.py         # Pydantic Settings
│   ├── models.py         # SQLModel 定義
│   ├── database.py       # 資料庫連接管理
│   ├── api/              # API 路由
│   │   ├── __init__.py
│   │   ├── sites.py
│   │   ├── analytics.py
│   │   └── sync.py
│   ├── services/         # 業務邏輯
│   │   ├── __init__.py
│   │   ├── gsc_client.py
│   │   ├── sync_service.py
│   │   └── analytics_service.py
│   └── utils/            # 工具函數
│       ├── __init__.py
│       └── retry.py
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

## 推薦的技術堆疊

### 核心依賴
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
sqlmodel = "^0.0.14"  # SQLAlchemy + Pydantic 整合
typer = "^0.9.0"
httpx = "^0.26.0"
pydantic-settings = "^2.1.0"
tenacity = "^8.2.0"
python-multipart = "^0.0.6"

# Google API
google-api-python-client = "^2.100.0"
google-auth-httplib2 = "^0.1.0"
google-auth-oauthlib = "^1.0.0"

# 數據處理
pandas = "^2.1.0"
numpy = "^1.25.0"

# 可視化（統一使用 Plotly）
plotly = "^5.18.0"
kaleido = "0.2.1"  # 用於導出圖片

# 異步支持
aiosqlite = "^0.19.0"
aiocache = "^0.12.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
ruff = "^0.1.0"
mypy = "^1.7.0"
```

### 移除的依賴
- dependency-injector（使用 FastAPI 內建）
- matplotlib, seaborn（統一使用 Plotly）
- requests（使用 httpx）
- 複雜的線程鎖庫

## 實施計劃

### 第一階段：基礎設施現代化
1. 遷移到 SQLModel/SQLAlchemy
2. 實現異步資料庫操作
3. 簡化配置管理

### 第二階段：API 現代化
1. 重構 API 端點使用異步
2. 簡化依賴注入
3. 實現新的錯誤處理模式

### 第三階段：同步邏輯優化
1. 保持順序處理（重要！）
2. 使用 httpx 進行異步 HTTP 調用
3. 簡化重試邏輯

### 第四階段：測試和文檔
1. 更新測試套件支持異步
2. 簡化文檔結構
3. 性能基準測試

## 預期效益

1. **代碼簡化**：減少約 40% 的樣板代碼
2. **性能提升**：異步 I/O 提升響應速度
3. **維護性**：更直觀的代碼結構
4. **現代化**：採用最新的 Python 最佳實踐
5. **依賴減少**：移除不必要的第三方庫

## 風險和緩解措施

1. **數據遷移**：提供自動遷移腳本
2. **API 兼容性**：保持現有 API 接口不變
3. **性能退化**：進行充分的性能測試
4. **學習曲線**：提供詳細的開發文檔

## 結論

此現代化提案通過採用現代 Python 生態系統的最佳實踐，可以顯著簡化代碼庫，同時保持所有核心功能。重點是減少不必要的抽象層，利用成熟的框架功能，並採用異步編程模式來提高性能。
