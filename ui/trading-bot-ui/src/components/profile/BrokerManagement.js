// src/components/profile/BrokerManagement.jsx
import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Chip,
  Skeleton,
  Alert,
  Snackbar,
  InputAdornment,
  useTheme,
  alpha,
  Fade,
  Zoom,
  Tooltip,
  Avatar,
  Divider,
  Stack,
  Paper,
  LinearProgress,
  CircularProgress,
} from "@mui/material";
import {
  Add as AddIcon,
  Business as BusinessIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Close as CloseIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  AccountBalance as AccountBalanceIcon,
  Refresh as RefreshIcon,
  Security as SecurityIcon,
  CloudSync as SyncIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { brokerService } from "../../services/brokerService";

const BrokerManagement = () => {
  const theme = useTheme();
  const [brokers, setBrokers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddBroker, setShowAddBroker] = useState(false);
  const [newBroker, setNewBroker] = useState({
    broker_name: "",
    api_key: "",
    api_secret: "",
  });
  const [showApiSecret, setShowApiSecret] = useState({});
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success",
  });
  const [deleteConfirm, setDeleteConfirm] = useState({
    open: false,
    brokerId: null,
  });
  const [connectionTest, setConnectionTest] = useState({});

  const showSnackbar = useCallback((message, severity = "success") => {
    setSnackbar({ open: true, message, severity });
  }, []);

  const fetchBrokers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await brokerService.getBrokers();
      if (response.data) {
        setBrokers(response.data.brokers || []);
      }
    } catch (error) {
      console.error("Failed to fetch brokers:", error);
      showSnackbar("Failed to fetch brokers", "error");
    } finally {
      setLoading(false);
    }
  }, [showSnackbar]);

  useEffect(() => {
    fetchBrokers();
  }, [fetchBrokers]);

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const handleAddBroker = async () => {
    if (!newBroker.broker_name || !newBroker.api_key || !newBroker.api_secret) {
      showSnackbar("Please fill all fields", "error");
      return;
    }

    try {
      setConnectionTest({ [newBroker.broker_name]: "testing" });

      const response = await brokerService.addBroker({
        broker_name: newBroker.broker_name,
        credentials: {
          api_key: newBroker.api_key,
          api_secret: newBroker.api_secret,
        },
      });

      if (response.data) {
        setBrokers((prev) => [...prev, response.data]);
        setNewBroker({ broker_name: "", api_key: "", api_secret: "" });
        setShowAddBroker(false);
        setConnectionTest({});
        showSnackbar("Broker connected successfully!");
      }
    } catch (error) {
      console.error("Failed to add broker:", error);
      setConnectionTest({});
      showSnackbar("Failed to connect broker", "error");
    }
  };

  const handleDeleteBroker = async (brokerId) => {
    try {
      await brokerService.deleteBroker(brokerId);
      setBrokers((prev) => prev.filter((broker) => broker.id !== brokerId));
      setDeleteConfirm({ open: false, brokerId: null });
      showSnackbar("Broker removed successfully!");
    } catch (error) {
      console.error("Failed to delete broker:", error);
      showSnackbar("Failed to remove broker", "error");
    }
  };

  const handleToggleBrokerStatus = async (brokerId) => {
    try {
      const broker = brokers.find((b) => b.id === brokerId);
      const response = await brokerService.toggleBrokerStatus(brokerId, {
        is_active: !broker.is_active,
      });

      if (response.data) {
        setBrokers((prev) =>
          prev.map((b) =>
            b.id === brokerId ? { ...b, is_active: response.data.is_active } : b
          )
        );
        showSnackbar(
          `Broker ${
            response.data.is_active ? "activated" : "deactivated"
          } successfully!`
        );
      }
    } catch (error) {
      console.error("Failed to toggle broker status:", error);
      showSnackbar("Failed to update broker status", "error");
    }
  };

  // Improved broker configuration - removed hardcoded emojis and features
  const getBrokerConfig = (brokerName) => {
    const name = brokerName?.toLowerCase() || "";
    const configs = {
      zerodha: {
        color: "#FF6B35",
        description: "India's largest discount broker",
      },
      upstox: {
        color: "#7B68EE",
        description: "Next-gen trading platform",
      },
      "angel one": {
        color: "#1976D2",
        description: "Full-service stockbroker",
      },
      angelone: {
        color: "#1976D2",
        description: "Full-service stockbroker",
      },
      dhan: {
        color: "#FF9800",
        description: "Modern trading experience",
      },
      fyers: {
        color: "#4CAF50",
        description: "Technology-driven platform",
      },
      iifl: {
        color: "#FFD700",
        description: "Full-service financial services",
      },
      "5paisa": {
        color: "#E91E63",
        description: "Discount brokerage platform",
      },
      kotak: {
        color: "#D32F2F",
        description: "Premium banking & trading",
      },
      icici: {
        color: "#FF5722",
        description: "Bank-backed trading platform",
      },
    };

    const config = configs[name] || {
      color: theme.palette.primary.main,
      description: "Professional trading platform",
    };

    // Generate initials from broker name
    const getInitials = (name) => {
      if (!name) return "B";
      return name
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase())
        .join("")
        .substring(0, 2);
    };

    return {
      ...config,
      initials: getInitials(brokerName),
    };
  };

  const getConnectionStatus = (broker) => {
    const lastSync = broker.last_sync ? new Date(broker.last_sync) : null;
    const now = new Date();
    const timeDiff = lastSync ? (now - lastSync) / (1000 * 60) : null;

    if (!lastSync)
      return { status: "never", label: "Never synced", color: "error" };
    if (timeDiff < 5)
      return { status: "live", label: "Live", color: "success" };
    if (timeDiff < 30)
      return { status: "recent", label: "Recent", color: "success" };
    if (timeDiff < 60)
      return { status: "stale", label: "Stale", color: "warning" };
    return { status: "disconnected", label: "Disconnected", color: "error" };
  };

  // Safe currency formatting
  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return "₹0";
    }
    return `₹${Number(amount).toLocaleString("en-IN")}`;
  };

  // Safe date formatting
  const formatDate = (dateString) => {
    if (!dateString) return "Never";
    try {
      return new Date(dateString).toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (error) {
      return "Invalid date";
    }
  };

  if (loading) {
    return (
      <Box>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          mb={4}
        >
          <Skeleton variant="text" width={300} height={40} />
          <Skeleton
            variant="rectangular"
            width={150}
            height={40}
            sx={{ borderRadius: 2 }}
          />
        </Stack>
        <Grid container spacing={3}>
          {[1, 2, 3].map((i) => (
            <Grid item xs={12} sm={6} lg={4} key={i}>
              <Skeleton
                variant="rectangular"
                height={280}
                sx={{ borderRadius: 3 }}
              />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  const renderBrokerCard = (broker, index) => {
    const config = getBrokerConfig(broker.broker_name);
    const connectionStatus = getConnectionStatus(broker);

    return (
      <Grid item xs={12} sm={6} lg={4} key={broker.id}>
        <Zoom in={true} timeout={300 + index * 100}>
          <Card
            sx={{
              height: "100%",
              transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              background: `
                linear-gradient(135deg, 
                  ${alpha(theme.palette.background.paper, 0.9)} 0%, 
                  ${alpha(config.color, 0.02)} 100%
                )
              `,
              backdropFilter: "blur(20px)",
              position: "relative",
              overflow: "hidden",
              "&:hover": {
                transform: "translateY(-8px)",
                boxShadow: `0 20px 40px ${alpha(config.color, 0.15)}`,
                borderColor: alpha(config.color, 0.3),
              },
              "&::before": {
                content: '""',
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 3,
                background: `linear-gradient(90deg, ${config.color}, ${alpha(
                  config.color,
                  0.6
                )})`,
              },
            }}
            elevation={0}
          >
            <CardContent
              sx={{
                p: 3,
                height: "100%",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {/* Header */}
              <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="flex-start"
                mb={2}
              >
                <Stack direction="row" alignItems="center" spacing={2}>
                  <Avatar
                    sx={{
                      width: 56,
                      height: 56,
                      bgcolor: config.color,
                      color: "white",
                      fontSize: "1.2rem",
                      fontWeight: 700,
                      border: `2px solid ${alpha(config.color, 0.2)}`,
                    }}
                  >
                    {config.initials}
                  </Avatar>
                  <Box>
                    <Typography variant="h6" fontWeight={700}>
                      {broker.broker_name || "Unknown Broker"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {config.description}
                    </Typography>
                  </Box>
                </Stack>

                <Stack alignItems="flex-end" spacing={1}>
                  <Chip
                    icon={
                      broker.is_active ? <CheckCircleIcon /> : <CancelIcon />
                    }
                    label={broker.is_active ? "Active" : "Inactive"}
                    color={broker.is_active ? "success" : "default"}
                    size="small"
                    sx={{ fontWeight: 600 }}
                  />
                  <Chip
                    label={connectionStatus.label}
                    color={connectionStatus.color}
                    size="small"
                    sx={{ fontSize: "0.7rem", height: 20 }}
                  />
                </Stack>
              </Stack>

              {/* Balance Section */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  mb: 2,
                  borderRadius: 2,
                  bgcolor: alpha(config.color, 0.05),
                  border: `1px solid ${alpha(config.color, 0.1)}`,
                }}
              >
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                >
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Available Balance
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight={700}
                      color={config.color}
                    >
                      {formatCurrency(broker.balance)}
                    </Typography>
                  </Box>
                  <Avatar
                    sx={{
                      bgcolor: alpha(config.color, 0.1),
                      color: config.color,
                      width: 40,
                      height: 40,
                    }}
                  >
                    <AccountBalanceIcon />
                  </Avatar>
                </Stack>
              </Paper>

              {/* Account Details */}
              <Box sx={{ mb: 2, flex: 1 }}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mb: 1, display: "block" }}
                >
                  ACCOUNT DETAILS
                </Typography>
                <Stack spacing={1}>
                  {broker.account_id && (
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Account ID
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {broker.account_id}
                      </Typography>
                    </Stack>
                  )}
                  {broker.client_id && (
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        Client ID
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {broker.client_id}
                      </Typography>
                    </Stack>
                  )}
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Connected
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {formatDate(broker.created_at)}
                    </Typography>
                  </Stack>
                </Stack>
              </Box>

              {/* Connection Info */}
              <Box sx={{ mb: 2 }}>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                  mb={1}
                >
                  <Typography variant="caption" color="text.secondary">
                    Last Sync
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatDate(broker.last_sync)}
                  </Typography>
                </Stack>
                <LinearProgress
                  variant="determinate"
                  value={
                    connectionStatus.status === "live"
                      ? 100
                      : connectionStatus.status === "recent"
                      ? 75
                      : connectionStatus.status === "stale"
                      ? 50
                      : 0
                  }
                  sx={{
                    height: 4,
                    borderRadius: 2,
                    bgcolor: alpha(theme.palette.divider, 0.1),
                    "& .MuiLinearProgress-bar": {
                      bgcolor: config.color,
                      borderRadius: 2,
                    },
                  }}
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Actions */}
              <Stack direction="row" spacing={1}>
                <Button
                  fullWidth
                  variant={broker.is_active ? "outlined" : "contained"}
                  color={broker.is_active ? "inherit" : "primary"}
                  onClick={() => handleToggleBrokerStatus(broker.id)}
                  sx={{
                    borderRadius: 2,
                    fontWeight: 600,
                    flex: 1,
                  }}
                >
                  {broker.is_active ? "Deactivate" : "Activate"}
                </Button>

                <Tooltip title="Sync Data">
                  <IconButton
                    sx={{
                      color: config.color,
                      "&:hover": {
                        bgcolor: alpha(config.color, 0.1),
                      },
                    }}
                  >
                    <SyncIcon />
                  </IconButton>
                </Tooltip>

                <Tooltip title="Delete Broker">
                  <IconButton
                    color="error"
                    onClick={() =>
                      setDeleteConfirm({ open: true, brokerId: broker.id })
                    }
                    sx={{
                      "&:hover": {
                        bgcolor: alpha(theme.palette.error.main, 0.1),
                      },
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Tooltip>
              </Stack>
            </CardContent>
          </Card>
        </Zoom>
      </Grid>
    );
  };

  return (
    <Box>
      {/* Header */}
      <Paper
        elevation={0}
        sx={{
          p: 4,
          mb: 4,
          borderRadius: 3,
          background: `linear-gradient(135deg, 
            ${alpha(theme.palette.primary.main, 0.05)} 0%, 
            ${alpha(theme.palette.secondary.main, 0.05)} 100%
          )`,
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
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
                <BusinessIcon sx={{ fontSize: 24 }} />
              </Avatar>
              <Typography
                variant="h4"
                component="h2"
                sx={{
                  fontWeight: 800,
                  background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                  backgroundClip: "text",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                Broker Connections
              </Typography>
            </Stack>
            <Typography variant="body1" color="text.secondary">
              Manage your broker connections and trading accounts securely
            </Typography>
          </Box>

          <Stack direction="row" spacing={2}>
            <Tooltip title="Refresh All Data">
              <IconButton
                onClick={fetchBrokers}
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

            <Button
              variant="contained"
              size="large"
              startIcon={<AddIcon />}
              onClick={() => setShowAddBroker(true)}
              sx={{
                borderRadius: 3,
                px: 4,
                fontWeight: 700,
                boxShadow: `0 8px 24px ${alpha(
                  theme.palette.primary.main,
                  0.3
                )}`,
                "&:hover": {
                  boxShadow: `0 12px 32px ${alpha(
                    theme.palette.primary.main,
                    0.4
                  )}`,
                  transform: "translateY(-2px)",
                },
                transition: "all 0.3s ease",
              }}
            >
              Connect Broker
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Brokers Grid */}
      <Grid container spacing={3}>
        {brokers.map(renderBrokerCard)}

        {/* Empty State */}
        {brokers.length === 0 && !loading && (
          <Grid item xs={12}>
            <Fade in={true}>
              <Paper
                elevation={0}
                sx={{
                  textAlign: "center",
                  py: 8,
                  px: 4,
                  borderRadius: 4,
                  background: `linear-gradient(135deg, 
                    ${alpha(theme.palette.primary.main, 0.02)} 0%, 
                    ${alpha(theme.palette.secondary.main, 0.02)} 100%
                  )`,
                  border: `2px dashed ${alpha(
                    theme.palette.primary.main,
                    0.2
                  )}`,
                }}
              >
                <Avatar
                  sx={{
                    width: 100,
                    height: 100,
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    mx: "auto",
                    mb: 3,
                  }}
                >
                  <BusinessIcon sx={{ fontSize: 50, color: "primary.main" }} />
                </Avatar>

                <Typography variant="h4" fontWeight={700} gutterBottom>
                  No Brokers Connected
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ mb: 4, maxWidth: 500, mx: "auto" }}
                >
                  Connect your first broker to start automated trading and track
                  your portfolio performance across multiple platforms.
                </Typography>

                <Button
                  variant="contained"
                  size="large"
                  startIcon={<AddIcon />}
                  onClick={() => setShowAddBroker(true)}
                  sx={{
                    borderRadius: 3,
                    px: 5,
                    py: 1.5,
                    fontWeight: 700,
                    fontSize: "1.1rem",
                  }}
                >
                  Connect Your First Broker
                </Button>
              </Paper>
            </Fade>
          </Grid>
        )}
      </Grid>

      {/* Add Broker Dialog */}
      <Dialog
        open={showAddBroker}
        onClose={() => setShowAddBroker(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 4,
            background: alpha(theme.palette.background.paper, 0.95),
            backdropFilter: "blur(20px)",
          },
        }}
      >
        <DialogTitle>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
          >
            <Stack direction="row" alignItems="center" spacing={2}>
              <Avatar
                sx={{
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  color: "primary.main",
                }}
              >
                <AddIcon />
              </Avatar>
              <Typography variant="h5" fontWeight={700}>
                Connect New Broker
              </Typography>
            </Stack>
            <IconButton onClick={() => setShowAddBroker(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Stack>
        </DialogTitle>

        <DialogContent sx={{ px: 3, pb: 2 }}>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Select Broker</InputLabel>
              <Select
                value={newBroker.broker_name}
                onChange={(e) =>
                  setNewBroker({ ...newBroker, broker_name: e.target.value })
                }
                label="Select Broker"
              >
                <MenuItem value="">Choose a broker</MenuItem>
                {[
                  "Zerodha",
                  "Upstox",
                  "Dhan",
                  "Angel One",
                  "Fyers",
                  "IIFL",
                  "5paisa",
                  "Kotak",
                  "ICICI",
                ].map((name) => {
                  const config = getBrokerConfig(name);
                  return (
                    <MenuItem key={name} value={name}>
                      <Stack direction="row" alignItems="center" spacing={2}>
                        <Avatar
                          sx={{
                            width: 32,
                            height: 32,
                            fontSize: "0.8rem",
                            bgcolor: config.color,
                            color: "white",
                            fontWeight: 700,
                          }}
                        >
                          {config.initials}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" fontWeight={600}>
                            {name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {config.description}
                          </Typography>
                        </Box>
                      </Stack>
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="API Key"
              value={newBroker.api_key}
              onChange={(e) =>
                setNewBroker({ ...newBroker, api_key: e.target.value })
              }
              placeholder="Enter your API key"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SecurityIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              fullWidth
              label="API Secret"
              type={showApiSecret.new ? "text" : "password"}
              value={newBroker.api_secret}
              onChange={(e) =>
                setNewBroker({ ...newBroker, api_secret: e.target.value })
              }
              placeholder="Enter your API secret"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SecurityIcon color="action" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() =>
                        setShowApiSecret({
                          ...showApiSecret,
                          new: !showApiSecret.new,
                        })
                      }
                      edge="end"
                    >
                      {showApiSecret.new ? (
                        <VisibilityOffIcon />
                      ) : (
                        <VisibilityIcon />
                      )}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            {newBroker.broker_name && (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                <Typography variant="body2">
                  <strong>
                    How to get API credentials for {newBroker.broker_name}:
                  </strong>
                  <br />
                  Visit your broker's developer portal and create API
                  credentials. Make sure to enable trading permissions for
                  automated strategies.
                </Typography>
              </Alert>
            )}
          </Stack>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button
            onClick={() => setShowAddBroker(false)}
            sx={{ borderRadius: 2, px: 3 }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleAddBroker}
            disabled={connectionTest[newBroker.broker_name] === "testing"}
            startIcon={
              connectionTest[newBroker.broker_name] === "testing" ? (
                <CircularProgress size={16} />
              ) : (
                <AddIcon />
              )
            }
            sx={{ borderRadius: 2, fontWeight: 600, px: 4 }}
          >
            {connectionTest[newBroker.broker_name] === "testing"
              ? "Connecting..."
              : "Connect Broker"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirm.open}
        onClose={() => setDeleteConfirm({ open: false, brokerId: null })}
        maxWidth="xs"
        fullWidth
        PaperProps={{
          sx: { borderRadius: 3 },
        }}
      >
        <DialogTitle>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Avatar
              sx={{
                bgcolor: alpha(theme.palette.error.main, 0.1),
                color: "error.main",
              }}
            >
              <WarningIcon />
            </Avatar>
            <Typography variant="h6" fontWeight={600}>
              Confirm Deletion
            </Typography>
          </Stack>
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to remove this broker connection? This action
            cannot be undone and you'll lose access to this account's trading
            functionality.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 3, gap: 1 }}>
          <Button
            onClick={() => setDeleteConfirm({ open: false, brokerId: null })}
            sx={{ borderRadius: 2 }}
          >
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => handleDeleteBroker(deleteConfirm.brokerId)}
            sx={{ borderRadius: 2, fontWeight: 600 }}
          >
            Delete Broker
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default BrokerManagement;
