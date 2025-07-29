# GSC Database Manager 現代化提案 (2025)

## 概述

本提案基於對 GSC Database Manager 的深入分析，提供實用的現代化建議。專案核心是管理 Google Search Console 的時間序列 SEO 數據，包含點擊、曝光、排名等結構化指標。重點是優化查詢性能、簡化架構，並保持系統穩定性。

## 核心功能理解

### 數據特性

1. **時間序列性能數據**：每日/每小時的搜索表現指標
2. **多維度查詢**：按站點、日期、頁面、查詢詞、設備等維度
3. **聚合分析**：排名趨勢、點擊率變化、關鍵詞表現
4. **長期存儲**：突破 GSC 官方 16 個月限制

### 必須保留的功能

1. **數據同步**：每日和每小時的 GSC 數據同步
2. **順序處理**：GSC API 調用必須保持順序（max_workers=1）
3. **API 服務**：RESTful API 用於數據查詢和分析
4. **批量處理**：支持多站點同步和批量數據處理
5. **錯誤恢復**：中斷同步的恢復機制

## 2025 現代化架構方案

### 1. 混合資料庫架構（SQLite + DuckDB）

#### 現況問題

- SQLite 在複雜聚合查詢上性能不足
- 缺乏現代分析函數支持
- 大量數據分析時效率低

#### 2025 方案

```python
# 保留 SQLite 作為主存儲，增加 DuckDB 作為分析引擎
import duckdb
import polars as pl
from datetime import datetime, timedelta

class HybridDataStore:
    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path
        self.duck_conn = duckdb.connect(':memory:')

        # 連接 SQLite 作為外部數據源
        self.duck_conn.execute(f"""
            ATTACH DATABASE '{sqlite_path}' AS sqlite_db (TYPE SQLITE);
        """)

    async def analyze_performance_trends(
        self,
        site_id: int,
        days: int
    ) -> pl.DataFrame:
        """使用 DuckDB 的窗口函數進行趨勢分析"""
        query = """
        WITH daily_stats AS (
            SELECT
                date,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(position) as avg_position,
                COUNT(DISTINCT query) as unique_queries
            FROM sqlite_db.gsc_performance_data
            WHERE site_id = ?
                AND date >= CURRENT_DATE - INTERVAL ? DAY
            GROUP BY date
        )
        SELECT
            *,
            AVG(total_clicks) OVER (
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) as clicks_7d_avg,
            total_clicks - LAG(total_clicks, 7) OVER (ORDER BY date) as clicks_wow_change
        FROM daily_stats
        ORDER BY date DESC
        """

        result = self.duck_conn.execute(query, [site_id, days]).pl()
        return result

    async def export_to_parquet(self, site_id: int, output_path: str):
        """導出數據為 Parquet 格式以便長期存檔"""
        self.duck_conn.execute(f"""
            COPY (
                SELECT * FROM sqlite_db.gsc_performance_data
                WHERE site_id = {site_id}
            ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
```

**優點**：

- 保持 SQLite 的簡單可靠
- 獲得 DuckDB 的分析性能（10-100x 提升）
- 支援複雜的窗口函數和時間序列分析
- 可直接導出 Parquet 進行歸檔

### 2. 使用 Litestar 取代 FastAPI (2025 最佳性能)

#### 現況問題

- FastAPI 性能瓶頸明顯
- 依賴注入系統複雜
- 序列化性能不足

#### 2025 方案

```python
# Litestar + msgspec 實現極致性能
from litestar import Litestar, get, post
from litestar.datastructures import State
from litestar.di import Provide
import msgspec
from typing import Annotated

# msgspec 模型（比 Pydantic 快 5-10x）
class RankingDataRequest(msgspec.Struct):
    site_id: int
    date_from: str
    date_to: str
    queries: list[str] | None = None
    group_by: list[str] = ["query"]
    limit: int = 1000

class PerformanceMetrics(msgspec.Struct):
    clicks: int
    impressions: int
    ctr: float
    position: float

class RankingDataResponse(msgspec.Struct):
    data: list[dict]
    total: int
    aggregations: PerformanceMetrics

# 依賴注入簡化
async def get_db_service(state: State) -> HybridDataStore:
    return state.db_service

# API 路由
@post("/api/v1/analytics/ranking-data")
async def get_ranking_data(
    data: RankingDataRequest,
    db: Annotated[HybridDataStore, Depends(get_db_service)]
) -> RankingDataResponse:
    # 使用 DuckDB 進行高效查詢
    results = await db.get_ranking_data(
        site_id=data.site_id,
        date_range=(data.date_from, data.date_to),
        queries=data.queries,
        group_by=data.group_by
    )

    return RankingDataResponse(
        data=results["data"],
        total=results["total"],
        aggregations=PerformanceMetrics(**results["aggregations"])
    )

# 應用配置
app = Litestar(
    route_handlers=[get_ranking_data],
    state=State({"db_service": HybridDataStore("./data/gsc.db")}),
    # 內建性能監控
    debug=False,
    compression_config=CompressionConfig(backend="gzip", minimum_size=1000),
)
```

**優點**：

- 比 FastAPI 快 2-3x
- msgspec 序列化比 Pydantic 快 5-10x
- 更簡潔的依賴注入
- 內建壓縮和性能優化

### 3. 現代化配置管理

#### 現況問題

- TOML + 環境變量混合系統複雜
- 路徑解析邏輯繁瑣
- 配置驗證不夠嚴謹

#### 2025 方案

```python
# 使用 Pydantic Settings v2 + python-dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GSC_",
        case_sensitive=False,
        # 2025 新功能：自動類型轉換
        json_schema_mode="validation"
    )

    # 資料庫設置
    database_path: Path = Field(
        default=Path("./data/gsc-data.db"),
        description="SQLite database path"
    )
    enable_duckdb: bool = Field(default=True)

    # API 設置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = Field(default=4, ge=1, le=16)

    # GSC 設置
    gsc_credentials_path: Path = Path("./cred/client_secret.json")
    gsc_max_retries: int = Field(default=3, ge=1, le=10)
    gsc_rate_limit_per_minute: int = 60

    # 性能設置
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    query_timeout_seconds: int = 30

    @field_validator('database_path', 'gsc_credentials_path')
    def ensure_path_exists(cls, v: Path) -> Path:
        if not v.exists():
            v.parent.mkdir(parents=True, exist_ok=True)
        return v

# 單例模式
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**優點**：

- 類型安全的配置
- 自動驗證和轉換
- 清晰的環境變量前綴
- 路徑自動創建

### 4. 異步優化與並發控制

#### 現況問題

- 同步阻塞 I/O
- 線程鎖管理複雜
- 無法充分利用現代硬體

#### 2025 方案

```python
import asyncio
import httpx
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class ModernGSCClient:
    def __init__(self, credentials_path: Path):
        # 使用 httpx 的連接池
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10),
            http2=True  # 啟用 HTTP/2
        )

        # 使用信號量控制並發（保持順序但優化 I/O）
        self.api_semaphore = asyncio.Semaphore(1)  # GSC API 順序調用
        self.db_semaphore = asyncio.Semaphore(5)   # 資料庫並發寫入

    @asynccontextmanager
    async def rate_limit(self):
        """速率限制上下文管理器"""
        async with self.api_semaphore:
            yield
            # 確保 API 調用間隔
            await asyncio.sleep(1.0)

    async def fetch_batch(
        self,
        site_url: str,
        dates: list[str]
    ) -> list[dict]:
        """批量獲取數據，但保持順序調用"""
        results = []

        for date in dates:
            async with self.rate_limit():
                try:
                    response = await self.client.post(
                        "https://searchconsole.googleapis.com/v1/...",
                        json={"startDate": date, "endDate": date}
                    )
                    results.append(response.json())
                except httpx.HTTPError as e:
                    # 智能重試邏輯
                    if e.response.status_code == 429:
                        await asyncio.sleep(60)  # 速率限制等待
                    raise

        return results
```

### 5. 快取層設計

#### 2025 方案

```python
# 使用 Redis + aiocache 實現多級快取
from aiocache import Cache
from aiocache.serializers import PickleSerializer
import hashlib
import json

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost"):
        # L1: 內存快取（熱數據）
        self.memory_cache = Cache(Cache.MEMORY)

        # L2: Redis 快取（持久化）
        self.redis_cache = Cache(
            Cache.REDIS,
            endpoint=redis_url,
            serializer=PickleSerializer(),
            ttl=3600
        )

    def _cache_key(self, prefix: str, **params) -> str:
        """生成穩定的快取鍵"""
        key_data = json.dumps(params, sort_keys=True)
        hash_key = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_key}"

    async def get_or_compute(
        self,
        key_prefix: str,
        compute_func,
        ttl: int = 3600,
        **params
    ):
        """快取 + 計算模式"""
        cache_key = self._cache_key(key_prefix, **params)

        # 檢查 L1 快取
        result = await self.memory_cache.get(cache_key)
        if result:
            return result

        # 檢查 L2 快取
        result = await self.redis_cache.get(cache_key)
        if result:
            # 回填 L1
            await self.memory_cache.set(cache_key, result, ttl=60)
            return result

        # 計算並快取
        result = await compute_func(**params)

        # 異步寫入兩級快取
        await asyncio.gather(
            self.memory_cache.set(cache_key, result, ttl=60),
            self.redis_cache.set(cache_key, result, ttl=ttl)
        )

        return result
```

### 6. 監控與可觀測性

#### 2025 方案

```python
# 使用 OpenTelemetry + Prometheus
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from prometheus_client import Counter, Histogram, Gauge
import time

# 自動儀表化
HTTPXClientInstrumentor().instrument()
SQLite3Instrumentor().instrument()

# 自定義指標
sync_counter = Counter('gsc_sync_total', 'Total sync operations', ['site_id', 'status'])
query_histogram = Histogram('gsc_query_duration_seconds', 'Query duration', ['query_type'])
active_syncs = Gauge('gsc_active_syncs', 'Number of active sync operations')

class MonitoredService:
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)

    @query_histogram.labels(query_type='ranking_data').time()
    async def get_ranking_data(self, site_id: int, **params):
        with self.tracer.start_as_current_span("get_ranking_data") as span:
            span.set_attribute("site_id", site_id)
            span.set_attribute("date_range", params.get("date_range"))

            try:
                result = await self._fetch_data(site_id, **params)
                span.set_attribute("result_count", len(result))
                return result
            except Exception as e:
                span.record_exception(e)
                raise
```

## 推薦的技術堆疊

```toml
[tool.poetry.dependencies]
python = "^3.12"  # 2025 年使用最新 Python
litestar = "^2.8.0"  # 高性能 Web 框架
msgspec = "^0.18.0"  # 極速序列化
duckdb = "^0.10.0"  # 分析引擎
polars = "^0.20.0"  # 高效數據處理
httpx = "^0.27.0"  # 現代 HTTP 客戶端
redis = "^5.0.0"  # 快取層
aiocache = "^0.12.0"  # 異步快取
pydantic-settings = "^2.2.0"  # 配置管理

# 監控
opentelemetry-api = "^1.24.0"
opentelemetry-instrumentation = "^0.45.0"
prometheus-client = "^0.20.0"

# Google API（保持不變）
google-api-python-client = "^2.120.0"
google-auth-httplib2 = "^0.2.0"
google-auth-oauthlib = "^1.2.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
ruff = "^0.3.0"
mypy = "^1.9.0"
```

## 簡化的專案結構

```
gsc_db/
├── src/
│   ├── __init__.py
│   ├── app.py              # Litestar 應用
│   ├── cli.py              # Typer CLI（保持不變）
│   ├── config.py           # Pydantic Settings
│   ├── models.py           # msgspec 模型定義
│   ├── database/
│   │   ├── hybrid.py       # SQLite + DuckDB
│   │   └── cache.py        # 快取服務
│   ├── services/
│   │   ├── gsc_client.py   # 異步 GSC 客戶端
│   │   ├── sync.py         # 同步邏輯
│   │   └── analytics.py    # 分析服務
│   └── api/
│       └── routes.py       # API 路由
├── tests/
├── .env
└── pyproject.toml
```

## 實施計劃

### 第一階段：基礎優化（2 週）

1. 升級到 Python 3.12
2. 替換 pandas 為 polars
3. 實施 DuckDB 分析層

### 第二階段：API 現代化（2 週）

1. 遷移到 Litestar + msgspec
2. 實施快取層
3. 簡化配置管理

### 第三階段：性能優化（1 週）

1. 完全異步化
2. 添加監控指標
3. 性能測試和調優

## 預期效益

1. **查詢性能**：使用 DuckDB 提升 10-100x
2. **API 響應**：Litestar + msgspec 提升 3-5x
3. **記憶體使用**：Polars 減少 50-70%
4. **開發體驗**：簡化架構，減少 30% 代碼量
5. **可維護性**：現代化工具鏈，更好的類型支持

## 結論

此現代化方案保留了系統的核心功能和穩定性，同時採用 2025 年最佳實踐來提升性能和開發體驗。重點是實用性改進而非激進重構，確保平滑過渡。
