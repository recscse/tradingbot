// src/components/profile/ProfileOverview.jsx
import React, { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Avatar,
  useTheme,
  Stack,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ShowChart as ActivityIcon,
  Refresh as RefreshIcon,
  Add as PlusIcon,
  AccountBalance as AccountBalanceIcon,
  Timeline as TimelineIcon,
  AttachMoney as DollarIcon,
  Business as BusinessIcon,
} from "@mui/icons-material";
import BrokerAccountCard from "./BrokerAccountCard";
import RecentActivityFeed from "./RecentActivityFeed";

const ProfileOverview = ({
  profileData,
  tradingStats,
  brokerAccounts,
  onRefresh,
}) => {
  const theme = useTheme();
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Simple stats using actual data
  const stats = [
    {
      title: "Total Portfolio",
      value: formatCurrency(tradingStats?.total_portfolio_value || 0),
      icon: AccountBalanceIcon,
      color: "primary",
    },
    {
      title: "Today's P&L",
      value: formatCurrency(
        tradingStats?.today_pnl || profileData?.todayPnl || 0
      ),
      icon:
        (tradingStats?.today_pnl || profileData?.todayPnl || 0) >= 0
          ? TrendingUpIcon
          : TrendingDownIcon,
      color:
        (tradingStats?.today_pnl || profileData?.todayPnl || 0) >= 0
          ? "success"
          : "error",
    },
    {
      title: "Total Trades",
      value: tradingStats?.total_trades || 0,
      icon: ActivityIcon,
      color: "info",
    },
    {
      title: "Active Positions",
      value: tradingStats?.active_positions || 0,
      icon: BusinessIcon,
      color: "warning",
    },
  ];

  const renderStatCard = (stat, index) => (
    <Grid item xs={6} sm={3} key={index}>
      <Card
        sx={{
          textAlign: "center",
          transition: "all 0.2s ease",
          "&:hover": {
            transform: "translateY(-2px)",
            boxShadow: theme.shadows[4],
          },
        }}
      >
        <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
          <Avatar
            sx={{
              bgcolor: `${stat.color}.main`,
              color: "white",
              width: { xs: 40, sm: 48 },
              height: { xs: 40, sm: 48 },
              mx: "auto",
              mb: 2,
            }}
          >
            <stat.icon sx={{ fontSize: { xs: 20, sm: 24 } }} />
          </Avatar>

          <Typography
            variant="h5"
            fontWeight={700}
            sx={{
              mb: 1,
              fontSize: { xs: "1.25rem", sm: "1.5rem" },
              color:
                stat.color === "error"
                  ? "error.main"
                  : stat.color === "success"
                  ? "success.main"
                  : "text.primary",
            }}
          >
            {stat.value}
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ fontSize: { xs: "0.8rem", sm: "0.875rem" } }}
          >
            {stat.title}
          </Typography>
        </CardContent>
      </Card>
    </Grid>
  );

  return (
    <Box sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={2}
        >
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              Account Overview
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Your trading performance and account summary
            </Typography>
          </Box>

          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={refreshing}
            sx={{ borderRadius: 2 }}
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </Button>
        </Stack>
      </Box>

      {/* Stats Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {stats.map(renderStatCard)}
      </Grid>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Broker Accounts */}
        <Grid item xs={12} lg={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                mb={3}
              >
                <Stack direction="row" alignItems="center" spacing={2}>
                  <Avatar
                    sx={{
                      bgcolor: "info.main",
                      color: "white",
                      width: 40,
                      height: 40,
                    }}
                  >
                    <AccountBalanceIcon />
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    Connected Brokers
                  </Typography>
                </Stack>

                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<PlusIcon />}
                  sx={{ borderRadius: 2 }}
                >
                  Add Broker
                </Button>
              </Stack>

              {brokerAccounts && brokerAccounts.length > 0 ? (
                <Stack spacing={2}>
                  {brokerAccounts.slice(0, 3).map((account) => (
                    <BrokerAccountCard
                      key={account.id}
                      account={account}
                      variant="compact"
                    />
                  ))}
                  {brokerAccounts.length > 3 && (
                    <Button variant="text" size="small">
                      View All {brokerAccounts.length} Brokers
                    </Button>
                  )}
                </Stack>
              ) : (
                <Box sx={{ textAlign: "center", py: 4 }}>
                  <Avatar
                    sx={{
                      width: 64,
                      height: 64,
                      mx: "auto",
                      mb: 2,
                      bgcolor: "primary.main",
                      color: "white",
                    }}
                  >
                    <DollarIcon sx={{ fontSize: 32 }} />
                  </Avatar>

                  <Typography variant="h6" gutterBottom>
                    No brokers connected
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 3 }}
                  >
                    Connect your first broker to start trading
                  </Typography>

                  <Button
                    variant="contained"
                    startIcon={<PlusIcon />}
                    sx={{ borderRadius: 2 }}
                  >
                    Connect Broker
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} lg={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" alignItems="center" spacing={2} mb={3}>
                <Avatar
                  sx={{
                    bgcolor: "secondary.main",
                    color: "white",
                    width: 40,
                    height: 40,
                  }}
                >
                  <TimelineIcon />
                </Avatar>
                <Typography variant="h6" fontWeight={600}>
                  Recent Activity
                </Typography>
              </Stack>

              <RecentActivityFeed
                activities={tradingStats?.recentActivity || []}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Card sx={{ mt: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 3 }}>
            Quick Actions
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 1.5,
                  borderRadius: 2,
                  textTransform: "none",
                }}
              >
                View Reports
              </Button>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 1.5,
                  borderRadius: 2,
                  textTransform: "none",
                }}
              >
                Settings
              </Button>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 1.5,
                  borderRadius: 2,
                  textTransform: "none",
                }}
              >
                Help Center
              </Button>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 1.5,
                  borderRadius: 2,
                  textTransform: "none",
                }}
              >
                Contact Support
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ProfileOverview;
