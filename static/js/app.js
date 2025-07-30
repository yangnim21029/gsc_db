// GSC Data Manager - Interactive Web UI
class GSCDataManager {
    constructor() {
        this.currentSite = null;
        this.charts = {};
        this.data = {};
        this.init();
    }

    async init() {
        await this.loadSites();
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.getElementById('site-select').addEventListener('change', () => this.onSiteChange());
        document.getElementById('refresh-btn').addEventListener('click', () => this.refreshData());
        document.getElementById('export-btn').addEventListener('click', () => this.exportData());
        document.getElementById('compare-btn').addEventListener('click', () => this.compareData());
        document.getElementById('query-search').addEventListener('input', (e) => this.filterQueries(e.target.value));
        document.getElementById('query-sort').addEventListener('change', () => this.sortQueries());
    }

    async loadSites() {
        try {
            const response = await fetch('/api/sites');
            const data = await response.json();
            
            const siteSelect = document.getElementById('site-select');
            siteSelect.innerHTML = '<option value="">Select a site...</option>';
            
            data.sites.forEach(site => {
                const option = document.createElement('option');
                option.value = site;
                option.textContent = site;
                siteSelect.appendChild(option);
            });
        } catch (error) {
            this.showError('Failed to load sites: ' + error.message);
        }
    }

    async onSiteChange() {
        const siteSelect = document.getElementById('site-select');
        this.currentSite = siteSelect.value;
        
        if (this.currentSite) {
            await this.refreshData();
        }
    }

    async refreshData() {
        if (!this.currentSite) {
            this.showError('Please select a site first');
            return;
        }

        this.showLoading(true);
        
        try {
            // Get date range
            const days = parseInt(document.getElementById('date-range').value);
            const pageFilter = document.getElementById('page-filter').value;
            
            // Fetch tracking data
            const trackingData = await this.fetchTrackingData(days, pageFilter);
            
            // Update metrics
            this.updateMetrics(trackingData);
            
            // Update charts
            this.updateCharts(trackingData);
            
            // Update tables
            this.updateQueriesTable(trackingData);
            
        } catch (error) {
            this.showError('Failed to load data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async fetchTrackingData(days, pageFilter) {
        const pages = pageFilter ? [pageFilter] : [];
        
        const response = await fetch('/track_pages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                site: this.currentSite,
                pages: pages,
                keywords: [],
                days: days
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch tracking data');
        }
        
        return response.json();
    }

    updateMetrics(data) {
        // Calculate totals
        const totals = data.daily_data.reduce((acc, day) => {
            acc.clicks += day.clicks;
            acc.impressions += day.impressions;
            acc.ctr += day.ctr;
            acc.position += day.position;
            acc.count++;
            return acc;
        }, { clicks: 0, impressions: 0, ctr: 0, position: 0, count: 0 });

        // Update metric cards
        document.getElementById('total-clicks').textContent = this.formatNumber(totals.clicks);
        document.getElementById('total-impressions').textContent = this.formatNumber(totals.impressions);
        document.getElementById('avg-ctr').textContent = (totals.ctr / totals.count).toFixed(2) + '%';
        document.getElementById('avg-position').textContent = (totals.position / totals.count).toFixed(1);

        // Calculate changes (compare last 7 days with previous 7 days)
        if (data.daily_data.length >= 14) {
            const recent = data.daily_data.slice(-7);
            const previous = data.daily_data.slice(-14, -7);
            
            const recentMetrics = this.calculatePeriodMetrics(recent);
            const previousMetrics = this.calculatePeriodMetrics(previous);
            
            this.updateMetricChange('clicks-change', recentMetrics.clicks, previousMetrics.clicks);
            this.updateMetricChange('impressions-change', recentMetrics.impressions, previousMetrics.impressions);
            this.updateMetricChange('ctr-change', recentMetrics.ctr, previousMetrics.ctr, true);
            this.updateMetricChange('position-change', previousMetrics.position, recentMetrics.position); // Inverted for position
        }
    }

    calculatePeriodMetrics(data) {
        const metrics = data.reduce((acc, day) => {
            acc.clicks += day.clicks;
            acc.impressions += day.impressions;
            acc.ctr += day.ctr;
            acc.position += day.position;
            acc.count++;
            return acc;
        }, { clicks: 0, impressions: 0, ctr: 0, position: 0, count: 0 });
        
        metrics.ctr = metrics.ctr / metrics.count;
        metrics.position = metrics.position / metrics.count;
        
        return metrics;
    }

    updateMetricChange(elementId, current, previous, isPercentage = false) {
        const element = document.getElementById(elementId);
        const change = ((current - previous) / previous) * 100;
        
        if (isPercentage) {
            element.textContent = `${change > 0 ? '+' : ''}${change.toFixed(1)}pp`;
        } else {
            element.textContent = `${change > 0 ? '+' : ''}${change.toFixed(1)}%`;
        }
        
        element.className = 'metric-change ' + (change > 0 ? 'positive' : 'negative');
    }

    updateCharts(data) {
        // Performance over time chart
        this.updatePerformanceChart(data.daily_data);
        
        // Top pages chart
        this.updatePagesChart(data.top_pages);
    }

    updatePerformanceChart(dailyData) {
        const ctx = document.getElementById('performance-chart').getContext('2d');
        
        if (this.charts.performance) {
            this.charts.performance.destroy();
        }
        
        this.charts.performance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dailyData.map(d => d.date),
                datasets: [
                    {
                        label: 'Clicks',
                        data: dailyData.map(d => d.clicks),
                        borderColor: '#1a73e8',
                        backgroundColor: 'rgba(26, 115, 232, 0.1)',
                        yAxisID: 'y',
                    },
                    {
                        label: 'Impressions',
                        data: dailyData.map(d => d.impressions),
                        borderColor: '#34a853',
                        backgroundColor: 'rgba(52, 168, 83, 0.1)',
                        yAxisID: 'y1',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Clicks'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Impressions'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    },
                }
            }
        });
    }

    updatePagesChart(topPages) {
        const ctx = document.getElementById('pages-chart').getContext('2d');
        
        if (this.charts.pages) {
            this.charts.pages.destroy();
        }
        
        // Take top 10 pages
        const pages = topPages.slice(0, 10);
        
        this.charts.pages = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: pages.map(p => this.truncateUrl(p.page, 30)),
                datasets: [{
                    label: 'Clicks',
                    data: pages.map(p => p.clicks),
                    backgroundColor: '#1a73e8',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: (context) => {
                                return pages[context[0].dataIndex].page;
                            }
                        }
                    }
                }
            }
        });
    }

    updateQueriesTable(data) {
        const tableDiv = document.getElementById('queries-table');
        
        if (!data.queries || data.queries.length === 0) {
            tableDiv.innerHTML = '<p>No query data available</p>';
            return;
        }
        
        this.queriesData = data.queries;
        this.renderQueriesTable();
    }

    renderQueriesTable() {
        const tableDiv = document.getElementById('queries-table');
        const searchTerm = document.getElementById('query-search').value.toLowerCase();
        const sortBy = document.getElementById('query-sort').value;
        
        let filteredQueries = this.queriesData.filter(q => 
            q.query.toLowerCase().includes(searchTerm)
        );
        
        // Sort queries
        filteredQueries.sort((a, b) => {
            switch(sortBy) {
                case 'clicks': return b.clicks - a.clicks;
                case 'impressions': return b.impressions - a.impressions;
                case 'ctr': return b.ctr - a.ctr;
                case 'position': return a.position - b.position;
                default: return b.clicks - a.clicks;
            }
        });
        
        // Take top 50
        filteredQueries = filteredQueries.slice(0, 50);
        
        const table = `
            <table>
                <thead>
                    <tr>
                        <th>Query</th>
                        <th>Clicks</th>
                        <th>Impressions</th>
                        <th>CTR</th>
                        <th>Position</th>
                    </tr>
                </thead>
                <tbody>
                    ${filteredQueries.map(q => `
                        <tr>
                            <td>${this.escapeHtml(q.query)}</td>
                            <td>${q.clicks}</td>
                            <td>${this.formatNumber(q.impressions)}</td>
                            <td>${q.ctr.toFixed(2)}%</td>
                            <td>${q.position.toFixed(1)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        tableDiv.innerHTML = table;
    }

    filterQueries(searchTerm) {
        this.renderQueriesTable();
    }

    sortQueries() {
        this.renderQueriesTable();
    }

    async compareData() {
        if (!this.currentSite) {
            this.showError('Please select a site first');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const period = document.getElementById('compare-period').value;
            
            const response = await fetch('/compare_periods', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    site: this.currentSite,
                    period_type: period
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch comparison data');
            }
            
            const data = await response.json();
            this.updateComparisonTable(data);
            
        } catch (error) {
            this.showError('Failed to compare periods: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    updateComparisonTable(data) {
        const tableDiv = document.getElementById('comparison-table');
        
        const table = `
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>${data.current_period}</th>
                        <th>${data.previous_period}</th>
                        <th>Change</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Clicks</td>
                        <td>${this.formatNumber(data.current_metrics.clicks)}</td>
                        <td>${this.formatNumber(data.previous_metrics.clicks)}</td>
                        <td class="${data.changes.clicks_change > 0 ? 'positive' : 'negative'}">
                            ${data.changes.clicks_change > 0 ? '+' : ''}${data.changes.clicks_change.toFixed(1)}%
                        </td>
                    </tr>
                    <tr>
                        <td>Impressions</td>
                        <td>${this.formatNumber(data.current_metrics.impressions)}</td>
                        <td>${this.formatNumber(data.previous_metrics.impressions)}</td>
                        <td class="${data.changes.impressions_change > 0 ? 'positive' : 'negative'}">
                            ${data.changes.impressions_change > 0 ? '+' : ''}${data.changes.impressions_change.toFixed(1)}%
                        </td>
                    </tr>
                    <tr>
                        <td>CTR</td>
                        <td>${data.current_metrics.ctr.toFixed(2)}%</td>
                        <td>${data.previous_metrics.ctr.toFixed(2)}%</td>
                        <td class="${data.changes.ctr_change > 0 ? 'positive' : 'negative'}">
                            ${data.changes.ctr_change > 0 ? '+' : ''}${data.changes.ctr_change.toFixed(1)}pp
                        </td>
                    </tr>
                    <tr>
                        <td>Avg Position</td>
                        <td>${data.current_metrics.position.toFixed(1)}</td>
                        <td>${data.previous_metrics.position.toFixed(1)}</td>
                        <td class="${data.changes.position_change < 0 ? 'positive' : 'negative'}">
                            ${data.changes.position_change > 0 ? '+' : ''}${data.changes.position_change.toFixed(1)}
                        </td>
                    </tr>
                </tbody>
            </table>
        `;
        
        tableDiv.innerHTML = table;
    }

    async exportData() {
        if (!this.currentSite) {
            this.showError('Please select a site first');
            return;
        }
        
        // For now, export the current queries data as CSV
        if (!this.queriesData || this.queriesData.length === 0) {
            this.showError('No data to export');
            return;
        }
        
        const csv = this.convertToCSV(this.queriesData);
        this.downloadCSV(csv, `gsc-data-${this.currentSite.replace(/[^a-z0-9]/gi, '-')}-${new Date().toISOString().split('T')[0]}.csv`);
    }

    convertToCSV(data) {
        const headers = ['Query', 'Clicks', 'Impressions', 'CTR', 'Position'];
        const rows = data.map(item => [
            item.query,
            item.clicks,
            item.impressions,
            item.ctr.toFixed(2),
            item.position.toFixed(1)
        ]);
        
        return [
            headers.join(','),
            ...rows.map(row => row.map(cell => 
                typeof cell === 'string' && cell.includes(',') ? `"${cell}"` : cell
            ).join(','))
        ].join('\n');
    }

    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    truncateUrl(url, maxLength) {
        if (url.length <= maxLength) return url;
        return url.substring(0, maxLength) + '...';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showLoading(show) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.remove('hidden');
        } else {
            loading.classList.add('hidden');
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('error');
        const errorMessage = document.getElementById('error-message');
        errorMessage.textContent = message;
        errorDiv.classList.remove('hidden');
        
        setTimeout(() => {
            errorDiv.classList.add('hidden');
        }, 5000);
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new GSCDataManager();
});