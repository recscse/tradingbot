// pages/UnifiedTradingPage.js
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
} from "@mui/material";
import {
  TrendingUp,
  AccountBalance,
  PlayArrow,
  Stop,
  Warning,
  Security,
  Analytics,
  Timeline,
  Assessment,
  ShowChart,
} from "@mui/icons-material";
import SelectedStocksPanel from "../components/trading/SelectedStocksPanel";
import apiClient from "../services/api";

const UnifiedTradingPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  
  // Trading State
  const [tradingMode, setTradingMode] = useState("PAPER"); // PAPER or LIVE
  const [isTrading, setIsTrading] = useState(false);
  const [selectedTradingStocks, setSelectedTradingStocks] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // Portfolio State
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState([]);
  const [positions, setPositions] = useState([]);
  
  // Trading Configuration
  const [tradingConfig, setTradingConfig] = useState({
    default_qty: 1,
    stop_loss_percent: 2.0,
    target_percent: 4.0,
    max_positions: 3,
    risk_per_trade_percent: 1.0,
    option_strategy: "BUY",
    option_expiry_preference: "NEAREST",
    enable_option_trading: true,
    enable_auto_square_off: true,
    enable_trailing_stop: false,
  });

  // Load trading configuration
  const loadTradingConfig = useCallback(async () => {
    try {
      const response = await apiClient.get("/api/v1/trading/config");
      if (response.data) {
        setTradingConfig(prev => ({ ...prev, ...response.data }));
      }
    } catch (error) {
      console.error("Error loading trading config:", error);
    }
  }, []);

  // Fetch portfolio data
  const fetchPortfolio = useCallback(async () => {
    try {
      const endpoint = tradingMode === "PAPER" 
        ? "/api/paper-trading/portfolio"
        : "/api/live-trading/portfolio";
      
      const response = await apiClient.get(endpoint);
      setPortfolio(response.data.portfolio);
      setIsTrading(response.data.portfolio?.is_active || false);
    } catch (error) {
      console.error("Error fetching portfolio:", error);
    }
  }, [tradingMode]);

  // Fetch trades
  const fetchTrades = useCallback(async () => {
    try {
      const endpoint = tradingMode === "PAPER"
        ? "/api/paper-trading/trades"
        : "/api/live-trading/trades";
      
      const response = await apiClient.get(endpoint);
      setTrades(response.data.trades || []);
    } catch (error) {
      console.error("Error fetching trades:", error);
    }
  }, [tradingMode]);

  // Fetch positions
  const fetchPositions = useCallback(async () => {
    try {
      const endpoint = tradingMode === "PAPER"
        ? "/api/paper-trading/positions"
        : "/api/live-trading/positions";
      
      const response = await apiClient.get(endpoint);
      setPositions(response.data.positions || []);
    } catch (error) {
      console.error("Error fetching positions:", error);
    }
  }, [tradingMode]);

  // Handle selected stocks
  const handleSelectedStocks = (stocks) => {
    setSelectedTradingStocks(stocks);
  };

  // Start trading with selected stocks
  const handleStartTrading = async (stocks, mode) => {
    try {
      setLoading(true);
      
      const endpoint = mode === "PAPER"
        ? "/api/paper-trading/start"
        : "/api/live-trading/start";

      const tradingRequest = {
        selected_stocks: stocks.map(stock => ({
          symbol: stock.symbol,
          instrument_key: stock.instrument_key,
          price_at_selection: stock.price_at_selection,
          option_contract: stock.option_contract,
          option_type: stock.option_type,
          sector: stock.sector,
        })),
        strategy_config: {
          ...tradingConfig,
          trade_mode: mode,
        },
        initial_balance: mode === "PAPER" ? 1000000 : undefined, // 10L for paper trading
      };

      const response = await apiClient.post(endpoint, tradingRequest);
      
      if (response.data.success !== false) {
        setIsTrading(true);
        alert(`${mode} trading started successfully with ${stocks.length} stocks!`);
        await fetchPortfolio();
        await fetchTrades();
        await fetchPositions();
      } else {
        alert(`Failed to start ${mode} trading: ${response.data.message}`);
      }
    } catch (error) {
      console.error("Error starting trading:", error);
      alert(`Failed to start ${mode} trading: ${error.response?.data?.message || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Stop trading
  const handleStopTrading = async () => {
    try {
      const endpoint = tradingMode === "PAPER"
        ? "/api/paper-trading/stop"
        : "/api/live-trading/stop";
      
      await apiClient.post(endpoint);
      setIsTrading(false);
      alert(`${tradingMode} trading stopped successfully`);
      await fetchPortfolio();
    } catch (error) {
      console.error("Error stopping trading:", error);
      alert("Failed to stop trading");
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
      const confirmed = window.confirm(
        "⚠️ LIVE TRADING WARNING ⚠️\n\n" +
        "You are about to switch to LIVE trading mode.\n" +
        "This will use REAL MONEY for all trades.\n\n" +
        "Are you absolutely sure?"
      );
      
      if (!confirmed) {
        return;
      }
    }
    
    setTradingMode(newMode);
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

  useEffect(() => {
    loadTradingConfig();
    fetchPortfolio();
    fetchTrades();
    fetchPositions();

    // Set up periodic refresh during trading
    const interval = setInterval(() => {
      if (isTrading) {
        fetchPortfolio();
        fetchTrades();
        fetchPositions();
      }
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [loadTradingConfig, fetchPortfolio, fetchTrades, fetchPositions, isTrading]);

  // Tab content rendering
  const renderTabContent = () => {
    switch (activeTab) {
      case 0: // Overview
        return (
          <Grid container spacing={3}>
            {/* Selected Stocks Panel */}
            <Grid item xs={12}>
              <SelectedStocksPanel
                onStockSelect={handleSelectedStocks}
                onStartTrading={handleStartTrading}
                tradingMode={tradingMode}
                showTradingControls={true}
              />
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
                        <TrendingUp sx={{ mr: 2, color: "success.main" }} />
                        <Box>
                          <Typography variant="h6">
                            {tradingMode === "PAPER" ? "Virtual Balance" : "Available Cash"}
                          </Typography>
                          <Typography variant="h4">
                            {formatCurrency(portfolio.current_balance)}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Available for trading
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
                          <Typography variant="h4">{trades.length}</Typography>
                          <Typography variant="body2" color="textSecondary">
                            Win Rate: {portfolio.win_rate?.toFixed(1)}%
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
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Active Positions ({tradingMode} Mode)
              </Typography>
              {positions.length === 0 ? (
                <Typography variant="body2" color="textSecondary">
                  No active positions
                </Typography>
              ) : (
                positions.map((position, index) => (
                  <Box key={index} sx={{ mb: 2, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {position.symbol}
                    </Typography>
                    <Typography variant="body2">
                      Quantity: {position.quantity} | Avg Price: {formatCurrency(position.avg_price)}
                    </Typography>
                    <Typography variant="body2" sx={{ color: getPnLColor(position.unrealized_pnl) }}>
                      P&L: {formatCurrency(position.unrealized_pnl)} ({position.unrealized_pnl_pct?.toFixed(2)}%)
                    </Typography>
                  </Box>
                ))
              )}
            </CardContent>
          </Card>
        );

      case 2: // Trade History
        return (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Trade History ({tradingMode} Mode)
              </Typography>
              {trades.length === 0 ? (
                <Typography variant="body2" color="textSecondary">
                  No completed trades
                </Typography>
              ) : (
                trades.slice(0, 10).map((trade, index) => (
                  <Box key={index} sx={{ mb: 2, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {trade.symbol} - {trade.action}
                    </Typography>
                    <Typography variant="body2">
                      Quantity: {trade.quantity} | Price: {formatCurrency(trade.price)}
                    </Typography>
                    <Typography variant="body2" sx={{ color: getPnLColor(trade.pnl) }}>
                      P&L: {formatCurrency(trade.pnl)} | Date: {new Date(trade.timestamp).toLocaleDateString()}
                    </Typography>
                  </Box>
                ))
              )}
            </CardContent>
          </Card>
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
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
                <Box>
                  <Typography variant="h4" gutterBottom>
                    Trading Dashboard
                  </Typography>
                  <Typography variant="body1" color="textSecondary">
                    {tradingMode === "PAPER" 
                      ? "Practice trading with virtual money" 
                      : "Live trading with real money"}
                  </Typography>
                </Box>

                <Box display="flex" alignItems="center" gap={2}>
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
                          <Typography variant="body2">
                            {tradingMode} Mode
                          </Typography>
                          {tradingMode === "LIVE" && <Warning color="error" />}
                        </Box>
                      }
                    />
                  </Box>

                  <Divider orientation="vertical" flexItem />

                  {/* Trading Controls */}
                  {!isTrading ? (
                    <Chip
                      label="Ready to Trade"
                      color="success"
                      variant="outlined"
                      icon={<ShowChart />}
                    />
                  ) : (
                    <Button
                      variant="contained"
                      color="secondary"
                      startIcon={<Stop />}
                      onClick={handleStopTrading}
                    >
                      Stop Trading
                    </Button>
                  )}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Trading Mode Alert */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Alert
            severity={tradingMode === "LIVE" ? "error" : "info"}
            icon={tradingMode === "LIVE" ? <Warning /> : <Security />}
          >
            <Typography variant="h6" gutterBottom>
              Current Mode: {tradingMode} Trading
            </Typography>
            <Typography variant="body2">
              {tradingMode === "LIVE"
                ? "⚠️ LIVE TRADING ACTIVE - All trades will use real money and execute in your demat account!"
                : "📊 Paper Trading Mode - Safe virtual environment for testing strategies with ₹10L virtual money"}
            </Typography>
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
                    Overview
                  </Box>
                }
              />
              <Tab
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Timeline />
                    Positions ({positions.length})
                  </Box>
                }
              />
              <Tab
                label={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Assessment />
                    History ({trades.length})
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
    </Container>
  );
};

export default UnifiedTradingPage;