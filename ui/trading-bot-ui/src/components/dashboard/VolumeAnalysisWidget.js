// components/dashboard/VolumeAnalysisWidget.jsx
import React from "react";
import { Box, Paper, Grid, Chip } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";

const VolumeAnalysisWidget = ({ data, isLoading, compact = false }) => {
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
            Loading volume analysis...
          </Box>
        </Box>
      </Paper>
    );
  }

  const {
    volume_leaders = [],
    unusual_volume = [],
    volume_momentum = [],
    summary = {},
  } = data;

  const formatVolume = (volume) => {
    if (!volume) return "N/A";
    if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
    if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  const renderVolumeStock = (stock, type) => {
    const getTypeColor = (type) => {
      switch (type) {
        case "unusual":
          return bloombergColors.warning;
        case "momentum":
          return bloombergColors.info;
        default:
          return bloombergColors.accent;
      }
    };

    const getTypeIcon = (type) => {
      switch (type) {
        case "unusual":
          return "⚡";
        case "momentum":
          return "🚀";
        default:
          return "📈";
      }
    };

    return (
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
            content: `"${getTypeIcon(type)}"`,
            position: "absolute",
            left: 4,
            top: "50%",
            transform: "translateY(-50%)",
            fontSize: "0.8rem",
          },
          pl: 3,
          "&:hover": {
            borderColor: getTypeColor(type),
            backgroundColor: `${getTypeColor(type)}10`,
          },
        }}
      >
        <Box>
          <Box sx={{ fontWeight: "bold", fontSize: "0.9rem" }}>
            {stock.symbol}
          </Box>
          <Box
            sx={{ fontSize: "0.75rem", color: bloombergColors.textSecondary }}
          >
            ₹{stock.last_price?.toFixed(2)}
          </Box>
        </Box>

        <Box sx={{ textAlign: "right" }}>
          <Box
            sx={{
              fontSize: "0.8rem",
              fontWeight: "bold",
              color: getTypeColor(type),
            }}
          >
            {formatVolume(stock.volume)}
          </Box>
          <Box
            sx={{ fontSize: "0.65rem", color: bloombergColors.textSecondary }}
          >
            {type === "unusual"
              ? `${stock.volume_ratio?.toFixed(1) || "N/A"}x`
              : type === "momentum"
              ? `${stock.change_percent?.toFixed(1) || "N/A"}%`
              : `Avg: ${formatVolume(stock.avg_volume) || "N/A"}`}
          </Box>
        </Box>
      </Box>
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
          fontSize: "1rem",
          fontWeight: "bold",
          color: bloombergColors.accent,
          mb: 2,
          letterSpacing: "1px",
        }}
      >
        📊 VOLUME ANALYSIS
      </Box>

      {/* Summary Stats */}
      {!compact && (
        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <Chip
            label={`Leaders: ${volume_leaders.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.accent}20`,
              color: bloombergColors.accent,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`Unusual: ${unusual_volume.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.warning}20`,
              color: bloombergColors.warning,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`Momentum: ${volume_momentum.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.info}20`,
              color: bloombergColors.info,
              fontSize: "0.7rem",
            }}
          />
        </Box>
      )}

      <Grid
        container
        spacing={2}
        sx={{ height: compact ? "calc(100% - 50px)" : "calc(100% - 100px)" }}
      >
        <Grid item xs={12} md={4}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.accent,
              mb: 1,
            }}
          >
            📈 VOLUME LEADERS ({volume_leaders.length})
          </Box>
          <Box sx={{ maxHeight: "200px", overflow: "auto" }}>
            {volume_leaders
              .slice(0, compact ? 3 : 6)
              .map((stock) => renderVolumeStock(stock, "leader"))}
          </Box>
        </Grid>

        <Grid item xs={12} md={4}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.warning,
              mb: 1,
            }}
          >
            ⚡ UNUSUAL VOLUME ({unusual_volume.length})
          </Box>
          <Box sx={{ maxHeight: "200px", overflow: "auto" }}>
            {unusual_volume
              .slice(0, compact ? 3 : 6)
              .map((stock) => renderVolumeStock(stock, "unusual"))}
          </Box>
        </Grid>

        <Grid item xs={12} md={4}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.info,
              mb: 1,
            }}
          >
            🚀 VOLUME MOMENTUM ({volume_momentum.length})
          </Box>
          <Box sx={{ maxHeight: "200px", overflow: "auto" }}>
            {volume_momentum
              .slice(0, compact ? 3 : 6)
              .map((stock) => renderVolumeStock(stock, "momentum"))}
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
              Total Volume
            </Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {formatVolume(summary.total_volume) || "N/A"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>Avg Ratio</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.warning }}>
              {summary.avg_volume_ratio?.toFixed(2) || "N/A"}x
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Activity Level
            </Box>
            <Box
              sx={{
                fontWeight: "bold",
                color:
                  summary.activity_level === "high"
                    ? bloombergColors.positive
                    : summary.activity_level === "low"
                    ? bloombergColors.negative
                    : bloombergColors.textPrimary,
              }}
            >
              {summary.activity_level?.toUpperCase() || "NORMAL"}
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default VolumeAnalysisWidget;
