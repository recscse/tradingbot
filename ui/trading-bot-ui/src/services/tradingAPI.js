import apiClient from "./api";  // ✅ Use centralized API client

const tradingAPI = {
    // ============================================================================
    // ENHANCED TRADING API - Full Backend Integration
    // ============================================================================
    
    // Auto-Trading Session Management
    startTradingSession: async (sessionConfig = {}) => {
        const response = await apiClient.post("/v1/auto-trading/start-session", {
            mode: sessionConfig.mode || "PAPER_TRADING",
            selected_stocks: sessionConfig.selectedStocks || [],
            risk_parameters: sessionConfig.riskParameters || {
                max_risk_per_trade: 0.02,
                max_daily_loss: 50000
            },
            strategy_config: sessionConfig.strategyConfig || {
                min_signal_strength: 70
            },
            max_positions: sessionConfig.maxPositions || 5,
            max_daily_loss: sessionConfig.maxDailyLoss || 50000
        });
        return response.data;
    },

    stopTradingSession: async () => {
        const response = await apiClient.post("/v1/auto-trading/stop-session");
        return response.data;
    },

    getTradingSessionStatus: async (sessionId) => {
        const response = await apiClient.get(`/v1/auto-trading/session-status/${sessionId}`);
        return response.data;
    },

    // System Statistics & Status
    getSystemStats: async () => {
        const response = await apiClient.get("/v1/auto-trading/system-stats");
        return response.data;
    },

    getPerformanceMetrics: async (days = 30) => {
        const response = await apiClient.get(`/v1/auto-trading/performance-metrics?days=${days}`);
        return response.data;
    },

    getPerformanceSummary: async () => {
        const response = await apiClient.get("/v1/auto-trading/performance-summary");
        return response.data;
    },

    // Stock Selection & Analysis
    getSelectedStocks: async () => {
        const response = await apiClient.get("/v1/auto-trading/selected-stocks");
        return response.data;
    },

    runStockSelection: async (config = {}) => {
        const response = await apiClient.post("/v1/auto-trading/run-stock-selection", {
            force_selection: config.forceSelection || false,
            max_stocks: config.maxStocks || 2
        });
        return response.data;
    },

    // Position & Trade Management
    getActivePositions: async () => {
        const response = await apiClient.get("/v1/auto-trading/position-summary");
        return response.data;
    },

    getActiveTrades: async () => {
        const response = await apiClient.get("/v1/auto-trading/active-trades");
        return response.data;
    },

    getTradingHistory: async (days = 7) => {
        const response = await apiClient.get(`/v1/auto-trading/trading-history?days=${days}`);
        return response.data;
    },

    // Emergency Controls & Risk Management
    emergencyStop: async (reason = "Manual emergency stop") => {
        const response = await apiClient.post("/v1/auto-trading/emergency-stop", {
            reason,
            force_close_positions: true
        });
        return response.data;
    },

    pauseTrading: async () => {
        const response = await apiClient.post("/v1/auto-trading/pause-trading");
        return response.data;
    },

    resumeTrading: async () => {
        const response = await apiClient.post("/v1/auto-trading/resume-trading");
        return response.data;
    },

    // Strategy Management
    getFibonacciStrategyStatus: async () => {
        const response = await apiClient.get("/v1/fibonacci-strategy/status");
        return response.data;
    },

    updateFibonacciConfig: async (config) => {
        const response = await apiClient.post("/v1/fibonacci-strategy/config", config);
        return response.data;
    },

    getNiftyStrategyStatus: async () => {
        const response = await apiClient.get("/v1/nifty-strategy/status");
        return response.data;
    },

    updateNiftyStrategyConfig: async (config) => {
        const response = await apiClient.post("/v1/nifty-strategy/config", config);
        return response.data;
    },

    startNiftyStrategy: async () => {
        const response = await apiClient.post("/v1/nifty-strategy/start");
        return response.data;
    },

    stopNiftyStrategy: async () => {
        const response = await apiClient.post("/v1/nifty-strategy/stop");
        return response.data;
    },

    // Legacy Support (backward compatibility)
    startTrading: async (symbol) => {
        // Use the new session-based approach
        return await tradingAPI.startTradingSession({
            selectedStocks: symbol ? [{ symbol }] : []
        });
    },

    stopTrading: async () => {
        // Use the new session-based approach
        return await tradingAPI.stopTradingSession();
    },

    getStockAnalysis: async (symbol) => {
        const response = await apiClient.get(`/analysis/stock/${symbol}`);
        return response.data;
    },

    // Market Data Integration
    subscribeToMarketData: async (instruments = []) => {
        const response = await apiClient.post("/market-data/subscribe", {
            instruments
        });
        return response.data;
    },

    unsubscribeFromMarketData: async (instruments = []) => {
        const response = await apiClient.post("/market-data/unsubscribe", {
            instruments
        });
        return response.data;
    },

    // Option Chain & Contract Management
    getOptionChain: async (symbol, expiry = null) => {
        const params = expiry ? `?expiry=${expiry}` : '';
        const response = await apiClient.get(`/options/chain/${symbol}${params}`);
        return response.data;
    },

    getOptionContracts: async (symbol, strike, expiry, optionType) => {
        const response = await apiClient.get(`/options/contracts/${symbol}`, {
            params: { strike, expiry, option_type: optionType }
        });
        return response.data;
    },

    // Risk Management
    updateRiskSettings: async (settings) => {
        const response = await apiClient.post("/v1/auto-trading/risk-settings", settings);
        return response.data;
    },

    getRiskSettings: async () => {
        const response = await apiClient.get("/v1/auto-trading/risk-settings");
        return response.data;
    },

    // System Health & Monitoring
    getSystemHealth: async () => {
        const response = await apiClient.get("/health");
        return response.data;
    },

    // Utility Functions
    formatCurrency: (amount) => {
        if (!amount) return '₹0';
        if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
        if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
        return `₹${amount.toFixed(0)}`;
    },

    formatPercentage: (value) => {
        if (!value) return '0%';
        return `${value.toFixed(1)}%`;
    },

    calculatePnL: (entryPrice, currentPrice, quantity, optionType = 'CE') => {
        const priceDiff = optionType === 'CE' 
            ? currentPrice - entryPrice 
            : entryPrice - currentPrice;
        return priceDiff * quantity;
    },

    calculateRiskReward: (entryPrice, stopLoss, target) => {
        const risk = Math.abs(entryPrice - stopLoss);
        const reward = Math.abs(target - entryPrice);
        return risk > 0 ? reward / risk : 0;
    }
};

export default tradingAPI;
