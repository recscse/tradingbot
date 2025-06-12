import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Typography,
  Grid,
  Box,
  LinearProgress,
  Chip,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  AccountBalance,
  Assessment,
} from "@mui/icons-material";
import { useEnhancedMarket } from "../../context/EnhancedMarketProvider";

const LiveTradingStats = () => {
  const { portfolio } = useEnhancedMarket();
  const [stats, setStats] = useState({
    totalValue: 0,
    dayChange: 0,
    dayChangePercent: 0,
    positions: [],
    winRate: 0,
    profitLoss: 0,
  });

  useEffect(() => {
    setStats((prev) => ({
      ...prev,
      ...portfolio,
    }));
  }, [portfolio]);

  const StatCard = ({ title, value, icon, color = "primary", subtitle }) => (
    <Card elevation={2} sx={{ height: "100%" }}>
      <CardContent>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Typography variant="h6" color="textSecondary">
            {title}
          </Typography>
          {icon}
        </Box>
        <Typography variant="h4" color={color + ".main"} mb={1}>
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="textSecondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const isPositive = stats.dayChange >= 0;

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Portfolio Value"
            value={formatCurrency(stats.totalValue)}
            icon={<AccountBalance color="primary" />}
            subtitle="Total investment value"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Day Change"
            value={`${isPositive ? "+" : ""}${formatCurrency(stats.dayChange)}`}
            icon={
              isPositive ? (
                <TrendingUp color="success" />
              ) : (
                <TrendingDown color="error" />
              )
            }
            color={isPositive ? "success" : "error"}
            subtitle={`${isPositive ? "+" : ""}${stats.dayChangePercent.toFixed(
              2
            )}%`}
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Active Positions"
            value={stats.positions.length}
            icon={<Assessment color="info" />}
            color="info"
            subtitle="Currently held"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <StatCard
            title="Win Rate"
            value={`${stats.winRate.toFixed(1)}%`}
            icon={<TrendingUp color="success" />}
            color="success"
            subtitle="Success percentage"
          />
        </Grid>
      </Grid>

      {stats.positions.length > 0 && (
        <Card elevation={3} sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" mb={2}>
              Active Positions
            </Typography>
            <Grid container spacing={2}>
              {stats.positions.slice(0, 5).map((position, index) => (
                <Grid item xs={12} key={index}>
                  <Box
                    display="flex"
                    justifyContent
                    alignItems="center"
                    p={2}
                    sx={{
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 1,
                      bgcolor: "background.paper",
                    }}
                  >
                    <Box flex={1}>
                      <Typography variant="subtitle2">
                        {position.symbol}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Qty: {position.quantity} | Avg: ₹
                        {position.avgPrice?.toFixed(2)}
                      </Typography>
                    </Box>

                    <Box textAlign="right">
                      <Typography
                        variant="subtitle2"
                        color={
                          position.pnl >= 0 ? "success.main" : "error.main"
                        }
                      >
                        {position.pnl >= 0 ? "+" : ""}₹
                        {position.pnl?.toFixed(2)}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {position.pnlPercent >= 0 ? "+" : ""}
                        {position.pnlPercent?.toFixed(2)}%
                      </Typography>
                    </Box>

                    <Chip
                      label={position.type || "EQUITY"}
                      size="small"
                      variant="outlined"
                      sx={{ ml: 2 }}
                    />
                  </Box>
                </Grid>
              ))}
            </Grid>

            {stats.positions.length > 5 && (
              <Box mt={2} textAlign="center">
                <Typography variant="caption" color="textSecondary">
                  Showing 5 of {stats.positions.length} positions
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default LiveTradingStats;
