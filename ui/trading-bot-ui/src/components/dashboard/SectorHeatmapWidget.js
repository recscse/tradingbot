// components/dashboard/SectorHeatmapWidget.jsx
import React, { useMemo } from "react";
import { Paper, Box, Tooltip, Grid2 } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";

const SectorHeatmapWidget = ({ data, isLoading, height = 350 }) => {
  // Process sector data - MUST be before any early returns
  const sectorData = useMemo(() => {
    if (!data || !data.sectors) return [];

    return Object.entries(data.sectors).map(([sectorName, sectorInfo]) => ({
      name: sectorName,
      change: sectorInfo.change_percent || 0,
      value: sectorInfo.market_cap || sectorInfo.volume || 100,
      stocks_count: sectorInfo.stocks_count || 0,
      top_performer: sectorInfo.top_performer || null,
      worst_performer: sectorInfo.worst_performer || null,
      avg_volume_ratio: sectorInfo.avg_volume_ratio || 1,
    }));
  }, [data]);

  if (isLoading) {
    return (
      <Paper
        sx={{
          backgroundColor: bloombergColors.cardBg,
          border: `1px solid ${bloombergColors.border}`,
          borderRadius: 1,
          p: 2,
          height: height,
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
            Loading sector heatmap...
          </Box>
        </Box>
      </Paper>
    );
  }

  // Fallback data if no real data is available
  const fallbackSectors = [
    {
      name: "BANKING",
      change: 2.35,
      value: 850,
      stocks_count: 45,
      avg_volume_ratio: 1.2,
    },
    {
      name: "IT",
      change: -1.25,
      value: 720,
      stocks_count: 32,
      avg_volume_ratio: 0.9,
    },
    {
      name: "PHARMA",
      change: 3.45,
      value: 340,
      stocks_count: 28,
      avg_volume_ratio: 1.4,
    },
    {
      name: "AUTO",
      change: -2.15,
      value: 280,
      stocks_count: 22,
      avg_volume_ratio: 1.1,
    },
    {
      name: "FMCG",
      change: 0.85,
      value: 420,
      stocks_count: 18,
      avg_volume_ratio: 0.8,
    },
    {
      name: "METALS",
      change: 4.25,
      value: 190,
      stocks_count: 25,
      avg_volume_ratio: 1.8,
    },
    {
      name: "ENERGY",
      change: -0.95,
      value: 380,
      stocks_count: 15,
      avg_volume_ratio: 1.3,
    },
    {
      name: "REALTY",
      change: 1.75,
      value: 120,
      stocks_count: 35,
      avg_volume_ratio: 2.1,
    },
    {
      name: "TELECOM",
      change: -1.85,
      value: 95,
      stocks_count: 8,
      avg_volume_ratio: 0.7,
    },
    {
      name: "MEDIA",
      change: 2.95,
      value: 65,
      stocks_count: 12,
      avg_volume_ratio: 1.5,
    },
    {
      name: "PSU",
      change: 1.45,
      value: 240,
      stocks_count: 28,
      avg_volume_ratio: 1.6,
    },
    {
      name: "FINANCE",
      change: -0.65,
      value: 520,
      stocks_count: 38,
      avg_volume_ratio: 1.0,
    },
  ];

  const sectors = sectorData.length > 0 ? sectorData : fallbackSectors;

  // Calculate colors and sizes
  const getHeatmapColor = (change) => {
    const intensity = Math.min(Math.abs(change) / 5, 1); // Scale to 0-1 based on 5% max
    if (change > 0) {
      return `rgba(0, 255, 65, ${0.2 + intensity * 0.6})`;
    } else if (change < 0) {
      return `rgba(255, 7, 58, ${0.2 + intensity * 0.6})`;
    } else {
      return `rgba(255, 176, 0, 0.3)`;
    }
  };

  const getBorderColor = (change) => {
    if (change > 2) return bloombergColors.positive;
    if (change < -2) return bloombergColors.negative;
    return bloombergColors.border;
  };

  const getRelativeSize = (value, maxValue) => {
    return Math.max(0.3, (value / maxValue) * 1.2); // Min 30%, max 120%
  };

  const maxValue = Math.max(...sectors.map((s) => s.value));

  // Get sector icon
  const getSectorIcon = (sectorName) => {
    const iconMap = {
      BANKING: "🏦",
      IT: "💻",
      PHARMA: "💊",
      AUTO: "🚗",
      FMCG: "🛒",
      METALS: "⚒️",
      ENERGY: "⚡",
      REALTY: "🏠",
      TELECOM: "📡",
      MEDIA: "📺",
      PSU: "🏛️",
      FINANCE: "💰",
    };
    return iconMap[sectorName.toUpperCase()] || "📊";
  };

  // Sort sectors by performance for better visualization
  const sortedSectors = [...sectors].sort((a, b) => b.change - a.change);

  return (
    <Paper
      elevation={0}
      sx={{
        backgroundColor: bloombergColors.cardBg,
        border: `1px solid ${bloombergColors.border}`,
        borderRadius: 1,
        p: 2,
        height: height,
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
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>🔥 SECTOR HEATMAP</Box>
        <Box
          sx={{
            fontSize: "0.7rem",
            color: bloombergColors.textSecondary,
            display: "flex",
            alignItems: "center",
            gap: 1,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                backgroundColor: bloombergColors.positive,
                borderRadius: "50%",
              }}
            />
            GAINERS
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                backgroundColor: bloombergColors.negative,
                borderRadius: "50%",
              }}
            />
            LOSERS
          </Box>
        </Box>
      </Box>

      <Grid2
        container
        spacing={1.5}
        sx={{
          height: "calc(100% - 50px)",
          overflow: "auto",
          "&::-webkit-scrollbar": {
            width: "4px",
          },
          "&::-webkit-scrollbar-track": {
            backgroundColor: bloombergColors.background,
          },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: bloombergColors.accent,
            borderRadius: "2px",
          },
        }}
      >
        {sortedSectors.map((sector) => {
          const relativeSize = getRelativeSize(sector.value, maxValue);
          const isLarge = relativeSize > 0.8;

          return (
            <Grid2
              key={sector.name}
              xs={isLarge ? 3 : 2}
              sm={isLarge ? 2 : 1.5}
              md={isLarge ? 2 : 1.5}
            >
              <Tooltip
                title={
                  <Box>
                    <Box sx={{ fontWeight: "bold", mb: 0.5 }}>
                      {getSectorIcon(sector.name)} {sector.name}
                    </Box>
                    <Box>
                      Change: {sector.change > 0 ? "+" : ""}
                      {sector.change.toFixed(2)}%
                    </Box>
                    <Box>Stocks: {sector.stocks_count}</Box>
                    <Box>Vol Ratio: {sector.avg_volume_ratio.toFixed(1)}x</Box>
                    {sector.top_performer && (
                      <Box>Top: {sector.top_performer}</Box>
                    )}
                    {sector.worst_performer && (
                      <Box>Worst: {sector.worst_performer}</Box>
                    )}
                  </Box>
                }
                arrow
              >
                <Box
                  sx={{
                    backgroundColor: getHeatmapColor(sector.change),
                    border: `2px solid ${getBorderColor(sector.change)}`,
                    borderRadius: 1,
                    p: 1,
                    height: `${60 + relativeSize * 40}px`,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    alignItems: "center",
                    cursor: "pointer",
                    transition: "all 0.3s ease",
                    position: "relative",
                    overflow: "hidden",
                    "&:hover": {
                      transform: "scale(1.05)",
                      boxShadow: `0 0 15px ${getBorderColor(sector.change)}40`,
                      borderWidth: "3px",
                    },
                    "&::before": {
                      content: '""',
                      position: "absolute",
                      top: 0,
                      left: 0,
                      right: 0,
                      height: "3px",
                      backgroundColor:
                        sector.change > 0
                          ? bloombergColors.positive
                          : sector.change < 0
                          ? bloombergColors.negative
                          : bloombergColors.warning,
                    },
                  }}
                >
                  {/* Sector Icon */}
                  <Box sx={{ fontSize: "1.2rem", mb: 0.5 }}>
                    {getSectorIcon(sector.name)}
                  </Box>

                  {/* Sector Name */}
                  <Box
                    sx={{
                      fontSize: "0.75rem",
                      fontWeight: "bold",
                      color: bloombergColors.textPrimary,
                      textAlign: "center",
                      mb: 0.5,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                    }}
                  >
                    {sector.name}
                  </Box>

                  {/* Performance */}
                  <Box
                    sx={{
                      fontSize: "0.9rem",
                      fontWeight: "bold",
                      color:
                        sector.change > 0
                          ? bloombergColors.positive
                          : sector.change < 0
                          ? bloombergColors.negative
                          : bloombergColors.warning,
                      textAlign: "center",
                    }}
                  >
                    {sector.change > 0 ? "+" : ""}
                    {sector.change.toFixed(2)}%
                  </Box>

                  {/* Stock Count */}
                  <Box
                    sx={{
                      fontSize: "0.6rem",
                      color: bloombergColors.textSecondary,
                      textAlign: "center",
                      mt: 0.5,
                    }}
                  >
                    {sector.stocks_count} stocks
                  </Box>

                  {/* High activity indicator */}
                  {sector.avg_volume_ratio > 1.5 && (
                    <Box
                      sx={{
                        position: "absolute",
                        top: 4,
                        right: 4,
                        fontSize: "0.7rem",
                      }}
                    >
                      🔥
                    </Box>
                  )}
                </Box>
              </Tooltip>
            </Grid2>
          );
        })}
      </Grid2>

      {/* Summary Footer */}
      <Box
        sx={{
          mt: 1,
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
          {sectors.filter((s) => s.change > 0).length} sectors advancing,{" "}
          {sectors.filter((s) => s.change < 0).length} declining
        </Box>
        <Box>
          Market Breadth:{" "}
          {sectors.filter((s) => s.change > 0).length >
          sectors.filter((s) => s.change < 0).length ? (
            <Box
              component="span"
              sx={{ color: bloombergColors.positive, fontWeight: "bold" }}
            >
              BULLISH
            </Box>
          ) : (
            <Box
              component="span"
              sx={{ color: bloombergColors.negative, fontWeight: "bold" }}
            >
              BEARISH
            </Box>
          )}
        </Box>
      </Box>
    </Paper>
  );
};

export default SectorHeatmapWidget;
