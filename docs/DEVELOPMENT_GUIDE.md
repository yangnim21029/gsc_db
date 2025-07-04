# 🛠️ 開發指南

## 🚀 快速開始

### 環境設置

1. **克隆專案**

```bash
git clone <your-repo-url>
cd gsc_db
```

2. **創建虛擬環境**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安裝依賴**

```bash
pip install -r requirements.txt
```

4. **設置 Google API 認證**

```bash
# 將 Google API 認證檔案放入 config/ 目錄
cp your_client_secret.json config/client_secret.json
```

### 基本開發流程

1. **運行測試**

```bash
python -m pytest tests/
```

2. **檢查代碼風格**

```bash
# 安裝開發依賴
pip install black flake8 mypy

# 格式化代碼
black src/ tests/

# 檢查代碼風格
flake8 src/ tests/

# 類型檢查
mypy src/
```

3. **運行 CLI 測試**

```bash
python main.py --help
python main.py auth
```

## 📁 專案架構

### 模組職責

- **`src/cli/`** - 命令行界面和用戶交互
- **`src/services/`** - 核心業務邏輯和外部服務
- **`src/analysis/`** - 數據分析和報告生成
- **`src/jobs/`** - 批量作業和後台任務
- **`src/utils/`** - 通用工具函數
- **`src/config.py`** - 集中配置管理

### 設計模式

1. **依賴注入** - 通過配置模組管理依賴
2. **工廠模式** - 用於創建不同類型的分析器
3. **策略模式** - 用於不同的報告生成策略
4. **觀察者模式** - 用於日誌記錄和進度通知

## 🔧 開發最佳實踐

### 1. 代碼風格

- 使用 **Black** 進行代碼格式化
- 遵循 **PEP 8** 風格指南
- 使用 **類型提示** 提高代碼可讀性
- 添加 **文檔字符串** 說明函數用途

### 2. 錯誤處理

```python
try:
    # 業務邏輯
    result = some_operation()
except SpecificException as e:
    logger.error(f"操作失敗: {e}")
    raise typer.Exit(1)
except Exception as e:
    logger.error(f"未知錯誤: {e}")
    raise typer.Exit(1)
```

### 3. 日誌記錄

```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.info("開始執行操作")
    try:
        # 操作邏輯
        logger.debug("操作詳情")
    except Exception as e:
        logger.error(f"操作失敗: {e}")
        raise
    logger.info("操作完成")
```

### 4. 配置管理

```python
from .. import config

def some_function(db_path: str = None):
    db_path = db_path or str(config.DB_PATH)
    # 使用配置
```

## 🧪 測試指南

### 單元測試

```python
import pytest
from unittest.mock import Mock, patch
from src.services.database import Database

def test_database_connection():
    """測試數據庫連接"""
    db = Database()
    assert db is not None

@patch('src.services.database.sqlite3.connect')
def test_database_operations(mock_connect):
    """測試數據庫操作"""
    mock_conn = Mock()
    mock_connect.return_value = mock_conn

    db = Database()
    db.get_sites()

    mock_connect.assert_called_once()
```

### 整合測試

```python
def test_cli_command():
    """測試 CLI 命令"""
    from typer.testing import CliRunner
    from main import app

    runner = CliRunner()
    result = runner.invoke(app, ["sites"])

    assert result.exit_code == 0
    assert "站點" in result.stdout
```

### 測試數據

- 使用 **fixtures** 創建測試數據
- 使用 **mock** 模擬外部服務
- 使用 **臨時數據庫** 進行測試

## 📊 性能優化

### 1. 數據庫優化

```python
# 使用索引
CREATE INDEX idx_date_site ON daily_rankings(date, site_id);

# 批量插入
def batch_insert(data_list):
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            "INSERT INTO daily_rankings VALUES (?, ?, ?, ?, ?, ?)",
            data_list
        )
```

### 2. 記憶體優化

```python
# 使用生成器處理大數據集
def process_large_dataset():
    for chunk in pd.read_sql_query(query, conn, chunksize=1000):
        yield process_chunk(chunk)
```

### 3. 並發處理

```python
import asyncio
import aiohttp

async def fetch_multiple_sites(sites):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_site_data(session, site) for site in sites]
        return await asyncio.gather(*tasks)
```

## 🔍 調試技巧

### 1. 日誌調試

```python
import logging

# 設置詳細日誌
logging.basicConfig(level=logging.DEBUG)

# 在關鍵位置添加日誌
logger.debug(f"處理數據: {data}")
```

### 2. 斷點調試

```python
import pdb

def some_function():
    # 設置斷點
    pdb.set_trace()
    # 代碼邏輯
```

### 3. 性能分析

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # 要分析的函數
    some_function()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats()
```

## 🚀 部署指南

### 1. 生產環境設置

```bash
# 安裝生產依賴
pip install -r requirements.txt

# 設置環境變數
export GSC_CLIENT_SECRET_PATH="/path/to/client_secret.json"
export GSC_DB_PATH="/path/to/production.db"
export GSC_LOG_LEVEL="INFO"
```

### 2. Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### 3. 監控和日誌

```python
# 添加健康檢查端點
@app.command()
def health_check():
    """健康檢查"""
    try:
        # 檢查數據庫連接
        db = Database()
        db.get_sites()

        # 檢查 API 連接
        gsc = GSCClient()
        gsc.is_authenticated()

        typer.secho("✅ 系統健康", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"❌ 系統異常: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
```

## 📝 貢獻指南

### 1. 提交規範

```
feat: 添加新功能
fix: 修復錯誤
docs: 更新文檔
style: 代碼格式調整
refactor: 代碼重構
test: 添加測試
chore: 構建過程或輔助工具的變動
```

### 2. 分支策略

- `main` - 主分支，穩定版本
- `develop` - 開發分支
- `feature/*` - 功能分支
- `hotfix/*` - 緊急修復分支

### 3. 代碼審查

- 所有代碼變更需要通過 PR
- 確保測試通過
- 檢查代碼風格
- 更新相關文檔

## 🎯 常見問題

### Q: 如何添加新的 CLI 命令？

A: 在 `src/cli/commands.py` 中添加新的命令函數，使用 `@app.command()` 裝飾器。

### Q: 如何添加新的分析類型？

A: 在 `src/analysis/` 中創建新的分析模組，實現分析邏輯，然後在 CLI 中添加對應命令。

### Q: 如何處理 API 限制？

A: 使用重試機制和速率限制，在 `src/services/gsc_client.py` 中實現。

### Q: 如何優化大數據集處理？

A: 使用分頁處理、批量操作和數據庫索引優化。

## 📚 參考資源

- [Typer 文檔](https://typer.tiangolo.com/)
- [Rich 文檔](https://rich.readthedocs.io/)
- [Google Search Console API](https://developers.google.com/search/apis)
- [SQLite 文檔](https://www.sqlite.org/docs.html)
- [Pandas 文檔](https://pandas.pydata.org/docs/)
- [Matplotlib 文檔](https://matplotlib.org/stable/contents.html)
