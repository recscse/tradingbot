// components/trading/SelectedStocksPanel.js
import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  Chip,
  Button,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  Badge,
  Stack,
  Divider,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  ShowChart,
  AccountBalance,
  Refresh,
  ExpandMore,
  CallMade,
  CallReceived,
  Schedule,
  Analytics,
  CheckCircle,
  Error,
  Warning,
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
            onStockSelect(response.data.data);
          }
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
  }, [onStockSelect, selectedForTrading.length]);

  // Fetch selection status
  const fetchSelectionStatus = useCallback(async () => {
    try {
      const response = await apiClient.get("/api/v1/trading/stocks/selection-status");
      if (response.data.success) {
        setSelectionStatus(response.data);
      }
    } catch (err) {
      console.error("Error fetching selection status:", err);
    }
  }, []);

  // Run fresh stock selection
  const runStockSelection = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post("/api/v1/trading/stocks/select", {
        force_refresh: true
      });
      
      if (response.data.success) {
        await fetchSelectedStocks();
        alert(`Successfully selected ${response.data.total_selected} stocks!`);
      } else {
        setError(response.data.message || "Stock selection failed");
      }
    } catch (err) {
      console.error("Error running stock selection:", err);
      setError("Failed to run stock selection");
    } finally {
      setLoading(false);
    }
  };

  // Toggle stock selection for trading
  const toggleStockForTrading = (symbol) => {
    const newSelection = selectedForTrading.includes(symbol)
      ? selectedForTrading.filter(s => s !== symbol)
      : [...selectedForTrading, symbol];
    
    setSelectedForTrading(newSelection);
    
    // Update parent with selected stocks data
    if (onStockSelect) {
      const selectedStockData = selectedStocks.filter(stock => 
        newSelection.includes(stock.symbol)
      );
      onStockSelect(selectedStockData);
    }
  };

  // Start trading with selected stocks
  const handleStartTrading = () => {
    if (selectedForTrading.length === 0) {
      alert("Please select at least one stock for trading");
      return;
    }
    
    const selectedStockData = selectedStocks.filter(stock => 
      selectedForTrading.includes(stock.symbol)
    );
    
    if (onStartTrading) {
      onStartTrading(selectedStockData, tradingMode);
    }
  };

  // Format currency
  const formatCurrency = (amount) => {
    if (amount == null) return "N/A";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amount);
  };

  // Get option type color
  const getOptionTypeColor = (optionType) => {
    switch (optionType) {
      case "CE":
        return "success";
      case "PE":
        return "error";
      default:
        return "default";
    }
  };

  // Get option type icon
  const getOptionTypeIcon = (optionType) => {
    switch (optionType) {
      case "CE":
        return <CallMade />;
      case "PE":
        return <CallReceived />;
      default:
        return <ShowChart />;
    }
  };

  useEffect(() => {
    fetchSelectedStocks();
    fetchSelectionStatus();
    
    // Refresh every 5 minutes during trading hours
    const interval = setInterval(() => {
      const now = new Date();
      const hour = now.getHours();
      // Refresh between 9 AM and 4 PM
      if (hour >= 9 && hour <= 16) {
        fetchSelectedStocks();
      }
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [fetchSelectedStocks, fetchSelectionStatus]);

  if (loading && selectedStocks.length === 0) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="center" alignItems="center" py={4}>
            <CircularProgress />
            <Typography variant="body1" sx={{ ml: 2 }}>
              Loading selected stocks...
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
          <Typography variant="h6" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <AccountBalance color="primary" />
            Today's Selected Stocks
            {selectedStocks.length > 0 && (
              <Badge badgeContent={selectedStocks.length} color="primary" />
            )}
          </Typography>
          
          <Box>
            {lastUpdated && (
              <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                Updated: {lastUpdated}
              </Typography>
            )}
            <Tooltip title="Refresh Selection">
              <IconButton onClick={fetchSelectedStocks} disabled={loading}>
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Trading Mode Indicator */}
        <Box mb={2}>
          <Chip
            label={`${tradingMode} Trading Mode`}
            color={tradingMode === "LIVE" ? "error" : "success"}
            icon={tradingMode === "LIVE" ? <Warning /> : <CheckCircle />}
            variant="filled"
          />
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
            {selectionStatus?.recommendations?.run_selection && (
              <Box mt={1}>
                <Button size="small" onClick={runStockSelection} disabled={loading}>
                  Run Stock Selection
                </Button>
              </Box>
            )}
          </Alert>
        )}

        {selectedStocks.length === 0 ? (
          <Alert severity="info">
            <Typography variant="body1">No stocks selected for today.</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Stock selection runs automatically at 9:00 AM during market days, or you can run it manually.
            </Typography>
            <Box mt={2}>
              <Button
                variant="contained"
                onClick={runStockSelection}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={16} /> : <Analytics />}
              >
                {loading ? "Selecting..." : "Run Stock Selection"}
              </Button>
            </Box>
          </Alert>
        ) : (
          <>
            {/* Stock Selection Summary */}
            <Box mb={3}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: "center" }}>
                    <Typography variant="h4" color="primary">
                      {selectedStocks.length}
                    </Typography>
                    <Typography variant="body2">Stocks Selected</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: "center" }}>
                    <Typography variant="h4" color="success.main">
                      {selectedStocks.filter(s => s.has_options).length}
                    </Typography>
                    <Typography variant="body2">Options Ready</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: "center" }}>
                    <Typography variant="h4" color="secondary">
                      {selectedForTrading.length}
                    </Typography>
                    <Typography variant="body2">For Trading</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: "center" }}>
                    <Typography variant="h4" color="info.main">
                      {[...new Set(selectedStocks.map(s => s.sector))].length}
                    </Typography>
                    <Typography variant="body2">Sectors</Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Box>

            {/* Selected Stocks Table */}
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">Trade</TableCell>
                    <TableCell>Stock</TableCell>
                    <TableCell>Sector</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="center">Score</TableCell>
                    <TableCell align="center">Options</TableCell>
                    <TableCell>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {selectedStocks.map((stock) => (
                    <TableRow key={stock.symbol}>
                      <TableCell padding="checkbox">
                        <Tooltip title={`${selectedForTrading.includes(stock.symbol) ? 'Remove from' : 'Add to'} trading`}>
                          <IconButton
                            size="small"
                            color={selectedForTrading.includes(stock.symbol) ? "primary" : "default"}
                            onClick={() => toggleStockForTrading(stock.symbol)}
                          >
                            {selectedForTrading.includes(stock.symbol) ? <CheckCircle /> : <Error />}
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                      
                      <TableCell>
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold">
                            {stock.symbol}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {stock.instrument_key?.split('|')[1] || 'N/A'}
                          </Typography>
                        </Box>
                      </TableCell>
                      
                      <TableCell>
                        <Chip size="small" label={stock.sector} variant="outlined" />
                      </TableCell>
                      
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight="bold">
                          {formatCurrency(stock.price_at_selection)}
                        </Typography>
                      </TableCell>
                      
                      <TableCell align="center">
                        <Chip
                          size="small"
                          label={stock.selection_score?.toFixed(1)}
                          color={stock.selection_score > 8 ? "success" : stock.selection_score > 6 ? "warning" : "default"}
                        />
                      </TableCell>
                      
                      <TableCell align="center">
                        {stock.has_options ? (
                          <Stack direction="row" spacing={0.5} alignItems="center" justifyContent="center">
                            <Chip
                              size="small"
                              icon={getOptionTypeIcon(stock.option_type)}
                              label={stock.option_type || "N/A"}
                              color={getOptionTypeColor(stock.option_type)}
                            />
                            <Typography variant="caption">
                              {stock.option_contracts_available}
                            </Typography>
                          </Stack>
                        ) : (
                          <Chip size="small" label="N/A" color="default" />
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <Accordion sx={{ boxShadow: 0 }}>
                          <AccordionSummary expandIcon={<ExpandMore />} sx={{ minHeight: 0, '& .MuiAccordionSummary-content': { margin: 0 } }}>
                            <Typography variant="caption">View Details</Typography>
                          </AccordionSummary>
                          <AccordionDetails sx={{ pt: 0 }}>
                            <Stack spacing={1}>
                              <Typography variant="caption">
                                <strong>Reason:</strong> {stock.selection_reason || "N/A"}
                              </Typography>
                              
                              {stock.option_contract && (
                                <Box>
                                  <Typography variant="caption" color="primary">
                                    <strong>ATM Contract:</strong>
                                  </Typography>
                                  <Typography variant="caption" display="block">
                                    Strike: ₹{stock.option_contract.strike_price}
                                  </Typography>
                                  <Typography variant="caption" display="block">
                                    Lot: {stock.option_contract.lot_size}
                                  </Typography>
                                  <Typography variant="caption" display="block">
                                    Expiry: {stock.option_expiry_date}
                                  </Typography>
                                </Box>
                              )}
                              
                              {stock.option_expiry_dates && stock.option_expiry_dates.length > 1 && (
                                <Box>
                                  <Typography variant="caption">
                                    <strong>Available Expiries:</strong> {stock.option_expiry_dates.length}
                                  </Typography>
                                </Box>
                              )}
                            </Stack>
                          </AccordionDetails>
                        </Accordion>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Trading Controls */}
            {showTradingControls && (
              <Box mt={3}>
                <Divider sx={{ mb: 2 }} />
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={6}>
                    <Alert severity={tradingMode === "LIVE" ? "error" : "info"}>
                      <Typography variant="body2">
                        {selectedForTrading.length} stocks selected for {tradingMode.toLowerCase()} trading
                      </Typography>
                    </Alert>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Stack direction="row" spacing={2} justifyContent="flex-end">
                      <Button
                        variant="contained"
                        color={tradingMode === "LIVE" ? "error" : "primary"}
                        onClick={handleStartTrading}
                        disabled={selectedForTrading.length === 0 || loading}
                        startIcon={<TrendingUp />}
                      >
                        Start {tradingMode} Trading
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={runStockSelection}
                        disabled={loading}
                        startIcon={<Refresh />}
                      >
                        Refresh Selection
                      </Button>
                    </Stack>
                  </Grid>
                </Grid>
              </Box>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default SelectedStocksPanel;