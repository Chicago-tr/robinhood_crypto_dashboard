const API_BASE = 'http://localhost:5000/api';

let portfolioChart = null;
let priceHistory = [];

// Initialize dashboard
async function init() {
    await checkHealth();
    await loadPortfolio();
    await loadRiskStatus();
    await loadOrders();
    
    // Start auto-refresh
    setInterval(loadPortfolio, 30000);
    setInterval(loadRiskStatus, 30000);
}

// Check API health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.getElementById('statusText');
        
        if (data.initialized) {
            statusDot.classList.add('healthy');
            statusText.textContent = 'Connected & Active';
        } else {
            statusDot.classList.remove('healthy');
            statusText.textContent = 'Initializing...';
        }
    } catch (error) {
        console.error('Health check failed:', error);
        document.getElementById('statusText').textContent = 'Disconnected';
    }
}

// Load portfolio data
async function loadPortfolio() {
    try {
        const response = await fetch(`${API_BASE}/portfolio`);
        const data = await response.json();
        
        updatePortfolioSummary(data);
        updateHoldingsTable(data.holdings);
        updateChart(data.total_value);
    } catch (error) {
        console.error('Failed to load portfolio:', error);
    }
}

// Update portfolio summary
function updatePortfolioSummary(data) {
    document.getElementById('totalValue').textContent = 
        formatCurrency(data.total_value);
    
    const pnlElem = document.getElementById('pnl');
    pnlElem.textContent = formatCurrency(data.pnl);
    pnlElem.className = data.pnl >= 0 ? 'value positive' : 'value negative';
    
    const pnlPercentElem = document.getElementById('pnlPercent');
    pnlPercentElem.textContent = formatPercent(data.pnl_percent);
    pnlPercentElem.className = data.pnl_percent >= 0 ? 'value positive' : 'value negative';
    
    document.getElementById('peakValue').textContent = 
        formatCurrency(data.peak_value);
}

// Load risk status
async function loadRiskStatus() {
    try {
        const response = await fetch(`${API_BASE}/risk`);
        const data = await response.json();
        
        document.getElementById('drawdown').textContent = 
            formatPercent(data.drawdown_percent);
        
        const liquidationStatus = document.getElementById('liquidationStatus');
        if (data.liquidation_triggered) {
            liquidationStatus.textContent = 'LIQUIDATING';
            liquidationStatus.className = 'critical';
        } else if (data.drawdown_percent > data.max_drawdown_allowed * 0.8) {
            liquidationStatus.textContent = 'Warning';
            liquidationStatus.className = 'warning';
        } else {
            liquidationStatus.textContent = 'Safe';
            liquidationStatus.className = 'safe';
        }
    } catch (error) {
        console.error('Failed to load risk status:', error);
    }
}

// Update holdings table
function updateHoldingsTable(holdings) {
    const tbody = document.getElementById('holdingsBody');
    
    if (holdings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No holdings</td></tr>';
        return;
    }
    
    tbody.innerHTML = holdings.map(h => `
        <tr>
            <td><strong>${h.symbol}</strong></td>
            <td>${h.name}</td>
            <td>${h.quantity.toFixed(6)}</td>
            <td>${formatCurrency(h.price)}</td>
            <td>${formatCurrency(h.value)}</td>
        </tr>
    `).join('');
}

// Load orders
async function loadOrders() {
    try {
        const response = await fetch(`${API_BASE}/orders`);
        const data = await response.json();
        
        const orders = data.orders || [];
        const orderHistory = document.getElementById('orderHistory');
        
        if (orders.length === 0) {
            orderHistory.innerHTML = '<p>No orders yet</p>';
            return;
        }
        
        orderHistory.innerHTML = orders.slice(0, 20).map(order => {
            const statusClass = order.status === 'filled' ? 'success' : '';
            return `
                <div class="order-item ${statusClass}">
                    <strong>${order.symbol}</strong> - ${order.side} 
                    ${order.quantity} @ ${formatCurrency(order.price)}
                    <br><small>${order.status} - ${new Date(order.created_at).toLocaleString()}</small>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load orders:', error);
    }
}

// Update risk settings
async function updateRiskSettings() {
    const maxDrawdown = document.getElementById('maxDrawdown').value;
    
    try {
        const response = await fetch(`${API_BASE}/risk/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_drawdown_percent: maxDrawdown })
        });
        
        const data = await response.json();
        if (data.success) {
            alert(`Max drawdown updated to ${maxDrawdown}%`);
            loadRiskStatus();
        }
    } catch (error) {
        console.error('Failed to update risk settings:', error);
        alert('Failed to update risk settings');
    }
}

// Reset peak value
async function resetPeak() {
    try {
        const response = await fetch(`${API_BASE}/reset-peak`);
        const data = await response.json();
        
        if (data.success) {
            alert('Peak value reset');
            loadRiskStatus();
        }
    } catch (error) {
        console.error('Failed to reset peak:', error);
        alert('Failed to reset peak value');
    }
}

// ============ RECONCILIATION FUNCTIONS ============

// Save daily snapshot
async function saveSnapshot() {
    try {
        const response = await fetch(`${API_BASE}/snapshot`);
        const data = await response.json();
        
        if (data.success) {
            alert(`Snapshot saved!\n\nPath: ${data.snapshot_path}\nTotal Value: ${formatCurrency(data.total_value)}\nTime: ${new Date(data.timestamp).toLocaleString()}`);
        }
    } catch (error) {
        console.error('Failed to save snapshot:', error);
        alert('Failed to save snapshot');
    }
}

// Reconcile positions
async function reconcilePositions() {
    try {
        const response = await fetch(`${API_BASE}/reconcile`);
        const data = await response.json();
        
        displayReconciliationResult(data);
    } catch (error) {
        console.error('Failed to reconcile positions:', error);
        alert('Failed to reconcile positions');
    }
}

// Generate daily CSV report
async function generateDailyReport() {
    try {
        const response = await fetch(`${API_BASE}/daily-report`);
        const data = await response.json();
        
        if (data.success) {
            alert(`Daily position report generated!\n\nPath: ${data.report_path}\nTime: ${new Date(data.timestamp).toLocaleString()}`);
        }
    } catch (error) {
        console.error('Failed to generate report:', error);
        alert('Failed to generate daily report');
    }
}

// Display reconciliation results
function displayReconciliationResult(data) {
    const resultDiv = document.getElementById('reconciliationResult');
    resultDiv.style.display = 'block';
    
    if (!data.reconciled) {
        resultDiv.innerHTML = `
            <div class="reconciliation-warning">
                <h4>Reconciliation Not Available</h4>
                <p>${data.message}</p>
                <p><strong>Action:</strong> Click "Save Daily Position Snapshot" first to create a baseline.</p>
            </div>
        `;
        return;
    }
    
    // Determine severity class
    let severityClass = 'reconciliation-success';
    if (data.discrepancy_count > 0) {
        const hasHighSeverity = data.discrepancies.some(d => d.severity === 'high');
        severityClass = hasHighSeverity ? 'reconciliation-critical' : 'reconciliation-warning';
    }
    
    const statusTitle = data.all_match ? 'RECONCILIATION PASSED' : 'RECONCILIATION NOTICE';
    
    let discrepanciesHtml = '';
    if (data.discrepancies.length > 0) {
        discrepanciesHtml = `
            <h4>Discrepancies Found (${data.discrepancy_count}):</h4>
            <table>
                <tr>
                    <th>Type</th>
                    <th>Symbol</th>
                    <th>Previous Qty</th>
                    <th>Current Qty</th>
                    <th>Difference</th>
                    <th>Severity</th>
                </tr>
                ${data.discrepancies.map(d => `
                    <tr>
                        <td>${d.type}</td>
                        <td><strong>${d.symbol}</strong></td>
                        <td>${d.previous_quantity.toFixed(6)}</td>
                        <td>${d.current_quantity.toFixed(6)}</td>
                        <td>${d.difference.toFixed(6)}</td>
                        <td class="severity-${d.severity}">${d.severity}</td>
                    </tr>
                `).join('')}
            </table>
        `;
    }
    
    const valueChangeSign = data.snapshot_comparison.value_change >= 0 ? '+' : '';
    
    resultDiv.innerHTML = `
        <div class="${severityClass}">
            <h4>${statusTitle}</h4>
            <p><strong>Discrepancies:</strong> ${data.discrepancy_count}</p>
            <p><strong>Reconciliation Time:</strong> ${new Date(data.reconciliation_time).toLocaleString()}</p>
            
            <div style="margin-top: 15px; padding: 10px; background: white; border-radius: 4px;">
                <h5>Portfolio Value Comparison:</h5>
                <p>Previous Snapshot (${new Date(data.snapshot_comparison.previous_snapshot_time).toLocaleString()}): ${formatCurrency(data.snapshot_comparison.previous_total_value)}</p>
                <p>Current Total: ${formatCurrency(data.snapshot_comparison.current_total_value)}</p>
                <p>Change: ${valueChangeSign}${formatCurrency(data.snapshot_comparison.value_change)} (${valueChangeSign}${data.snapshot_comparison.value_change_percent.toFixed(2)}%)</p>
            </div>
            
            ${discrepanciesHtml}
        </div>
    `;
}

// Update chart
function updateChart(currentValue) {
    const now = new Date().getTime();
    priceHistory.push({ x: now, y: currentValue });
    
    // Keep last 100 points
    if (priceHistory.length > 100) {
        priceHistory = priceHistory.slice(-100);
    }
    
    if (!portfolioChart) {
        const canvas = document.createElement('canvas');
        canvas.id = 'portfolioChart';
        canvas.style.height = '200px';
        canvas.style.marginTop = '20px';
        
        const chartContainer = document.querySelector('.portfolio-summary');
        chartContainer.appendChild(canvas);
        
        portfolioChart = new Chart(canvas, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Portfolio Value',
                    data: priceHistory,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        type: 'linear',
                        display: false
                    },
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
    } else {
        portfolioChart.data.datasets[0].data = priceHistory;
        portfolioChart.update();
    }
}

// Helper functions
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

function formatPercent(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);