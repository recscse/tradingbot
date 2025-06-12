// src/components/profile/ProfileNotifications.jsx
import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Switch,
  FormControl,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  Chip,
  IconButton,
  Divider,
  Paper,
  useTheme,
  alpha,
  Fade,
  useMediaQuery,
  Tooltip,
  Badge,
  Grid,
  Stack,
  Alert,
  CircularProgress,
  Skeleton,
} from "@mui/material";
import {
  Notifications as NotificationsIcon,
  Email as EmailIcon,
  PhoneIphone as SmartphoneIcon,
  Settings as SettingsIcon,
  Close as CloseIcon,
  Warning as AlertIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as DollarIcon,
  Schedule as ClockIcon,
  FilterList as FilterIcon,
  MarkEmailRead as ReadIcon,
  Security as SecurityIcon,
  CampaignOutlined as MarketingIcon,
  Sms as SmsIcon,
  AccountBalance as AccountIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import { toast } from "react-toastify";

const ProfileNotifications = ({
  notifications = [],
  onUpdate,
  onMarkAsRead,
  onDeleteNotification,
  loading = false,
  error = null,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md"));

  const [notificationSettings, setNotificationSettings] = useState({
    email_trading_alerts: true,
    email_account_updates: true,
    email_marketing: false,
    push_trading_alerts: true,
    push_account_updates: true,
    push_price_alerts: true,
    sms_security_alerts: true,
    sms_trading_alerts: false,
  });

  const [filter, setFilter] = useState("all");
  const [updating, setUpdating] = useState(false);
  const [localError, setLocalError] = useState("");

  // Load settings from props or localStorage
  useEffect(() => {
    const savedSettings = localStorage.getItem("notificationSettings");
    if (savedSettings) {
      try {
        setNotificationSettings(JSON.parse(savedSettings));
      } catch (error) {
        console.error("Failed to parse saved notification settings:", error);
      }
    }
  }, []);

  const handleSettingChange = async (setting) => {
    try {
      setUpdating(true);
      setLocalError("");

      const newSettings = {
        ...notificationSettings,
        [setting]: !notificationSettings[setting],
      };

      setNotificationSettings(newSettings);

      // Save to localStorage
      localStorage.setItem("notificationSettings", JSON.stringify(newSettings));

      // Call parent update handler if provided
      if (onUpdate) {
        await onUpdate(newSettings);
      }

      toast.success("Notification preferences updated");
    } catch (error) {
      console.error("Error updating notification settings:", error);
      setLocalError("Failed to update notification settings");
      // Revert the change
      setNotificationSettings((prev) => ({
        ...prev,
        [setting]: !prev[setting],
      }));
    } finally {
      setUpdating(false);
    }
  };

  // Safe notification filtering
  const filteredNotifications = Array.isArray(notifications)
    ? notifications.filter((notification) => {
        if (!notification) return false;
        if (filter === "unread")
          return !notification.read && !notification.is_read;
        if (filter === "read") return notification.read || notification.is_read;
        return true;
      })
    : [];

  // Safe notification icon detection
  const getNotificationIcon = (notification) => {
    if (!notification || !notification.message) {
      return <NotificationsIcon sx={{ color: "text.secondary" }} />;
    }

    const message = notification.message.toLowerCase();
    const type = notification.type?.toLowerCase() || "";

    // Priority: notification type first, then message content
    if (
      type === "security" ||
      message.includes("security") ||
      message.includes("login")
    ) {
      return <SecurityIcon sx={{ color: "error.main" }} />;
    }
    if (
      type === "trading" ||
      message.includes("trade") ||
      message.includes("order")
    ) {
      return <TrendingUpIcon sx={{ color: "primary.main" }} />;
    }
    if (
      type === "payment" ||
      message.includes("payment") ||
      message.includes("revenue") ||
      message.includes("fund")
    ) {
      return <DollarIcon sx={{ color: "success.main" }} />;
    }
    if (
      type === "account" ||
      message.includes("account") ||
      message.includes("profile")
    ) {
      return <AccountIcon sx={{ color: "info.main" }} />;
    }
    if (
      type === "alert" ||
      message.includes("alert") ||
      message.includes("warning")
    ) {
      return <AlertIcon sx={{ color: "warning.main" }} />;
    }
    if (
      type === "info" ||
      message.includes("update") ||
      message.includes("news")
    ) {
      return <InfoIcon sx={{ color: "info.main" }} />;
    }

    return <NotificationsIcon sx={{ color: "text.secondary" }} />;
  };

  // Safe notification priority detection
  const getNotificationPriority = (notification) => {
    if (!notification) return "low";

    const type = notification.type?.toLowerCase() || "";
    const priority = notification.priority?.toLowerCase() || "";
    const message = notification.message?.toLowerCase() || "";

    if (
      priority === "high" ||
      type === "security" ||
      message.includes("urgent")
    ) {
      return "high";
    }
    if (
      priority === "medium" ||
      type === "trading" ||
      message.includes("important")
    ) {
      return "medium";
    }
    return "low";
  };

  // Safe date formatting
  const formatNotificationTime = (timeString) => {
    if (!timeString) return "Unknown time";

    try {
      const date = new Date(timeString);
      const now = new Date();
      const diffInMinutes = Math.floor((now - date) / (1000 * 60));

      if (diffInMinutes < 1) return "Just now";
      if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
      if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
      if (diffInMinutes < 10080)
        return `${Math.floor(diffInMinutes / 1440)}d ago`;

      return date.toLocaleDateString("en-IN", {
        month: "short",
        day: "numeric",
        year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
      });
    } catch (error) {
      return timeString;
    }
  };

  const notificationCategories = [
    {
      title: "Email Notifications",
      icon: EmailIcon,
      color: "primary",
      settings: [
        {
          key: "email_trading_alerts",
          title: "Trading Alerts",
          description: "Get notified about trade executions and market changes",
          icon: TrendingUpIcon,
        },
        {
          key: "email_account_updates",
          title: "Account Updates",
          description: "Important account and security notifications",
          icon: SecurityIcon,
        },
        {
          key: "email_marketing",
          title: "Marketing Emails",
          description: "Product updates and promotional content",
          icon: MarketingIcon,
        },
      ],
    },
    {
      title: "Push Notifications",
      icon: SmartphoneIcon,
      color: "secondary",
      settings: [
        {
          key: "push_trading_alerts",
          title: "Trading Alerts",
          description: "Real-time trading notifications",
          icon: TrendingUpIcon,
        },
        {
          key: "push_account_updates",
          title: "Account Updates",
          description: "Important account notifications",
          icon: SecurityIcon,
        },
        {
          key: "push_price_alerts",
          title: "Price Alerts",
          description: "Stock price movement notifications",
          icon: DollarIcon,
        },
      ],
    },
    {
      title: "SMS Notifications",
      icon: SmsIcon,
      color: "success",
      settings: [
        {
          key: "sms_security_alerts",
          title: "Security Alerts",
          description: "Critical security notifications via SMS",
          icon: SecurityIcon,
        },
        {
          key: "sms_trading_alerts",
          title: "Trading Alerts",
          description: "Important trading updates via SMS",
          icon: TrendingUpIcon,
        },
      ],
    },
  ];

  const unreadCount = filteredNotifications.filter(
    (n) => n && !(n.read || n.is_read)
  ).length;

  const handleMarkAsRead = async (notificationId) => {
    if (onMarkAsRead) {
      try {
        await onMarkAsRead(notificationId);
        toast.success("Notification marked as read");
      } catch (error) {
        console.error("Error marking notification as read:", error);
        toast.error("Failed to mark notification as read");
      }
    }
  };

  const handleDeleteNotification = async (notificationId) => {
    if (onDeleteNotification) {
      try {
        await onDeleteNotification(notificationId);
        toast.success("Notification removed");
      } catch (error) {
        console.error("Error deleting notification:", error);
        toast.error("Failed to remove notification");
      }
    }
  };

  const renderSettingItem = (setting, category) => (
    <ListItem
      key={setting.key}
      sx={{
        py: 2,
        px: { xs: 2, sm: 3 },
        "&:hover": {
          bgcolor: alpha(theme.palette[category.color].main, 0.04),
        },
        borderRadius: 1,
        mx: 1,
      }}
    >
      <ListItemIcon>
        <Avatar
          sx={{
            width: 36,
            height: 36,
            bgcolor: alpha(theme.palette[category.color].main, 0.1),
            color: `${category.color}.main`,
          }}
        >
          <setting.icon sx={{ fontSize: 20 }} />
        </Avatar>
      </ListItemIcon>

      <ListItemText
        primary={
          <Typography variant="body1" fontWeight={500}>
            {setting.title}
          </Typography>
        }
        secondary={
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" } }}
          >
            {setting.description}
          </Typography>
        }
      />

      <ListItemSecondaryAction>
        <Switch
          edge="end"
          checked={notificationSettings[setting.key] || false}
          onChange={() => handleSettingChange(setting.key)}
          color={category.color}
          disabled={updating}
        />
      </ListItemSecondaryAction>
    </ListItem>
  );

  const renderNotificationItem = (notification, index) => {
    if (!notification) return null;

    const isRead = notification.read || notification.is_read;
    const priority = getNotificationPriority(notification);

    return (
      <React.Fragment key={notification.id || index}>
        <ListItem
          sx={{
            py: 2,
            px: { xs: 2, sm: 3 },
            bgcolor: isRead
              ? "transparent"
              : alpha(theme.palette.primary.main, 0.04),
            border: isRead
              ? "none"
              : `1px solid ${alpha(theme.palette.primary.main, 0.12)}`,
            borderRadius: isRead ? 0 : 2,
            mb: isRead ? 0 : 1,
            mx: 1,
            "&:hover": {
              bgcolor: alpha(theme.palette.primary.main, 0.04),
            },
          }}
        >
          <ListItemIcon>
            <Badge
              variant="dot"
              color={priority === "high" ? "error" : "primary"}
              invisible={isRead}
              sx={{
                "& .MuiBadge-badge": {
                  right: 2,
                  top: 2,
                },
              }}
            >
              <Avatar
                sx={{
                  width: { xs: 36, sm: 40 },
                  height: { xs: 36, sm: 40 },
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                }}
              >
                {getNotificationIcon(notification)}
              </Avatar>
            </Badge>
          </ListItemIcon>

          <ListItemText
            primary={
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography
                  variant="body1"
                  sx={{
                    fontWeight: isRead ? 400 : 600,
                    color: isRead ? "text.secondary" : "text.primary",
                    fontSize: { xs: "0.875rem", sm: "1rem" },
                    flex: 1,
                  }}
                >
                  {notification.message || "No message"}
                </Typography>
                {priority === "high" && !isRead && (
                  <Chip
                    label="Urgent"
                    size="small"
                    color="error"
                    sx={{
                      fontSize: "0.6rem",
                      height: 18,
                      display: { xs: "none", sm: "flex" },
                    }}
                  />
                )}
              </Stack>
            }
            secondary={
              <Box sx={{ display: "flex", alignItems: "center", mt: 0.5 }}>
                <ClockIcon
                  sx={{ fontSize: 14, mr: 0.5, color: "text.disabled" }}
                />
                <Typography variant="caption" color="text.disabled">
                  {formatNotificationTime(
                    notification.time || notification.created_at
                  )}
                </Typography>
                {notification.type && (
                  <>
                    <Typography
                      variant="caption"
                      color="text.disabled"
                      sx={{ mx: 1 }}
                    >
                      •
                    </Typography>
                    <Chip
                      label={notification.type}
                      size="small"
                      variant="outlined"
                      sx={{
                        fontSize: "0.6rem",
                        height: 16,
                        "& .MuiChip-label": { px: 0.5 },
                      }}
                    />
                  </>
                )}
              </Box>
            }
          />

          <ListItemSecondaryAction>
            <Stack direction="row" spacing={1} alignItems="center">
              {!isRead && (
                <Chip
                  label="New"
                  size="small"
                  color="primary"
                  sx={{
                    fontSize: "0.65rem",
                    height: 20,
                    display: { xs: "none", sm: "flex" },
                  }}
                />
              )}
              {!isRead && (
                <Tooltip title="Mark as read">
                  <IconButton
                    size="small"
                    sx={{ color: "text.secondary" }}
                    onClick={() => handleMarkAsRead(notification.id)}
                  >
                    <ReadIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              <Tooltip title="Remove">
                <IconButton
                  size="small"
                  sx={{ color: "text.secondary" }}
                  onClick={() => handleDeleteNotification(notification.id)}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
          </ListItemSecondaryAction>
        </ListItem>
        {index < filteredNotifications.length - 1 && <Divider sx={{ mx: 2 }} />}
      </React.Fragment>
    );
  };

  if (loading) {
    return (
      <Box sx={{ py: { xs: 2, sm: 4 } }}>
        <Skeleton
          variant="rectangular"
          height={120}
          sx={{ borderRadius: 2, mb: 3 }}
        />
        <Skeleton
          variant="rectangular"
          height={400}
          sx={{ borderRadius: 2, mb: 3 }}
        />
        <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />
      </Box>
    );
  }

  return (
    <Box sx={{ py: { xs: 2, sm: 4 } }}>
      {/* Header */}
      <Fade in={true} timeout={300}>
        <Card
          sx={{
            mb: 4,
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            background: `linear-gradient(135deg, 
              ${alpha(theme.palette.background.paper, 0.9)} 0%, 
              ${alpha(theme.palette.primary.main, 0.02)} 100%
            )`,
            backdropFilter: "blur(20px)",
            borderRadius: 3,
          }}
          elevation={0}
        >
          <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              flexWrap="wrap"
              gap={2}
            >
              <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar
                  sx={{
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    color: "primary.main",
                    width: { xs: 40, sm: 48 },
                    height: { xs: 40, sm: 48 },
                  }}
                >
                  <NotificationsIcon />
                </Avatar>
                <Box>
                  <Typography
                    variant={isMobile ? "h5" : "h4"}
                    component="h2"
                    fontWeight={700}
                    sx={{
                      background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                      backgroundClip: "text",
                      WebkitBackgroundClip: "text",
                      WebkitTextFillColor: "transparent",
                    }}
                  >
                    Notifications
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Manage your notification preferences and view recent alerts
                  </Typography>
                </Box>
              </Stack>

              {unreadCount > 0 && (
                <Chip
                  label={`${unreadCount} unread`}
                  color="primary"
                  sx={{ fontWeight: 600 }}
                />
              )}
            </Stack>
          </CardContent>
        </Card>
      </Fade>

      {/* Error Alert */}
      {(error || localError) && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          {error || localError}
        </Alert>
      )}

      {/* Notification Settings */}
      <Fade in={true} timeout={500}>
        <Card
          sx={{
            mb: 4,
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            background: alpha(theme.palette.background.paper, 0.8),
            backdropFilter: "blur(20px)",
            borderRadius: 3,
          }}
          elevation={0}
        >
          <Box
            sx={{
              p: { xs: 3, sm: 4 },
              borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              display: "flex",
              alignItems: "center",
              gap: 2,
            }}
          >
            <SettingsIcon sx={{ color: "primary.main" }} />
            <Typography variant="h6" fontWeight={600}>
              Notification Preferences
            </Typography>
            {updating && <CircularProgress size={20} />}
          </Box>

          <Box sx={{ p: { xs: 2, sm: 3 } }}>
            <Grid container spacing={{ xs: 2, sm: 3 }}>
              {notificationCategories.map((category, categoryIndex) => (
                <Grid item xs={12} lg={4} key={categoryIndex}>
                  <Paper
                    variant="outlined"
                    sx={{
                      borderRadius: 3,
                      overflow: "hidden",
                      he