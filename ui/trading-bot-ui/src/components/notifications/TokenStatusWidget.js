import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  Alert,
  IconButton,
  Button,
  Tooltip,
  useTheme,
  alpha,
  Stack,
  Divider,
  CircularProgress,
} from "@mui/material";
import {
  Token as TokenIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as CheckIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  AccountBalance as BrokerIcon,
} from "@mui/icons-material";
import { useNotifications } from "../../context/NotificationContext";

const TokenStatusWidget = () => {
  const theme = useTheme();
  const { tokenStatus, fetchTokenStatus } = useNotifications();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTokenStatus();
  }, [fetchTokenStatus]);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await fetchTokenStatus();
    } finally {
      setLoading(false);
    }
  };

  if (!tokenStatus) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <CircularProgress size={20} />
            <Typography>Loading token status...</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const { summary, expired_tokens, critical_tokens, high_priority_tokens } = tokenStatus;
  const needsAttention = summary.needs_attention;

  const getStatusColor = (hours) => {
    if (hours <= 0) return theme.palette.error.main;
    if (hours <= 2) return theme.palette.error.main;
    if (hours <= 12) return theme.palette.warning.main;
    if (hours <= 48) return theme.palette.info.main;
    return theme.palette.success.main;
  };

  const getStatusIcon = (hours) => {
    if (hours <= 0) return <ErrorIcon color="error" />;
    if (hours <= 2) return <ErrorIcon color="error" />;
    if (hours <= 12) return <WarningIcon color="warning" />;
    return <CheckIcon color="success" />;
  };

  const getUrgencyLabel = (hours) => {
    if (hours <= 0) return "EXPIRED";
    if (hours <= 2) return "CRITICAL";
    if (hours <= 12) return "URGENT";
    if (hours <= 48) return "ATTENTION";
    return "OK";
  };

  const allPriorityTokens = [
    ...expired_tokens,
    ...critical_tokens,
    ...high_priority_tokens,
  ].slice(0, 5); // Show max 5 most urgent tokens

  return (
    <Card
      sx={{
        mb: 2,
        border: needsAttention ? `2px solid ${theme.palette.warning.main}` : "none",
        bgcolor: needsAttention
          ? alpha(theme.palette.warning.main, 0.02)
          : "background.paper",
      }}
    >
      <CardContent>
        {/* Header */}
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <TokenIcon color={needsAttention ? "warning" : "primary"} />
            <Typography variant="h6" fontWeight={600}>
              Broker Token Status
            </Typography>
            {needsAttention && (
              <Chip
                label={`${summary.total_expired + summary.total_expiring_soon} Need Attention`}
                color="warning"
                size="small"
                icon={<WarningIcon />}
              />
            )}
          </Box>
          
          <Tooltip title="Refresh token status">
            <IconButton onClick={handleRefresh} disabled={loading} size="small">
              <RefreshIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Summary Alert */}
        {needsAttention && (
          <Alert
            severity="warning"
            sx={{ mb: 2 }}
            action={
              <Button size="small" color="inherit">
                Fix Now
              </Button>
            }
          >
            {summary.total_expired > 0 && (
              <strong>{summary.total_expired} tokens have expired</strong>
            )}
            {summary.total_expired > 0 && summary.total_expiring_soon > 0 && " and "}
            {summary.total_expiring_soon > 0 && (
              <strong>{summary.total_expiring_soon} are expiring soon</strong>
            )}
            . Trading may be disrupted.
          </Alert>
        )}

        {/* No issues state */}
        {!needsAttention && allPriorityTokens.length === 0 && (
          <Box sx={{ textAlign: "center", py: 2 }}>
            <CheckIcon sx={{ fontSize: 48, color: "success.main", mb: 1 }} />
            <Typography variant="body1" color="success.main" fontWeight={600}>
              All tokens are healthy
            </Typography>
            <Typography variant="body2" color="text.secondary">
              No action required at this time
            </Typography>
          </Box>
        )}

        {/* Token List */}
        {allPriorityTokens.length > 0 && (
          <Stack spacing={1}>
            <Typography variant="subtitle2" color="text.secondary">
              Tokens Requiring Attention:
            </Typography>
            
            {allPriorityTokens.map((token, index) => (
              <Box key={index}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    p: 1.5,
                    borderRadius: 1,
                    bgcolor: alpha(getStatusColor(token.hours_remaining), 0.05),
                    border: `1px solid ${alpha(getStatusColor(token.hours_remaining), 0.2)}`,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    {getStatusIcon(token.hours_remaining)}
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        {token.broker_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {token.hours_remaining <= 0
                          ? "Expired"
                          : `${Math.ceil(token.hours_remaining)} hours remaining`}
                      </Typography>
                    </Box>
                  </Box>

                  <Chip
                    label={getUrgencyLabel(token.hours_remaining)}
                    size="small"
                    color={
                      token.hours_remaining <= 0 ? "error" :
                      token.hours_remaining <= 12 ? "warning" : "info"
                    }
                    sx={{ fontWeight: 600, fontSize: "0.7rem" }}
                  />
                </Box>

                {/* Progress bar for tokens expiring in <48h */}
                {token.hours_remaining > 0 && token.hours_remaining <= 48 && (
                  <LinearProgress
                    variant="determinate"
                    value={Math.max(0, Math.min(100, (token.hours_remaining / 48) * 100))}
                    color={
                      token.hours_remaining <= 2 ? "error" :
                      token.hours_remaining <= 12 ? "warning" : "info"
                    }
                    sx={{ 
                      mt: 0.5, 
                      height: 4, 
                      borderRadius: 2,
                      bgcolor: alpha(getStatusColor(token.hours_remaining), 0.1),
                    }}
                  />
                )}
              </Box>
            ))}
          </Stack>
        )}

        {/* Quick Actions */}
        {needsAttention && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Button
                startIcon={<BrokerIcon />}
                variant="outlined"
                size="small"
                onClick={() => window.open("/profile", "_blank")}
              >
                Manage Brokers
              </Button>
              <Button
                startIcon={<ScheduleIcon />}
                variant="text"
                size="small"
                color="info"
              >
                Set Reminders
              </Button>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default TokenStatusWidget;