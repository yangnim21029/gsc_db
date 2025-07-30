document.addEventListener('DOMContentLoaded', async () => {
    // Load sites
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
        showError('Failed to load sites: ' + error.message);
    }
    
    // Execute query button
    document.getElementById('execute-btn').addEventListener('click', executeQuery);
    
    // Execute on Ctrl+Enter
    document.getElementById('sql-query').addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            executeQuery();
        }
    });
    
    // Convert natural language on Enter
    document.getElementById('nl-input').addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const text = e.target.value.trim();
            if (!text) return;
            
            // Show loading state
            const input = e.target;
            input.disabled = true;
            const originalPlaceholder = input.placeholder;
            input.placeholder = 'Converting...';
            
            try {
                const response = await fetch('/api/nl2sql', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });
                
                const data = await response.json();
                if (data.sql) {
                    document.getElementById('sql-query').value = data.sql;
                }
            } catch (error) {
                console.error('Failed to convert:', error);
            } finally {
                // Restore input state
                input.disabled = false;
                input.placeholder = originalPlaceholder;
            }
        }
    });
});

async function executeQuery() {
    const site = document.getElementById('site-select').value;
    const sql = document.getElementById('sql-query').value;
    
    if (!site) {
        showError('Please select a site');
        return;
    }
    
    if (!sql.trim()) {
        showError('Please enter a SQL query');
        return;
    }
    
    const resultsDiv = document.getElementById('results');
    const button = document.getElementById('execute-btn');
    
    // Show loading state
    button.disabled = true;
    button.textContent = 'Loading...';
    resultsDiv.innerHTML = '';
    
    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ site, sql })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Query failed');
        }
        
        displayResults(data.results);
        
    } catch (error) {
        showError(error.message);
    } finally {
        // Restore button state
        button.disabled = false;
        button.textContent = 'Execute Query';
    }
}

function displayResults(results) {
    const resultsDiv = document.getElementById('results');
    
    if (!results || results.length === 0) {
        resultsDiv.innerHTML = '<p style="padding: 20px;">No results found</p>';
        return;
    }
    
    // Get column names from first row
    const columns = Object.keys(results[0]);
    
    // Build table
    let html = '<table><thead><tr>';
    columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    results.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            let value = row[col];
            // Decode URLs in page column
            if (col === 'page' && typeof value === 'string') {
                value = decodeURIComponent(value);
            }
            // Handle NaN and null values
            if (value === null || (typeof value === 'number' && isNaN(value))) {
                value = '-';
            } else if (typeof value === 'number' && !isNaN(value)) {
                // Format numbers nicely
                value = value.toLocaleString();
            }
            html += `<td>${escapeHtml(String(value))}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    html += `<p style="padding: 10px; color: #666;">${results.length} rows returned</p>`;
    
    resultsDiv.innerHTML = html;
}

function showError(message) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}