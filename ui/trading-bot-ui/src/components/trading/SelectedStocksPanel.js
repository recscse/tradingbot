// components/trading/SelectedStocksPanel.js - Updated for Market Timing
import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  Paper,
  IconButton,
  Tooltip,
  Stack,
  Divider,
} from "@mui/material";
import {
  TrendingUp,
  ShowChart,
  Refresh,
  CheckCircle,
  Error,
  Schedule,
  CallMade,
  CallReceived,
} from "@mui/icons-material";
import apiClient from "../../services/api";

const SelectedStocksPanel = ({ 
  onStockSelect, 
  onStartTrading, 
  tradingMode = "PAPER",
  showTradingControls = true 
}) => {
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectionStatus, setSelectionStatus] = useState(null);
  const [selectedForTrading, setSelectedForTrading] = useState([]);

  // Fetch selected stocks from the trading selection API
  const fetchSelectedStocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get("/api/v1/trading/stocks/selected", {
        params: {
          include_options: true,
        }
      });
      
      if (response.data.success) {
        const responseData = response.data;
        
        // Set stocks data
        setSelectedStocks(responseData.data || []);
        setLastUpdated(new Date().toLocaleTimeString());
        
        // Set market timing status information
        setSelectionStatus({
          market_status: responseData.market_status,
          market_message: responseData.market_message,
          show_stocks: responseData.show_stocks,
          can_trade: responseData.can_trade,
          next_selection: responseData.next_selection,
          total_selected: responseData.total_selected,
          selection_date: responseData.selection_date
        });
        
        // Auto-select all stocks for trading if none selected and if stocks should be shown
        if (selectedForTrading.length === 0 && responseData.data.length > 0 && responseData.show_stocks) {
          const stockSymbols = responseData.data.map(stock => stock.symbol);
          setSelectedForTrading(stockSymbols);
          
          // Notify parent component
          if (onStockSelect) {
            onStockSelect(responseData.data);
          }
        } else if (!responseData.show_stocks) {
          // Clear selection if stocks shouldn't be shown (market closed, etc.)
          setSelectedForTrading([]);
        }
      } else {
        // API call succeeded but no success flag - set basic status
        setSelectionStatus({
          market_status: "error",
          market_message: "No stocks selected for today",
          show_stocks: false,
          can_trade: false,
          next_selection: "Check market timing",
          total_selected: 0,
          selection_date: new Date().toISOString().split('T')[0]
        });
        setError("No stocks selected for today");
      }
    } catch (err) {
      console.error("Error fetching selected stocks:", err);
      setError("Failed to load selected stocks");
      // Set error status
      setSelectionStatus({
        market_status: "error",
        market_message: "Unable to load stock selection data",
        show_stocks: false,
        can_trade: false,
        next_selection: "Retry needed",
        total_selected: 0,
        selection_date: new Date().toISOString().split('T')[0]
      });
    } finally {
      setLoading(false);
    }
  }, [selectedForTrading.length, onStockSelect]);

  // Initial load and periodic refresh
  useEffect(() => {
    fetchSelectedStocks();
    
    // Refresh every 5 minutes during market hours
    const interval = setInterval(fetchSelectedStocks, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [fetchSelectedStocks]);

  // Get status color and icon
  const getStatusDisplay = (status) => {
    switch (status) {
      case "market_open_ready":
        return { color: "success", icon: <CheckCircle />, severity: "success" };
      case "pre_market_ready":
        return { color: "warning", icon: <Schedule />, severity: "warning" };
      case "market_closed_with_stocks":
        return { color: "info", icon: <ShowChart />, severity: "info" };
      case "weekend":
      case "after_hours_no_stocks":
        return { color: "default", icon: <Schedule />, severity: "info" };
      case "error":
        return { color: "error", icon: <Error />, severity: "error" };
      default:
        return { color: "default", icon: <Schedule />, severity: "info" };
    }
  };

  // Format price display
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2
    }).format(price).replace('₹', '₹');
  };

  const statusDisplay = selectionStatus ? getStatusDisplay(selectionStatus.market_status) : null;

  return (
    <Card elevation={2}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" fontWeight="bold">
            📊 Selected Stocks
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {selectionStatus?.total_selected > 0 && (
              <Chip 
                label={`${selectionStatus.total_selected} selected`} 
                color="primary" 
                size="small" 
              />
            )}
            <Tooltip title="Refresh stock data">
              <IconButton onClick={fetchSelectedStocks} disabled={loading} size="small">
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {loading && (
          <Box display="flex" justifyContent="center" p={2}>
            <CircularProgress size={24} />
          </Box>
        )}

        {/* Market Status Alert */}
        {selectionStatus && statusDisplay && (
          <Alert 
            severity={statusDisplay.severity} 
            icon={statusDisplay.icon}
            sx={{ mb: 2 }}
          >
            <Typography variant="body2" fontWeight="medium">
              {selectionStatus.market_message}
            </Typography>
            
            {selectionStatus.next_selection && (
              <Typography variant="caption" color="textSecondary" display="block" mt={1}>
                Next selection: {selectionStatus.next_selection}
              </Typography>
            )}
            
            {selectionStatus.selection_date && (
              <Typography variant="caption" color="textSecondary" display="block">
                Selection date: {selectionStatus.selection_date}
              </Typography>
            )}
          </Alert>
        )}

        {error && !loading && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Display selected stocks if available and should be shown */}
        {selectionStatus?.show_stocks && selectedStocks.length > 0 && (
          <>
            {/* Stock Selection Summary */}
            <Box bgcolor="background.paper" borderRadius={1} border={1} borderColor="divider" p={2} mb={2}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm={6}>
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <ShowChart color="primary" />
                    <Typography variant="subtitle2">
                      Today's Algorithm Selection ({selectionStatus.selection_date})
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="textSecondary" mt={0.5}>
                    {selectionStatus.total_selected} stocks selected for trading
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Chip
                      label={selectionStatus.can_trade ? "Trading Active" : "Trading Disabled"}
                      color={selectionStatus.can_trade ? "success" : "default"}
                      size="small"
                      icon={selectionStatus.can_trade ? <TrendingUp /> : <Schedule />}
                    />
                  </Stack>
                </Grid>
              </Grid>
            </Box>

            {/* Selected Stocks Table */}
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Symbol</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">Change %</TableCell>
                    <TableCell>Sector</TableCell>
                    <TableCell align="right">Score</TableCell>
                    <TableCell>Reason</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {selectedStocks.map((stock) => (
                    <TableRow key={stock.symbol} hover>
                      <TableCell>
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body2" fontWeight="medium">
                            {stock.symbol}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontFamily="monospace">
                          {formatPrice(stock.price_at_selection)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5}>
                          {stock.change_percent_at_selection >= 0 ? (
                            <CallMade color="success" sx={{ fontSize: 16 }} />
                          ) : (
                            <CallReceived color="error" sx={{ fontSize: 16 }} />
                          )}
                          <Typography 
                            variant="body2" 
                            color={stock.change_percent_at_selection >= 0 ? "success.main" : "error.main"}
                            fontFamily="monospace"
                          >
                            {stock.change_percent_at_selection >= 0 ? '+' : ''}{stock.change_percent_at_selection?.toFixed(2)}%
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={stock.sector} 
                          size="small" 
                          variant="outlined"
                          color="default"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography 
                          variant="body2" 
                          fontWeight="medium"
                          color="primary.main"
                        >
                          {stock.selection_score?.toFixed(1)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="textSecondary">
                          {stock.selection_reason}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {lastUpdated && (
              <Typography variant="caption" color="textSecondary" display="block" mt={1} textAlign="right">
                Last updated: {lastUpdated}
              </Typography>
            )}
          </>
        )}

        {/* No stocks message when stocks shouldn't be shown */}
        {selectionStatus && !selectionStatus.show_stocks && !loading && (
          <Box textAlign="center" py={4}>
            <Schedule color="disabled" sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="body1" color="textSecondary" gutterBottom>
              {selectionStatus.market_message}
            </Typography>
            {selectionStatus.next_selection && (
              <Typography variant="caption" color="textSecondary">
                Next selection: {selectionStatus.next_selection}
              </Typography>
            )}
          </Box>
        )}

        <Divider sx={{ my: 2 }} />
        
        {/* Information Section */}
        <Box bgcolor="grey.50" borderRadius={1} p={2}>
          <Typography variant="subtitle2" gutterBottom>
            ℹ️ How Stock Selection Works
          </Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            • Stocks are automatically selected at 9:00 AM on trading days
          </Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            • Algorithm analyzes market sentiment, volume, and technical patterns
          </Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            • No manual intervention required - fully automated process
          </Typography>
          <Typography variant="body2" color="textSecondary">
            • Trading is enabled only during market hours (9:15 AM - 3:30 PM)
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default SelectedStocksPanel;