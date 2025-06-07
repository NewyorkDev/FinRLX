// System X Advanced Trading Dashboard JavaScript
class TradingDashboard {
    constructor() {
        this.charts = {};
        this.updateInterval = 5000; // 5 seconds
        this.isConnected = true;
        this.activityLog = [];
        this.chartInitialized = false;
        this.updateIntervalId = null;
        this.isUpdating = false;
        this.portfolioUpdatePending = false; // Prevent portfolio chart spam
        this.strategyUpdatePending = false; // Prevent strategy chart spam
        this.lastStrategyUpdate = null; // Track last strategy chart update
        
        this.init();
    }

    async init() {
        // Initialize charts
        this.initCharts();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start real-time updates
        this.startRealTimeUpdates();
        
        // Hide loading overlay
        setTimeout(() => {
            document.getElementById('loading-overlay').classList.add('hidden');
        }, 2000);
    }

    initCharts() {
        if (this.chartInitialized) return;
        
        // Portfolio Performance Chart
        const portfolioCtx = document.getElementById('portfolio-chart');
        if (!portfolioCtx) return;
        
        this.charts.portfolio = new Chart(portfolioCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Portfolio Value',
                    data: [],
                    borderColor: '#2b8dc8',
                    backgroundColor: 'rgba(43, 141, 200, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Benchmark',
                    data: [],
                    borderColor: '#71a2dc',
                    backgroundColor: 'transparent',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0 // Disable animations to prevent scrolling issues
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#b0b8c7'
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        },
                        grid: {
                            color: '#1e4784'
                        },
                        ticks: {
                            color: '#b0b8c7'
                        }
                    },
                    y: {
                        grid: {
                            color: '#1e4784'
                        },
                        ticks: {
                            color: '#b0b8c7',
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0,
                        hoverRadius: 6
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });

        // Strategy Performance Chart - Initialize with static data to prevent updates
        const strategyCtx = document.getElementById('strategy-chart');
        if (!strategyCtx) return;
        
        this.charts.strategy = new Chart(strategyCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['V9B Pure', 'Technical Only', 'ML Enhanced'],
                datasets: [{
                    data: [1, 1, 1], // Start with equal data to prevent initial animations
                    backgroundColor: [
                        '#2b8dc8',
                        '#3b9cdc',
                        '#71a2dc'
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0 // Disable animations to prevent scrolling issues
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#b0b8c7',
                            padding: 20
                        }
                    }
                }
            }
        });
        
        this.chartInitialized = true;
    }

    setupEventListeners() {
        // Emergency stop button
        document.getElementById('emergency-stop').addEventListener('click', () => {
            this.emergencyStop();
        });

        // Time period buttons
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.updateChartPeriod(e.target.dataset.period);
            });
        });
    }

    async startRealTimeUpdates() {
        // Initial update
        await this.updateDashboard();
        
        // Set up interval - make sure we don't create multiple intervals
        if (this.updateIntervalId) {
            clearInterval(this.updateIntervalId);
        }
        
        this.updateIntervalId = setInterval(async () => {
            try {
                await this.updateDashboard();
            } catch (error) {
                console.error('Dashboard update error:', error);
            }
        }, this.updateInterval);
    }

    async updateDashboard() {
        if (this.isUpdating) return; // Prevent multiple simultaneous updates
        
        try {
            this.isUpdating = true;
            
            // Fetch all data in parallel
            const [healthData, metricsData, configData] = await Promise.all([
                this.fetchData('/health'),
                this.fetchData('/metrics'),
                this.fetchData('/config')
            ]);

            // Update UI components
            this.updateHeader(healthData);
            this.updateMetrics(metricsData);
            this.updateHealthStatus(healthData);
            this.updateRiskMetrics(metricsData);
            this.updateCharts(metricsData);
            this.updateTables();

            this.isConnected = true;
            this.updateConnectionStatus('OPERATIONAL', true);

        } catch (error) {
            console.error('Dashboard update error:', error);
            this.isConnected = false;
            this.updateConnectionStatus('CONNECTION ERROR', false);
        } finally {
            this.isUpdating = false;
        }
    }

    async fetchData(endpoint) {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }

    updateHeader(data) {
        // Update account balance
        document.getElementById('account-balance').textContent = 
            '$' + (data.account_balance || 0).toLocaleString();

        // Update market status
        const marketStatus = data.market_open ? 'OPEN' : 'CLOSED';
        document.getElementById('market-status').textContent = marketStatus;
        document.getElementById('market-status').className = 
            data.market_open ? 'status-open' : 'status-closed';
    }

    updateMetrics(data) {
        // Daily P&L
        const dailyPnl = data.performance?.daily_pnl || 0;
        const dailyPnlPct = data.performance?.daily_pnl_pct || 0;
        document.getElementById('daily-pnl').textContent = 
            (dailyPnl >= 0 ? '+$' : '-$') + Math.abs(dailyPnl).toLocaleString();
        
        const pnlElement = document.getElementById('daily-pnl-pct');
        pnlElement.textContent = (dailyPnlPct >= 0 ? '+' : '') + dailyPnlPct.toFixed(2) + '%';
        pnlElement.className = 'metric-change ' + (dailyPnlPct >= 0 ? 'positive' : 'negative');

        // Positions
        const positionsCount = data.trading?.positions || 0;
        const exposurePct = data.trading?.exposure || 0;
        document.getElementById('positions-count').textContent = positionsCount;
        document.getElementById('exposure-pct').textContent = exposurePct.toFixed(1) + '%';

        // Trades
        const tradesToday = data.trading?.trades_today || 0;
        const winRate = this.calculateWinRate(data.strategy_performance);
        document.getElementById('trades-today').textContent = tradesToday;
        document.getElementById('win-rate').textContent = winRate.toFixed(1) + '%';

        // ML Confidence
        const mlConfidence = data.ml_model?.confidence || 0;
        document.getElementById('ml-confidence').textContent = (mlConfidence * 100).toFixed(0) + '%';
        document.getElementById('model-status').textContent = 
            data.ml_model?.available ? 'Active' : 'Training';

        // Performance ratios
        const sharpe = data.performance?.sharpe_ratio || 0;
        const sortino = data.performance?.sortino_ratio || 0;
        document.getElementById('sharpe-ratio').textContent = sharpe.toFixed(2);
        document.getElementById('sortino-ratio').textContent = sortino.toFixed(2);
    }

    updateHealthStatus(data) {
        // Update connection statuses
        this.updateStatus('supabase-status', data.supabase_connected);
        this.updateStatus('alpaca-status', data.alpaca_connected);
        this.updateStatus('polygon-status', true); // Assume connected if no error
        this.updateStatus('ml-status', true);
        this.updateStatus('trading-status', true);

        // Update uptime
        const uptimeMinutes = data.uptime_minutes || 0;
        const uptimeHours = Math.floor(uptimeMinutes / 60);
        const remainingMinutes = Math.floor(uptimeMinutes % 60);
        
        let uptimeText;
        if (uptimeHours > 0) {
            uptimeText = `${uptimeHours}h ${remainingMinutes}m`;
        } else {
            uptimeText = `${remainingMinutes}m`;
        }
        document.getElementById('uptime').textContent = uptimeText;
    }

    updateStatus(elementId, isOnline) {
        const element = document.getElementById(elementId);
        element.textContent = isOnline ? 'Online' : 'Offline';
        element.className = 'health-status ' + (isOnline ? 'online' : 'offline');
    }

    updateRiskMetrics(data) {
        const var95 = data.performance?.var_95 || 0;
        const maxDrawdown = data.performance?.max_drawdown || 0;
        
        document.getElementById('var-95').textContent = '$' + Math.abs(var95).toLocaleString();
        document.getElementById('max-drawdown').textContent = (maxDrawdown * 100).toFixed(1) + '%';
        document.getElementById('kelly-position').textContent = '12%'; // Placeholder
        document.getElementById('stop-loss').textContent = '5%';
    }

    updateCharts(data) {
        // Update portfolio chart with sample data - prevent infinite scrolling
        if (this.charts.portfolio && this.chartInitialized) {
            const portfolioValue = data.account_balance || 30000;
            
            // Only update chart data on first load or when value actually changes
            const currentDataset = this.charts.portfolio.data.datasets[0];
            const lastValue = currentDataset.data[currentDataset.data.length - 1];
            
            // Only add new data if portfolio value changed by more than $10 or chart is empty
            if (currentDataset.data.length === 0 || Math.abs(portfolioValue - lastValue) > 10) {
                // Prevent duplicate chart updates
                if (!this.portfolioUpdatePending) {
                    this.portfolioUpdatePending = true;
                    
                    try {
                        const now = new Date();
                        this.charts.portfolio.data.labels.push(now.toLocaleTimeString());
                        this.charts.portfolio.data.datasets[0].data.push(portfolioValue);
                        
                        // Add benchmark data (slightly lower)
                        this.charts.portfolio.data.datasets[1].data.push(portfolioValue * 0.98);
                        
                        // Keep last 20 points only (reasonable chart length)
                        if (this.charts.portfolio.data.labels.length > 20) {
                            this.charts.portfolio.data.labels.shift();
                            this.charts.portfolio.data.datasets[0].data.shift();
                            this.charts.portfolio.data.datasets[1].data.shift();
                        }
                        
                        // Use silent update to prevent reflow issues
                        this.charts.portfolio.update('none');
                    } catch (error) {
                        console.error('Portfolio chart update error:', error);
                    } finally {
                        // Reset flag after a short delay
                        setTimeout(() => {
                            this.portfolioUpdatePending = false;
                        }, 2000);
                    }
                }
            }
        }

        // Update strategy chart - prevent infinite updates
        if (this.charts.strategy && this.chartInitialized) {
            // Only update strategy chart every 30 minutes to prevent scrolling issues
            const now = Date.now();
            if (!this.lastStrategyUpdate || (now - this.lastStrategyUpdate) > 1800000) { // 30 minutes
                
                if (!this.strategyUpdatePending) {
                    this.strategyUpdatePending = true;
                    
                    try {
                        const strategyData = data.strategy_performance || {};
                        const v9bTrades = strategyData.V9B_PURE?.trades || 1;
                        const techTrades = strategyData.TECHNICAL_ONLY?.trades || 1;
                        const mlTrades = strategyData.ML_ENHANCED?.trades || 1;
                        
                        // Only update if data has actually changed
                        const currentData = this.charts.strategy.data.datasets[0].data;
                        const newData = [v9bTrades, techTrades, mlTrades];
                        
                        if (JSON.stringify(currentData) !== JSON.stringify(newData)) {
                            this.charts.strategy.data.datasets[0].data = newData;
                            this.charts.strategy.update('none');
                            this.lastStrategyUpdate = now;
                        }
                    } catch (error) {
                        console.error('Strategy chart update error:', error);
                    } finally {
                        setTimeout(() => {
                            this.strategyUpdatePending = false;
                        }, 2000);
                    }
                }
            }
        }
    }

    async updateTables() {
        // Update positions table (placeholder data)
        const positionsTable = document.getElementById('positions-tbody');
        if (positionsTable) {
            positionsTable.innerHTML = '<tr><td colspan="6" class="no-data">No open positions</td></tr>';
        }

        // Update qualified stocks table
        try {
            const response = await fetch('/qualified-stocks');
            const stocks = await response.json();
            
            const qualifiedTable = document.getElementById('qualified-tbody');
            const qualifiedCount = document.getElementById('qualified-count');
            
            if (qualifiedTable) {
                if (stocks.length === 0) {
                    qualifiedTable.innerHTML = '<tr><td colspan="5" class="no-data">No qualified stocks</td></tr>';
                } else {
                    qualifiedTable.innerHTML = stocks.slice(0, 5).map(stock => `
                        <tr>
                            <td><strong>${stock.ticker || stock.symbol || 'N/A'}</strong></td>
                            <td>${stock.dts_score || 'N/A'}</td>
                            <td>${(stock.v9b_confidence * 10).toFixed(1) || 'N/A'}</td>
                            <td><span class="signal signal-hold">HOLD</span></td>
                            <td><button class="action-btn">Analyze</button></td>
                        </tr>
                    `).join('');
                }
            }
            
            if (qualifiedCount) {
                qualifiedCount.textContent = `${stocks.length} stocks`;
            }
        } catch (error) {
            console.error('Error fetching qualified stocks:', error);
        }
    }

    updateConnectionStatus(status, isOnline) {
        document.getElementById('connection-text').textContent = status;
        const statusDot = document.getElementById('connection-status');
        statusDot.className = 'status-dot ' + (isOnline ? 'online' : 'offline');
    }

    calculateWinRate(strategyData) {
        if (!strategyData) return 0;
        
        let totalTrades = 0;
        let totalWins = 0;
        
        Object.values(strategyData).forEach(strategy => {
            totalTrades += strategy.trades || 0;
            totalWins += strategy.wins || 0;
        });
        
        return totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0;
    }

    getSignalClass(signal) {
        switch (signal) {
            case 'BUY': return 'signal-buy';
            case 'SELL': return 'signal-sell';
            default: return 'signal-hold';
        }
    }

    updateChartPeriod(period) {
        // Implement chart period update logic
        console.log('Updating chart period to:', period);
        // This would fetch new data based on the selected period
    }

    async emergencyStop() {
        if (confirm('Are you sure you want to trigger an emergency stop? This will halt all trading immediately.')) {
            try {
                const response = await fetch('/emergency-stop', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        reason: 'MANUAL_DASHBOARD_STOP'
                    })
                });
                
                if (response.ok) {
                    this.addActivity('Emergency stop activated');
                    alert('Emergency stop activated successfully');
                } else {
                    alert('Failed to activate emergency stop');
                }
            } catch (error) {
                console.error('Emergency stop error:', error);
                alert('Error activating emergency stop');
            }
        }
    }

    addActivity(message) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
        
        const activityLog = document.getElementById('activity-log');
        if (!activityLog) return;
        
        // Check if this message already exists (prevent duplicates)
        const existingItems = activityLog.querySelectorAll('.activity-text');
        for (let item of existingItems) {
            if (item.textContent === message) {
                return; // Don't add duplicate
            }
        }
        
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.innerHTML = `
            <span class="activity-time">${timeStr}</span>
            <span class="activity-text">${message}</span>
        `;
        
        activityLog.insertBefore(activityItem, activityLog.firstChild);
        
        // Keep only last 10 items
        while (activityLog.children.length > 10) {
            activityLog.removeChild(activityLog.lastChild);
        }
    }
}

// Custom CSS for additional styling
const additionalStyles = `
    .signal-buy { color: #10b981; font-weight: 600; }
    .signal-sell { color: #ef4444; font-weight: 600; }
    .signal-hold { color: #6b7280; font-weight: 600; }
    
    .action-btn {
        background: var(--accent-blue);
        color: white;
        border: none;
        padding: 0.25rem 0.75rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .action-btn:hover {
        background: var(--accent-blue-light);
        transform: translateY(-1px);
    }
    
    .status-open { color: var(--accent-green); }
    .status-closed { color: var(--accent-yellow); }
`;

// Inject additional styles
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TradingDashboard();
});