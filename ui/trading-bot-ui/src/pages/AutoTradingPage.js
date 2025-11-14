import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Stack,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  LinearProgress,
  Tabs,
  Tab,
  Button,
  Switch,
  FormControlLabel,
  Tooltip,
  Collapse,
} from "@mui/material";
import {
  AccountBalance as AccountBalanceIcon,
  ShowChart as ShowChartIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  Stop as StopIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  SignalCellularAlt as SignalIcon,
} from "@mui/icons-material";
import api from "../services/api";
import StockActivityChart from "../components/trading/StockActivityChart";

const AutoTradingPage = () => {
  // State management - Will be loaded from database
  const [tradingMode, setTradingMode] = useState("paper"); // paper or live
  const [executionMode, setExecutionMode] = useState("multi_demat"); // single_demat or multi_demat
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [activePositions, setActivePositions] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [pnlSummary, setPnlSummary] = useState({
    total_pnl: 0,
    total_investment: 0,
    pnl_percent: 0,
    active_positions_count: 0,
  });
  const [isLoading, setIsLoading] = useState(true); // Start with loading
  const [stocksLoading, setStocksLoading] = useState(true); // Track stocks loading separately
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [executionResults] = useState(null);
  const [showCapitalBreakdown, setShowCapitalBreakdown] = useState(false);
  const [showExecutionDetails, setShowExecutionDetails] = useState(false);
  const [emergencyStopLoading, setEmergencyStopLoading] = useState(false);
  const [autoTradingRunning, setAutoTradingRunning] = useState(false);

  // Live activity tracking - PER STOCK CHART
  const [activityFeed, setActivityFeed] = useState([]);
  const [stockActivityStats, setStockActivityStats] = useState({}); // Per-stock activity count
  const maxActivityItems = 10;
  const [showLiveActivity, setShowLiveActivity] = useState(false);

  // WebSocket ref
  const socketRef = useRef(null);
  // Capital state
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

  // ---------- Data fetchers ----------
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
      const response = await api.get(
        "/v1/trading/execution/trade-history?limit=50"
      );
      if (response.data.success) {
        setTradeHistory(response.data.trades || []);
      }
    } catch (err) {
      console.error("Error fetching trade history:", err);
    }
  }, []);

  const fetchTradingPreferences = useCallback(async () => {
    try {
      const response = await api.get(
        "/v1/trading/execution/user-trading-preferences"
      );
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
      const response = await api.get(
        `/v1/trading/execution/user-capital-overview?trading_mode=${tradingMode}`
      );
      if (response.data.success) {
        setCapitalData(response.data.capital_overview);
      }
    } catch (err) {
      console.error("Error fetching capital overview:", err);
    }
  }, [tradingMode]);

  const fetchSelectedStocks = useCallback(async () => {
    setStocksLoading(true); // Start loading
    try {
      const response = await api.get("/v1/trading/execution/selected-stocks");

      console.debug("fetchSelectedStocks response:", response?.data);

      // Backend now returns clean, pre-parsed data - no complex parsing needed!
      const payload = response?.data;

      if (!payload || !payload.success) {
        setSelectedStocks([]);
        return;
      }

      // Get stocks array from response
      const stocks = payload.stocks || [];

      // Backend already parsed and validated everything - just use the data directly
      const cleanedStocks = stocks.map((stock) => ({
        // All fields are already parsed by backend
        ...stock,
        // Ensure numeric types with safe defaults
        strike_price: stock.strike_price || 0,
        lot_size: stock.lot_size || 0,
        premium: stock.premium || 0,
        capital_allocation: stock.capital_allocation || 0,
        position_size_lots: stock.position_size_lots || 0,
        max_loss: stock.max_loss || 0,
        target_profit: stock.target_profit || 0,
        selection_score: stock.selection_score || 0,
        price_at_selection: stock.price_at_selection || 0,
        // Ensure strings with safe defaults
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
      setStocksLoading(false); // Always stop loading
    }
  }, []);

  // ---------- Trading Actions ----------
  const handleClosePosition = async (positionId) => {
    if (!window.confirm("Are you sure you want to close this position?")) {
      return;
    }

    try {
      const response = await api.post(
        `/v1/trading/execution/close-position/${positionId}`
      );

      if (response.data.success) {
        setSuccess(`Position closed. PnL: ₹${response.data.pnl.toFixed(2)}`);
        await fetchActivePositions();
        await fetchPortfolioSummary();
        await fetchTradeHistory();
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to close position");
    }
  };

  const handleEmergencyStopAll = async () => {
    if (
      !window.confirm(
        "EMERGENCY STOP ALL POSITIONS\n\n" +
          "This will immediately close ALL active positions at market price.\n\n" +
          "Are you absolutely sure you want to continue?"
      )
    ) {
      return;
    }

    setEmergencyStopLoading(true);
    setError(null);

    try {
      const closePromises = activePositions.map((position) =>
        api.post(`/v1/trading/execution/close-position/${position.position_id}`)
      );

      const results = await Promise.allSettled(closePromises);

      const successCount = results.filter(
        (r) => r.status === "fulfilled"
      ).length;
      const failCount = results.filter((r) => r.status === "rejected").length;

      setSuccess(
        `Emergency Stop Complete: ${successCount} positions closed${
          failCount > 0 ? `, ${failCount} failed` : ""
        }`
      );

      await fetchActivePositions();
      await fetchPortfolioSummary();
      await fetchTradeHistory();
    } catch (err) {
      setError(
        "Emergency stop failed. Please try closing positions individually."
      );
    } finally {
      setEmergencyStopLoading(false);
    }
  };

  const handleTradingModeToggle = async () => {
    const newMode = tradingMode === "paper" ? "live" : "paper";

    if (newMode === "live") {
      if (
        !window.confirm(
          "⚠️ SWITCHING TO LIVE TRADING\n\n" +
            "This will use REAL MONEY from your broker account.\n\n" +
            "Are you sure you want to continue?"
        )
      ) {
        return;
      }
    }

    try {
      // Save to database
      const response = await api.post(
        `/v1/trading/execution/user-trading-preferences?trading_mode=${newMode}&execution_mode=${executionMode}`
      );

      if (response.data.success) {
        setTradingMode(newMode);
        // Refresh capital data for new mode
        await fetchPortfolioSummary();
      }
    } catch (err) {
      console.error("Error updating trading mode:", err);
      setError("Failed to update trading mode");
    }
  };

  // ---------- WebSocket for Real-time PnL ----------
  const initializeWebSocket = useCallback(() => {
    try {
      const baseUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";
      const wsUrl =
        baseUrl.replace("http://", "ws://").replace("https://", "wss://") +
        "/ws/unified";

      console.log("Connecting to WebSocket:", wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("Connected to unified WebSocket for trading updates");

        // Send client info
        ws.send(
          JSON.stringify({
            type: "client_info",
            client_type: "trading_execution",
            timestamp: new Date().toISOString(),
          })
        );

        // Subscribe to all trading events
        ws.send(
          JSON.stringify({
            type: "subscribe",
            events: ["all"], // Subscribe to all events including trading_signal
          })
        );

        console.log("Subscribed to all trading events");
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // Handle PnL updates
          if (message.type === "pnl_update") {
            const data = message.data;
            // Update specific position in activePositions
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

            // Refresh summary
            fetchPortfolioSummary();
          }

          // Handle trading signals - Track per-stock activity
          if (message.type === "trading_signal") {
            const signalData = message.data;
            const symbol = signalData.symbol;

            console.log(
              `Signal: ${signalData.signal_type} for ${symbol} (Conf: ${signalData.confidence})`
            );

            // Update per-stock stats
            setStockActivityStats((prev) => ({
              ...prev,
              [symbol]: {
                symbol: symbol,
                signals: (prev[symbol]?.signals || 0) + 1,
                trades: prev[symbol]?.trades || 0,
                pnl: prev[symbol]?.pnl || 0,
                lastActivity: new Date().toISOString(),
                status: signalData.signal_type,
              },
            }));

            // Add to activity feed
            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "signal",
                symbol: symbol,
                message: `${signalData.signal_type.toUpperCase()} signal`,
                details: `Confidence: ${(signalData.confidence * 100).toFixed(
                  0
                )}% | Price: ₹${signalData.price}`,
                timestamp: new Date().toISOString(),
                severity: "info",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // Handle signal skipped
          if (message.type === "signal_skipped") {
            console.log(
              `Signal skipped for ${message.data.symbol}: ${message.data.reason}`
            );

            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "signal_skipped",
                message: `Signal skipped for ${message.data.symbol}`,
                details: message.data.reason,
                timestamp: new Date().toISOString(),
                severity: "warning",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // Handle trade execution - Track per-stock
          if (message.type === "trade_executed") {
            const tradeData = message.data;
            const symbol = tradeData.symbol;

            setSuccess(
              `Trade executed: ${symbol} ${
                tradeData.option_type
              } @ ₹${tradeData.entry_price.toFixed(2)}`
            );

            // Update per-stock stats
            setStockActivityStats((prev) => ({
              ...prev,
              [symbol]: {
                ...(prev[symbol] || { signals: 0, trades: 0, pnl: 0 }),
                symbol: symbol,
                trades: (prev[symbol]?.trades || 0) + 1,
                lastActivity: new Date().toISOString(),
                status: "traded",
              },
            }));

            fetchActivePositions();
            fetchPortfolioSummary();
            fetchSelectedStocks();

            // Add to activity feed
            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "trade_executed",
                symbol: symbol,
                message: `Trade Executed: ${tradeData.option_type}`,
                details: `Entry: ₹${tradeData.entry_price.toFixed(2)} | Lots: ${
                  tradeData.lot_size
                } | Mode: ${tradeData.trading_mode}`,
                timestamp: tradeData.timestamp || new Date().toISOString(),
                severity: "success",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // CRITICAL FIX: Handle active position created event
          // This is broadcasted when a position is opened and MUST be handled
          // to display positions in real-time
          if (message.type === "active_position_created") {
            const posData = message.data;
            console.log(
              `Active position created: ${posData.symbol} @ ₹${posData.entry_price}`
            );

            // Add position to state immediately - don't wait for API refresh
            setActivePositions((prev) => {
              // Check if position already exists (prevent duplicates)
              const existingIndex = prev.findIndex(
                (p) => p.position_id === posData.position_id
              );

              if (existingIndex >= 0) {
                // Update existing position
                const updated = [...prev];
                updated[existingIndex] = {
                  ...updated[existingIndex],
                  ...posData,
                };
                return updated;
              } else {
                // Add new position at the top
                return [
                  {
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
                  },
                  ...prev,
                ];
              }
            });

            // Refresh summary data
            fetchPortfolioSummary();
            fetchSelectedStocks();

            // Add to activity feed
            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "position_created",
                message: `Position Opened: ${posData.symbol}`,
                details: `Entry: ₹${posData.entry_price.toFixed(2)} | SL: ₹${
                  posData.stop_loss
                } | Target: ₹${posData.target}`,
                timestamp: posData.timestamp || new Date().toISOString(),
                severity: "success",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // Handle trade errors
          if (message.type === "trade_error") {
            setError(
              `Trade error for ${message.data.symbol}: ${message.data.error}`
            );

            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "trade_error",
                message: `Trade Error: ${message.data.symbol}`,
                details: message.data.error,
                timestamp: message.data.timestamp || new Date().toISOString(),
                severity: "error",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // Handle trade preparation failures
          if (message.type === "trade_preparation_failed") {
            console.warn(
              `Trade prep failed for ${message.data.symbol}: ${message.data.status}`
            );

            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "trade_prep_failed",
                message: `Trade Preparation Failed: ${message.data.symbol}`,
                details: `Status: ${message.data.status}`,
                timestamp: message.data.timestamp || new Date().toISOString(),
                severity: "warning",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // Handle position closed
          if (message.type === "position_closed") {
            const posData = message.data;
            setSuccess(
              `Position closed: ${posData.symbol} - PnL: ₹${posData.pnl.toFixed(
                2
              )}`
            );
            fetchActivePositions();
            fetchPortfolioSummary();
            fetchTradeHistory();

            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "position_closed",
                message: `Position Closed: ${posData.symbol}`,
                details: `PnL: ₹${posData.pnl.toFixed(2)} | Exit: ₹${
                  posData.exit_price
                }`,
                timestamp: posData.timestamp || new Date().toISOString(),
                severity: posData.pnl >= 0 ? "success" : "error",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // Handle position closing
          if (message.type === "position_closing") {
            console.log(`Closing position for ${message.data.symbol}...`);

            setActivityFeed((prev) => [
              {
                id: Date.now(),
                type: "position_closing",
                message: `Closing Position: ${message.data.symbol}`,
                details: "Exit signal triggered",
                timestamp: message.data.timestamp || new Date().toISOString(),
                severity: "info",
              },
              ...prev.slice(0, maxActivityItems - 1),
            ]);
          }

          // Handle live price updates for selected stocks
          if (message.type === "selected_stock_price_update") {
            const data = message.data;
            setSelectedStocks((prev) =>
              prev.map((stock) =>
                stock.option_instrument_key === data.option_instrument_key ||
                stock.symbol === data.symbol
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
        console.log("WebSocket connection closed:", event.code);
        setTimeout(() => {
          if (socketRef.current === ws) {
            console.log("Attempting to reconnect WebSocket...");
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
  }, [
    fetchActivePositions,
    fetchPortfolioSummary,
    fetchSelectedStocks,
    fetchTradeHistory,
  ]);

  // ---------- Effects ----------
  // OPTIMIZED: Load ALL data in parallel for INSTANT page load
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // CRITICAL FIX: Load EVERYTHING in parallel - don't wait for preferences!
        // This makes the page load 3-5x faster
        await Promise.allSettled([
          fetchTradingPreferences(),
          fetchSelectedStocks(),
          fetchPortfolioSummary(),
          fetchActivePositions(),
          fetchCapitalOverview(),
          fetchTradeHistory(),
        ]);

        console.log("All initial data loaded successfully");
      } catch (err) {
        console.error("Error loading initial data:", err);
      } finally {
        // Mark page as loaded - this happens FAST now!
        setIsLoading(false);
      }

      // Initialize WebSocket after data loaded
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

  // OPTIMIZED: Auto-refresh every 5 seconds (less server load)
  // WebSocket provides real-time updates, so polling can be slower
  useEffect(() => {
    const interval = setInterval(() => {
      // Only refresh if page is visible (performance optimization)
      if (document.visibilityState === "visible") {
        fetchPortfolioSummary();
        fetchActivePositions();
      }
    }, 5000); // Changed from 2s to 5s - WebSocket handles real-time updates

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // OPTIMIZED: Poll auto-trading status every 10 seconds
  useEffect(() => {
    const checkAutoTradingStatus = async () => {
      // Skip if page not visible (save resources)
      if (document.visibilityState !== "visible") return;

      try {
        const response = await api.get(
          "/v1/trading/execution/auto-trading-status"
        );
        if (response.data.success) {
          setAutoTradingRunning(response.data.websocket_running || false);
        }
      } catch (err) {
        // Silently fail - status check is not critical
        console.error("Failed to get auto-trading status:", err);
      }
    };

    // Check immediately
    checkAutoTradingStatus();

    // Then poll every 10 seconds (reduced from 5s - less server load)
    const interval = setInterval(checkAutoTradingStatus, 10000);

    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
    }).format(amount || 0);
  };

  const formatPercentage = (value = 0) => {
    const num = Number.isFinite(value) ? value : 0;
    return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
  };

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Emergency Controls - Sticky Header */}
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 1000,
          bgcolor: "background.paper",
          borderBottom: 1,
          borderColor: "divider",
          mb: 3,
          pb: 2,
          pt: 1,
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          spacing={2}
        >
          {/* Left: Title & Mode */}
          <Box>
            <Typography
              variant="h5"
              component="h1"
              fontWeight={600}
              sx={{ mb: 0.5 }}
            >
              Automated Trading
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip
                label={tradingMode === "paper" ? "PAPER" : "LIVE"}
                color={tradingMode === "paper" ? "info" : "error"}
                size="small"
                sx={{ fontWeight: 600 }}
              />
              <Typography variant="caption" color="text.secondary">
                {activePositions.length} Active Position
                {activePositions.length !== 1 ? "s" : ""}
              </Typography>
            </Stack>
          </Box>

          {/* Center: Quick P&L */}
          <Box sx={{ textAlign: "center", px: 3 }}>
            <Typography variant="caption" color="text.secondary">
              Total P&L
            </Typography>
            <Typography
              variant="h5"
              fontWeight={700}
              color={pnlSummary.total_pnl >= 0 ? "success.main" : "error.main"}
            >
              {formatCurrency(pnlSummary.total_pnl)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatPercentage(pnlSummary.pnl_percent)}
            </Typography>
          </Box>

          {/* Right: Emergency Controls */}
          <Stack direction="row" spacing={2} alignItems="center">
            <Tooltip title="Close all active positions immediately">
              <Button
                variant="contained"
                color="error"
                size="large"
                startIcon={<StopIcon />}
                onClick={handleEmergencyStopAll}
                disabled={emergencyStopLoading || activePositions.length === 0}
                sx={{
                  fontWeight: 600,
                  minWidth: 180,
                  boxShadow: 3,
                  "&:hover": {
                    boxShadow: 6,
                  },
                }}
              >
                {emergencyStopLoading ? "STOPPING..." : "EMERGENCY STOP"}
              </Button>
            </Tooltip>
          </Stack>
        </Stack>
      </Box>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          onClose={() => setSuccess(null)}
        >
          {success}
        </Alert>
      )}

      {isLoading && <LinearProgress sx={{ mb: 2 }} />}

      <Grid container spacing={2.5}>
        {/* Portfolio Summary - Top Priority */}
        <Grid item xs={12}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" fontWeight={600} sx={{ mb: 2.5 }}>
                Portfolio Summary
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor:
                        pnlSummary.total_pnl >= 0
                          ? "success.light"
                          : "error.light",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="white"
                      sx={{ opacity: 0.9, display: "block", mb: 0.5 }}
                    >
                      Total P&L
                    </Typography>
                    <Typography variant="h5" color="white" fontWeight={700}>
                      {formatCurrency(pnlSummary.total_pnl)}
                    </Typography>
                    <Typography variant="body2" color="white" sx={{ mt: 0.5 }}>
                      {formatPercentage(pnlSummary.pnl_percent)}
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 0.5 }}
                    >
                      Active Positions
                    </Typography>
                    <Typography variant="h5" fontWeight={700}>
                      {pnlSummary.active_positions_count}
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 0.5 }}
                    >
                      Total Investment
                    </Typography>
                    <Typography variant="h5" fontWeight={700}>
                      {formatCurrency(pnlSummary.total_investment)}
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 0.5 }}
                    >
                      Available Capital
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight={700}
                      color="primary.main"
                    >
                      {formatCurrency(capitalData.total_free_margin)}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Live Stock Activity Chart - Per Stock Visualization */}
        <StockActivityChart
          stockActivityStats={stockActivityStats}
          showLiveActivity={showLiveActivity}
          setShowLiveActivity={setShowLiveActivity}
        />

        {/* Keep collapsed OLD timeline for reference - will remove later */}
        {false && activityFeed.length > 0 && (
          <Grid item xs={12}>
            <Card elevation={2}>
              <CardContent>
                <Collapse in={false}>
                  <Box sx={{ mt: 2, position: "relative" }}>
                    {activityFeed.length === 0 ? (
                      <Alert severity="info" sx={{ borderRadius: 2 }}>
                        No recent activity. The timeline will show trades, signals, and system events in real-time.
                      </Alert>
                    ) : (
                      <Box sx={{ position: "relative", pl: 2 }}>
                        {/* Vertical Timeline Line */}
                        <Box
                          sx={{
                            position: "absolute",
                            left: "29px",
                            top: "20px",
                            bottom: "20px",
                            width: "2px",
                            bgcolor: "divider",
                          }}
                        />

                        {/* Timeline Items */}
                        <Stack spacing={2.5}>
                          {activityFeed.map((activity, index) => {
                            const getIcon = () => {
                              if (activity.type === "trade_executed" || activity.type === "position_created") {
                                return <CheckCircleIcon />;
                              } else if (activity.type === "position_closed") {
                                return activity.severity === "success" ? <TrendingUpIcon /> : <TrendingDownIcon />;
                              } else if (activity.type === "signal") {
                                return <SignalIcon />;
                              } else if (activity.severity === "error") {
                                return <ErrorIcon />;
                              } else if (activity.severity === "warning") {
                                return <WarningIcon />;
                              } else {
                                return <InfoIcon />;
                              }
                            };

                            const getColor = () => {
                              if (activity.severity === "success") return "success.main";
                              if (activity.severity === "error") return "error.main";
                              if (activity.severity === "warning") return "warning.main";
                              return "info.main";
                            };

                            return (
                              <Box
                                key={activity.id}
                                sx={{
                                  display: "flex",
                                  gap: 2,
                                  position: "relative",
                                  animation: index === 0 ? "fadeSlideIn 0.5s ease-out" : "none",
                                  "@keyframes fadeSlideIn": {
                                    from: {
                                      opacity: 0,
                                      transform: "translateY(-10px)",
                                    },
                                    to: {
                                      opacity: 1,
                                      transform: "translateY(0)",
                                    },
                                  },
                                }}
                              >
                                {/* Timeline Icon */}
                                <Box
                                  sx={{
                                    width: 40,
                                    height: 40,
                                    borderRadius: "50%",
                                    bgcolor: "background.paper",
                                    border: 2,
                                    borderColor: getColor(),
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    flexShrink: 0,
                                    zIndex: 1,
                                    color: getColor(),
                                  }}
                                >
                                  {getIcon()}
                                </Box>

                                {/* Activity Card */}
                                <Box
                                  sx={{
                                    flex: 1,
                                    bgcolor: "background.default",
                                    borderRadius: 2,
                                    p: 2,
                                    border: 1,
                                    borderColor: "divider",
                                    transition: "all 0.2s",
                                    "&:hover": {
                                      borderColor: getColor(),
                                      boxShadow: `0 2px 8px ${getColor()}20`,
                                      transform: "translateX(4px)",
                                    },
                                  }}
                                >
                                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 0.5 }}>
                                    <Typography variant="body1" fontWeight={600}>
                                      {activity.message}
                                    </Typography>
                                    <Typography
                                      variant="caption"
                                      sx={{
                                        fontFamily: "monospace",
                                        bgcolor: "background.paper",
                                        px: 1,
                                        py: 0.5,
                                        borderRadius: 1,
                                        border: 1,
                                        borderColor: "divider",
                                      }}
                                    >
                                      {new Date(activity.timestamp).toLocaleTimeString("en-IN", {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                        second: "2-digit",
                                      })}
                                    </Typography>
                                  </Stack>
                                  <Typography variant="body2" color="text.secondary">
                                    {activity.details}
                                  </Typography>
                                  <Box sx={{ mt: 1 }}>
                                    <Chip
                                      label={
                                        activity.severity === "success"
                                          ? "Success"
                                          : activity.severity === "error"
                                          ? "Error"
                                          : activity.severity === "warning"
                                          ? "Warning"
                                          : "Info"
                                      }
                                      size="small"
                                      color={
                                        activity.severity === "success"
                                          ? "success"
                                          : activity.severity === "error"
                                          ? "error"
                                          : activity.severity === "warning"
                                          ? "warning"
                                          : "info"
                                      }
                                    />
                                  </Box>
                                </Box>
                              </Box>
                            );
                          })}
                        </Stack>
                      </Box>
                    )}
                  </Box>
                </Collapse>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Trading Settings */}
        <Grid item xs={12}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" fontWeight={600} sx={{ mb: 2.5 }}>
                Trading Settings
              </Typography>

              <Grid container spacing={2.5}>
                {/* Trading Mode */}
                <Grid item xs={12} sm={6}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                      border:
                        tradingMode === "live" ? "2px solid" : "1px solid",
                      borderColor:
                        tradingMode === "live" ? "error.main" : "divider",
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 1 }}
                    >
                      Trading Mode
                    </Typography>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={tradingMode === "live"}
                          onChange={handleTradingModeToggle}
                          color="error"
                        />
                      }
                      label={
                        <Typography variant="body2" fontWeight={500}>
                          {tradingMode === "paper"
                            ? "Paper Trading"
                            : "Live Trading"}
                        </Typography>
                      }
                    />
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mt: 0.5 }}
                    >
                      {tradingMode === "paper"
                        ? "Virtual ₹10 lakhs - No real money"
                        : "⚠️ Real money trading - Actual broker API"}
                    </Typography>
                  </Box>
                </Grid>

                {/* Execution Mode */}
                <Grid item xs={12} sm={6}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 1 }}
                    >
                      Execution Mode
                    </Typography>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={executionMode === "multi_demat"}
                          onChange={async (e) => {
                            const newMode = e.target.checked
                              ? "multi_demat"
                              : "single_demat";
                            try {
                              const response = await api.post(
                                `/v1/trading/execution/user-trading-preferences?trading_mode=${tradingMode}&execution_mode=${newMode}`
                              );
                              if (response.data.success) {
                                setExecutionMode(newMode);
                              }
                            } catch (err) {
                              console.error(
                                "Error updating execution mode:",
                                err
                              );
                            }
                          }}
                          color="primary"
                        />
                      }
                      label={
                        <Typography variant="body2" fontWeight={500}>
                          {executionMode === "multi_demat"
                            ? "Multi-Demat"
                            : "Single-Demat"}
                        </Typography>
                      }
                    />
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mt: 0.5 }}
                    >
                      {executionMode === "multi_demat"
                        ? "Distribute across all active demats"
                        : "Execute on default demat only"}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Auto-Trading Status Indicator */}
              <Box
                sx={{
                  mt: 2.5,
                  p: 2,
                  bgcolor: autoTradingRunning ? "success.50" : "grey.50",
                  borderRadius: 1,
                }}
              >
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: "50%",
                      bgcolor: autoTradingRunning ? "success.main" : "grey.400",
                      animation: autoTradingRunning
                        ? "pulse 2s infinite"
                        : "none",
                      "@keyframes pulse": {
                        "0%, 100%": { opacity: 1 },
                        "50%": { opacity: 0.5 },
                      },
                    }}
                  />
                  <Typography
                    variant="body2"
                    fontWeight={600}
                    color={
                      autoTradingRunning ? "success.main" : "text.secondary"
                    }
                  >
                    {autoTradingRunning
                      ? `Auto-Trading Active - Monitoring ${selectedStocks.length} stocks`
                      : "Auto-Trading will start automatically when stocks are selected"}
                  </Typography>
                </Stack>
                {autoTradingRunning && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mt: 1, ml: 3 }}
                  >
                    Strategy running on live data • Trades execute automatically
                    on valid signals • Real-time PnL tracking active
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Capital Overview */}
        <Grid item xs={12}>
          <Card elevation={2}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ mb: 2.5 }}
              >
                <Typography variant="h6" fontWeight={600}>
                  Capital Overview
                </Typography>
                <Chip
                  label={`${capitalData.active_demats || 0} Active Demat${
                    (capitalData.active_demats || 0) !== 1 ? "s" : ""
                  }`}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              </Stack>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 0.5 }}
                    >
                      Total Capital
                    </Typography>
                    <Typography variant="h5" fontWeight={700}>
                      {formatCurrency(capitalData.total_available_capital || 0)}
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 0.5 }}
                    >
                      Used Margin
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight={700}
                      color="error.main"
                    >
                      {formatCurrency(capitalData.total_used_margin || 0)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {capitalData.capital_utilization_percent?.toFixed(1) || 0}
                      % utilized
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 0.5 }}
                    >
                      Free Margin
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight={700}
                      color="success.main"
                    >
                      {formatCurrency(capitalData.total_free_margin || 0)}
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: "background.default",
                      borderRadius: 1,
                    }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mb: 0.5 }}
                    >
                      Max Per Trade
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight={700}
                      color="primary.main"
                    >
                      {formatCurrency(capitalData.max_trade_allocation || 0)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      20% of total
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Per-Demat Breakdown - Collapsible */}
              {capitalData.demats && capitalData.demats.length > 0 && (
                <Box sx={{ mt: 2.5 }}>
                  <Button
                    size="small"
                    onClick={() =>
                      setShowCapitalBreakdown(!showCapitalBreakdown)
                    }
                    endIcon={
                      showCapitalBreakdown ? (
                        <ExpandLessIcon />
                      ) : (
                        <ExpandMoreIcon />
                      )
                    }
                    sx={{ mb: showCapitalBreakdown ? 1.5 : 0 }}
                  >
                    Demat Breakdown
                  </Button>
                  <Collapse in={showCapitalBreakdown}>
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Broker</TableCell>
                            <TableCell align="right">Available</TableCell>
                            <TableCell align="right">Used</TableCell>
                            <TableCell align="right">Free</TableCell>
                            <TableCell align="right">Utilization</TableCell>
                            <TableCell align="center">Status</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {capitalData.demats.map((demat, idx) => (
                            <TableRow key={idx}>
                              <TableCell>
                                <Typography variant="body2" fontWeight={600}>
                                  {demat.broker_name?.toUpperCase() || "N/A"}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                {formatCurrency(demat.available_margin || 0)}
                              </TableCell>
                              <TableCell align="right">
                                {formatCurrency(demat.used_margin || 0)}
                              </TableCell>
                              <TableCell align="right">
                                <Typography
                                  variant="body2"
                                  fontWeight={600}
                                  color={
                                    demat.free_margin > 0
                                      ? "success.main"
                                      : "error.main"
                                  }
                                >
                                  {formatCurrency(demat.free_margin || 0)}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Stack
                                  direction="row"
                                  alignItems="center"
                                  spacing={1}
                                  justifyContent="flex-end"
                                >
                                  <LinearProgress
                                    variant="determinate"
                                    value={Math.min(
                                      demat.utilization_percent || 0,
                                      100
                                    )}
                                    sx={{ width: 60 }}
                                    color={
                                      (demat.utilization_percent || 0) > 80
                                        ? "error"
                                        : (demat.utilization_percent || 0) > 50
                                        ? "warning"
                                        : "success"
                                    }
                                  />
                                  <Typography variant="caption">
                                    {(demat.utilization_percent || 0).toFixed(
                                      0
                                    )}
                                    %
                                  </Typography>
                                </Stack>
                              </TableCell>
                              <TableCell align="center">
                                <Chip
                                  label={
                                    demat.token_valid ? "Active" : "Expired"
                                  }
                                  color={
                                    demat.token_valid ? "success" : "error"
                                  }
                                  size="small"
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Collapse>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Execution Results Summary */}
        {executionResults &&
          executionResults.execution_mode === "multi_demat" && (
            <Grid item xs={12}>
              <Card elevation={2}>
                <CardContent>
                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ mb: 2.5 }}
                  >
                    <Typography variant="h6" fontWeight={600}>
                      Execution Results
                    </Typography>
                    <Chip
                      label={`${(
                        (executionResults.successful_executions /
                          executionResults.total_selections) *
                        100
                      ).toFixed(0)}% Success Rate`}
                      color="success"
                      size="small"
                    />
                  </Stack>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: "background.default",
                          borderRadius: 1,
                        }}
                      >
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mb: 0.5 }}
                        >
                          Total Trades
                        </Typography>
                        <Typography variant="h5" fontWeight={700}>
                          {executionResults.successful_executions}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: "background.default",
                          borderRadius: 1,
                        }}
                      >
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mb: 0.5 }}
                        >
                          Capital Allocated
                        </Typography>
                        <Typography
                          variant="h5"
                          fontWeight={700}
                          color="primary.main"
                        >
                          {formatCurrency(
                            executionResults.total_allocated_capital
                          )}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: "background.default",
                          borderRadius: 1,
                        }}
                      >
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mb: 0.5 }}
                        >
                          Total Quantity
                        </Typography>
                        <Typography variant="h5" fontWeight={700}>
                          {executionResults.total_quantity}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: "background.default",
                          borderRadius: 1,
                        }}
                      >
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mb: 0.5 }}
                        >
                          Stocks Executed
                        </Typography>
                        <Typography variant="h5" fontWeight={700}>
                          {executionResults.executions?.length || 0}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  {/* Per-Stock Execution Breakdown - Collapsible */}
                  {executionResults.executions &&
                    executionResults.executions.length > 0 && (
                      <Box sx={{ mt: 2.5 }}>
                        <Button
                          size="small"
                          onClick={() =>
                            setShowExecutionDetails(!showExecutionDetails)
                          }
                          endIcon={
                            showExecutionDetails ? (
                              <ExpandLessIcon />
                            ) : (
                              <ExpandMoreIcon />
                            )
                          }
                          sx={{ mb: showExecutionDetails ? 1.5 : 0 }}
                        >
                          Execution Details
                        </Button>
                        <Collapse in={showExecutionDetails}>
                          <TableContainer component={Paper} variant="outlined">
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Stock</TableCell>
                                  <TableCell>Demats Used</TableCell>
                                  <TableCell align="right">Capital</TableCell>
                                  <TableCell align="right">Quantity</TableCell>
                                  <TableCell align="center">Status</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {executionResults.executions.map(
                                  (exec, idx) => (
                                    <TableRow key={idx}>
                                      <TableCell>
                                        <Typography
                                          variant="body2"
                                          fontWeight={600}
                                        >
                                          {exec.symbol}
                                        </Typography>
                                      </TableCell>
                                      <TableCell>
                                        <Chip
                                          label={`${exec.successful_executions}/${exec.total_demats}`}
                                          color={
                                            exec.successful_executions > 0
                                              ? "success"
                                              : "error"
                                          }
                                          size="small"
                                        />
                                      </TableCell>
                                      <TableCell align="right">
                                        {formatCurrency(
                                          exec.total_allocated_capital || 0
                                        )}
                                      </TableCell>
                                      <TableCell align="right">
                                        {exec.total_quantity || 0}
                                      </TableCell>
                                      <TableCell align="center">
                                        <Chip
                                          label={
                                            exec.success ? "Success" : "Failed"
                                          }
                                          color={
                                            exec.success ? "success" : "error"
                                          }
                                          size="small"
                                        />
                                      </TableCell>
                                    </TableRow>
                                  )
                                )}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </Collapse>
                      </Box>
                    )}
                </CardContent>
              </Card>
            </Grid>
          )}

        {/* Tabbed Content */}
        <Grid item xs={12}>
          <Card elevation={2}>
            <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
              <Tabs
                value={activeTab}
                onChange={(e, v) => setActiveTab(v)}
                variant="fullWidth"
              >
                <Tab
                  label="Active Positions"
                  icon={<TimelineIcon />}
                  iconPosition="start"
                  sx={{ minHeight: 64 }}
                />
                <Tab
                  label="Selected Stocks"
                  icon={<ShowChartIcon />}
                  iconPosition="start"
                  sx={{ minHeight: 64 }}
                />
                <Tab
                  label="Trade History"
                  icon={<AssessmentIcon />}
                  iconPosition="start"
                  sx={{ minHeight: 64 }}
                />
                {executionResults &&
                  executionResults.execution_mode === "multi_demat" && (
                    <Tab
                      label="Demat Details"
                      icon={<AccountBalanceIcon />}
                      iconPosition="start"
                      sx={{ minHeight: 64 }}
                    />
                  )}
              </Tabs>
            </Box>

            {/* Active Positions Tab */}
            {activeTab === 0 && (
              <CardContent sx={{ p: 3 }}>
                <Stack
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  sx={{ mb: 2.5 }}
                >
                  <Typography variant="h6" fontWeight={600}>
                    Active Positions ({activePositions.length})
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Live Updates Every Second
                  </Typography>
                </Stack>

                {activePositions.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 600 }}>Broker</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Symbol</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Mode</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Entry
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Current
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Qty
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Lots
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Investment
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            P&L
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            P&L %
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            SL
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Target
                          </TableCell>
                          <TableCell align="center" sx={{ fontWeight: 600 }}>
                            Trailing
                          </TableCell>
                          <TableCell align="center" sx={{ fontWeight: 600 }}>
                            Time
                          </TableCell>
                          <TableCell align="center" sx={{ fontWeight: 600 }}>
                            Action
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {activePositions.map((position) => {
                          const duration = position.entry_time
                            ? Math.floor(
                                (new Date() - new Date(position.entry_time)) /
                                  (1000 * 60)
                              )
                            : 0;

                          return (
                            <TableRow key={position.position_id} hover>
                              <TableCell>
                                <Chip
                                  label={(position.broker_name || "N/A").toUpperCase()}
                                  size="small"
                                  color={position.broker_name ? "primary" : "default"}
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" fontWeight={600}>
                                  {position.symbol}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  {position.trade_id}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={position.signal_type}
                                  size="small"
                                  color={
                                    position.signal_type?.includes("CE")
                                      ? "success"
                                      : "error"
                                  }
                                />
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={(position.trading_mode || "paper").toUpperCase()}
                                  size="small"
                                  color={position.trading_mode === "live" ? "error" : "info"}
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {formatCurrency(position.entry_price)}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Stack
                                  direction="row"
                                  alignItems="center"
                                  justifyContent="flex-end"
                                  spacing={0.5}
                                >
                                  <Typography variant="body2">
                                    {formatCurrency(position.current_price)}
                                  </Typography>
                                  {position.current_price >
                                  position.entry_price ? (
                                    <TrendingUpIcon
                                      color="success"
                                      fontSize="small"
                                    />
                                  ) : (
                                    <TrendingDownIcon
                                      color="error"
                                      fontSize="small"
                                    />
                                  )}
                                </Stack>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {position.quantity}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {position.lots_traded || 0}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2" fontWeight={600}>
                                  {formatCurrency(position.total_investment || 0)}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography
                                  variant="body2"
                                  color={
                                    position.current_pnl >= 0
                                      ? "success.main"
                                      : "error.main"
                                  }
                                  fontWeight={600}
                                >
                                  {formatCurrency(position.current_pnl)}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Chip
                                  label={formatPercentage(
                                    position.current_pnl_percentage
                                  )}
                                  color={
                                    position.current_pnl_percentage >= 0
                                      ? "success"
                                      : "error"
                                  }
                                  size="small"
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {formatCurrency(position.stop_loss)}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {formatCurrency(position.target)}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Chip
                                  label={
                                    position.trailing_stop_active ? "ON" : "OFF"
                                  }
                                  color={
                                    position.trailing_stop_active
                                      ? "success"
                                      : "default"
                                  }
                                  size="small"
                                  sx={{ minWidth: 50 }}
                                />
                              </TableCell>
                              <TableCell align="center">
                                <Typography variant="body2">
                                  {duration}m
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Tooltip title="Close Position">
                                  <IconButton
                                    color="error"
                                    size="small"
                                    onClick={() =>
                                      handleClosePosition(position.position_id)
                                    }
                                  >
                                    <CloseIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No active positions. Execute trades to see live positions
                    here.
                  </Alert>
                )}
              </CardContent>
            )}

            {/* Selected Stocks Tab */}
            {activeTab === 1 && (
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={600} sx={{ mb: 2.5 }}>
                  Selected Stocks ({selectedStocks.length})
                </Typography>

                {/* Loading indicator for stocks */}
                {stocksLoading && (
                  <Box sx={{ textAlign: "center", py: 4 }}>
                    <LinearProgress sx={{ mb: 2 }} />
                    <Typography variant="body2" color="text.secondary">
                      Loading selected stocks...
                    </Typography>
                  </Box>
                )}

                {!stocksLoading && selectedStocks.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 600 }}>Symbol</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Instrument</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Strike
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Expiry
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            LTP
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Change %
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Lot Size
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Lots to Trade
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Total Qty
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Capital Required
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Score
                          </TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>
                            Status
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedStocks.map((stock, idx) => {
                          const lotsToTrade = stock.position_size_lots || 1;
                          const lotSize = stock.lot_size || 0;
                          const totalQty = lotsToTrade * lotSize;
                          const ltp = stock.live_price || stock.entry_price || 0;
                          const capitalRequired = ltp * totalQty;

                          return (
                            <TableRow key={idx} hover>
                              <TableCell>
                                <Typography variant="body2" fontWeight={600}>
                                  {stock.symbol}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  {stock.sector || "N/A"}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                                  {stock.instrument_key ? stock.instrument_key.split("|")[1] : "N/A"}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={stock.option_type || "N/A"}
                                  color={
                                    stock.option_type === "CE"
                                      ? "success"
                                      : "error"
                                  }
                                  size="small"
                                  sx={{ minWidth: 40 }}
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2" fontWeight={600}>
                                  {formatCurrency(stock.strike_price || 0)}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {stock.expiry_date || "N/A"}
                                </Typography>
                              </TableCell>
                            <TableCell align="right">
                              <Typography
                                variant="body2"
                                fontWeight={600}
                                color="primary"
                              >
                                {formatCurrency(
                                  stock.live_price || stock.premium || 0
                                )}
                              </Typography>
                              {stock.live_price && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  At sel: {formatCurrency(stock.premium || 0)}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell align="right">
                              {stock.price_change_percent !== undefined &&
                              stock.price_change_percent !== null ? (
                                <Chip
                                  label={`${
                                    stock.price_change_percent >= 0 ? "+" : ""
                                  }${stock.price_change_percent.toFixed(2)}%`}
                                  color={
                                    stock.price_change_percent >= 0
                                      ? "success"
                                      : "error"
                                  }
                                  size="small"
                                />
                              ) : (
                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                >
                                  -
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" fontWeight={600}>
                                {lotSize}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" fontWeight={700} color="primary">
                                {lotsToTrade}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" fontWeight={600}>
                                {totalQty}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" fontWeight={700} color="error.main">
                                {formatCurrency(capitalRequired)}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                @ {formatCurrency(ltp)}/unit
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={`${(
                                  (stock.selection_score || 0) * 100
                                ).toFixed(0)}%`}
                                color={
                                  (stock.selection_score || 0) >= 0.8
                                    ? "success"
                                    : "warning"
                                }
                                size="small"
                              />
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={stock.trade_status || "SELECTED"}
                                size="small"
                                color={
                                  stock.trade_status === "TRADED" ? "success" :
                                  stock.trade_status === "IN_POSITION" ? "warning" :
                                  "info"
                                }
                              />
                            </TableCell>
                          </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : !stocksLoading ? (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No stocks selected yet. Stock selection runs automatically
                    during market hours (9:00-9:15 AM pre-open).
                  </Alert>
                ) : null}
              </CardContent>
            )}

            {/* Trade History Tab */}
            {activeTab === 2 && (
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={600} sx={{ mb: 2.5 }}>
                  Trade History ({tradeHistory.length})
                </Typography>

                {tradeHistory.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 600 }}>Broker</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Symbol</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Entry Date
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Entry Time
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Entry Price
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Exit Date
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Exit Time
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Exit Price
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Quantity
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Lots
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            Investment
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            P&L
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            P&L %
                          </TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>
                            Mode
                          </TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>
                            Exit Reason
                          </TableCell>
                          <TableCell align="center" sx={{ fontWeight: 600 }}>
                            Duration
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {tradeHistory.map((trade, idx) => (
                          <TableRow key={idx} hover>
                            <TableCell>
                              <Chip
                                label={(trade.broker_name || "N/A").toUpperCase()}
                                size="small"
                                color={trade.broker_name ? "primary" : "default"}
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" fontWeight={600}>
                                {trade.symbol}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={trade.signal_type}
                                size="small"
                                color={
                                  trade.signal_type?.includes("CE")
                                    ? "success"
                                    : "error"
                                }
                              />
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {trade.entry_date || "N/A"}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {trade.entry_time_str || "N/A"}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {formatCurrency(trade.entry_price)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {trade.exit_date || "N/A"}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {trade.exit_time_str || "N/A"}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {formatCurrency(trade.exit_price)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {trade.quantity || 0}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2">
                                {trade.lots_traded || 0}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" fontWeight={600}>
                                {formatCurrency(trade.total_investment)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography
                                variant="body2"
                                color={
                                  trade.net_pnl >= 0
                                    ? "success.main"
                                    : "error.main"
                                }
                                fontWeight={600}
                              >
                                {formatCurrency(trade.net_pnl)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={formatPercentage(trade.pnl_percentage)}
                                color={
                                  trade.pnl_percentage >= 0
                                    ? "success"
                                    : "error"
                                }
                                size="small"
                              />
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={(trade.trading_mode || "paper").toUpperCase()}
                                size="small"
                                color={trade.trading_mode === "live" ? "error" : "info"}
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {trade.exit_reason}
                              </Typography>
                            </TableCell>
                            <TableCell align="center">
                              <Typography variant="body2">
                                {trade.duration_minutes
                                  ? trade.duration_minutes + "m"
                                  : "N/A"}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No trade history available.
                  </Alert>
                )}
              </CardContent>
            )}

            {/* Per-Demat Details Tab */}
            {activeTab === 3 &&
              executionResults &&
              executionResults.execution_mode === "multi_demat" && (
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" fontWeight={600} sx={{ mb: 2.5 }}>
                    Per-Demat Execution Details
                  </Typography>

                  {executionResults.executions &&
                  executionResults.executions.length > 0 ? (
                    executionResults.executions.map(
                      (stockExec, stockIdx) =>
                        stockExec.demat_executions &&
                        stockExec.demat_executions.length > 0 && (
                          <Box key={stockIdx} sx={{ mb: 3 }}>
                            <Typography
                              variant="subtitle1"
                              fontWeight={600}
                              sx={{ mb: 1.5 }}
                            >
                              {stockExec.symbol}
                              <Chip
                                label={`${stockExec.successful_executions} Demat(s)`}
                                size="small"
                                color="primary"
                                sx={{ ml: 1 }}
                              />
                            </Typography>
                            <TableContainer
                              component={Paper}
                              variant="outlined"
                            >
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell sx={{ fontWeight: 600 }}>
                                      Broker
                                    </TableCell>
                                    <TableCell
                                      align="right"
                                      sx={{ fontWeight: 600 }}
                                    >
                                      Lots
                                    </TableCell>
                                    <TableCell
                                      align="right"
                                      sx={{ fontWeight: 600 }}
                                    >
                                      Qty
                                    </TableCell>
                                    <TableCell
                                      align="right"
                                      sx={{ fontWeight: 600 }}
                                    >
                                      Entry
                                    </TableCell>
                                    <TableCell
                                      align="right"
                                      sx={{ fontWeight: 600 }}
                                    >
                                      Capital
                                    </TableCell>
                                    <TableCell sx={{ fontWeight: 600 }}>
                                      Trade ID
                                    </TableCell>
                                    <TableCell sx={{ fontWeight: 600 }}>
                                      Status
                                    </TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {stockExec.demat_executions.map(
                                    (dematExec, dematIdx) => (
                                      <TableRow key={dematIdx} hover>
                                        <TableCell>
                                          <Typography
                                            variant="body2"
                                            fontWeight={600}
                                          >
                                            {dematExec.broker_name?.toUpperCase() ||
                                              "N/A"}
                                          </Typography>
                                        </TableCell>
                                        <TableCell align="right">
                                          <Typography variant="body2">
                                            {dematExec.lots || 0}
                                          </Typography>
                                        </TableCell>
                                        <TableCell align="right">
                                          <Typography variant="body2">
                                            {dematExec.quantity || 0}
                                          </Typography>
                                        </TableCell>
                                        <TableCell align="right">
                                          <Typography variant="body2">
                                            {formatCurrency(
                                              dematExec.entry_price || 0
                                            )}
                                          </Typography>
                                        </TableCell>
                                        <TableCell align="right">
                                          <Typography
                                            variant="body2"
                                            fontWeight={600}
                                            color="primary.main"
                                          >
                                            {formatCurrency(
                                              dematExec.allocated_capital || 0
                                            )}
                                          </Typography>
                                        </TableCell>
                                        <TableCell>
                                          <Typography
                                            variant="caption"
                                            sx={{ fontFamily: "monospace" }}
                                          >
                                            {dematExec.trade_id || "N/A"}
                                          </Typography>
                                        </TableCell>
                                        <TableCell>
                                          <Chip
                                            label={
                                              dematExec.success
                                                ? "Success"
                                                : "Failed"
                                            }
                                            color={
                                              dematExec.success
                                                ? "success"
                                                : "error"
                                            }
                                            size="small"
                                          />
                                          {!dematExec.success &&
                                            dematExec.error && (
                                              <Typography
                                                variant="caption"
                                                color="error.main"
                                                display="block"
                                                sx={{ mt: 0.5 }}
                                              >
                                                {dematExec.error}
                                              </Typography>
                                            )}
                                        </TableCell>
                                      </TableRow>
                                    )
                                  )}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </Box>
                        )
                    )
                  ) : (
                    <Alert severity="info" sx={{ mt: 2 }}>
                      No per-demat execution details available.
                    </Alert>
                  )}
                </CardContent>
              )}
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default AutoTradingPage;
