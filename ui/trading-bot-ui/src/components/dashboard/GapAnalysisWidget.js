// components/dashboard/RecordMoversWidget.jsx
import React from "react";
import { bloombergColors } from "../../themes/bloombergColors";
import { Paper, Box, Grid } from "@mui/material";

const RecordMoversWidget = ({ data, isLoading, compact = false }) => {
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
            Loading record movers...
          </Box>
        </Box>
      </Paper>
    );
  }

  const { new_highs = [], new_lows = [], summary = {} } = data;

  const renderRecordStock = (stock, isHigh) => (
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
          content: isHigh ? '"🏆"' : '"⚠️"',
          position: "absolute",
          left: 4,
          top: "50%",
          transform: "translateY(-50%)",
          fontSize: "0.8rem",
        },
        pl: 3,
        "&:hover": {
          backgroundColor: isHigh
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
            color: isHigh ? bloombergColors.positive : bloombergColors.negative,
            fontWeight: "bold",
            fontSize: "0.8rem",
          }}
        >
          {stock.high_proximity || stock.low_proximity || "N/A"}%
        </Box>
        <Box sx={{ fontSize: "0.65rem", color: bloombergColors.textSecondary }}>
          Vol: {stock.volume ? (stock.volume / 1000).toFixed(0) + "K" : "N/A"}
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
        📊 RECORD MOVERS
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
            🏆 NEW HIGHS ({new_highs.length})
          </Box>
          <Box sx={{ maxHeight: "250px", overflow: "auto" }}>
            {new_highs
              .slice(0, compact ? 5 : 8)
              .map((stock) => renderRecordStock(stock, true))}
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
            ⚠️ NEW LOWS ({new_lows.length})
          </Box>
          <Box sx={{ maxHeight: "250px", overflow: "auto" }}>
            {new_lows
              .slice(0, compact ? 5 : 8)
              .map((stock) => renderRecordStock(stock, false))}
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
              Market Strength
            </Box>
            <Box
              sx={{
                fontWeight: "bold",
                color:
                  summary.market_strength === "strong"
                    ? bloombergColors.positive
                    : summary.market_strength === "weak"
                    ? bloombergColors.negative
                    : bloombergColors.textPrimary,
              }}
            >
              {summary.market_strength?.toUpperCase() || "NEUTRAL"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>H/L Ratio</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {summary.high_low_ratio?.toFixed(2) || "N/A"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Total Records
            </Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {new_highs.length + new_lows.length}
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default RecordMoversWidget;
