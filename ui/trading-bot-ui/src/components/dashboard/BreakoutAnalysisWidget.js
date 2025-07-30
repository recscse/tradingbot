// components/dashboard/BreakoutAnalysisWidget.jsx
import React from "react";
import { Paper, Box, Grid } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";

const BreakoutAnalysisWidget = ({ data, isLoading, compact = false }) => {
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

  const { breakouts = [], breakdowns = [], summary = {} } = data;

  const renderBreakoutStock = (stock, isBreakout) => (
    <Box
      key={stock.symbol}
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
        position: "relative",
        "&::before": {
          content: '""',
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: "3px",
          backgroundColor: isBreakout
            ? bloombergColors.positive
            : bloombergColors.negative,
        },
        "&:hover": {
          backgroundColor: isBreakout
            ? `${bloombergColors.positive}15`
            : `${bloombergColors.negative}15`,
        },
      }}
    >
      <Box>
        <Box sx={{ fontWeight: "bold", fontSize: "0.9rem" }}>
          {stock.symbol}
        </Box>
        <Box sx={{ fontSize: "0.75rem", color: bloombergColors.textSecondary }}>
          ₹{stock.last_price?.toFixed(2)}
        </Box>
      </Box>

      <Box sx={{ textAlign: "right" }}>
        <Box
          sx={{
            color: isBreakout
              ? bloombergColors.positive
              : bloombergColors.negative,
            fontWeight: "bold",
            fontSize: "0.8rem",
          }}
        >
          {isBreakout ? "🔥" : "❄️"}{" "}
          {stock.breakout_strength || stock.breakdown_strength || "N/A"}
        </Box>
        <Box sx={{ fontSize: "0.65rem", color: bloombergColors.textSecondary }}>
          Vol: {stock.volume_ratio?.toFixed(1) || "N/A"}x
        </Box>
      </Box>
    </Box>
  );

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
        🔥 BREAKOUT ANALYSIS
      </Box>

      <Grid container spacing={2} sx={{ height: "calc(100% - 50px)" }}>
        <Grid item xs={12} md={6}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.positive,
              mb: 1,
            }}
          >
            🚀 BREAKOUTS ({breakouts.length})
          </Box>
          <Box sx={{ maxHeight: "250px", overflow: "auto" }}>
            {breakouts
              .slice(0, compact ? 5 : 8)
              .map((stock) => renderBreakoutStock(stock, true))}
          </Box>
        </Grid>

        <Grid item xs={12} md={6}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.negative,
              mb: 1,
            }}
          >
            💥 BREAKDOWNS ({breakdowns.length})
          </Box>
          <Box sx={{ maxHeight: "250px", overflow: "auto" }}>
            {breakdowns
              .slice(0, compact ? 5 : 8)
              .map((stock) => renderBreakoutStock(stock, false))}
          </Box>
        </Grid>
      </Grid>

      {/* Summary Section */}
      {!compact && summary && Object.keys(summary).length > 0 && (
        <Box
          sx={{
            mt: 2,
            pt: 2,
            borderTop: `1px solid ${bloombergColors.border}`,
            display: "flex",
            justifyContent: "space-around",
            fontSize: "0.75rem",
          }}
        >
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Market Sentiment
            </Box>
            <Box
              sx={{
                fontWeight: "bold",
                color:
                  summary.sentiment === "bullish"
                    ? bloombergColors.positive
                    : summary.sentiment === "bearish"
                    ? bloombergColors.negative
                    : bloombergColors.textPrimary,
              }}
            >
              {summary.sentiment?.toUpperCase() || "NEUTRAL"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>Avg Volume</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {summary.avg_volume_ratio?.toFixed(1) || "N/A"}x
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Total Signals
            </Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {breakouts.length + breakdowns.length}
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default BreakoutAnalysisWidget;
