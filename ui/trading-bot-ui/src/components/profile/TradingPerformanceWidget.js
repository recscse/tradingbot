// src/components/profile/TradingPerformanceWidget.jsx
import React from "react";
import {
  Box,
  Typography,
  Paper,
  Stack,
  Chip,
  LinearProgress,
  useTheme,
  alpha,
  Grid,
  Tooltip,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Timeline as TimelineIcon,
  Speed as SpeedIcon,
  MonetizationOn as MoneyIcon,
} from "@mui/icons-material";

const TradingPerformanceWidget = ({ tradingStats, compact = false }) => {
  const theme = useTheme();

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const performanceMetrics = [
    {
      title: "Win Rate",
      value: `${tradingStats?.win_rate || 0}%`,
      progress: (tradingStats?.win_rate || 0) / 100,
      color: tradingStats?.win_rate >= 60 ? "success" : tradingStats?.win_rate >= 40 ? "warning" : "error",
      icon: SpeedIcon,
    },
    {
      title: "Total P&L",
      value: formatCurrency(tradingStats?.total_pnl || 0),
      progress: Math.min(Math.abs(tradingStats?.total_pnl || 0) / 100000, 1), // Normalize to max 1L
      color: (tradingStats?.total_pnl || 0) >= 0 ? "success" : "error",
      icon: (tradingStats?.total_pnl || 0) >= 0 ? TrendingUpIcon : TrendingDownIcon,
    },
    {
      title: "Avg Trade",
      value: formatCurrency(tradingStats?.avg_trade_value || 0),
      progress: Math.min(Math.abs(tradingStats?.avg_trade_value || 0) / 10000, 1), // Normalize to max 10K
      color: "info",
      icon: MoneyIcon,
    },
  ];

  const tradingStreak = tradingStats?.current_streak || 0;
  const streakType = tradingStreak >= 0 ? "winning" : "losing";

  if (compact) {
    return (
      <Paper
        elevation={0}
        sx={{
          p: 3,
          bgcolor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: "blur(10px)",
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          borderRadius: 3,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={2} mb={2}>
          <TimelineIcon color="primary" />
          <Typography variant="h6" fontWeight={700}>
            Trading Performance
          </Typography>
        </Stack>

        <Grid container spacing={2}>
          {performanceMetrics.map((metric, index) => (
            <Grid item xs={4} key={index}>
              <Box textAlign="center">
                <Typography variant="h6" fontWeight={700} color={`${metric.color}.main`}>
                  {metric.value}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {metric.title}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>
    );
  }

  return (
    <Paper
      elevation={0}
      sx={{
        p: 4,
        bgcolor: alpha(theme.palette.background.paper, 0.8),
        backdropFilter: "blur(10px)",
        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        borderRadius: 3,
        position: "relative",
        overflow: "hidden",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
        }
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={3}>
        <Stack direction="row" alignItems="center" spacing={2}>
          <TimelineIcon color="primary" sx={{ fontSize: 28 }} />
          <Box>
            <Typography variant="h6" fontWeight={700}>
              Trading Performance Overview
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Your trading statistics and trends
            </Typography>
          </Box>
        </Stack>

        {tradingStreak !== 0 && (
          <Tooltip title={`Current ${streakType} streak`}>
            <Chip
              label={`${Math.abs(tradingStreak)} ${streakType} streak`}
              color={streakType === "winning" ? "success" : "error"}
              variant="outlined"
              sx={{ fontWeight: 600 }}
            />
          </Tooltip>
        )}
      </Stack>

      <Grid container spacing={3}>
        {performanceMetrics.map((metric, index) => (
          <Grid item xs={12} sm={4} key={index}>
            <Box>
              <Stack direction="row" alignItems="center" spacing={1} mb={1}>
                <metric.icon color={metric.color} sx={{ fontSize: 20 }} />
                <Typography variant="body2" fontWeight={600} color="text.primary">
                  {metric.title}
                </Typography>
              </Stack>
              
              <Typography variant="h5" fontWeight={700} color={`${metric.color}.main`} mb={1}>
                {metric.value}
              </Typography>
              
              <LinearProgress
                variant="determinate"
                value={metric.progress * 100}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  bgcolor: alpha(theme.palette[metric.color].main, 0.1),
                  "& .MuiLinearProgress-bar": {
                    borderRadius: 3,
                    bgcolor: `${metric.color}.main`,
                  }
                }}
              />
            </Box>
          </Grid>
        ))}
      </Grid>

      {/* Additional trading insights */}
      <Box mt={4} pt={3} borderTop={`1px solid ${alpha(theme.palette.divider, 0.1)}`}>
        <Typography variant="body2" color="text.secondary" mb={2}>
          Trading Insights
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <Box textAlign="center">
              <Typography variant="h6" fontWeight={700} color="primary.main">
                {tradingStats?.total_trades || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total Trades
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs={6} sm={3}>
            <Box textAlign="center">
              <Typography variant="h6" fontWeight={700} color="success.main">
                {tradingStats?.profitable_trades || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Profitable
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs={6} sm={3}>
            <Box textAlign="center">
              <Typography variant="h6" fontWeight={700} color="error.main">
                {tradingStats?.losing_trades || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Losses
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs={6} sm={3}>
            <Box textAlign="center">
              <Typography variant="h6" fontWeight={700} color="info.main">
                {tradingStats?.active_positions || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active Now
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Box>
    </Paper>
  );
};

export default TradingPerformanceWidget;