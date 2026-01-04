// components/dashboard/TopMoversWidget.jsx
import React from "react";
import { Box, Paper, Grid2, Skeleton, Chip, Tooltip } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";
import { withErrorBoundary } from "../common/ErrorBoundary";

const TopMoversWidget = ({ data, isLoading, compact = false }) => {
  const { gainers: rawGainers = [], losers: rawLosers = [], summary = {} } = data || {};

  // Deduplicate gainers and losers by symbol
  const gainers = React.useMemo(() => {
    const seen = new Set();
    return (rawGainers || []).filter((s) => {
      if (!s?.symbol || seen.has(s.symbol)) return false;
      seen.add(s.symbol);
      return true;
    });
  }, [rawGainers]);

  const losers = React.useMemo(() => {
    const seen = new Set();
    return (rawLosers || []).filter((s) => {
      if (!s?.symbol || seen.has(s.symbol)) return false;
      seen.add(s.symbol);
      return true;
    });
  }, [rawLosers]);

  if (isLoading) {
    return (
      <Paper
        sx={{ backgroundColor: bloombergColors.cardBg, p: 2, height: "100%" }}
      >
        <Skeleton
          variant="text"
          width="60%"
          height={30}
          sx={{ bgcolor: bloombergColors.border }}
        />
        {Array.from(new Array(5)).map((_, index) => (
          <Box key={index} sx={{ mb: 1 }}>
            <Skeleton
              variant="text"
              width="100%"
              height={20}
              sx={{ bgcolor: bloombergColors.border }}
            />
          </Box>
        ))}
      </Paper>
    );
  }

  const formatVolume = (volume) => {
    if (!volume) return "N/A";
    if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
    if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  const getPerformanceIcon = (changePercent) => {
    const absChange = Math.abs(changePercent);
    if (absChange >= 10) return "🔥";
    if (absChange >= 5) return "⚡";
    if (absChange >= 2) return "📈";
    return "📊";
  };

  const getPerformanceLevel = (changePercent) => {
    const absChange = Math.abs(changePercent);
    if (absChange >= 10) return "EXTREME";
    if (absChange >= 5) return "HIGH";
    if (absChange >= 2) return "MODERATE";
    return "LOW";
  };

  const renderStock = (stock, isGainer) => {
    const changePercent = stock.change_percent || 0;
    const absChangePercent = Math.abs(changePercent);
    const performanceLevel = getPerformanceLevel(changePercent);

    return (
      <Tooltip
        key={stock.symbol}
        title={
          <Box>
            <Box sx={{ fontWeight: "bold" }}>{stock.symbol}</Box>
            <Box>Price: ₹{stock.last_price?.toFixed(2)}</Box>
            <Box>
              Change: {isGainer ? "+" : ""}
              {changePercent.toFixed(2)}%
            </Box>
            <Box>Volume: {formatVolume(stock.volume)}</Box>
            <Box>Performance: {performanceLevel}</Box>
            {stock.market_cap && (
              <Box>MCap: ₹{formatVolume(stock.market_cap)}</Box>
            )}
          </Box>
        }
        arrow
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            py: 0.5,
            px: 1,
            mb: 0.5,
            backgroundColor: bloombergColors.background,
            border: `1px solid ${bloombergColors.border}`,
            borderRadius: 0.5,
            borderLeft: `3px solid ${
              isGainer ? bloombergColors.positive : bloombergColors.negative
            }`,
            position: "relative",
            cursor: "pointer",
            transition: "all 0.3s ease",
            "&:hover": {
              borderColor: isGainer
                ? bloombergColors.positive
                : bloombergColors.negative,
              backgroundColor: isGainer
                ? `${bloombergColors.positive}15`
                : `${bloombergColors.negative}15`,
              transform: "translateX(2px)",
            },
          }}
        >
          {/* Performance indicator */}
          {absChangePercent >= 5 && (
            <Box
              sx={{
                position: "absolute",
                top: 2,
                right: 2,
                fontSize: "0.7rem",
              }}
            >
              {getPerformanceIcon(changePercent)}
            </Box>
          )}

          <Box sx={{ flex: 1 }}>
            <Box
              sx={{
                fontWeight: "bold",
                fontSize: "0.9rem",
                display: "flex",
                alignItems: "center",
                gap: 0.5,
              }}
            >
              <span style={{ fontSize: "0.7rem" }}>
                {getPerformanceIcon(changePercent)}
              </span>
              {stock.symbol}
            </Box>
            <Box
              sx={{ fontSize: "0.75rem", color: bloombergColors.textSecondary }}
            >
              ₹{stock.last_price?.toFixed(2)}
            </Box>
            {/* Additional info */}
            {stock.prev_close && (
              <Box
                sx={{
                  fontSize: "0.65rem",
                  color: bloombergColors.textSecondary,
                }}
              >
                Prev: ₹{stock.prev_close.toFixed(2)}
              </Box>
            )}
          </Box>

          <Box sx={{ textAlign: "right", minWidth: "80px" }}>
            <Chip
              label={`${isGainer ? "+" : ""}${changePercent.toFixed(2)}%`}
              size="small"
              sx={{
                backgroundColor: isGainer
                  ? bloombergColors.positive
                  : bloombergColors.negative,
                color: bloombergColors.background,
                fontWeight: "bold",
                fontSize: "0.7rem",
                height: "20px",
                mb: 0.5,
              }}
            />
            <Box
              sx={{
                fontSize: "0.65rem",
                color: bloombergColors.textSecondary,
                display: "flex",
                flexDirection: "column",
                gap: 0.2,
              }}
            >
              <Box>Vol: {formatVolume(stock.volume)}</Box>
              {stock.turnover && <Box>TO: {formatVolume(stock.turnover)}</Box>}
            </Box>
          </Box>
        </Box>
      </Tooltip>
    );
  };

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
          🚀 TOP MOVERS
        </Box>

        {/* Summary chips */}
        {!compact && (
          <Box sx={{ display: "flex", gap: 1 }}>
            <Chip
              label={`↗ ${gainers.length}`}
              size="small"
              sx={{
                backgroundColor: `${bloombergColors.positive}20`,
                color: bloombergColors.positive,
                fontSize: "0.7rem",
              }}
            />
            <Chip
              label={`↘ ${losers.length}`}
              size="small"
              sx={{
                backgroundColor: `${bloombergColors.negative}20`,
                color: bloombergColors.negative,
                fontSize: "0.7rem",
              }}
            />
          </Box>
        )}
      </Box>

      <Grid2
        container
        spacing={2}
        sx={{ height: compact ? "calc(100% - 50px)" : "calc(100% - 80px)" }}
      >
        <Grid2 xs={12} md={6}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.positive,
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            📈 GAINERS ({gainers.length})
          </Box>
          <Box sx={{ maxHeight: "300px", overflow: "auto", pr: 1 }}>
            {gainers
              .slice(0, compact ? 5 : 10)
              .map((stock) => renderStock(stock, true))}
          </Box>
        </Grid2>

        <Grid2 xs={12} md={6}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.negative,
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            📉 LOSERS ({losers.length})
          </Box>
          <Box sx={{ maxHeight: "300px", overflow: "auto", pr: 1 }}>
            {losers
              .slice(0, compact ? 5 : 10)
              .map((stock) => renderStock(stock, false))}
          </Box>
        </Grid2>
      </Grid2>

      {/* Summary Footer */}
      {!compact && summary && Object.keys(summary).length > 0 && (
        <Box
          sx={{
            mt: 2,
            pt: 1,
            borderTop: `1px solid ${bloombergColors.border}`,
            display: "flex",
            justifyContent: "space-around",
            fontSize: "0.75rem",
          }}
        >
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>Avg Gain</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.positive }}>
              +{summary.avg_gain?.toFixed(2) || "N/A"}%
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>Avg Loss</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.negative }}>
              {summary.avg_loss?.toFixed(2) || "N/A"}%
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Market Breadth
            </Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {gainers.length > losers.length
                ? "BULLISH"
                : losers.length > gainers.length
                ? "BEARISH"
                : "NEUTRAL"}
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default withErrorBoundary(TopMoversWidget, {
  fallbackMessage: "Unable to load top movers data. Market data may be temporarily unavailable.",
  height: "100%"
});
