import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  FormGroup,
  Button,
  Alert,
  Chip,
  TextField,
  Grid,
  Stack,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  Email as EmailIcon,
  Sms as SmsIcon,
  Notifications as PushIcon,
  Schedule as ScheduleIcon,
  Security as SecurityIcon,
  TrendingUp as TradingIcon,
  Settings as SettingsIcon,
  PlayArrow as TestIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import { useNotifications } from "../../context/NotificationContext";

const NotificationPreferences = () => {
  // const theme = useTheme();
  const {
    preferences,
    fetchPreferences,
    updatePreferences,
    sendTestNotification,
  } = useNotifications();

  const [localPreferences, setLocalPreferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testLoading, setTestLoading] = useState({});
  const [hasChanges, setHasChanges] = useState(false);

  // Load preferences on component mount
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        await fetchPreferences();
      } finally {
        setLoading(false);
      }
    };
    loadPreferences();
  }, [fetchPreferences]);

  // Update local state when preferences are loaded
  useEffect(() => {
    if (preferences) {
      setLocalPreferences(preferences);
      setHasChanges(false);
    }
  }, [preferences]);

  const handlePreferenceChange = (field, value) => {
    setLocalPreferences((prev) => ({
      ...prev,
      [field]: value,
    }));
    setHasChanges(true);
  };

  const handleNestedPreferenceChange = (field, subfield, value) => {
    setLocalPreferences((prev) => ({
      ...prev,
      [field]: {
        ...prev[field],
        [subfield]: value,
      },
    }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updatePreferences(localPreferences);
      setHasChanges(false);
    } catch (error) {
      console.error("Failed to save preferences:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleTestNotification = async (channel, type = "order_executed") => {
    const key = `${channel}-${type}`;
    setTestLoading((prev) => ({ ...prev, [key]: true }));

    try {
      await sendTestNotification(type, channel);
    } catch (error) {
      console.error(`Failed to send test ${channel} notification:`, error);
    } finally {
      setTestLoading((prev) => ({ ...prev, [key]: false }));
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (!localPreferences) {
    return (
      <Card>
        <CardContent>
          <Alert severity="error">
            Failed to load notification preferences. Please try again.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Header with save button */}
      <Paper
        sx={{
          p: 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>
          <Typography variant="h6" fontWeight={600}>
            Notification Preferences
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Customize how and when you receive notifications
          </Typography>
        </Box>

        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            startIcon={<RefreshIcon />}
            variant="outlined"
            onClick={() => window.location.reload()}
            size="small"
          >
            Reset
          </Button>
          <Button
            startIcon={<SaveIcon />}
            variant="contained"
            onClick={handleSave}
            disabled={!hasChanges || saving}
            size="small"
          >
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </Box>
      </Paper>

      {/* Channel Preferences */}
      <Card>
        <CardContent>
          <Typography
            variant="h6"
            gutterBottom
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <SettingsIcon />
            Notification Channels
          </Typography>

          <Grid container spacing={3}>
            {/* Email Preferences */}
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, height: "100%" }}>
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
                >
                  <EmailIcon color="primary" />
                  <Typography variant="subtitle1" fontWeight={600}>
                    Email
                  </Typography>
                  <Chip
                    label={localPreferences.email_enabled ? "ON" : "OFF"}
                    color={
                      localPreferences.email_enabled ? "success" : "default"
                    }
                    size="small"
                  />
                </Box>

                <FormControlLabel
                  control={
                    <Switch
                      checked={localPreferences.email_enabled}
                      onChange={(e) =>
                        handlePreferenceChange(
                          "email_enabled",
                          e.target.checked
                        )
                      }
                    />
                  }
                  label="Enable email notifications"
                  sx={{ mb: 2 }}
                />

                <Button
                  startIcon={
                    testLoading["email-order_executed"] ? (
                      <CircularProgress size={16} />
                    ) : (
                      <TestIcon />
                    )
                  }
                  variant="outlined"
                  size="small"
                  fullWidth
                  disabled={
                    !localPreferences.email_enabled ||
                    testLoading["email-order_executed"]
                  }
                  onClick={() => handleTestNotification("email")}
                >
                  Send Test Email
                </Button>
              </Paper>
            </Grid>

            {/* SMS Preferences */}
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, height: "100%" }}>
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
                >
                  <SmsIcon color="primary" />
                  <Typography variant="subtitle1" fontWeight={600}>
                    SMS
                  </Typography>
                  <Chip
                    label={localPreferences.sms_enabled ? "ON" : "OFF"}
                    color={localPreferences.sms_enabled ? "success" : "default"}
                    size="small"
                  />
                </Box>

                <FormControlLabel
                  control={
                    <Switch
                      checked={localPreferences.sms_enabled}
                      onChange={(e) =>
                        handlePreferenceChange("sms_enabled", e.target.checked)
                      }
                    />
                  }
                  label="Enable SMS notifications"
                  sx={{ mb: 2 }}
                />

                <Button
                  startIcon={
                    testLoading["sms-order_executed"] ? (
                      <CircularProgress size={16} />
                    ) : (
                      <TestIcon />
                    )
                  }
                  variant="outlined"
                  size="small"
                  fullWidth
                  disabled={
                    !localPreferences.sms_enabled ||
                    testLoading["sms-order_executed"]
                  }
                  onClick={() => handleTestNotification("sms")}
                >
                  Send Test SMS
                </Button>
              </Paper>
            </Grid>

            {/* Push Preferences */}
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, height: "100%" }}>
                <Box
                  sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
                >
                  <PushIcon color="primary" />
                  <Typography variant="subtitle1" fontWeight={600}>
                    Push
                  </Typography>
                  <Chip
                    label={localPreferences.push_enabled ? "ON" : "OFF"}
                    color={
                      localPreferences.push_enabled ? "success" : "default"
                    }
                    size="small"
                  />
                </Box>

                <FormControlLabel
                  control={
                    <Switch
                      checked={localPreferences.push_enabled}
                      onChange={(e) =>
                        handlePreferenceChange("push_enabled", e.target.checked)
                      }
                    />
                  }
                  label="Enable push notifications"
                  sx={{ mb: 2 }}
                />

                <Button
                  startIcon={
                    testLoading["push-order_executed"] ? (
                      <CircularProgress size={16} />
                    ) : (
                      <TestIcon />
                    )
                  }
                  variant="outlined"
                  size="small"
                  fullWidth
                  disabled={
                    !localPreferences.push_enabled ||
                    testLoading["push-order_executed"]
                  }
                  onClick={() => handleTestNotification("push")}
                >
                  Send Test Push
                </Button>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Notification Types */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Notification Types
          </Typography>

          <Stack spacing={1}>
            {/* Trading Notifications */}
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <TradingIcon />
                  <Typography fontWeight={600}>Trading & Orders</Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <FormGroup>
                  {Object.entries(localPreferences.email_types || {}).map(
                    ([key, value]) => {
                      if (
                        !key.includes("trading") &&
                        !key.includes("order") &&
                        !key.includes("position")
                      )
                        return null;
                      return (
                        <FormControlLabel
                          key={key}
                          control={
                            <Switch
                              checked={value}
                              onChange={(e) =>
                                handleNestedPreferenceChange(
                                  "email_types",
                                  key,
                                  e.target.checked
                                )
                              }
                            />
                          }
                          label={key
                            .replace(/_/g, " ")
                            .replace(/\b\w/g, (l) => l.toUpperCase())}
                        />
                      );
                    }
                  )}
                </FormGroup>
              </AccordionDetails>
            </Accordion>

            {/* Token & Security */}
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <SecurityIcon />
                  <Typography fontWeight={600}>Token & Security</Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Token expiry notifications are critical for preventing trading
                  disruptions
                </Alert>
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          localPreferences.email_types?.token_expiry !== false
                        }
                        onChange={(e) =>
                          handleNestedPreferenceChange(
                            "email_types",
                            "token_expiry",
                            e.target.checked
                          )
                        }
                      />
                    }
                    label="Token expiry alerts (Email)"
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          localPreferences.sms_types?.token_expiry !== false
                        }
                        onChange={(e) =>
                          handleNestedPreferenceChange(
                            "sms_types",
                            "token_expiry",
                            e.target.checked
                          )
                        }
                      />
                    }
                    label="Token expiry alerts (SMS)"
                  />
                </FormGroup>
              </AccordionDetails>
            </Accordion>
          </Stack>
        </CardContent>
      </Card>

      {/* Quiet Hours */}
      <Card>
        <CardContent>
          <Typography
            variant="h6"
            gutterBottom
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <ScheduleIcon />
            Quiet Hours
          </Typography>

          <FormControlLabel
            control={
              <Switch
                checked={localPreferences.quiet_hours_enabled}
                onChange={(e) =>
                  handlePreferenceChange(
                    "quiet_hours_enabled",
                    e.target.checked
                  )
                }
              />
            }
            label="Enable quiet hours (non-critical notifications will be paused)"
            sx={{ mb: 2 }}
          />

          {localPreferences.quiet_hours_enabled && (
            <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
              <TextField
                label="Start Time"
                type="time"
                value={localPreferences.quiet_start_time || "22:00"}
                onChange={(e) =>
                  handlePreferenceChange("quiet_start_time", e.target.value)
                }
                size="small"
              />
              <Typography>to</Typography>
              <TextField
                label="End Time"
                type="time"
                value={localPreferences.quiet_end_time || "07:00"}
                onChange={(e) =>
                  handlePreferenceChange("quiet_end_time", e.target.value)
                }
                size="small"
              />
            </Box>
          )}

          <Alert severity="info" sx={{ mt: 2 }}>
            <strong>Critical notifications</strong> (like token expiry and
            margin calls) will override quiet hours settings
          </Alert>
        </CardContent>
      </Card>

      {/* Rate Limits */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Rate Limits
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Max emails per hour"
                type="number"
                value={localPreferences.max_emails_per_hour || 10}
                onChange={(e) =>
                  handlePreferenceChange(
                    "max_emails_per_hour",
                    parseInt(e.target.value)
                  )
                }
                inputProps={{ min: 1, max: 50 }}
                size="small"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Max SMS per day"
                type="number"
                value={localPreferences.max_sms_per_day || 5}
                onChange={(e) =>
                  handlePreferenceChange(
                    "max_sms_per_day",
                    parseInt(e.target.value)
                  )
                }
                inputProps={{ min: 1, max: 20 }}
                size="small"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Max push per hour"
                type="number"
                value={localPreferences.max_push_per_hour || 50}
                onChange={(e) =>
                  handlePreferenceChange(
                    "max_push_per_hour",
                    parseInt(e.target.value)
                  )
                }
                inputProps={{ min: 1, max: 100 }}
                size="small"
              />
            </Grid>
          </Grid>

          <Alert severity="warning" sx={{ mt: 2 }}>
            Rate limits help prevent notification spam but critical alerts can
            override these limits
          </Alert>
        </CardContent>
      </Card>
    </Stack>
  );
};

export default NotificationPreferences;
