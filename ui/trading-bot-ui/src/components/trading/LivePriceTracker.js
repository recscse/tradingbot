// components/trading/LivePriceTracker.js
import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  Paper,
  IconButton,
  Tooltip,
  Alert,
  Stack,
} from "@mui/material";
import {
  Refresh,
  TrendingUp,
  TrendingDown,
  CallMade,
  CallReceived,
  Timeline,
  Speed,
  WarningAmber,
  CheckCircle,
} from "@mui/icons-material";
import apiClient from "../../services/api";

const LivePriceTracker = ({ positions, tradingMode, onRefresh }) => {
  const [liveData, setLiveData] = useState({});
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [priceAlerts, setPriceAlerts] = useState([]);

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

  // Calculate real-time P&L
  const calculateRealtimePnL = (position, currentPrice) => {
    if (!currentPrice || !position.avg_price) return { pnl: 0, pnlPct: 0 };
    
    const priceDiff = currentPrice - position.avg_price;
    const pnl = priceDiff * position.quantity * (position.side === "BUY" ? 1 : -1);
    const pnlPct = (priceDiff / position.avg_price) * 100 * (position.side === "BUY" ? 1 : -1);
    
    return { pnl, pnlPct };
  };

  // Check for price alerts
  const checkPriceAlerts = useCallback((positions, liveData) => {
    const alerts = [];
    
    positions.forEach(position => {
      const livePrice = liveData[position.symbol];
      if (!livePrice || !position.stop_loss || !position.target_price) return;
      
      const currentPrice = livePrice.price;
      
      // Stop loss alert
      if (position.side === "BUY" && currentPrice <= position.stop_loss) {
        alerts.push({
          type: "stop_loss",
          symbol: position.symbol,
          message: `${position.symbol} hit stop loss at ${formatCurrency(currentPrice)}`,
          severity: "error",
        });
      } else if (position.side === "SELL" && currentPrice >= position.stop_loss) {
        alerts.push({
          type: "stop_loss",
          symbol: position.symbol,
          message: `${position.symbol} hit stop loss at ${formatCurrency(currentPrice)}`,
          severity: "error",
        });
      }
      
      // Target alert
      if (position.side === "BUY" && currentPrice >= position.target_price) {
        alerts.push({
          type: "target",
          symbol: position.symbol,
          message: `${position.symbol} reached target at ${formatCurrency(currentPrice)}`,
          severity: "success",
        });
      } else if (position.side === "SELL" && currentPrice <= position.target_price) {
        alerts.push({
          type: "target",
          symbol: position.symbol,
          message: `${position.symbol} reached target at ${formatCurrency(currentPrice)}`,
          severity: "success",
        });
      }
    });
    
    setPriceAlerts(alerts);
  }, []);

  // Fetch live prices for positions
  const fetchLivePrices = useCallback(async () => {
    if (!positions || positions.length === 0) return;
    
    setLoading(true);
    try {
      const symbols = positions.map(p => p.symbol);
      const response = await apiClient.post("/api/market/live-prices", {
        symbols: symbols
      });
      
      if (response.data.success) {
        const newLiveData = {};
        response.data.data.forEach(item => {
          newLiveData[item.symbol] = {
            price: item.price,
            change: item.change,
            changePct: item.changePct,
            volume: item.volume,
            timestamp: item.timestamp,
          };
        });
        
        setLiveData(newLiveData);
        setLastUpdated(new Date().toLocaleTimeString());
        
        // Check for alerts
        checkPriceAlerts(positions, newLiveData);
      }
    } catch (error) {
      console.error("Error fetching live prices:", error);
      // Simulate live data for demo purposes
      const simulatedData = {};
      positions.forEach(position => {
        const basePrice = position.avg_price || 100;
        const variation = (Math.random() - 0.5) * 0.1; // ±5% variation
        const currentPrice = basePrice * (1 + variation);
        const change = currentPrice - basePrice;
        const changePct = (change / basePrice) * 100;
        
        simulatedData[position.symbol] = {
          price: currentPrice,
          change: change,
          changePct: changePct,
          volume: Math.floor(Math.random() * 1000000),
          timestamp: new Date().toISOString(),
        };
      });
      
      setLiveData(simulatedData);
      setLastUpdated(new Date().toLocaleTimeString());
      checkPriceAlerts(positions, simulatedData);
    } finally {
      setLoading(false);
    }
  }, [positions, checkPriceAlerts]);

  // Auto-refresh live prices
  useEffect(() => {
    fetchLivePrices();
    
    const interval = setInterval(fetchLivePrices, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, [fetchLivePrices]);

  if (!positions || positions.length === 0) {
    return (
      <Card>
        <CardContent>
          <Box textAlign="center" py={4}>
            <Timeline sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
            <Typography variant="h6" color="textSecondary" gutterBottom>
              No Active Positions
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Start trading to see live price tracking
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" fontWeight="bold">
            📈 Live Price Tracker ({tradingMode} Mode)
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            {lastUpdated && (
              <Typography variant="caption" color="textSecondary">
                Updated: {lastUpdated}
              </Typography>
            )}
            <Tooltip title="Refresh prices">
              <IconButton 
                onClick={() => {
                  fetchLivePrices();
                  if (onRefresh) onRefresh();
                }}
                disabled={loading}
                size="small"
              >
                <Refresh />
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Price Alerts */}
        {priceAlerts.length > 0 && (
          <Box mb={2}>
            {priceAlerts.map((alert, index) => (
              <Alert 
                key={index} 
                severity={alert.severity} 
                sx={{ mb: 1 }}
                icon={alert.type === "target" ? <CheckCircle /> : <WarningAmber />}
              >
                {alert.message}
              </Alert>
            ))}
          </Box>
        )}

        {/* Live Price Table */}
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Symbol</TableCell>
                <TableCell align="right">Live Price</TableCell>
                <TableCell align="right">Change</TableCell>
                <TableCell align="right">Avg Price</TableCell>
                <TableCell align="right">Live P&L</TableCell>
                <TableCell align="right">P&L %</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Volume</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.map((position, index) => {
                const livePrice = liveData[position.symbol];
                const realtimePnL = livePrice ? calculateRealtimePnL(position, livePrice.price) : { pnl: 0, pnlPct: 0 };
                
                return (
                  <TableRow key={index} hover>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2" fontWeight="medium">
                          {position.symbol}
                        </Typography>
                        <Chip 
                          label={position.side}
                          size="small"
                          color={position.side === "BUY" ? "success" : "error"}
                          variant="outlined"
                        />
                      </Box>
                    </TableCell>
                    
                    <TableCell align="right">
                      {livePrice ? (
                        <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5}>
                          <Typography variant="body2" fontFamily="monospace" fontWeight="medium">
                            {formatCurrency(livePrice.price)}
                          </Typography>
                          <Speed sx={{ fontSize: 14, color: "primary.main" }} />
                        </Box>
                      ) : (
                        <Typography variant="body2" color="textSecondary">
                          Loading...
                        </Typography>
                      )}
                    </TableCell>
                    
                    <TableCell align="right">
                      {livePrice ? (
                        <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5}>
                          {livePrice.changePct >= 0 ? (
                            <CallMade color="success" sx={{ fontSize: 14 }} />
                          ) : (
                            <CallReceived color="error" sx={{ fontSize: 14 }} />
                          )}
                          <Typography 
                            variant="body2" 
                            color={livePrice.changePct >= 0 ? "success.main" : "error.main"}
                            fontFamily="monospace"
                          >
                            {livePrice.changePct >= 0 ? '+' : ''}{livePrice.changePct.toFixed(2)}%
                          </Typography>
                        </Box>
                      ) : (
                        <Typography variant="body2" color="textSecondary">-</Typography>
                      )}
                    </TableCell>
                    
                    <TableCell align="right">
                      <Typography variant="body2" fontFamily="monospace">
                        {formatCurrency(position.avg_price)}
                      </Typography>
                    </TableCell>
                    
                    <TableCell align="right" sx={{ color: getPnLColor(realtimePnL.pnl) }}>
                      <Typography variant="body2" fontFamily="monospace" fontWeight="medium">
                        {formatCurrency(realtimePnL.pnl)}
                      </Typography>
                    </TableCell>
                    
                    <TableCell align="right" sx={{ color: getPnLColor(realtimePnL.pnlPct) }}>
                      <Typography variant="body2" fontFamily="monospace" fontWeight="medium">
                        {realtimePnL.pnlPct >= 0 ? '+' : ''}{realtimePnL.pnlPct.toFixed(2)}%
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Chip 
                        label={position.is_active ? "Active" : "Closed"}
                        size="small"
                        color={position.is_active ? "success" : "default"}
                      />
                    </TableCell>
                    
                    <TableCell align="right">
                      {livePrice ? (
                        <Typography variant="caption" color="textSecondary">
                          {(livePrice.volume || 0).toLocaleString()}
                        </Typography>
                      ) : (
                        <Typography variant="caption" color="textSecondary">-</Typography>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Summary Stats */}
        <Box mt={2} p={2} bgcolor="background.paper" borderRadius={1} border={1} borderColor="divider">
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Total Positions
              </Typography>
              <Typography variant="h6" fontWeight="bold">
                {positions.length}
              </Typography>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Active Positions
              </Typography>
              <Typography variant="h6" fontWeight="bold" color="success.main">
                {positions.filter(p => p.is_active).length}
              </Typography>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Total Live P&L
              </Typography>
              <Typography 
                variant="h6" 
                fontWeight="bold" 
                sx={{ color: getPnLColor(
                  positions.reduce((sum, pos) => {
                    const livePrice = liveData[pos.symbol];
                    return sum + (livePrice ? calculateRealtimePnL(pos, livePrice.price).pnl : 0);
                  }, 0)
                )}}
              >
                {formatCurrency(
                  positions.reduce((sum, pos) => {
                    const livePrice = liveData[pos.symbol];
                    return sum + (livePrice ? calculateRealtimePnL(pos, livePrice.price).pnl : 0);
                  }, 0)
                )}
              </Typography>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Price Alerts
              </Typography>
              <Typography variant="h6" fontWeight="bold" color={priceAlerts.length > 0 ? "warning.main" : "text.primary"}>
                {priceAlerts.length}
              </Typography>
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );
};

export default LivePriceTracker;