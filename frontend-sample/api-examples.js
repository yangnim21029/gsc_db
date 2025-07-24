/**
 * GSC API JavaScript Examples
 * These examples show how to call the GSC API from frontend applications
 * 
 * IMPORTANT: Test Data Management
 * - Use site_id: 3 (test.com) for testing, not production sites
 * - Test data should be cleaned up after testing
 * - Run `python clean_test_data.py` to remove test data
 * - Avoid using production site IDs (e.g., 17 for urbanlifehk.com)
 */

const API_BASE_URL = 'http://localhost:8000';

// ============================================
// 1. SITES MANAGEMENT
// ============================================

// List all sites
async function listSites() {
    const response = await fetch(`${API_BASE_URL}/api/v1/sites`);
    const sites = await response.json();
    return sites;
}

// Get specific site details
async function getSiteDetails(siteId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/sites/${siteId}`);
    const site = await response.json();
    return site;
}

// ============================================
// 2. SEARCH & ANALYTICS
// ============================================

// Search queries with ranking data
async function searchQueries(hostname, keywords, dateFrom, dateTo) {
    const response = await fetch(`${API_BASE_URL}/api/v1/analytics/ranking-data`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            hostname: hostname,
            date_from: dateFrom,
            date_to: dateTo,
            queries: keywords,
            exact_match: false,
            limit: 100,
            group_by: ['query', 'page']
        })
    });

    const data = await response.json();
    return data;
}

// Get performance trends
async function getPerformanceTrends(hostname, days = 30) {
    const params = new URLSearchParams({
        hostname: hostname,
        days: days
    });

    const response = await fetch(`${API_BASE_URL}/api/v1/analytics/performance-trends?${params}`);
    const trends = await response.json();
    return trends;
}

// Get page-keyword performance with optional URL filtering
async function getPageKeywordPerformance(hostname, days = 30, urlFilter = null) {
    const requestBody = {
        hostname: hostname,
        days: days
    };

    // Add URL filter if provided
    if (urlFilter) {
        requestBody.query = urlFilter;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/page-keyword-performance/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
    });

    const data = await response.json();
    return data;
}

// Download performance data as CSV with optional URL filtering
async function downloadPerformanceCSV(hostname, days = 30, urlFilter = null) {
    const params = new URLSearchParams({
        hostname: hostname,
        days: days
    });

    // Add URL filter if provided
    if (urlFilter) {
        params.append('query', urlFilter);
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/page-keyword-performance/csv?${params}`);

    if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `performance_${hostname}_${days}days.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// ============================================
// 3. SYNC STATUS
// ============================================

// Check sync status
async function checkSyncStatus(hostname, days = 30) {
    const params = new URLSearchParams({
        hostname: hostname,
        days: days
    });

    const response = await fetch(`${API_BASE_URL}/api/v1/sync/status?${params}`);
    const status = await response.json();
    return status;
}

// ============================================
// 4. EXAMPLE WORKFLOWS
// ============================================

// Example 1: Search for specific keywords and display results
async function searchAndDisplay() {
    try {
        // Search for "理髮" related queries
        const results = await searchQueries(
            'businessfocus.io',
            ['理髮'],
            '2025-01-01',
            '2025-01-31'
        );

        console.log(`Found ${results.total} results`);
        console.log('Top 5 results:');

        results.data.slice(0, 5).forEach(item => {
            console.log(`- ${item.query} (${item.clicks} clicks, position ${item.position.toFixed(1)})`);
        });

    } catch (error) {
        console.error('Search failed:', error);
    }
}

// Example 2: Build a performance dashboard
async function buildDashboard(hostname) {
    try {
        // Fetch all data in parallel
        const [sites, trends, pagePerformance] = await Promise.all([
            listSites(),
            getPerformanceTrends(hostname, 30),
            getPageKeywordPerformance(hostname, 30)
        ]);

        // Process and display data
        const dashboard = {
            totalClicks: trends.summary.total_clicks,
            avgPosition: trends.summary.avg_position,
            uniqueQueries: trends.summary.unique_queries,
            topPages: pagePerformance.data.slice(0, 10),
            trendData: trends.data
        };

        return dashboard;

    } catch (error) {
        console.error('Dashboard loading failed:', error);
    }
}

// Example 3: Monitor sync status with retry
async function monitorSync(hostname, maxRetries = 5) {
    let retries = 0;

    while (retries < maxRetries) {
        try {
            const status = await checkSyncStatus(hostname, 7);

            const syncedDays = Object.values(status.daily_coverage).filter(v => v).length;
            const totalDays = Object.keys(status.daily_coverage).length;

            console.log(`Sync progress: ${syncedDays}/${totalDays} days`);

            if (syncedDays === totalDays) {
                console.log('Sync complete!');
                return true;
            }

            // Wait 30 seconds before next check
            await new Promise(resolve => setTimeout(resolve, 30000));
            retries++;

        } catch (error) {
            console.error('Sync check failed:', error);
            retries++;
        }
    }

    console.log('Max retries reached');
    return false;
}

// ============================================
// 5. ERROR HANDLING
// ============================================

// Wrapper function with error handling
async function apiCall(fn, ...args) {
    try {
        const result = await fn(...args);
        return { success: true, data: result };
    } catch (error) {
        console.error(`API call failed:`, error);

        // Parse error response
        let errorMessage = 'Unknown error';
        if (error.response) {
            try {
                const errorData = await error.response.json();
                errorMessage = errorData.detail || errorData.message || errorMessage;
            } catch (e) {
                errorMessage = error.response.statusText;
            }
        }

        return {
            success: false,
            error: errorMessage,
            status: error.response?.status
        };
    }
}

// Example usage with error handling
async function safeSearch(hostname, keywords) {
    const result = await apiCall(
        searchQueries,
        hostname,
        keywords,
        '2025-01-01',
        '2025-01-31'
    );

    if (result.success) {
        console.log('Search results:', result.data);
    } else {
        console.error('Search failed:', result.error);
    }
}

// Example 4: Get performance data for specific page types
async function getPageTypePerformance(hostname) {
    try {
        // Get performance for different page types
        const [articlePages, tagPages, newsPages] = await Promise.all([
            getPageKeywordPerformance(hostname, 30, '/article'),
            getPageKeywordPerformance(hostname, 30, '/tag'),
            getPageKeywordPerformance(hostname, 30, '/news')
        ]);

        console.log('Article pages:', articlePages.data.length);
        console.log('Tag pages:', tagPages.data.length);
        console.log('News pages:', newsPages.data.length);

        // Find top performing article pages
        const topArticles = articlePages.data
            .sort((a, b) => b.total_clicks - a.total_clicks)
            .slice(0, 5);

        console.log('Top 5 article pages:');
        topArticles.forEach(page => {
            console.log(`- ${page.url}: ${page.total_clicks} clicks, ${page.keyword_count} keywords`);
        });

        // Download CSV for article pages
        await downloadPerformanceCSV(hostname, 30, '/article');

    } catch (error) {
        console.error('Failed to get page type performance:', error);
    }
}

// Example 5: Analyze specific URL patterns
async function analyzeUrlPatterns(hostname, patterns) {
    const results = {};

    for (const pattern of patterns) {
        const data = await getPageKeywordPerformance(hostname, 30, pattern);
        results[pattern] = {
            pageCount: data.total_pages,
            totalKeywords: data.total_keywords,
            avgKeywordsPerPage: data.total_keywords / data.total_pages || 0,
            topPages: data.data.slice(0, 3).map(p => ({
                url: p.url,
                clicks: p.total_clicks,
                keywords: p.keyword_count
            }))
        };
    }

    return results;
}

// Usage example:
// const patterns = ['/article', '/tag', '/category', '/author'];
// const analysis = await analyzeUrlPatterns('example.com', patterns);

// ============================================
// 6. UTILITY FUNCTIONS
// ============================================

// Format date for API
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// Get date range for last N days
function getDateRange(days) {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);

    return {
        date_from: formatDate(start),
        date_to: formatDate(end)
    };
}

// Parse hostname from various formats
function parseHostname(input) {
    // Remove protocol and www
    return input
        .replace(/^https?:\/\//, '')
        .replace(/^www\./, '')
        .replace(/\/$/, '');
}

// Convert results to CSV format
function resultsToCSV(results) {
    if (!results.data || results.data.length === 0) {
        return '';
    }

    const headers = Object.keys(results.data[0]);
    const rows = results.data.map(row =>
        headers.map(h => `"${row[h] || ''}"`).join(',')
    );

    return [headers.join(','), ...rows].join('\n');
}

// Export all functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        listSites,
        getSiteDetails,
        searchQueries,
        getPerformanceTrends,
        getPageKeywordPerformance,
        downloadPerformanceCSV,
        checkSyncStatus,
        searchAndDisplay,
        buildDashboard,
        monitorSync,
        apiCall,
        formatDate,
        getDateRange,
        parseHostname,
        resultsToCSV
    };
}
