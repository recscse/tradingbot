import React from "react";
import {
  Box,
  Grid,
  Stack,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Collapse,
  Alert,
} from "@mui/material";
import {
  Assessment as AssessmentIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  SignalCellularAlt as SignalIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";

const StockActivityChart = ({ stockActivityStats, showLiveActivity, setShowLiveActivity }) => {
  if (Object.keys(stockActivityStats).length === 0) {
    return null;
  }

  const maxActivity = Math.max(...Object.values(stockActivityStats).map(s => (s.signals || 0) + (s.trades || 0)));

  return (
    <Grid item xs={12}>
      <Card elevation={2}>
        <CardContent>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ mb: showLiveActivity ? 2.5 : 0 }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <AssessmentIcon color="primary" sx={{ fontSize: 28 }} />
              <Typography variant="h6" fontWeight={600}>
                Live Stock Activity
              </Typography>
              <Chip
                label={`${Object.keys(stockActivityStats).length} stocks active`}
                size="small"
                color="primary"
                variant="outlined"
              />
            </Box>
            <Button
              size="small"
              onClick={() => setShowLiveActivity(!showLiveActivity)}
              endIcon={
                showLiveActivity ? <ExpandLessIcon /> : <ExpandMoreIcon />
              }
            >
              {showLiveActivity ? "Hide" : "Show"}
            </Button>
          </Stack>

          <Collapse in={showLiveActivity}>
            <Box sx={{ mt: 2 }}>
              {Object.keys(stockActivityStats).length === 0 ? (
                <Alert severity="info" sx={{ borderRadius: 2 }}>
                  No stock activity yet. Bars will appear here as signals and trades happen.
                </Alert>
              ) : (
                <Grid container spacing={2}>
                  {Object.values(stockActivityStats)
                    .sort((a, b) => (b.signals + b.trades) - (a.signals + a.trades))
                    .map((stock) => {
                      const totalActivity = (stock.signals || 0) + (stock.trades || 0);
                      const signalsPercent = maxActivity > 0 ? ((stock.signals || 0) / maxActivity) * 100 : 0;
                      const tradesPercent = maxActivity > 0 ? ((stock.trades || 0) / maxActivity) * 100 : 0;

                      return (
                        <Grid item xs={12} key={stock.symbol}>
                          <Box
                            sx={{
                              p: 2,
                              bgcolor: "background.default",
                              borderRadius: 2,
                              border: 1,
                              borderColor: "divider",
                              transition: "all 0.3s",
                              "&:hover": {
                                borderColor: "primary.main",
                                boxShadow: 3,
                                transform: "translateY(-2px)",
                              },
                            }}
                          >
                            <Stack direction="row" spacing={2} alignItems="center">
                              {/* Stock Symbol */}
                              <Box sx={{ minWidth: 120 }}>
                                <Typography variant="h6" fontWeight={700} color="primary.main">
                                  {stock.symbol}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {new Date(stock.lastActivity).toLocaleTimeString("en-IN", {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </Typography>
                              </Box>

                              {/* Visual Bar Chart */}
                              <Box sx={{ flex: 1 }}>
                                <Box sx={{ mb: 0.5, display: "flex", justifyContent: "space-between" }}>
                                  <Typography variant="caption" fontWeight={600} color="text.secondary">
                                    Activity Level
                                  </Typography>
                                  <Typography variant="caption" fontWeight={600} color="primary.main">
                                    {totalActivity} total events
                                  </Typography>
                                </Box>
                                <Box
                                  sx={{
                                    height: 40,
                                    bgcolor: "action.hover",
                                    borderRadius: 1,
                                    overflow: "hidden",
                                    position: "relative",
                                    border: 1,
                                    borderColor: "divider",
                                  }}
                                >
                                  {/* Signals Bar (Blue) */}
                                  <Box
                                    sx={{
                                      position: "absolute",
                                      left: 0,
                                      top: 0,
                                      height: "100%",
                                      width: `${signalsPercent}%`,
                                      bgcolor: "info.main",
                                      transition: "width 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                                      display: "flex",
                                      alignItems: "center",
                                      pl: 1,
                                    }}
                                  >
                                    {stock.signals > 0 && (
                                      <Typography variant="caption" color="white" fontWeight={700}>
                                        {stock.signals} signal{stock.signals > 1 ? "s" : ""}
                                      </Typography>
                                    )}
                                  </Box>

                                  {/* Trades Bar (Green) - Stacked after signals */}
                                  <Box
                                    sx={{
                                      position: "absolute",
                                      left: `${signalsPercent}%`,
                                      top: 0,
                                      height: "100%",
                                      width: `${tradesPercent}%`,
                                      bgcolor: "success.main",
                                      transition: "all 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
                                      display: "flex",
                                      alignItems: "center",
                                      pl: 1,
                                    }}
                                  >
                                    {stock.trades > 0 && (
                                      <Typography variant="caption" color="white" fontWeight={700}>
                                        {stock.trades} trade{stock.trades > 1 ? "s" : ""}
                                      </Typography>
                                    )}
                                  </Box>
                                </Box>

                                {/* Legend */}
                                <Stack direction="row" spacing={2} sx={{ mt: 0.5 }}>
                                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                    <Box sx={{ width: 12, height: 12, bgcolor: "info.main", borderRadius: "50%" }} />
                                    <Typography variant="caption" color="text.secondary">
                                      Signals
                                    </Typography>
                                  </Box>
                                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                    <Box sx={{ width: 12, height: 12, bgcolor: "success.main", borderRadius: "50%" }} />
                                    <Typography variant="caption" color="text.secondary">
                                      Trades
                                    </Typography>
                                  </Box>
                                </Stack>
                              </Box>

                              {/* Stats Summary */}
                              <Stack direction="row" spacing={1}>
                                <Chip
                                  icon={<SignalIcon />}
                                  label={stock.signals || 0}
                                  size="small"
                                  color="info"
                                  variant="filled"
                                />
                                <Chip
                                  icon={<TrendingUpIcon />}
                                  label={stock.trades || 0}
                                  size="small"
                                  color="success"
                                  variant="filled"
                                />
                              </Stack>

                              {/* Status Indicator */}
                              <Chip
                                label={stock.status ? stock.status.toUpperCase() : "IDLE"}
                                size="small"
                                color={
                                  stock.status === "traded" ? "success" :
                                  stock.status === "buy" || stock.status === "sell" ? "warning" :
                                  "default"
                                }
                                variant="outlined"
                              />
                            </Stack>
                          </Box>
                        </Grid>
                      );
                    })}
                </Grid>
              )}
            </Box>
          </Collapse>
        </CardContent>
      </Card>
    </Grid>
  );
};

export default StockActivityChart;
