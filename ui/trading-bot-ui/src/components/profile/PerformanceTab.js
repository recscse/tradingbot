// src/components/profile/PerformanceTab.jsx
import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  ButtonGroup,
  Skeleton,
  useTheme,
  alpha,
  Fade,
  Zoom,
  useMediaQuery,
  Avatar,
  Divider,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  CalendarToday as CalendarIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  ShowChart as ShowChartIcon,
  AccountBalance as AccountBalanceIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
} from "@mui/icons-material";
import { profileService } from "../../services/profileService";

const PerformanceTab = ({ profile, loading }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md"));

  const [performanceData, setPerformanceData] = useState(null);
  const [timeframe, setTimeframe] = useState("1M");
  const [performanceLoading, setPerformanceLoading] = useState(true);

  useEffect(() => {
    fetchPerformanceData();
  }, [timeframe]);

  const fetchPerformanceData = async () => {
    try {
      setPerformanceLoading(true);
      const response = await profileService.getTradingStats();
      if (response.data) {
        setPerformanceData(response.data);
      }
    } catch (error) {
      console.error("Error fetching performance data:", error);
    } finally {
      setPerformanceLoading(false);
    }
  };

  const timeframes = [
    { label: "1D", value: "1D" },
    { label: "1W", value: "1W" },
    { label: "1M", value: "1M" },
    { label: "3M", value: "3M" },
    { label: "1Y", value: "1Y" },
    { label: "All", value: "ALL" },
  ];

  const performanceMetrics = [
    {
      label: "Total Return",
      value: performanceData?.totalReturn || 0,
      change: performanceData?.totalReturnChange || 0,
      format: "currency",
      icon: AccountBalanceIcon,
      color: "primary",
    },
    {
      label: "Win Rate",
      value: performanceData?.winRate || 0,
      change: performanceData?.winRateChange || 0,
      format: "percentage",
      icon: AssessmentIcon,
      color: "success",
    },
    {
      label: "Avg. Profit per Trade",
      value: performanceData?.avgProfitPerTrade || 0,
      change: performanceData?.avgProfitChange || 0,
      format: "currency",
      icon: TrendingUpIcon,
      color: "info",
    },
    {
      label: "Max Drawdown",
      value: performanceData?.maxDrawdown || 0,
      change: performanceData?.drawdownChange || 0,
      format: "percentage",
      icon: TrendingDownIcon,
      color: "warning",
    },
    {
      label: "Sharpe Ratio",
      value: performanceData?.sharpeRatio || 0,
      change: performanceData?.sharpeChange || 0,
      format: "decimal",
      icon: ShowChartIcon,
      color: "secondary",
    },
    {
      label: "Total Trades",
      value: performanceData?.totalTrades || 0,
      change: performanceData?.tradesChange || 0,
      format: "number",
      icon: TimelineIcon,
      color: "primary",
    },
  ];

  const formatValue = (value, format) => {
    switch (format) {
      case "currency":
        return `₹${Math.abs(value).toLocaleString("en-IN")}`;
      case "percentage":
        return `${value.toFixed(2)}%`;
      case "decimal":
        return value.toFixed(2);
      case "number":
        return value.toLocaleString("en-IN");
      default:
        return value;
    }
  };

  // const getChangeColor = (change) => {
  //   return change >= 0 ? "success.main" : "error.main";
  // };

  const renderMetricCard = (metric, index) => (
    <Grid item xs={12} sm={6} lg={4} key={index}>
      <Zoom in={true} timeout={300 + index * 100}>
        <Card
          sx={{
            height: "100%",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            background: alpha(theme.palette.background.paper, 0.8),
            backdropFilter: "blur(20px)",
            "&:hover": {
              transform: "translateY(-4px)",
              boxShadow: theme.shadows[8],
              borderColor: alpha(theme.palette[metric.color].main, 0.3),
            },
          }}
          elevation={0}
        >
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                mb: 2,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Avatar
                  sx={{
                    width: { xs: 32, sm: 40 },
                    height: { xs: 32, sm: 40 },
                    bgcolor: alpha(theme.palette[metric.color].main, 0.1),
                    color: `${metric.color}.main`,
                  }}
                >
                  <metric.icon sx={{ fontSize: { xs: 16, sm: 20 } }} />
                </Avatar>
                <Typography
                  variant={isMobile ? "body2" : "body1"}
                  color="text.secondary"
                  fontWeight={500}
                  sx={{
                    fontSize: { xs: "0.75rem", sm: "0.875rem" },
                    lineHeight: 1.2,
                  }}
                >
                  {metric.label}
                </Typography>
              </Box>

              <Chip
                icon={
                  metric.change >= 0 ? <TrendingUpIcon /> : <TrendingDownIcon />
                }
                label={`${metric.change >= 0 ? "+" : ""}${metric.change.toFixed(
                  1
                )}%`}
                color={metric.change >= 0 ? "success" : "error"}
                size="small"
                sx={{
                  fontSize: { xs: "0.6rem", sm: "0.75rem" },
                  height: { xs: 20, sm: 24 },
                }}
              />
            </Box>

            <Typography
              variant={isMobile ? "h6" : "h5"}
              component="div"
              sx={{
                fontWeight: 700,
                color: metric.value >= 0 ? "text.primary" : "error.main",
                fontSize: { xs: "1.1rem", sm: "1.25rem", md: "1.5rem" },
                lineHeight: 1.2,
                wordBreak: "break-word",
              }}
            >
              {performanceLoading ? (
                <Skeleton variant="text" width="80%" height={40} />
              ) : (
                formatValue(metric.value, metric.format)
              )}
            </Typography>
          </CardContent>
        </Card>
      </Zoom>
    </Grid>
  );

  const renderMobileTradesList = () => (
    <List sx={{ p: 0 }}>
      {performanceData?.recentTrades?.length > 0 ? (
        performanceData.recentTrades.map((trade, index) => (
          <React.Fragment key={index}>
            <ListItem
              sx={{
                px: { xs: 2, sm: 3 },
                py: 2,
                "&:hover": {
                  bgcolor: alpha(theme.palette.primary.main, 0.04),
                },
              }}
            >
              <ListItemAvatar>
                <Avatar
                  sx={{
                    bgcolor:
                      trade.type === "BUY" ? "success.light" : "error.light",
                    color:
                      trade.type === "BUY"
                        ? "success.contrastText"
                        : "error.contrastText",
                    width: 40,
                    height: 40,
                  }}
                >
                  {trade.type === "BUY" ? (
                    <TrendingUpIcon />
                  ) : (
                    <TrendingDownIcon />
                  )}
                </Avatar>
              </ListItemAvatar>

              <ListItemText
                primary={
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      mb: 0.5,
                    }}
                  >
                    <Typography variant="subtitle2" fontWeight={600}>
                      {trade.symbol}
                    </Typography>
                    <Typography
                      variant="subtitle2"
                      fontWeight={600}
                      color={trade.pnl >= 0 ? "success.main" : "error.main"}
                    >
                      ₹{Math.abs(trade.pnl).toLocaleString("en-IN")}
                    </Typography>
                  </Box>
                }
                secondary={
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      flexWrap: "wrap",
                      gap: 1,
                    }}
                  >
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                      <Chip
                        label={trade.type}
                        color={trade.type === "BUY" ? "success" : "error"}
                        size="small"
                        sx={{ fontSize: "0.65rem", height: 20 }}
                      />
                      <Chip
                        label={trade.status}
                        color={
                          trade.status === "CLOSED" ? "default" : "primary"
                        }
                        size="small"
                        sx={{ fontSize: "0.65rem", height: 20 }}
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(trade.date).toLocaleDateString()}
                    </Typography>
                  </Box>
                }
              />
            </ListItem>
            {index < performanceData.recentTrades.length - 1 && <Divider />}
          </React.Fragment>
        ))
      ) : (
        <Box sx={{ textAlign: "center", py: 6 }}>
          <CalendarIcon sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
          <Typography variant="body2" color="text.secondary">
            No recent trades available
          </Typography>
        </Box>
      )}
    </List>
  );

  const renderDesktopTable = () => (
    <TableContainer>
      <Table sx={{ minWidth: 650 }}>
        <TableHead>
          <TableRow sx={{ bgcolor: alpha(theme.palette.primary.main, 0.04) }}>
            <TableCell sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
              Date
            </TableCell>
            <TableCell sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
              Symbol
            </TableCell>
            <TableCell sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
              Type
            </TableCell>
            <TableCell sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
              Quantity
            </TableCell>
            <TableCell sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
              P&L
            </TableCell>
            <TableCell sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
              Status
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {performanceLoading ? (
            Array.from({ length: 5 }).map((_, index) => (
              <TableRow key={index}>
                {Array.from({ length: 6 }).map((_, cellIndex) => (
                  <TableCell key={cellIndex}>
                    <Skeleton variant="text" height={20} />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : performanceData?.recentTrades?.length > 0 ? (
            performanceData.recentTrades.map((trade, index) => (
              <TableRow
                key={index}
                sx={{
                  "&:hover": {
                    bgcolor: alpha(theme.palette.primary.main, 0.04),
                  },
                }}
              >
                <TableCell>
                  <Typography variant="body2">
                    {new Date(trade.date).toLocaleDateString()}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>
                    {trade.symbol}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={trade.type}
                    color={trade.type === "BUY" ? "success" : "error"}
                    size="small"
                    sx={{ fontSize: "0.75rem" }}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {trade.quantity?.toLocaleString("en-IN")}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography
                    variant="body2"
                    fontWeight={600}
                    color={trade.pnl >= 0 ? "success.main" : "error.main"}
                  >
                    ₹{Math.abs(trade.pnl).toLocaleString("en-IN")}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={trade.status}
                    color={trade.status === "CLOSED" ? "default" : "primary"}
                    size="small"
                    sx={{ fontSize: "0.75rem" }}
                  />
                </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={6}>
                <Box sx={{ textAlign: "center", py: 6 }}>
                  <CalendarIcon
                    sx={{ fontSize: 48, color: "text.disabled", mb: 2 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    No recent trades available
                  </Typography>
                </Box>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Box sx={{ py: { xs: 2, sm: 4 } }}>
      {/* Header */}
      <Fade in={true} timeout={300}>
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            justifyContent: "space-between",
            alignItems: { xs: "flex-start", sm: "center" },
            gap: { xs: 3, sm: 2 },
            mb: 4,
          }}
        >
          <Box>
            <Typography
              variant={isMobile ? "h5" : "h4"}
              component="h2"
              sx={{
                fontWeight: 700,
                background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                mb: 1,
              }}
            >
              Trading Performance
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{ fontSize: { xs: "0.875rem", sm: "1rem" } }}
            >
              Track your trading metrics and performance over time
            </Typography>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Tooltip title="Refresh Data">
              <IconButton
                onClick={fetchPerformanceData}
                sx={{
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  "&:hover": {
                    bgcolor: alpha(theme.palette.primary.main, 0.2),
                  },
                }}
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterIcon sx={{ color: "text.secondary", fontSize: 20 }} />
              <ButtonGroup
                size={isMobile ? "small" : "medium"}
                variant="outlined"
                sx={{
                  "& .MuiButton-root": {
                    minWidth: { xs: 32, sm: 48 },
                    fontSize: { xs: "0.75rem", sm: "0.875rem" },
                    px: { xs: 1, sm: 2 },
                  },
                }}
              >
                {timeframes.map((tf) => (
                  <Button
                    key={tf.value}
                    onClick={() => setTimeframe(tf.value)}
                    variant={timeframe === tf.value ? "contained" : "outlined"}
                    sx={{
                      fontWeight: timeframe === tf.value ? 600 : 400,
                    }}
                  >
                    {tf.label}
                  </Button>
                ))}
              </ButtonGroup>
            </Box>
          </Box>
        </Box>
      </Fade>

      {/* Performance Metrics Grid */}
      <Fade in={true} timeout={500}>
        <Grid container spacing={{ xs: 2, sm: 3 }} sx={{ mb: 4 }}>
          {performanceMetrics.map(renderMetricCard)}
        </Grid>
      </Fade>

      {/* Recent Trades */}
      <Fade in={true} timeout={700}>
        <Card
          sx={{
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            background: alpha(theme.palette.background.paper, 0.8),
            backdropFilter: "blur(20px)",
          }}
          elevation={0}
        >
          <Box
            sx={{
              p: { xs: 2, sm: 3 },
              borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CalendarIcon
                sx={{ color: "primary.main", fontSize: { xs: 20, sm: 24 } }}
              />
              <Typography
                variant={isMobile ? "h6" : "h5"}
                component="h3"
                fontWeight={600}
              >
                Recent Trades
              </Typography>
            </Box>

            {performanceData?.recentTrades?.length > 0 && (
              <Typography variant="caption" color="text.secondary">
                Last {performanceData.recentTrades.length} trades
              </Typography>
            )}
          </Box>

          <Box
            sx={{
              minHeight: 200,
              overflow: "hidden",
            }}
          >
            {isMobile ? renderMobileTradesList() : renderDesktopTable()}
          </Box>
        </Card>
      </Fade>
    </Box>
  );
};

export default PerformanceTab;
