// components/common/FinancialHeatmap.jsx - Traditional Financial Treemap Style
import React, { memo, useMemo, useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Paper,
  Tooltip,
  useTheme,
  useMediaQuery,
  Stack,
  Chip,
  ButtonGroup,
  Button,
  Divider,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ViewModule as TreemapIcon,
  BubbleChart as BubbleIcon,
  BarChart as BarIcon,
  Timeline as TimelineIcon,
} from "@mui/icons-material";

const FinancialHeatmap = memo(
  ({
    data = [],
    marketData = {},
    title = "🔥 SECTOR HEATMAP",
    isLoading = false,
    maxItems = 30, // Increased from 20 to 30
    fullPage = true, // New prop for full page mode
  }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
    const isTablet = useMediaQuery(theme.breakpoints.down("md"));
    const isLargeScreen = useMediaQuery(theme.breakpoints.up("xl"));

    // Removed unused sectorStocks state - functionality handled in useMemo
    const [visualizationMode, setVisualizationMode] = useState("treemap"); // treemap, bubble, bar, timeline

    // Stock organization is handled in the processedSectors useMemo below

    // Financial color scheme
    const colors = {
      background: theme.palette.mode === "dark" ? "#0a0e1a" : "#ffffff",
      surface: theme.palette.mode === "dark" ? "#1e293b" : "#f8f9fa",
      text: theme.palette.mode === "dark" ? "#ffffff" : "#000000",
      textSecondary: theme.palette.mode === "dark" ? "#94a3b8" : "#666666",
      positive1: "#00C851", // Light green
      positive2: "#007E33", // Medium green
      positive3: "#004D20", // Dark green
      negative1: "#FF4444", // Light red
      negative2: "#CC0000", // Medium red
      negative3: "#800000", // Dark red
      neutral: "#E0E0E0",
      border: theme.palette.mode === "dark" ? "#475569" : "#cccccc",
    };

    // Process sectors and extract stocks for each sector from marketData
    const processedData = useMemo(() => {
      if (!data || !Array.isArray(data) || !marketData) return [];

      const sectors = data
        .slice(0, maxItems)
        .map((sector) => ({
          ...sector,
          sector_name: sector.sector || sector.sector_name || "UNKNOWN",
          change_percent: parseFloat(
            sector.avg_change_percent || sector.change_percent || 0
          ),
          stocks_count: parseInt(
            sector.stocks_count || sector.total_stocks || 0
          ),
          market_weight: parseFloat(
            sector.market_weight || sector.stocks_count || 1
          ),
        }))
        .sort(
          (a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent)
        );

      // For each sector, find the individual stocks from marketData
      return sectors.map((sector) => {
        const sectorStocks = [];

        // Find stocks in this sector from marketData
        Object.entries(marketData).forEach(([instrumentKey, stockData]) => {
          if (stockData && stockData.sector === sector.sector_name) {
            const symbol =
              stockData.symbol || stockData.trading_symbol || instrumentKey;
            if (symbol && stockData.ltp) {
              sectorStocks.push({
                symbol: symbol,
                name: stockData.name || symbol,
                last_price: parseFloat(
                  stockData.ltp || stockData.last_price || 0
                ),
                change_percent: parseFloat(
                  stockData.change_percent || stockData.pchange || 0
                ),
                volume: parseInt(stockData.volume || 0),
                instrument_key: instrumentKey,
              });
            }
          }
        });

        // Sort stocks by absolute change percent
        sectorStocks.sort(
          (a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent)
        );

        return {
          ...sector,
          stocks: sectorStocks.slice(0, 12), // Limit stocks per sector for display
        };
      });
    }, [data, marketData, maxItems]);

    // Get performance-based color
    const getPerformanceColor = (changePercent) => {
      if (changePercent > 3) return colors.positive3;
      if (changePercent > 1) return colors.positive2;
      if (changePercent > 0) return colors.positive1;
      if (changePercent < -3) return colors.negative3;
      if (changePercent < -1) return colors.negative2;
      if (changePercent < 0) return colors.negative1;
      return colors.neutral;
    };

    // Get stock performance color
    const getStockColor = (changePercent) => {
      const baseColor = getPerformanceColor(changePercent);
      return `${baseColor}E6`; // 90% opacity
    };

    // Calculate worst aspect ratio in a row (moved up for proper dependency order)
    const worst = useCallback((row, sideLength) => {
      if (row.length === 0) return Infinity;

      const sum = row.reduce((acc, item) => acc + item.area, 0);
      const min = Math.min(...row.map((item) => item.area));
      const max = Math.max(...row.map((item) => item.area));

      const s2 = sum * sum;
      const w2 = sideLength * sideLength;

      return Math.max((w2 * max) / s2, s2 / (w2 * min));
    }, []);

    // Layout a row of items (moved up for proper dependency order)
    const layoutRow = useCallback((row, width, height, x, y) => {
      const totalArea = row.reduce((sum, item) => sum + item.area, 0);
      let currentPos = 0;

      return row.map((item) => {
        const itemArea = item.area;
        const ratio = itemArea / totalArea;

        let itemWidth, itemHeight, itemX, itemY;

        if (width >= height) {
          // Horizontal layout
          itemWidth = ratio * width;
          itemHeight = height;
          itemX = x + currentPos;
          itemY = y;
          currentPos += itemWidth;
        } else {
          // Vertical layout
          itemWidth = width;
          itemHeight = ratio * height;
          itemX = x;
          itemY = y + currentPos;
          currentPos += itemHeight;
        }

        return {
          ...item,
          x: itemX,
          y: itemY,
          width: Math.max(10, itemWidth), // Minimum width
          height: Math.max(10, itemHeight), // Minimum height
        };
      });
    }, []);

    // Squarified treemap algorithm for better aspect ratios
    const squarify = useCallback(
      (data, currentRow, width, height, x, y) => {
        if (data.length === 0) {
          if (currentRow.length === 0) return [];
          return layoutRow(currentRow, width, height, x, y);
        }

        const item = data[0];
        const newRow = [...currentRow, item];

        if (
          currentRow.length === 0 ||
          worst(newRow, Math.min(width, height)) <=
            worst(currentRow, Math.min(width, height))
        ) {
          // Add item to current row
          return squarify(data.slice(1), newRow, width, height, x, y);
        } else {
          // Layout current row and start new one
          const rowArea = currentRow.reduce((sum, item) => sum + item.area, 0);
          const totalArea = width * height;
          const rowSize = rowArea / totalArea;

          let newWidth, newHeight, newX, newY;

          if (width >= height) {
            // Horizontal split
            const rowWidth = rowSize * width;
            newWidth = width - rowWidth;
            newHeight = height;
            newX = x + rowWidth;
            newY = y;
          } else {
            // Vertical split
            const rowHeight = rowSize * height;
            newWidth = width;
            newHeight = height - rowHeight;
            newX = x;
            newY = y + rowHeight;
          }

          const currentLayout = layoutRow(
            currentRow,
            width >= height ? rowSize * width : width,
            width >= height ? height : rowSize * height,
            x,
            y
          );

          const remainingLayout = squarify(
            data,
            [],
            newWidth,
            newHeight,
            newX,
            newY
          );

          return [...currentLayout, ...remainingLayout];
        }
      },
      [worst, layoutRow]
    );

    // Enhanced Squarified Treemap Algorithm Implementation
    const calculateTreemapLayout = useCallback(
      (data, containerWidth, containerHeight) => {
        if (!data || data.length === 0) return [];

        // Sort data by value (descending) for better layout
        const sortedData = [...data].sort(
          (a, b) => (b.value || 1) - (a.value || 1)
        );
        const totalValue = sortedData.reduce(
          (sum, item) => sum + (item.value || 1),
          0
        );

        if (totalValue === 0) return [];

        // Calculate normalized areas
        const normalizedData = sortedData.map((item) => ({
          ...item,
          normalizedValue: (item.value || 1) / totalValue,
          area:
            ((item.value || 1) / totalValue) * containerWidth * containerHeight,
        }));

        return squarify(
          normalizedData,
          [],
          containerWidth,
          containerHeight,
          0,
          0
        );
      },
      [squarify]
    );

    // Helper functions moved above for proper dependency order

    // Calculate sector treemap layout
    const sectorTreemapLayout = useMemo(() => {
      if (!processedData.length) return [];

      // Enhanced responsive dimensions for full page mode
      const containerWidth = fullPage
        ? isLargeScreen
          ? 1200
          : isTablet
          ? 900
          : isMobile
          ? 320
          : 1000
        : isMobile
        ? 320
        : 800;
      const containerHeight = fullPage
        ? isLargeScreen
          ? 800
          : isTablet
          ? 600
          : isMobile
          ? 400
          : 700
        : isMobile
        ? 300
        : 500;

      const sectorsWithValues = processedData.map((sector) => ({
        ...sector,
        value:
          sector.market_weight > 0 ? sector.market_weight : sector.stocks_count,
      }));

      return calculateTreemapLayout(
        sectorsWithValues,
        containerWidth,
        containerHeight
      );
    }, [
      processedData,
      isMobile,
      calculateTreemapLayout,
      fullPage,
      isLargeScreen,
      isTablet,
    ]);

    // Calculate stock treemap layout for each sector with better spacing
    const getStockTreemapLayout = (stocks, sectorWidth, sectorHeight) => {
      if (!stocks || stocks.length === 0) return [];

      // Filter and enhance stock data
      const validStocks = stocks
        .filter((stock) => stock && stock.symbol)
        .slice(0, 8) // Limit to 8 stocks for better visibility
        .map((stock) => ({
          ...stock,
          value: Math.max(
            1,
            (stock.last_price || 100) * (stock.volume || 1000) +
              Math.abs(stock.change_percent || 0) * 10000
          ),
        }));

      if (validStocks.length === 0) return [];

      // Calculate inner dimensions with better margins
      const headerHeight = 30; // Space for sector header
      const footerHeight = 25; // Space for sector footer
      const margin = 8; // Margin around the edges

      const innerWidth = Math.max(50, sectorWidth - margin * 2);
      const innerHeight = Math.max(
        30,
        sectorHeight - headerHeight - footerHeight - margin
      );

      if (innerWidth <= 50 || innerHeight <= 30) return [];

      return calculateTreemapLayout(validStocks, innerWidth, innerHeight);
    };

    // Bubble Chart Layout Algorithm
    const calculateBubbleLayout = (data, containerWidth, containerHeight) => {
      if (!data || data.length === 0) return [];

      const totalValue = data.reduce((sum, item) => sum + (item.value || 1), 0);
      const maxRadius = Math.min(containerWidth, containerHeight) * 0.15;
      const minRadius = 20;

      // Calculate radius for each bubble
      const bubbles = data.map((item) => ({
        ...item,
        radius: Math.max(
          minRadius,
          Math.min(
            maxRadius,
            Math.sqrt(item.value / totalValue) * maxRadius * 3
          )
        ),
      }));

      // Simple circle packing algorithm
      const result = [];
      const attempts = 50;

      bubbles.forEach((bubble, index) => {
        let placed = false;
        let bestX = containerWidth / 2;
        let bestY = containerHeight / 2;

        for (let attempt = 0; attempt < attempts && !placed; attempt++) {
          const x =
            bubble.radius +
            Math.random() * (containerWidth - 2 * bubble.radius);
          const y =
            bubble.radius +
            Math.random() * (containerHeight - 2 * bubble.radius);

          let overlapping = false;
          for (let j = 0; j < result.length; j++) {
            const other = result[j];
            const distance = Math.sqrt(
              Math.pow(x - other.x, 2) + Math.pow(y - other.y, 2)
            );
            if (distance < bubble.radius + other.radius + 5) {
              overlapping = true;
              break;
            }
          }

          if (!overlapping) {
            bestX = x;
            bestY = y;
            placed = true;
          }
        }

        result.push({
          ...bubble,
          x: bestX,
          y: bestY,
        });
      });

      return result;
    };

    // Calculate sector bubble layout
    const sectorBubbleLayout = useMemo(() => {
      if (!processedData.length) return [];

      // Enhanced responsive dimensions for full page mode
      const containerWidth = fullPage
        ? isLargeScreen
          ? 1200
          : isTablet
          ? 900
          : isMobile
          ? 320
          : 1000
        : isMobile
        ? 320
        : 800;
      const containerHeight = fullPage
        ? isLargeScreen
          ? 800
          : isTablet
          ? 600
          : isMobile
          ? 400
          : 700
        : isMobile
        ? 300
        : 500;

      const sectorsWithValues = processedData.map((sector) => ({
        ...sector,
        value:
          sector.market_weight > 0 ? sector.market_weight : sector.stocks_count,
      }));

      return calculateBubbleLayout(
        sectorsWithValues,
        containerWidth,
        containerHeight
      );
    }, [processedData, isMobile, fullPage, isLargeScreen, isTablet]);

    // Calculate stock bubble layout for each sector
    const getStockBubbleLayout = (stocks, sectorRadius) => {
      if (!stocks || stocks.length === 0) return [];

      const stocksWithValues = stocks.map((stock) => ({
        ...stock,
        value: stock.last_price * (stock.volume || 1000),
      }));

      const containerSize = sectorRadius * 1.6;
      return calculateBubbleLayout(
        stocksWithValues,
        containerSize,
        containerSize
      );
    };

    if (isLoading) {
      return (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, color: colors.text }}>
              {title}
            </Typography>
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                gap: 1,
                animation: "pulse 1.5s ease-in-out infinite",
                "@keyframes pulse": {
                  "0%, 100%": { opacity: 1 },
                  "50%": { opacity: 0.5 },
                },
              }}
            >
              {[...Array(isMobile ? 6 : 12)].map((_, i) => (
                <Box
                  key={i}
                  sx={{
                    width: isMobile ? 100 : 150,
                    height: isMobile ? 60 : 90,
                    bgcolor: colors.surface,
                    borderRadius: 1,
                  }}
                />
              ))}
            </Box>
          </CardContent>
        </Card>
      );
    }

    if (!processedData.length) {
      return (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, color: colors.text }}>
              {title}
            </Typography>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                py: 4,
                color: colors.textSecondary,
              }}
            >
              <Typography variant="body2">No sector data available</Typography>
            </Box>
          </CardContent>
        </Card>
      );
    }

    return (
      <Card
        sx={{
          mb: fullPage ? 0 : 2,
          bgcolor: colors.background,
          border: `1px solid ${colors.border}`,
          borderRadius: fullPage ? 1 : 2,
          overflow: "visible", // Always allow tooltips to show
          width: "100%", // Use full container width
          maxWidth: "100%", // Prevent overflow
          minHeight: fullPage ? "auto" : "auto",
          position: "relative",
          mx: 0, // No extra margins
          p: 0, // No extra padding
        }}
      >
        <CardContent sx={{ p: { xs: 1, sm: 2, md: 3 }, overflow: "hidden" }}>
          {/* Header */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <Typography
              variant={isMobile ? "subtitle1" : "h6"}
              sx={{
                color: colors.text,
                fontWeight: 700,
                fontSize: { xs: "1rem", sm: "1.25rem" },
                fontFamily: '"Segoe UI", "Inter", sans-serif',
              }}
            >
              {title} ({processedData.length})
            </Typography>

            <Stack direction="row" spacing={1}>
              <Chip
                icon={<TrendingUpIcon sx={{ fontSize: "0.8rem" }} />}
                label={`${
                  processedData.filter((s) => s.change_percent > 0).length
                } ↑`}
                size="small"
                sx={{
                  bgcolor: `${colors.positive1}20`,
                  color: colors.positive2,
                  fontSize: "0.7rem",
                  height: 24,
                }}
              />
              <Chip
                icon={<TrendingDownIcon sx={{ fontSize: "0.8rem" }} />}
                label={`${
                  processedData.filter((s) => s.change_percent < 0).length
                } ↓`}
                size="small"
                sx={{
                  bgcolor: `${colors.negative1}20`,
                  color: colors.negative2,
                  fontSize: "0.7rem",
                  height: 24,
                }}
              />
            </Stack>
          </Box>

          {/* Visualization Mode Controls */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <ButtonGroup size="small" variant="outlined">
              <Button
                startIcon={<TreemapIcon />}
                onClick={() => setVisualizationMode("treemap")}
                variant={
                  visualizationMode === "treemap" ? "contained" : "outlined"
                }
                sx={{
                  fontSize: "0.7rem",
                  minWidth: isMobile ? 70 : 90,
                }}
              >
                {isMobile ? "Tree" : "Treemap"}
              </Button>
              <Button
                startIcon={<BubbleIcon />}
                onClick={() => setVisualizationMode("bubble")}
                variant={
                  visualizationMode === "bubble" ? "contained" : "outlined"
                }
                sx={{
                  fontSize: "0.7rem",
                  minWidth: isMobile ? 70 : 90,
                }}
              >
                {isMobile ? "Bubble" : "Bubble"}
              </Button>
              <Button
                startIcon={<BarIcon />}
                onClick={() => setVisualizationMode("bar")}
                variant={visualizationMode === "bar" ? "contained" : "outlined"}
                sx={{
                  fontSize: "0.7rem",
                  minWidth: isMobile ? 60 : 80,
                }}
              >
                Bar
              </Button>
              <Button
                startIcon={<TimelineIcon />}
                onClick={() => setVisualizationMode("timeline")}
                variant={
                  visualizationMode === "timeline" ? "contained" : "outlined"
                }
                sx={{
                  fontSize: "0.7rem",
                  minWidth: isMobile ? 70 : 90,
                }}
              >
                {isMobile ? "Time" : "Timeline"}
              </Button>
            </ButtonGroup>

            <Typography
              variant="caption"
              sx={{
                color: colors.textSecondary,
                fontSize: "0.65rem",
                fontFamily: '"SF Mono", "Consolas", monospace',
              }}
            >
              {visualizationMode.toUpperCase()} VIEW
            </Typography>
          </Box>

          <Divider sx={{ mb: 2, bgcolor: colors.border }} />

          {/* Render Based on Visualization Mode */}
          {visualizationMode === "treemap" && renderTreemapVisualization()}
          {visualizationMode === "bubble" && renderBubbleVisualization()}
          {visualizationMode === "bar" && renderBarVisualization()}
          {visualizationMode === "timeline" && renderTimelineVisualization()}

          {/* Footer Stats */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mt: 2,
              pt: 1.5,
              borderTop: `1px solid ${colors.border}`,
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: colors.textSecondary,
                fontSize: { xs: "0.65rem", sm: "0.7rem" },
                fontFamily: '"SF Mono", "Consolas", monospace',
              }}
            >
              Nested {visualizationMode} • Sectors with stocks • Size by market
              weight
            </Typography>

            <Typography
              variant="caption"
              sx={{
                color: colors.textSecondary,
                fontSize: { xs: "0.65rem", sm: "0.7rem" },
                fontFamily: '"SF Mono", "Consolas", monospace',
              }}
            >
              {processedData.length} sectors •{" "}
              {processedData.reduce(
                (sum, s) => sum + (s.stocks?.length || 0),
                0
              )}{" "}
              stocks
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );

    // Enhanced Treemap Visualization Component with Professional Styling
    function renderTreemapVisualization() {
      return (
        <Box
          sx={{
            position: "relative",
            width: "100%",
            height: fullPage
              ? isLargeScreen
                ? 800
                : isTablet
                ? 600
                : isMobile
                ? 400
                : 700
              : isMobile
              ? 300
              : 500,
            maxWidth: "100%",
            border: `2px solid ${colors.border}`,
            borderRadius: 2,
            overflow: "hidden",
            bgcolor: colors.surface,
            mx: 0,
            boxShadow: fullPage
              ? "none"
              : theme.palette.mode === "dark"
              ? "0 4px 20px rgba(0,0,0,0.3)"
              : "0 4px 20px rgba(0,0,0,0.1)",
          }}
        >
          {sectorTreemapLayout.map((sector, index) => {
            const availableStocks = sector.stocks || [];
            const sectorColor = getPerformanceColor(sector.change_percent);
            const stockLayout = getStockTreemapLayout(
              availableStocks,
              sector.width,
              sector.height
            );

            return (
              <Tooltip
                key={index}
                title={
                  <Box sx={{ p: 1 }}>
                    <Typography
                      variant="subtitle2"
                      sx={{ fontWeight: 700, mb: 1, color: "#ffffff" }}
                    >
                      🏢 {sector.sector_name}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ mb: 0.5, color: "#e0e0e0" }}
                    >
                      📈 Performance:{" "}
                      <strong style={{ color: sectorColor }}>
                        {sector.change_percent >= 0 ? "+" : ""}
                        {sector.change_percent.toFixed(2)}%
                      </strong>
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ mb: 0.5, color: "#e0e0e0" }}
                    >
                      📊 Total Stocks: {sector.stocks_count}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ mb: 0.5, color: "#e0e0e0" }}
                    >
                      ✅ Available: {availableStocks.length}
                    </Typography>
                    <Typography variant="body2" sx={{ color: "#e0e0e0" }}>
                      ⚖️ Market Weight: {sector.market_weight.toFixed(1)}
                    </Typography>
                  </Box>
                }
                arrow
                placement="top"
              >
                <Box
                  sx={{
                    position: "absolute",
                    left: sector.x,
                    top: sector.y,
                    width: sector.width,
                    height: sector.height,
                    bgcolor: `${sectorColor}15`, // Very light background
                    border: `3px solid ${sectorColor}`,
                    borderRadius: 2,
                    cursor: "pointer",
                    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                    overflow: "hidden",
                    boxShadow: `0 2px 8px ${sectorColor}30`,

                    "&:hover": {
                      transform: "scale(1.02)",
                      boxShadow: `0 8px 25px ${sectorColor}60`,
                      zIndex: 15,
                      border: `3px solid ${sectorColor}`,
                      bgcolor: `${sectorColor}25`,
                    },
                  }}
                >
                  {/* Sector Header with Gradient */}
                  <Box
                    sx={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      right: 0,
                      height: 30,
                      background: `linear-gradient(135deg, ${sectorColor}DD, ${sectorColor}AA)`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      px: 1,
                      zIndex: 3,
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: "#ffffff",
                        fontWeight: 800,
                        fontSize: sector.width > 150 ? "0.8rem" : "0.7rem",
                        fontFamily: '"Inter", "Segoe UI", sans-serif',
                        textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                        letterSpacing: "0.5px",
                      }}
                    >
                      {sector.sector_name}
                    </Typography>

                    {sector.width > 120 && (
                      <Typography
                        variant="caption"
                        sx={{
                          color: "#ffffff",
                          fontWeight: 700,
                          fontSize: "0.65rem",
                          fontFamily: '"SF Mono", "Consolas", monospace',
                          textShadow: "0 1px 2px rgba(0,0,0,0.8)",
                          bgcolor: "rgba(255,255,255,0.15)",
                          px: 0.5,
                          borderRadius: 0.5,
                        }}
                      >
                        {sector.change_percent >= 0 ? "+" : ""}
                        {sector.change_percent.toFixed(1)}%
                      </Typography>
                    )}
                  </Box>

                  {/* Main Performance Display */}
                  {sector.width > 140 &&
                    sector.height > 90 &&
                    stockLayout.length === 0 && (
                      <Box
                        sx={{
                          position: "absolute",
                          top: "50%",
                          left: "50%",
                          transform: "translate(-50%, -50%)",
                          textAlign: "center",
                          zIndex: 2,
                        }}
                      >
                        <Typography
                          variant="h4"
                          sx={{
                            color: sectorColor,
                            fontWeight: 900,
                            fontSize: sector.width > 200 ? "2rem" : "1.5rem",
                            fontFamily: '"SF Mono", "Consolas", monospace',
                            textShadow: "0 2px 4px rgba(0,0,0,0.3)",
                            lineHeight: 1,
                          }}
                        >
                          {sector.change_percent >= 0 ? "+" : ""}
                          {sector.change_percent.toFixed(2)}%
                        </Typography>
                      </Box>
                    )}

                  {/* Stock Count Badge */}
                  {sector.width > 80 && (
                    <Box
                      sx={{
                        position: "absolute",
                        bottom: 4,
                        right: 6,
                        bgcolor: "rgba(0,0,0,0.6)",
                        borderRadius: 1,
                        px: 0.5,
                        py: 0.25,
                        zIndex: 3,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          color: "#ffffff",
                          fontSize: "0.65rem",
                          fontWeight: 600,
                          fontFamily: '"SF Mono", "Consolas", monospace',
                        }}
                      >
                        {availableStocks.length}/{sector.stocks_count}
                      </Typography>
                    </Box>
                  )}

                  {/* Enhanced Stock Treemap */}
                  {sector.width > 150 &&
                    sector.height > 100 &&
                    stockLayout.length > 0 && (
                      <Box
                        sx={{
                          position: "absolute",
                          left: 8,
                          right: 8,
                          top: 35,
                          bottom: 30,
                          zIndex: 2,
                        }}
                      >
                        {stockLayout.map((stock, stockIndex) => (
                          <Tooltip
                            key={stockIndex}
                            title={
                              <Box sx={{ p: 0.5 }}>
                                <Typography
                                  variant="subtitle2"
                                  sx={{ fontWeight: 600, mb: 0.5 }}
                                >
                                  {stock.name} ({stock.symbol})
                                </Typography>
                                <Typography variant="body2">
                                  Price: ₹{stock.last_price.toFixed(2)}
                                </Typography>
                                <Typography variant="body2">
                                  Change: {stock.change_percent >= 0 ? "+" : ""}
                                  {stock.change_percent.toFixed(2)}%
                                </Typography>
                                <Typography variant="body2">
                                  Volume: {stock.volume.toLocaleString()}
                                </Typography>
                              </Box>
                            }
                            arrow
                            placement="top"
                          >
                            <Box
                              sx={{
                                position: "absolute",
                                left: stock.x,
                                top: stock.y,
                                width: Math.max(25, stock.width - 2),
                                height: Math.max(20, stock.height - 2),
                                bgcolor: getStockColor(stock.change_percent),
                                border: `2px solid ${getPerformanceColor(
                                  stock.change_percent
                                )}`,
                                borderRadius: 1,
                                cursor: "pointer",
                                transition:
                                  "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                justifyContent: "center",
                                p: 0.5,
                                boxShadow: `0 1px 3px ${getPerformanceColor(
                                  stock.change_percent
                                )}40`,

                                "&:hover": {
                                  transform: "scale(1.08)",
                                  bgcolor: getPerformanceColor(
                                    stock.change_percent
                                  ),
                                  zIndex: 20,
                                  boxShadow: `0 4px 15px ${getPerformanceColor(
                                    stock.change_percent
                                  )}70`,
                                  border: `2px solid #ffffff`,
                                },
                              }}
                            >
                              {/* Stock Symbol */}
                              {stock.width > 35 && stock.height > 25 && (
                                <Typography
                                  variant="caption"
                                  sx={{
                                    color: "#ffffff",
                                    fontSize:
                                      stock.width > 70 ? "0.7rem" : "0.6rem",
                                    fontWeight: 800,
                                    textShadow: "0 1px 2px rgba(0,0,0,0.9)",
                                    lineHeight: 1,
                                    textAlign: "center",
                                    letterSpacing: "0.5px",
                                  }}
                                >
                                  {stock.symbol.substring(
                                    0,
                                    stock.width > 70 ? 6 : 4
                                  )}
                                </Typography>
                              )}

                              {/* Stock Performance */}
                              {stock.width > 50 && stock.height > 40 && (
                                <Typography
                                  variant="caption"
                                  sx={{
                                    color: "#ffffff",
                                    fontSize: "0.5rem",
                                    fontWeight: 700,
                                    textShadow: "0 1px 2px rgba(0,0,0,0.9)",
                                    lineHeight: 1,
                                    mt: 0.3,
                                    fontFamily:
                                      '"SF Mono", "Consolas", monospace',
                                  }}
                                >
                                  {stock.change_percent >= 0 ? "+" : ""}
                                  {stock.change_percent.toFixed(1)}%
                                </Typography>
                              )}
                            </Box>
                          </Tooltip>
                        ))}
                      </Box>
                    )}
                </Box>
              </Tooltip>
            );
          })}
        </Box>
      );
    }

    // Bubble Visualization Component
    function renderBubbleVisualization() {
      return (
        <Box
          sx={{
            position: "relative",
            width: "100%",
            height: fullPage
              ? isLargeScreen
                ? 800
                : isTablet
                ? 600
                : isMobile
                ? 400
                : 700
              : isMobile
              ? 300
              : 500,
            maxWidth: "100%",
            border: `1px solid ${colors.border}`,
            borderRadius: 1,
            overflow: "hidden",
            bgcolor: colors.surface,
            mx: 0,
          }}
        >
          {sectorBubbleLayout.map((sector, index) => {
            const availableStocks = sector.stocks || [];
            const sectorColor = getPerformanceColor(sector.change_percent);
            const stockBubbles = getStockBubbleLayout(
              availableStocks,
              sector.radius
            );

            return (
              <Box key={index}>
                {/* Sector Bubble */}
                <Tooltip
                  title={
                    <Box>
                      <Typography
                        variant="subtitle2"
                        sx={{ fontWeight: 600, mb: 0.5 }}
                      >
                        {sector.sector_name}
                      </Typography>
                      <Typography variant="body2">
                        Performance: {sector.change_percent >= 0 ? "+" : ""}
                        {sector.change_percent.toFixed(2)}%
                      </Typography>
                      <Typography variant="body2">
                        Stocks: {sector.stocks_count}
                      </Typography>
                    </Box>
                  }
                  arrow
                >
                  <Box
                    sx={{
                      position: "absolute",
                      left: sector.x - sector.radius,
                      top: sector.y - sector.radius,
                      width: sector.radius * 2,
                      height: sector.radius * 2,
                      borderRadius: "50%",
                      bgcolor: `${sectorColor}40`,
                      border: `3px solid ${sectorColor}`,
                      cursor: "pointer",
                      transition: "all 0.3s ease",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",

                      "&:hover": {
                        transform: "scale(1.05)",
                        boxShadow: `0 8px 20px ${sectorColor}60`,
                        zIndex: 20,
                      },
                    }}
                  >
                    {/* Sector Name */}
                    <Typography
                      variant="caption"
                      sx={{
                        color: colors.text,
                        fontWeight: 700,
                        fontSize: sector.radius > 60 ? "0.8rem" : "0.65rem",
                        textAlign: "center",
                        lineHeight: 1.1,
                        mb: 0.5,
                        textShadow: "0 1px 2px rgba(0,0,0,0.3)",
                      }}
                    >
                      {sector.sector_name}
                    </Typography>

                    {/* Performance */}
                    <Typography
                      variant="body2"
                      sx={{
                        color: sectorColor,
                        fontWeight: 700,
                        fontSize: sector.radius > 60 ? "0.9rem" : "0.7rem",
                        fontFamily: '"SF Mono", "Consolas", monospace',
                        textAlign: "center",
                      }}
                    >
                      {sector.change_percent >= 0 ? "+" : ""}
                      {sector.change_percent.toFixed(1)}%
                    </Typography>
                  </Box>
                </Tooltip>

                {/* Stock Bubbles inside Sector */}
                {sector.radius > 80 &&
                  stockBubbles.map((stock, stockIndex) => (
                    <Tooltip
                      key={stockIndex}
                      title={`${stock.symbol}: ${
                        stock.change_percent >= 0 ? "+" : ""
                      }${stock.change_percent.toFixed(2)}% | ₹${
                        stock.last_price
                      }`}
                      arrow
                    >
                      <Box
                        sx={{
                          position: "absolute",
                          left:
                            sector.x -
                            sector.radius * 0.8 +
                            stock.x -
                            stock.radius,
                          top:
                            sector.y -
                            sector.radius * 0.8 +
                            stock.y -
                            stock.radius,
                          width: stock.radius * 2,
                          height: stock.radius * 2,
                          borderRadius: "50%",
                          bgcolor: getStockColor(stock.change_percent),
                          border: `1px solid ${getPerformanceColor(
                            stock.change_percent
                          )}`,
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          justifyContent: "center",

                          "&:hover": {
                            transform: "scale(1.2)",
                            zIndex: 25,
                            boxShadow: `0 4px 12px ${getPerformanceColor(
                              stock.change_percent
                            )}80`,
                          },
                        }}
                      >
                        {stock.radius > 15 && (
                          <Typography
                            variant="caption"
                            sx={{
                              color: "#ffffff",
                              fontSize: stock.radius > 25 ? "0.6rem" : "0.5rem",
                              fontWeight: 600,
                              textAlign: "center",
                              textShadow: "0 1px 1px rgba(0,0,0,0.8)",
                            }}
                          >
                            {stock.symbol.substring(
                              0,
                              stock.radius > 25 ? 4 : 3
                            )}
                          </Typography>
                        )}
                      </Box>
                    </Tooltip>
                  ))}
              </Box>
            );
          })}
        </Box>
      );
    }

    // Bar Chart Visualization Component
    function renderBarVisualization() {
      const sortedSectors = [...processedData].sort(
        (a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent)
      );
      const maxChange = Math.max(
        ...sortedSectors.map((s) => Math.abs(s.change_percent))
      );
      const containerHeight = isMobile ? 400 : 600;
      const barHeight = Math.max(
        25,
        (containerHeight - 100) / sortedSectors.length
      );

      return (
        <Box
          sx={{
            width: "100%",
            height: containerHeight,
            maxWidth: "100%",
            border: `1px solid ${colors.border}`,
            borderRadius: 1,
            overflow: "auto",
            bgcolor: colors.surface,
            mx: 0,
            p: 2,
          }}
        >
          {sortedSectors.map((sector, index) => {
            const barWidth =
              maxChange > 0
                ? (Math.abs(sector.change_percent) / maxChange) * 70
                : 0;
            const sectorColor = getPerformanceColor(sector.change_percent);
            const availableStocks = sector.stocks || [];

            return (
              <Box
                key={index}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  mb: 1,
                  height: barHeight,
                  position: "relative",
                }}
              >
                {/* Sector Name */}
                <Box sx={{ width: "25%", pr: 1 }}>
                  <Typography
                    variant="caption"
                    sx={{
                      color: colors.text,
                      fontSize: "0.75rem",
                      fontWeight: 600,
                    }}
                  >
                    {sector.sector_name}
                  </Typography>
                </Box>

                {/* Bar */}
                <Box sx={{ width: "70%", position: "relative" }}>
                  <Tooltip
                    title={
                      <Box>
                        <Typography variant="subtitle2">
                          {sector.sector_name}
                        </Typography>
                        <Typography variant="body2">
                          Performance: {sector.change_percent >= 0 ? "+" : ""}
                          {sector.change_percent.toFixed(2)}%
                        </Typography>
                        <Typography variant="body2">
                          Stocks: {sector.stocks_count}
                        </Typography>
                        <Typography variant="body2">
                          Available: {availableStocks.length}
                        </Typography>
                      </Box>
                    }
                    arrow
                  >
                    <Box
                      sx={{
                        width: `${barWidth}%`,
                        height: barHeight - 4,
                        bgcolor: sectorColor,
                        borderRadius: 0.5,
                        cursor: "pointer",
                        transition: "all 0.2s ease",
                        position: "relative",

                        "&:hover": {
                          transform: "scaleX(1.02)",
                          boxShadow: `0 2px 8px ${sectorColor}60`,
                        },
                      }}
                    >
                      {/* Stock indicators inside bar */}
                      {barWidth > 10 &&
                        availableStocks.slice(0, 5).map((stock, stockIndex) => (
                          <Box
                            key={stockIndex}
                            sx={{
                              position: "absolute",
                              left: `${(stockIndex / 5) * 80}%`,
                              top: 2,
                              bottom: 2,
                              width: "12%",
                              bgcolor: getStockColor(stock.change_percent),
                              borderRadius: 0.25,
                              border: `1px solid ${getPerformanceColor(
                                stock.change_percent
                              )}`,
                            }}
                          />
                        ))}
                    </Box>
                  </Tooltip>
                </Box>

                {/* Value */}
                <Box sx={{ width: "5%", textAlign: "right" }}>
                  <Typography
                    variant="caption"
                    sx={{
                      color: sectorColor,
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      fontFamily: '"SF Mono", "Consolas", monospace',
                    }}
                  >
                    {sector.change_percent >= 0 ? "+" : ""}
                    {sector.change_percent.toFixed(1)}%
                  </Typography>
                </Box>
              </Box>
            );
          })}
        </Box>
      );
    }

    // Timeline Visualization Component
    function renderTimelineVisualization() {
      const sortedSectors = [...processedData].sort(
        (a, b) => b.change_percent - a.change_percent
      );
      const containerHeight = isMobile ? 400 : 600;

      return (
        <Box
          sx={{
            width: "100%",
            height: containerHeight,
            maxWidth: "100%",
            border: `1px solid ${colors.border}`,
            borderRadius: 1,
            overflow: "auto",
            bgcolor: colors.surface,
            mx: 0,
            p: 2,
            position: "relative",
          }}
        >
          {/* Timeline axis */}
          <Box
            sx={{
              position: "absolute",
              left: "50%",
              top: 20,
              bottom: 20,
              width: "2px",
              bgcolor: colors.border,
              transform: "translateX(-50%)",
            }}
          />

          {sortedSectors.map((sector, index) => {
            const isLeft = index % 2 === 0;
            const sectorColor = getPerformanceColor(sector.change_percent);
            const availableStocks = sector.stocks || [];
            const yPosition = 40 + index * 80;

            return (
              <Box
                key={index}
                sx={{
                  position: "absolute",
                  top: yPosition,
                  [isLeft ? "right" : "left"]: "52%",
                  width: "45%",
                  display: "flex",
                  alignItems: "center",
                  [isLeft ? "flexDirection" : "flexDirection"]: isLeft
                    ? "row"
                    : "row-reverse",
                }}
              >
                {/* Timeline dot */}
                <Box
                  sx={{
                    position: "absolute",
                    [isLeft ? "right" : "left"]: "-6px",
                    width: "12px",
                    height: "12px",
                    borderRadius: "50%",
                    bgcolor: sectorColor,
                    border: `2px solid ${colors.surface}`,
                    zIndex: 2,
                  }}
                />

                {/* Sector card */}
                <Tooltip
                  title={
                    <Box>
                      <Typography variant="subtitle2">
                        {sector.sector_name}
                      </Typography>
                      <Typography variant="body2">
                        Performance: {sector.change_percent >= 0 ? "+" : ""}
                        {sector.change_percent.toFixed(2)}%
                      </Typography>
                      <Typography variant="body2">
                        Stocks: {sector.stocks_count}
                      </Typography>
                    </Box>
                  }
                  arrow
                >
                  <Paper
                    sx={{
                      p: 1.5,
                      bgcolor: colors.background,
                      border: `2px solid ${sectorColor}`,
                      borderRadius: 1,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                      width: "100%",

                      "&:hover": {
                        transform: "scale(1.02)",
                        boxShadow: `0 4px 12px ${sectorColor}40`,
                      },
                    }}
                  >
                    <Typography
                      variant="subtitle2"
                      sx={{
                        color: colors.text,
                        fontWeight: 600,
                        mb: 0.5,
                      }}
                    >
                      {sector.sector_name}
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{
                        color: sectorColor,
                        fontWeight: 700,
                        fontFamily: '"SF Mono", "Consolas", monospace',
                        mb: 1,
                      }}
                    >
                      {sector.change_percent >= 0 ? "+" : ""}
                      {sector.change_percent.toFixed(2)}%
                    </Typography>

                    {/* Top stocks in sector */}
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {availableStocks.slice(0, 3).map((stock, stockIndex) => (
                        <Chip
                          key={stockIndex}
                          label={`${stock.symbol} ${
                            stock.change_percent >= 0 ? "+" : ""
                          }${stock.change_percent.toFixed(1)}%`}
                          size="small"
                          sx={{
                            fontSize: "0.6rem",
                            height: 20,
                            bgcolor: `${getStockColor(stock.change_percent)}40`,
                            color: getPerformanceColor(stock.change_percent),
                            border: `1px solid ${getPerformanceColor(
                              stock.change_percent
                            )}60`,
                          }}
                        />
                      ))}
                    </Box>
                  </Paper>
                </Tooltip>
              </Box>
            );
          })}
        </Box>
      );
    }
  }
);

FinancialHeatmap.displayName = "FinancialHeatmap";

export default FinancialHeatmap;
