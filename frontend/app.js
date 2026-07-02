const API_BASE = 'http://localhost:5000/api';

let portfolioChart = null;
let priceHistory = [];

// Initialize the dashboard
async function init() {
    await checkHealth();
    await loadPortfolio();
    await loadRiskStatus();
    await loadOrders();
    
    // Start auto-refresh, 30s currently can be a lot faster
    setInterval(loadPortfolio, 30000);
    setInterval(loadRiskStatus, 30000);
}

// Testing API
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

function updateLastUpdated() {
    const now = new Date();
    document.getElementById('lastUpdated').textContent = `Last updated: ${now.toLocaleString()}`;
}

let notificationTimeout = null;
function showNotification(message, type = 'success', duration = 4500) {
    const notification = document.getElementById('notification');
    if (!notification) return;

    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';

    if (notificationTimeout) {
        clearTimeout(notificationTimeout);
    }

    notificationTimeout = setTimeout(() => {
        notification.classList.add('hide');
        setTimeout(() => {
            notification.style.display = 'none';
            notification.classList.remove('hide');
        }, 200);
    }, duration);
}

function displaySectionError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = `<p class="error-text">${message}</p>`;
    }
}


async function loadPortfolio() {
    try {
        const response = await fetch(`${API_BASE}/portfolio`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        console.log(">>> Portfolio data from API:", data);
        console.log(">>> Holdings:", data.holdings);
        
        updatePortfolioSummary(data);
        updateHoldingsTable(data.holdings);
        updateChart(data.total_value);
        updateLastUpdated();
    } catch (error) {
        console.error('Failed to load portfolio:', error);
        displaySectionError('holdingsBody', 'Unable to load portfolio data at this time.');
        document.getElementById('totalValue').textContent = '--';
        document.getElementById('pnl').textContent = '--';
        document.getElementById('pnlPercent').textContent = '--';
        document.getElementById('peakValue').textContent = '--';
    }
}


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

// Check portfolio against risk thresholds
async function loadRiskStatus() {
    try {
        const response = await fetch(`${API_BASE}/risk`);
        const data = await response.json();
        
        document.getElementById('drawdown').textContent = 
            formatPercent(data.drawdown_percent);
        
        const liquidationStatus = document.getElementById('liquidationStatus');
        const riskTrend = document.getElementById('riskTrend');
        if (data.liquidation_triggered) {
            liquidationStatus.textContent = 'LIQUIDATING';
            liquidationStatus.className = 'status-chip critical';
            riskTrend.textContent = 'Deteriorating';
            riskTrend.className = 'status-chip deteriorating';
        } else if (data.drawdown_percent > data.max_drawdown_allowed * 0.75) {
            liquidationStatus.textContent = 'Warning';
            liquidationStatus.className = 'status-chip warning';
            riskTrend.textContent = 'Deteriorating';
            riskTrend.className = 'status-chip deteriorating';
        } else if (data.drawdown_percent > data.max_drawdown_allowed * 0.35) {
            liquidationStatus.textContent = 'Warning';
            liquidationStatus.className = 'status-chip warning';
            riskTrend.textContent = 'Caution';
            riskTrend.className = 'status-chip warning';
        } else {
            liquidationStatus.textContent = 'Safe';
            liquidationStatus.className = 'status-chip safe';
            riskTrend.textContent = 'Stable';
            riskTrend.className = 'status-chip stable';
        }
    } catch (error) {
        console.error('Failed to load risk status:', error);
    }
}

// Map of Symbols to their coin names
const assetDisplayNames = {
    RAY: 'Raydium',
    BTC: 'Bitcoin',
    ETH: 'Ethereum',
    SOL: 'Solana',
    ADA: 'Cardano',
    DOGE: 'Dogecoin',
    DOT: 'Polkadot',
    LINK: 'Chainlink',
    MATIC: 'Polygon',
    USDC: 'USD Coin',
    USDT: 'Tether',
    BNB: 'BNB',
    LTC: 'Litecoin',
    XRP: 'XRP',
    AVAX: 'Avalanche',
    SHIB: 'Shiba Inu',
    AAVE: 'Aave',
    UNI: 'Uniswap',
    SOL: 'Solana',
    CRV: 'Curve'
};

function getDisplayName(holding) {
    if (holding.name && holding.name !== holding.symbol) {
        return holding.name;
    }

    return assetDisplayNames[holding.symbol] || holding.symbol;
}


function updateHoldingsTable(holdings) {
    const tbody = document.getElementById('holdingsBody');
    
    if (holdings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No holdings</td></tr>';
        return;
    }
    
    tbody.innerHTML = holdings.map(h => `
        <tr>
            <td><strong>${h.symbol}</strong></td>
            <td>${getDisplayName(h)}</td>
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
            const filledQty = parseFloat(order.filled_asset_quantity || (order.executions?.[0]?.quantity ?? 0)) || 0;
            const price = parseFloat(order.average_price || order.executions?.[0]?.effective_price || 0) || 0;
            const symbol = order.symbol ? order.symbol.replace('-USD', '') : 'UNKNOWN';
            const side = order.side || 'unknown';
            const statusClass = order.state === 'filled' ? 'success' : '';
            const stateLabel = order.state || order.status || 'unknown';
            return `
                <div class="order-item ${statusClass}">
                    <strong>${symbol}</strong> - ${side} 
                    ${filledQty.toFixed(6)} @ ${formatCurrency(price)}
                    <br><small>${stateLabel} - ${new Date(order.created_at).toLocaleString()}</small>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load orders:', error);
    }
}

// Update risk limits
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
            showNotification(`Max drawdown updated to ${maxDrawdown}%`, 'success');
            loadRiskStatus();
        }
    } catch (error) {
        console.error('Failed to update risk settings:', error);
        showNotification('Failed to update risk settings', 'error');
    }
}


async function resetPeak() {
    try {
        const response = await fetch(`${API_BASE}/reset-peak`);
        const data = await response.json();
        
        if (data.success) {
            showNotification('Peak value reset', 'success');
            loadRiskStatus();
        }
    } catch (error) {
        console.error('Failed to reset peak:', error);
        showNotification('Failed to reset peak value', 'error');
    }
}

// ============ RECONCILIATION FUNCTIONS ============

// Save daily snapshot
async function saveSnapshot() {
    try {
        const response = await fetch(`${API_BASE}/snapshot`);
        const data = await response.json();
        
        if (data.success) {
            showNotification(`Snapshot saved successfully`, 'success');
        }
    } catch (error) {
        console.error('Failed to save snapshot:', error);
        showNotification('Failed to save snapshot', 'error');
    }
}

// Reconcile positions
async function reconcilePositions() {
    try {
        const response = await fetch(`${API_BASE}/reconcile`);
        const data = await response.json();
        
        displayReconciliationResult(data);
        if (data.reconciled) {
            showNotification('Reconciliation completed', 'success');
        } else {
            showNotification(data.message || 'Reconciliation completed with discrepancies', 'error');
        }
    } catch (error) {
        console.error('Failed to reconcile positions:', error);
        showNotification('Failed to reconcile positions', 'error');
    }
}


async function generateDailyReport() {
    try {
        const response = await fetch(`${API_BASE}/daily-report`);
        const data = await response.json();
        
        if (data.success) {
            showNotification('Daily report generated successfully', 'success');
        }
    } catch (error) {
        console.error('Failed to generate report:', error);
        showNotification('Failed to generate daily report', 'error');
    }
}


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
    
    // Severity button stuff below
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
    
    const canvas = document.getElementById('portfolioChart');
    if (!canvas) {
        console.error('Portfolio chart canvas not found');
        return;
    }

    if (!portfolioChart) {
        portfolioChart = new Chart(canvas, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Portfolio Value',
                    data: priceHistory,
                    borderColor: 'rgba(102, 126, 234, 0.82)',
                    backgroundColor: 'rgba(102, 126, 234, 0.18)',
                    pointRadius: 0,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.38,
                    cubicInterpolationMode: 'monotone'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 14,
                        bottom: 14,
                        left: 8,
                        right: 8
                    }
                },
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        type: 'linear',
                        display: false,
                        grid: {
                            drawBorder: false,
                            color: 'rgba(255, 255, 255, 0.06)'
                        },
                        ticks: {
                            color: 'rgba(15, 23, 42, 0.55)'
                        }
                    },
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(15, 23, 42, 0.08)',
                            borderDash: [4, 6]
                        },
                        ticks: {
                            color: 'rgba(15, 23, 42, 0.65)'
                        }
                    }
                }
            }
        });
    } else {
        portfolioChart.data.datasets[0].data = priceHistory;
        portfolioChart.update();
    }
}

// A couple helper functions
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