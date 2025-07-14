-- GSC Database Optimized Output Format Queries
-- 優化輸出格式的查詢集合，提供更好的可讀性和實用性

-- ============================================================================
-- SQLite 輸出格式優化設置
-- ============================================================================

-- 設置SQLite輸出模式（在SQLite命令行中使用）
/*
.mode column
.headers on
.width 15 25 10 12 8 8 10
.nullvalue "N/A"
*/

-- ============================================================================
-- 格式化的基礎查詢
-- ============================================================================

-- 1. 網站性能儀表板（格式化版本）
SELECT
    PRINTF('%02d', s.id) as "ID",
    SUBSTR(s.name, 1, 20) || CASE WHEN LENGTH(s.name) > 20 THEN '...' ELSE '' END as "網站名稱",
    COUNT(DISTINCT g.date) as "活躍天數",
    PRINTF('%,d', COALESCE(SUM(g.clicks), 0)) as "總點擊",
    PRINTF('%,d', COALESCE(SUM(g.impressions), 0)) as "總曝光",
    PRINTF('%.2f%%', COALESCE(AVG(g.ctr), 0) * 100) as "平均CTR",
    PRINTF('%.1f', COALESCE(AVG(g.position), 0)) as "平均排名",
    '⭐ ' || CASE
        WHEN AVG(g.position) <= 3 THEN '優秀'
        WHEN AVG(g.position) <= 10 THEN '良好'
        WHEN AVG(g.position) <= 20 THEN '一般'
        ELSE '需改進'
    END as "評級"
FROM sites s
LEFT JOIN gsc_performance_data g ON s.id = g.site_id
WHERE g.date >= date('now', '-7 days')
GROUP BY s.id, s.name
ORDER BY SUM(g.clicks) DESC
LIMIT 10;

-- 2. 關鍵詞排行榜（美化輸出）
SELECT
    ROW_NUMBER() OVER (ORDER BY SUM(g.clicks) DESC) as "排名",
    SUBSTR(g.query, 1, 30) || CASE WHEN LENGTH(g.query) > 30 THEN '...' ELSE '' END as "關鍵詞",
    PRINTF('%,d', SUM(g.clicks)) as "點擊數",
    PRINTF('%,d', SUM(g.impressions)) as "曝光數",
    PRINTF('%.2f%%', AVG(g.ctr) * 100) as "CTR",
    PRINTF('%.1f', AVG(g.position)) as "排名",
    CASE
        WHEN AVG(g.position) <= 3 THEN '🥇'
        WHEN AVG(g.position) <= 10 THEN '🥈'
        WHEN AVG(g.position) <= 20 THEN '🥉'
        ELSE '📊'
    END as "圖標",
    CASE
        WHEN SUM(g.clicks) > 100 THEN '🔥 熱門'
        WHEN SUM(g.clicks) > 50 THEN '📈 成長'
        WHEN SUM(g.clicks) > 10 THEN '⚡ 潛力'
        ELSE '🌱 新興'
    END as "狀態"
FROM gsc_performance_data g
WHERE g.site_id = 4
    AND g.date >= date('now', '-7 days')
    AND g.query IS NOT NULL
    AND g.query != ''
GROUP BY g.query
HAVING SUM(g.clicks) > 0
ORDER BY SUM(g.clicks) DESC
LIMIT 20;

-- 3. 頁面性能報告（表格化輸出）
SELECT
    ROW_NUMBER() OVER (ORDER BY SUM(g.clicks) DESC) as "#",
    CASE
        WHEN g.page LIKE '%/' THEN SUBSTR(g.page, -30)
        ELSE SUBSTR(REPLACE(g.page, 'https://', ''), 1, 35) || '...'
    END as "頁面URL",
    PRINTF('%,d', SUM(g.clicks)) as "點擊",
    PRINTF('%,d', SUM(g.impressions)) as "曝光",
    PRINTF('%.1f%%', AVG(g.ctr) * 100) as "CTR",
    PRINTF('%.1f', AVG(g.position)) as "排名",
    COUNT(DISTINCT g.query) as "關鍵詞數",
    CASE
        WHEN AVG(g.ctr) > 0.05 THEN '🎯 高轉換'
        WHEN AVG(g.ctr) > 0.02 THEN '✅ 正常'
        WHEN SUM(g.impressions) > 100 THEN '⚠️ 待優化'
        ELSE '📊 觀察中'
    END as "建議"
FROM gsc_performance_data g
WHERE g.site_id = 4
    AND g.date >= date('now', '-7 days')
    AND g.page IS NOT NULL
GROUP BY g.page
ORDER BY SUM(g.clicks) DESC
LIMIT 15;

-- ============================================================================
-- 趨勢分析（時間序列格式化）
-- ============================================================================

-- 4. 每日趨勢圖（ASCII圖表風格）
WITH daily_stats AS (
    SELECT
        g.date,
        SUM(g.clicks) as daily_clicks,
        SUM(g.impressions) as daily_impressions,
        AVG(g.ctr) as daily_ctr
    FROM gsc_performance_data g
    WHERE g.site_id = 4
        AND g.date >= date('now', '-7 days')
    GROUP BY g.date
),
max_clicks AS (
    SELECT MAX(daily_clicks) as max_val FROM daily_stats
)
SELECT
    strftime('%m/%d', d.date) as "日期",
    strftime('%a', d.date) as "星期",
    PRINTF('%,d', d.daily_clicks) as "點擊數",
    PRINTF('%,d', d.daily_impressions) as "曝光數",
    PRINTF('%.2f%%', d.daily_ctr * 100) as "CTR",
    SUBSTR('████████████████████████████████████████',
           1,
           CAST(d.daily_clicks * 40.0 / m.max_val AS INTEGER)) as "點擊趨勢圖"
FROM daily_stats d
CROSS JOIN max_clicks m
ORDER BY d.date DESC;

-- ============================================================================
-- 競爭分析（對比格式化）
-- ============================================================================

-- 5. 位置變化報告（前後對比）
WITH recent_week AS (
    SELECT
        query,
        AVG(position) as recent_pos,
        SUM(clicks) as recent_clicks
    FROM gsc_performance_data
    WHERE site_id = 4
        AND date >= date('now', '-7 days')
        AND query IS NOT NULL
    GROUP BY query
),
previous_week AS (
    SELECT
        query,
        AVG(position) as prev_pos,
        SUM(clicks) as prev_clicks
    FROM gsc_performance_data
    WHERE site_id = 4
        AND date >= date('now', '-14 days')
        AND date < date('now', '-7 days')
        AND query IS NOT NULL
    GROUP BY query
)
SELECT
    SUBSTR(r.query, 1, 25) || '...' as "關鍵詞",
    PRINTF('%.1f', p.prev_pos) as "前週排名",
    PRINTF('%.1f', r.recent_pos) as "本週排名",
    CASE
        WHEN r.recent_pos < p.prev_pos THEN '📈 +' || PRINTF('%.1f', p.prev_pos - r.recent_pos)
        WHEN r.recent_pos > p.prev_pos THEN '📉 -' || PRINTF('%.1f', r.recent_pos - p.prev_pos)
        ELSE '➡️ 持平'
    END as "變化",
    PRINTF('%,d', r.recent_clicks) as "本週點擊",
    CASE
        WHEN p.prev_pos - r.recent_pos > 5 THEN '🚀 大躍進'
        WHEN p.prev_pos - r.recent_pos > 2 THEN '⬆️ 上升'
        WHEN p.prev_pos - r.recent_pos > 0 THEN '📈 微升'
        WHEN r.recent_pos - p.prev_pos > 2 THEN '⬇️ 下降'
        ELSE '➡️ 穩定'
    END as "趨勢"
FROM recent_week r
JOIN previous_week p ON r.query = p.query
WHERE ABS(r.recent_pos - p.prev_pos) > 0.5
ORDER BY (p.prev_pos - r.recent_pos) DESC
LIMIT 15;

-- ============================================================================
-- 機會分析（actionable insights）
-- ============================================================================

-- 6. 優化機會報告
SELECT
    '🎯 ' || SUBSTR(g.query, 1, 30) as "關鍵詞",
    PRINTF('%.1f', AVG(g.position)) as "當前排名",
    PRINTF('%,d', SUM(g.impressions)) as "曝光潛力",
    PRINTF('%,d', SUM(g.clicks)) as "當前點擊",
    PRINTF('%,d', CAST(SUM(g.impressions) * 0.1 AS INTEGER)) as "預估潛力",
    CASE
        WHEN AVG(g.position) BETWEEN 4 AND 6 THEN '🥉 衝前三'
        WHEN AVG(g.position) BETWEEN 7 AND 10 THEN '🔝 進首頁'
        WHEN AVG(g.position) BETWEEN 11 AND 15 THEN '📈 快速提升'
        WHEN AVG(g.position) BETWEEN 16 AND 20 THEN '⚡ 進首頁'
        ELSE '📊 長期優化'
    END as "優化策略",
    CASE
        WHEN SUM(g.impressions) > 1000 THEN '🔥 高優先級'
        WHEN SUM(g.impressions) > 500 THEN '⭐ 中優先級'
        ELSE '📝 低優先級'
    END as "優先級"
FROM gsc_performance_data g
WHERE g.site_id = 4
    AND g.date >= date('now', '-7 days')
    AND g.query IS NOT NULL
GROUP BY g.query
HAVING SUM(g.impressions) > 50
    AND AVG(g.position) BETWEEN 4 AND 20  -- 移到HAVING子句
ORDER BY SUM(g.impressions) DESC
LIMIT 12;

-- ============================================================================
-- 設備性能對比（分類顯示）
-- ============================================================================

-- 7. 設備性能矩陣
SELECT
    COALESCE(g.device, '未知') as "設備類型",
    PRINTF('%,d', SUM(g.clicks)) as "總點擊",
    PRINTF('%,d', SUM(g.impressions)) as "總曝光",
    PRINTF('%.2f%%', AVG(g.ctr) * 100) as "CTR",
    PRINTF('%.1f', AVG(g.position)) as "平均排名",
    PRINTF('%.1f%%',
        SUM(g.clicks) * 100.0 /
        (SELECT SUM(clicks) FROM gsc_performance_data
         WHERE site_id = 4 AND date >= date('now', '-7 days'))
    ) as "點擊佔比",
    CASE
        WHEN g.device = 'MOBILE' THEN '📱'
        WHEN g.device = 'DESKTOP' THEN '💻'
        WHEN g.device = 'TABLET' THEN '📟'
        ELSE '❓'
    END as "圖標"
FROM gsc_performance_data g
WHERE g.site_id = 4
    AND g.date >= date('now', '-7 days')
    AND g.device IS NOT NULL
GROUP BY g.device
ORDER BY SUM(g.clicks) DESC;

-- ============================================================================
-- 摘要報告（executive summary）
-- ============================================================================

-- 8. 執行摘要報告
SELECT
    '📊 數據概覽' as "報告類型",
    '' as "指標",
    '' as "數值",
    '' as "狀態"
UNION ALL
SELECT
    '├─ 時間範圍',
    '最近7天',
    strftime('%Y-%m-%d', date('now', '-7 days')) || ' ~ ' || strftime('%Y-%m-%d', date('now', '-1 day')),
    '✅ 最新'
UNION ALL
SELECT
    '├─ 總點擊數',
    PRINTF('%,d', SUM(clicks)),
    CASE WHEN SUM(clicks) > 1000 THEN '🔥 優秀' WHEN SUM(clicks) > 100 THEN '📈 良好' ELSE '📊 一般' END,
    ''
FROM gsc_performance_data WHERE site_id = 4 AND date >= date('now', '-7 days')
UNION ALL
SELECT
    '├─ 總曝光數',
    PRINTF('%,d', SUM(impressions)),
    CASE WHEN SUM(impressions) > 10000 THEN '🎯 高曝光' WHEN SUM(impressions) > 1000 THEN '👀 中曝光' ELSE '📱 低曝光' END,
    ''
FROM gsc_performance_data WHERE site_id = 4 AND date >= date('now', '-7 days')
UNION ALL
SELECT
    '├─ 平均CTR',
    PRINTF('%.2f%%', AVG(ctr) * 100),
    CASE WHEN AVG(ctr) > 0.05 THEN '🎯 優秀' WHEN AVG(ctr) > 0.02 THEN '✅ 良好' ELSE '⚠️ 待改進' END,
    ''
FROM gsc_performance_data WHERE site_id = 4 AND date >= date('now', '-7 days')
UNION ALL
SELECT
    '└─ 平均排名',
    PRINTF('%.1f', AVG(position)),
    CASE WHEN AVG(position) <= 5 THEN '🥇 頂級' WHEN AVG(position) <= 10 THEN '🥈 首頁' ELSE '📈 待提升' END,
    ''
FROM gsc_performance_data WHERE site_id = 4 AND date >= date('now', '-7 days');

-- ============================================================================
-- 輸出格式設置說明
-- ============================================================================

/*
🎨 SQLite 命令行美化設置：

在SQLite命令行中執行以下命令：
.mode column
.headers on
.width 5 25 10 10 8 8 12 15
.nullvalue "N/A"

或者使用表格模式：
.mode table

或者使用盒狀模式：
.mode box

📊 CSV輸出（用於Excel）：
.mode csv
.output results.csv
-- 執行查詢
.output stdout

📋 HTML輸出（用於報告）：
.mode html
.output report.html
-- 執行查詢
.output stdout

🔧 JSON輸出（用於API）：
.mode json
.output data.json
-- 執行查詢
.output stdout
*/
