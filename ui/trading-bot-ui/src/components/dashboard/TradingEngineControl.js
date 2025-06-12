import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Switch,
  FormControlLabel,
  Alert,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
} from "@mui/material";
import { PlayArrow, Stop, Settings, Security } from "@mui/icons-material";
import { useEnhancedMarket } from "../../context/EnhancedMarketProvider";

const TradingEngineControl = () => {
  const { addNotification, connectionStatus } = useEnhancedMarket();
  const [engineStatus, setEngineStatus] = useState("stopped"); // 'stopped', 'starting', 'running', 'stopping'
  const [autoTrading, setAutoTrading] = useState(false);
  const [riskManagement, setRiskManagement] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState({
    maxPositions: 5,
    maxRiskPerTrade: 2,
    stopLossPercent: 3,
    takeProfitPercent: 5,
  });

  useEffect(() => {
    // Load saved settings from localStorage
    const savedSettings = localStorage.getItem("tradingEngineSettings");
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
  }, []);

  const handleStartEngine = async () => {
    if (connectionStatus !== "connected") {
      addNotification({
        type: "error",
        message: "Market data connection required to start trading engine",
        title: "Connection Error",
      });
      return;
    }

    setEngineStatus("starting");

    try {
      // Simulate API call to start trading engine
      await new Promise((resolve) => setTimeout(resolve, 2000));

      setEngineStatus("running");
      addNotification({
        type: "success",
        message: "Trading engine started successfully",
        title: "Engine Started",
      });
    } catch (error) {
      setEngineStatus("stopped");
      addNotification({
        type: "error",
        message: "Failed to start trading engine",
        title: "Engine Error",
      });
    }
  };

  const handleStopEngine = async () => {
    setEngineStatus("stopping");

    try {
      // Simulate API call to stop trading engine
      await new Promise((resolve) => setTimeout(resolve, 1500));

      setEngineStatus("stopped");
      setAutoTrading(false);
      addNotification({
        type: "info",
        message: "Trading engine stopped",
        title: "Engine Stopped",
      });
    } catch (error) {
      setEngineStatus("running");
      addNotification({
        type: "error",
        message: "Failed to stop trading engine",
        title: "Engine Error",
      });
    }
  };

  const handleAutoTradingToggle = (event) => {
    const enabled = event.target.checked;
    setAutoTrading(enabled);

    addNotification({
      type: enabled ? "warning" : "info",
      message: `Auto trading ${enabled ? "enabled" : "disabled"}`,
      title: "Auto Trading",
    });
  };

  const handleSaveSettings = () => {
    localStorage.setItem("tradingEngineSettings", JSON.stringify(settings));
    setSettingsOpen(false);

    addNotification({
      type: "success",
      message: "Settings saved successfully",
      title: "Settings Updated",
    });
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "running":
        return "success";
      case "starting":
      case "stopping":
        return "warning";
      case "stopped":
      default:
        return "error";
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case "running":
        return "Running";
      case "starting":
        return "Starting...";
      case "stopping":
        return "Stopping...";
      case "stopped":
      default:
        return "Stopped";
    }
  };

  const isLoading = engineStatus === "starting" || engineStatus === "stopping";
  const isRunning = engineStatus === "running";
  const canStart =
    engineStatus === "stopped" && connectionStatus === "connected";
  const canStop = engineStatus === "running";

  return (
    <>
      <Card elevation={3}>
        <CardContent>
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={3}
          >
            <Typography variant="h6" component="div">
              Trading Engine
            </Typography>
            <Box display="flex" alignItems="center" gap={1}>
              <Chip
                label={getStatusText(engineStatus)}
                color={getStatusColor(engineStatus)}
                icon={isLoading ? <CircularProgress size={16} /> : undefined}
              />
              <Button
                size="small"
                startIcon={<Settings />}
                onClick={() => setSettingsOpen(true)}
              >
                Settings
              </Button>
            </Box>
          </Box>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box display="flex" flexDirection="column" gap={2}>
                <Box display="flex" gap={2}>
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={
                      isLoading ? <CircularProgress size={16} /> : <PlayArrow />
                    }
                    onClick={handleStartEngine}
                    disabled={!canStart || isLoading}
                    fullWidth
                  >
                    Start Engine
                  </Button>

                  <Button
                    variant="contained"
                    color="error"
                    startIcon={
                      isLoading ? <CircularProgress size={16} /> : <Stop />
                    }
                    onClick={handleStopEngine}
                    disabled={!canStop || isLoading}
                    fullWidth
                  >
                    Stop Engine
                  </Button>
                </Box>

                <FormControlLabel
                  control={
                    <Switch
                      checked={autoTrading}
                      onChange={handleAutoTradingToggle}
                      disabled={!isRunning}
                    />
                  }
                  label="Auto Trading"
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={riskManagement}
                      onChange={(e) => setRiskManagement(e.target.checked)}
                    />
                  }
                  label="Risk Management"
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Current Settings
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Max Positions:</Typography>
                    <Typography variant="body2">
                      {settings.maxPositions}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Risk per Trade:</Typography>
                    <Typography variant="body2">
                      {settings.maxRiskPerTrade}%
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Stop Loss:</Typography>
                    <Typography variant="body2">
                      {settings.stopLossPercent}%
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Take Profit:</Typography>
                    <Typography variant="body2">
                      {settings.takeProfitPercent}%
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </Grid>
          </Grid>

          {!isRunning && connectionStatus !== "connected" && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Market data connection required to start trading engine
            </Alert>
          )}

          {isRunning && autoTrading && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Auto trading is enabled. Monitor positions carefully.
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Settings Dialog */}
      <Dialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <Settings />
            Trading Engine Settings
          </Box>
        </DialogTitle>

        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Max Positions"
                type="number"
                value={settings.maxPositions}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    maxPositions: parseInt(e.target.value) || 0,
                  }))
                }
                inputProps={{ min: 1, max: 20 }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Max Risk per Trade (%)"
                type="number"
                value={settings.maxRiskPerTrade}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    maxRiskPerTrade: parseFloat(e.target.value) || 0,
                  }))
                }
                inputProps={{ min: 0.1, max: 10, step: 0.1 }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Stop Loss (%)"
                type="number"
                value={settings.stopLossPercent}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    stopLossPercent: parseFloat(e.target.value) || 0,
                  }))
                }
                inputProps={{ min: 0.5, max: 20, step: 0.1 }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Take Profit (%)"
                type="number"
                value={settings.takeProfitPercent}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    takeProfitPercent: parseFloat(e.target.value) || 0,
                  }))
                }
                inputProps={{ min: 1, max: 50, step: 0.1 }}
              />
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveSettings}
            variant="contained"
            startIcon={<Security />}
          >
            Save Settings
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default TradingEngineControl;
