# GSC API 優化改進文檔

## 概述

根據 Google Search Console API 官方文件的最佳實踐，我們對 GSC 數據同步功能進行了全面優化，以解決 SSL 錯誤和提高 API 使用效率。

## 問題分析

### 1. 原始問題

- **高併發 SSL 錯誤**：過多的並行請求導致 SSL 連接不穩定
- **API 速率限制**：未考慮 GSC API 的配額限制
- **非最佳實踐**：沒有遵循 API 文件建議的查詢模式

### 2. 根本原因

- 使用過多的併發 workers（默認 4 個）
- 沒有實施 API 速率限制檢查
- 沒有使用每日查詢模式
- 缺乏適當的錯誤處理和重試機制

## 優化改進

### 1. API 速率限制管理

#### 新增功能

- **速率限制檢查**：`_rate_limit_check()` 方法
- **每分鐘請求限制**：保守估計 100 requests/minute
- **智能等待機制**：自動計算等待時間

```python
def _rate_limit_check(self):
    """實施 API 速率限制檢查"""
    with self._api_lock:
        # 檢查每分鐘限制
        if self.api_requests_this_minute >= 100:
            sleep_time = 60 - now.second
            time.sleep(sleep_time)
```

### 2. 優化的數據流處理

#### 新增方法

- **`stream_site_data_optimized()`**：遵循 API 最佳實踐的優化版本
- **每日查詢模式**：按天分組處理數據
- **順序處理**：避免過度併發

#### 關鍵改進

```python
# 按日期分組，每天處理一次
while current_date <= end_date_obj:
    date_str = current_date.strftime("%Y-%m-%d")

    # 對每個搜索類型順序處理（避免過度併發）
    for search_type in search_types:
        # 使用 API 推薦的查詢模式
        request_body = {
            "startDate": date_str,
            "endDate": date_str,  # 每天查詢一天的數據
            # ...
        }
```

### 3. 併發控制優化

#### 自動併發調整

- **最大 workers 限制**：自動調整為最多 2 個併發 worker
- **智能警告**：當用戶請求過多 workers 時提供建議

```python
# 根據 GSC API 最佳實踐，減少併發數量
optimized_max_workers = min(max_workers, 2)
```

#### 更新的默認值

- **BulkDataSynchronizer**：默認 `max_workers=2`
- **所有 justfile 命令**：添加 `--max-workers 2` 參數

### 4. 錯誤處理增強

#### 429 速率限制處理

```python
elif e.resp.status == 429:
    logger.warning(f"Rate limit exceeded, waiting 60 seconds...")
    time.sleep(60)
    continue  # 重試當前搜索類型
```

#### 搜索類型間延遲

```python
# 在不同搜索類型之間添加小延遲
time.sleep(0.1)
```

### 5. 向後兼容性

#### 保持兼容

- **舊方法保留**：`stream_site_data()` 內部使用優化版本
- **API 不變**：所有現有調用保持不變
- **漸進式改進**：可選擇使用新的優化方法

## 測試驗證

### 新增測試套件

創建了 `test_gsc_api_optimization.py` 包含 7 個測試：

1. **test_rate_limit_check**：驗證速率限制檢查功能
2. **test_optimized_stream_data_structure**：測試優化後的數據流結構
3. **test_concurrent_worker_optimization**：驗證併發工作者數量優化
4. **test_api_best_practices_compliance**：測試 API 最佳實踐遵循
5. **test_ssl_error_handling_improvement**：測試 SSL 錯誤處理改進
6. **test_rate_limit_429_handling**：測試 429 速率限制錯誤處理
7. **test_backward_compatibility**：測試向後兼容性

### 測試結果

- ✅ **所有 49 個測試通過**
- ✅ **新增 7 個優化測試**
- ✅ **向後兼容性確認**

## 配置更新

### justfile 命令優化

所有同步相關命令都已更新：

```bash
# 單站點同步
just sync-site 1 7  # 自動使用 --max-workers 2

# 批量同步
just sync-multiple "1 2 3"  # 自動使用 --max-workers 2

# 智能同步
just smart-sync all 7  # 自動使用 --max-workers 2

# 維護程序
just maintenance  # 自動使用 --max-workers 2
```

## 性能影響

### 預期改進

- **減少 SSL 錯誤**：通過降低併發壓力
- **提高穩定性**：遵循 API 速率限制
- **更好的錯誤恢復**：智能重試機制

### 性能權衡

- **稍慢的同步速度**：但更穩定可靠
- **更少的 API 配額消耗**：避免重複請求
- **更好的用戶體驗**：減少失敗和重試

## 使用建議

### 最佳實踐

1. **使用默認設置**：新的默認值已經過優化
2. **監控 API 使用量**：使用內建的 API 使用統計
3. **錯誤日誌關注**：注意 SSL 和速率限制警告

### 故障排除

1. **SSL 錯誤持續**：檢查網絡連接穩定性
2. **速率限制頻繁**：考慮進一步減少併發數
3. **同步緩慢**：這是正常的，穩定性優先

## 未來改進計劃

### 批次請求支持

- **實施 GSC Batch API**：單個請求包含多個查詢
- **進一步減少 HTTP 連接數**：遵循 API 文件建議

### 智能調度

- **動態併發調整**：根據 API 響應時間調整
- **錯誤率監控**：自動降級併發級別

### 緩存優化

- **結果緩存**：避免重複請求相同數據
- **增量同步**：只同步變更的數據

## 相關文件

- **API 文件**：`docs/gsc_guide.md`、`docs/gsc_hourly_guide.md`
- **SSL 錯誤處理**：`docs/ssl_error_handling.md`
- **實施代碼**：`src/services/gsc_client.py`、`src/jobs/bulk_data_synchronizer.py`
- **測試文件**：`tests/test_gsc_api_optimization.py`

---

_此文檔記錄了根據 Google Search Console API 最佳實踐實施的優化改進，旨在提高系統穩定性和 API 使用效率。_
