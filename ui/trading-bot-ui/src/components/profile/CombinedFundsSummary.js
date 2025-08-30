// src/components/profile/CombinedFundsSummary.jsx
import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Grid,
  CircularProgress,
  Alert,
  IconButton,
  useTheme,
  alpha,
  Chip,
  LinearProgress,
  Tooltip,
  Divider,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  AccountBalance as FundsIcon,
  TrendingUp as TrendingUpIcon,
  PieChart as PieChartIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import brokerProfileService from "../../services/brokerProfileService";

const CombinedFundsSummary = ({ onError }) => {
  const theme = useTheme();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // ✅ useCallback so function reference is stable
  const loadFundsSummary = useCallback(
    async (forceRefresh = false) => {
      try {
        setLoading(true);
        setError(null);

        const response = await brokerProfileService.getCombinedFundsSummary();
        const formattedSummary =
          brokerProfileService.formatCombinedSummary(response);
        setSummary(formattedSummary);
        setLastUpdated(new Date().toLocaleTimeString());
      } catch (error) {
        const errorMessage = brokerProfileService.handleError(
          error,
          "Failed to load funds summary"
        );
        setError(errorMessage.message);
        if (onError) onError(errorMessage.message);
      } finally {
        setLoading(false);
      }
    },
    [onError] // ✅ dependency included
  );

  useEffect(() => {
    loadFundsSummary();
  }, [loadFundsSummary]); // ✅ no ESLint warning now

  const formatCurrency = (amount) => {
    if (!amount || amount === 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getUtilizationColor = (utilization) => {
    if (utilization > 80) return theme.palette.error.main;
    if (utilization > 50) return theme.palette.warning.main;
    return theme.palette.success.main;
  };

  const getUtilizationSeverity = (utilization) => {
    if (utilization > 80) return "error";
    if (utilization > 50) return "warning";
    return "success";
  };

  return (
    <Card
      elevation={3}
      sx={{
        background: `linear-gradient(145deg, ${alpha(
          theme.palette.primary.main,
          0.05
        )}, ${alpha(theme.palette.secondary.main, 0.02)})`,
        border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
      }}
    >
      <CardHeader
        avatar={
          <Box
            sx={{
              background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
              borderRadius: "50%",
              p: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <FundsIcon sx={{ color: "white" }} />
          </Box>
        }
        title={
          <Typography variant="h6" fontWeight={600}>
            💰 Combined Funds Summary
          </Typography>
        }
        subheader={
          <Box>
            <Typography variant="body2" color="textSecondary">
              Across all active brokers
            </Typography>
            {lastUpdated && (
              <Typography variant="caption" color="textSecondary">
                Last updated: {lastUpdated}
              </Typography>
            )}
          </Box>
        }
        action={
          <Tooltip title="Refresh Data">
            <IconButton
              onClick={() => loadFundsSummary(true)}
              disabled={loading}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        }
      />

      <CardContent>
        {loading && (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {summary && !loading && (
          <>
            {/* Main Summary Cards */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={4}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    background: `linear-gradient(45deg, ${alpha(
                      theme.palette.success.main,
                      0.1
                    )}, ${alpha(theme.palette.success.main, 0.05)})`,
                    border: `1px solid ${alpha(
                      theme.palette.success.main,
                      0.3
                    )}`,
                  }}
                >
                  <Typography
                    variant="h4"
                    color="success.main"
                    fontWeight={700}
                  >
                    {formatCurrency(summary.totalAvailable)}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="textSecondary"
                    gutterBottom
                  >
                    Total Available Margin
                  </Typography>
                  <TrendingUpIcon color="success" fontSize="small" />
                </Box>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    background: `linear-gradient(45deg, ${alpha(
                      theme.palette.warning.main,
                      0.1
                    )}, ${alpha(theme.palette.warning.main, 0.05)})`,
                    border: `1px solid ${alpha(
                      theme.palette.warning.main,
                      0.3
                    )}`,
                  }}
                >
                  <Typography
                    variant="h4"
                    color="warning.main"
                    fontWeight={700}
                  >
                    {formatCurrency(summary.totalUsed)}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="textSecondary"
                    gutterBottom
                  >
                    Total Used Margin
                  </Typography>
                  <PieChartIcon color="warning" fontSize="small" />
                </Box>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    background: `linear-gradient(45deg, ${alpha(
                      getUtilizationColor(summary.utilization),
                      0.1
                    )}, ${alpha(
                      getUtilizationColor(summary.utilization),
                      0.05
                    )})`,
                    border: `1px solid ${alpha(
                      getUtilizationColor(summary.utilization),
                      0.3
                    )}`,
                  }}
                >
                  <Typography
                    variant="h4"
                    fontWeight={700}
                    sx={{ color: getUtilizationColor(summary.utilization) }}
                  >
                    {summary.utilization.toFixed(1)}%
                  </Typography>
                  <Typography
                    variant="body2"
                    color="textSecondary"
                    gutterBottom
                  >
                    Margin Utilization
                  </Typography>
                  {summary.utilization > 50 && (
                    <WarningIcon
                      fontSize="small"
                      sx={{ color: getUtilizationColor(summary.utilization) }}
                    />
                  )}
                </Box>
              </Grid>
            </Grid>

            {/* Utilization Progress Bar */}
            <Box sx={{ mb: 3 }}>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={1}
              >
                <Typography variant="subtitle2" fontWeight={600}>
                  Overall Utilization
                </Typography>
                <Chip
                  label={`${summary.utilization.toFixed(1)}%`}
                  color={getUtilizationSeverity(summary.utilization)}
                  size="small"
                  variant="outlined"
                />
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.min(summary.utilization, 100)}
                sx={{
                  height: 12,
                  borderRadius: 6,
                  backgroundColor: alpha(theme.palette.grey[400], 0.3),
                  "& .MuiLinearProgress-bar": {
                    borderRadius: 6,
                    backgroundColor: getUtilizationColor(summary.utilization),
                  },
                }}
              />
              <Box mt={1}>
                <Typography variant="caption" color="textSecondary">
                  Safe: 0-50% • Caution: 50-80% • High Risk: 80%+
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ mb: 3 }} />

            {/* Individual Broker Breakdown */}
            <Box>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                📊 Broker-wise Breakdown
              </Typography>

              {Object.entries(summary.brokerFunds).map(
                ([brokerName, brokerData]) => {
                  if (brokerData.error) {
                    return (
                      <Box key={brokerName} sx={{ mb: 2 }}>
                        <Alert severity="warning">
                          <strong style={{ textTransform: "capitalize" }}>
                            {brokerName}
                          </strong>
                          : {brokerData.error}
                        </Alert>
                      </Box>
                    );
                  }

                  const funds =
                    brokerProfileService.formatFundsData(brokerData);
                  if (!funds) return null;

                  return (
                    <Box key={brokerName} sx={{ mb: 2 }}>
                      <Box
                        sx={{
                          p: 2,
                          border: `1px solid ${alpha(
                            theme.palette.divider,
                            0.5
                          )}`,
                          borderRadius: 2,
                          background: alpha(
                            theme.palette.background.paper,
                            0.7
                          ),
                        }}
                      >
                        <Box
                          display="flex"
                          justifyContent="space-between"
                          alignItems="center"
                          mb={1}
                        >
                          <Typography
                            variant="subtitle2"
                            fontWeight={600}
                            sx={{ textTransform: "capitalize" }}
                          >
                            🏦 {brokerName}
                          </Typography>
                          <Chip
                            label={`${funds.equity.utilization}%`}
                            size="small"
                            color={
                              funds.equity.utilization > 80
                                ? "error"
                                : funds.equity.utilization > 50
                                ? "warning"
                                : "success"
                            }
                            variant="outlined"
                          />
                        </Box>

                        <Grid container spacing={2}>
                          <Grid item xs={4}>
                            <Typography variant="body2" fontWeight={500}>
                              {formatCurrency(funds.equity.availableMargin)}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              Available
                            </Typography>
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="body2" fontWeight={500}>
                              {formatCurrency(funds.equity.usedMargin)}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              Used
                            </Typography>
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="body2" fontWeight={500}>
                              {formatCurrency(funds.equity.payinAmount)}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              Payin
                            </Typography>
                          </Grid>
                        </Grid>

                        <LinearProgress
                          variant="determinate"
                          value={Math.min(
                            parseFloat(funds.equity.utilization),
                            100
                          )}
                          sx={{
                            mt: 1,
                            height: 4,
                            borderRadius: 2,
                            backgroundColor: alpha(
                              theme.palette.grey[400],
                              0.3
                            ),
                            "& .MuiLinearProgress-bar": {
                              borderRadius: 2,
                              backgroundColor:
                                funds.equity.utilization > 80
                                  ? theme.palette.error.main
                                  : funds.equity.utilization > 50
                                  ? theme.palette.warning.main
                                  : theme.palette.success.main,
                            },
                          }}
                        />
                      </Box>
                    </Box>
                  );
                }
              )}
            </Box>

            {/* Risk Alert */}
            {summary.utilization > 70 && (
              <Alert severity="warning" sx={{ mt: 3 }}>
                <Typography variant="body2">
                  ⚠️ <strong>High Margin Utilization:</strong> Consider reducing
                  positions or adding funds to maintain safe trading levels.
                </Typography>
              </Alert>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default CombinedFundsSummary;
