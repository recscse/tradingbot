import React, { useState, useEffect, useRef, useCallback } from "react";
import api from "../services/api";

const AutoTradingPage = () => {
  const [tradingMode, setTradingMode] = useState("paper");
  const [executionMode, setExecutionMode] = useState("multi_demat");
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [activePositions, setActivePositions] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [pnlSummary, setPnlSummary] = useState({
    total_pnl: 0,
    total_investment: 0,
    pnl_percent: 0,
    active_positions_count: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [stocksLoading, setStocksLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [emergencyStopLoading, setEmergencyStopLoading] = useState(false);
  const [autoTradingRunning, setAutoTradingRunning] = useState(false);
  const [realtimeStats, setRealtimeStats] = useState({
    signals_today: 0,
    trades_today: 0,
    active_stocks: 0
  });
  const socketRef = useRef(null);
  const [capitalData, setCapitalData] = useState({
    total_available_capital: 0,
    total_used_margin: 0,
    total_free_margin: 0,
    capital_utilization_percent: 0,
    max_trade_allocation: 0,
    demats: [],
    total_demats: 0,
    active_demats: 0,
    trading_mode: "paper",
  });

  const fetchActivePositions = useCallback(async () => {
    try {
      const response = await api.get("/v1/trading/execution/active-positions");
      if (response.data.success) {
        setActivePositions(response.data.active_positions || []);
      }
    } catch (err) {
      console.error("Error fetching active positions:", err);
      setActivePositions([]);
    }
  }, []);

  const fetchPortfolioSummary = useCallback(async () => {
    try {
      const response = await api.get("/v1/trading/execution/pnl-summary");
      if (response.data.success) {
        setPnlSummary(response.data.summary);
      }
    } catch (err) {
      console.error("Error fetching PnL summary:", err);
    }
  }, []);

  const fetchTradeHistory = useCallback(async () => {
    try {
      const response = await api.get("/v1/trading/execution/trade-history?limit=50");
      if (response.data.success) {
        setTradeHistory(response.data.trades || []);
      }
    } catch (err) {
      console.error("Error fetching trade history:", err);
    }
  }, []);

  const fetchTradingPreferences = useCallback(async () => {
    try {
      const response = await api.get("/v1/trading/execution/user-trading-preferences");
      if (response.data.success) {
        setTradingMode(response.data.trading_mode || "paper");
        setExecutionMode(response.data.execution_mode || "multi_demat");
      }
    } catch (err) {
      console.error("Error fetching trading preferences:", err);
    }
  }, []);

  const fetchCapitalOverview = useCallback(async () => {
    try {
      const response = await api.get(`/v1/trading/execution/user-capital-overview?trading_mode=${tradingMode}`);
      if (response.data.success) {
        setCapitalData(response.data.capital_overview);
      }
    } catch (err) {
      console.error("Error fetching capital overview:", err);
    }
  }, [tradingMode]);

  const fetchSelectedStocks = useCallback(async () => {
    setStocksLoading(true);
    try {
      const response = await api.get("/v1/trading/execution/selected-stocks");
      const payload = response?.data;
      if (!payload || !payload.success) {
        setSelectedStocks([]);
        return;
      }
      const stocks = payload.stocks || [];
      const cleanedStocks = stocks.map((stock) => ({
        ...stock,
        strike_price: stock.strike_price || 0,
        lot_size: stock.lot_size || 0,
        premium: stock.premium || 0,
        capital_allocation: stock.capital_allocation || 0,
        position_size_lots: stock.position_size_lots || 0,
        max_loss: stock.max_loss || 0,
        target_profit: stock.target_profit || 0,
        selection_score: stock.selection_score || 0,
        price_at_selection: stock.price_at_selection || 0,
        symbol: stock.symbol || "",
        option_type: stock.option_type || "N/A",
        expiry_date: stock.expiry_date || "",
        option_instrument_key: stock.option_instrument_key || "",
        sector: stock.sector || "OTHER",
      }));
      setSelectedStocks(cleanedStocks);
    } catch (err) {
      console.error("Error fetching selected stocks:", err);
      setSelectedStocks([]);
    } finally {
      setStocksLoading(false);
    }
  }, []);

  const handleClosePosition = useCallback(async (positionId) => {
    if (!window.confirm("Are you sure you want to close this position?")) {
      return;
    }
    try {
      const response = await api.post(`/v1/trading/execution/close-position/${positionId}`);
      if (response.data.success) {
        setSuccess(`Position closed. PnL: ₹${response.data.pnl.toFixed(2)}`);
        await fetchActivePositions();
        await fetchPortfolioSummary();
        await fetchTradeHistory();
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to close position");
    }
  }, [fetchActivePositions, fetchPortfolioSummary, fetchTradeHistory]);

  const handleEmergencyStopAll = useCallback(async () => {
    if (!window.confirm("EMERGENCY STOP ALL POSITIONS\n\nThis will immediately close ALL active positions at market price.\n\nAre you absolutely sure you want to continue?")) {
      return;
    }
    setEmergencyStopLoading(true);
    setError(null);
    try {
      const closePromises = activePositions.map((position) =>
        api.post(`/v1/trading/execution/close-position/${position.position_id}`)
      );
      const results = await Promise.allSettled(closePromises);
      const successCount = results.filter((r) => r.status === "fulfilled").length;
      const failCount = results.filter((r) => r.status === "rejected").length;
      setSuccess(`Emergency Stop Complete: ${successCount} positions closed${failCount > 0 ? `, ${failCount} failed` : ""}`);
      await fetchActivePositions();
      await fetchPortfolioSummary();
      await fetchTradeHistory();
    } catch (err) {
      setError("Emergency stop failed. Please try closing positions individually.");
    } finally {
      setEmergencyStopLoading(false);
    }
  }, [activePositions, fetchActivePositions, fetchPortfolioSummary, fetchTradeHistory]);

  const handleTradingModeToggle = useCallback(async () => {
    const newMode = tradingMode === "paper" ? "live" : "paper";
    if (newMode === "live") {
      if (!window.confirm("⚠️ SWITCHING TO LIVE TRADING\n\nThis will use REAL MONEY from your broker account.\n\nAre you sure you want to continue?")) {
        return;
      }
    }
    try {
      const response = await api.post(`/v1/trading/execution/user-trading-preferences?trading_mode=${newMode}&execution_mode=${executionMode}`);
      if (response.data.success) {
        setTradingMode(newMode);
        await fetchPortfolioSummary();
      }
    } catch (err) {
      console.error("Error updating trading mode:", err);
      setError("Failed to update trading mode");
    }
  }, [tradingMode, executionMode, fetchPortfolioSummary]);

  const initializeWebSocket = useCallback(() => {
    try {
      const baseUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";
      const wsUrl = baseUrl.replace("http://", "ws://").replace("https://", "wss://") + "/ws/unified";
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: "client_info",
          client_type: "trading_execution",
          timestamp: new Date().toISOString(),
        }));
        ws.send(JSON.stringify({
          type: "subscribe",
          events: ["all"],
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "pnl_update") {
            const data = message.data;
            setActivePositions((prev) =>
              prev.map((pos) =>
                pos.position_id === data.position_id
                  ? {
                      ...pos,
                      current_price: data.current_price,
                      current_pnl: data.pnl,
                      current_pnl_percentage: data.pnl_percent,
                      stop_loss: data.stop_loss,
                      trailing_stop_active: data.trailing_sl_active,
                      last_updated: data.last_updated,
                    }
                  : pos
              )
            );
            fetchPortfolioSummary();
          }
          if (message.type === "trading_signal") {
            setRealtimeStats(prev => ({
              ...prev,
              signals_today: prev.signals_today + 1
            }));
          }
          if (message.type === "trade_executed") {
            const tradeData = message.data;
            setSuccess(`Trade executed: ${tradeData.symbol} @ ₹${tradeData.entry_price.toFixed(2)}`);
            setRealtimeStats(prev => ({
              ...prev,
              trades_today: prev.trades_today + 1
            }));
            fetchActivePositions();
            fetchPortfolioSummary();
            fetchSelectedStocks();
          }
          if (message.type === "active_position_created") {
            const posData = message.data;
            setActivePositions((prev) => {
              const existingIndex = prev.findIndex((p) => p.position_id === posData.position_id);
              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = { ...updated[existingIndex], ...posData };
                return updated;
              } else {
                return [{
                  position_id: posData.position_id,
                  trade_id: posData.trade_id,
                  symbol: posData.symbol,
                  instrument_key: posData.instrument_key,
                  option_type: posData.option_type,
                  strike_price: posData.strike_price,
                  entry_price: posData.entry_price,
                  current_price: posData.current_price || posData.entry_price,
                  stop_loss: posData.stop_loss,
                  target: posData.target,
                  quantity: posData.quantity,
                  current_pnl: posData.current_pnl || 0,
                  current_pnl_percentage: posData.current_pnl_percentage || 0,
                  broker_name: posData.broker_name,
                  trading_mode: posData.trading_mode,
                  entry_time: posData.timestamp,
                  last_updated: posData.timestamp,
                  trailing_stop_active: false,
                }, ...prev];
              }
            });
            fetchPortfolioSummary();
            fetchSelectedStocks();
          }
          if (message.type === "trade_error") {
            setError(`Trade error for ${message.data.symbol}: ${message.data.error}`);
          }
          if (message.type === "position_closed") {
            const posData = message.data;
            setSuccess(`Position closed: ${posData.symbol} - PnL: ₹${posData.pnl.toFixed(2)}`);
            fetchActivePositions();
            fetchPortfolioSummary();
            fetchTradeHistory();
          }
          if (message.type === "selected_stock_price_update") {
            const data = message.data;
            setSelectedStocks((prev) =>
              prev.map((stock) =>
                stock.option_instrument_key === data.option_instrument_key || stock.symbol === data.symbol
                  ? {
                      ...stock,
                      live_price: data.live_option_premium,
                      live_spot_price: data.live_spot_price,
                      price_change: data.price_change,
                      price_change_percent: data.price_change_percent,
                      unrealized_pnl: data.unrealized_pnl,
                      unrealized_pnl_percent: data.unrealized_pnl_percent,
                      state: data.state,
                      last_updated: data.timestamp,
                    }
                  : stock
              )
            );
          }
        } catch (parseError) {
          console.error("Error parsing WebSocket message:", parseError);
        }
      };

      ws.onclose = (event) => {
        setTimeout(() => {
          if (socketRef.current === ws) {
            initializeWebSocket();
          }
        }, 5000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      socketRef.current = ws;
    } catch (err) {
      console.error("WebSocket connection error:", err);
    }
  }, [fetchActivePositions, fetchPortfolioSummary, fetchSelectedStocks, fetchTradeHistory]);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        await Promise.allSettled([
          fetchTradingPreferences(),
          fetchSelectedStocks(),
          fetchPortfolioSummary(),
          fetchActivePositions(),
          fetchCapitalOverview(),
          fetchTradeHistory(),
        ]);
      } catch (err) {
        console.error("Error loading initial data:", err);
      } finally {
        setIsLoading(false);
      }
      initializeWebSocket();
    };
    loadInitialData();
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        fetchPortfolioSummary();
        fetchActivePositions();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchPortfolioSummary, fetchActivePositions]);

  useEffect(() => {
    const checkAutoTradingStatus = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const response = await api.get("/v1/trading/execution/auto-trading-status");
        if (response.data.success) {
          setAutoTradingRunning(response.data.websocket_running || false);
        }
      } catch (err) {
        console.error("Failed to get auto-trading status:", err);
      }
    };
    checkAutoTradingStatus();
    const interval = setInterval(checkAutoTradingStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setRealtimeStats(prev => ({
      ...prev,
      active_stocks: selectedStocks.length
    }));
  }, [selectedStocks]);

  const formatCurrency = useCallback((amount) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
    }).format(amount || 0);
  }, []);

  const formatPercentage = useCallback((value = 0) => {
    const num = Number.isFinite(value) ? value : 0;
    return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
  }, []);

  const getPnlColor = useCallback((value) => {
    if (value > 0) return 'tw-text-emerald-300';
    if (value < 0) return 'tw-text-rose-300';
    return 'tw-text-slate-300';
  }, []);

  const getPnlBgColor = useCallback((value) => {
    if (value > 0) return 'tw-bg-emerald-500/10 tw-border-emerald-500/30';
    if (value < 0) return 'tw-bg-rose-500/10 tw-border-rose-500/30';
    return 'tw-bg-slate-500/10 tw-border-slate-500/30';
  }, []);

  if (isLoading) {
    return (
      <div className="tw-min-h-screen tw-bg-gradient-to-br tw-from-slate-950 tw-via-slate-900 tw-to-slate-950 tw-flex tw-items-center tw-justify-center">
        <div className="tw-text-center tw-space-y-4">
          <div className="tw-relative tw-w-20 tw-h-20 tw-mx-auto">
            <div className="tw-absolute tw-inset-0 tw-border-4 tw-border-slate-700/30 tw-rounded-full"></div>
            <div className="tw-absolute tw-inset-0 tw-border-4 tw-border-cyan-500 tw-rounded-full tw-border-t-transparent tw-animate-spin"></div>
          </div>
          <div>
            <p className="tw-text-slate-300 tw-text-lg tw-font-semibold">Loading Trading Dashboard</p>
            <p className="tw-text-slate-500 tw-text-sm">Initializing systems...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="tw-min-h-screen tw-bg-gradient-to-br tw-from-slate-950 tw-via-slate-900 tw-to-slate-950 tw-p-4 md:tw-p-6 lg:tw-p-8">
      {/* Sticky Header with Emergency Controls */}
      <div className="tw-sticky tw-top-0 tw-z-50 tw-bg-slate-900/95 tw-backdrop-blur-xl tw-border-b tw-border-slate-700/50 tw-mb-6 tw-p-4 tw-rounded-2xl tw-shadow-2xl">
        <div className="tw-flex tw-flex-col lg:tw-flex-row lg:tw-items-center lg:tw-justify-between tw-gap-4">
          {/* Left: Title & Mode */}
          <div>
            <h1 className="tw-text-2xl tw-font-bold tw-text-white tw-mb-2">Automated Trading</h1>
            <div className="tw-flex tw-items-center tw-gap-3">
              <span className={`tw-px-3 tw-py-1 tw-rounded-full tw-text-xs tw-font-bold tw-uppercase ${tradingMode === "paper" ? 'tw-bg-cyan-500/20 tw-text-cyan-300 tw-border tw-border-cyan-500/30' : 'tw-bg-rose-500/20 tw-text-rose-300 tw-border tw-border-rose-500/30'}`}>
                {tradingMode === "paper" ? "PAPER" : "LIVE"}
              </span>
              <span className="tw-text-slate-400 tw-text-sm">
                {activePositions.length} Active Position{activePositions.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>

          {/* Center: Quick P&L */}
          <div className="tw-text-center lg:tw-px-6">
            <p className="tw-text-slate-400 tw-text-xs tw-uppercase tw-tracking-wider tw-mb-1">Total P&L</p>
            <p className={`tw-text-3xl tw-font-bold ${getPnlColor(pnlSummary.total_pnl)}`}>
              {formatCurrency(pnlSummary.total_pnl)}
            </p>
            <p className={`tw-text-sm ${getPnlColor(pnlSummary.pnl_percent)}`}>
              {formatPercentage(pnlSummary.pnl_percent)}
            </p>
          </div>

          {/* Right: Emergency Stop */}
          <button
            onClick={handleEmergencyStopAll}
            disabled={emergencyStopLoading || activePositions.length === 0}
            className="tw-px-6 tw-py-3 tw-bg-rose-600 hover:tw-bg-rose-700 tw-text-white tw-rounded-xl tw-font-semibold tw-transition-all tw-duration-200 tw-shadow-lg hover:tw-shadow-xl disabled:tw-opacity-50 disabled:tw-cursor-not-allowed tw-flex tw-items-center tw-justify-center tw-gap-2"
          >
            <svg className="tw-w-5 tw-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            {emergencyStopLoading ? "STOPPING..." : "EMERGENCY STOP"}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="tw-mb-6 tw-p-4 tw-bg-rose-500/10 tw-border tw-border-rose-500/30 tw-rounded-xl tw-flex tw-items-start tw-gap-3">
          <svg className="tw-w-5 tw-h-5 tw-text-rose-400 tw-flex-shrink-0 tw-mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div className="tw-flex-1">
            <p className="tw-text-rose-300 tw-font-medium">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="tw-text-rose-400 hover:tw-text-rose-300">
            <svg className="tw-w-5 tw-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      )}
      {success && (
        <div className="tw-mb-6 tw-p-4 tw-bg-emerald-500/10 tw-border tw-border-emerald-500/30 tw-rounded-xl tw-flex tw-items-start tw-gap-3">
          <svg className="tw-w-5 tw-h-5 tw-text-emerald-400 tw-flex-shrink-0 tw-mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div className="tw-flex-1">
            <p className="tw-text-emerald-300 tw-font-medium">{success}</p>
          </div>
          <button onClick={() => setSuccess(null)} className="tw-text-emerald-400 hover:tw-text-emerald-300">
            <svg className="tw-w-5 tw-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      )}

      {/* Portfolio Summary */}
      <div className="tw-mb-6 tw-bg-slate-900/50 tw-backdrop-blur-xl tw-border tw-border-slate-700/50 tw-rounded-2xl tw-p-6 tw-shadow-2xl">
        <h2 className="tw-text-xl tw-font-bold tw-text-white tw-mb-6">Portfolio Summary</h2>
        <div className="tw-grid tw-grid-cols-1 sm:tw-grid-cols-2 lg:tw-grid-cols-4 tw-gap-4">
          <div className={`tw-p-5 tw-rounded-xl tw-border ${getPnlBgColor(pnlSummary.total_pnl)}`}>
            <p className="tw-text-slate-400 tw-text-sm tw-mb-2">Total P&L</p>
            <p className={`tw-text-3xl tw-font-bold ${getPnlColor(pnlSummary.total_pnl)}`}>
              {formatCurrency(pnlSummary.total_pnl)}
            </p>
            <p className={`tw-text-sm tw-mt-1 ${getPnlColor(pnlSummary.pnl_percent)}`}>
              {formatPercentage(pnlSummary.pnl_percent)}
            </p>
          </div>
          <div className="tw-p-5 tw-bg-slate-800/50 tw-rounded-xl tw-border tw-border-slate-700/50">
            <p className="tw-text-slate-400 tw-text-sm tw-mb-2">Active Positions</p>
            <p className="tw-text-3xl tw-font-bold tw-text-white">{pnlSummary.active_positions_count}</p>
          </div>
          <div className="tw-p-5 tw-bg-slate-800/50 tw-rounded-xl tw-border tw-border-slate-700/50">
            <p className="tw-text-slate-400 tw-text-sm tw-mb-2">Total Investment</p>
            <p className="tw-text-3xl tw-font-bold tw-text-white">{formatCurrency(pnlSummary.total_investment)}</p>
          </div>
          <div className="tw-p-5 tw-bg-slate-800/50 tw-rounded-xl tw-border tw-border-slate-700/50">
            <p className="tw-text-slate-400 tw-text-sm tw-mb-2">Available Capital</p>
            <p className="tw-text-3xl tw-font-bold tw-text-cyan-400">{formatCurrency(capitalData.total_free_margin)}</p>
          </div>
        </div>
      </div>

      {/* Real-time Activity Stats - NEW DESIGN */}
      <div className="tw-mb-6 tw-bg-gradient-to-br tw-from-slate-900/50 tw-to-slate-800/50 tw-backdrop-blur-xl tw-border tw-border-slate-700/50 tw-rounded-2xl tw-p-6 tw-shadow-2xl">
        <div className="tw-flex tw-items-center tw-justify-between tw-mb-6">
          <h2 className="tw-text-xl tw-font-bold tw-text-white tw-flex tw-items-center tw-gap-3">
            <span className="tw-relative tw-flex tw-h-3 tw-w-3">
              <span className={`tw-animate-ping tw-absolute tw-inline-flex tw-h-full tw-w-full tw-rounded-full ${autoTradingRunning ? 'tw-bg-emerald-400' : 'tw-bg-slate-400'} tw-opacity-75`}></span>
              <span className={`tw-relative tw-inline-flex tw-rounded-full tw-h-3 tw-w-3 ${autoTradingRunning ? 'tw-bg-emerald-500' : 'tw-bg-slate-500'}`}></span>
            </span>
            Real-Time Activity
          </h2>
          <span className={`tw-px-3 tw-py-1 tw-rounded-full tw-text-xs tw-font-bold ${autoTradingRunning ? 'tw-bg-emerald-500/20 tw-text-emerald-300 tw-border tw-border-emerald-500/30' : 'tw-bg-slate-500/20 tw-text-slate-400 tw-border tw-border-slate-500/30'}`}>
            {autoTradingRunning ? 'MONITORING' : 'IDLE'}
          </span>
        </div>
        <div className="tw-grid tw-grid-cols-1 sm:tw-grid-cols-3 tw-gap-4">
          <div className="tw-p-5 tw-bg-cyan-500/10 tw-rounded-xl tw-border tw-border-cyan-500/30">
            <div className="tw-flex tw-items-center tw-justify-between tw-mb-2">
              <p className="tw-text-cyan-300 tw-text-sm tw-font-medium">Signals Today</p>
              <svg className="tw-w-5 tw-h-5 tw-text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
              </svg>
            </div>
            <p className="tw-text-3xl tw-font-bold tw-text-cyan-400">{realtimeStats.signals_today}</p>
          </div>
          <div className="tw-p-5 tw-bg-emerald-500/10 tw-rounded-xl tw-border tw-border-emerald-500/30">
            <div className="tw-flex tw-items-center tw-justify-between tw-mb-2">
              <p className="tw-text-emerald-300 tw-text-sm tw-font-medium">Trades Executed</p>
              <svg className="tw-w-5 tw-h-5 tw-text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <p className="tw-text-3xl tw-font-bold tw-text-emerald-400">{realtimeStats.trades_today}</p>
          </div>
          <div className="tw-p-5 tw-bg-amber-500/10 tw-rounded-xl tw-border tw-border-amber-500/30">
            <div className="tw-flex tw-items-center tw-justify-between tw-mb-2">
              <p className="tw-text-amber-300 tw-text-sm tw-font-medium">Active Stocks</p>
              <svg className="tw-w-5 tw-h-5 tw-text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"/>
              </svg>
            </div>
            <p className="tw-text-3xl tw-font-bold tw-text-amber-400">{realtimeStats.active_stocks}</p>
          </div>
        </div>
        {autoTradingRunning && (
          <div className="tw-mt-4 tw-p-4 tw-bg-slate-800/30 tw-rounded-xl tw-border tw-border-slate-700/30">
            <p className="tw-text-sm tw-text-slate-300">
              <span className="tw-font-semibold tw-text-emerald-400">Strategy Active:</span> Monitoring {selectedStocks.length} stocks • Real-time signal processing • Auto-execution enabled
            </p>
          </div>
        )}
      </div>

      {/* Trading Settings */}
      <div className="tw-mb-6 tw-bg-slate-900/50 tw-backdrop-blur-xl tw-border tw-border-slate-700/50 tw-rounded-2xl tw-p-6 tw-shadow-2xl">
        <h2 className="tw-text-xl tw-font-bold tw-text-white tw-mb-6">Trading Settings</h2>
        <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 tw-gap-6">
          <div className={`tw-p-5 tw-rounded-xl tw-border ${tradingMode === "live" ? 'tw-border-rose-500/50 tw-bg-rose-500/5' : 'tw-border-slate-700/50 tw-bg-slate-800/30'}`}>
            <p className="tw-text-slate-400 tw-text-sm tw-mb-3">Trading Mode</p>
            <label className="tw-flex tw-items-center tw-gap-3 tw-cursor-pointer">
              <div className="tw-relative">
                <input
                  type="checkbox"
                  checked={tradingMode === "live"}
                  onChange={handleTradingModeToggle}
                  className="tw-sr-only tw-peer"
                />
                <div className="tw-w-14 tw-h-7 tw-bg-slate-700 tw-peer-focus:tw-outline-none tw-rounded-full tw-peer tw-peer-checked:after:tw-translate-x-full peer-checked:after:tw-border-white after:tw-content-[''] after:tw-absolute after:tw-top-0.5 after:tw-left-[4px] after:tw-bg-white after:tw-border-slate-300 after:tw-border after:tw-rounded-full after:tw-h-6 after:tw-w-6 after:tw-transition-all tw-peer-checked:tw-bg-rose-600"></div>
              </div>
              <div>
                <p className="tw-text-white tw-font-medium">{tradingMode === "paper" ? "Paper Trading" : "Live Trading"}</p>
                <p className="tw-text-xs tw-text-slate-400">
                  {tradingMode === "paper" ? "Virtual ₹10 lakhs - No real money" : "⚠️ Real money trading - Actual broker API"}
                </p>
              </div>
            </label>
          </div>
          <div className="tw-p-5 tw-bg-slate-800/30 tw-rounded-xl tw-border tw-border-slate-700/50">
            <p className="tw-text-slate-400 tw-text-sm tw-mb-3">Execution Mode</p>
            <label className="tw-flex tw-items-center tw-gap-3 tw-cursor-pointer">
              <div className="tw-relative">
                <input
                  type="checkbox"
                  checked={executionMode === "multi_demat"}
                  onChange={async (e) => {
                    const newMode = e.target.checked ? "multi_demat" : "single_demat";
                    try {
                      const response = await api.post(`/v1/trading/execution/user-trading-preferences?trading_mode=${tradingMode}&execution_mode=${newMode}`);
                      if (response.data.success) {
                        setExecutionMode(newMode);
                      }
                    } catch (err) {
                      console.error("Error updating execution mode:", err);
                    }
                  }}
                  className="tw-sr-only tw-peer"
                />
                <div className="tw-w-14 tw-h-7 tw-bg-slate-700 tw-peer-focus:tw-outline-none tw-rounded-full tw-peer tw-peer-checked:after:tw-translate-x-full peer-checked:after:tw-border-white after:tw-content-[''] after:tw-absolute after:tw-top-0.5 after:tw-left-[4px] after:tw-bg-white after:tw-border-slate-300 after:tw-border after:tw-rounded-full after:tw-h-6 after:tw-w-6 after:tw-transition-all tw-peer-checked:tw-bg-cyan-600"></div>
              </div>
              <div>
                <p className="tw-text-white tw-font-medium">{executionMode === "multi_demat" ? "Multi-Demat" : "Single-Demat"}</p>
                <p className="tw-text-xs tw-text-slate-400">
                  {executionMode === "multi_demat" ? "Distribute across all active demats" : "Execute on default demat only"}
                </p>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Capital Overview */}
      <div className="tw-mb-6 tw-bg-slate-900/50 tw-backdrop-blur-xl tw-border tw-border-slate-700/50 tw-rounded-2xl tw-p-6 tw-shadow-2xl">
        <div className="tw-flex tw-items-center tw-justify-between tw-mb-6">
          <h2 className="tw-text-xl tw-font-bold tw-text-white">Capital Overview</h2>
          <span className="tw-px-3 tw-py-1 tw-rounded-full tw-text-xs tw-font-bold tw-bg-cyan-500/20 tw-text-cyan-300 tw-border tw-border-cyan-500/30">
            {capitalData.active_demats || 0} Active Demat{(capitalData.active_demats || 0) !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="tw-grid tw-grid-cols-1 sm:tw-grid-cols-2 lg:tw-grid-cols-4 tw-gap-4">
          <div className="tw-p-5 tw-bg-slate-800/50 tw-rounded-xl tw-border tw-border-slate-700/50">
            <p className="tw-text-slate-400 tw-text-sm tw-mb-2">Total Capital</p>
            <p className="tw-text-3xl tw-font-bold tw-text-white">{formatCurrency(capitalData.total_available_capital || 0)}</p>
          </div>
          <div className="tw-p-5 tw-bg-rose-500/10 tw-rounded-xl tw-border tw-border-rose-500/30">
            <p className="tw-text-rose-300 tw-text-sm tw-mb-2">Used Margin</p>
            <p className="tw-text-3xl tw-font-bold tw-text-rose-400">{formatCurrency(capitalData.total_used_margin || 0)}</p>
            <p className="tw-text-xs tw-text-slate-400 tw-mt-1">{capitalData.capital_utilization_percent?.toFixed(1) || 0}% utilized</p>
          </div>
          <div className="tw-p-5 tw-bg-emerald-500/10 tw-rounded-xl tw-border tw-border-emerald-500/30">
            <p className="tw-text-emerald-300 tw-text-sm tw-mb-2">Free Margin</p>
            <p className="tw-text-3xl tw-font-bold tw-text-emerald-400">{formatCurrency(capitalData.total_free_margin || 0)}</p>
          </div>
          <div className="tw-p-5 tw-bg-slate-800/50 tw-rounded-xl tw-border tw-border-slate-700/50">
            <p className="tw-text-slate-400 tw-text-sm tw-mb-2">Max Per Trade</p>
            <p className="tw-text-3xl tw-font-bold tw-text-cyan-400">{formatCurrency(capitalData.max_trade_allocation || 0)}</p>
            <p className="tw-text-xs tw-text-slate-400 tw-mt-1">20% of total</p>
          </div>
        </div>
      </div>

      {/* Tabbed Content */}
      <div className="tw-bg-slate-900/50 tw-backdrop-blur-xl tw-border tw-border-slate-700/50 tw-rounded-2xl tw-shadow-2xl tw-overflow-hidden">
        <div className="tw-flex tw-border-b tw-border-slate-700/50">
          {['Active Positions', 'Selected Stocks', 'Trade History'].map((tab, index) => (
            <button
              key={index}
              onClick={() => setActiveTab(index)}
              className={`tw-flex-1 tw-px-6 tw-py-4 tw-font-semibold tw-transition-all tw-duration-200 ${
                activeTab === index
                  ? 'tw-bg-slate-800 tw-text-white tw-border-b-2 tw-border-cyan-500'
                  : 'tw-text-slate-400 hover:tw-text-white hover:tw-bg-slate-800/50'
              }`}
            >
              {tab} ({index === 0 ? activePositions.length : index === 1 ? selectedStocks.length : tradeHistory.length})
            </button>
          ))}
        </div>

        <div className="tw-p-6">
          {/* Active Positions Tab - REDESIGNED */}
          {activeTab === 0 && (
            <div>
              {activePositions.length > 0 ? (
                <div className="tw-grid tw-grid-cols-1 lg:tw-grid-cols-2 tw-gap-4">
                  {activePositions.map((position) => {
                    const isProfit = position.current_pnl >= 0;

                    return (
                      <div
                        key={position.position_id}
                        className={`tw-relative tw-overflow-hidden tw-rounded-2xl tw-border tw-transition-all tw-duration-300 hover:tw-shadow-2xl hover:tw-scale-[1.02] ${
                          isProfit
                            ? 'tw-bg-gradient-to-br tw-from-emerald-950/40 tw-to-emerald-900/20 tw-border-emerald-500/30'
                            : 'tw-bg-gradient-to-br tw-from-rose-950/40 tw-to-rose-900/20 tw-border-rose-500/30'
                        }`}
                      >
                        {/* Real-time Pulse Indicator */}
                        <div className="tw-absolute tw-top-4 tw-right-4">
                          <span className="tw-relative tw-flex tw-h-3 tw-w-3">
                            <span className={`tw-animate-ping tw-absolute tw-inline-flex tw-h-full tw-w-full tw-rounded-full ${isProfit ? 'tw-bg-emerald-400' : 'tw-bg-rose-400'} tw-opacity-75`}></span>
                            <span className={`tw-relative tw-inline-flex tw-rounded-full tw-h-3 tw-w-3 ${isProfit ? 'tw-bg-emerald-500' : 'tw-bg-rose-500'}`}></span>
                          </span>
                        </div>

                        <div className="tw-p-6">
                          {/* Header: Symbol & Type */}
                          <div className="tw-flex tw-items-start tw-justify-between tw-mb-4">
                            <div>
                              <h3 className="tw-text-2xl tw-font-bold tw-text-white tw-mb-1">{position.symbol}</h3>
                              <div className="tw-flex tw-items-center tw-gap-2">
                                <span className={`tw-px-3 tw-py-1 tw-rounded-full tw-text-xs tw-font-bold ${
                                  position.signal_type?.includes("CE")
                                    ? 'tw-bg-emerald-500/30 tw-text-emerald-200 tw-border tw-border-emerald-500/50'
                                    : 'tw-bg-rose-500/30 tw-text-rose-200 tw-border tw-border-rose-500/50'
                                }`}>
                                  {position.signal_type}
                                </span>
                                <span className="tw-text-xs tw-text-slate-400 tw-font-medium">
                                  {position.broker_name?.toUpperCase() || "BROKER"}
                                </span>
                              </div>
                            </div>

                            {/* Large P&L Display */}
                            <div className="tw-text-right">
                              <div className={`tw-text-3xl tw-font-bold ${getPnlColor(position.current_pnl)}`}>
                                {formatCurrency(position.current_pnl)}
                              </div>
                              <div className={`tw-text-lg tw-font-semibold ${getPnlColor(position.current_pnl_percentage)}`}>
                                {formatPercentage(position.current_pnl_percentage)}
                              </div>
                            </div>
                          </div>

                          {/* Price Progress Bar */}
                          <div className="tw-mb-4">
                            <div className="tw-flex tw-justify-between tw-text-xs tw-text-slate-400 tw-mb-2">
                              <span>Entry: {formatCurrency(position.entry_price)}</span>
                              <span>Current: {formatCurrency(position.current_price)}</span>
                            </div>
                            <div className="tw-relative tw-h-2 tw-bg-slate-800 tw-rounded-full tw-overflow-hidden">
                              <div
                                className={`tw-absolute tw-h-full tw-rounded-full tw-transition-all tw-duration-500 ${
                                  isProfit ? 'tw-bg-gradient-to-r tw-from-emerald-500 tw-to-emerald-400' : 'tw-bg-gradient-to-r tw-from-rose-500 tw-to-rose-400'
                                }`}
                                style={{ width: `${Math.min(Math.abs(position.current_pnl_percentage) * 2, 100)}%` }}
                              ></div>
                            </div>
                            <div className="tw-flex tw-justify-between tw-text-xs tw-mt-1">
                              <span className="tw-text-slate-500">SL: {formatCurrency(position.stop_loss || 0)}</span>
                              <span className="tw-text-slate-500">Target: {formatCurrency(position.target || 0)}</span>
                            </div>
                          </div>

                          {/* Stats Grid */}
                          <div className="tw-grid tw-grid-cols-3 tw-gap-3 tw-mb-4">
                            <div className="tw-bg-slate-800/50 tw-rounded-xl tw-p-3 tw-border tw-border-slate-700/50">
                              <div className="tw-text-xs tw-text-slate-400 tw-mb-1">Quantity</div>
                              <div className="tw-text-lg tw-font-bold tw-text-white">{position.quantity}</div>
                            </div>
                            <div className="tw-bg-slate-800/50 tw-rounded-xl tw-p-3 tw-border tw-border-slate-700/50">
                              <div className="tw-text-xs tw-text-slate-400 tw-mb-1">Investment</div>
                              <div className="tw-text-sm tw-font-bold tw-text-cyan-400">
                                {formatCurrency(position.entry_price * position.quantity)}
                              </div>
                            </div>
                            <div className="tw-bg-slate-800/50 tw-rounded-xl tw-p-3 tw-border tw-border-slate-700/50">
                              <div className="tw-text-xs tw-text-slate-400 tw-mb-1">Value</div>
                              <div className="tw-text-sm tw-font-bold tw-text-white">
                                {formatCurrency(position.current_price * position.quantity)}
                              </div>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="tw-flex tw-gap-2">
                            <button
                              onClick={() => handleClosePosition(position.position_id)}
                              className="tw-flex-1 tw-px-4 tw-py-3 tw-bg-rose-600 hover:tw-bg-rose-700 tw-text-white tw-rounded-xl tw-font-semibold tw-transition-all tw-duration-200 tw-shadow-lg hover:tw-shadow-xl tw-flex tw-items-center tw-justify-center tw-gap-2"
                            >
                              <svg className="tw-w-5 tw-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                              Close Position
                            </button>
                            {position.trailing_stop_active && (
                              <div className="tw-px-4 tw-py-3 tw-bg-amber-500/20 tw-border tw-border-amber-500/30 tw-rounded-xl tw-flex tw-items-center tw-justify-center">
                                <svg className="tw-w-5 tw-h-5 tw-text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                </svg>
                              </div>
                            )}
                          </div>

                          {/* Time Indicator */}
                          <div className="tw-mt-3 tw-text-xs tw-text-slate-500 tw-flex tw-items-center tw-gap-2">
                            <svg className="tw-w-4 tw-h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Entry: {new Date(position.entry_time).toLocaleString('en-IN', {
                              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                            })}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="tw-text-center tw-py-16">
                  <div className="tw-relative tw-w-24 tw-h-24 tw-mx-auto tw-mb-6">
                    <svg className="tw-w-full tw-h-full tw-text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                    </svg>
                  </div>
                  <h3 className="tw-text-xl tw-font-bold tw-text-slate-300 tw-mb-2">No Active Positions</h3>
                  <p className="tw-text-slate-500 tw-mb-6">Your trading positions will appear here in real-time</p>
                  <div className="tw-inline-flex tw-items-center tw-gap-2 tw-px-6 tw-py-3 tw-bg-cyan-500/10 tw-border tw-border-cyan-500/30 tw-rounded-xl tw-text-cyan-300">
                    <svg className="tw-w-5 tw-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span className="tw-text-sm tw-font-semibold">Auto-trading active - Waiting for signals</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Selected Stocks Tab */}
          {activeTab === 1 && (
            <div>
              {stocksLoading ? (
                <div className="tw-text-center tw-py-12">
                  <div className="tw-animate-spin tw-rounded-full tw-h-12 tw-w-12 tw-border-b-2 tw-border-cyan-500 tw-mx-auto"></div>
                  <p className="tw-text-slate-400 tw-mt-4">Loading selected stocks...</p>
                </div>
              ) : selectedStocks.length > 0 ? (
                <div className="tw-space-y-3">
                  {selectedStocks.map((stock, idx) => {
                    const lotsToTrade = stock.position_size_lots || 1;
                    const lotSize = stock.lot_size || 0;
                    const totalQty = lotsToTrade * lotSize;
                    const ltp = stock.live_price || stock.premium || 0;
                    const capitalRequired = ltp * totalQty;
                    return (
                      <div key={idx} className="tw-bg-gradient-to-r tw-from-slate-800/80 tw-to-slate-900/80 tw-rounded-xl tw-p-5 tw-border tw-border-slate-700/50 hover:tw-border-cyan-500/50 tw-transition-all tw-duration-300 hover:tw-shadow-xl">
                        <div className="tw-grid tw-grid-cols-12 tw-gap-4 tw-items-center">
                          {/* Symbol & Type */}
                          <div className="tw-col-span-3">
                            <div className="tw-text-2xl tw-font-extrabold tw-text-white tw-mb-1">{stock.symbol}</div>
                            <div className="tw-flex tw-items-center tw-gap-2">
                              <span className={`tw-inline-block tw-px-3 tw-py-1 tw-rounded-md tw-text-xs tw-font-bold ${stock.option_type === "CE" ? 'tw-bg-green-600 tw-text-white' : 'tw-bg-red-600 tw-text-white'}`}>
                                {stock.option_type || "N/A"}
                              </span>
                              <span className="tw-text-xs tw-text-slate-400">{stock.sector || "N/A"}</span>
                            </div>
                          </div>

                          {/* Strike & LTP */}
                          <div className="tw-col-span-3">
                            <div className="tw-text-xs tw-text-slate-400 tw-uppercase tw-mb-1">Strike / LTP</div>
                            <div className="tw-text-lg tw-font-bold tw-text-white">{formatCurrency(stock.strike_price || 0)}</div>
                            <div className="tw-text-base tw-font-bold tw-text-cyan-400">{formatCurrency(ltp)}</div>
                          </div>

                          {/* Lot Info */}
                          <div className="tw-col-span-2">
                            <div className="tw-text-xs tw-text-slate-400 tw-uppercase tw-mb-1">Lot Size</div>
                            <div className="tw-text-lg tw-font-bold tw-text-white">{lotSize}</div>
                            <div className="tw-text-sm tw-text-slate-400">x {lotsToTrade} lots</div>
                          </div>

                          {/* Capital Required */}
                          <div className="tw-col-span-2">
                            <div className="tw-text-xs tw-text-slate-400 tw-uppercase tw-mb-1">Capital</div>
                            <div className="tw-text-lg tw-font-extrabold tw-text-orange-400">{formatCurrency(capitalRequired)}</div>
                          </div>

                          {/* Status */}
                          <div className="tw-col-span-2 tw-text-right">
                            <span className={`tw-inline-block tw-px-4 tw-py-2 tw-rounded-lg tw-text-sm tw-font-bold ${stock.trade_status === "TRADED" ? 'tw-bg-green-600 tw-text-white' : stock.trade_status === "IN_POSITION" ? 'tw-bg-yellow-600 tw-text-white' : 'tw-bg-blue-600 tw-text-white'}`}>
                              {stock.trade_status || "SELECTED"}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="tw-text-center tw-py-12">
                  <svg className="tw-w-16 tw-h-16 tw-text-slate-600 tw-mx-auto tw-mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                  </svg>
                  <p className="tw-text-slate-400 tw-text-lg">No stocks selected yet</p>
                  <p className="tw-text-slate-500 tw-text-sm tw-mt-2">Stock selection runs automatically during market hours (9:00-9:15 AM)</p>
                </div>
              )}
            </div>
          )}

          {/* Trade History Tab */}
          {activeTab === 2 && (
            <div>
              {tradeHistory.length > 0 ? (
                <div className="tw-space-y-3">
                  {tradeHistory.map((trade, idx) => {
                    const isProfitable = trade.net_pnl >= 0;
                    return (
                      <div key={idx} className={`tw-bg-gradient-to-r tw-rounded-xl tw-p-5 tw-border tw-transition-all tw-duration-300 hover:tw-shadow-xl ${isProfitable ? 'tw-from-green-900/20 tw-to-slate-900/80 tw-border-green-700/30 hover:tw-border-green-500/50' : 'tw-from-red-900/20 tw-to-slate-900/80 tw-border-red-700/30 hover:tw-border-red-500/50'}`}>
                        <div className="tw-grid tw-grid-cols-12 tw-gap-4 tw-items-center">
                          {/* Symbol & Type */}
                          <div className="tw-col-span-3">
                            <div className="tw-text-2xl tw-font-extrabold tw-text-white tw-mb-1">{trade.symbol}</div>
                            <div className="tw-flex tw-items-center tw-gap-2">
                              <span className={`tw-inline-block tw-px-3 tw-py-1 tw-rounded-md tw-text-xs tw-font-bold ${trade.signal_type?.includes("CE") ? 'tw-bg-green-600 tw-text-white' : 'tw-bg-red-600 tw-text-white'}`}>
                                {trade.signal_type}
                              </span>
                              <span className="tw-text-xs tw-text-slate-400">{trade.broker_name?.toUpperCase() || "N/A"}</span>
                            </div>
                          </div>

                          {/* Entry & Exit Prices */}
                          <div className="tw-col-span-3">
                            <div className="tw-text-xs tw-text-slate-400 tw-uppercase tw-mb-1">Entry → Exit</div>
                            <div className="tw-flex tw-items-center tw-gap-2">
                              <span className="tw-text-base tw-font-bold tw-text-white">{formatCurrency(trade.entry_price)}</span>
                              <svg className="tw-w-4 tw-h-4 tw-text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                              </svg>
                              <span className="tw-text-base tw-font-bold tw-text-cyan-400">{formatCurrency(trade.exit_price)}</span>
                            </div>
                            <div className="tw-text-xs tw-text-slate-500 tw-mt-0.5">Qty: {trade.quantity || 0}</div>
                          </div>

                          {/* P&L Amount */}
                          <div className="tw-col-span-3">
                            <div className="tw-text-xs tw-text-slate-400 tw-uppercase tw-mb-1">P&L Amount</div>
                            <div className={`tw-text-2xl tw-font-extrabold ${isProfitable ? 'tw-text-green-400' : 'tw-text-red-400'}`}>
                              {formatCurrency(trade.net_pnl)}
                            </div>
                          </div>

                          {/* P&L % & Exit Reason */}
                          <div className="tw-col-span-3 tw-text-right">
                            <div className={`tw-inline-block tw-px-4 tw-py-2 tw-rounded-lg tw-text-lg tw-font-extrabold tw-mb-2 ${isProfitable ? 'tw-bg-green-600 tw-text-white' : 'tw-bg-red-600 tw-text-white'}`}>
                              {formatPercentage(trade.pnl_percentage)}
                            </div>
                            <div className="tw-text-xs tw-text-slate-400 tw-mt-1">{trade.exit_reason}</div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="tw-text-center tw-py-12">
                  <svg className="tw-w-16 tw-h-16 tw-text-slate-600 tw-mx-auto tw-mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <p className="tw-text-slate-400 tw-text-lg">No trade history available</p>
                  <p className="tw-text-slate-500 tw-text-sm tw-mt-2">Completed trades will appear here</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AutoTradingPage;
