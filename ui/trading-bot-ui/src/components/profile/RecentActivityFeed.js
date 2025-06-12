// src/components/profile/RecentActivityFeed.jsx
import React, { useState, useMemo } from "react";
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  Chip,
  Divider,
  useTheme,
  alpha,
  useMediaQuery,
  Stack,
  Card,
  CardContent,
  Tooltip,
  Fade,
  Skeleton,
  Alert,
  IconButton,
  Button,
  Paper,
  Badge,
} from "@mui/material";
import {
  ShowChart as ActivityIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Schedule as ClockIcon,
  Timeline as TimelineIcon,
  AccountBalance as BrokerIcon,
  Security as SecurityIcon,
  Notifications as NotificationIcon,
  Settings as SettingsIcon,
  Payment as PaymentIcon,
  SwapHoriz as TransferIcon,
  Login as LoginIcon,
  Logout as LogoutIcon,
  Person as PersonIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
} from "@mui/icons-material";

const RecentActivityFeed = ({
  activities = [],
  loading = false,
  error = null,
  onRefresh = null,
  maxItems = 20,
  showFilter = false,
  realTime = false,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md"));

  const [filterType, setFilterType] = useState("all");
  // Removed unused expandedItem state

  // Enhanced activity categorization with more types
  const getActivityData = (activity) => {
    if (!activity || (!activity.type && !activity.description)) {
      return { icon: ActivityIcon, color: "primary", category: "general" };
    }

    const type = activity.type?.toLowerCase() || "";
    const description = activity.description?.toLowerCase() || "";
    const action = activity.action?.toLowerCase() || "";

    // Priority: explicit type > action > description content
    if (
      type === "trade" ||
      action === "buy" ||
      description.includes("buy") ||
      description.includes("purchased")
    ) {
      return {
        icon: TrendingUpIcon,
        color: "success",
        category: "trade",
        label: "BUY",
      };
    }
    if (
      type === "trade" ||
      action === "sell" ||
      description.includes("sell") ||
      description.includes("sold")
    ) {
      return {
        icon: TrendingDownIcon,
        color: "error",
        category: "trade",
        label: "SELL",
      };
    }
    if (
      type === "deposit" ||
      action === "deposit" ||
      description.includes("deposit") ||
      description.includes("credited")
    ) {
      return {
        icon: PaymentIcon,
        color: "success",
        category: "payment",
        label: "DEPOSIT",
      };
    }
    if (
      type === "withdrawal" ||
      action === "withdrawal" ||
      description.includes("withdrawal") ||
      description.includes("withdraw")
    ) {
      return {
        icon: PaymentIcon,
        color: "warning",
        category: "payment",
        label: "WITHDRAWAL",
      };
    }
    if (
      type === "transfer" ||
      action === "transfer" ||
      description.includes("transfer")
    ) {
      return {
        icon: TransferIcon,
        color: "info",
        category: "payment",
        label: "TRANSFER",
      };
    }
    if (
      type === "login" ||
      action === "login" ||
      description.includes("login") ||
      description.includes("signed in")
    ) {
      return {
        icon: LoginIcon,
        color: "info",
        category: "security",
        label: "LOGIN",
      };
    }
    if (
      type === "logout" ||
      action === "logout" ||
      description.includes("logout") ||
      description.includes("signed out")
    ) {
      return {
        icon: LogoutIcon,
        color: "secondary",
        category: "security",
        label: "LOGOUT",
      };
    }
    if (
      type === "security" ||
      description.includes("password") ||
      description.includes("2fa") ||
      description.includes("security")
    ) {
      return {
        icon: SecurityIcon,
        color: "error",
        category: "security",
        label: "SECURITY",
      };
    }
    if (
      type === "broker" ||
      description.includes("broker") ||
      description.includes("connection")
    ) {
      return {
        icon: BrokerIcon,
        color: "primary",
        category: "broker",
        label: "BROKER",
      };
    }
    if (
      type === "notification" ||
      description.includes("notification") ||
      description.includes("alert")
    ) {
      return {
        icon: NotificationIcon,
        color: "warning",
        category: "notification",
        label: "ALERT",
      };
    }
    if (
      type === "profile" ||
      description.includes("profile") ||
      description.includes("updated")
    ) {
      return {
        icon: PersonIcon,
        color: "secondary",
        category: "profile",
        label: "PROFILE",
      };
    }
    if (
      type === "settings" ||
      description.includes("settings") ||
      description.includes("preference")
    ) {
      return {
        icon: SettingsIcon,
        color: "secondary",
        category: "settings",
        label: "SETTINGS",
      };
    }
    if (
      type === "error" ||
      description.includes("error") ||
      description.includes("failed")
    ) {
      return {
        icon: ErrorIcon,
        color: "error",
        category: "error",
        label: "ERROR",
      };
    }
    if (
      type === "success" ||
      description.includes("success") ||
      description.includes("completed")
    ) {
      return {
        icon: SuccessIcon,
        color: "success",
        category: "success",
        label: "SUCCESS",
      };
    }

    return {
      icon: ActivityIcon,
      color: "primary",
      category: "general",
      label: "ACTIVITY",
    };
  };

  // Safe time formatting with better relative time
  const formatTime = (timestamp) => {
    if (!timestamp) return "Unknown time";

    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffInSeconds = Math.floor((now - date) / 1000);
      const diffInMinutes = Math.floor(diffInSeconds / 60);
      const diffInHours = Math.floor(diffInMinutes / 60);
      const diffInDays = Math.floor(diffInHours / 24);

      if (diffInSeconds < 60) {
        return diffInSeconds <= 5 ? "Just now" : `${diffInSeconds}s ago`;
      } else if (diffInMinutes < 60) {
        return `${diffInMinutes}m ago`;
      } else if (diffInHours < 24) {
        return `${diffInHours}h ago`;
      } else if (diffInDays < 7) {
        return `${diffInDays}d ago`;
      } else if (diffInDays < 30) {
        return `${Math.floor(diffInDays / 7)}w ago`;
      } else {
        return date.toLocaleDateString("en-IN", {
          month: "short",
          day: "numeric",
          year:
            date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
        });
      }
    } catch (error) {
      return "Invalid date";
    }
  };

  const formatTimeDetailed = (timestamp) => {
    if (!timestamp) return "Unknown time";
    try {
      return new Date(timestamp).toLocaleString("en-IN", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch (error) {
      return "Invalid date";
    }
  };

  // Filter activities based on selected filter
  const filteredActivities = useMemo(() => {
    if (!Array.isArray(activities)) return [];

    let filtered = activities;

    if (filterType !== "all") {
      filtered = activities.filter((activity) => {
        const activityData = getActivityData(activity);
        return activityData.category === filterType;
      });
    }

    return filtered.slice(0, maxItems);
  }, [activities, filterType, maxItems]);

  // Get unique categories for filter
  const availableCategories = useMemo(() => {
    if (!Array.isArray(activities)) return [];

    const categories = new Set(["all"]);
    activities.forEach((activity) => {
      const activityData = getActivityData(activity);
      categories.add(activityData.category);
    });

    return Array.from(categories);
  }, [activities]);

  // Removed unused getPriority function

  // Loading skeleton component
  const LoadingSkeleton = () => (
    <Stack spacing={2}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Card key={i} variant="outlined">
          <CardContent sx={{ p: 2 }}>
            <Stack direction="row" spacing={2} alignItems="flex-start">
              <Skeleton variant="circular" width={40} height={40} />
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width="60%" height={20} />
                <Skeleton variant="text" width="40%" height={16} />
                <Skeleton variant="text" width="80%" height={16} />
              </Box>
            </Stack>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );

  // Empty state component
  const EmptyState = () => (
    <Fade in={true} timeout={500}>
      <Paper
        elevation={0}
        sx={{
          textAlign: "center",
          py: { xs: 4, sm: 6 },
          px: 2,
          borderRadius: 3,
          bgcolor: alpha(theme.palette.primary.main, 0.02),
          border: `2px dashed ${alpha(theme.palette.primary.main, 0.2)}`,
        }}
      >
        <Avatar
          sx={{
            width: { xs: 60, sm: 80 },
            height: { xs: 60, sm: 80 },
            mx: "auto",
            mb: 3,
            bgcolor: alpha(theme.palette.primary.main, 0.1),
            color: "primary.main",
          }}
        >
          <TimelineIcon sx={{ fontSize: { xs: 30, sm: 40 } }} />
        </Avatar>

        <Typography
          variant={isMobile ? "h6" : "h5"}
          fontWeight={600}
          gutterBottom
          color="text.primary"
        >
          {filterType === "all"
            ? "No recent activity"
            : `No ${filterType} activities`}
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ maxWidth: 350, mx: "auto", lineHeight: 1.5 }}
        >
          {filterType === "all"
            ? "Your activities will appear here once you start using the platform"
            : `No ${filterType} activities found. Try selecting a different filter or check back later.`}
        </Typography>

        {onRefresh && (
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={onRefresh}
            sx={{ mt: 2, borderRadius: 2 }}
          >
            Refresh
          </Button>
        )}
      </Paper>
    </Fade>
  );

  // Error state component
  const ErrorState = () => (
    <Alert
      severity="error"
      sx={{
        borderRadius: 2,
        "& .MuiAlert-icon": {
          alignItems: "center",
        },
      }}
      action={
        onRefresh && (
          <Button
            color="inherit"
            size="small"
            onClick={onRefresh}
            startIcon={<RefreshIcon />}
          >
            Retry
          </Button>
        )
      }
    >
      {error || "Failed to load recent activities"}
    </Alert>
  );

  // Mobile card layout for activities
  const MobileActivityCard = ({ activity, index }) => {
    const activityData = getActivityData(activity);
    const ActivityIconComponent = activityData.icon;
    // Removed unused isExpanded variable

    return (
      <Fade in={true} timeout={300 + index * 50} key={`mobile-${index}`}>
        <Card
          variant="outlined"
          sx={{
            mb: 2,
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            "&:hover": {
              boxShadow: `0 8px 24px ${alpha(
                activityData.color === "primary"
                  ? theme.palette.primary.main
                  : theme.palette[activityData.color].main,
                0.15
              )}`,
              transform: "translateY(-2px)",
              borderColor: alpha(theme.palette[activityData.color].main, 0.3),
            },
          }}
        >
          <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
            <Stack direction="row" alignItems="flex-start" spacing={2}>
              <Avatar
                sx={{
                  bgcolor: alpha(theme.palette[activityData.color].main, 0.1),
                  color: `${activityData.color}.main`,
                  width: 40,
                  height: 40,
                  border: `2px solid ${alpha(
                    theme.palette[activityData.color].main,
                    0.2
                  )}`,
                }}
              >
                <ActivityIconComponent sx={{ fontSize: 20 }} />
              </Avatar>

              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Stack
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  mb={1}
                >
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <Chip
                      label={activityData.label}
                      size="small"
                      color={activityData.color}
                      sx={{
                        fontSize: "0.7rem",
                        height: 20,
                        fontWeight: 600,
                      }}
                    />
                    {activity.amount && (
                      <Chip
                        label={`₹${Number(activity.amount).toLocaleString(
                          "en-IN"
                        )}`}
                        size="small"
                        variant="outlined"
                        sx={{
                          fontSize: "0.65rem",
                          height: 18,
                        }}
                      />
                    )}
                  </Stack>

                  <Typography variant="caption" color="text.secondary">
                    {formatTime(activity.timestamp || activity.created_at)}
                  </Typography>
                </Stack>

                <Typography
                  variant="body2"
                  color="text.primary"
                  sx={{
                    wordBreak: "break-word",
                    lineHeight: 1.4,
                    mb: 1,
                  }}
                >
                  {activity.description ||
                    activity.message ||
                    "No description available"}
                </Typography>

                {(activity.status || activity.broker || activity.symbol) && (
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {activity.status && (
                      <Chip
                        label={activity.status}
                        size="small"
                        variant="outlined"
                        color={
                          activity.status === "completed"
                            ? "success"
                            : activity.status === "failed"
                            ? "error"
                            : "default"
                        }
                        sx={{ fontSize: "0.6rem", height: 16 }}
                      />
                    )}
                    {activity.broker && (
                      <Chip
                        label={activity.broker}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: "0.6rem", height: 16 }}
                      />
                    )}
                    {activity.symbol && (
                      <Chip
                        label={activity.symbol}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: "0.6rem", height: 16 }}
                      />
                    )}
                  </Stack>
                )}
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Fade>
    );
  };

  // Desktop list layout for activities
  const DesktopActivityList = () => (
    <List sx={{ p: 0 }}>
      {filteredActivities.map((activity, index) => {
        const activityData = getActivityData(activity);
        const ActivityIconComponent = activityData.icon;

        return (
          <React.Fragment key={`desktop-${index}`}>
            <Fade in={true} timeout={300 + index * 50}>
              <ListItem
                sx={{
                  py: 2,
                  px: 2,
                  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                  borderRadius: 2,
                  mx: 1,
                  "&:hover": {
                    bgcolor: alpha(
                      theme.palette[activityData.color].main,
                      0.04
                    ),
                    transform: "translateX(8px)",
                    boxShadow: `0 4px 12px ${alpha(
                      theme.palette[activityData.color].main,
                      0.1
                    )}`,
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 48 }}>
                  <Tooltip
                    title={`${activityData.label} Activity`}
                    placement="left"
                  >
                    <Avatar
                      sx={{
                        bgcolor: alpha(
                          theme.palette[activityData.color].main,
                          0.1
                        ),
                        color: `${activityData.color}.main`,
                        width: 36,
                        height: 36,
                        border: `2px solid ${alpha(
                          theme.palette[activityData.color].main,
                          0.2
                        )}`,
                      }}
                    >
                      <ActivityIconComponent sx={{ fontSize: 18 }} />
                    </Avatar>
                  </Tooltip>
                </ListItemIcon>

                <ListItemText
                  primary={
                    <Stack
                      direction="row"
                      alignItems="center"
                      justifyContent="space-between"
                      mb={0.5}
                    >
                      <Typography
                        variant="body2"
                        color="text.primary"
                        sx={{
                          fontWeight: 500,
                          lineHeight: 1.3,
                          flex: 1,
                          mr: 2,
                        }}
                      >
                        {activity.description ||
                          activity.message ||
                          "No description available"}
                      </Typography>

                      <Stack direction="row" alignItems="center" spacing={1}>
                        <Chip
                          label={activityData.label}
                          size="small"
                          color={activityData.color}
                          sx={{
                            fontSize: "0.7rem",
                            height: 22,
                            fontWeight: 600,
                          }}
                        />

                        {activity.amount && (
                          <Chip
                            label={`₹${Number(activity.amount).toLocaleString(
                              "en-IN"
                            )}`}
                            size="small"
                            variant="outlined"
                            sx={{
                              fontSize: "0.65rem",
                              height: 20,
                              fontWeight: 500,
      