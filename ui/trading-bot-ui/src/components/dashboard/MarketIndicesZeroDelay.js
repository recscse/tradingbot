// components/dashboard/MarketIndicesZeroDelay.js
/**
 * 🚀 ZERO-DELAY Market Indices Component
 *
 * This component combines legacy indices metadata with ZERO-DELAY live price updates
 * to provide real-time indices price updates without any processing delays.
 */

import React, { useState, useMemo, useCallback } from "react";
import { Box, Grid2, Paper, Chip, Typography, Tooltip } from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  SignalWifi4Bar,
  SignalWifi0Bar,
} from "@mui/icons-material";
import { green, red, grey } from "@mui/material/colors";
import { bloombergColors } from "../../themes/bloombergColors";
import { withErrorBoundary } from "../common/ErrorBoundary";
import { useZeroDelayMarketData } from "../../hooks/useZeroDelayMarketData";

const MarketIndicesZeroDelay = ({
  indicesMetadata = [],
  isLoading = false,
  showPerformanceStats = true,
}) => {
  const [priceChanges, setPriceChanges] = useState({}); // Track price changes for animations
  const [updateCount, setUpdateCount] = useState(0);

  // 🚀 Connect to ZERO-DELAY streaming for live prices
  const {
    marketData: liveData,
    connectionStatus,
    latency,
    isConnected,
    lastUpdate,
  } = useZeroDelayMarketData({
    enableStats: showPerformanceStats,
    onDataReceived: useCallback((data) => {
      setUpdateCount((prev) => prev + 1);
    }, []),
  });

  // // Standard index symbols that we want to track
  // const standardIndices = useMemo(() => [
  //   'NIFTY 50', 'NIFTY', 'SENSEX', 'NIFTY BANK', 'BANKNIFTY',
  //   'NIFTY IT', 'NIFTY AUTO', 'NIFTY PHARMA', 'NIFTY METAL',
  //   'NIFTY FMCG', 'NIFTY REALTY', 'NIFTY ENERGY', 'NIFTY INFRA',
  //   'NIFTY PSU BANK', 'NIFTY PVT BANK', 'NIFTY FIN SERVICE',
  //   'NIFTY MID SELECT', 'NIFTY MIDCAP 50', 'NIFTY SMLCAP 50'
  // ], []);

  // Process indices data with live prices
  const processedIndices = useMemo(() => {
    if (!liveData || Object.keys(liveData).length === 0) {
      // Return metadata-only data if no live data available
      return indicesMetadata.map((index) => ({
        ...index,
        _source: "metadata",
        _live_data_available: false,
      }));
    }

    // Combine metadata with live data
    const processed = [];

    // First, process indices from metadata that have live data
    indicesMetadata.forEach((index) => {
      const symbol = index.symbol || index.name;
      const possibleKeys = [
        `NSE_INDEX|${symbol}`,
        `BSE_INDEX|${symbol}`,
        `INDEX|${symbol}`,
        symbol,
        index.instrument_key,
        index.instrument_token,
      ].filter(Boolean);

      let liveDataEntry = null;
      let matchedKey = null;

      for (const key of possibleKeys) {
        if (liveData[key]) {
          liveDataEntry = liveData[key];
          matchedKey = key;
          break;
        }
      }

      if (liveDataEntry) {
        // Track price changes for visual effects
        const currentPrice = parseFloat(
          liveDataEntry.lp || liveDataEntry.last_price || 0
        );
        const previousPrice =
          processed.find((p) => p.symbol === symbol)?.ltp || currentPrice;

        if (currentPrice !== previousPrice && currentPrice > 0) {
          setPriceChanges((prev) => ({
            ...prev,
            [symbol]: {
              direction: currentPrice > previousPrice ? "up" : "down",
              timestamp: Date.now(),
            },
          }));
        }

        processed.push({
          ...index,
          // Live price data
          ltp: currentPrice,
          last_price: currentPrice,
          open: parseFloat(
            liveDataEntry.op || liveDataEntry.open || index.open || 0
          ),
          high: parseFloat(
            liveDataEntry.h || liveDataEntry.high || index.high || 0
          ),
          low: parseFloat(
            liveDataEntry.l || liveDataEntry.low || index.low || 0
          ),

          // Calculate changes from live data
          change: liveDataEntry.op
            ? currentPrice - parseFloat(liveDataEntry.op)
            : index.change || 0,
          change_percent: liveDataEntry.op
            ? ((currentPrice - parseFloat(liveDataEntry.op)) /
                parseFloat(liveDataEntry.op)) *
              100
            : index.change_percent || 0,

          // Volume and other data
          volume: parseInt(liveDataEntry.v || liveDataEntry.volume || 0),

          // Metadata
          _matched_key: matchedKey,
          _live_data_available: true,
          _source: "zero_delay_live",
          _last_update: liveData._lastUpdate,
        });
      } else {
        // Keep metadata entry without live data
        processed.push({
          ...index,
          _live_data_available: false,
          _source: "metadata",
        });
      }
    });

    // Then, add any additional indices found in live data that weren't in metadata
    Object.keys(liveData).forEach((key) => {
      if (
        key.includes("INDEX") ||
        key.includes("NIFTY") ||
        key.includes("SENSEX")
      ) {
        const symbol = key.split("|").pop() || key;

        // Check if this index is already processed
        const alreadyProcessed = processed.some(
          (p) =>
            p.symbol === symbol ||
            p._matched_key === key ||
            p.instrument_key === key
        );

        if (!alreadyProcessed) {
          const liveDataEntry = liveData[key];
          const currentPrice = parseFloat(
            liveDataEntry.lp || liveDataEntry.last_price || 0
          );

          if (currentPrice > 0) {
            processed.push({
              symbol: symbol,
              name: symbol.replace(/_/g, " "),
              ltp: currentPrice,
              last_price: currentPrice,
              open: parseFloat(liveDataEntry.op || liveDataEntry.open || 0),
              high: parseFloat(liveDataEntry.h || liveDataEntry.high || 0),
              low: parseFloat(liveDataEntry.l || liveDataEntry.low || 0),
              change: liveDataEntry.op
                ? currentPrice - parseFloat(liveDataEntry.op)
                : 0,
              change_percent: liveDataEntry.op
                ? ((currentPrice - parseFloat(liveDataEntry.op)) /
                    parseFloat(liveDataEntry.op)) *
                  100
                : 0,
              volume: parseInt(liveDataEntry.v || liveDataEntry.volume || 0),
              _matched_key: key,
              _live_data_available: true,
              _source: "zero_delay_discovery",
              _last_update: liveData._lastUpdate,
            });
          }
        }
      }
    });

    // Sort: live data first, then by importance/name
    return processed.sort((a, b) => {
      if (a._live_data_available && !b._live_data_available) return -1;
      if (!a._live_data_available && b._live_data_available) return 1;

      // Prioritize major indices
      const majorIndicesOrder = [
        "NIFTY 50",
        "NIFTY",
        "SENSEX",
        "NIFTY BANK",
        "BANKNIFTY",
      ];
      const aIndex = majorIndicesOrder.indexOf(a.symbol || a.name);
      const bIndex = majorIndicesOrder.indexOf(b.symbol || b.name);

      if (aIndex !== -1 && bIndex === -1) return -1;
      if (aIndex === -1 && bIndex !== -1) return 1;
      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;

      return (a.name || a.symbol || "").localeCompare(b.name || b.symbol || "");
    });
  }, [indicesMetadata, liveData]);

  // Price change indicator component
  const PriceChangeIndicator = ({ index }) => {
    const change = priceChanges[index.symbol || index.name];
    const isRecent = change && Date.now() - change.timestamp < 3000; // 3 second highlight

    if (!isRecent) return null;

    return (
      <Box
        component="span"
        sx={{
          animation: "pulse 1.5s ease-in-out",
          "@keyframes pulse": {
            "0%": { opacity: 1, transform: "scale(1)" },
            "50%": { opacity: 0.7, transform: "scale(1.1)" },
            "100%": { opacity: 1, transform: "scale(1)" },
          },
        }}
      >
        {change.direction === "up" ? (
          <TrendingUp sx={{ color: green[500], fontSize: 16, ml: 0.5 }} />
        ) : (
          <TrendingDown sx={{ color: red[500], fontSize: 16, ml: 0.5 }} />
        )}
      </Box>
    );
  };

  // Format price with proper decimals
  const formatPrice = (price) => {
    return typeof price === "number"
      ? price.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : "N/A";
  };

  // // Format percentage with color
  // const formatPercentage = (percent) => {
  //   if (typeof percent !== 'number') return '0.00%';

  //   const value = percent.toFixed(2);
  //   const color = percent >= 0 ? green[600] : red[600];

  //   return (
  //     <Typography component="span" sx={{ color, fontWeight: 600 }}>
  //       {percent >= 0 ? '+' : ''}{value}%
  //     </Typography>
  //   );
  // };

  // Get index icon
  const getIndexIcon = (symbol) => {
    const symbolLower = (symbol || "").toLowerCase();
    if (symbolLower.includes("nifty") && symbolLower.includes("50"))
      return "🔥";
    if (symbolLower.includes("nifty") && symbolLower.includes("bank"))
      return "🏦";
    if (symbolLower.includes("sensex")) return "📈";
    if (symbolLower.includes("nifty") && symbolLower.includes("it"))
      return "💻";
    if (symbolLower.includes("pharma")) return "💊";
    if (symbolLower.includes("auto")) return "🚗";
    if (symbolLower.includes("metal")) return "⚒️";
    if (symbolLower.includes("realty")) return "🏠";
    if (symbolLower.includes("fmcg")) return "🛒";
    if (symbolLower.includes("energy")) return "⚡";
    if (symbolLower.includes("nifty")) return "📊";
    return "📈";
  };

  // Get market status
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
          <Typography sx={{ color: bloombergColors.textSecondary }}>
            Loading market indices...
          </Typography>
        </Box>
      </Paper>
    );
  }

  const liveIndicesCount = processedIndices.filter(
    (i) => i._live_data_available
  ).length;

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
      {/* Header with Market Status and Connection */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Box>
          <Typography
            sx={{
              fontSize: "1rem",
              fontWeight: "bold",
              color: bloombergColors.accent,
              letterSpacing: "1px",
            }}
          >
            🚀 MARKET INDICES {isConnected && "(ZERO-DELAY)"}
          </Typography>
          {lastUpdate && (
            <Typography variant="caption" color="textSecondary">
              Last update: {new Date(lastUpdate).toLocaleTimeString()}
              {updateCount > 0 && ` (${updateCount} updates)`}
            </Typography>
          )}
        </Box>

        <Box display="flex" alignItems="center" gap={1}>
          <Tooltip
            title={`Connection: ${connectionStatus} | Live: ${liveIndicesCount}/${processedIndices.length}`}
          >
            <Box display="flex" alignItems="center">
              {isConnected ? (
                <SignalWifi4Bar sx={{ color: green[500], fontSize: 20 }} />
              ) : (
                <SignalWifi0Bar sx={{ color: red[500], fontSize: 20 }} />
              )}
              {latency !== null && (
                <Typography
                  variant="caption"
                  sx={{ ml: 0.5, color: grey[600] }}
                >
                  {latency}ms
                </Typography>
              )}
            </Box>
          </Tooltip>

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
      </Box>

      {/* Performance Stats */}
      {showPerformanceStats && liveIndicesCount > 0 && (
        <Box display="flex" gap={1} mb={2} flexWrap="wrap">
          <Chip
            label={`${liveIndicesCount} Live`}
            color="success"
            size="small"
            variant="outlined"
          />
          <Chip
            label={`${processedIndices.length} Total`}
            variant="outlined"
            size="small"
          />
          {isConnected && (
            <Chip label="🚀 ZERO-DELAY" color="success" size="small" />
          )}
        </Box>
      )}

      <Grid2 container spacing={2}>
        {processedIndices.slice(0, 20).map((index, idx) => {
          const isPositive = (index.change_percent || 0) >= 0;
          const changePercent = index.change_percent || 0;
          // const absChangePercent = Math.abs(changePercent);

          return (
            <Grid2
              xs={12}
              sm={6}
              md={4}
              lg={2.4}
              key={index.symbol || index.name || idx}
            >
              <Box
                sx={{
                  backgroundColor: bloombergColors.background,
                  border: `1px solid ${
                    index._live_data_available
                      ? bloombergColors.accent
                      : bloombergColors.border
                  }`,
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
                    transform: "translateY(-2px)",
                  },
                }}
              >
                {/* Live indicator */}
                {index._live_data_available && (
                  <Box
                    sx={{
                      position: "absolute",
                      top: 4,
                      right: 4,
                      fontSize: "0.7rem",
                    }}
                  >
                    <Chip
                      label="LIVE"
                      color="success"
                      size="small"
                      sx={{ fontSize: "0.6rem", height: "16px" }}
                    />
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
                    {getIndexIcon(index.symbol || index.name)}
                  </span>
                  {(index.symbol || index.name || "").substring(0, 12)}
                  <PriceChangeIndicator index={index} />
                </Box>

                <Box
                  sx={{
                    fontSize: "1.1rem",
                    fontWeight: "bold",
                    color: index._live_data_available
                      ? bloombergColors.textPrimary
                      : bloombergColors.textSecondary,
                    mb: 0.5,
                  }}
                >
                  {formatPrice(index.ltp || index.last_price)}
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
                    {Math.abs(index.change || 0).toFixed(2)}
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
                {index._live_data_available && (
                  <Box
                    sx={{
                      mt: 1,
                      fontSize: "0.65rem",
                      color: bloombergColors.textSecondary,
                    }}
                  >
                    {index.high && index.low && (
                      <Box>
                        H: {formatPrice(index.high)} | L:{" "}
                        {formatPrice(index.low)}
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
            </Grid2>
          );
        })}
      </Grid2>

      {/* Footer */}
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
        <Box>
          {liveIndicesCount}/{processedIndices.length} Live Indices
          {isConnected && " • 🚀 ZERO-DELAY Active"}
        </Box>
        <Box>
          Updated:{" "}
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

export default withErrorBoundary(MarketIndicesZeroDelay, {
  fallbackMessage:
    "Unable to load market indices data. Please check your connection and try again.",
  height: "100%",
});
