# 數據庫建置與 API 配額分析

## 🏗️ 數據庫建置策略

### 1. 數據庫初始化

數據庫會在首次運行時自動建置，包含以下核心表：

```sql
-- 站點信息表
CREATE TABLE sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 關鍵字表
CREATE TABLE keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    site_id INTEGER NOT NULL,
    category TEXT,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites (id),
    UNIQUE(keyword, site_id)
);

-- 日排名數據表
CREATE TABLE daily_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    keyword_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    query TEXT,
    position REAL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    page TEXT,
    country TEXT DEFAULT 'TWN',
    device TEXT DEFAULT 'ALL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites (id),
    FOREIGN KEY (keyword_id) REFERENCES keywords (id),
    UNIQUE(site_id, keyword_id, date, query, country, device)
);

-- 頁面數據表
CREATE TABLE page_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    page TEXT NOT NULL,
    date TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    position REAL DEFAULT 0,
    country TEXT DEFAULT 'TWN',
    device TEXT DEFAULT 'ALL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites (id),
    UNIQUE(site_id, page, date, country, device)
);

-- 每小時排名數據表 (2025年新功能)
CREATE TABLE hourly_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    keyword_id INTEGER,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    hour_timestamp TEXT NOT NULL,
    query TEXT,
    position REAL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    page TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites (id),
    FOREIGN KEY (keyword_id) REFERENCES keywords (id),
    UNIQUE(site_id, hour_timestamp, query, page)
);

-- 任務追蹤表
CREATE TABLE sync_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER,
    task_type TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    start_date TEXT,
    end_date TEXT,
    total_records INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites (id)
);
```

### 2. 數據庫索引優化

自動創建的索引確保查詢性能：

```sql
-- 核心查詢索引
CREATE INDEX idx_daily_rankings_date ON daily_rankings(date);
CREATE INDEX idx_daily_rankings_site ON daily_rankings(site_id);
CREATE INDEX idx_daily_rankings_keyword ON daily_rankings(keyword_id);
CREATE INDEX idx_page_data_date ON page_data(date);
CREATE INDEX idx_page_data_site ON page_data(site_id);

-- 每小時數據專用索引
CREATE INDEX idx_hourly_rankings_date ON hourly_rankings(date);
CREATE INDEX idx_hourly_rankings_site ON hourly_rankings(site_id);
CREATE INDEX idx_hourly_rankings_hour ON hourly_rankings(hour);
CREATE INDEX idx_hourly_rankings_timestamp ON hourly_rankings(hour_timestamp);

-- 任務追蹤索引
CREATE INDEX idx_sync_tasks_status ON sync_tasks(status);
```

## 📊 API 配額使用分析

### Google Search Console API 限制

```
📋 官方配額限制：
• 每日請求數：100,000 次
• 每分鐘請求數：1,200 次
• 每次請求最大行數：1,000 行
• 數據延遲：2-3 天
• 每小時數據範圍：最多 10 天 (2025年新功能)
```

### 實際使用測試數據

基於我們的測試結果：

**日常數據同步 (每天)**

- 每個站點、每天約需 **2-5 個 API 請求**
- 每次請求獲得約 **200-1000 筆記錄**
- 單站點 30 天數據約需 **60-150 個請求**

**每小時數據同步 (特殊功能)**

- 每個站點、每天約需 **3-8 個 API 請求**
- 數據密度更高，平均每請求 **500-1500 筆記錄**
- 10 天每小時數據約需 **30-80 個請求**

## 🔢 配額計算與建置能力

### 場景 1: 單站點歷史數據建置

**保守估算:**

- 每天需要: 3 個請求
- 1 年數據 (365 天): 3 × 365 = **1,095 個請求**
- **可建置歷史:** 100,000 ÷ 1,095 = **91 年的數據**

**現實估算:**

- 每天需要: 5 個請求
- 1 年數據: 5 × 365 = **1,825 個請求**
- **可建置歷史:** 100,000 ÷ 1,825 = **54 年的數據**

### 場景 2: 多站點同時建置

**10 個活躍站點:**

- 每個站點每天: 5 個請求
- 10 站點 × 30 天: 10 × 5 × 30 = **1,500 個請求**
- **每日可建置:** 100,000 ÷ 1,500 = **66 組 (30 天數據)**
- **實際建議:** 每天建置 2-3 年的歷史數據

**建議策略:** 分批建置，每天處理 2-3 年範圍

### 場景 3: 每小時數據建置

**單站點每小時數據:**

- 10 天每小時數據: 約 50 個請求
- **每日可建置:** 100,000 ÷ 50 = **2,000 組 (10 天數據)**
- **等效:** 可建置約 54 年的每小時數據

**多站點每小時數據:**

- 10 站點 × 10 天: 10 × 50 = **500 個請求**
- **每日可建置:** 100,000 ÷ 500 = **200 組**
- **等效:** 可建置約 5 年的多站點每小時數據

## 🚀 最佳建置策略

### 1. 分階段建置方案

**第一階段 - 核心數據 (優先級: 高)**

```bash
# 建置最近 90 天的核心數據
python gsc_simple.py sync --all-sites --start-date=2024-10-01 --end-date=2024-12-31
```

- 預估請求數: **450-900 個**
- 可完成度: **100%**
- 包含: 關鍵字排名、頁面數據

**第二階段 - 歷史數據 (優先級: 中)**

```bash
# 分批建置歷史數據，每次 6 個月
python gsc_simple.py sync --all-sites --start-date=2024-01-01 --end-date=2024-06-30
python gsc_simple.py sync --all-sites --start-date=2023-07-01 --end-date=2023-12-31
```

- 每批預估請求數: **900-1,800 個**
- 可在 **2-3 天**內完成多年數據

**第三階段 - 每小時數據 (優先級: 低)**

```bash
# 建置最近的每小時數據
python gsc_simple.py hourly-sync --site-url="sc-domain:example.com"
```

- 預估請求數: **50-100 個**
- 適合**近期監控**和**時段分析**

### 2. 日常維護方案

**每日自動同步**

```bash
# 每天同步最近 7 天 (確保數據完整性)
python gsc_simple.py sync --all-sites --recent-days=7
```

- 預估請求數: **35-70 個**
- 配額使用率: **0.07%**
- 可持續運行: **100%**

**每週深度同步**

```bash
# 每週同步最近 30 天 (補強數據)
python gsc_simple.py sync --all-sites --recent-days=30
```

- 預估請求數: **150-300 個**
- 配額使用率: **0.3%**
- 週末執行最佳

## 📈 配額監控與優化

### 配額使用監控

```bash
# 檢查 API 使用狀態
python gsc_simple.py api-status

# 查看近期同步記錄
python gsc_simple.py progress
```

### 優化建議

1. **批次大小控制**

   - 避免單次請求過大
   - 使用 `row_limit=1000` 最大化效率

2. **請求間隔管理**

   - 自動控制請求頻率
   - 避免超出每分鐘限制

3. **錯誤恢復機制**

   - 配額耗盡時自動暫停
   - 第二天自動重新開始

4. **增量同步優化**
   - 只同步缺失的數據
   - 避免重複 API 調用

## 💾 儲存空間需求

### 數據量估算

**單站點年度數據:**

- 日排名記錄: ~365,000 筆 (1,000 關鍵字/天)
- 頁面數據記錄: ~36,500 筆 (100 頁面/天)
- 每小時記錄: ~8,760,000 筆 (1,000 查詢 ×24 小時 ×365 天)
- **總計:** ~9.1M 記錄/年

**儲存空間:**

- SQLite 壓縮率高
- 單站點年度數據: ~**500MB-1GB**
- 10 站點年度數據: ~**5-10GB**
- 建議預留: **20-50GB** (安全餘裕)

## 🎯 實施建議

### 適合大規模建置的策略

1. **週末批次處理**

   - 利用配額充足時段
   - 可連續運行數小時

2. **優先級分類**

   - 核心站點優先
   - 歷史數據次之
   - 每小時數據最後

3. **監控與調整**
   - 每日檢查進度
   - 根據 API 使用率調整策略
   - 保留 20% 配額用於緊急需求

### 長期維護計劃

- **日常:** 最近 7 天增量同步
- **週度:** 最近 30 天補強同步
- **月度:** 歷史數據回填
- **季度:** 每小時數據建置

這個策略可確保在 **API 配額限制下**完成**大規模數據建置**，同時保持**高效的日常維護**。
