import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Stack,
  Tabs,
  Tab,
  Button,
  IconButton,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  InputAdornment,
} from "@mui/material";
import {
  Notifications as NotificationsIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  MarkEmailRead as MarkAllIcon,
  Search as SearchIcon,
} from "@mui/icons-material";
import { useNotifications } from "../../context/NotificationContext";
import NotificationItem from "./NotificationItem";
import NotificationPreferences from "./NotificationPreferences";
import TokenStatusWidget from "./TokenStatusWidget";

const NotificationsDashboard = () => {
  const {
    notifications,
    loading,
    unreadCount,
    fetchNotifications,
    markAllAsRead,
    getNotificationStats,
  } = useNotifications();

  const [activeTab, setActiveTab] = useState(0);
  const [filterType, setFilterType] = useState("all");
  const [filterPriority, setFilterPriority] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [stats, setStats] = useState(null);

  // ✅ Memoized stats loader to fix eslint deps warning
  const loadStats = useCallback(async () => {
    try {
      const statsData = await getNotificationStats(7);
      setStats(statsData);
    } catch (error) {
      console.error("Failed to load notification stats:", error);
    }
  }, [getNotificationStats]);

  // ✅ Fixed ESLint deps: now includes loadStats
  useEffect(() => {
    fetchNotifications();
    loadStats();
  }, [fetchNotifications, loadStats]);

  const handleRefresh = () => {
    fetchNotifications();
    loadStats();
  };

  const handleMarkAllAsRead = async () => {
    await markAllAsRead();
    await fetchNotifications();
  };

  // ✅ useMemo to avoid recomputing filters on every render
  const filteredNotifications = useMemo(() => {
    return notifications.filter((notification) => {
      const matchesType =
        filterType === "all" || notification.type === filterType;
      const matchesPriority =
        filterPriority === "all" || notification.priority === filterPriority;
      const matchesSearch =
        !searchQuery ||
        notification.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        notification.message.toLowerCase().includes(searchQuery.toLowerCase());

      return matchesType && matchesPriority && matchesSearch;
    });
  }, [notifications, filterType, filterPriority, searchQuery]);

  const tabContent = [
    // All Notifications Tab
    <Stack key="notifications" spacing={2}>
      {/* Controls */}
      <Card>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              gap: 2,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <TextField
              placeholder="Search notifications..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              size="small"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ color: "text.secondary" }} />
                  </InputAdornment>
                ),
              }}
              sx={{ minWidth: 200 }}
            />

            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Type</InputLabel>
              <Select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                label="Type"
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="order_executed">Orders</MenuItem>
                <MenuItem value="token_expired">Tokens</MenuItem>
                <MenuItem value="margin_call">Risk</MenuItem>
                <MenuItem value="ai_buy_signal">AI Signals</MenuItem>
              </Select>
            </FormControl>

            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Priority</InputLabel>
              <Select
                value={filterPriority}
                onChange={(e) => setFilterPriority(e.target.value)}
                label="Priority"
              >
                <MenuItem value="all">All Priorities</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="normal">Normal</MenuItem>
                <MenuItem value="low">Low</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ ml: "auto", display: "flex", gap: 1 }}>
              <Button
                startIcon={<MarkAllIcon />}
                onClick={handleMarkAllAsRead}
                disabled={unreadCount === 0}
                size="small"
              >
                Mark All Read ({unreadCount})
              </Button>
              <IconButton onClick={handleRefresh} size="small">
                <RefreshIcon />
              </IconButton>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Token Status */}
      <TokenStatusWidget />

      {/* Statistics Cards */}
      {stats && (
        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: "center" }}>
                <Typography variant="h4" color="primary">
                  {stats.total_notifications}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: "center" }}>
                <Typography variant="h4" color="error">
                  {stats.unread_notifications}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Unread
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: "center" }}>
                <Typography variant="h4" color="success.main">
                  {stats.read_rate}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Read Rate
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: "center" }}>
                <Typography variant="h4" color="info.main">
                  {stats.period_days}d
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Period
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Notifications List */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          {loading ? (
            <Box sx={{ p: 4, textAlign: "center" }}>
              <Typography>Loading notifications...</Typography>
            </Box>
          ) : filteredNotifications.length === 0 ? (
            <Box sx={{ p: 4, textAlign: "center" }}>
              <NotificationsIcon
                sx={{ fontSize: 64, color: "text.disabled", mb: 2 }}
              />
              <Typography variant="h6" color="text.secondary">
                {searchQuery || filterType !== "all" || filterPriority !== "all"
                  ? "No notifications match your filters"
                  : "No notifications yet"}
              </Typography>
            </Box>
          ) : (
            <Stack divider={<Divider />}>
              {filteredNotifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkAsRead={async (id) => {
                    await fetchNotifications();
                  }}
                  onDelete={async (id) => {
                    await fetchNotifications();
                  }}
                  onClick={(notification) => {
                    console.log("Notification clicked:", notification);
                  }}
                />
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>,

    // Preferences Tab
    <NotificationPreferences key="preferences" />,
  ];

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Notifications
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage your trading notifications and preferences
        </Typography>
      </Box>

      {/* Tabs */}
      <Card sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: "divider" }}
        >
          <Tab
            icon={<NotificationsIcon />}
            label={`Notifications ${unreadCount > 0 ? `(${unreadCount})` : ""}`}
            iconPosition="start"
          />
          <Tab
            icon={<SettingsIcon />}
            label="Preferences"
            iconPosition="start"
          />
        </Tabs>
      </Card>

      {/* Tab Content */}
      {tabContent[activeTab]}
    </Box>
  );
};

export default NotificationsDashboard;
