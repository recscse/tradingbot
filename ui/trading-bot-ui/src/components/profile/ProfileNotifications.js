// src/components/profile/ProfileNotifications.jsx
import React, { useState, useEffect, useCallback, useMemo } from "react";
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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  FormControlLabel,
  TextField,
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
  Delete as DeleteIcon,
  CheckCircle as CheckIcon,
  Send as TestIcon,
} from "@mui/icons-material";
import { toast } from "react-toastify";

const ProfileNotifications = ({
  notifications = [],
  onUpdate,
  onMarkAsRead,
  onDeleteNotification,
  onTestNotification,
  loading = false,
  error = null,
  userProfile = {},
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  const [notificationSettings, setNotificationSettings] = useState({
    email_trading_alerts: true,
    email_account_updates: true,
    email_marketing: false,
    push_trading_alerts: true,
    push_account_updates: true,
    push_price_alerts: true,
    sms_security_alerts: true,
    sms_trading_alerts: false,
    frequency_trading: 'instant',
    frequency_account: 'instant',
    frequency_marketing: 'weekly',
    quiet_hours_enabled: false,
    quiet_hours_start: '22:00',
    quiet_hours_end: '08:00',
  });

  const [filter, setFilter] = useState("all");
  const [updating, setUpdating] = useState(false);
  const [localError, setLocalError] = useState("");
  const [testDialog, setTestDialog] = useState({ open: false, type: '' });
  const [bulkAction, setBulkAction] = useState(false);
  const [selectedNotifications, setSelectedNotifications] = useState(new Set());
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // Memoized notification filtering
  const filteredNotifications = useMemo(() => {
    if (!Array.isArray(notifications)) return [];
    
    return notifications.filter((notification) => {
      if (!notification) return false;
      
      switch (filter) {
        case "unread":
          return !notification.read && !notification.is_read;
        case "read":
          return notification.read || notification.is_read;
        case "security":
          return notification.type?.toLowerCase() === "security";
        case "trading":
          return notification.type?.toLowerCase() === "trading";
        case "account":
          return notification.type?.toLowerCase() === "account";
        default:
          return true;
      }
    });
  }, [notifications, filter]);

  // Load settings from props or localStorage
  useEffect(() => {
    const savedSettings = localStorage.getItem("notificationSettings");
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setNotificationSettings(prev => ({ ...prev, ...parsed }));
      } catch (error) {
        console.error("Failed to parse saved notification settings:", error);
      }
    }
  }, []);

  // Show snackbar
  const showSnackbar = useCallback((message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
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
      localStorage.setItem("notificationSettings", JSON.stringify(newSettings));

      if (onUpdate) {
        await onUpdate(newSettings);
      }

      showSnackbar("Notification preferences updated");
    } catch (error) {
      console.error("Error updating notification settings:", error);
      setLocalError("Failed to update notification settings");
      // Revert the change
      setNotificationSettings((prev) => ({
        ...prev,
        [setting]: !prev[setting],
      }));
      showSnackbar("Failed to update preferences", 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleFrequencyChange = async (setting, value) => {
    try {
      setUpdating(true);
      const newSettings = { ...notificationSettings, [setting]: value };
      setNotificationSettings(newSettings);
      localStorage.setItem("notificationSettings", JSON.stringify(newSettings));
      
      if (onUpdate) {
        await onUpdate(newSettings);
      }
      
      showSnackbar("Frequency updated");
    } catch (error) {
      console.error("Error updating frequency:", error);
      showSnackbar("Failed to update frequency", 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleTestNotification = async (type) => {
    if (!onTestNotification) return;
    
    try {
      await onTestNotification(type);
      setTestDialog({ open: false, type: '' });
      showSnackbar(`Test ${type} notification sent!`);
    } catch (error) {
      console.error("Error sending test notification:", error);
      showSnackbar("Failed to send test notification", 'error');
    }
  };

  // Safe notification icon detection
  const getNotificationIcon = useCallback((notification) => {
    if (!notification?.message) {
      return <NotificationsIcon sx={{ color: "text.secondary" }} />;
    }

    const message = notification.message.toLowerCase();
    const type = notification.type?.toLowerCase() || "";

    const iconMap = {
      security: <SecurityIcon sx={{ color: "error.main" }} />,
      trading: <TrendingUpIcon sx={{ color: "primary.main" }} />,
      payment: <DollarIcon sx={{ color: "success.main" }} />,
      account: <AccountIcon sx={{ color: "info.main" }} />,
      alert: <AlertIcon sx={{ color: "warning.main" }} />,
      info: <InfoIcon sx={{ color: "info.main" }} />,
    };

    // Check type first
    if (iconMap[type]) return iconMap[type];

    // Check message content
    for (const [key, icon] of Object.entries(iconMap)) {
      if (message.includes(key)) return icon;
    }

    return <NotificationsIcon sx={{ color: "text.secondary" }} />;
  }, []);

  // Safe notification priority detection
  const getNotificationPriority = useCallback((notification) => {
    if (!notification) return "low";

    const type = notification.type?.toLowerCase() || "";
    const priority = notification.priority?.toLowerCase() || "";
    const message = notification.message?.toLowerCase() || "";

    if (priority === "high" || type === "security" || message.includes("urgent")) {
      return "high";
    }
    if (priority === "medium" || type === "trading" || message.includes("important")) {
      return "medium";
    }
    return "low";
  }, []);

  // Safe date formatting
  const formatNotificationTime = useCallback((timeString) => {
    if (!timeString) return "Unknown time";

    try {
      const date = new Date(timeString);
      const now = new Date();
      const diffInMinutes = Math.floor((now - date) / (1000 * 60));

      if (diffInMinutes < 1) return "Just now";
      if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
      if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
      if (diffInMinutes < 10080) return `${Math.floor(diffInMinutes / 1440)}d ago`;

      return date.toLocaleDateString("en-IN", {
        month: "short",
        day: "numeric",
        year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
      });
    } catch (error) {
      return timeString;
    }
  }, []);

  const handleMarkAsRead = async (notificationId) => {
    if (!onMarkAsRead) return;
    
    try {
      await onMarkAsRead(notificationId);
      showSnackbar("Notification marked as read");
    } catch (error) {
      console.error("Error marking notification as read:", error);
      showSnackbar("Failed to mark notification as read", 'error');
    }
  };

  const handleDeleteNotification = async (notificationId) => {
    if (!onDeleteNotification) return;
    
    try {
      await onDeleteNotification(notificationId);
      showSnackbar("Notification removed");
    } catch (error) {
      console.error("Error deleting notification:", error);
      showSnackbar("Failed to remove notification", 'error');
    }
  };

  const handleBulkAction = async (action) => {
    if (selectedNotifications.size === 0) return;

    try {
      const promises = Array.from(selectedNotifications).map(id => {
        return action === 'read' ? onMarkAsRead(id) : onDeleteNotification(id);
      });

      await Promise.all(promises);
      setSelectedNotifications(new Set());
      setBulkAction(false);
      showSnackbar(`${selectedNotifications.size} notifications ${action === 'read' ? 'marked as read' : 'deleted'}`);
    } catch (error) {
      console.error("Error with bulk action:", error);
      showSnackbar("Failed to complete bulk action", 'error');
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
          frequency: "frequency_trading",
        },
        {
          key: "email_account_updates",
          title: "Account Updates",
          description: "Important account and security notifications",
          icon: SecurityIcon,
          frequency: "frequency_account",
        },
        {
          key: "email_marketing",
          title: "Marketing Emails",
          description: "Product updates and promotional content",
          icon: MarketingIcon,
          frequency: "frequency_marketing",
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

  const filterOptions = [
    { value: "all", label: "All Notifications" },
    { value: "unread", label: "Unread" },
    { value: "read", label: "Read" },
    { value: "security", label: "Security" },
    { value: "trading", label: "Trading" },
    { value: "account", label: "Account" },
  ];

  const frequencyOptions = [
    { value: "instant", label: "Instant" },
    { value: "hourly", label: "Hourly Digest" },
    { value: "daily", label: "Daily Digest" },
    { value: "weekly", label: "Weekly Digest" },
  ];

  const unreadCount = filteredNotifications.filter(n => n && !(n.read || n.is_read)).length;

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
          <Box>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" }, mb: 1 }}
            >
              {setting.description}
            </Typography>
            {setting.frequency && notificationSettings[setting.key] && (
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <Select
                  value={notificationSettings[setting.frequency] || 'instant'}
                  onChange={(e) => handleFrequencyChange(setting.frequency, e.target.value)}
                  disabled={updating}
                  sx={{ fontSize: '0.75rem' }}
                >
                  {frequencyOptions.map(option => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Box>
        }
      />

      <ListItemSecondaryAction>
        <Stack direction="row" spacing={1} alignItems="center">
          {onTestNotification && (
            <Tooltip title="Test notification">
              <IconButton
                size="small"
                onClick={() => setTestDialog({ open: true, type: category.title.toLowerCase() })}
                sx={{ color: 'text.secondary' }}
              >
                <TestIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          <Switch
            edge="end"
            checked={notificationSettings[setting.key] || false}
            onChange={() => handleSettingChange(setting.key)}
            color={category.color}
            disabled={updating}
          />
        </Stack>
      </ListItemSecondaryAction>
    </ListItem>
  );

  const renderNotificationItem = (notification, index) => {
    if (!notification) return null;

    const isRead = notification.read || notification.is_read;
    const priority = getNotificationPriority(notification);
    const isSelected = selectedNotifications.has(notification.id);

    return (
      <React.Fragment key={notification.id || index}>
        <ListItem
          sx={{
            py: 2,
            px: { xs: 2, sm: 3 },
            bgcolor: isRead
              ? "transparent"
              : alpha(theme.palette.primary.main, 0.04),
            border: isSelected
              ? `2px solid ${theme.palette.primary.main}`
              : isRead
              ? "none"
              : `1px solid ${alpha(theme.palette.primary.main, 0.12)}`,
            borderRadius: 2,
            mb: 1,
            mx: 1,
            "&:hover": {
              bgcolor: alpha(theme.palette.primary.main, 0.04),
            },
            cursor: bulkAction ? 'pointer' : 'default',
          }}
          onClick={() => {
            if (bulkAction) {
              const newSelected = new Set(selectedNotifications);
              if (isSelected) {
                newSelected.delete(notification.id);
              } else {
                newSelected.add(notification.id);
              }
              setSelectedNotifications(newSelected);
            }
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

          {!bulkAction && (
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
          )}
        </ListItem>
        {index < filteredNotifications.length - 1 && <Divider sx={{ mx: 2 }} />}
      </React.Fragment>
    );
  };

  if (loading) {
    return (
      <Box sx={{ py: { xs: 2, sm: 4 } }}>
        <Skeleton variant="rectangular" height={120} sx={{ borderRadius: 2, mb: 3 }} />
        <Skeleton variant="rectangular" height={400} sx={{ borderRadius: 2, mb: 3 }} />
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
                      height: "100%",
                      background: alpha(theme.palette[category.color].main, 0.02),
                      border: `1px solid ${alpha(theme.palette[category.color].main, 0.1)}`,
                    }}
                  >
                    <Box
                      sx={{
                        p: 2,
                        bgcolor: alpha(theme.palette[category.color].main, 0.1),
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                      }}
                    >
                      <category.icon sx={{ color: `${category.color}.main` }} />
                      <Typography variant="subtitle1" fontWeight={600}>
                        {category.title}
                      </Typography>
                    </Box>
                    <List sx={{ py: 0 }}>
                      {category.settings.map((setting) =>
                        renderSettingItem(setting, category)
                      )}
                    </List>
                  </Paper>
                </Grid>
              ))}
            </Grid>

            {/* Quiet Hours */}
            <Paper
              variant="outlined"
              sx={{
                mt: 3,
                p: 3,
                borderRadius: 3,
                background: alpha(theme.palette.info.main, 0.02),
                border: `1px solid ${alpha(theme.palette.info.main, 0.1)}`,
              }}
            >
              <Typography variant="h6" gutterBottom>
                Quiet Hours
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Disable non-urgent notifications during specified hours
              </Typography>
              
              <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.quiet_hours_enabled}
                      onChange={() => handleSettingChange('quiet_hours_enabled')}
                      color="info"
                    />
                  }
                  label="Enable quiet hours"
                />
                
                {notificationSettings.quiet_hours_enabled && (
                  <>
                    <TextField
                      label="Start time"
                      type="time"
                      size="small"
                      value={notificationSettings.quiet_hours_start}
                      onChange={(e) => handleFrequencyChange('quiet_hours_start', e.target.value)}
                      InputLabelProps={{ shrink: true }}
                    />
                    <TextField
                      label="End time"
                      type="time"
                      size="small"
                      value={notificationSettings.quiet_hours_end}
                      onChange={(e) => handleFrequencyChange('quiet_hours_end', e.target.value)}
                      InputLabelProps={{ shrink: true }}
                    />
                  </>
                )}
              </Stack>
            </Paper>
          </Box>
        </Card>
      </Fade>

      {/* Recent Notifications */}
      <Fade in={true} timeout={700}>
        <Card
          sx={{
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
            }}
          >
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              flexWrap="wrap"
              gap={2}
            >
              <Stack direction="row" alignItems="center" spacing={2}>
                <NotificationsIcon sx={{ color: "primary.main" }} />
                <Typography variant="h6" fontWeight={600}>
                  Recent Notifications
                </Typography>
                {unreadCount > 0 && (
                  <Chip
                    label={unreadCount}
                    size="small"
                    color="primary"
                    sx={{ minWidth: 'auto' }}
                  />
                )}
              </Stack>

              <Stack direction="row" spacing={1} alignItems="center">
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <Select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    startAdornment={<FilterIcon sx={{ mr: 1, fontSize: 16 }} />}
                  >
                    {filterOptions.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {filteredNotifications.length > 0 && (
                  <Button
                    variant={bulkAction ? "contained" : "outlined"}
                    size="small"
                    onClick={() => setBulkAction(!bulkAction)}
                    startIcon={bulkAction ? <CloseIcon /> : <CheckIcon />}
                  >
                    {bulkAction ? "Cancel" : "Select"}
                  </Button>
                )}

                {bulkAction && selectedNotifications.size > 0 && (
                  <>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => handleBulkAction('read')}
                      startIcon={<ReadIcon />}
                      color="primary"
                    >
                      Mark Read ({selectedNotifications.size})
                    </Button>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => handleBulkAction('delete')}
                      startIcon={<DeleteIcon />}
                      color="error"
                    >
                      Delete ({selectedNotifications.size})
                    </Button>
                  </>
                )}
              </Stack>
            </Stack>
          </Box>

          <Box sx={{ p: { xs: 1, sm: 2 } }}>
            {filteredNotifications.length > 0 ? (
              <List sx={{ py: 0 }}>
                {filteredNotifications.map((notification, index) =>
                  renderNotificationItem(notification, index)
                )}
              </List>
            ) : (
              <Box
                sx={{
                  textAlign: "center",
                  py: 6,
                  color: "text.secondary",
                }}
              >
                <NotificationsIcon
                  sx={{ fontSize: 48, mb: 2, opacity: 0.5 }}
                />
                <Typography variant="h6" gutterBottom>
                  No notifications found
                </Typography>
                <Typography variant="body2">
                  {filter === "all"
                    ? "You're all caught up! No notifications to display."
                    : `No ${filter} notifications found.`}
                </Typography>
              </Box>
            )}
          </Box>
        </Card>
      </Fade>

      {/* Test Notification Dialog */}
      <Dialog
        open={testDialog.open}
        onClose={() => setTestDialog({ open: false, type: '' })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Test {testDialog.type} Notification
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            This will send a test notification to verify your {testDialog.type} notification settings.
          </Typography>
          
          {testDialog.type === 'sms' && (
            <Alert severity="info" sx={{ mb: 2 }}>
              SMS will be sent to: {userProfile.phone || 'your registered phone number'}
            </Alert>
          )}
          
          {testDialog.type === 'email' && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Email will be sent to: {userProfile.email || 'your registered email address'}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTestDialog({ open: false, type: '' })}>
            Cancel
          </Button>
          <Button
            onClick={() => handleTestNotification(testDialog.type)}
            variant="contained"
            startIcon={<TestIcon />}
          >
            Send Test
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ProfileNotifications;