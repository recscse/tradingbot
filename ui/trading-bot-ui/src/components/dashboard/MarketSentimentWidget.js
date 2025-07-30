// components/dashboard/MarketSentimentWidget.jsx
import React from "react";
import { Box, Paper, LinearProgress, Grid2, Chip } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";

const MarketSentimentWidget = ({ data, isLoading, compact = false }) => {
  if (isLoading) {
    return (
      <Paper
        sx={{ backgroundColor: bloombergColors.cardBg, p: 2, height: "100%" }}
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
            Loading sentiment...
          </Box>
        </Box>
      </Paper>
    );
  }

  const {
    sentiment = "neutral",
    confidence = 0,
    metrics = {},
    score = 0,
    trend = "stable",
  } = data;

  const getSentimentColor = () => {
    switch (sentiment) {
      case "very_bullish":
        return bloombergColors.positive;
      case "bullish":
        return "#66ff66";
      case "neutral":
        return bloombergColors.warning;
      case "bearish":
        return "#ff6666";
      case "very_bearish":
        return bloombergColors.negative;
      default:
        return bloombergColors.textPrimary;
    }
  };

  const getSentimentIcon = () => {
    switch (sentiment) {
      case "very_bullish":
        return "🚀";
      case "bullish":
        return "📈";
      case "neutral":
        return "➡️";
      case "bearish":
        return "📉";
      case "very_bearish":
        return "💥";
      default:
        return "❓";
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case "improving":
        return "⬆️";
      case "declining":
        return "⬇️";
      case "stable":
        return "➡️";
      default:
        return "➡️";
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case "improving":
        return bloombergColors.positive;
      case "declining":
        return bloombergColors.negative;
      case "stable":
        return bloombergColors.warning;
      default:
        return bloombergColors.textSecondary;
    }
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
          fontSize: "1rem",
          fontWeight: "bold",
          color: bloombergColors.accent,
          mb: 2,
          letterSpacing: "1px",
        }}
      >
        💭 MARKET SENTIMENT
      </Box>

      {/* Main Sentiment Display */}
      <Box
        sx={{
          textAlign: "center",
          mb: 3,
          p: 2,
          backgroundColor: bloombergColors.background,
          border: `2px solid ${getSentimentColor()}`,
          borderRadius: 1,
          position: "relative",
        }}
      >
        {/* Trend Indicator */}
        <Box
          sx={{
            position: "absolute",
            top: 8,
            right: 8,
            fontSize: "0.8rem",
          }}
        >
          <Chip
            label={`${getTrendIcon()} ${trend.toUpperCase()}`}
            size="small"
            sx={{
              backgroundColor: getTrendColor(),
              color: bloombergColors.background,
              fontSize: "0.6rem",
              height: "18px",
            }}
          />
        </Box>

        <Box sx={{ fontSize: "2rem", mb: 1 }}>{getSentimentIcon()}</Box>

        <Box
          sx={{
            fontSize: "1.2rem",
            fontWeight: "bold",
            color: getSentimentColor(),
            textTransform: "uppercase",
            letterSpacing: "1px",
            mb: 1,
          }}
        >
          {sentiment.replace("_", " ")}
        </Box>

        <Box
          sx={{
            color: bloombergColors.textSecondary,
            fontSize: "0.8rem",
            mb: 1,
          }}
        >
          Confidence: {confidence}%
        </Box>

        <LinearProgress
          variant="determinate"
          value={confidence}
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: bloombergColors.border,
            "& .MuiLinearProgress-bar": {
              backgroundColor: getSentimentColor(),
              borderRadius: 4,
            },
          }}
        />

        {/* Sentiment Score */}
        {score !== 0 && (
          <Box
            sx={{
              mt: 1,
              fontSize: "0.75rem",
              color: bloombergColors.textSecondary,
            }}
          >
            Score:{" "}
            <Box
              component="span"
              sx={{ color: bloombergColors.accent, fontWeight: "bold" }}
            >
              {score.toFixed(1)}
            </Box>
          </Box>
        )}
      </Box>

      {/* Metrics Grid */}
      <Grid2 container spacing={1} sx={{ mb: 2 }}>
        <Grid2 xs={6}>
          <Box
            sx={{
              textAlign: "center",
              p: 1,
              backgroundColor: bloombergColors.background,
              borderRadius: 0.5,
              border: `1px solid ${bloombergColors.border}`,
            }}
          >
            <Box
              sx={{
                fontSize: "1.2rem",
                fontWeight: "bold",
                color: bloombergColors.positive,
              }}
            >
              {(metrics.advancing || 0).toLocaleString()}
            </Box>
            <Box
              sx={{ fontSize: "0.7rem", color: bloombergColors.textSecondary }}
            >
              📈 ADVANCING
            </Box>
          </Box>
        </Grid2>

        <Grid2 xs={6}>
          <Box
            sx={{
              textAlign: "center",
              p: 1,
              backgroundColor: bloombergColors.background,
              borderRadius: 0.5,
              border: `1px solid ${bloombergColors.border}`,
            }}
          >
            <Box
              sx={{
                fontSize: "1.2rem",
                fontWeight: "bold",
                color: bloombergColors.negative,
              }}
            >
              {(metrics.declining || 0).toLocaleString()}
            </Box>
            <Box
              sx={{ fontSize: "0.7rem", color: bloombergColors.textSecondary }}
            >
              📉 DECLINING
            </Box>
          </Box>
        </Grid2>
      </Grid2>

      {/* Additional Metrics */}
      {!compact && (
        <Grid2 container spacing={1}>
          <Grid2 xs={4}>
            <Box sx={{ textAlign: "center" }}>
              <Box
                sx={{
                  fontSize: "1rem",
                  fontWeight: "bold",
                  color: bloombergColors.accent,
                }}
              >
                {metrics.unchanged || 0}
              </Box>
              <Box
                sx={{
                  fontSize: "0.65rem",
                  color: bloombergColors.textSecondary,
                }}
              >
                UNCHANGED
              </Box>
            </Box>
          </Grid2>

          <Grid2 xs={4}>
            <Box sx={{ textAlign: "center" }}>
              <Box
                sx={{
                  fontSize: "1rem",
                  fontWeight: "bold",
                  color: bloombergColors.info,
                }}
              >
                {metrics.volume_ratio?.toFixed(1) || "N/A"}x
              </Box>
              <Box
                sx={{
                  fontSize: "0.65rem",
                  color: bloombergColors.textSecondary,
                }}
              >
                VOL RATIO
              </Box>
            </Box>
          </Grid2>

          <Grid2 xs={4}>
            <Box sx={{ textAlign: "center" }}>
              <Box
                sx={{
                  fontSize: "1rem",
                  fontWeight: "bold",
                  color: getSentimentColor(),
                }}
              >
                {((metrics.advancing || 0) / (metrics.declining || 1)).toFixed(
                  1
                )}
              </Box>
              <Box
                sx={{
                  fontSize: "0.65rem",
                  color: bloombergColors.textSecondary,
                }}
              >
                A/D RATIO
              </Box>
            </Box>
          </Grid2>
        </Grid2>
      )}

      {/* Summary Footer */}
      {!compact && (
        <Box
          sx={{
            mt: 2,
            pt: 1,
            borderTop: `1px solid ${bloombergColors.border}`,
            textAlign: "center",
            fontSize: "0.7rem",
            color: bloombergColors.textSecondary,
          }}
        >
          Last Updated:{" "}
          {new Date().toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Box>
      )}
    </Paper>
  );
};

export default MarketSentimentWidget;
