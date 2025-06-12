import React, { useState, useEffect, useCallback } from "react";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Chip,
  Box,
  LinearProgress,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
} from "@mui/material";
import {
  TrendingUp,
  PlayArrow,
  Stop,
  Analytics,
  AccountBalance,
  Timeline,
} from "@mui/icons-material";
import axios from "axios";

const PaperTradingDashboard = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [screenedStocks, setScreenedStocks] = useState([]);
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [isTrading, setIsTrading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [startTradingDialog, setStartTradingDialog] = useState(false);

  const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

  // Strategy configuration
  const [strategyConfig, setStrategyConfig] = useState({
    risk_per_trade: 0.02,
    stop_loss_pct: 0.05,
    target_pct: 0.1,
    min_confidence: 70,
    analysis_interval: 300,
    use_trailing_stop: true,
    trailing_stop_pct: 0.03,
  });

  const fetchPortfolio = useCallback(async () => {
    try {
      const response = await axios.get(
        `${API_BASE}/api/paper-trading/portfolio`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      setPortfolio(response.data.portfolio);
      setIsTrading(response.data.portfolio?.is_active || false);
    } catch (error) {
      console.error("Error fetching portfolio:", error);
    }
  }, [API_BASE]);

  const fetchTrades = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/paper-trading/trades`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      setTrades(response.data.trades);
    } catch (error) {
      console.error("Error fetching trades:", error);
    }
  }, [API_BASE]);

  const fetchAnalytics = useCallback(async () => {
    try {
      const response = await axios.get(
        `${API_BASE}/api/paper-trading/analytics`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      setAnalytics(response.data);
    } catch (error) {
      console.error("Error fetching analytics:", error);
    }
  }, [API_BASE]);

  const screenStocks = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `${API_BASE}/api/paper-trading/screen-stocks`,
        {
          sector: null,
          min_score: 60,
          max_results: 50,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      setScreenedStocks(response.data.stocks);
    } catch (error) {
      console.error("Error screening stocks:", error);
    }
    setLoading(false);
  }, [API_BASE]);

  const startTrading = async () => {
    if (selectedStocks.length === 0) {
      alert("Please select at least one stock");
      return;
    }

    setLoading(true);
    try {
      // Removed unused response variable
      await axios.post(
        `${API_BASE}/api/paper-trading/start`,
        {
          selected_stocks: selectedStocks,
          strategy_config: strategyConfig,
          initial_balance: 1000000,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );

      setIsTrading(true);
      setStartTradingDialog(false);
      alert("Paper trading started successfully!");
      fetchPortfolio();
    } catch (error) {
      console.error("Error starting trading:", error);
      alert("Failed to start trading");
    }
    setLoading(false);
  };

  const stopTrading = async () => {
    try {
      await axios.post(
        `${API_BASE}/api/paper-trading/stop`,
        {},
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );

      setIsTrading(false);
      alert("Paper trading stopped");
      fetchPortfolio();
    } catch (error) {
      console.error("Error stopping trading:", error);
    }
  };

  useEffect(() => {
    fetchPortfolio();
    fetchTrades();
    fetchAnalytics();
    screenStocks();

    // Set up periodic refresh
    const interval = setInterval(() => {
      if (isTrading) {
        fetchPortfolio();
        fetchTrades();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [isTrading, fetchPortfolio, fetchTrades, fetchAnalytics, screenStocks]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "OPEN":
        return "primary";
      case "CLOSED":
        return "default";
      default:
        return "default";
    }
  };

  const getPnLColor = (pnl) => {
    if (pnl > 0) return "#4caf50";
    if (pnl < 0) return "#f44336";
    return "#9e9e9e";
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* Header */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Box>
                  <Typography variant="h4" gutterBottom>
                    Paper Trading Dashboard
                  </Typography>
                  <Typography variant="body1" color="textSecondary">
                    Practice trading with virtual money to test your strategies
                  </Typography>
                </Box>
                <Box>
                  {!isTrading ? (
                    <Button
                      variant="contained"
                      startIcon={<PlayArrow />}
                      onClick={() => setStartTradingDialog(true)}
                      size="large"
                    >
                      Start Trading
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      color="secondary"
                      startIcon={<Stop />}
                      onClick={stopTrading}
                      size="large"
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

      {/* Portfolio Summary */}
      {portfolio && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <AccountBalance sx={{ mr: 2, color: "primary.main" }} />
                  <Box>
                    <Typography variant="h6">Portfolio Value</Typography>
                    <Typography variant="h4">
                      {formatCurrency(portfolio.current_portfolio_value)}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ color: getPnLColor(portfolio.total_pnl) }}
                    >
                      {portfolio.total_pnl >= 0 ? "+" : ""}
                      {formatCurrency(portfolio.total_pnl)}(
                      {portfolio.total_pnl_pct?.toFixed(2)}%)
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <TrendingUp sx={{ mr: 2, color: "success.main" }} />
                  <Box>
                    <Typography variant="h6">Cash Balance</Typography>
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

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <Timeline sx={{ mr: 2, color: "info.main" }} />
                  <Box>
                    <Typography variant="h6">Active Positions</Typography>
                    <Typography variant="h4">
                      {portfolio.positions?.length || 0}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Unrealized P&L:{" "}
                      {formatCurrency(portfolio.unrealized_pnl || 0)}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <Analytics sx={{ mr: 2, color: "warning.main" }} />
                  <Box>
                    <Typography variant="h6">Win Rate</Typography>
                    <Typography variant="h4">
                      {portfolio.risk_metrics?.win_rate?.toFixed(1) || 0}%
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {portfolio.winning_trades}/{portfolio.total_trades} trades
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Tabs */}
      <Card sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
        >
          <Tab label="Positions" />
          <Tab label="Trade History" />
          <Tab label="Stock Screener" />
          <Tab label="Analytics" />
        </Tabs>
      </Card>

      {/* Tab Content */}
      {activeTab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Current Positions
            </Typography>
            {portfolio?.positions?.length > 0 ? (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Symbol</TableCell>
                    <TableCell align="right">Quantity</TableCell>
                    <TableCell align="right">Entry Price</TableCell>
                    <TableCell align="right">Current Price</TableCell>
                    <TableCell align="right">Unrealized P&L</TableCell>
                    <TableCell align="right">P&L %</TableCell>
                    <TableCell align="right">Stop Loss</TableCell>
                    <TableCell align="right">Target</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {portfolio.positions.map((position) => (
                    <TableRow key={position.symbol}>
                      <TableCell>{position.symbol}</TableCell>
                      <TableCell align="right">{position.quantity}</TableCell>
                      <TableCell align="right">
                        ₹{position.entry_price?.toFixed(2)}
                      </TableCell>
                      <TableCell align="right">
                        ₹{position.current_price?.toFixed(2)}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: getPnLColor(position.unrealized_pnl) }}
                      >
                        ₹{position.unrealized_pnl?.toFixed(2)}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: getPnLColor(position.unrealized_pnl_pct) }}
                      >
                        {position.unrealized_pnl_pct?.toFixed(2)}%
                      </TableCell>
                      <TableCell align="right">
                        ₹{position.stop_loss?.toFixed(2)}
                      </TableCell>
                      <TableCell align="right">
                        ₹{position.target_price?.toFixed(2)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Alert severity="info">No open positions</Alert>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Trade History
            </Typography>
            {trades.length > 0 ? (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date/Time</TableCell>
                    <TableCell>Symbol</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell align="right">Quantity</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">P&L</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Exit Reason</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {trades.map((trade, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        {new Date(trade.timestamp).toLocaleDateString()}{" "}
                        {new Date(trade.timestamp).toLocaleTimeString()}
                      </TableCell>
                      <TableCell>{trade.symbol}</TableCell>
                      <TableCell>
                        <Chip
                          label={trade.action}
                          color={trade.action === "BUY" ? "success" : "error"}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">{trade.quantity}</TableCell>
                      <TableCell align="right">
                        ₹{trade.price?.toFixed(2)}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: getPnLColor(trade.pnl) }}
                      >
                        {trade.pnl
                          ? `₹${trade.pnl.toFixed(2)} (${trade.pnl_pct?.toFixed(
                              2
                            )}%)`
                          : "-"}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={trade.status}
                          color={getStatusColor(trade.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{trade.exit_reason || "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Alert severity="info">No trades executed yet</Alert>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && (
        <Card>
          <CardContent>
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              mb={2}
            >
              <Typography variant="h6">Stock Screener</Typography>
              <Button
                variant="outlined"
                onClick={screenStocks}
                disabled={loading}
              >
                {loading ? "Screening..." : "Refresh Screen"}
              </Button>
            </Box>

            {loading && <LinearProgress sx={{ mb: 2 }} />}

            {screenedStocks.length > 0 ? (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Select</TableCell>
                    <TableCell>Symbol</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">Score</TableCell>
                    <TableCell>Recommendation</TableCell>
                    <TableCell align="right">Confidence</TableCell>
                    <TableCell>Trend</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {screenedStocks.map((stock) => (
                    <TableRow key={stock.symbol}>
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedStocks.includes(stock.symbol)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedStocks([
                                ...selectedStocks,
                                stock.symbol,
                              ]);
                            } else {
                              setSelectedStocks(
                                selectedStocks.filter((s) => s !== stock.symbol)
                              );
                            }
                          }}
                        />
                      </TableCell>
                      <TableCell>{stock.symbol}</TableCell>
                      <TableCell>{stock.name}</TableCell>
                      <TableCell align="right">
                        ₹{stock.analysis.current_price}
                      </TableCell>
                      <TableCell align="right">
                        <Box display="flex" alignItems="center">
                          {stock.analysis.score}/100
                          <LinearProgress
                            variant="determinate"
                            value={stock.analysis.score}
                            sx={{ ml: 1, width: 50 }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={stock.recommendation.action}
                          color={
                            stock.recommendation.action.includes("BUY")
                              ? "success"
                              : stock.recommendation.action === "SELL"
                              ? "error"
                              : "default"
                          }
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">
                        {stock.recommendation.confidence}%
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={stock.analysis.trend}
                          color={
                            stock.analysis.trend.includes("UP")
                              ? "success"
                              : stock.analysis.trend.includes("DOWN")
                              ? "error"
                              : "default"
                          }
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Alert severity="info">
                Click "Refresh Screen" to analyze stocks
              </Alert>
            )}

            {selectedStocks.length > 0 && (
              <Alert severity="success" sx={{ mt: 2 }}>
                {selectedStocks.length} stocks selected for trading
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 3 && (
        <Grid container spacing={3}>
          {analytics && analytics.total_trades > 0 ? (
            <>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Performance Metrics
                    </Typography>
                    <Box sx={{ mt: 2 }}>
                      <Typography>
                        Total Trades: {analytics.total_trades}
                      </Typography>
                      <Typography>
                        Gross Profit: {formatCurrency(analytics.gross_profit)}
                      </Typography>
                      <Typography>
                        Gross Loss: {formatCurrency(analytics.gross_loss)}
                      </Typography>
                      <Typography>
                        Profit Factor: {analytics.profit_factor?.toFixed(2)}
                      </Typography>
                      <Typography>
                        Avg Holding Period:{" "}
                        {analytics.avg_holding_period_hours?.toFixed(1)} hours
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Best & Worst Trades
                    </Typography>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" color="success.main">
                        Best Trade:
                      </Typography>
                      <Typography>
                        {analytics.best_trade.symbol}:{" "}
                        {formatCurrency(analytics.best_trade.pnl)} (
                        {analytics.best_trade.pnl_pct?.toFixed(2)}%)
                      </Typography>

                      <Typography
                        variant="subtitle2"
                        color="error.main"
                        sx={{ mt: 2 }}
                      >
                        Worst Trade:
                      </Typography>
                      <Typography>
                        {analytics.worst_trade.symbol}:{" "}
                        {formatCurrency(analytics.worst_trade.pnl)} (
                        {analytics.worst_trade.pnl_pct?.toFixed(2)}%)
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </>
          ) : (
            <Grid item xs={12}>
              <Alert severity="info">
                Start trading to see performance analytics
              </Alert>
            </Grid>
          )}
        </Grid>
      )}

      {/* Start Trading Dialog */}
      <Dialog
        open={startTradingDialog}
        onClose={() => setStartTradingDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Start Paper Trading</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 3 }}>
            Paper trading uses virtual money to test your strategies. No real
            money is involved.
          </Alert>

          <Typography variant="h6" gutterBottom>
            Strategy Configuration
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Risk Per Trade (%)"
                type="number"
                value={strategyConfig.risk_per_trade * 100}
                onChange={(e) =>
                  setStrategyConfig({
                    ...strategyConfig,
                    risk_per_trade: parseFloat(e.target.value) / 100,
                  })
                }
                inputProps={{ min: 0.1, max: 10, step: 0.1 }}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Stop Loss (%)"
                type="number"
                value={strategyConfig.stop_loss_pct * 100}
                onChange={(e) =>
                  setStrategyConfig({
                    ...strategyConfig,
                    stop_loss_pct: parseFloat(e.target.value) / 100,
                  })
                }
                inputProps={{ min: 1, max: 20, step: 0.5 }}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Target (%)"
                type="number"
                value={strategyConfig.target_pct * 100}
                onChange={(e) =>
                  setStrategyConfig({
                    ...strategyConfig,
                    target_pct: parseFloat(e.target.value) / 100,
                  })
                }
                inputProps={{ min: 2, max: 50, step: 1 }}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Minimum Confidence (%)"
                type="number"
                value={strategyConfig.min_confidence}
                onChange={(e) =>
                  setStrategyConfig({
                    ...strategyConfig,
                    min_confidence: parseInt(e.target.value),
                  })
                }
                inputProps={{ min: 50, max: 95, step: 5 }}
              />
            </Grid>
          </Grid>

          <Typography variant="body2" sx={{ mt: 2 }}>
            Selected Stocks:{" "}
            {selectedStocks.length > 0 ? selectedStocks.join(", ") : "None"}
          </Typography>

          {selectedStocks.length === 0 && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Please select stocks from the Stock Screener tab first
            </Alert>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setStartTradingDialog(false)}>Cancel</Button>
          <Button
            onClick={startTrading}
            variant="contained"
            disabled={selectedStocks.length === 0 || loading}
          >
            {loading ? "Starting..." : "Start Trading"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PaperTradingDashboard;
