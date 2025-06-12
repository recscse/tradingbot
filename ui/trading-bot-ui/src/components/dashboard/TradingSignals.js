import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Box,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Timeline,
  Refresh,
  NotificationsActive,
} from "@mui/icons-material";
import { useEnhancedMarket } from "../../context/EnhancedMarketProvider";

const TradingSignals = () => {
  const { tradingSignals, addNotification, loading } = useEnhancedMarket();
  const [signals, setSignals] = useState([]);

  useEffect(() => {
    setSignals(tradingSignals);
  }, [tradingSignals]);

  const getSignalColor = (signal) => {
    switch (signal.toLowerCase()) {
      case "buy":
        return "success";
      case "sell":
        return "error";
      case "hold":
        return "warning";
      default:
        return "default";
    }
  };

  const getSignalIcon = (signal) => {
    switch (signal.toLowerCase()) {
      case "buy":
        return <TrendingUp color="success" />;
      case "sell":
        return <TrendingDown color="error" />;
      case "hold":
        return <Timeline color="warning" />;
      default:
        return <NotificationsActive />;
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return "success";
    if (confidence >= 60) return "warning";
    return "error";
  };

  const handleRefresh = () => {
    // Trigger refresh of trading signals
    addNotification({
      type: "info",
      message: "Refreshing trading signals...",
      title: "Update",
    });
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <Card elevation={3}>
      <CardContent>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Typography variant="h6" component="div">
            Trading Signals
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={`${signals.length} Active`}
              color="primary"
              size="small"
            />
            <Tooltip title="Refresh signals">
              <IconButton size="small" onClick={handleRefresh}>
                <Refresh />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {loading && (
          <Box display="flex" justifyContent="center" py={2}>
            <CircularProgress size={24} />
          </Box>
        )}

        {!loading && signals.length === 0 && (
          <Alert severity="info">
            No trading signals available at the moment.
          </Alert>
        )}

        {!loading && signals.length > 0 && (
          <List dense>
            {signals.slice(0, 10).map((signal, index) => (
              <ListItem
                key={signal.id || index}
                divider={index < signals.length - 1}
                sx={{
                  borderLeft: `4px solid`,
                  borderLeftColor: getSignalColor(signal.action) + ".main",
                  mb: 1,
                  borderRadius: 1,
                  bgcolor: "background.paper",
                }}
              >
                <ListItemIcon>{getSignalIcon(signal.action)}</ListItemIcon>

                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="subtitle2">
                        {signal.symbol}
                      </Typography>
                      <Chip
                        label={signal.action?.toUpperCase()}
                        color={getSignalColor(signal.action)}
                        size="small"
                      />
                      <Chip
                        label={`${signal.confidence || 0}%`}
                        color={getConfidenceColor(signal.confidence || 0)}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="textSecondary">
                        {signal.reason || "AI-generated signal"}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {signal.timestamp
                          ? formatTime(signal.timestamp)
                          : "Just now"}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}

        <Box mt={2}>
          <Typography variant="caption" color="textSecondary">
            Signals are generated using AI analysis and should be used as
            guidance only.
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TradingSignals;
