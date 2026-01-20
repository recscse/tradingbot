import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Container,
  Paper,
  Tabs,
  Tab,
  Button,
  Grid,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  Chip,
  CircularProgress,
  Alert,
} from "@mui/material";
import {
  Notifications as NotificationsIcon,
  Settings as SettingsIcon,
  MarkEmailRead as MarkAllReadIcon,
} from "@mui/icons-material";
import { useNotifications } from "../contexts/NotificationContext";
import NotificationItem from "../components/notifications/NotificationItem";
import { notificationService } from "../services/notificationService";

const NotificationsPage = () => {
  const [tabValue, setTabValue] = useState(0);
  const [filter, setFilter] = useState("all");
  const [settings, setSettings] = useState(null);
  const [loadingSettings, setLoadingSettings] = useState(false);

  const {
    notifications,
    loading,
    error,
    markAsRead,
    markAllAsRead,
    deleteNotification,
  } = useNotifications();

  const filterTypes = [
    { value: "all", label: "All" },
    { value: "trade_executed", label: "Trades" },
    { value: "price_alert", label: "Price Alerts" },
    { value: "stop_loss", label: "Stop Loss" },
    { value: "system", label: "System" },
  ];

  const filteredNotifications = notifications.filter((notification) => {
    if (filter === "all") return true;
    return notification.type === filter;
  });

  const unreadNotifications = filteredNotifications.filter((n) => !n.is_read);

  useEffect(() => {
    fetchNotificationSettings();
  }, []);

  const fetchNotificationSettings = async () => {
    try {
      setLoadingSettings(true);
      const data = await notificationService.getSettings();
      setSettings(data.settings);
    } catch (error) {
      console.error("Error fetching notification settings:", error);
    } finally {
      setLoadingSettings(false);
    }
  };

  const updateNotificationSettings = async (newSettings) => {
    try {
      await notificationService.updateSettings(newSettings);
      setSettings(newSettings);
    } catch (error) {
      console.error("Error updating notification settings:", error);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Notifications
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Stay updated with your trading activities and market alerts
        </Typography>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(e, newValue) => setTabValue(newValue)}
          sx={{ borderBottom: 1, borderColor: "divider" }}
        >
          <Tab
            icon={<NotificationsIcon />}
            label="All Notifications"
            iconPosition="start"
          />
          <Tab icon={<SettingsIcon />} label="Settings" iconPosition="start" />
        </Tabs>

        {/* Notifications Tab */}
        {tabValue === 0 && (
          <Box sx={{ p: 3 }}>
            {/* Actions Bar */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 3,
              }}
            >
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                {filterTypes.map((type) => (
                  <Chip
                    key={type.value}
                    label={type.label}
                    onClick={() => setFilter(type.value)}
                    color={filter === type.value ? "primary" : "default"}
                    variant={filter === type.value ? "filled" : "outlined"}
                  />
                ))}
              </Box>

              {unreadNotifications.length > 0 && (
                <Button
                  startIcon={<MarkAllReadIcon />}
                  onClick={markAllAsRead}
                  variant="outlined"
                  size="small"
                >
                  Mark All Read
                </Button>
              )}
            </Box>

            {/* Notifications List */}
            {loading ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
              </Box>
            ) : error ? (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            ) : filteredNotifications.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <NotificationsIcon
                  sx={{ fontSize: 64, color: "text.secondary", mb: 2 }}
                />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No notifications found
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {filter === "all"
                    ? "You're all caught up! New notifications will appear here."
                    : `No ${filterTypes
                        .find((f) => f.value === filter)
                        ?.label.toLowerCase()} notifications found.`}
                </Typography>
              </Box>
            ) : (
              <Paper variant="outlined" sx={{ borderRadius: 2 }}>
                {filteredNotifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onMarkAsRead={markAsRead}
                    onDelete={deleteNotification}
                  />
                ))}
              </Paper>
            )}
          </Box>
        )}

        {/* Settings Tab */}
        {tabValue === 1 && (
          <Box sx={{ p: 3 }}>
            {loadingSettings ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
              </Box>
            ) : (
              <Grid container spacing={3}>
                {/* Email Notifications */}
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Email Notifications
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mb: 2 }}
                      >
                        Receive notifications via email
                      </Typography>

                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 1,
                        }}
                      >
                        <FormControlLabel
                          control={
                            <Switch
                              checked={
                                settings?.email_notifications?.trade_executed ||
                                false
                              }
                              onChange={(e) =>
                                updateNotificationSettings({
                                  ...settings,
                                  email_notifications: {
                                    ...settings?.email_notifications,
                                    trade_executed: e.target.checked,
                                  },
                                })
                              }
                            />
                          }
                          label="Trade Execution"
                        />
                        <FormControlLabel
                          control={
                            <Switch
                              checked={
                                settings?.email_notifications?.price_alerts ||
                                false
                              }
                              onChange={(e) =>
                                updateNotificationSettings({
                                  ...settings,
                                  email_notifications: {
                                    ...settings?.email_notifications,
                                    price_alerts: e.target.checked,
                                  },
                                })
                              }
                            />
                          }
                          label="Price Alerts"
                        />
                        <FormControlLabel
                          control={
                            <Switch
                              checked={
                                settings?.email_notifications?.stop_loss ||
                                false
                              }
                              onChange={(e) =>
                                updateNotificationSettings({
                                  ...settings,
                                  email_notifications: {
                                    ...settings?.email_notifications,
                                    stop_loss: e.target.checked,
                                  },
                                })
                              }
                            />
                          }
                          label="Stop Loss Triggers"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Push Notifications */}
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Push Notifications
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mb: 2 }}
                      >
                        Receive browser push notifications
                      </Typography>

                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 1,
                        }}
                      >
                        <FormControlLabel
                          control={
                            <Switch
                              checked={
                                settings?.push_notifications?.enabled || false
                              }
                              onChange={(e) =>
                                updateNotificationSettings({
                                  ...settings,
                                  push_notifications: {
                                    ...settings?.push_notifications,
                                    enabled: e.target.checked,
                                  },
                                })
                              }
                            />
                          }
                          label="Enable Push Notifications"
                        />
                        <FormControlLabel
                          control={
                            <Switch
                              checked={
                                settings?.push_notifications?.sound || false
                              }
                              onChange={(e) =>
                                updateNotificationSettings({
                                  ...settings,
                                  push_notifications: {
                                    ...settings?.push_notifications,
                                    sound: e.target.checked,
                                  },
                                })
                              }
                            />
                          }
                          label="Sound Alerts"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Trading Alerts */}
                <Grid item xs={12}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Trading Alerts
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mb: 2 }}
                      >
                        Configure when to receive trading-related notifications
                      </Typography>

                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={
                                  settings?.trading_alerts
                                    ?.immediate_execution || false
                                }
                                onChange={(e) =>
                                  updateNotificationSettings({
                                    ...settings,
                                    trading_alerts: {
                                      ...settings?.trading_alerts,
                                      immediate_execution: e.target.checked,
                                    },
                                  })
                                }
                              />
                            }
                            label="Immediate Trade Execution"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={
                                  settings?.trading_alerts?.daily_summary ||
                                  false
                                }
                                onChange={(e) =>
                                  updateNotificationSettings({
                                    ...settings,
                                    trading_alerts: {
                                      ...settings?.trading_alerts,
                                      daily_summary: e.target.checked,
                                    },
                                  })
                                }
                              />
                            }
                            label="Daily Trading Summary"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={
                                  settings?.trading_alerts
                                    ?.profit_loss_alerts || false
                                }
                                onChange={(e) =>
                                  updateNotificationSettings({
                                    ...settings,
                                    trading_alerts: {
                                      ...settings?.trading_alerts,
                                      profit_loss_alerts: e.target.checked,
                                    },
                                  })
                                }
                              />
                            }
                            label="Profit/Loss Alerts"
                          />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={
                                  settings?.trading_alerts?.market_hours_only ||
                                  false
                                }
                                onChange={(e) =>
                                  updateNotificationSettings({
                                    ...settings,
                                    trading_alerts: {
                                      ...settings?.trading_alerts,
                                      market_hours_only: e.target.checked,
                                    },
                                  })
                                }
                              />
                            }
                            label="Market Hours Only"
                          />
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default NotificationsPage;
