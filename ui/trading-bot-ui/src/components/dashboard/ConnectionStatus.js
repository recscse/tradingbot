// components/dashboard/ConnectionStatus.jsx
import React, { useState, useEffect } from "react";
import { Box, Chip, Tooltip } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";

const ConnectionStatus = ({
  isConnected,
  connectionStatus,
  isStale,
  marketStats = {},
  lastUpdateTime,
  serverLatency = 0,
}) => {
  const [blinking, setBlinking] = useState(false);
  const [connectionTime, setConnectionTime] = useState(null);

  useEffect(() => {
    if (isConnected && !connectionTime) {
      setConnectionTime(new Date());
    } else if (!isConnected) {
      setConnectionTime(null);
    }
  }, [isConnected, connectionTime]);

  useEffect(() => {
    if (!isConnected) {
      const interval = setInterval(() => {
        setBlinking((prev) => !prev);
      }, 500);
      return () => clearInterval(interval);
    } else {
      setBlinking(false);
    }
  }, [isConnected]);

  const getStatusColor = () => {
    if (!isConnected) return bloombergColors.negative;
    if (isStale) return bloombergColors.warning;
    return bloombergColors.positive;
  };

  const getStatusText = () => {
    if (!isConnected) return "OFFLINE";
    if (isStale) return "STALE";
    return "LIVE";
  };

  const getStatusIcon = () => {
    if (!isConnected) return "🔴";
    if (isStale) return "🟡";
    return "🟢";
  };

  const getLatencyColor = () => {
    if (serverLatency < 50) return bloombergColors.positive;
    if (serverLatency < 200) return bloombergColors.warning;
    return bloombergColors.negative;
  };

  const formatUptime = () => {
    if (!connectionTime) return "00:00:00";
    const now = new Date();
    const diff = now - connectionTime;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    return `${hours.toString().padStart(2, "0")}:${minutes
      .toString()
      .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  };

  const getTotalStocks = () => {
    return (
      (marketStats.advancing || 0) +
      (marketStats.declining || 0) +
      (marketStats.unchanged || 0)
    );
  };

  const getAdvanceDeclineRatio = () => {
    const advancing = marketStats.advancing || 0;
    const declining = marketStats.declining || 1; // Avoid division by zero
    return (advancing / declining).toFixed(2);
  };

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 2,
        p: 1,
        backgroundColor: bloombergColors.background,
        borderRadius: 0.5,
        border: `1px solid ${bloombergColors.border}`,
      }}
    >
      {/* Market Breadth */}
      <Box
        sx={{
          display: "flex",
          gap: 1.5,
          fontSize: "0.8rem",
          alignItems: "center",
        }}
      >
        <Tooltip title="Advancing Stocks" arrow>
          <Box
            sx={{
              color: bloombergColors.positive,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              fontWeight: "bold",
            }}
          >
            📈 {(marketStats.advancing || 0).toLocaleString()}
          </Box>
        </Tooltip>

        <Tooltip title="Declining Stocks" arrow>
          <Box
            sx={{
              color: bloombergColors.negative,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              fontWeight: "bold",
            }}
          >
            📉 {(marketStats.declining || 0).toLocaleString()}
          </Box>
        </Tooltip>

        <Tooltip title="Unchanged Stocks" arrow>
          <Box
            sx={{
              color: bloombergColors.textSecondary,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              fontWeight: "bold",
            }}
          >
            ➖ {(marketStats.unchanged || 0).toLocaleString()}
          </Box>
        </Tooltip>

        {/* A/D Ratio */}
        <Box
          sx={{
            fontSize: "0.7rem",
            color: bloombergColors.accent,
            ml: 1,
          }}
        >
          A/D: {getAdvanceDeclineRatio()}
        </Box>
      </Box>

      {/* Separator */}
      <Box
        sx={{
          width: "1px",
          height: "20px",
          backgroundColor: bloombergColors.border,
        }}
      />

      {/* Connection Status */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Tooltip
          title={
            <Box>
              <Box>Status: {getStatusText()}</Box>
              <Box>Latency: {serverLatency}ms</Box>
              <Box>Uptime: {formatUptime()}</Box>
              <Box>Total Stocks: {getTotalStocks().toLocaleString()}</Box>
              {lastUpdateTime && (
                <Box>
                  Last Update: {new Date(lastUpdateTime).toLocaleTimeString()}
                </Box>
              )}
            </Box>
          }
          arrow
        >
          <Chip
            label={`${getStatusIcon()} ${getStatusText()}`}
            size="small"
            sx={{
              backgroundColor: getStatusColor(),
              color: bloombergColors.background,
              fontWeight: "bold",
              fontSize: "0.75rem",
              fontFamily: "inherit",
              opacity: blinking ? 0.5 : 1,
              transition: "opacity 0.3s ease",
            }}
          />
        </Tooltip>

        {/* Latency Indicator */}
        {isConnected && (
          <Chip
            label={`${serverLatency}ms`}
            size="small"
            sx={{
              backgroundColor: getLatencyColor(),
              color: bloombergColors.background,
              fontSize: "0.65rem",
              height: "20px",
              fontWeight: "bold",
            }}
          />
        )}

        {/* Uptime Counter */}
        {isConnected && (
          <Box
            sx={{
              fontSize: "0.65rem",
              color: bloombergColors.textSecondary,
              fontFamily: "monospace",
            }}
          >
            ⏱️ {formatUptime()}
          </Box>
        )}
      </Box>

      {/* Data Quality Indicator */}
      {isConnected && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <Box
            sx={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: isStale
                ? bloombergColors.warning
                : bloombergColors.positive,
              animation: isStale ? "none" : "pulse 2s infinite",
              "@keyframes pulse": {
                "0%": { opacity: 1 },
                "50%": { opacity: 0.5 },
                "100%": { opacity: 1 },
              },
            }}
          />
          <Box
            sx={{
              fontSize: "0.65rem",
              color: bloombergColors.textSecondary,
            }}
          >
            {isStale ? "STALE" : "LIVE"}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default ConnectionStatus;
