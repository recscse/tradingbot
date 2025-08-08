// src/components/profile/ProfileOverview.jsx
import React, { useState } from "react";
import {
  Box,
  Typography,
  Button,
  Grid,
  Avatar,
  useTheme,
  Stack,
  alpha,
  Paper,
  Tooltip,
  IconButton,
  Chip,
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
  Speed as SpeedIcon,
  Assessment as AssessmentIcon,
  Info as InfoIcon,
} from "@mui/icons-material";
import BrokerAccountCard from "./BrokerAccountCard";
import RecentActivityFeed from "./RecentActivityFeed";
import TradingPerformanceWidget from "./TradingPerformanceWidget";
import PortfolioHealthIndicator from "./PortfolioHealthIndicator";

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

  // Enhanced stats with additional trading metrics
  const stats = [
    {
      title: "Total Portfolio",
      value: formatCurrency(tradingStats?.total_portfolio_value || 0),
      icon: AccountBalanceIcon,
      color: "primary",
      subtitle: "Total investment value",
      trend: null,
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
      subtitle: "Daily performance",
      trend:
        (tradingStats?.today_pnl || profileData?.todayPnl || 0) >= 0
          ? "up"
          : "down",
    },
    {
      title: "Total Trades",
      value: tradingStats?.total_trades || 0,
      icon: ActivityIcon,
      color: "info",
      subtitle: "Lifetime trades executed",
      trend: null,
    },
    {
      title: "Win Rate",
      value: `${tradingStats?.win_rate || 0}%`,
      icon: SpeedIcon,
      color:
        tradingStats?.win_rate >= 60
          ? "success"
          : tradingStats?.win_rate >= 40
          ? "warning"
          : "error",
      subtitle: "Success percentage",
      trend: null,
    },
  ];

  const renderStatCard = (stat, index) => (
    <Grid item xs={6} sm={3} key={index}>
      <Paper
        elevation={0}
        sx={{
          textAlign: "center",
          transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          bgcolor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: "blur(10px)",
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          borderRadius: 3,
          p: { xs: 2.5, sm: 3 },
          position: "relative",
          overflow: "hidden",
          "&:hover": {
            transform: "translateY(-6px)",
            boxShadow: `0 12px 24px ${alpha(
              theme.palette[stat.color].main,
              0.2
            )}`,
            borderColor: alpha(theme.palette[stat.color].main, 0.3),
            bgcolor: alpha(theme.palette[stat.color].main, 0.02),
          },
          "&::before": {
            content: '""',
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            background: `linear-gradient(90deg, ${
              theme.palette[stat.color].main
            }, ${theme.palette[stat.color].light})`,
            opacity: 0.8,
          },
        }}
      >
        <Stack alignItems="center" spacing={2}>
          <Avatar
            sx={{
              bgcolor: alpha(theme.palette[stat.color].main, 0.1),
              color: `${stat.color}.main`,
              width: { xs: 48, sm: 56 },
              height: { xs: 48, sm: 56 },
              boxShadow: `0 4px 12px ${alpha(
                theme.palette[stat.color].main,
                0.2
              )}`,
            }}
          >
            <stat.icon sx={{ fontSize: { xs: 24, sm: 28 } }} />
          </Avatar>

          <Box>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="center"
              spacing={1}
            >
              <Typography
                variant="h5"
                fontWeight={700}
                sx={{
                  fontSize: { xs: "1.4rem", sm: "1.6rem" },
                  color: `${stat.color}.main`,
                  lineHeight: 1.2,
                }}
              >
                {stat.value}
              </Typography>
              {stat.trend && (
                <Chip
                  size="small"
                  label={stat.trend === "up" ? "↗" : "↘"}
                  sx={{
                    bgcolor: alpha(theme.palette[stat.color].main, 0.1),
                    color: `${stat.color}.main`,
                    fontSize: "0.7rem",
                    height: 20,
                    fontWeight: 600,
                  }}
                />
              )}
            </Stack>

            <Typography
              variant="body2"
              fontWeight={600}
              sx={{
                color: "text.primary",
                fontSize: { xs: "0.85rem", sm: "0.9rem" },
                mb: 0.5,
              }}
            >
              {stat.title}
            </Typography>

            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                fontSize: { xs: "0.75rem", sm: "0.8rem" },
                opacity: 0.8,
              }}
            >
              {stat.subtitle}
            </Typography>
          </Box>
        </Stack>
      </Paper>
    </Grid>
  );

  return (
    <Box sx={{ py: 4 }}>
      {/* Enhanced Header */}
      <Paper
        elevation={0}
        sx={{
          mb: 4,
          p: 4,
          bgcolor: alpha(theme.palette.primary.main, 0.03),
          border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
          borderRadius: 3,
        }}
      >
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={3}
        >
          <Box>
            <Stack direction="row" alignItems="center" spacing={2} mb={1}>
              <Avatar
                sx={{
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  color: "primary.main",
                  width: 48,
                  height: 48,
                }}
              >
                <AssessmentIcon sx={{ fontSize: 24 }} />
              </Avatar>
              <Box>
                <Typography
                  variant="h4"
                  fontWeight={700}
                  sx={{
                    color: "text.primary",
                    fontSize: { xs: "1.8rem", sm: "2.2rem" },
                  }}
                >
                  Trading Dashboard
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ fontSize: { xs: "0.9rem", sm: "1rem" } }}
                >
                  Real-time performance metrics and portfolio insights
                </Typography>
              </Box>
            </Stack>
          </Box>

          <Stack direction="row" spacing={2}>
            <Tooltip title="View detailed analytics">
              <IconButton
                sx={{
                  bgcolor: alpha(theme.palette.info.main, 0.1),
                  color: "info.main",
                  "&:hover": {
                    bgcolor: alpha(theme.palette.info.main, 0.2),
                    transform: "scale(1.05)",
                  },
                }}
              >
                <InfoIcon />
              </IconButton>
            </Tooltip>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={refreshing}
              sx={{
                borderRadius: 2.5,
                px: 3,
                py: 1.2,
                fontWeight: 600,
                textTransform: "none",
                boxShadow: `0 4px 12px ${alpha(
                  theme.palette.primary.main,
                  0.3
                )}`,
                "&:hover": {
                  transform: "translateY(-2px)",
                  boxShadow: `0 6px 16px ${alpha(
                    theme.palette.primary.main,
                    0.4
                  )}`,
                },
              }}
            >
              {refreshing ? "Refreshing..." : "Refresh Data"}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Stats Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {stats.map(renderStatCard)}
      </Grid>

      {/* Enhanced Main Content */}
      <Grid container spacing={4}>
        {/* Broker Accounts */}
        <Grid item xs={12} lg={6}>
          <Paper
            elevation={0}
            sx={{
              height: "100%",
              bgcolor: alpha(theme.palette.background.paper, 0.8),
              backdropFilter: "blur(10px)",
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              borderRadius: 3,
            }}
          >
            <Box sx={{ p: 3 }}>
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                mb={3}
              >
                <Stack direction="row" alignItems="center" spacing={2}>
                  <Avatar
                    sx={{
                      bgcolor: alpha(theme.palette.info.main, 0.1),
                      color: "info.main",
                      width: 48,
                      height: 48,
                      boxShadow: `0 4px 12px ${alpha(
                        theme.palette.info.main,
                        0.2
                      )}`,
                    }}
                  >
                    <AccountBalanceIcon sx={{ fontSize: 24 }} />
                  </Avatar>
                  <Box>
                    <Typography variant="h6" fontWeight={700}>
                      Connected Brokers
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {brokerAccounts?.length || 0} active connections
                    </Typography>
                  </Box>
                </Stack>

                <Button
                  variant="contained"
                  size="small"
                  startIcon={<PlusIcon />}
                  sx={{
                    borderRadius: 2,
                    textTransform: "none",
                    fontWeight: 600,
                    px: 2.5,
                  }}
                >
                  Add Broker
                </Button>
              </Stack>

              {brokerAccounts && brokerAccounts.length > 0 ? (
                <Stack spacing={2.5}>
                  {brokerAccounts.slice(0, 3).map((account) => (
                    <BrokerAccountCard
                      key={account.id}
                      account={account}
                      variant="compact"
                    />
                  ))}
                  {brokerAccounts.length > 3 && (
                    <Button
                      variant="text"
                      size="small"
                      sx={{
                        textTransform: "none",
                        fontWeight: 600,
                        color: "primary.main",
                        "&:hover": {
                          bgcolor: alpha(theme.palette.primary.main, 0.04),
                        },
                      }}
                    >
                      View All {brokerAccounts.length} Brokers →
                    </Button>
                  )}
                </Stack>
              ) : (
                <Box sx={{ textAlign: "center", py: 5 }}>
                  <Avatar
                    sx={{
                      width: 72,
                      height: 72,
                      mx: "auto",
                      mb: 3,
                      bgcolor: alpha(theme.palette.primary.main, 0.1),
                      color: "primary.main",
                      boxShadow: `0 4px 12px ${alpha(
                        theme.palette.primary.main,
                        0.2
                      )}`,
                    }}
                  >
                    <DollarIcon sx={{ fontSize: 36 }} />
                  </Avatar>

                  <Typography variant="h6" gutterBottom fontWeight={700}>
                    No brokers connected
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 4, maxWidth: 300, mx: "auto" }}
                  >
                    Connect your first broker account to start automated trading
                    and access real-time market data
                  </Typography>

                  <Button
                    variant="contained"
                    startIcon={<PlusIcon />}
                    sx={{
                      borderRadius: 2.5,
                      px: 3,
                      py: 1.2,
                      textTransform: "none",
                      fontWeight: 600,
                      boxShadow: `0 4px 12px ${alpha(
                        theme.palette.primary.main,
                        0.3
                      )}`,
                    }}
                  >
                    Connect Your First Broker
                  </Button>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} lg={6}>
          <Paper
            elevation={0}
            sx={{
              height: "100%",
              bgcolor: alpha(theme.palette.background.paper, 0.8),
              backdropFilter: "blur(10px)",
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              borderRadius: 3,
            }}
          >
            <Box sx={{ p: 3 }}>
              <Stack direction="row" alignItems="center" spacing={2} mb={3}>
                <Avatar
                  sx={{
                    bgcolor: alpha(theme.palette.secondary.main, 0.1),
                    color: "secondary.main",
                    width: 48,
                    height: 48,
                    boxShadow: `0 4px 12px ${alpha(
                      theme.palette.secondary.main,
                      0.2
                    )}`,
                  }}
                >
                  <TimelineIcon sx={{ fontSize: 24 }} />
                </Avatar>
                <Box>
                  <Typography variant="h6" fontWeight={700}>
                    Recent Activity
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Latest trading events and updates
                  </Typography>
                </Box>
              </Stack>

              <RecentActivityFeed
                activities={tradingStats?.recentActivity || []}
              />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Trading Performance Widget */}
      <Box sx={{ mt: 4 }}>
        <TradingPerformanceWidget tradingStats={tradingStats} />
      </Box>

      {/* Portfolio Health Indicator */}
      <Box sx={{ mt: 4 }}>
        <PortfolioHealthIndicator
          portfolioData={{ brokerAccounts }}
          tradingStats={tradingStats}
        />
      </Box>

      {/* Enhanced Quick Actions */}
      <Paper
        elevation={0}
        sx={{
          mt: 5,
          bgcolor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: "blur(10px)",
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          borderRadius: 3,
        }}
      >
        <Box sx={{ p: 4 }}>
          <Stack direction="row" alignItems="center" spacing={2} mb={4}>
            <Avatar
              sx={{
                bgcolor: alpha(theme.palette.success.main, 0.1),
                color: "success.main",
                width: 48,
                height: 48,
              }}
            >
              <SpeedIcon sx={{ fontSize: 24 }} />
            </Avatar>
            <Box>
              <Typography variant="h6" fontWeight={700}>
                Quick Actions
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Streamline your trading workflow
              </Typography>
            </Box>
          </Stack>

          <Grid container spacing={3}>
            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 2,
                  borderRadius: 2.5,
                  textTransform: "none",
                  fontWeight: 600,
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                  color: "primary.main",
                  "&:hover": {
                    bgcolor: alpha(theme.palette.primary.main, 0.04),
                    borderColor: "primary.main",
                    transform: "translateY(-2px)",
                  },
                }}
              >
                📊 Performance Reports
              </Button>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 2,
                  borderRadius: 2.5,
                  textTransform: "none",
                  fontWeight: 600,
                  border: `1px solid ${alpha(
                    theme.palette.secondary.main,
                    0.3
                  )}`,
                  color: "secondary.main",
                  "&:hover": {
                    bgcolor: alpha(theme.palette.secondary.main, 0.04),
                    borderColor: "secondary.main",
                    transform: "translateY(-2px)",
                  },
                }}
              >
                ⚙️ Account Settings
              </Button>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 2,
                  borderRadius: 2.5,
                  textTransform: "none",
                  fontWeight: 600,
                  border: `1px solid ${alpha(theme.palette.info.main, 0.3)}`,
                  color: "info.main",
                  "&:hover": {
                    bgcolor: alpha(theme.palette.info.main, 0.04),
                    borderColor: "info.main",
                    transform: "translateY(-2px)",
                  },
                }}
              >
                📚 Help Center
              </Button>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Button
                fullWidth
                variant="outlined"
                sx={{
                  py: 2,
                  borderRadius: 2.5,
                  textTransform: "none",
                  fontWeight: 600,
                  border: `1px solid ${alpha(theme.palette.warning.main, 0.3)}`,
                  color: "warning.main",
                  "&:hover": {
                    bgcolor: alpha(theme.palette.warning.main, 0.04),
                    borderColor: "warning.main",
                    transform: "translateY(-2px)",
                  },
                }}
              >
                💬 Contact Support
              </Button>
            </Grid>
          </Grid>
        </Box>
      </Paper>
    </Box>
  );
};

export default ProfileOverview;
