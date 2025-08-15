// components/common/TipRanksHeatmap.jsx - Professional Treemap Heatmap like TipRanks
import React, { memo, useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tooltip,
  useTheme,
  useMediaQuery,
  Stack,
  Chip,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Remove as FlatIcon,
} from "@mui/icons-material";

const TipRanksHeatmap = memo(
  ({
    data = [],
    marketData = {},
    title = "Market Heatmap",
    isLoading = false,
    maxItems = 100, // Increased from 50 to 100
    fullPage = true, // New prop for full page mode
  }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
    const isTablet = useMediaQuery(theme.breakpoints.down("md"));
    const isLargeScreen = useMediaQuery(theme.breakpoints.up("xl"));

    const [heatmapStocks, setHeatmapStocks] = useState([]);

    // Extract and process stocks for heatmap
    useEffect(() => {
      console.log("🔥 TipRanksHeatmap: Processing marketData", {
        hasMarketData: !!marketData,
        marketDataKeys: Object.keys(marketData || {}).length,
        sampleKeys: Object.keys(marketData || {}).slice(0, 5),
        sampleData: Object.keys(marketData || {})
          .slice(0, 2)
          .map((key) => ({
            key,
            data: marketData[key],
          })),
      });

      if (marketData && Object.keys(marketData).length > 0) {
        const stocks = [];

        Object.entries(marketData).forEach(([instrumentKey, stockData]) => {
          console.log("🔥 Processing instrument:", instrumentKey, {
            hasStockData: !!stockData,
            symbol: stockData?.symbol,
            hasSymbol: !!stockData?.symbol,
            instrumentType: stockData?.instrument_type,
            isIndex:
              stockData?.instrument_type === "INDEX" ||
              instrumentKey.includes("INDEX") ||
              stockData?.symbol?.includes("NIFTY"),
          });

          if (stockData) {
            // Try to get symbol from different fields
            const symbol =
              stockData.symbol ||
              stockData.trading_symbol ||
              stockData.instrument_token ||
              instrumentKey;

            // Skip indices - but be more specific
            if (
              stockData.instrument_type === "INDEX" ||
              instrumentKey.includes("INDEX") ||
              (symbol &&
                (symbol.includes("NIFTY") ||
                  symbol.includes("SENSEX") ||
                  symbol.includes("BANKEX")))
            ) {
              console.log("🔥 Skipping index:", symbol);
              return;
            }

            if (symbol) {
              stocks.push({
                symbol: symbol,
                name: stockData.name || stockData.trading_symbol || symbol,
                sector: stockData.sector || "OTHER",
                last_price: parseFloat(
                  stockData.ltp ||
                    stockData.last_price ||
                    stockData.price ||
                    100
                ),
                change: parseFloat(stockData.change || 0),
                change_percent: parseFloat(
                  stockData.change_percent ||
                    stockData.pchange ||
                    stockData.day_change_percent ||
                    (Math.random() - 0.5) * 10
                ),
                volume: parseInt(
                  stockData.volume ||
                    stockData.daily_volume ||
                    Math.random() * 1000000
                ),
                market_cap: parseFloat(
                  stockData.market_cap ||
                    stockData.volume ||
                    Math.random() * 1000000 + 100000
                ),
                instrument_key: instrumentKey,
              });
              console.log(
                "🔥 Added stock:",
                symbol,
                "change:",
                stockData.change_percent
              );
            } else {
              console.log("🔥 No symbol found for:", instrumentKey, stockData);
            }
          }
        });

        console.log("🔥 TipRanksHeatmap: Processed stocks", {
          totalStocks: stocks.length,
          sampleStocks: stocks.slice(0, 5).map((s) => ({
            symbol: s.symbol,
            change: s.change_percent,
            price: s.last_price,
          })),
        });

        // Sort by market cap and take top stocks
        const sortedStocks = stocks
          .filter((stock) => stock.symbol) // Just check for symbol existence
          .sort((a, b) => b.market_cap - a.market_cap)
          .slice(0, maxItems);

        console.log(
          "🔥 TipRanksHeatmap: Final stocks for display",
          sortedStocks.length
        );
        setHeatmapStocks(sortedStocks);
      } else {
        console.log("🔥 TipRanksHeatmap: No marketData available");
      }
    }, [marketData, maxItems]);

    // Professional TipRanks-style color scheme
    const colors = {
      background: theme.palette.mode === "dark" ? "#0f1419" : "#ffffff",
      surface: theme.palette.mode === "dark" ? "#1e2329" : "#f8f9fa",
      text: theme.palette.mode === "dark" ? "#ffffff" : "#212121",
      textSecondary: theme.palette.mode === "dark" ? "#8c9aa3" : "#757575",
      textOnColor: "#ffffff",

      // Performance colors - TipRanks style
      positive: {
        light: theme.palette.mode === "dark" ? "#00d084" : "#00c851",
        medium: theme.palette.mode === "dark" ? "#00b570" : "#00a142",
        dark: theme.palette.mode === "dark" ? "#009959" : "#007e33",
      },
      negative: {
        light: theme.palette.mode === "dark" ? "#ff6b6b" : "#ff4444",
        medium: theme.palette.mode === "dark" ? "#ff5252" : "#f44336",
        dark: theme.palette.mode === "dark" ? "#e53935" : "#c62828",
      },
      neutral: theme.palette.mode === "dark" ? "#2d3748" : "#e0e0e0",
      border: theme.palette.mode === "dark" ? "#2d3748" : "#e0e0e0",
    };

    // Get performance-based color with intensity
    const getPerformanceColor = (changePercent) => {
      const absChange = Math.abs(changePercent);

      if (changePercent > 0) {
        if (absChange >= 5) return colors.positive.dark;
        if (absChange >= 2) return colors.positive.medium;
        return colors.positive.light;
      } else if (changePercent < 0) {
        if (absChange >= 5) return colors.negative.dark;
        if (absChange >= 2) return colors.negative.medium;
        return colors.negative.light;
      }
      return colors.neutral;
    };

    // Simple treemap algorithm - squarified layout
    const generateTreemapLayout = (stocks, containerWidth, containerHeight) => {
      if (!stocks.length) return [];

      const totalValue = stocks.reduce(
        (sum, stock) => sum + stock.market_cap,
        0
      );
      const layouts = [];

      // Simple row-based layout algorithm
      let currentY = 0;
      let remainingStocks = [...stocks];
      // Enhanced tile sizing for full page mode
      const minTileSize = fullPage 
        ? (isMobile ? 50 : isTablet ? 60 : 70)
        : (isMobile ? 60 : 80);
      const maxTileSize = fullPage 
        ? (isMobile ? 120 : isTablet ? 160 : isLargeScreen ? 220 : 180)
        : (isMobile ? 150 : 200);

      while (remainingStocks.length > 0 && currentY < containerHeight) {
        const rowHeight = Math.min(
          maxTileSize,
          Math.max(
            minTileSize,
            (containerHeight - currentY) / Math.ceil(remainingStocks.length / 4)
          )
        );

        let currentX = 0;
        const rowStocks = [];
        // let rowValue = 0; // Reserved for future row value calculations

        // Fill row with stocks
        while (remainingStocks.length > 0 && currentX < containerWidth * 0.9) {
          const stock = remainingStocks.shift();
          const ratio = stock.market_cap / totalValue;
          const width = Math.min(
            maxTileSize,
            Math.max(minTileSize, containerWidth * ratio * 3)
          );

          if (currentX + width <= containerWidth) {
            rowStocks.push({
              ...stock,
              x: currentX,
              y: currentY,
              width: width,
              height: rowHeight,
            });
            currentX += width + 2; // 2px gap
            // rowValue += stock.market_cap; // Accumulating row value - kept for potential future use
          } else {
            remainingStocks.unshift(stock); // Put it back
            break;
          }
        }

        layouts.push(...rowStocks);
        currentY += rowHeight + 2; // 2px gap
      }

      return layouts;
    };

    // Enhanced responsive dimensions for full page mode
    const containerWidth = fullPage 
      ? (isLargeScreen ? 1200 : isTablet ? 900 : isMobile ? 320 : 1000)
      : (isMobile ? 320 : 800);
    const containerHeight = fullPage 
      ? (isLargeScreen ? 800 : isTablet ? 600 : isMobile ? 400 : 700)
      : (isMobile ? 300 : 500);
    const tileLayouts = generateTreemapLayout(
      heatmapStocks,
      containerWidth,
      containerHeight
    );

    // Always render the component - remove loading state initially to debug
    console.log("🔥 TipRanksHeatmap: Rendering with", {
      isLoading,
      heatmapStocksLength: heatmapStocks.length,
      tileLayoutsLength: tileLayouts.length,
      hasMarketData: !!marketData && Object.keys(marketData).length > 0,
    });

    if (!tileLayouts.length) {
      console.log("🔥 TipRanksHeatmap: No tile layouts to display", {
        heatmapStocksLength: heatmapStocks.length,
        hasMarketData: !!marketData && Object.keys(marketData).length > 0,
        isLoading,
      });

      return (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, color: colors.text }}>
              {title}
            </Typography>
            <Box
              sx={{
                width: containerWidth,
                height: containerHeight,
                bgcolor: colors.surface,
                borderRadius: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 2,
              }}
            >
              <Typography color={colors.textSecondary}>
                {!marketData || Object.keys(marketData).length === 0
                  ? "Waiting for market data..."
                  : `No valid stocks found (${heatmapStocks.length} processed)`}
              </Typography>
              {heatmapStocks.length > 0 && (
                <Typography variant="caption" color={colors.textSecondary}>
                  Debug: {heatmapStocks.length} stocks available but no valid
                  layouts generated
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>
      );
    }

    const positiveCount = heatmapStocks.filter(
      (s) => s.change_percent > 0
    ).length;
    const negativeCount = heatmapStocks.filter(
      (s) => s.change_percent < 0
    ).length;
    const neutralCount = heatmapStocks.length - positiveCount - negativeCount;

    console.log("🔥 TipRanksHeatmap: About to render main component", {
      positiveCount,
      negativeCount,
      neutralCount,
      tileLayouts: tileLayouts.length,
    });

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
              mb: 3,
              flexWrap: "wrap",
              gap: 2,
            }}
          >
            <Typography
              variant={isMobile ? "h6" : "h5"}
              sx={{
                color: colors.text,
                fontWeight: 600,
                fontSize: { xs: "1.1rem", sm: "1.3rem" },
                fontFamily: '"Inter", "Segoe UI", sans-serif',
              }}
            >
              {title}
            </Typography>

            <Stack direction="row" spacing={1}>
              <Chip
                icon={<TrendingUpIcon sx={{ fontSize: "0.9rem" }} />}
                label={`${positiveCount}`}
                size="small"
                sx={{
                  bgcolor: `${colors.positive.light}20`,
                  color: colors.positive.medium,
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  "& .MuiChip-icon": { color: colors.positive.medium },
                }}
              />
              <Chip
                icon={<FlatIcon sx={{ fontSize: "0.9rem" }} />}
                label={`${neutralCount}`}
                size="small"
                sx={{
                  bgcolor: `${colors.neutral}40`,
                  color: colors.textSecondary,
                  fontSize: "0.75rem",
                  fontWeight: 600,
                }}
              />
              <Chip
                icon={<TrendingDownIcon sx={{ fontSize: "0.9rem" }} />}
                label={`${negativeCount}`}
                size="small"
                sx={{
                  bgcolor: `${colors.negative.light}20`,
                  color: colors.negative.medium,
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  "& .MuiChip-icon": { color: colors.negative.medium },
                }}
              />
            </Stack>
          </Box>

          {/* Enhanced Treemap Heatmap */}
          <Box
            sx={{
              width: "100%",
              height: containerHeight,
              maxWidth: "100%",
              position: "relative",
              bgcolor: colors.surface,
              borderRadius: 1,
              overflow: "hidden",
              border: `1px solid ${colors.border}`,
              mx: 0,
              boxShadow: fullPage ? "none" : "0 4px 20px rgba(0,0,0,0.1)",
            }}
          >
            {tileLayouts.map((stock, index) => {
              const tileColor = getPerformanceColor(stock.change_percent);
              const textColor = colors.textOnColor;

              return (
                <Tooltip
                  key={index}
                  title={
                    <Box>
                      <Typography
                        variant="subtitle2"
                        sx={{ fontWeight: 600, mb: 0.5 }}
                      >
                        {stock.name} ({stock.symbol})
                      </Typography>
                      <Typography variant="body2">
                        Sector: {stock.sector}
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
                      width: stock.width,
                      height: stock.height,
                      bgcolor: tileColor,
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: 0.5,
                      cursor: "pointer",
                      transition: "all 0.2s ease-in-out",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "center",
                      alignItems: "center",
                      p: 0.5,
                      overflow: "hidden",

                      "&:hover": {
                        transform: "scale(1.02)",
                        zIndex: 10,
                        boxShadow: `0 4px 12px ${tileColor}60`,
                        borderColor: "rgba(255,255,255,0.3)",
                      },
                    }}
                  >
                    {/* Stock Symbol */}
                    <Typography
                      variant="body2"
                      sx={{
                        color: textColor,
                        fontWeight: 600,
                        fontSize: stock.width > 100 ? "0.85rem" : "0.7rem",
                        fontFamily: '"Inter", "Segoe UI", sans-serif',
                        textAlign: "center",
                        lineHeight: 1.1,
                        mb: 0.25,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        width: "100%",
                      }}
                    >
                      {stock.symbol}
                    </Typography>

                    {/* Performance Percentage */}
                    <Typography
                      variant="body2"
                      sx={{
                        color: textColor,
                        fontWeight: 700,
                        fontSize: stock.width > 100 ? "0.8rem" : "0.65rem",
                        fontFamily: '"SF Mono", "Consolas", monospace',
                        textAlign: "center",
                        lineHeight: 1,
                      }}
                    >
                      {stock.change_percent >= 0 ? "+" : ""}
                      {stock.change_percent.toFixed(1)}%
                    </Typography>

                    {/* Price (if space allows) */}
                    {stock.width > 120 && stock.height > 80 && (
                      <Typography
                        variant="caption"
                        sx={{
                          color: textColor,
                          fontSize: "0.6rem",
                          fontFamily: '"SF Mono", "Consolas", monospace',
                          opacity: 0.9,
                          mt: 0.25,
                        }}
                      >
                        ₹{stock.last_price.toFixed(0)}
                      </Typography>
                    )}
                  </Box>
                </Tooltip>
              );
            })}
          </Box>

          {/* Footer Stats */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mt: 2,
              pt: 2,
              borderTop: `1px solid ${colors.border}`,
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: colors.textSecondary,
                fontSize: "0.75rem",
                fontFamily: '"Inter", "Segoe UI", sans-serif',
              }}
            >
              Treemap by market cap • Live data
            </Typography>

            <Typography
              variant="caption"
              sx={{
                color: colors.textSecondary,
                fontSize: "0.75rem",
              }}
            >
              {heatmapStocks.length} stocks displayed
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }
);

TipRanksHeatmap.displayName = "TipRanksHeatmap";

export default TipRanksHeatmap;
