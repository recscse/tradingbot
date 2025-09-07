// components/dashboard/BreakoutAnalysisWidget.jsx
import React, { useState } from "react";
import { bloombergColors } from "../../themes/bloombergColors";
import { Paper, Box, Chip, Tooltip, Button, Typography } from "@mui/material";
import { withErrorBoundary } from "../common/ErrorBoundary";

const BreakoutAnalysisWidget = ({ data, isLoading, compact = false }) => {
  const [selectedType, setSelectedType] = useState("all"); // "all", "breakout", "breakdown"
  const [selectedQuality, setSelectedQuality] = useState("all"); // "all", "weak", "moderate", "strong", "very_strong"

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
            Loading breakout analysis...
          </Box>
        </Box>
      </Paper>
    );
  }

  // FIXED: Backend sends breakouts and breakdowns arrays
  const { breakouts = [], breakdowns = [], summary = {} } = data;

  // Combine and filter breakout/breakdown signals
  const allSignals = [
    ...breakouts.map((b) => ({ ...b, breakout_type: "breakout" })),
    ...breakdowns.map((b) => ({ ...b, breakout_type: "breakdown" })),
  ];

  // Apply filters
  const filteredSignals = allSignals
    .filter((signal) => {
      // Type filter
      if (selectedType !== "all" && signal.breakout_type !== selectedType) {
        return false;
      }

      // Quality filter
      if (
        selectedQuality !== "all" &&
        signal.breakout_quality !== selectedQuality
      ) {
        return false;
      }

      return true;
    })
    .sort((a, b) => {
      // Sort by timestamp (newest first)
      return new Date(b.timestamp) - new Date(a.timestamp);
    });

  // Format volume for display
  const formatVolume = (volume) => {
    if (!volume) return "N/A";
    if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
    if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  // Get breakout quality color
  const getQualityColor = (quality) => {
    switch (quality) {
      case "very_strong":
        return bloombergColors.accent;
      case "strong":
        return bloombergColors.positive;
      case "moderate":
        return bloombergColors.warning;
      case "weak":
        return bloombergColors.textSecondary;
      default:
        return bloombergColors.textSecondary;
    }
  };

  // Get breakout strength icon
  const getBreakoutIcon = (strength, type) => {
    const isBreakout = type === "breakout";
    if (strength >= 3.0) return isBreakout ? "🚀" : "💥";
    if (strength >= 2.0) return isBreakout ? "⚡" : "⚠️";
    if (strength >= 1.0) return isBreakout ? "📈" : "📉";
    return isBreakout ? "↗️" : "↘️";
  };

  // Calculate time ago
  const getTimeAgo = (timestamp) => {
    if (!timestamp) return "N/A";
    const now = new Date();
    const time = new Date(timestamp);
    const diffInMinutes = Math.floor((now - time) / (1000 * 60));

    if (diffInMinutes < 1) return "Just now";
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    const hours = Math.floor(diffInMinutes / 60);
    if (hours < 24) return `${hours}h ${diffInMinutes % 60}m ago`;
    return time.toLocaleDateString();
  };

  // Render individual breakout signal
  const renderBreakoutSignal = (signal) => {
    const isBreakout = signal.breakout_type === "breakout";
    const strength = signal.breakout_strength || 0;
    const quality = signal.breakout_quality || "weak";
    const confidence = signal.confidence_score || 0;
    const timeAgo = getTimeAgo(signal.timestamp);

    // Use direct breakout time from service if available, fallback to parsing timestamp
    const displayTime =
      signal.breakout_time ||
      (signal.timestamp
        ? new Date(signal.timestamp).toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })
        : "N/A");

    // Enhanced date display
    const displayDate =
      signal.breakout_date ||
      (signal.timestamp
        ? new Date(signal.timestamp).toLocaleDateString("en-US", {
            month: "short",
            day: "2-digit",
          })
        : "N/A");

    return (
      <Tooltip
        key={`${signal.symbol}-${signal.timestamp}`}
        title={
          <Box>
            <Box sx={{ fontWeight: "bold", fontSize: "1rem", mb: 1 }}>
              {signal.symbol}
            </Box>
            <Box sx={{ color: "#FFD700", fontWeight: "bold", mb: 1 }}>
              🕒 {displayTime} on {displayDate}
            </Box>
            <Box>Type: {signal.breakout_type.toUpperCase()}</Box>
            <Box>Price: ₹{signal.current_price?.toFixed(2)}</Box>
            {isBreakout ? (
              <Box>Resistance: ₹{signal.resistance_level?.toFixed(2)}</Box>
            ) : (
              <Box>Support: ₹{signal.support_level?.toFixed(2)}</Box>
            )}
            <Box>Strength: {strength.toFixed(2)}%</Box>
            <Box>
              Volume: {formatVolume(signal.volume)} (
              {signal.volume_ratio?.toFixed(1)}x avg)
            </Box>
            <Box>Quality: {quality.toUpperCase()}</Box>
            <Box>Confidence: {(confidence * 100).toFixed(0)}%</Box>
            <Box>Momentum: {signal.price_momentum?.toFixed(2)}%</Box>
            <Box>Time since level: {signal.time_since_level || "N/A"}min</Box>
            <Box>Sector: {signal.sector || "N/A"}</Box>
            <Box>Market Cap: {signal.market_cap || "N/A"}</Box>
            <Box sx={{ color: "#B0B0B0", fontSize: "0.85rem", mt: 1 }}>
              Detected {timeAgo}
            </Box>
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
              isBreakout ? bloombergColors.positive : bloombergColors.negative
            }`,
            position: "relative",
            cursor: "pointer",
            transition: "all 0.3s ease",
            "&:hover": {
              borderColor: isBreakout
                ? bloombergColors.positive
                : bloombergColors.negative,
              backgroundColor: isBreakout
                ? `${bloombergColors.positive}15`
                : `${bloombergColors.negative}15`,
              transform: "translateX(2px)",
            },
          }}
        >
          {/* Quality indicator */}
          {strength >= 2.0 && (
            <Box
              sx={{
                position: "absolute",
                top: 2,
                right: 2,
                fontSize: "0.7rem",
              }}
            >
              {getBreakoutIcon(strength, signal.breakout_type)}
            </Box>
          )}

          {/* Timestamp indicator for recent breakouts */}
          {timeAgo && timeAgo.includes("min") && parseInt(timeAgo) <= 15 && (
            <Box
              sx={{
                position: "absolute",
                top: 2,
                left: 2,
                fontSize: "0.6rem",
                backgroundColor: `${bloombergColors.accent}80`,
                color: bloombergColors.background,
                px: 0.5,
                borderRadius: 0.5,
                fontWeight: "bold",
              }}
            >
              🔥 FRESH
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
                {getBreakoutIcon(strength, signal.breakout_type)}
              </span>
              {signal.symbol}
            </Box>
            <Box
              sx={{ fontSize: "0.75rem", color: bloombergColors.textSecondary }}
            >
              ₹{signal.current_price?.toFixed(2)} |
              {isBreakout
                ? ` R: ₹${signal.resistance_level?.toFixed(2)}`
                : ` S: ₹${signal.support_level?.toFixed(2)}`}
            </Box>
            <Box
              sx={{
                fontSize: "0.65rem",
                color: bloombergColors.textSecondary,
              }}
            >
              🕒 {displayTime} | {timeAgo} | Vol: {formatVolume(signal.volume)}
            </Box>
            {displayDate !== "N/A" && (
              <Box
                sx={{
                  fontSize: "0.6rem",
                  color: bloombergColors.accent,
                  fontWeight: "bold",
                }}
              >
                📅 {displayDate}
              </Box>
            )}
          </Box>

          <Box sx={{ textAlign: "right", minWidth: "80px" }}>
            <Chip
              label={`${strength >= 0 ? "+" : ""}${strength.toFixed(1)}%`}
              size="small"
              sx={{
                backgroundColor: isBreakout
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
                color: getQualityColor(quality),
                fontWeight: "bold",
                textTransform: "uppercase",
              }}
            >
              {quality.replace("_", " ")}
            </Box>
            <Box
              sx={{
                fontSize: "0.6rem",
                color: bloombergColors.textSecondary,
              }}
            >
              {(confidence * 100).toFixed(0)}% conf
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
          ⚡ BREAKOUT ANALYSIS
        </Box>

        {/* Live indicator */}
        <Chip
          label="REAL-TIME"
          size="small"
          sx={{
            backgroundColor: `${bloombergColors.accent}20`,
            color: bloombergColors.accent,
            fontSize: "0.7rem",
            fontWeight: "bold",
            animation: "pulse 2s infinite",
            "@keyframes pulse": {
              "0%, 100%": { opacity: 1 },
              "50%": { opacity: 0.5 },
            },
          }}
        />
      </Box>

      {/* Filter Controls */}
      {!compact && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: "flex", gap: 1, mb: 1, flexWrap: "wrap" }}>
            <Typography
              variant="caption"
              sx={{
                color: bloombergColors.textSecondary,
                alignSelf: "center",
                minWidth: "40px",
              }}
            >
              Type:
            </Typography>
            {["all", "breakout", "breakdown"].map((type) => (
              <Button
                key={type}
                size="small"
                variant={selectedType === type ? "contained" : "outlined"}
                onClick={() => setSelectedType(type)}
                sx={{
                  fontSize: "0.7rem",
                  minWidth: "60px",
                  height: "24px",
                  borderColor: bloombergColors.border,
                  color:
                    selectedType === type
                      ? bloombergColors.background
                      : bloombergColors.textSecondary,
                  backgroundColor:
                    selectedType === type
                      ? bloombergColors.accent
                      : "transparent",
                  "&:hover": {
                    backgroundColor:
                      selectedType === type
                        ? bloombergColors.accent
                        : `${bloombergColors.accent}20`,
                  },
                }}
              >
                {type.toUpperCase()}
              </Button>
            ))}
          </Box>

          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Typography
              variant="caption"
              sx={{
                color: bloombergColors.textSecondary,
                alignSelf: "center",
                minWidth: "40px",
              }}
            >
              Quality:
            </Typography>
            {["all", "weak", "moderate", "strong", "very_strong"].map(
              (quality) => (
                <Button
                  key={quality}
                  size="small"
                  variant={
                    selectedQuality === quality ? "contained" : "outlined"
                  }
                  onClick={() => setSelectedQuality(quality)}
                  sx={{
                    fontSize: "0.65rem",
                    minWidth: "50px",
                    height: "22px",
                    borderColor: bloombergColors.border,
                    color:
                      selectedQuality === quality
                        ? bloombergColors.background
                        : bloombergColors.textSecondary,
                    backgroundColor:
                      selectedQuality === quality
                        ? getQualityColor(quality)
                        : "transparent",
                    "&:hover": {
                      backgroundColor:
                        selectedQuality === quality
                          ? getQualityColor(quality)
                          : `${getQualityColor(quality)}20`,
                    },
                  }}
                >
                  {quality === "very_strong"
                    ? "V.STRONG"
                    : quality.toUpperCase()}
                </Button>
              )
            )}
          </Box>
        </Box>
      )}

      {/* Summary stats */}
      {!compact && (
        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <Chip
            label={`⚡ Total: ${allSignals.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.accent}20`,
              color: bloombergColors.accent,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`↗ Breakouts: ${breakouts.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.positive}20`,
              color: bloombergColors.positive,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`↘ Breakdowns: ${breakdowns.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.negative}20`,
              color: bloombergColors.negative,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`🔍 Filtered: ${filteredSignals.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.warning}20`,
              color: bloombergColors.warning,
              fontSize: "0.7rem",
            }}
          />
        </Box>
      )}

      {/* Signals List */}
      <Box
        sx={{
          height: compact ? "calc(100% - 50px)" : "calc(100% - 200px)",
          overflow: "auto",
          pr: 1,
        }}
      >
        {filteredSignals.length > 0 ? (
          filteredSignals
            .slice(0, compact ? 5 : 15)
            .map((signal) => renderBreakoutSignal(signal))
        ) : allSignals.length > 0 ? (
          <Box
            sx={{
              p: 2,
              textAlign: "center",
              color: bloombergColors.textSecondary,
              fontSize: "0.8rem",
            }}
          >
            No signals match the selected filters
          </Box>
        ) : (
          <Box
            sx={{
              p: 2,
              textAlign: "center",
              color: bloombergColors.textSecondary,
              fontSize: "0.8rem",
            }}
          >
            No breakout signals detected yet today
          </Box>
        )}
      </Box>

      {/* Summary Footer */}
      {!compact && summary && Object.keys(summary).length > 0 && (
        <Box
          sx={{
            mt: 1,
            pt: 1,
            borderTop: `1px solid ${bloombergColors.border}`,
            display: "flex",
            justifyContent: "space-around",
            fontSize: "0.75rem",
          }}
        >
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Market Hours
            </Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.positive }}>
              ACTIVE
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Breakout Ratio
            </Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {breakouts.length > 0 || breakdowns.length > 0
                ? (breakouts.length / Math.max(breakdowns.length, 1)).toFixed(2)
                : "N/A"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Market Direction
            </Box>
            <Box
              sx={{
                fontWeight: "bold",
                color:
                  breakouts.length > breakdowns.length
                    ? bloombergColors.positive
                    : breakdowns.length > breakouts.length
                    ? bloombergColors.negative
                    : bloombergColors.textPrimary,
              }}
            >
              {breakouts.length > breakdowns.length
                ? "BULLISH"
                : breakdowns.length > breakouts.length
                ? "BEARISH"
                : "NEUTRAL"}
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default withErrorBoundary(BreakoutAnalysisWidget, {
  fallbackMessage:
    "Unable to load breakout analysis data. Real-time breakout detection is currently unavailable.",
  height: "100%",
});
