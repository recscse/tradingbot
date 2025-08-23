// components/trading/TradingMetrics.js
import React from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  LinearProgress,
  Chip,
  Stack,
  Divider,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Speed,
  Target,
  Shield,
  Assessment,
} from "@mui/icons-material";

const TradingMetrics = ({ analytics, tradingMode }) => {
  const formatCurrency = (amount) => {
    if (amount == null) return "₹0.00";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const getPnLColor = (value) => {
    if (value > 0) return "success.main";
    if (value < 0) return "error.main";
    return "text.primary";
  };

  const getPerformanceRating = (winRate) => {
    if (winRate >= 70) return { label: "Excellent", color: "success" };
    if (winRate >= 60) return { label: "Good", color: "info" };
    if (winRate >= 50) return { label: "Average", color: "warning" };
    return { label: "Needs Improvement", color: "error" };
  };

  const getRiskRewardRating = (ratio) => {
    if (ratio >= 2.5) return { label: "Excellent", color: "success" };
    if (ratio >= 2.0) return { label: "Good", color: "info" };
    if (ratio >= 1.5) return { label: "Average", color: "warning" };
    return { label: "Poor", color: "error" };
  };

  if (!analytics || analytics.total_trades === 0) {
    return (
      <Card>
        <CardContent>
          <Box textAlign="center" py={4}>
            <Assessment sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
            <Typography variant="h6" color="textSecondary" gutterBottom>
              No Trading Metrics Available
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Start trading to see detailed performance analytics
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const performanceRating = getPerformanceRating(analytics.win_rate);
  const riskRewardRating = getRiskRewardRating(analytics.risk_reward_ratio);

  return (
    <Grid container spacing={3}>
      {/* Performance Overview */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📊 Performance Overview
            </Typography>
            
            <Stack spacing={3}>
              {/* Win Rate */}
              <Box>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="textSecondary">
                    Win Rate
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="h6" fontWeight="bold">
                      {analytics.win_rate.toFixed(1)}%
                    </Typography>
                    <Chip 
                      label={performanceRating.label}
                      color={performanceRating.color}
                      size="small"
                    />
                  </Box>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={Math.min(analytics.win_rate, 100)}
                  color={performanceRating.color}
                  sx={{ height: 8, borderRadius: 1 }}
                />
                <Typography variant="caption" color="textSecondary" mt={0.5}>
                  {analytics.winning_trades} wins out of {analytics.total_trades} trades
                </Typography>
              </Box>

              {/* Profit Factor */}
              <Box>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="textSecondary">
                    Profit Factor
                  </Typography>
                  <Typography variant="h6" fontWeight="bold" sx={{ color: getPnLColor(analytics.profit_factor - 1) }}>
                    {analytics.profit_factor.toFixed(2)}
                  </Typography>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={Math.min((analytics.profit_factor / 3) * 100, 100)}
                  color={analytics.profit_factor >= 1.5 ? "success" : analytics.profit_factor >= 1 ? "warning" : "error"}
                  sx={{ height: 8, borderRadius: 1 }}
                />
                <Typography variant="caption" color="textSecondary" mt={0.5}>
                  {analytics.profit_factor >= 1 ? "Profitable" : "Losing"} strategy
                </Typography>
              </Box>

              {/* Risk:Reward Ratio */}
              <Box>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="textSecondary">
                    Risk:Reward Ratio
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="h6" fontWeight="bold">
                      1:{analytics.risk_reward_ratio.toFixed(2)}
                    </Typography>
                    <Chip 
                      label={riskRewardRating.label}
                      color={riskRewardRating.color}
                      size="small"
                    />
                  </Box>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={Math.min((analytics.risk_reward_ratio / 3) * 100, 100)}
                  color={riskRewardRating.color}
                  sx={{ height: 8, borderRadius: 1 }}
                />
                <Typography variant="caption" color="textSecondary" mt={0.5}>
                  Average reward per unit of risk
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* Financial Metrics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              💰 Financial Performance
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box textAlign="center" p={2} bgcolor="success.light" borderRadius={1}>
                  <TrendingUp color="success" sx={{ fontSize: 32, mb: 1 }} />
                  <Typography variant="h6" color="success.dark" fontWeight="bold">
                    {formatCurrency(analytics.gross_profit)}
                  </Typography>
                  <Typography variant="caption" color="success.dark">
                    Gross Profit
                  </Typography>
                </Box>
              </Grid>
              
              <Grid item xs={6}>
                <Box textAlign="center" p={2} bgcolor="error.light" borderRadius={1}>
                  <TrendingDown color="error" sx={{ fontSize: 32, mb: 1 }} />
                  <Typography variant="h6" color="error.dark" fontWeight="bold">
                    {formatCurrency(analytics.gross_loss)}
                  </Typography>
                  <Typography variant="caption" color="error.dark">
                    Gross Loss
                  </Typography>
                </Box>
              </Grid>

              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Box textAlign="center" p={2} bgcolor="background.paper" borderRadius={1} border={1} borderColor="divider">
                  <Typography variant="h5" sx={{ color: getPnLColor(analytics.net_profit) }} fontWeight="bold">
                    {formatCurrency(analytics.net_profit)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Net Profit ({tradingMode} Trading)
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>

      {/* Trade Analysis */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎯 Trade Analysis
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <Target color="success" />
                  <Box>
                    <Typography variant="h6" color="success.main">
                      {formatCurrency(analytics.avg_win)}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Average Win
                    </Typography>
                  </Box>
                </Box>
              </Grid>
              
              <Grid item xs={6}>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <Shield color="error" />
                  <Box>
                    <Typography variant="h6" color="error.main">
                      {formatCurrency(analytics.avg_loss)}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Average Loss
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              <Grid item xs={6}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Speed color="success" />
                  <Box>
                    <Typography variant="h6" color="success.main">
                      {formatCurrency(analytics.largest_win)}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Best Trade
                    </Typography>
                  </Box>
                </Box>
              </Grid>
              
              <Grid item xs={6}>
                <Box display="flex" alignItems="center" gap={1}>
                  <TrendingDown color="error" />
                  <Box>
                    <Typography variant="h6" color="error.main">
                      {formatCurrency(analytics.largest_loss)}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Worst Trade
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>

      {/* Trading Summary */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📈 Trading Summary
            </Typography>
            
            <Stack spacing={2}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" color="textSecondary">
                  Total Trades
                </Typography>
                <Typography variant="h6" fontWeight="bold">
                  {analytics.total_trades}
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" color="textSecondary">
                  Winning Trades
                </Typography>
                <Typography variant="h6" color="success.main" fontWeight="bold">
                  {analytics.winning_trades}
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" color="textSecondary">
                  Losing Trades
                </Typography>
                <Typography variant="h6" color="error.main" fontWeight="bold">
                  {analytics.losing_trades}
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Performance Rating
                </Typography>
                <Chip 
                  label={`${performanceRating.label} Trader`}
                  color={performanceRating.color}
                  sx={{ fontWeight: "bold" }}
                />
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default TradingMetrics;