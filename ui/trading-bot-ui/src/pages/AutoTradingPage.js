import React, { useState, useEffect, useRef, useCallback } from "react";
import api from "../services/api";
import ActivePositionCard from "../components/ActivePositionCard";
import SelectedStockCard from "../components/SelectedStockCard";

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

  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [wsConnected, setWsConnected] = useState(false);
  const [showLiveConfirmation, setShowLiveConfirmation] = useState(false);
  
  // WebSocket Throttling Refs
  const updatesBuffer = useRef({
    activePositions: {}, // Map by position_id
    selectedStocks: {},  // Map by symbol/key
    pnlSummary: null,
    hasUpdates: false
  });

  // Batch process WebSocket updates
  useEffect(() => {
    const processUpdates = () => {
      if (!updatesBuffer.current.hasUpdates) return;

      const buffer = updatesBuffer.current;
      
      // Batch update active positions
      if (Object.keys(buffer.activePositions).length > 0) {
        setActivePositions(prev => {
          let hasChanges = false;
          const newPositions = prev.map(pos => {
            if (buffer.activePositions[pos.position_id]) {
              hasChanges = true;
              return { ...pos, ...buffer.activePositions[pos.position_id] };
            }
            return pos;
          });
          
          // Also handle new positions created via WS
          // Note: Full sync is handled by fetchActivePositions, this is just for updates
          return hasChanges ? newPositions : prev;
        });
        buffer.activePositions = {};
      }

      // Batch update selected stocks
      if (Object.keys(buffer.selectedStocks).length > 0) {
        setSelectedStocks(prev => {
          let hasChanges = false;
          const newStocks = prev.map(stock => {
            const key = stock.option_instrument_key || stock.symbol;
            if (buffer.selectedStocks[key]) {
              hasChanges = true;
              return { ...stock, ...buffer.selectedStocks[key] };
            }
            return stock;
          });
          return hasChanges ? newStocks : prev;
        });
        buffer.selectedStocks = {};
      }

      buffer.hasUpdates = false;
    };

    const interval = setInterval(processUpdates, 500); // 500ms throttle
    return () => clearInterval(interval);
  }, []);

  const fetchActivePositions = useCallback(async () => {
    try {
      const response = await api.get("/v1/trading/execution/active-positions");
      if (response.data.success) {
        const newPositions = response.data.active_positions || [];
        setActivePositions(prev => {
          if (JSON.stringify(prev) !== JSON.stringify(newPositions)) {
            return newPositions;
          }
          return prev;
        });
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
        setPnlSummary(prev => {
          if (JSON.stringify(prev) !== JSON.stringify(response.data.summary)) {
            return response.data.summary;
          }
          return prev;
        });
      }
    } catch (err) {
      console.error("Error fetching PnL summary:", err);
    }
  }, []);

  const fetchTradeHistory = useCallback(async () => {
    try {
      const response = await api.get(`/v1/trading/execution/trade-history?limit=50&trading_mode=${tradingMode}`);
      if (response.data.success) {
        const newHistory = response.data.trades || [];
        setTradeHistory(prev => {
          if (JSON.stringify(prev) !== JSON.stringify(newHistory)) {
            return newHistory;
          }
          return prev;
        });
      }
    } catch (err) {
      console.error("Error fetching trade history:", err);
    }
  }, [tradingMode]);

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
    // Only show loading state if we have no data
    if (selectedStocks.length === 0) setStocksLoading(true);
    
    try {
      const response = await api.get("/v1/trading/execution/selected-stocks");
      const payload = response?.data;
      if (!payload || !payload.success) {
        // Only clear if we expected data but got error/empty
        if (selectedStocks.length > 0) setSelectedStocks([]);
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
      
      setSelectedStocks(prev => {
        if (JSON.stringify(prev) !== JSON.stringify(cleanedStocks)) {
          return cleanedStocks;
        }
        return prev;
      });
    } catch (err) {
      console.error("Error fetching selected stocks:", err);
      // Only clear if we strictly need to
      // setSelectedStocks([]); 
    } finally {
      setStocksLoading(false);
    }
  }, [selectedStocks.length]);

  const handleManualRefresh = useCallback(async () => {
    setIsLoading(true);
    await Promise.allSettled([
      fetchActivePositions(),
      fetchPortfolioSummary(),
      fetchTradeHistory(),
      fetchSelectedStocks(),
      fetchCapitalOverview()
    ]);
    setLastUpdated(new Date());
    setIsLoading(false);
  }, [fetchActivePositions, fetchPortfolioSummary, fetchTradeHistory, fetchSelectedStocks, fetchCapitalOverview]);

  const handleClosePosition = useCallback(async (positionId) => {
    if (!window.confirm("Are you sure you want to close this position?")) {
      return;
    }
    try {
      const response = await api.post(`/v1/trading/execution/close-position/${positionId}`);
      if (response.data.success) {
        setSuccess(`Position closed. PnL: ₹${response.data.pnl.toFixed(2)}`);
        handleManualRefresh();
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to close position");
    }
  }, [handleManualRefresh]);

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
      handleManualRefresh();
    } catch (err) {
      setError("Emergency stop failed. Please try closing positions individually.");
    } finally {
      setEmergencyStopLoading(false);
    }
  }, [activePositions, handleManualRefresh]);

  const updateTradingMode = useCallback(async (mode) => {
    try {
      const response = await api.post(`/v1/trading/execution/user-trading-preferences?trading_mode=${mode}&execution_mode=${executionMode}`);
      if (response.data.success) {
        setTradingMode(mode);
        setShowLiveConfirmation(false);
      }
    } catch (err) {
      console.error("Error updating trading mode:", err);
      setError("Failed to update trading mode");
      setShowLiveConfirmation(false);
    }
  }, [executionMode]);

  const handleTradingModeToggle = useCallback(() => {
    if (tradingMode === "paper") {
      setShowLiveConfirmation(true);
    } else {
      updateTradingMode("paper");
    }
  }, [tradingMode, updateTradingMode]);

  // Refresh data when trading mode changes
  useEffect(() => {
    fetchPortfolioSummary();
    fetchCapitalOverview();
  }, [tradingMode, fetchPortfolioSummary, fetchCapitalOverview]);

  const initializeWebSocket = useCallback(() => {
    try {
      const baseUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";
      const wsUrl = baseUrl.replace("http://", "ws://").replace("https://", "wss://") + "/ws/unified";
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
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
            updatesBuffer.current.activePositions[data.position_id] = {
              current_price: data.current_price,
              current_pnl: data.pnl,
              current_pnl_percentage: data.pnl_percent,
              stop_loss: data.stop_loss,
              trailing_stop_active: data.trailing_sl_active,
              last_updated: data.last_updated,
            };
            updatesBuffer.current.hasUpdates = true;
            // Also trigger summary fetch periodically via interval, not here
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
            // Immediate refresh for important events
            handleManualRefresh();
          }
          
          if (message.type === "active_position_created") {
            // Immediate update for new position creation
            const posData = message.data;
            setActivePositions((prev) => {
              const existingIndex = prev.findIndex((p) => p.position_id === posData.position_id);
              if (existingIndex >= 0) return prev;
              
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
            });
          }
          
          if (message.type === "trade_error") {
            setError(`Trade error for ${message.data.symbol}: ${message.data.error}`);
          }
          
          if (message.type === "position_closed") {
            const posData = message.data;
            setSuccess(`Position closed: ${posData.symbol} - PnL: ₹${posData.pnl.toFixed(2)}`);
            handleManualRefresh();
          }
          
          if (message.type === "selected_stock_price_update") {
            const data = message.data;
            const key = data.option_instrument_key || data.symbol;
            updatesBuffer.current.selectedStocks[key] = {
              live_price: data.live_option_premium,
              live_spot_price: data.live_spot_price,
              price_change: data.price_change,
              price_change_percent: data.price_change_percent,
              unrealized_pnl: data.unrealized_pnl,
              unrealized_pnl_percent: data.unrealized_pnl_percent,
              state: data.state,
              last_updated: data.timestamp,
            };
            updatesBuffer.current.hasUpdates = true;
          }
        } catch (parseError) {
          console.error("Error parsing WebSocket message:", parseError);
        }
      };

      ws.onclose = (event) => {
        setWsConnected(false);
        setTimeout(() => {
          if (socketRef.current === ws) {
            initializeWebSocket();
          }
        }, 5000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setWsConnected(false);
      };

      socketRef.current = ws;
    } catch (err) {
      console.error("WebSocket connection error:", err);
      setWsConnected(false);
    }
  }, [handleManualRefresh]);

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
    if (activeTab === 0) fetchActivePositions();
    if (activeTab === 1) fetchSelectedStocks();
    if (activeTab === 2) fetchTradeHistory();
  }, [activeTab, fetchActivePositions, fetchSelectedStocks, fetchTradeHistory]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        if (activeTab === 0) fetchActivePositions();
        // Only fetch stocks if we don't have them yet. 
        // Once loaded, they are static for the day (prices update via WebSocket)
        if (selectedStocks.length === 0) fetchSelectedStocks(); 
        if (activeTab === 2) fetchTradeHistory(); 
        fetchPortfolioSummary(); 
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchPortfolioSummary, fetchActivePositions, fetchSelectedStocks, fetchTradeHistory, selectedStocks.length]);

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
    const formatted = new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(Math.abs(amount || 0));
    return `${amount < 0 ? '-' : ''}₹${formatted}`;
  }, []);

  const formatPercentage = useCallback((value = 0) => {
    const num = Number.isFinite(value) ? value : 0;
    return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
  }, []);

  const getPnlColor = useCallback((value) => {
    if (value > 0) return 'tw-text-emerald-500';
    if (value < 0) return 'tw-text-rose-500';
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
              {/* WebSocket Status */}
              <div className="tw-flex tw-items-center tw-gap-1.5 tw-px-2 tw-py-1 tw-bg-slate-800/50 tw-rounded-full tw-border tw-border-slate-700/50" title={wsConnected ? "Real-time connection active" : "Connecting..."}>
                <span className={`tw-w-2 tw-h-2 tw-rounded-full ${wsConnected ? 'tw-bg-emerald-500 tw-animate-pulse' : 'tw-bg-rose-500'}`}></span>
                <span className="tw-text-[10px] tw-font-medium tw-text-slate-400">{wsConnected ? "LIVE" : "OFFLINE"}</span>
              </div>
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

          {/* Right: Controls */}
          <div className="tw-flex tw-gap-3">
            {/* Manual Refresh Button */}
            <div className="tw-flex tw-flex-col tw-items-end tw-justify-center">
              <button 
                onClick={handleManualRefresh} 
                disabled={isLoading}
                className="tw-p-3 tw-bg-slate-800 hover:tw-bg-slate-700 tw-text-slate-300 hover:tw-text-white tw-rounded-xl tw-transition-all tw-border tw-border-slate-700 hover:tw-border-slate-600 disabled:tw-opacity-50"
                title="Force Refresh Data"
              >
                <svg className={`tw-w-5 tw-h-5 ${isLoading ? 'tw-animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              <span className="tw-text-[10px] tw-text-slate-500 tw-mt-1">
                Updated: {lastUpdated.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            {/* Emergency Stop */}
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
            <p className="tw-text-xs tw-text-slate-400 tw-mt-1">60% of total</p>
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
                  {activePositions.map((position) => (
                    <ActivePositionCard 
                      key={position.position_id} 
                      position={position} 
                      onClose={handleClosePosition} 
                    />
                  ))}
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
                  {selectedStocks.map((stock, idx) => (
                    <SelectedStockCard key={idx} stock={stock} />
                  ))}
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
            <div className="tw-overflow-x-auto">
              {tradeHistory.length > 0 ? (
                <table className="tw-w-full tw-text-xs md:tw-text-sm tw-text-left">
                  <thead className="tw-text-xs tw-text-slate-400 tw-uppercase tw-bg-slate-800/80">
                    <tr>
                      <th className="tw-px-4 tw-py-3 tw-whitespace-nowrap">Date</th>
                      <th className="tw-px-4 tw-py-3 tw-whitespace-nowrap">Instrument</th>
                      <th className="tw-px-4 tw-py-3 tw-whitespace-nowrap">Type</th>
                      <th className="tw-px-4 tw-py-3 tw-text-right">Qty</th>
                      <th className="tw-px-4 tw-py-3 tw-text-right">Buy Avg</th>
                      <th className="tw-px-4 tw-py-3 tw-text-right">Sell Avg</th>
                      <th className="tw-px-4 tw-py-3 tw-text-right">Gross P&L</th>
                      <th className="tw-px-4 tw-py-3 tw-text-right">Charges</th>
                      <th className="tw-px-4 tw-py-3 tw-text-right">Net P&L</th>
                      <th className="tw-px-4 tw-py-3 tw-text-right">% Chg</th>
                    </tr>
                  </thead>
                  <tbody className="tw-divide-y tw-divide-slate-800">
                    {tradeHistory.map((trade, idx) => {
                      const grossPnl = trade.gross_pnl || (trade.exit_price - trade.entry_price) * trade.quantity;
                      // Calculate charges if not provided (Gross - Net)
                      const charges = trade.gross_pnl && trade.net_pnl 
                        ? trade.gross_pnl - trade.net_pnl 
                        : Math.abs(grossPnl * 0.005); // Fallback est. 0.5%
                      const netPnl = trade.net_pnl || (grossPnl - charges);
                      const isProfit = netPnl >= 0;

                      return (
                        <tr key={idx} className="tw-hover:bg-slate-800/30 tw-transition-colors">
                          <td className="tw-px-4 tw-py-3 tw-text-slate-400 tw-whitespace-nowrap">
                            <div>{trade.entry_date || 'N/A'}</div>
                            <div className="tw-text-[10px] tw-text-slate-600">{trade.entry_time_str?.split(' ')[0]}</div>
                          </td>
                          <td className="tw-px-4 tw-py-3">
                            <div className="tw-font-bold tw-text-white">{trade.symbol}</div>
                            {/* <div className="tw-text-[10px] tw-text-slate-500">{trade.trade_id}</div> */}
                          </td>
                          <td className="tw-px-4 tw-py-3">
                            <span className={`tw-px-2 tw-py-0.5 tw-rounded tw-text-[10px] tw-font-bold tw-uppercase ${
                              trade.signal_type?.includes('BUY') ? 'tw-bg-emerald-500/10 tw-text-emerald-400' : 'tw-bg-rose-500/10 tw-text-rose-400'
                            }`}>
                              {trade.signal_type?.includes('BUY') ? 'INTRADAY' : 'DELIVERY'}
                            </span>
                          </td>
                          <td className="tw-px-4 tw-py-3 tw-text-right tw-font-medium tw-text-slate-300">{trade.quantity}</td>
                          <td className="tw-px-4 tw-py-3 tw-text-right tw-text-slate-300">{formatCurrency(trade.entry_price)}</td>
                          <td className="tw-px-4 tw-py-3 tw-text-right tw-text-slate-300">{formatCurrency(trade.exit_price)}</td>
                          <td className={`tw-px-4 tw-py-3 tw-text-right ${grossPnl >= 0 ? 'tw-text-emerald-400' : 'tw-text-rose-400'}`}>
                            {formatCurrency(grossPnl)}
                          </td>
                          <td className="tw-px-4 tw-py-3 tw-text-right tw-text-rose-300 tw-text-xs">
                            {formatCurrency(charges)}
                          </td>
                          <td className={`tw-px-4 tw-py-3 tw-text-right tw-font-bold ${isProfit ? 'tw-text-emerald-400' : 'tw-text-rose-400'}`}>
                            {formatCurrency(netPnl)}
                          </td>
                          <td className={`tw-px-4 tw-py-3 tw-text-right ${isProfit ? 'tw-text-emerald-400' : 'tw-text-rose-400'}`}>
                            {formatPercentage(trade.pnl_percentage)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
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
      {/* Live Trading Confirmation Modal */}
      {showLiveConfirmation && (
        <div className="tw-fixed tw-inset-0 tw-z-[100] tw-flex tw-items-center tw-justify-center tw-p-4 tw-bg-slate-950/80 tw-backdrop-blur-sm">
          <div className="tw-bg-slate-900 tw-border tw-border-rose-500/30 tw-rounded-2xl tw-shadow-2xl tw-max-w-md tw-w-full tw-overflow-hidden tw-animate-in tw-fade-in tw-zoom-in-95 tw-duration-200">
            <div className="tw-p-6">
              <div className="tw-flex tw-items-center tw-gap-4 tw-mb-4">
                <div className="tw-p-3 tw-bg-rose-500/10 tw-rounded-full tw-border tw-border-rose-500/20">
                  <svg className="tw-w-8 tw-h-8 tw-text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <h3 className="tw-text-xl tw-font-bold tw-text-white">Enable Live Trading?</h3>
                  <p className="tw-text-rose-400 tw-text-sm tw-font-medium">Real Money Risk Warning</p>
                </div>
              </div>
              
              <div className="tw-space-y-4 tw-mb-6">
                <p className="tw-text-slate-300 tw-text-sm tw-leading-relaxed">
                  You are about to switch to <span className="tw-text-white tw-font-bold">LIVE TRADING</span> mode.
                </p>
                <div className="tw-bg-rose-500/5 tw-border tw-border-rose-500/20 tw-rounded-xl tw-p-4">
                  <ul className="tw-space-y-2 tw-text-sm tw-text-slate-300">
                    <li className="tw-flex tw-items-start tw-gap-2">
                      <span className="tw-text-rose-500 tw-mt-0.5">•</span>
                      Trades will be executed on your real broker account.
                    </li>
                    <li className="tw-flex tw-items-start tw-gap-2">
                      <span className="tw-text-rose-500 tw-mt-0.5">•</span>
                      Real funds will be used for all transactions.
                    </li>
                    <li className="tw-flex tw-items-start tw-gap-2">
                      <span className="tw-text-rose-500 tw-mt-0.5">•</span>
                      Profit and Loss will be real financial impact.
                    </li>
                  </ul>
                </div>
                <p className="tw-text-slate-400 tw-text-xs">
                  Please ensure your risk management settings (Stop Loss, Max Daily Loss) are correctly configured before proceeding.
                </p>
              </div>

              <div className="tw-flex tw-gap-3">
                <button
                  onClick={() => setShowLiveConfirmation(false)}
                  className="tw-flex-1 tw-py-3 tw-bg-slate-800 hover:tw-bg-slate-700 tw-text-slate-300 tw-rounded-xl tw-font-medium tw-transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => updateTradingMode("live")}
                  className="tw-flex-1 tw-py-3 tw-bg-rose-600 hover:tw-bg-rose-700 tw-text-white tw-rounded-xl tw-font-bold tw-transition-colors tw-shadow-lg hover:tw-shadow-rose-900/20"
                >
                  Confirm Live Trading
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AutoTradingPage;
