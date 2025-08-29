import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
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
  Badge,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from "@mui/material";
import {
  AccountBalance as AccountBalanceIcon,
  ShowChart as ShowChartIcon,
  Delete as DeleteIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  Visibility as VisibilityIcon,
  Notifications as NotificationsIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  AttachMoney as AttachMoneyIcon,
  Speed as SpeedIcon,
} from "@mui/icons-material";
import api from "../services/api";
import io from "socket.io-client";

const AutoTradingPage = () => {
  // State management
  const [tradingSession, setTradingSession] = useState(null);
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [activeTrades, setActiveTrades] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [activeTab, setActiveTab] = useState(0);

  // WebSocket ref (stable, not in deps)
  const socketRef = useRef(null);

  // Real-time data state
  const [realTimeData, setRealTimeData] = useState({
    totalPnL: 0,
    dailyPnL: 0,
    winRate: 0,
    totalTrades: 0,
    activeTrades: 0,
    positionsValue: 0,
  });

  // Configuration state
  const [config, setConfig] = useState({
    mode: "PAPER_TRADING",
    max_risk_per_trade: 0, // ensure defaults to avoid render errors
    max_daily_loss: 0,
    max_positions: 0,
  });

  // Capital state
  const [capitalData, setCapitalData] = useState({
    total_capital: 500000,
    available_capital: 500000,
    used_capital: 0,
    trading_mode: "PAPER_TRADING",
  });

  // ---------- Data fetchers (memoized) ----------
  const fetchTradingSession = useCallback(async () => {
    try {
      const response = await api.get("/v1/auto-trading/session-status");
      setTradingSession(response.data);
    } catch (err) {
      console.error("Error fetching trading session:", err);
      setError("Failed to load trading session status");
    }
  }, []);

  const fetchSelectedStocks = useCallback(async () => {
    try {
      const response = await api.get("/v1/auto-trading/selected-stocks");
      if (response.data && response.data.stocks) {
        setSelectedStocks(response.data.stocks);
        setTradingSession(response.data.trading_session);
      }
    } catch (err) {
      console.error("Error fetching selected stocks:", err);
    }
  }, []);

  const fetchActiveTrades = useCallback(async () => {
    try {
      const response = await api.get("/v1/auto-trading/active-trades");
      const trades = response.data.active_trades || [];

      const processedTrades = trades.map((trade) => ({
        id: trade.id || `trade_${Date.now()}_${Math.random()}`,
        symbol: trade.symbol || "UNKNOWN",
        option_type: trade.option_type || "CE",
        entry_price: Number(trade.entry_price) || 0,
        current_price: Number(trade.current_price) || 0,
        quantity: Number(trade.quantity) || 0,
        lot_size: Number(trade.lot_size) || 1,
        pnl: Number(trade.pnl) || 0,
        pnl_percentage: Number(trade.pnl_percentage) || 0,
        stop_loss: Number(trade.stop_loss) || 0,
        target: Number(trade.target) || 0,
        entry_time: trade.entry_time || new Date().toISOString(),
        status: trade.status || "ACTIVE",
      }));

      setActiveTrades(processedTrades);
    } catch (err) {
      console.error("Error fetching active trades:", err);
      setActiveTrades([]);
    }
  }, []);

  const fetchTradeHistory = useCallback(async () => {
    try {
      const response = await api.get("/v1/auto-trading/trading-history?days=1");
      setTradeHistory(response.data.trades || []);
    } catch (err) {
      console.error("Error fetching trade history:", err);
    }
  }, []);

  const fetchRealTimeData = useCallback(async () => {
    try {
      const response = await api.get("/v1/auto-trading/system-stats");
      if (response.data.success) {
        setRealTimeData({
          totalPnL: response.data.data.totalReturn || 0,
          dailyPnL: response.data.data.dailyPnL || 0,
          winRate:
            response.data.data.winRate || response.data.data.successRate || 0,
          totalTrades: response.data.data.totalTrades || 0,
          activeTrades: response.data.data.activeTrades || 0,
          positionsValue: response.data.data.portfolioValue || 0,
        });
      } else {
        setRealTimeData({
          totalPnL: 0,
          dailyPnL: 0,
          winRate: 0,
          totalTrades: 0,
          activeTrades: 0,
          positionsValue: 0,
        });
      }
    } catch (err) {
      console.error("Error fetching real-time data:", err);
      setRealTimeData({
        totalPnL: 0,
        dailyPnL: 0,
        winRate: 0,
        totalTrades: 0,
        activeTrades: 0,
        positionsValue: 0,
      });
    }
  }, []);

  const fetchCapitalData = useCallback(async () => {
    try {
      const response = await api.get("/v1/auto-trading/user-capital");
      if (response.data.success) {
        setCapitalData(response.data);
        setConfig((prev) => ({
          ...prev,
          mode: response.data.trading_mode,
        }));
      }
    } catch (err) {
      console.error("Error fetching capital data:", err);
    }
  }, []);

  // ---------- WebSocket (memoized) ----------
  const initializeWebSocket = useCallback(() => {
    try {
      const s = io(`${process.env.REACT_APP_API_URL}`, {
        transports: ["websocket"],
      });

      s.on("connect", () => {
        console.log("Connected to WebSocket for auto-trading updates");
        s.emit("join_auto_trading_room");
      });

      s.on("auto_trading_update", (data) => {
        if (data.type === "position_update") {
          fetchActiveTrades();
          fetchRealTimeData();
        } else if (data.type === "trade_executed") {
          setSuccess(`Trade executed: ${data.symbol} ${data.option_type}`);
          fetchActiveTrades();
          fetchTradeHistory();
        }
      });

      s.on("disconnect", () => {
        console.log("Disconnected from WebSocket");
      });

      socketRef.current = s;
    } catch (err) {
      console.error("WebSocket connection error:", err);
    }
  }, [fetchActiveTrades, fetchRealTimeData, fetchTradeHistory]);

  // ---------- Effects ----------
  // Load on mount
  useEffect(() => {
    fetchTradingSession();
    fetchSelectedStocks();
    fetchActiveTrades();
    fetchTradeHistory();
    fetchCapitalData();
    initializeWebSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, [
    fetchTradingSession,
    fetchSelectedStocks,
    fetchActiveTrades,
    fetchTradeHistory,
    fetchCapitalData,
    initializeWebSocket,
  ]);

  // Auto-refresh data every 5s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchRealTimeData();
      fetchActiveTrades();
      fetchCapitalData();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchRealTimeData, fetchActiveTrades, fetchCapitalData]);

  const handleKillSwitch = async (symbol) => {
    if (
      !window.confirm(
        `⚠️ Emergency Kill Switch\n\nThis will immediately close ALL positions for ${symbol} and deactivate it from trading.\n\nAre you sure you want to proceed?`
      )
    ) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.post(`/api/v1/auto-trading/kill-switch/${symbol}`);

      if (response.data.success) {
        setSuccess(
          `🚨 Kill switch activated for ${symbol}. ${
            response.data.positions_closed
          } position(s) closed. P&L: ${formatCurrency(response.data.total_pnl)}`
        );
        await fetchSelectedStocks();
        await fetchActiveTrades();
        await fetchRealTimeData();
      } else {
        throw new Error(response.data.message || "Kill switch failed");
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          `Failed to activate kill switch for ${symbol}`
      );
    } finally {
      setIsLoading(false);
    }
  };

  const removeSelectedStock = async (stockId) => {
    try {
      await api.delete(`/api/v1/auto-trading/selected-stocks/${stockId}`);
      await fetchSelectedStocks();
      setSuccess("Stock removed from selection");
    } catch (err) {
      setError("Failed to remove stock");
    }
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

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
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Auto Trading System
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Automated F&O trading with Fibonacci + EMA strategy, real-time P&L
          tracking, and intelligent risk management
        </Typography>
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

      {/* Loading indicator */}
      {isLoading && <LinearProgress sx={{ mb: 2 }} />}

      <Grid container spacing={3}>
        {/* Real-time Performance Metrics */}
        <Grid item xs={12}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography
                    variant="h6"
                    color={
                      realTimeData.dailyPnL >= 0 ? "success.main" : "error.main"
                    }
                  >
                    {formatCurrency(realTimeData.dailyPnL)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Daily P&L
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="h6" color="primary">
                    {Number(realTimeData.winRate || 0).toFixed(1)}%
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Win Rate
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="h6">
                    {realTimeData.totalTrades}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Total Trades
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Badge badgeContent={realTimeData.activeTrades} color="error">
                    <Typography variant="h6">
                      {realTimeData.activeTrades}
                    </Typography>
                  </Badge>
                  <Typography variant="body2" color="textSecondary">
                    Active Trades
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="h6">
                    {formatCurrency(realTimeData.positionsValue)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Position Value
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <Card>
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography
                    variant="h6"
                    color={
                      realTimeData.totalPnL >= 0 ? "success.main" : "error.main"
                    }
                  >
                    {formatCurrency(realTimeData.totalPnL)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Total P&L
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        {/* System Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <AccountBalanceIcon sx={{ mr: 1, verticalAlign: "middle" }} />
                Auto Trading System Status
              </Typography>

              <Box>
                <Chip label="AUTOMATIC MODE" color="primary" sx={{ mb: 2 }} />
                <Typography variant="body2" gutterBottom>
                  Trading Mode: {capitalData.trading_mode}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  Active Trades: {realTimeData.activeTrades}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  Trades Today: {realTimeData.totalTrades}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  Daily P&L: {formatCurrency(realTimeData.dailyPnL)}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  Selected Stocks: {selectedStocks.length}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 1, display: "block" }}
                >
                  💡 Trading executes automatically based on selected stocks and
                  Fibonacci signals
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Capital Information */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <AttachMoneyIcon sx={{ mr: 1, verticalAlign: "middle" }} />
                Trading Capital
              </Typography>

              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Mode:</Typography>
                  <Chip
                    label={capitalData.trading_mode}
                    color={
                      capitalData.trading_mode === "PAPER_TRADING"
                        ? "info"
                        : "success"
                    }
                    size="small"
                  />
                </Box>

                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Total Capital:</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {formatCurrency(capitalData.total_capital)}
                  </Typography>
                </Box>

                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Available:</Typography>
                  <Typography variant="body2" color="success.main">
                    {formatCurrency(capitalData.available_capital)}
                  </Typography>
                </Box>

                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Used:</Typography>
                  <Typography variant="body2" color="error.main">
                    {formatCurrency(capitalData.used_capital)}
                  </Typography>
                </Box>

                {capitalData.trading_mode === "LIVE_TRADING" &&
                  capitalData.broker_name && (
                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2">Broker:</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {capitalData.broker_name}
                      </Typography>
                    </Box>
                  )}

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  {capitalData.trading_mode === "PAPER_TRADING"
                    ? "💡 Using virtual money for safe testing"
                    : "⚠️ Using real money from your demat account"}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Trading Session Info (uses tradingSession state) */}
        {tradingSession && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Trading Session
                </Typography>

                <Box
                  sx={{ display: "flex", gap: 1, mb: 2, alignItems: "center" }}
                >
                  <Chip
                    label={tradingSession.is_active ? "ACTIVE" : "INACTIVE"}
                    color={tradingSession.is_active ? "success" : "default"}
                    size="small"
                  />
                  <Chip
                    label={tradingSession.trading_mode || "PAPER_TRADING"}
                    color={
                      tradingSession.trading_mode === "LIVE_TRADING"
                        ? "success"
                        : "info"
                    }
                    size="small"
                  />
                </Box>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    rowGap: 1,
                  }}
                >
                  <Typography variant="body2">
                    Active Trades:{" "}
                    <strong>{tradingSession.active_trades ?? 0}</strong>
                  </Typography>
                  <Typography variant="body2">
                    Trades Today:{" "}
                    <strong>{tradingSession.trades_executed_today ?? 0}</strong>
                  </Typography>
                  <Typography variant="body2">
                    Daily P&L:{" "}
                    <strong>
                      {formatCurrency(tradingSession.daily_pnl ?? 0)}
                    </strong>
                  </Typography>
                  <Typography variant="body2">
                    Selected Stocks:{" "}
                    <strong>{tradingSession.selected_stocks_count ?? 0}</strong>
                  </Typography>
                  <Typography variant="body2">
                    Session Date:{" "}
                    <strong>
                      {tradingSession.session_date
                        ? new Date(
                            tradingSession.session_date
                          ).toLocaleDateString()
                        : "—"}
                    </strong>
                  </Typography>
                  {tradingSession.session_id && (
                    <Typography variant="caption" color="text.secondary">
                      Session ID: {tradingSession.session_id}
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Tabbed Content Area */}
        <Grid item xs={12}>
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
              <Tabs value={activeTab} onChange={handleTabChange}>
                <Tab label="Selected Stocks" icon={<ShowChartIcon />} />
                <Tab label="Active Trades" icon={<TimelineIcon />} />
                <Tab label="Trade History" icon={<AssessmentIcon />} />
                <Tab label="Real-time Monitor" icon={<SpeedIcon />} />
              </Tabs>
            </Box>

            {/* Tab Panel 0: Stock Selection */}
            {activeTab === 0 && (
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 2,
                  }}
                >
                  <Typography variant="h6">
                    <ShowChartIcon sx={{ mr: 1, verticalAlign: "middle" }} />
                    Selected Stocks ({selectedStocks.length})
                  </Typography>
                </Box>

                {selectedStocks.length > 0 ? (
                  <TableContainer component={Paper} variant="outlined">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Option Type</TableCell>
                          <TableCell align="right">ATM Strike</TableCell>
                          <TableCell align="right">Selection Score</TableCell>
                          <TableCell align="right">Current Price</TableCell>
                          <TableCell align="right">Change %</TableCell>
                          <TableCell align="center">Selection Date</TableCell>
                          <TableCell align="center">Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedStocks.map((stock, index) => (
                          <TableRow key={stock.id || index}>
                            <TableCell>
                              <Typography variant="subtitle2" fontWeight="bold">
                                {stock.symbol}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="textSecondary"
                              >
                                {stock.sector}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={stock.option_type || "NEUTRAL"}
                                color={
                                  stock.option_type === "CE"
                                    ? "success"
                                    : stock.option_type === "PE"
                                    ? "error"
                                    : "default"
                                }
                                size="small"
                              />
                            </TableCell>
                            <TableCell align="right">
                              ₹{stock.atm_strike?.toFixed(2) || "N/A"}
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={`${(
                                  (stock.selection_score ?? 0) * 100
                                ).toFixed(1)}%`}
                                color={
                                  (stock.selection_score ?? 0) >= 0.8
                                    ? "success"
                                    : "warning"
                                }
                                size="small"
                              />
                            </TableCell>
                            <TableCell align="right">
                              ₹{stock.price_at_selection?.toFixed(2) || "N/A"}
                            </TableCell>
                            <TableCell align="right">
                              <Typography
                                color={
                                  (stock.change_percent ?? 0) >= 0
                                    ? "success.main"
                                    : "error.main"
                                }
                              >
                                {(stock.change_percent ?? 0) >= 0 ? "+" : ""}
                                {(stock.change_percent ?? 0).toFixed(2)}%
                              </Typography>
                            </TableCell>
                            <TableCell align="center">
                              {stock.selection_date
                                ? new Date(
                                    stock.selection_date
                                  ).toLocaleDateString()
                                : "N/A"}
                            </TableCell>
                            <TableCell align="center">
                              <Box
                                sx={{
                                  display: "flex",
                                  gap: 1,
                                  justifyContent: "center",
                                }}
                              >
                                {/* Kill Switch Button */}
                                <IconButton
                                  color="error"
                                  onClick={() => handleKillSwitch(stock.symbol)}
                                  disabled={isLoading}
                                  size="small"
                                  title={`Emergency Kill Switch for ${stock.symbol}`}
                                  sx={{
                                    bgcolor: "error.light",
                                    color: "white",
                                    "&:hover": {
                                      bgcolor: "error.main",
                                      transform: "scale(1.1)",
                                    },
                                    minWidth: "32px",
                                    height: "32px",
                                  }}
                                >
                                  <CancelIcon sx={{ fontSize: "18px" }} />
                                </IconButton>

                                {/* Remove from Selection Button */}
                                <IconButton
                                  color="warning"
                                  onClick={() => removeSelectedStock(stock.id)}
                                  disabled={isLoading}
                                  size="small"
                                  title={`Remove ${stock.symbol} from selection`}
                                >
                                  <DeleteIcon />
                                </IconButton>
                              </Box>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Alert severity="info">
                    No stocks selected yet. Click "Auto Select Stocks" to let
                    the system choose optimal stocks for trading.
                  </Alert>
                )}
              </CardContent>
            )}

            {/* Tab Panel 1: Active Trades */}
            {activeTab === 1 && (
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <TimelineIcon sx={{ mr: 1, verticalAlign: "middle" }} />
                  Active Trades ({activeTrades.length})
                </Typography>
                {activeTrades.length > 0 ? (
                  <TableContainer component={Paper} variant="outlined">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Type</TableCell>
                          <TableCell align="right">Entry Price</TableCell>
                          <TableCell align="right">Current Price</TableCell>
                          <TableCell align="right">P&L</TableCell>
                          <TableCell align="right">P&L %</TableCell>
                          <TableCell align="right">Stop Loss</TableCell>
                          <TableCell align="right">Target</TableCell>
                          <TableCell align="center">Entry Time</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {activeTrades.map((trade, index) => (
                          <TableRow key={trade.id || index}>
                            <TableCell>
                              <Typography variant="subtitle2" fontWeight="bold">
                                {trade.symbol}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={trade.option_type}
                                color={
                                  trade.option_type === "CE"
                                    ? "success"
                                    : "error"
                                }
                                size="small"
                              />
                            </TableCell>
                            <TableCell align="right">
                              ₹{trade.entry_price?.toFixed(2)}
                            </TableCell>
                            <TableCell align="right">
                              ₹{trade.current_price?.toFixed(2)}
                            </TableCell>
                            <TableCell align="right">
                              <Typography
                                color={
                                  trade.pnl >= 0 ? "success.main" : "error.main"
                                }
                              >
                                {formatCurrency(trade.pnl)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography
                                color={
                                  trade.pnl_percentage >= 0
                                    ? "success.main"
                                    : "error.main"
                                }
                              >
                                {formatPercentage(trade.pnl_percentage)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              ₹{trade.stop_loss?.toFixed(2)}
                            </TableCell>
                            <TableCell align="right">
                              ₹{trade.target?.toFixed(2)}
                            </TableCell>
                            <TableCell align="center">
                              {new Date(trade.entry_time).toLocaleTimeString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Alert severity="info">
                    No active trades. Start the trading session to see live
                    positions.
                  </Alert>
                )}
              </CardContent>
            )}

            {/* Tab Panel 2: Trade History */}
            {activeTab === 2 && (
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <AssessmentIcon sx={{ mr: 1, verticalAlign: "middle" }} />
                  Today's Trade History ({tradeHistory.length})
                </Typography>
                {tradeHistory.length > 0 ? (
                  <TableContainer component={Paper} variant="outlined">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Type</TableCell>
                          <TableCell align="right">Entry</TableCell>
                          <TableCell align="right">Exit</TableCell>
                          <TableCell align="right">P&L</TableCell>
                          <TableCell align="right">P&L %</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Exit Reason</TableCell>
                          <TableCell align="center">Duration</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {tradeHistory.map((trade, index) => (
                          <TableRow key={trade.id || index}>
                            <TableCell>{trade.symbol}</TableCell>
                            <TableCell>
                              <Chip
                                label={trade.option_type || trade.trade_type}
                                size="small"
                                color={
                                  (trade.option_type || trade.trade_type) ===
                                  "CE"
                                    ? "success"
                                    : "error"
                                }
                              />
                            </TableCell>
                            <TableCell align="right">
                              ₹{trade.entry_price?.toFixed(2)}
                            </TableCell>
                            <TableCell align="right">
                              ₹{trade.exit_price?.toFixed(2)}
                            </TableCell>
                            <TableCell align="right">
                              <Typography
                                color={
                                  trade.pnl >= 0 ? "success.main" : "error.main"
                                }
                              >
                                {formatCurrency(trade.pnl)}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography
                                color={
                                  trade.pnl_percentage >= 0
                                    ? "success.main"
                                    : "error.main"
                                }
                              >
                                {formatPercentage(trade.pnl_percentage)}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={trade.status}
                                color={
                                  trade.status === "CLOSED"
                                    ? "success"
                                    : "default"
                                }
                                size="small"
                                icon={
                                  trade.pnl >= 0 ? (
                                    <CheckCircleIcon />
                                  ) : (
                                    <CancelIcon />
                                  )
                                }
                              />
                            </TableCell>
                            <TableCell>{trade.exit_reason}</TableCell>
                            <TableCell align="center">
                              {trade.entry_time && trade.exit_time
                                ? Math.round(
                                    (new Date(trade.exit_time) -
                                      new Date(trade.entry_time)) /
                                      (1000 * 60)
                                  ) + "m"
                                : "N/A"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Alert severity="info">No trade history for today.</Alert>
                )}
              </CardContent>
            )}

            {/* Tab Panel 3: Real-time Monitor */}
            {activeTab === 3 && (
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <SpeedIcon sx={{ mr: 1, verticalAlign: "middle" }} />
                  Real-time Trading Monitor
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          Strategy Performance
                        </Typography>
                        <List>
                          <ListItem>
                            <ListItemIcon>
                              <AttachMoneyIcon />
                            </ListItemIcon>
                            <ListItemText
                              primary="Today's P&L"
                              secondary={formatCurrency(realTimeData.dailyPnL)}
                            />
                          </ListItem>
                          <ListItem>
                            <ListItemIcon>
                              <AssessmentIcon />
                            </ListItemIcon>
                            <ListItemText
                              primary="Win Rate"
                              secondary={`${Number(
                                realTimeData.winRate || 0
                              ).toFixed(1)}%`}
                            />
                          </ListItem>
                          <ListItem>
                            <ListItemIcon>
                              <TimelineIcon />
                            </ListItemIcon>
                            <ListItemText
                              primary="Active Positions"
                              secondary={`${realTimeData.activeTrades} trades`}
                            />
                          </ListItem>
                        </List>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          Risk Management
                        </Typography>
                        <List>
                          <ListItem>
                            <ListItemIcon>
                              <SpeedIcon />
                            </ListItemIcon>
                            <ListItemText
                              primary="Max Risk Per Trade"
                              secondary={`${Number(
                                config.max_risk_per_trade || 0
                              ).toFixed(1)}%`}
                            />
                          </ListItem>
                          <ListItem>
                            <ListItemIcon>
                              <NotificationsIcon />
                            </ListItemIcon>
                            <ListItemText
                              primary="Daily Loss Limit"
                              secondary={formatCurrency(
                                config.max_daily_loss || 0
                              )}
                            />
                          </ListItem>
                          <ListItem>
                            <ListItemIcon>
                              <VisibilityIcon />
                            </ListItemIcon>
                            <ListItemText
                              primary="Max Positions"
                              secondary={`${
                                config.max_positions || 0
                              } positions`}
                            />
                          </ListItem>
                        </List>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </CardContent>
            )}
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default AutoTradingPage;
