// components/dashboard/MarketIndices.jsx
import React from "react";
import { Box, Grid2, Paper, Chip } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";
import { withErrorBoundary } from "../common/ErrorBoundary";

const MarketIndices = ({ marketData, symbols, isLoading = false }) => {
  const getIndexData = (symbol) => {
    const keys = Object.keys(marketData || {});
    const indexKey = keys.find(
      (key) => key.includes(`INDEX|${symbol}`) || key.includes(symbol)
    );
    return indexKey ? marketData[indexKey] : null;
  };

  const formatPrice = (price) => {
    return typeof price === "number"
      ? price.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : "N/A";
  };

  const getIndexIcon = (symbol) => {
    const iconMap = {
      NIFTY: "🔥",
      SENSEX: "📈",
      BANKNIFTY: "🏦",
      NIFTYIT: "💻",
      NIFTYPHARMA: "💊",
      NIFTYAUTO: "🚗",
      NIFTYMETAL: "⚒️",
      NIFTYREALTY: "🏠",
      NIFTYFMCG: "🛒",
      NIFTYENERGY: "⚡",
    };
    return iconMap[symbol] || "📊";
  };

  const getMarketStatus = () => {
    const now = new Date();
    const currentTime = now.getHours() * 100 + now.getMinutes();
    const marketOpen = 915; // 9:15 AM
    const marketClose = 1530; // 3:30 PM

    if (currentTime >= marketOpen && currentTime <= marketClose) {
      return { status: "OPEN", color: bloombergColors.positive };
    } else if (currentTime < marketOpen) {
      return { status: "PRE-MARKET", color: bloombergColors.warning };
    } else {
      return { status: "CLOSED", color: bloombergColors.negative };
    }
  };

  const marketStatus = getMarketStatus();

  if (isLoading) {
    return (
      <Paper
        elevation={0}
        sx={{
          backgroundColor: bloombergColors.cardBg,
          border: `1px solid ${bloombergColors.border}`,
          borderRadius: 1,
          p: 2,
          height: "100%",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
          }}
        >
          <Box sx={{ color: bloombergColors.textSecondary }}>
            Loading market indices...
          </Box>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper
      elevation={0}
      sx={{
        backgroundColor: bloombergColors.cardBg,
        border: `1px solid ${bloombergColors.border}`,
        borderRadius: 1,
        p: 2,
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Header with Market Status */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Box
          sx={{
            fontSize: "1rem",
            fontWeight: "bold",
            color: bloombergColors.accent,
            letterSpacing: "1px",
          }}
        >
          📊 MARKET INDICES
        </Box>

        <Chip
          label={marketStatus.status}
          size="small"
          sx={{
            backgroundColor: marketStatus.color,
            color: bloombergColors.background,
            fontWeight: "bold",
            fontSize: "0.7rem",
            height: "20px",
          }}
        />
      </Box>

      <Grid2 container spacing={2}>
        {symbols?.map((symbol) => {
          const data = getIndexData(symbol);
          const isPositive = (data?.change_percent || 0) >= 0;
          const changePercent = data?.change_percent || 0;
          const absChangePercent = Math.abs(changePercent);

          // Determine intensity based on change percentage
          const getIntensityColor = (percent) => {
            const intensity = Math.min(Math.abs(percent) / 2, 1); // Scale to 0-1
            if (isPositive) {
              return `rgba(0, 255, 0, ${0.1 + intensity * 0.2})`;
            } else {
              return `rgba(255, 51, 51, ${0.1 + intensity * 0.2})`;
            }
          };

          return (
            <Grid2 xs={12} sm={6} md={4} lg={2.4} key={symbol}>
              <Box
                sx={{
                  backgroundColor: bloombergColors.background,
                  border: `1px solid ${bloombergColors.border}`,
                  borderLeft: `4px solid ${
                    isPositive
                      ? bloombergColors.positive
                      : bloombergColors.negative
                  }`,
                  p: 1.5,
                  borderRadius: 1,
                  transition: "all 0.3s ease",
                  position: "relative",
                  minHeight: "100px",
                  "&:hover": {
                    borderColor: bloombergColors.accent,
                    boxShadow: `0 0 15px ${bloombergColors.accent}40`,
                    backgroundColor: getIntensityColor(changePercent),
                    transform: "translateY(-2px)",
                  },
                }}
              >
                {/* Volatility Indicator */}
                {absChangePercent > 2 && (
                  <Box
                    sx={{
                      position: "absolute",
                      top: 4,
                      right: 4,
                      fontSize: "0.7rem",
                    }}
                  >
                    {absChangePercent > 5 ? "🔥" : "⚡"}
                  </Box>
                )}

                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    fontSize: "0.9rem",
                    fontWeight: "bold",
                    color: bloombergColors.accent,
                    mb: 0.5,
                  }}
                >
                  <span style={{ fontSize: "0.8rem" }}>
                    {getIndexIcon(symbol)}
                  </span>
                  {symbol}
                </Box>

                <Box
                  sx={{
                    fontSize: "1.1rem",
                    fontWeight: "bold",
                    color: bloombergColors.textPrimary,
                    mb: 0.5,
                  }}
                >
                  {formatPrice(data?.ltp)}
                </Box>

                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Box
                    sx={{
                      fontSize: "0.8rem",
                      color: isPositive
                        ? bloombergColors.positive
                        : bloombergColors.negative,
                      fontWeight: "bold",
                    }}
                  >
                    {isPositive ? "▲" : "▼"}{" "}
                    {Math.abs(data?.change || 0).toFixed(2)}
                  </Box>

                  <Chip
                    label={`${isPositive ? "+" : ""}${changePercent.toFixed(
                      2
                    )}%`}
                    size="small"
                    sx={{
                      backgroundColor: isPositive
                        ? bloombergColors.positive
                        : bloombergColors.negative,
                      color: bloombergColors.background,
                      fontSize: "0.65rem",
                      fontWeight: "bold",
                      height: "18px",
                    }}
                  />
                </Box>

                {/* Additional Data */}
                {data && (
                  <Box
                    sx={{
                      mt: 1,
                      fontSize: "0.65rem",
                      color: bloombergColors.textSecondary,
                    }}
                  >
                    {data.high && data.low && (
                      <Box>
                        H: {formatPrice(data.high)} | L: {formatPrice(data.low)}
                      </Box>
                    )}
                    {data.volume && (
                      <Box sx={{ mt: 0.5 }}>
                        Vol: {(data.volume / 1000000).toFixed(1)}M
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
            </Grid2>
          );
        })}
      </Grid2>

      {/* Summary Footer */}
      <Box
        sx={{
          mt: 2,
          pt: 1,
          borderTop: `1px solid ${bloombergColors.border}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "0.7rem",
          color: bloombergColors.textSecondary,
        }}
      >
        <Box>{symbols?.length || 0} Indices Tracked</Box>
        <Box>
          Last Updated:{" "}
          {new Date().toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Box>
      </Box>
    </Paper>
  );
};

export default withErrorBoundary(MarketIndices, {
  fallbackMessage: "Unable to load market indices data. Please check your connection and try again.",
  height: "100%"
});
