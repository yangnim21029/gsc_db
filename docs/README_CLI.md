# GSC 數據導出工具 - CLI 版本

這是一個純 Python 的 Google Search Console 數據導出工具，去除了前端界面，專注於命令行操作。

## 主要功能

- ✅ **純命令行操作** - 所有功能都在 terminal 完成
- ✅ **自動繼續功能** - 中斷後可以繼續未完成的同步
- ✅ **API 限制管理** - 了解和管理 GSC API 使用限制
- ✅ **增量同步** - 只同步缺失的數據，避免重複
- ✅ **進度追蹤** - 實時查看同步進度
- ✅ **數據存儲** - 所有數據存儲到 SQLite 數據庫
- ✅ **每小時數據支援** - 支援 Google 2025 年 4 月推出的每小時數據功能

## 安裝和設置

### 1. 確保依賴已安裝

```bash
pip install -r requirements.txt
```

### 2. 準備 Google API 憑證

確保項目目錄中有 `client_secret.json` 文件（Google OAuth 憑證）

### 3. 初始化數據庫

數據庫會在首次運行時自動創建

## 使用方法

### 基本工作流程

#### 1. 認證 GSC API

```bash
python gsc_simple.py auth
```

- 會打開瀏覽器進行 Google 認證
- 按照提示完成授權
- 認證信息會保存到 `gsc_credentials.json`

#### 2. 列出可用站點

```bash
python gsc_simple.py sites
```

- 顯示 GSC 中的所有站點
- 標示哪些已添加到數據庫

#### 3. 添加站點到數據庫

```bash
python gsc_simple.py add-site "https://example.com/"
python gsc_simple.py add-site "sc-domain:example.com" --name "我的網站"
```

#### 4. 檢查數據覆蓋情況

```bash
# 查看所有站點的數據覆蓋
python gsc_simple.py coverage

# 查看特定站點的數據覆蓋
python gsc_simple.py coverage --site-id 1
```

#### 5. 同步數據

```bash
# 同步最近 30 天的數據（所有站點）
python gsc_simple.py sync --recent-days 30

# 同步特定日期範圍（所有站點）
python gsc_simple.py sync --start-date 2024-01-01 --end-date 2024-01-31

# 同步特定站點
python gsc_simple.py sync --site-id 1 --recent-days 30

# 強制重建數據（會覆蓋現有數據）
python gsc_simple.py sync --recent-days 30 --force
```

#### 6. 監控同步進度

```bash
# 查看當前運行中的任務
python gsc_simple.py progress

# 查看 API 使用狀態
python gsc_simple.py api-status
```

#### 7. 管理任務

```bash
# 取消所有運行中的任務
python gsc_simple.py cancel
```

## 🕐 每小時數據 (新功能)

Google Search Console 在 2025 年 4 月推出了每小時數據功能，本工具已完整支援：

### 同步每小時數據

```bash
# 同步昨天的每小時數據 (默認)
python gsc_simple.py hourly-sync --site-url="sc-domain:example.com"

# 同步指定日期範圍的每小時數據
python gsc_simple.py hourly-sync --site-url="sc-domain:example.com" --start-date=2025-01-14 --end-date=2025-01-15
```

### 查看每小時數據總結

```bash
# 查看最近 3 天的每小時總結
python gsc_simple.py hourly-summary --site-id=1

# 查看特定日期的每小時總結
python gsc_simple.py hourly-summary --site-id=1 --date=2025-01-15
```

### 檢查每小時數據覆蓋情況

```bash
python gsc_simple.py hourly-coverage --site-id=1
```

### 每小時數據特性

- **時間範圍**：API 最多提供 10 天的每小時數據
- **數據狀態**：使用 `HOURLY_ALL` 狀態，表示數據可能不完整
- **更新頻率**：數據通常在 2-3 天後更完整
- **時間格式**：使用 ISO 8601 格式 (如：2025-04-07T00:00:00-07:00)

### 每小時數據使用場景

1. **監控近期內容表現**：快速了解新發布內容的搜尋表現
2. **時段分析**：分析不同時段的搜尋流量模式
3. **即時優化**：根據每小時數據快速調整內容策略
4. **週期比較**：對比同一週期不同天的表現

## 🚀 CLI 命令完整列表

### 基本功能

- `auth` - GSC API 認證
- `sites` - 列出站點
- `add-site <url>` - 添加站點到數據庫
- `coverage` - 檢查數據覆蓋情況

### 數據同步

- `sync` - 日常數據同步

  - `--recent-days <數量>` - 同步最近 N 天
  - `--start-date <日期> --end-date <日期>` - 同步指定範圍
  - `--site-id <ID>` - 同步特定站點
  - `--force` - 強制重建數據

- `hourly-sync` - 每小時數據同步
  - `--site-url <URL>` - 指定站點
  - `--start-date <日期> --end-date <日期>` - 指定日期範圍

### 數據查詢

- `progress` - 查看同步進度
- `hourly-summary` - 每小時數據總結
- `hourly-coverage` - 每小時數據覆蓋情況

### 監控工具

- `cancel` - 取消運行中的任務
- `api-status` - 檢查 API 使用狀態

## 常用命令示例

### 日常數據維護

```bash
# 每日增量同步（推薦）
python gsc_simple.py sync --recent-days 7

# 檢查數據狀態
python gsc_simple.py coverage

# 監控同步進度
python gsc_simple.py progress
```

### 初次設置大量數據

```bash
# 同步過去 3 個月的數據
python gsc_simple.py sync --recent-days 90

# 如果中斷了，可以重新運行相同命令
# 系統會自動跳過已有數據，繼續同步缺失部分
```

### 故障排除

```bash
# 查看所有站點和數據狀態
python gsc_simple.py sites
python gsc_simple.py coverage

# 取消卡住的任務
python gsc_simple.py cancel

# 重新認證
python gsc_simple.py auth
```

## 最佳實踐

### 1. API 配額管理

- 避免在高峰時段運行大量同步
- 使用 `--recent-days` 參數控制同步範圍
- 定期檢查 API 使用狀態

### 2. 數據同步策略

- **日常維護**: 每天同步最近 7 天的數據
- **歷史數據**: 分批同步，每次不超過 30 天
- **監控**: 定期檢查數據覆蓋情況

### 3. 錯誤處理

- 查看日誌文件 `gsc_simple.log` 排查問題
- 中斷後檢查 `progress` 狀態
- 必要時使用 `cancel` 清理卡住的任務

### 4. 系統維護

- 定期備份數據庫文件 `gsc_data.db`
- 清理舊的日誌文件
- 監控磁盤空間使用

## 常見問題

### Q: 認證失敗怎麼辦？

A: 檢查 `client_secret.json` 文件是否正確，重新運行 `auth` 命令

### Q: 數據同步中斷了怎麼辦？

A: 重新運行相同的同步命令，系統會自動繼續未完成的部分

### Q: 如何查看同步了多少數據？

A: 使用 `coverage` 命令查看數據覆蓋情況

### Q: API 配額用完了怎麼辦？

A: 等到第二天重置，或聯繫 Google 申請更高配額

### Q: 數據庫文件太大怎麼辦？

A: 考慮按站點或時間範圍進行數據清理

## ⚠️ 重要限制

**API 限制提醒：**

- 每日請求限制：100,000 次
- 每分鐘請求限制：1,200 次
- 每次請求最大行數：1,000 行
- 數據延遲：2-3 天
- 每小時數據範圍：最多 10 天

**注意事項：**

- GSC 數據有 2-3 天延遲
- 每小時數據可能不完整，建議等待 2-3 天後查詢
- Search Console 中的數據可能與實際搜尋結果略有差異

## 技術支持

如遇到問題，請檢查：

1. 日誌文件 `gsc_simple.log`
2. 網絡連接狀態
3. Google API 憑證有效性
4. 磁盤空間是否足夠

建議在測試環境先運行小範圍的數據同步，確認無誤後再進行大規模同步。

## 📖 更多文檔

- **數據庫建置與配額分析**：`docs/DATABASE_SETUP_AND_QUOTA_ANALYSIS.md`
- **項目結構說明**：`docs/PROJECT_STRUCTURE.md`
- **代碼質量改善**：`docs/CODE_QUALITY_IMPROVEMENTS.md`
- **優化總結**：`docs/OPTIMIZATION_SUMMARY.md`
