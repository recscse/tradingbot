// components/dashboard/QuickStatsBar.jsx
import React from "react";
import { Box, Chip } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";

const QuickStatsBar = ({ marketData, marketSentiment, topMovers, sx }) => {
  const totalStocks = Object.keys(marketData || {}).length;
  const gainersCount = topMovers?.gainers?.length || 0;
  const losersCount = topMovers?.losers?.length || 0;
  const unchangedCount = totalStocks - gainersCount - losersCount;

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case "very_bullish":
      case "bullish":
        return bloombergColors.positive;
      case "very_bearish":
      case "bearish":
        return bloombergColors.negative;
      case "neutral":
        return bloombergColors.warning;
      default:
        return bloombergColors.textSecondary;
    }
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment) {
      case "very_bullish":
        return "🚀";
      case "bullish":
        return "📈";
      case "very_bearish":
        return "💥";
      case "bearish":
        return "📉";
      case "neutral":
        return "➖";
      default:
        return "💭";
    }
  };

  const currentTime = new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <Box
      sx={{
        ...sx,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        px: 3,
        py: 1,
        fontSize: "0.75rem",
        fontFamily: "inherit",
        backgroundColor: bloombergColors.background,
        borderBottom: `1px solid ${bloombergColors.border}`,
        minHeight: "40px",
      }}
    >
      <Box
        sx={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}
      >
        <Box sx={{ display: "flex", alignItems: "center" }}>
          📊 INSTRUMENTS:{" "}
          <Box
            component="span"
            sx={{
              color: bloombergColors.accent,
              fontWeight: "bold",
              ml: 0.5,
            }}
          >
            {totalStocks.toLocaleString()}
          </Box>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center" }}>
          📈 GAINERS:{" "}
          <Box
            component="span"
            sx={{
              color: bloombergColors.positive,
              fontWeight: "bold",
              ml: 0.5,
            }}
          >
            {gainersCount.toLocaleString()}
          </Box>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center" }}>
          📉 LOSERS:{" "}
          <Box
            component="span"
            sx={{
              color: bloombergColors.negative,
              fontWeight: "bold",
              ml: 0.5,
            }}
          >
            {losersCount.toLocaleString()}
          </Box>
        </Box>

        {unchangedCount > 0 && (
          <Box sx={{ display: "flex", alignItems: "center" }}>
            ➖ UNCHANGED:{" "}
            <Box
              component="span"
              sx={{
                color: bloombergColors.textSecondary,
                fontWeight: "bold",
                ml: 0.5,
              }}
            >
              {unchangedCount.toLocaleString()}
            </Box>
          </Box>
        )}

        <Box sx={{ display: "flex", alignItems: "center" }}>
          {getSentimentIcon(marketSentiment?.sentiment)} SENTIMENT:{" "}
          <Chip
            label={
              marketSentiment?.sentiment?.replace("_", " ")?.toUpperCase() ||
              "NEUTRAL"
            }
            size="small"
            sx={{
              ml: 0.5,
              backgroundColor: getSentimentColor(marketSentiment?.sentiment),
              color: bloombergColors.background,
              fontWeight: "bold",
              fontSize: "0.65rem",
              height: "20px",
            }}
          />
        </Box>

        {/* Market Status Indicator */}
        <Box sx={{ display: "flex", alignItems: "center" }}>
          🕐 STATUS:{" "}
          <Box
            component="span"
            sx={{
              color: bloombergColors.positive,
              fontWeight: "bold",
              ml: 0.5,
            }}
          >
            LIVE
          </Box>
        </Box>
      </Box>

      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          color: bloombergColors.textSecondary,
        }}
      >
        {/* Additional Stats */}
        {marketSentiment?.score && (
          <Box sx={{ fontSize: "0.7rem" }}>
            SCORE:{" "}
            <Box component="span" sx={{ color: bloombergColors.accent }}>
              {marketSentiment.score.toFixed(1)}
            </Box>
          </Box>
        )}

        <Box sx={{ fontSize: "0.7rem" }}>
          LAST UPDATE:{" "}
          <Box component="span" sx={{ color: bloombergColors.accent }}>
            {currentTime}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default QuickStatsBar;
