// pages/EnhancedTradingPage.js
import React, { useState, useEffect, useCallback } from "react";
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Alert,
  Chip,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Paper,
  Stack,
  Divider,
  useTheme,
  useMediaQuery,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  Fab,
  Tooltip,
  Badge,
  LinearProgress,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  AccountBalance,
  PlayArrow,
  Stop,
  Warning,
  Security,
  Analytics,
  Timeline,
  Assessment,
  ShowChart,
  Refresh,
  Settings,
  Speed,
  Target,
  Shield,
  AttachMoney,
  Schedule,
  CallMade,
  CallReceived,
  BarChart,
  Notifications,
  History,
} from "@mui/icons-material";
import SelectedStocksPanel from "../components/trading/SelectedStocksPanel";
import TradingMetrics from "../components/trading/TradingMetrics";
import LivePriceTracker from "../components/trading/LivePriceTracker";
import TradeExecutionLog from "../components/trading/TradeExecutionLog";
import { useTradingWebSocket } from "../hooks/useTradingWebSocket";
import apiClient from "../services/api";

const EnhancedTradingPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  
  // Trading State
  const [tradingMode, setTradingMode] = useState("PAPER"); // PAPER or LIVE
  const [isTrading, setIsTrading] = useState(false);
  const [selectedTradingStocks, setSelectedTradingStocks] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  // Portfolio State
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState([]);
  const [positions, setPositions] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  
  // Dialog States
  const [settingsDialog, setSettingsDialog] = useState(false);
  const [capitalDialog, setCapitalDialog] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState({ open: false, action: null });
  
  // Capital Management
  const [virtualCapital, setVirtualCapital] = useState(1000000);
  const [realTimeBalance, setRealTimeBalance] = useState(0);
  
  // Trading Configuration
  const [tradingConfig, setTradingConfig] = useState({
    risk_per_trade: 2.0,
    stop_loss_percent: 2.0,
    target_percent: 4.0,
    max_positions: 3,
    enable_trailing_stop: false,
    trailing_stop_percent: 1.5,
    enable_auto_square_off: true,
    auto_square_off_time: "15:15",
  });

  // Auto-refresh interval
  const [autoRefresh, setAutoRefresh] = useState(true);

  // WebSocket integration for real-time updates
  const {
    isConnected: wsConnected,
    connectionError: wsError,
    portfolioUpdate,
    positionUpdate,
    tradeUpdate,
    priceUpdate,
    subscribeToSymbols,
    clearPortfolioUpdate,
    clearPositionUpdate,
    clearTradeUpdate,
  } = useTradingWebSocket(tradingMode, isTrading);

  // Fetch portfolio data
  const fetchPortfolio = useCallback(async () => {
    try {
      const response = await apiClient.get("/api/unified-trading/portfolio", {
        params: { trading_mode: tradingMode }
      });
      
      if (response.data.success) {
        setPortfolio(response.data.portfolio);
        setIsTrading(response.data.portfolio?.is_active || false);
        
        if (tradingMode === "LIVE") {
          setRealTimeBalance(response.data.portfolio.current_balance);
        }
      }
    } catch (error) {
      console.error("Error fetching portfolio:", error);
    }
  }, [tradingMode]);

  // Fetch trades
  const fetchTrades = useCallback(async () => {
    try {
      const response = await apiClient.get("/api/unified-trading/trades", {
        params: { trading_mode: tradingMode, limit: 50 }
      });
      
      if (response.data.success) {
        setTrades(response.data.trades || []);
      }
    } catch (error) {
      console.error("Error fetching trades:", error);
    }
  }, [tradingMode]);

  // Fetch positions
  const fetchPositions = useCallback(async () => {
    try {
      const response = await apiClient.get("/api/unified-trading/positions", {
        params: { trading_mode: tradingMode }
      });
      
      if (response.data.success) {
        setPositions(response.data.positions || []);
      }
    } catch (error) {
      console.error("Error fetching positions:", error);
    }
  }, [tradingMode]);

  // Fetch analytics
  const fetchAnalytics = useCallback(async () => {
    try {
      const response = await apiClient.get("/api/unified-trading/analytics", {
        params: { trading_mode: tradingMode }
      });
      
      if (response.data.success) {
        setAnalytics(response.data.analytics);
      }
    } catch (error) {
      console.error("Error fetching analytics:", error);
    }
  }, [tradingMode]);

  // Refresh all data
  const refreshAllData = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchPortfolio(),
        fetchTrades(),
        fetchPositions(),
        fetchAnalytics(),
      ]);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (error) {
      console.error("Error refreshing data:", error);
    } finally {
      setLoading(false);
    }
  }, [fetchPortfolio, fetchTrades, fetchPositions, fetchAnalytics]);

  // Handle selected stocks
  const handleSelectedStocks = (stocks) => {
    setSelectedTradingStocks(stocks);
  };

  // Start trading with selected stocks
  const handleStartTrading = async (stocks, mode) => {
    try {
      setLoading(true);
      
      const tradingRequest = {
        trading_mode: mode || tradingMode,
        selected_stocks: stocks.map(stock => ({
          symbol: stock.symbol,
          instrument_key: stock.instrument_key,
          price_at_selection: stock.price_at_selection,
          option_contract: stock.option_contract,
          option_type: stock.option_type,
          sector: stock.sector,
          quantity: stock.quantity || 1,
        })),
        strategy_config: tradingConfig,
        initial_balance: mode === "PAPER" ? virtualCapital : undefined,
      };

      const response = await apiClient.post("/api/unified-trading/start", tradingRequest);
      
      if (response.data.success) {
        setIsTrading(true);
        setConfirmDialog({ open: false, action: null });
        await refreshAllData();
        
        // Show success message
        alert(`${mode || tradingMode} trading started successfully with ${stocks.length} stocks!`);
      } else {
        alert(`Failed to start trading: ${response.data.message}`);
      }
    } catch (error) {
      console.error("Error starting trading:", error);
      alert(`Failed to start trading: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Stop trading
  const handleStopTrading = async () => {
    try {
      setLoading(true);
      
      const response = await apiClient.post("/api/unified-trading/stop", {
        trading_mode: tradingMode
      });
      
      if (response.data.success) {
        setIsTrading(false);
        await refreshAllData();
        alert(`${tradingMode} trading stopped successfully`);
      }
    } catch (error) {
      console.error("Error stopping trading:", error);
      alert("Failed to stop trading");
    } finally {
      setLoading(false);
    }
  };

  // Handle trading mode change
  const handleTradingModeChange = (event) => {
    const newMode = event.target.checked ? "LIVE" : "PAPER";
    
    if (newMode === "LIVE" && isTrading) {
      alert("Please stop current trading session before switching to LIVE mode");
      return;
    }
    
    if (newMode === "LIVE") {
      setConfirmDialog({
        open: true,
        action: () => {
          setTradingMode(newMode);
          setConfirmDialog({ open: false, action: null });
        },
        title: "⚠️ LIVE TRADING WARNING",
        message: "You are about to switch to LIVE trading mode. This will use REAL MONEY for all trades. Are you absolutely sure?",
        dangerous: true,
      });
    } else {
      setTradingMode(newMode);
    }
  };

  // Format currency
  const formatCurrency = (amount) => {
    if (amount == null) return "₹0.00";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Get P&L color
  const getPnLColor = (pnl) => {
    if (pnl > 0) return "success.main";
    if (pnl < 0) return "error.main";
    return "text.primary";
  };

  // Get strategy description
  const getStrategyDescription = (trade) => {
    const strategies = [];
    if (trade.strategy) strategies.push(trade.strategy);
    if (tradingConfig.enable_trailing_stop) strategies.push("Trailing Stop");
    if (tradingConfig.enable_auto_square_off) strategies.push("Auto Square-off");
    return strategies.length > 0 ? strategies.join(", ") : "Manual Trade";
  };

  // Calculate risk-reward ratio
  const calculateRiskReward = (entry, stopLoss, target) => {
    if (!entry || !stopLoss || !target) return "N/A";
    const risk = Math.abs(entry - stopLoss);
    const reward = Math.abs(target - entry);
    return risk > 0 ? (reward / risk).toFixed(2) : "N/A";
  };

  // Handle WebSocket portfolio updates
  useEffect(() => {
    if (portfolioUpdate) {
      setPortfolio(prev => ({ ...prev, ...portfolioUpdate }));
      clearPortfolioUpdate();
    }
  }, [portfolioUpdate, clearPortfolioUpdate]);

  // Handle WebSocket position updates
  useEffect(() => {
    if (positionUpdate) {
      setPositions(prev => {
        const updatedPositions = [...prev];
        const index = updatedPositions.findIndex(p => p.symbol === positionUpdate.symbol);
        
        if (index >= 0) {
          updatedPositions[index] = { ...updatedPositions[index], ...positionUpdate };
        } else {
          updatedPositions.push(positionUpdate);
        }
        
        return updatedPositions;
      });
      clearPositionUpdate();
    }
  }, [positionUpdate, clearPositionUpdate]);

  // Handle WebSocket trade updates
  useEffect(() => {
    if (tradeUpdate) {
      setTrades(prev => [tradeUpdate, ...prev.slice(0, 99)]); // Keep last 100 trades
      clearTradeUpdate();
    }
  }, [tradeUpdate, clearTradeUpdate]);

  // Subscribe to symbols for price updates
  useEffect(() => {
    if (positions.length > 0 && wsConnected) {
      const symbols = positions.map(p => p.symbol);
      subscribeToSymbols(symbols);
    }
  }, [positions, wsConnected, subscribeToSymbols]);

  useEffect(() => {
    refreshAllData();

    // Set up auto-refresh during trading (less frequent when WebSocket is connected)
    let interval;
    if (autoRefresh && isTrading) {
      const refreshInterval = wsConnected ? 60000 : 30000; // 1 min if WS connected, 30s otherwise
      interval = setInterval(refreshAllData, refreshInterval);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [refreshAllData, autoRefresh, isTrading, wsConnected]);

  // Tab content rendering
  const renderTabContent = () => {
    switch (activeTab) {
      case 0: // Dashboard
        return (
          <Grid container spacing={3}>
            {/* Trading Controls */}
            <Grid item xs={12}>
              <Card elevation={2}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6" fontWeight="bold">
                      🎯 Trading Controls
                    </Typography>
                    <Box display="flex" gap={1}>
                      {selectedTradingStocks.length > 0 && !isTrading && (
                        <Button
                          variant="contained"
                          startIcon={<PlayArrow />}
                          onClick={() => {
                            if (tradingMode === "LIVE") {
                              setConfirmDialog({
                                open: true,
                                action: () => handleStartTrading(selectedTradingStocks),
                                title: "⚠️ CONFIRM LIVE TRADING",
                                message: `You are about to start LIVE trading with ${selectedTradingStocks.length} stocks. Real money will be used!`,
                                dangerous: true,
                              });
                            } else {
                              handleStartTrading(selectedTradingStocks);
                            }
                          }}
                          disabled={loading}
                          color={tradingMode === "LIVE" ? "error" : "primary"}
                        >
                          Start {tradingMode} Trading
                        </Button>
                      )}
                      
                      {isTrading && (
                        <Button
                          variant="contained"
                          color="secondary"
                          startIcon={<Stop />}
                          onClick={handleStopTrading}
                          disabled={loading}
                        >
                          Stop Trading
                        </Button>
                      )}
                    </Box>
                  </Box>

                  {selectedTradingStocks.length === 0 && !isTrading && (
                    <Alert severity="info">
                      Select stocks from the panel below to start trading
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Selected Stocks Panel */}
            <Grid item xs={12}>
              <SelectedStocksPanel
                onStockSelect={handleSelectedStocks}
                onStartTrading={handleStartTrading}
                tradingMode={tradingMode}
                showTradingControls={false}
              />
            </Grid>

            {/* Capital Management */}
            <Grid item xs={12}>
              <Card elevation={2}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6" fontWeight="bold">
                      💰 Capital Management
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<Settings />}
                      onClick={() => setCapitalDialog(true)}
                    >
                      Configure
                    </Button>
                  </Box>

                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Box display="flex" alignItems="center" gap={2}>
                        <AccountBalance color="primary" />
                        <Box>
                          <Typography variant="body2" color="textSecondary">
                            {tradingMode === "PAPER" ? "Virtual Capital" : "Real Balance"}
                          </Typography>
                          <Typography variant="h5" fontWeight="bold">
                            {formatCurrency(tradingMode === "PAPER" ? virtualCapital : realTimeBalance)}
                          </Typography>
                        </Box>
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <Box display="flex" alignItems="center" gap={2}>
                        <AttachMoney color="success" />
                        <Box>
                          <Typography variant="body2" color="textSecondary">
                            Available for Trading
                          </Typography>
                          <Typography variant="h5" fontWeight="bold">
                            {formatCurrency(portfolio?.current_balance || 0)}
                          </Typography>
                        </Box>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            {/* Portfolio Summary */}
            {portfolio && (
              <>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box display="flex" alignItems="center">
                        <AccountBalance sx={{ mr: 2, color: "primary.main" }} />
                        <Box>
                          <Typography variant="h6">Portfolio Value</Typography>
                          <Typography variant="h4">
                            {formatCurrency(portfolio.current_portfolio_value)}
                          </Typography>
                          <Typography variant="body2" sx={{ color: getPnLColor(portfolio.total_pnl) }}>
                            {portfolio.total_pnl >= 0 ? "+" : ""}
                            {formatCurrency(portfolio.total_pnl)} ({portfolio.total_pnl_pct?.toFixed(2)}%)
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box display="flex" alignItems="center">
                        <Timeline sx={{ mr: 2, color: "info.main" }} />
                        <Box>
                          <Typography variant="h6">Active Positions</Typography>
                          <Typography variant="h4">{positions.length}</Typography>
                          <Typography variant="body2" color="textSecondary">
                            Unrealized P&L: {formatCurrency(portfolio.unrealized_pnl || 0)}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box display="flex" alignItems="center">
                        <Assessment sx={{ mr: 2, color: "warning.main" }} />
                        <Box>
                          <Typography variant="h6">Total Trades</Typography>
                          <Typography variant="h4">{portfolio.total_trades}</Typography>
                          <Typography variant="body2" color="textSecondary">
                            Win Rate: {portfolio.win_rate?.toFixed(1)}%
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Box display="flex" alignItems="center">
                        <Speed sx={{ mr: 2, color: "success.main" }} />
                        <Box>
                          <Typography variant="h6">Performance</Typography>
                          <Typography variant="h4" sx={{ color: getPnLColor(portfolio.total_pnl) }}>
                            {portfolio.total_pnl_pct?.toFixed(1)}%
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Since inception
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </>
            )}
          </Grid>
        );

      case 1: // Positions
        return (
          <LivePriceTracker 
            positions={positions}
            tradingMode={tradingMode}
            onRefresh={refreshAllData}
          />
        );

      case 2: // Trade History
        return (
          <TradeExecutionLog 
            trades={trades}
            tradingMode={tradingMode}
            analytics={analytics}
          />
        );

      case 3: // Analytics
        return (
          <TradingMetrics 
            analytics={analytics}
            tradingMode={tradingMode}
          />
        );

      case 4: // Live Dashboard
        return (
          <Grid container spacing={3}>
            {/* Live Price Tracker */}
            <Grid item xs={12}>
              <LivePriceTracker 
                positions={positions}
                tradingMode={tradingMode}
                onRefresh={refreshAllData}
              />
            </Grid>

            {/* Trading Metrics */}
            <Grid item xs={12}>
              <TradingMetrics 
                analytics={analytics}
                tradingMode={tradingMode}
              />
            </Grid>

            {/* Recent Trade Execution Log */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    🔥 Recent Trade Executions
                  </Typography>
                  <TradeExecutionLog 
                    trades={trades.slice(0, 5)} // Show only last 5 trades
                    tradingMode={tradingMode}
                    analytics={analytics}
                  />
                </CardContent>
              </Card>
            </Grid>

            {/* Real-time Market Status */}
            <Grid item xs={12}>
              <Alert 
                severity={isTrading ? "success" : "info"} 
                sx={{ 
                  fontWeight: "medium",
                  "& .MuiAlert-message": { width: "100%" }
                }}
              >
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      🎯 Trading Status: {isTrading ? "ACTIVE" : "INACTIVE"}
                    </Typography>
                    <Typography variant="body2">
                      Mode: {tradingMode} • Positions: {positions.length} • 
                      Total P&L: {formatCurrency(portfolio?.total_pnl || 0)} • 
                      Win Rate: {portfolio?.win_rate?.toFixed(1) || 0}%
                    </Typography>
                  </Box>
                  {lastUpdated && (
                    <Typography variant="caption" color="textSecondary">
                      Last sync: {lastUpdated}
                    </Typography>
                  )}
                </Box>
              </Alert>
            </Grid>
          </Grid>
        );

      default:
        return null;
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Card elevation={3}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
                <Box>
                  <Typography variant="h4" gutterBottom>
                    🚀 Advanced Trading Dashboard
                  </Typography>
                  <Typography variant="body1" color="textSecondary">
                    {tradingMode === "PAPER" 
                      ? "Practice trading with virtual money to test your strategies" 
                      : "Live trading with real money - Execute with caution"}
                  </Typography>
                </Box>

                <Box display="flex" alignItems="center" gap={2}>
                  {/* WebSocket Status */}
                  <Tooltip title={wsConnected ? "Real-time connection active" : "Real-time connection disconnected"}>
                    <Chip
                      icon={wsConnected ? <CheckCircle /> : <Error />}
                      label={wsConnected ? "Live" : "Offline"}
                      color={wsConnected ? "success" : "error"}
                      variant="outlined"
                      size="small"
                    />
                  </Tooltip>

                  {/* Auto Refresh Toggle */}
                  <FormControlLabel
                    control={
                      <Switch
                        checked={autoRefresh}
                        onChange={(e) => setAutoRefresh(e.target.checked)}
                        size="small"
                      />
                    }
                    label="Auto Refresh"
                  />

                  <Divider orientation="vertical" flexItem />

                  {/* Trading Mode Toggle */}
                  <Box display="flex" alignItems="center" gap={1}>
                    <Security color={tradingMode === "PAPER" ? "success" : "disabled"} />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={tradingMode === "LIVE"}
                          onChange={handleTradingModeChange}
                          disabled={isTrading}
                        />
                      }
                      label={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body2" fontWeight="medium">
                            {tradingMode} Mode
                          </Typography>
                          {tradingMode === "LIVE" && <Warning color="error" />}
                        </Box>
                      }
                    />
                  </Box>

                  <Divider orientation="vertical" flexItem />

                  {/* Action Buttons */}
                  <Tooltip title="Refresh all data">
                    <span>
                      <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        onClick={refreshAllData}
                        disabled={loading}
                        size="small"
                      >
                        Refresh
                      </Button>
                    </span>
                  </Tooltip>

                  <Tooltip title="Trading settings">
                    <span>
                      <Button
                        variant="outlined"
                        startIcon={<Settings />}
                        onClick={() => setSettingsDialog(true)}
                        size="small"
                      >
                        Settings
                      </Button>
                    </span>
                  </Tooltip>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* WebSocket Error Alert */}
      {wsError && (
        <Grid container spacing={3} sx={{ mb: 2 }}>
          <Grid item xs={12}>
            <Alert severity="warning" onClose={() => {}}>
              <Typography variant="body2">
                <strong>Real-time Connection Issue:</strong> {wsError}. 
                Data will refresh automatically, but live updates may be delayed.
              </Typography>
            </Alert>
          </Grid>
        </Grid>
      )}

      {/* Trading Status Alert */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Alert
            severity={tradingMode === "LIVE" ? "error" : "info"}
            icon={tradingMode === "LIVE" ? <Warning /> : <Security />}
            sx={{ 
              fontWeight: "medium",
              "& .MuiAlert-message": { width: "100%" }
            }}
          >
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="h6" gutterBottom>
                  Current Mode: {tradingMode} Trading
                  {isTrading && (
                    <Chip 
                      label="ACTIVE" 
                      color={tradingMode === "LIVE" ? "error" : "success"} 
                      size="small" 
                      sx={{ ml: 1 }}
                    />
                  )}
                </Typography>
                <Typography variant="body2">
                  {tradingMode === "LIVE"
                    ? "⚠️ LIVE TRADING ACTIVE - All trades will use real money and execute in your demat account!"
                    : "📊 Paper Trading Mode - Safe virtual environment for testing strategies"}
                </Typography>
              </Box>
              {lastUpdated && (
                <Typography variant="caption" color="textSecondary">
                  Last updated: {lastUpdated}
                </Typography>
              )}
            </Box>
          </Alert>
        </Grid>
      </Grid>

      {/* Main Content with Tabs */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ width: "100%" }}>
            <Tabs
              value={activeTab}
              onChange={(e, newValue) => setActiveTab(newValue)}
              variant={isMobile ? "scrollable" : "fullWidth"}
              scrollButtons="auto"
              sx={{ borderBottom: 1, borderColor: "divider" }}
            >
              <Tab
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Analytics />
                    Dashboard
                  </Box>
                }
              />
              <Tab
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Timeline />
                    Positions
                    <Badge badgeContent={positions.length} color="primary" />
                  </Box>
                }
              />
              <Tab
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Assessment />
                    Trade History
                    <Badge badgeContent={trades.length} color="primary" />
                  </Box>
                }
              />
              <Tab
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <BarChart />
                    Analytics
                  </Box>
                }
              />
              <Tab
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Speed />
                    Live Dashboard
                  </Box>
                }
              />
            </Tabs>

            <Box sx={{ p: 3 }}>
              {renderTabContent()}
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Floating Action Button for Quick Actions */}
      {isTrading && (
        <Fab
          color="secondary"
          aria-label="stop trading"
          sx={{ position: "fixed", bottom: 16, right: 16 }}
          onClick={handleStopTrading}
        >
          <Stop />
        </Fab>
      )}

      {/* Loading Overlay */}
      {loading && (
        <Box
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bgcolor="rgba(0,0,0,0.3)"
          display="flex"
          alignItems="center"
          justifyContent="center"
          zIndex={9999}
        >
          <CircularProgress size={60} />
        </Box>
      )}

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialog.open} onClose={() => setConfirmDialog({ open: false, action: null })}>
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <Warning color="error" />
            {confirmDialog.title}
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography>{confirmDialog.message}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialog({ open: false, action: null })}>
            Cancel
          </Button>
          <Button
            onClick={confirmDialog.action}
            variant="contained"
            color={confirmDialog.dangerous ? "error" : "primary"}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      {/* Capital Management Dialog */}
      <Dialog open={capitalDialog} onClose={() => setCapitalDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>💰 Capital Management</DialogTitle>
        <DialogContent>
          <Box mt={2}>
            {tradingMode === "PAPER" ? (
              <TextField
                fullWidth
                label="Virtual Capital"
                type="number"
                value={virtualCapital}
                onChange={(e) => setVirtualCapital(parseFloat(e.target.value))}
                InputProps={{
                  startAdornment: "₹",
                }}
                helperText="Set your virtual trading capital for paper trading"
              />
            ) : (
              <Alert severity="info">
                Live trading capital is fetched automatically from your broker account.
                Current balance: {formatCurrency(realTimeBalance)}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCapitalDialog(false)}>Cancel</Button>
          <Button onClick={() => setCapitalDialog(false)} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Trading Settings Dialog */}
      <Dialog open={settingsDialog} onClose={() => setSettingsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>⚙️ Trading Configuration</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Risk Per Trade (%)"
                type="number"
                value={tradingConfig.risk_per_trade}
                onChange={(e) => setTradingConfig({
                  ...tradingConfig,
                  risk_per_trade: parseFloat(e.target.value)
                })}
                inputProps={{ min: 0.1, max: 10, step: 0.1 }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Stop Loss (%)"
                type="number"
                value={tradingConfig.stop_loss_percent}
                onChange={(e) => setTradingConfig({
                  ...tradingConfig,
                  stop_loss_percent: parseFloat(e.target.value)
                })}
                inputProps={{ min: 0.5, max: 20, step: 0.5 }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Target (%)"
                type="number"
                value={tradingConfig.target_percent}
                onChange={(e) => setTradingConfig({
                  ...tradingConfig,
                  target_percent: parseFloat(e.target.value)
                })}
                inputProps={{ min: 1, max: 50, step: 1 }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Max Positions"
                type="number"
                value={tradingConfig.max_positions}
                onChange={(e) => setTradingConfig({
                  ...tradingConfig,
                  max_positions: parseInt(e.target.value)
                })}
                inputProps={{ min: 1, max: 10, step: 1 }}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={tradingConfig.enable_trailing_stop}
                    onChange={(e) => setTradingConfig({
                      ...tradingConfig,
                      enable_trailing_stop: e.target.checked
                    })}
                  />
                }
                label="Enable Trailing Stop Loss"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={tradingConfig.enable_auto_square_off}
                    onChange={(e) => setTradingConfig({
                      ...tradingConfig,
                      enable_auto_square_off: e.target.checked
                    })}
                  />
                }
                label="Enable Auto Square-off (3:20 PM)"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsDialog(false)}>Cancel</Button>
          <Button onClick={() => setSettingsDialog(false)} variant="contained">
            Save Settings
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default EnhancedTradingPage;