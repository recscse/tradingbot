// components/dashboard/GapAnalysisWidget.jsx
import React from "react";
import { bloombergColors } from "../../themes/bloombergColors";
import { Paper, Box, Grid2, Chip, Tooltip } from "@mui/material";
import { withErrorBoundary } from "../common/ErrorBoundary";

const GapAnalysisWidget = ({ data, isLoading, compact = false }) => {
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
            Loading gap analysis...
          </Box>
        </Box>
      </Paper>
    );
  }

  // FIXED: Backend sends gap_up and gap_down arrays
  const { gap_up = [], gap_down = [], summary = {} } = data;

  // Format volume for display
  const formatVolume = (volume) => {
    if (!volume) return "N/A";
    if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
    if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  // Get gap strength color
  const getGapStrengthColor = (strength) => {
    switch (strength) {
      case "very_strong":
        return bloombergColors.accent;
      case "strong":
        return bloombergColors.positive;
      case "moderate":
        return bloombergColors.warning;
      default:
        return bloombergColors.textSecondary;
    }
  };

  // Get gap strength icon
  const getGapStrengthIcon = (percentage) => {
    const abs = Math.abs(percentage);
    if (abs >= 8) return "🔥";
    if (abs >= 5) return "⚡";
    if (abs >= 2.5) return "📈";
    return "📊";
  };

  // Render individual gap stock
  const renderGapStock = (stock, isGapUp) => {
    const gapPercentage = stock.gap_percentage || 0;
    const absGapPercentage = Math.abs(gapPercentage);
    const gapStrength = stock.gap_strength || "weak";
    const confidence = stock.confidence_score || 0;

    // Format timestamp for display
    const timeStr = stock.timestamp 
      ? new Date(stock.timestamp).toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
        })
      : "N/A";

    return (
      <Tooltip
        key={stock.symbol}
        title={
          <Box>
            <Box sx={{ fontWeight: "bold" }}>{stock.symbol}</Box>
            <Box>Open: ₹{stock.open_price?.toFixed(2)}</Box>
            <Box>Prev Close: ₹{stock.previous_close?.toFixed(2)}</Box>
            <Box>Gap: {gapPercentage > 0 ? "+" : ""}{gapPercentage.toFixed(2)}%</Box>
            <Box>Volume: {formatVolume(stock.volume)} ({stock.volume_ratio?.toFixed(1)}x)</Box>
            <Box>Strength: {gapStrength.toUpperCase()}</Box>
            <Box>Confidence: {(confidence * 100).toFixed(0)}%</Box>
            <Box>Sector: {stock.sector || "N/A"}</Box>
            <Box>Time: {timeStr}</Box>
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
              isGapUp ? bloombergColors.positive : bloombergColors.negative
            }`,
            position: "relative",
            cursor: "pointer",
            transition: "all 0.3s ease",
            "&:hover": {
              borderColor: isGapUp
                ? bloombergColors.positive
                : bloombergColors.negative,
              backgroundColor: isGapUp
                ? `${bloombergColors.positive}15`
                : `${bloombergColors.negative}15`,
              transform: "translateX(2px)",
            },
          }}
        >
          {/* Gap strength indicator */}
          {absGapPercentage >= 5 && (
            <Box
              sx={{
                position: "absolute",
                top: 2,
                right: 2,
                fontSize: "0.7rem",
              }}
            >
              {getGapStrengthIcon(gapPercentage)}
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
                {getGapStrengthIcon(gapPercentage)}
              </span>
              {stock.symbol}
            </Box>
            <Box
              sx={{ fontSize: "0.75rem", color: bloombergColors.textSecondary }}
            >
              ₹{stock.current_price?.toFixed(2)} | Open: ₹{stock.open_price?.toFixed(2)}
            </Box>
            <Box
              sx={{
                fontSize: "0.65rem",
                color: bloombergColors.textSecondary,
              }}
            >
              {timeStr} | Vol: {formatVolume(stock.volume)}
            </Box>
          </Box>

          <Box sx={{ textAlign: "right", minWidth: "80px" }}>
            <Chip
              label={`${gapPercentage > 0 ? "+" : ""}${gapPercentage.toFixed(1)}%`}
              size="small"
              sx={{
                backgroundColor: isGapUp
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
                color: getGapStrengthColor(gapStrength),
                fontWeight: "bold",
                textTransform: "uppercase",
              }}
            >
              {gapStrength}
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
          📈 GAP ANALYSIS
        </Box>

        {/* Market opening indicator */}
        <Chip
          label="MARKET OPEN"
          size="small"
          sx={{
            backgroundColor: `${bloombergColors.positive}20`,
            color: bloombergColors.positive,
            fontSize: "0.7rem",
            fontWeight: "bold",
          }}
        />
      </Box>

      {/* Summary stats */}
      {!compact && (
        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <Chip
            label={`↗ Gap Up: ${gap_up.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.positive}20`,
              color: bloombergColors.positive,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`↘ Gap Down: ${gap_down.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.negative}20`,
              color: bloombergColors.negative,
              fontSize: "0.7rem",
            }}
          />
          {summary.avg_gap_up && (
            <Chip
              label={`Avg ↗: ${summary.avg_gap_up.toFixed(1)}%`}
              size="small"
              sx={{
                backgroundColor: `${bloombergColors.accent}20`,
                color: bloombergColors.accent,
                fontSize: "0.7rem",
              }}
            />
          )}
          {summary.avg_gap_down && (
            <Chip
              label={`Avg ↘: ${Math.abs(summary.avg_gap_down).toFixed(1)}%`}
              size="small"
              sx={{
                backgroundColor: `${bloombergColors.warning}20`,
                color: bloombergColors.warning,
                fontSize: "0.7rem",
              }}
            />
          )}
        </Box>
      )}

      <Grid2
        container
        spacing={2}
        sx={{ height: compact ? "calc(100% - 50px)" : "calc(100% - 120px)" }}
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
            📈 GAP UP ({gap_up.length})
          </Box>
          <Box sx={{ maxHeight: "300px", overflow: "auto", pr: 1 }}>
            {gap_up.length > 0 ? (
              gap_up
                .slice(0, compact ? 5 : 10)
                .map((stock) => renderGapStock(stock, true))
            ) : (
              <Box sx={{ 
                p: 2, 
                textAlign: "center", 
                color: bloombergColors.textSecondary,
                fontSize: "0.8rem"
              }}>
                No gap up stocks detected today
              </Box>
            )}
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
            📉 GAP DOWN ({gap_down.length})
          </Box>
          <Box sx={{ maxHeight: "300px", overflow: "auto", pr: 1 }}>
            {gap_down.length > 0 ? (
              gap_down
                .slice(0, compact ? 5 : 10)
                .map((stock) => renderGapStock(stock, false))
            ) : (
              <Box sx={{ 
                p: 2, 
                textAlign: "center", 
                color: bloombergColors.textSecondary,
                fontSize: "0.8rem"
              }}>
                No gap down stocks detected today
              </Box>
            )}
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
            <Box sx={{ color: bloombergColors.textSecondary }}>Market Opening</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {new Date().toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
              })}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>Gap Ratio</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {gap_up.length > 0 || gap_down.length > 0
                ? (gap_up.length / Math.max(gap_down.length, 1)).toFixed(2)
                : "N/A"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Market Mood
            </Box>
            <Box sx={{ 
              fontWeight: "bold", 
              color: gap_up.length > gap_down.length 
                ? bloombergColors.positive 
                : gap_down.length > gap_up.length 
                ? bloombergColors.negative 
                : bloombergColors.textPrimary 
            }}>
              {gap_up.length > gap_down.length
                ? "BULLISH"
                : gap_down.length > gap_up.length
                ? "BEARISH"
                : "NEUTRAL"}
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default withErrorBoundary(GapAnalysisWidget, {
  fallbackMessage: "Unable to load gap analysis data. Gap detection occurs at market opening (9:15 AM).",
  height: "100%"
});