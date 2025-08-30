// src/components/profile/BrokerProfileCard.jsx
import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Chip,
  Grid,
  IconButton,
  Collapse,
  Alert,
  Skeleton,
  useTheme,
  alpha,
  Divider,
  Tooltip,
  LinearProgress,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  CheckCircle as VerifiedIcon,
} from "@mui/icons-material";
import brokerProfileService from "../../services/brokerProfileService";

const BrokerProfileCard = ({ brokerName, onError }) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);
  const [profile, setProfile] = useState(null);
  const [funds, setFunds] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // ✅ Wrap in useCallback to fix ESLint warning
  const loadBrokerData = useCallback(
    async (forceRefresh = false) => {
      if (!brokerName) return;

      try {
        setLoading(true);
        setError(null);

        // Load cached data first for better UX
        if (!forceRefresh) {
          const cachedProfile =
            brokerProfileService.getCachedProfile(brokerName);
          if (cachedProfile) {
            setProfile(brokerProfileService.formatProfileData(cachedProfile));
          }
        }

        // Fetch fresh data
        const [profileResponse, fundsResponse] = await Promise.allSettled([
          brokerProfileService.getBrokerProfile(brokerName),
          brokerProfileService.getBrokerFunds(brokerName),
        ]);

        if (profileResponse.status === "fulfilled") {
          const formattedProfile = brokerProfileService.formatProfileData(
            profileResponse.value
          );
          setProfile(formattedProfile);
          brokerProfileService.cacheProfile(brokerName, profileResponse.value);
        } else {
          console.error("Profile fetch failed:", profileResponse.reason);
        }

        if (fundsResponse.status === "fulfilled") {
          const formattedFunds = brokerProfileService.formatFundsData(
            fundsResponse.value
          );
          setFunds(formattedFunds);
        } else {
          console.error("Funds fetch failed:", fundsResponse.reason);
        }

        setLastUpdated(new Date().toLocaleTimeString());
      } catch (error) {
        const errorMessage = brokerProfileService.handleError(
          error,
          `Failed to load ${brokerName} data`
        );
        setError(errorMessage.message);
        if (onError) onError(errorMessage.message);
      } finally {
        setLoading(false);
      }
    },
    [brokerName, onError] // ✅ dependencies
  );

  useEffect(() => {
    if (brokerName) {
      loadBrokerData();
    }
  }, [brokerName, loadBrokerData]); // ✅ fixed deps

  const handleRefresh = () => {
    loadBrokerData(true);
  };

  const formatCurrency = (amount) => {
    if (!amount || amount === 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getBrokerIcon = (brokerName) => {
    const icons = {
      upstox: "📊",
      angel: "😇",
      dhan: "💰",
      zerodha: "🟢",
      fyers: "🚀",
    };
    return icons[brokerName?.toLowerCase()] || "🏦";
  };

  if (loading && !profile) {
    return (
      <Card>
        <CardHeader
          title={<Skeleton width="60%" />}
          action={<Skeleton variant="circular" width={40} height={40} />}
        />
        <CardContent>
          <Skeleton height={60} />
          <Box mt={2}>
            <Skeleton height={40} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      elevation={2}
      sx={{
        transition: "all 0.3s ease",
        "&:hover": {
          elevation: 4,
          transform: "translateY(-2px)",
        },
      }}
    >
      <CardHeader
        avatar={
          <Box
            sx={{
              fontSize: "1.5rem",
              width: 48,
              height: 48,
              borderRadius: "50%",
              background: `linear-gradient(45deg, ${alpha(
                theme.palette.primary.main,
                0.1
              )}, ${alpha(theme.palette.secondary.main, 0.1)})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {getBrokerIcon(brokerName)}
          </Box>
        }
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6" sx={{ textTransform: "capitalize" }}>
              {brokerName}
            </Typography>
            {profile?.isActive && (
              <Tooltip title="Account Active">
                <VerifiedIcon color="success" fontSize="small" />
              </Tooltip>
            )}
          </Box>
        }
        subheader={
          <Box>
            {profile ? (
              <Typography variant="body2" color="textSecondary">
                {profile.userName} • {profile.userType}
              </Typography>
            ) : error ? (
              <Typography variant="body2" color="error">
                {error}
              </Typography>
            ) : (
              "Loading..."
            )}
            {lastUpdated && (
              <Typography variant="caption" color="textSecondary">
                Last updated: {lastUpdated}
              </Typography>
            )}
          </Box>
        }
        action={
          <Box display="flex" alignItems="center">
            <Tooltip title="Refresh Data">
              <IconButton onClick={handleRefresh} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title={expanded ? "Show Less" : "Show More"}>
              <IconButton onClick={() => setExpanded(!expanded)}>
                {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Tooltip>
          </Box>
        }
      />

      <CardContent sx={{ pt: 0 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Quick Summary */}
        {funds && (
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6}>
              <Box textAlign="center">
                <Typography variant="h6" color="primary">
                  {formatCurrency(funds.equity.availableMargin)}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  Available Margin
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box textAlign="center">
                <Typography
                  variant="h6"
                  color={
                    funds.equity.usedMargin > 0
                      ? "warning.main"
                      : "textSecondary"
                  }
                >
                  {formatCurrency(funds.equity.usedMargin)}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  Used Margin
                </Typography>
              </Box>
            </Grid>
          </Grid>
        )}

        {/* Utilization Bar */}
        {funds && funds.equity.availableMargin > 0 && (
          <Box sx={{ mb: 2 }}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="caption">Margin Utilization</Typography>
              <Typography variant="caption" color="textSecondary">
                {funds.equity.utilization}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={Math.min(parseFloat(funds.equity.utilization), 100)}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: alpha(theme.palette.grey[400], 0.3),
                "& .MuiLinearProgress-bar": {
                  borderRadius: 4,
                  backgroundColor:
                    parseFloat(funds.equity.utilization) > 80
                      ? theme.palette.error.main
                      : parseFloat(funds.equity.utilization) > 50
                      ? theme.palette.warning.main
                      : theme.palette.success.main,
                },
              }}
            />
          </Box>
        )}

        {/* Expanded Details */}
        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Divider sx={{ mb: 2 }} />

          {/* Profile Details */}
          {profile && (
            <Box mb={3}>
              <Typography variant="subtitle2" gutterBottom>
                📋 Profile Details
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" color="textSecondary">
                    User ID
                  </Typography>
                  <Typography variant="body2">{profile.userId}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" color="textSecondary">
                    Email
                  </Typography>
                  <Typography variant="body2">{profile.email}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="caption" color="textSecondary">
                    Exchanges
                  </Typography>
                  <Box mt={0.5}>
                    {profile.exchanges.map((exchange) => (
                      <Chip
                        key={exchange}
                        label={exchange}
                        size="small"
                        sx={{ mr: 0.5, mb: 0.5 }}
                        color="primary"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="caption" color="textSecondary">
                    Order Types
                  </Typography>
                  <Box mt={0.5}>
                    {profile.orderTypes.map((orderType) => (
                      <Chip
                        key={orderType}
                        label={orderType}
                        size="small"
                        sx={{ mr: 0.5, mb: 0.5 }}
                        color="secondary"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                </Grid>
              </Grid>
            </Box>
          )}

          {/* Detailed Funds */}
          {funds && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                💰 Detailed Funds
              </Typography>

              {/* Equity Segment */}
              <Box mb={2}>
                <Typography variant="body2" color="primary" gutterBottom>
                  Equity Segment
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="textSecondary">
                      Payin Amount
                    </Typography>
                    <Typography variant="body2">
                      {formatCurrency(funds.equity.payinAmount)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="textSecondary">
                      SPAN Margin
                    </Typography>
                    <Typography variant="body2">
                      {formatCurrency(funds.equity.spanMargin)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="textSecondary">
                      Exposure Margin
                    </Typography>
                    <Typography variant="body2">
                      {formatCurrency(funds.equity.exposureMargin)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="textSecondary">
                      Adhoc Margin
                    </Typography>
                    <Typography variant="body2">
                      {formatCurrency(funds.equity.adhocMargin)}
                    </Typography>
                  </Grid>
                </Grid>
              </Box>

              {/* Commodity Segment */}
              {funds.commodity && funds.commodity.availableMargin > 0 && (
                <Box>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Commodity Segment
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="textSecondary">
                        Available Margin
                      </Typography>
                      <Typography variant="body2">
                        {formatCurrency(funds.commodity.availableMargin)}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="textSecondary">
                        Used Margin
                      </Typography>
                      <Typography variant="body2">
                        {formatCurrency(funds.commodity.usedMargin)}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              )}

              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="caption">
                  💡 Fund service may be unavailable from 12:00 AM to 5:30 AM
                  IST daily for maintenance.
                </Typography>
              </Alert>
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default BrokerProfileCard;
