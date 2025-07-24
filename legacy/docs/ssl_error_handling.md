# SSL 錯誤處理和網絡問題解決方案

## 問題描述

在使用 Google Search Console API 進行數據同步時，可能會遇到 SSL 相關的網絡錯誤，例如：

- `SSLError: [SSL: LENGTH_MISMATCH] length mismatch`
- `SSLError: [SSL] record layer failure`
- 網絡連接超時
- HTTP 請求失敗

這些錯誤通常是由於網絡不穩定、SSL 握手失敗或 Google API 服務器臨時問題造成的。

## 解決方案

### 1. 自動重試機制

我們實現了智能重試機制，能夠自動識別並重試可恢復的錯誤：

```python
# 增強的重試配置
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((ssl.SSLError, requests.exceptions.RequestException, HttpError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
```

### 2. 錯誤分類和處理

系統能夠智能識別不同類型的錯誤：

- **可重試錯誤**: SSL 錯誤、網絡連接錯誤、5xx 服務器錯誤
- **不可重試錯誤**: 認證錯誤、權限錯誤、格式錯誤

### 3. 網絡健康檢查

提供了完整的網絡診斷工具：

```bash
# 檢查網絡連接狀態
just network-check

# 智能同步（自動處理 SSL 錯誤）
just smart-sync
```

### 4. 配置優化

調整了重試參數以更好地處理 SSL 錯誤：

```python
class RetrySettings(BaseModel):
    attempts: int = 5          # 增加重試次數
    wait_min_seconds: int = 2  # 減少最小等待時間
    wait_max_seconds: int = 30 # 增加最大等待時間
```

## 使用指南

### 遇到 SSL 錯誤時的處理步驟

1. **檢查網絡連接**

   ```bash
   just network-check
   ```

2. **使用智能同步**

   ```bash
   # 同步所有站點
   just smart-sync

   # 同步特定站點
   just smart-sync site_id=123
   ```

3. **降低並發數**
   ```bash
   # 如果問題持續，降低並發數
   poetry run python -m src.app sync daily --all-sites --max-workers 1
   ```

### 手動診斷

如果自動重試仍然失敗，可以進行手動診斷：

```python
from src.utils.system_health_check import diagnose_ssl_issues

# 獲取 SSL 診斷信息
diagnosis = diagnose_ssl_issues()
print(diagnosis)
```

## 預防措施

### 1. 網絡環境

- 確保網絡連接穩定
- 檢查防火牆設定
- 避免使用不穩定的 VPN 或代理

### 2. 系統配置

- 保持 Python 和依賴庫的最新版本
- 確保 OpenSSL 版本支持現代 SSL/TLS 協議
- 定期更新系統證書

### 3. 監控和日誌

- 啟用詳細日誌記錄
- 監控 API 使用配額
- 設置錯誤告警

## 故障排除

### 常見問題

1. **SSL 握手失敗**

   - 檢查系統時間是否正確
   - 更新 CA 證書
   - 嘗試不同的 DNS 服務器

2. **連接超時**

   - 增加超時時間
   - 檢查網絡延遲
   - 使用更穩定的網絡連接

3. **證書驗證失敗**
   - 檢查系統證書庫
   - 確認沒有中間人攻擊
   - 驗證 Google API 證書

### 調試命令

```bash
# 檢查 SSL 版本
python -c "import ssl; print(ssl.OPENSSL_VERSION)"

# 測試 Google API 連接
curl -I https://www.googleapis.com/discovery/v1/apis

# 檢查 DNS 解析
nslookup www.googleapis.com
```

## 技術細節

### 重試策略

使用指數退避算法，重試間隔逐漸增加：

- 第 1 次重試: 2 秒後
- 第 2 次重試: 4 秒後
- 第 3 次重試: 8 秒後
- 第 4 次重試: 16 秒後
- 第 5 次重試: 30 秒後

### 錯誤檢測

```python
def _is_retryable_error(exception: Exception) -> bool:
    # SSL 錯誤
    if isinstance(exception, ssl.SSLError):
        return True

    # 網絡連接錯誤
    if isinstance(exception, (requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout)):
        return True

    # HTTP 錯誤中的臨時錯誤
    if isinstance(exception, HttpError):
        if exception.resp.status >= 500 or exception.resp.status == 429:
            return True

    return False
```

### 網絡健康檢查

系統會檢查以下項目：

- DNS 解析能力
- HTTP/HTTPS 連接
- Google API 可達性
- SSL/TLS 握手過程

## 更新日誌

- **2025-01-07**: 實現智能重試機制和網絡診斷工具
- **2025-01-07**: 增加 SSL 錯誤特殊處理
- **2025-01-07**: 優化重試配置參數
- **2025-01-07**: 添加網絡健康檢查功能

## 相關資源

- [Google API 錯誤處理文檔](https://developers.google.com/search-console/v1/errors)
- [Python SSL 模塊文檔](https://docs.python.org/3/library/ssl.html)
- [Requests 庫重試策略](https://requests.readthedocs.io/en/latest/)
- [Tenacity 重試庫](https://tenacity.readthedocs.io/)
