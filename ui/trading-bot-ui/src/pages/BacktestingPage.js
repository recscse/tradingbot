import React, { useState } from "react";
import {
  Container,
  Typography,
  Grid,
  TextField,
  MenuItem,
  Button,
  CircularProgress,
  Box,
  Card,
  CardContent,
  Alert,
  Chip,
  Stack,
  useTheme,
  useMediaQuery,
  IconButton,
  Collapse,
} from "@mui/material";
import {
  PlayArrow,
  Analytics,
  Assessment,
  ExpandLess,
  Timeline,
  DataUsage,
  Speed,
} from "@mui/icons-material";
import axios from "axios";
import StockSearch from "../components/trading/StockSearch";

const BacktestingPage = () => {
  const [interval, setInterval] = useState("1minute");
  const [selectedStock, setSelectedStock] = useState(null);
  const [loading, setLoading] = useState(false);
  const [candles, setCandles] = useState([]);
  const [report, setReport] = useState(null);
  const [tradeLog, setTradeLog] = useState([]);
  const [expandedSections, setExpandedSections] = useState({
    tradeLog: false,
    candleData: false,
  });

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md"));

  const handleRunBacktest = async () => {
    if (!selectedStock) return;

    setLoading(true);
    setReport(null);
    setTradeLog([]);
    setCandles([]);

    try {
      const res = await axios.get(`/api/backtesting/intraday-candles`, {
        params: {
          instrument_key: selectedStock.instrumentKey,
          interval,
        },
      });

      const candleData = res.data.candles || [];
      setCandles(candleData);

      const strategyRes = await axios.post(
        "/api/backtesting/execute-strategy",
        {
          instrument_key: selectedStock.instrumentKey,
          interval,
          candles: candleData,
          strategy: "sma_crossover",
        }
      );

      setReport(strategyRes.data.report || null);
      setTradeLog(strategyRes.data.trades || []);
    } catch (err) {
      console.error("Backtest error:", err);
    }

    setLoading(false);
  };

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const intervalOptions = [
    { value: "1minute", label: isMobile ? "1m" : "1 Minute" },
    { value: "15minute", label: isMobile ? "15m" : "15 Minute" },
    { value: "30minute", label: isMobile ? "30m" : "30 Minute" },
    { value: "day", label: "Day" },
    { value: "week", label: "Week" },
    { value: "month", label: "Month" },
  ];

  return (
    <Container
      maxWidth="xl"
      sx={{
        py: { xs: 2, sm: 3, md: 4 },
        px: { xs: 1, sm: 2 },
      }}
    >
      {/* Header Section */}
      <Box sx={{ mb: { xs: 3, sm: 4 } }}>
        <Typography
          variant="h4"
          fontWeight={700}
          gutterBottom
          color="primary"
          sx={{
            fontSize: { xs: "1.75rem", sm: "2rem", md: "2.5rem" },
            textAlign: { xs: "center", sm: "left" },
            background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            display: "flex",
            alignItems: "center",
            justifyContent: { xs: "center", sm: "flex-start" },
            gap: 1,
          }}
        >
          <Analytics sx={{ fontSize: "inherit" }} />
          Strategy Backtesting
        </Typography>

        <Typography
          variant="body1"
          color="text.secondary"
          sx={{
            fontSize: { xs: "0.875rem", sm: "1rem" },
            textAlign: { xs: "center", sm: "left" },
            maxWidth: 600,
          }}
        >
          Test your trading strategies against historical data to optimize
          performance
        </Typography>
      </Box>

      {/* Configuration Section */}
      <Card className="trading-card" sx={{ mb: 3 }}>
        <CardContent className="spacing-responsive">
          <Typography
            variant="h6"
            gutterBottom
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              fontSize: { xs: "1.1rem", sm: "1.25rem" },
              mb: 3,
            }}
          >
            <Speed color="primary" />
            Backtest Configuration
          </Typography>

          <Grid
            container
            spacing={{ xs: 2, sm: 3 }}
            className="form-responsive"
          >
            {/* Stock Search */}
            <Grid item xs={12} lg={6}>
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Select Stock/Instrument
                </Typography>
              </Box>
              <StockSearch
                onSearch={(stock) => setSelectedStock(stock)}
                sx={{
                  "& .MuiTextField-root": {
                    "& .MuiInputBase-root": {
                      minHeight: 48,
                      fontSize: { xs: "1rem", sm: "1.1rem" },
                    },
                  },
                }}
              />
            </Grid>

            {/* Interval Selection */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Time Interval
                </Typography>
              </Box>
              <TextField
                select
                label="Interval"
                value={interval}
                fullWidth
                onChange={(e) => setInterval(e.target.value)}
                className="touch-button"
                sx={{
                  "& .MuiInputBase-root": {
                    minHeight: 48,
                    fontSize: { xs: "1rem", sm: "1.1rem" },
                  },
                }}
              >
                {intervalOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            {/* Run Button */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Execute
                </Typography>
              </Box>
              <Button
                variant="contained"
                color="success"
                fullWidth
                disabled={!selectedStock || loading}
                onClick={handleRunBacktest}
                startIcon={
                  loading ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <PlayArrow />
                  )
                }
                className="touch-button"
                sx={{
                  minHeight: 48,
                  fontSize: { xs: "0.9rem", sm: "1rem" },
                  fontWeight: 600,
                }}
              >
                {loading ? "Running..." : "Run Backtest"}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Selected Stock Display */}
      {selectedStock && (
        <Alert
          severity="info"
          sx={{
            mb: 3,
            "& .MuiAlert-message": {
              width: "100%",
            },
          }}
        >
          <Box>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Selected: {selectedStock.symbol} ({selectedStock.exchange})
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Instrument Key: {selectedStock.instrumentKey || "Not available"}
            </Typography>
          </Box>
        </Alert>
      )}

      {/* Results Section */}
      {report && (
        <Grid container spacing={{ xs: 2, sm: 3 }} sx={{ mb: 3 }}>
          {/* Report Summary */}
          <Grid item xs={12} lg={8}>
            <Card className="trading-card">
              <CardContent className="spacing-responsive">
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    fontSize: { xs: "1.1rem", sm: "1.25rem" },
                  }}
                >
                  <Assessment color="primary" />
                  Backtest Results
                </Typography>

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={4}>
                    <Box
                      sx={{
                        textAlign: "center",
                        p: 2,
                        bgcolor: "action.hover",
                        borderRadius: 2,
                      }}
                    >
                      <Typography
                        variant="h4"
                        color="primary.main"
                        fontWeight={700}
                      >
                        {report.totalTrades}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Trades
                      </Typography>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6} md={4}>
                    <Box
                      sx={{
                        textAlign: "center",
                        p: 2,
                        bgcolor: "success.light",
                        borderRadius: 2,
                        color: "success.contrastText",
                      }}
                    >
                      <Typography variant="h4" fontWeight={700}>
                        {report.winTrades}
                      </Typography>
                      <Typography variant="body2">Winning Trades</Typography>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6} md={4}>
                    <Box
                      sx={{
                        textAlign: "center",
                        p: 2,
                        bgcolor: "error.light",
                        borderRadius: 2,
                        color: "error.contrastText",
                      }}
                    >
                      <Typography variant="h4" fontWeight={700}>
                        {report.lossTrades}
                      </Typography>
                      <Typography variant="body2">Losing Trades</Typography>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Box
                      sx={{
                        textAlign: "center",
                        p: 2,
                        bgcolor: "info.light",
                        borderRadius: 2,
                        color: "info.contrastText",
                      }}
                    >
                      <Typography variant="h4" fontWeight={700}>
                        {report.winRate}%
                      </Typography>
                      <Typography variant="body2">Win Rate</Typography>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Box
                      sx={{
                        textAlign: "center",
                        p: 2,
                        bgcolor:
                          report.netProfit >= 0 ? "success.main" : "error.main",
                        borderRadius: 2,
                        color: "white",
                      }}
                    >
                      <Typography variant="h4" fontWeight={700}>
                        ₹{Number(report.netProfit).toLocaleString()}
                      </Typography>
                      <Typography variant="body2">Net P&L</Typography>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Quick Actions */}
          <Grid item xs={12} lg={4}>
            <Stack spacing={2}>
              <Card className="trading-card">
                <CardContent className="spacing-responsive">
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{ fontSize: { xs: "1.1rem", sm: "1.25rem" } }}
                  >
                    Quick Actions
                  </Typography>

                  <Stack spacing={1.5}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<Timeline />}
                      onClick={() => toggleSection("tradeLog")}
                      className="touch-button"
                    >
                      {expandedSections.tradeLog ? "Hide" : "Show"} Trade Log
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<DataUsage />}
                      onClick={() => toggleSection("candleData")}
                      className="touch-button"
                    >
                      {expandedSections.candleData ? "Hide" : "Show"} Raw Data
                    </Button>
                  </Stack>
                </CardContent>
              </Card>

              {/* Performance Chip */}
              <Box sx={{ textAlign: "center" }}>
                <Chip
                  label={
                    report.netProfit >= 0
                      ? "PROFITABLE STRATEGY"
                      : "NEEDS OPTIMIZATION"
                  }
                  color={report.netProfit >= 0 ? "success" : "error"}
                  variant="filled"
                  sx={{
                    fontWeight: 600,
                    fontSize: { xs: "0.8rem", sm: "0.9rem" },
                    px: 2,
                  }}
                />
              </Box>
            </Stack>
          </Grid>
        </Grid>
      )}

      {/* Expandable Trade Log */}
      {tradeLog.length > 0 && (
        <Collapse in={expandedSections.tradeLog}>
          <Card className="trading-card" sx={{ mb: 3 }}>
            <CardContent className="spacing-responsive">
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 2,
                }}
              >
                <Typography
                  variant="h6"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    fontSize: { xs: "1.1rem", sm: "1.25rem" },
                  }}
                >
                  <Timeline color="primary" />
                  Trade Log ({tradeLog.length} trades)
                </Typography>
                <IconButton
                  onClick={() => toggleSection("tradeLog")}
                  size="small"
                >
                  <ExpandLess />
                </IconButton>
              </Box>

              <Box className="trading-table-container custom-scrollbar">
                <pre
                  style={{
                    maxHeight: isMobile ? 250 : 400,
                    overflow: "auto",
                    background:
                      theme.palette.mode === "dark" ? "#1a1a1a" : "#f5f5f5",
                    padding: isMobile ? 12 : 16,
                    fontSize: isMobile ? 11 : 13,
                    borderRadius: 8,
                    lineHeight: 1.4,
                    margin: 0,
                    fontFamily: "'Courier New', monospace",
                  }}
                  className="custom-scrollbar"
                >
                  {JSON.stringify(
                    tradeLog.slice(0, isMobile ? 10 : 20),
                    null,
                    2
                  )}
                </pre>
              </Box>
            </CardContent>
          </Card>
        </Collapse>
      )}

      {/* Expandable Candle Data */}
      {candles.length > 0 && (
        <Collapse in={expandedSections.candleData}>
          <Card className="trading-card">
            <CardContent className="spacing-responsive">
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 2,
                }}
              >
                <Typography
                  variant="h6"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    fontSize: { xs: "1.1rem", sm: "1.25rem" },
                  }}
                >
                  <DataUsage color="primary" />
                  Raw Candle Data ({candles.length} candles)
                </Typography>
                <IconButton
                  onClick={() => toggleSection("candleData")}
                  size="small"
                >
                  <ExpandLess />
                </IconButton>
              </Box>

              <Box className="trading-table-container custom-scrollbar">
                <pre
                  style={{
                    maxHeight: isMobile ? 250 : 300,
                    overflow: "auto",
                    background:
                      theme.palette.mode === "dark" ? "#1a1a1a" : "#f9f9f9",
                    padding: isMobile ? 12 : 16,
                    fontSize: isMobile ? 11 : 13,
                    borderRadius: 8,
                    lineHeight: 1.4,
                    margin: 0,
                    fontFamily: "'Courier New', monospace",
                  }}
                  className="custom-scrollbar"
                >
                  {JSON.stringify(candles.slice(0, isMobile ? 5 : 10), null, 2)}
                </pre>
              </Box>
            </CardContent>
          </Card>
        </Collapse>
      )}

      {/* Mobile-specific help */}
      {isMobile && !report && !loading && (
        <Alert severity="info" sx={{ mt: 3 }}>
          <Typography variant="body2">
            <strong>Mobile Tip:</strong> Select a stock and interval, then tap
            "Run Backtest" to analyze historical performance.
          </Typography>
        </Alert>
      )}
    </Container>
  );
};

export default BacktestingPage;
