// components/common/Heatmap.jsx - Advanced Sector Heatmap with Analytics
import React, { memo, useMemo, useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Chip,
  Tooltip,
  useTheme,
  useMediaQuery,
  Stack,
  Collapse,
  IconButton,
  LinearProgress,
  Badge,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  VolumeUp as VolumeIcon,
  ShowChart as PerformanceIcon,
} from "@mui/icons-material";

const Heatmap = memo(
  ({
    data = [],
    marketData = {}, // Add marketData prop to get individual stocks
    title = "🔥 SECTOR HEATMAP",
    isLoading = false,
    maxItems = 20,
    compact = false,
  }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
    const isTablet = useMediaQuery(theme.breakpoints.down("md"));
    
    const [expandedSectors, setExpandedSectors] = useState(new Set());
    const [sectorStocks, setSectorStocks] = useState({});

    // Extract individual stocks from marketData and organize by sector
    useEffect(() => {
      if (marketData && Object.keys(marketData).length > 0) {
        const stocksBySector = {};
        
        Object.entries(marketData).forEach(([instrumentKey, stockData]) => {
          if (stockData && stockData.sector && stockData.symbol) {
            const sector = stockData.sector;
            if (!stocksBySector[sector]) {
              stocksBySector[sector] = [];
            }
            
            stocksBySector[sector].push({
              symbol: stockData.symbol,
              name: stockData.name || stockData.symbol,
              trading_symbol: stockData.trading_symbol || stockData.symbol,
              last_price: stockData.ltp || stockData.last_price || 0,
              change: stockData.change || 0,
              change_percent: stockData.change_percent || stockData.pchange || 0,
              volume: stockData.volume || stockData.daily_volume || 0,
              high: stockData.high || 0,
              low: stockData.low || 0,
              open: stockData.open || 0,
              close: stockData.close || stockData.cp || 0,
              instrument_key: instrumentKey,
              exchange: stockData.exchange || "NSE",
              instrument_type: stockData.instrument_type || "EQ",
            });
          }
        });
        
        // Sort stocks within each sector by performance
        Object.keys(stocksBySector).forEach(sector => {
          stocksBySector[sector].sort((a, b) => 
            Math.abs(b.change_percent) - Math.abs(a.change_percent)
          );
        });
        
        setSectorStocks(stocksBySector);
      }
    }, [marketData]);

    // Professional color scheme
    const colors = {
      background: theme.palette.mode === "dark" ? "#0a0e1a" : "#ffffff",
      surface: theme.palette.mode === "dark" ? "#1e293b" : "#f8f9fa",
      text: theme.palette.mode === "dark" ? "#e2e8f0" : "#1e293b",
      textSecondary: theme.palette.mode === "dark" ? "#94a3b8" : "#64748b",
      positive: theme.palette.mode === "dark" ? "#22c55e" : "#16a34a",
      negative: theme.palette.mode === "dark" ? "#ef4444" : "#dc2626",
      neutral: theme.palette.mode === "dark" ? "#f59e0b" : "#d97706",
      primary: theme.palette.mode === "dark" ? "#3b82f6" : "#2563eb",
      accent: theme.palette.mode === "dark" ? "#06b6d4" : "#0891b2",
      border: theme.palette.mode === "dark" ? "#475569" : "#e2e8f0",
      cardBackground: theme.palette.mode === "dark" ? "#1e293b" : "#ffffff",
    };

    // Process and sort data
    const processedData = useMemo(() => {
      if (!data || !Array.isArray(data)) return [];
      
      return data
        .slice(0, maxItems)
        .map((sector) => ({
          ...sector,
          sector_name: sector.sector || sector.sector_name || "UNKNOWN",
          change_percent: parseFloat(sector.avg_change_percent || sector.change_percent || 0),
          strength: parseFloat(sector.strength_score || 0),
          advancing: parseInt(sector.advancing || 0),
          declining: parseInt(sector.declining || 0),
          stocks_count: parseInt(sector.stocks_count || sector.total_stocks || 0),
          stocks: sector.stocks || [],
          top_performer: sector.top_performer || null,
          worst_performer: sector.worst_performer || null,
        }))
        .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent));
    }, [data, maxItems]);

    // Calculate intensity for color mapping
    const getIntensity = (changePercent) => {
      const maxChange = Math.max(...processedData.map(s => Math.abs(s.change_percent)));
      if (maxChange === 0) return 0;
      return Math.abs(changePercent) / maxChange;
    };

    // Get color based on performance
    const getTileColor = (changePercent, intensity = 0.5) => {
      const alpha = Math.max(0.15, Math.min(0.4, intensity));
      if (changePercent > 0) {
        return `${colors.positive}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`;
      } else if (changePercent < 0) {
        return `${colors.negative}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`;
      } else {
        return `${colors.neutral}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`;
      }
    };

    // Get border color
    const getBorderColor = (changePercent) => {
      if (changePercent > 0) return colors.positive;
      if (changePercent < 0) return colors.negative;
      return colors.neutral;
    };

    // Get stock color based on its performance
    const getStockColor = (changePercent) => {
      const intensity = Math.min(0.8, Math.abs(changePercent) / 10); // Scale by 10% max
      if (changePercent > 0) {
        return `${colors.positive}${Math.floor(intensity * 255).toString(16).padStart(2, '0')}`;
      } else if (changePercent < 0) {
        return `${colors.negative}${Math.floor(intensity * 255).toString(16).padStart(2, '0')}`;
      } else {
        return `${colors.neutral}20`;
      }
    };

    // Toggle sector expansion
    const toggleSector = (sectorName) => {
      const newExpanded = new Set(expandedSectors);
      if (newExpanded.has(sectorName)) {
        newExpanded.delete(sectorName);
      } else {
        newExpanded.add(sectorName);
      }
      setExpandedSectors(newExpanded);
    };

    if (isLoading) {
      return (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              {title}
            </Typography>
            <Grid container spacing={1}>
              {[...Array(isMobile ? 2 : 4)].map((_, i) => (
                <Grid item xs={12} sm={6} md={4} lg={3} key={i}>
                  <Paper
                    sx={{
                      height: 120,
                      bgcolor: colors.surface,
                      borderRadius: 2,
                      animation: "pulse 1.5s ease-in-out infinite",
                      "@keyframes pulse": {
                        "0%, 100%": { opacity: 1 },
                        "50%": { opacity: 0.5 },
                      },
                    }}
                  />
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      );
    }

    if (!processedData.length) {
      return (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, color: colors.primary }}>
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
          mb: 2,
          bgcolor: colors.cardBackground,
          border: `1px solid ${colors.border}`,
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <CardContent sx={{ p: { xs: 1.5, sm: 2 } }}>
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
                color: colors.primary,
                fontWeight: 700,
                fontSize: { xs: "1rem", sm: "1.25rem" },
                fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
              }}
            >
              {title} ({processedData.length})
            </Typography>
            
            <Stack direction="row" spacing={1}>
              <Chip
                icon={<TrendingUpIcon sx={{ fontSize: "0.8rem" }} />}
                label={`${processedData.filter(s => s.change_percent > 0).length} ↑`}
                size="small"
                sx={{
                  bgcolor: `${colors.positive}20`,
                  color: colors.positive,
                  fontSize: "0.7rem",
                  height: 24,
                }}
              />
              <Chip
                icon={<TrendingDownIcon sx={{ fontSize: "0.8rem" }} />}
                label={`${processedData.filter(s => s.change_percent < 0).length} ↓`}
                size="small"
                sx={{
                  bgcolor: `${colors.negative}20`,
                  color: colors.negative,
                  fontSize: "0.7rem",
                  height: 24,
                }}
              />
            </Stack>
          </Box>

          {/* Sector Tiles Grid */}
          <Grid container spacing={{ xs: 1, sm: 1.5, md: 2 }}>
            {processedData.map((sector, index) => {
              const intensity = getIntensity(sector.change_percent);
              const tileColor = getTileColor(sector.change_percent, intensity);
              const borderColor = getBorderColor(sector.change_percent);
              const isExpanded = expandedSectors.has(sector.sector_name);
              
              // Get stocks for this sector from marketData
              const availableStocks = sectorStocks[sector.sector_name] || [];
              const topStocks = availableStocks.slice(0, isMobile ? 4 : 8);
              
              // Calculate volume weighted performance for better heatmap
              const totalVolume = availableStocks.reduce((sum, stock) => sum + stock.volume, 0);
              const volumeWeightedChange = totalVolume > 0 ? 
                availableStocks.reduce((sum, stock) => 
                  sum + (stock.change_percent * stock.volume / totalVolume), 0
                ) : sector.change_percent;

              return (
                <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
                  <Paper
                    sx={{
                      bgcolor: tileColor,
                      border: `2px solid ${borderColor}`,
                      borderRadius: 3,
                      transition: "all 0.2s ease-in-out",
                      position: "relative",
                      overflow: "hidden",
                      
                      "&:hover": {
                        transform: "translateY(-2px)",
                        boxShadow: `0 8px 25px ${borderColor}30`,
                        borderColor: borderColor,
                      },
                    }}
                  >
                    {/* Sector Header */}
                    <Box
                      sx={{
                        p: { xs: 1.5, sm: 2 },
                        borderBottom: `1px solid ${colors.border}50`,
                        position: "relative",
                        cursor: "pointer",
                      }}
                      onClick={() => toggleSector(sector.sector_name)}
                    >
                      {/* Top accent line */}
                      <Box
                        sx={{
                          position: "absolute",
                          top: 0,
                          left: 0,
                          right: 0,
                          height: 4,
                          bgcolor: borderColor,
                        }}
                      />

                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          mb: 1,
                        }}
                      >
                        <Typography
                          variant="subtitle1"
                          sx={{
                            fontWeight: 700,
                            color: colors.text,
                            fontSize: { xs: "0.9rem", sm: "1rem" },
                            fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
                          }}
                        >
                          {sector.sector_name}
                        </Typography>
                        
                        <IconButton
                          size="small"
                          sx={{ color: colors.textSecondary, p: 0 }}
                        >
                          {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </Box>

                      {/* Sector Performance */}
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          mb: 1,
                        }}
                      >
                        <Box>
                          <Typography
                            variant="h5"
                            sx={{
                              color: borderColor,
                              fontWeight: 700,
                              fontSize: { xs: "1.1rem", sm: "1.3rem" },
                              fontFamily: '"SF Mono", "Consolas", monospace',
                              lineHeight: 1,
                            }}
                          >
                            {sector.change_percent >= 0 ? "+" : ""}{sector.change_percent.toFixed(2)}%
                          </Typography>
                          {/* Volume Weighted Performance */}
                          {Math.abs(volumeWeightedChange - sector.change_percent) > 0.1 && (
                            <Typography
                              variant="caption"
                              sx={{
                                color: colors.accent,
                                fontSize: "0.6rem",
                                fontFamily: '"SF Mono", "Consolas", monospace',
                                display: "block",
                                mt: 0.25,
                              }}
                            >
                              Vol.Wtd: {volumeWeightedChange >= 0 ? "+" : ""}{volumeWeightedChange.toFixed(2)}%
                            </Typography>
                          )}
                        </Box>
                        
                        <Box sx={{ textAlign: "right" }}>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
                            <Typography
                              variant="caption"
                              sx={{
                                color: colors.textSecondary,
                                fontSize: "0.7rem",
                              }}
                            >
                              {availableStocks.length}/{sector.stocks_count}
                            </Typography>
                            {totalVolume > 0 && (
                              <VolumeIcon 
                                sx={{ 
                                  fontSize: "0.8rem", 
                                  color: colors.accent,
                                  opacity: Math.min(1, totalVolume / 10000000) // Scale by 1Cr volume
                                }} 
                              />
                            )}
                          </Box>
                          <Box sx={{ display: "flex", gap: 1 }}>
                            <Typography
                              variant="caption"
                              sx={{
                                color: colors.positive,
                                fontSize: "0.65rem",
                                fontFamily: '"SF Mono", "Consolas", monospace',
                              }}
                            >
                              {sector.advancing}↑
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                color: colors.negative,
                                fontSize: "0.65rem",
                                fontFamily: '"SF Mono", "Consolas", monospace',
                              }}
                            >
                              {sector.declining}↓
                            </Typography>
                          </Box>
                        </Box>
                      </Box>

                      {/* Sector Strength Progress Bar */}
                      <Box sx={{ mb: 0.5 }}>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min(100, Math.abs(sector.strength_score || 0))}
                          sx={{
                            height: 3,
                            borderRadius: 1.5,
                            bgcolor: `${colors.border}30`,
                            "& .MuiLinearProgress-bar": {
                              bgcolor: borderColor,
                              borderRadius: 1.5,
                            },
                          }}
                        />
                        <Typography
                          variant="caption"
                          sx={{
                            color: colors.textSecondary,
                            fontSize: "0.6rem",
                            fontFamily: '"SF Mono", "Consolas", monospace',
                          }}
                        >
                          Strength: {(sector.strength_score || 0).toFixed(1)}
                        </Typography>
                      </Box>
                    </Box>

                    {/* Stock Tiles Grid */}
                    <Collapse in={isExpanded} timeout="auto">
                      <Box sx={{ p: { xs: 1, sm: 1.5 } }}>
                        <Grid container spacing={0.5}>
                          {topStocks.map((stock, stockIndex) => {
                            const stockChangePercent = stock.change_percent || 0;
                            const stockVolume = stock.volume || 0;
                            const stockPrice = stock.last_price || 0;
                            
                            // Enhanced color based on volume and performance
                            const volumeIntensity = Math.min(1, stockVolume / 1000000); // Scale by 10L volume
                            const performanceIntensity = Math.min(1, Math.abs(stockChangePercent) / 10);
                            const combinedIntensity = (volumeIntensity * 0.3) + (performanceIntensity * 0.7);
                            
                            // Enhanced stock color calculation with volume weighting
                            const stockColor = (() => {
                              const baseIntensity = Math.min(0.8, combinedIntensity);
                              if (stockChangePercent > 0) {
                                return `${colors.positive}${Math.floor(baseIntensity * 255).toString(16).padStart(2, '0')}`;
                              } else if (stockChangePercent < 0) {
                                return `${colors.negative}${Math.floor(baseIntensity * 255).toString(16).padStart(2, '0')}`;
                              } else {
                                return `${colors.neutral}30`;
                              }
                            })();
                            
                            const stockBorderColor = getBorderColor(stockChangePercent);
                            
                            // Format volume for display
                            const formatVolume = (vol) => {
                              if (vol >= 10000000) return `${(vol / 10000000).toFixed(1)}Cr`;
                              if (vol >= 100000) return `${(vol / 100000).toFixed(1)}L`;
                              if (vol >= 1000) return `${(vol / 1000).toFixed(1)}K`;
                              return vol.toString();
                            };
                            
                            return (
                              <Grid item xs={6} key={stockIndex}>
                                <Tooltip
                                  title={
                                    <Box>
                                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                                        {stock.symbol} - {stock.name}
                                      </Typography>
                                      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.5 }}>
                                        <Typography variant="body2">
                                          Price: ₹{stockPrice.toFixed(2)}
                                        </Typography>
                                        <Typography variant="body2">
                                          Change: {stockChangePercent >= 0 ? "+" : ""}{stockChangePercent.toFixed(2)}%
                                        </Typography>
                                        <Typography variant="body2">
                                          Volume: {formatVolume(stockVolume)}
                                        </Typography>
                                        <Typography variant="body2">
                                          High: ₹{(stock.high || 0).toFixed(2)}
                                        </Typography>
                                        <Typography variant="body2">
                                          Low: ₹{(stock.low || 0).toFixed(2)}
                                        </Typography>
                                        <Typography variant="body2">
                                          Open: ₹{(stock.open || 0).toFixed(2)}
                                        </Typography>
                                      </Box>
                                      {stock.exchange && (
                                        <Typography variant="caption" sx={{ display: "block", mt: 0.5, opacity: 0.7 }}>
                                          Exchange: {stock.exchange} | Type: {stock.instrument_type}
                                        </Typography>
                                      )}
                                    </Box>
                                  }
                                  arrow
                                >
                                  <Paper
                                    sx={{
                                      p: 0.75,
                                      height: { xs: 50, sm: 55 },
                                      bgcolor: stockColor,
                                      border: `1px solid ${stockBorderColor}`,
                                      borderRadius: 1.5,
                                      cursor: "pointer",
                                      transition: "all 0.15s ease",
                                      display: "flex",
                                      flexDirection: "column",
                                      justifyContent: "space-between",
                                      alignItems: "center",
                                      position: "relative",
                                      overflow: "hidden",
                                      
                                      "&:hover": {
                                        transform: "scale(1.02)",
                                        borderWidth: 2,
                                        boxShadow: `0 4px 12px ${stockBorderColor}40`,
                                      },
                                      
                                      // Volume indicator bar
                                      "&::before": volumeIntensity > 0.1 ? {
                                        content: '""',
                                        position: "absolute",
                                        bottom: 0,
                                        left: 0,
                                        right: 0,
                                        height: `${Math.max(2, volumeIntensity * 8)}px`,
                                        bgcolor: colors.accent,
                                        opacity: 0.6,
                                      } : {},
                                    }}
                                  >
                                    <Box sx={{ textAlign: "center", flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
                                      <Typography
                                        variant="body2"
                                        sx={{
                                          fontWeight: 600,
                                          color: colors.text,
                                          fontSize: { xs: "0.65rem", sm: "0.7rem" },
                                          lineHeight: 1,
                                          overflow: "hidden",
                                          textOverflow: "ellipsis",
                                          whiteSpace: "nowrap",
                                          maxWidth: "100%",
                                        }}
                                      >
                                        {(stock.symbol || "").substring(0, 8)}
                                      </Typography>
                                      
                                      <Typography
                                        variant="caption"
                                        sx={{
                                          color: stockBorderColor,
                                          fontWeight: 600,
                                          fontSize: { xs: "0.6rem", sm: "0.65rem" },
                                          fontFamily: '"SF Mono", "Consolas", monospace',
                                          mt: 0.25,
                                        }}
                                      >
                                        {stockChangePercent >= 0 ? "+" : ""}{stockChangePercent.toFixed(1)}%
                                      </Typography>
                                    </Box>
                                    
                                    {/* Volume and Price indicators */}
                                    <Box 
                                      sx={{ 
                                        display: "flex", 
                                        justifyContent: "space-between", 
                                        alignItems: "center", 
                                        width: "100%",
                                        mt: 0.25,
                                      }}
                                    >
                                      {stockVolume > 0 && (
                                        <Typography
                                          variant="caption"
                                          sx={{
                                            color: colors.accent,
                                            fontSize: "0.55rem",
                                            fontFamily: '"SF Mono", "Consolas", monospace',
                                            opacity: 0.8,
                                          }}
                                        >
                                          {formatVolume(stockVolume)}
                                        </Typography>
                                      )}
                                      
                                      <Typography
                                        variant="caption"
                                        sx={{
                                          color: colors.textSecondary,
                                          fontSize: "0.55rem",
                                          fontFamily: '"SF Mono", "Consolas", monospace',
                                          opacity: 0.8,
                                        }}
                                      >
                                        ₹{stockPrice.toFixed(0)}
                                      </Typography>
                                    </Box>
                                    
                                    {/* High volume indicator */}
                                    {volumeIntensity > 0.5 && (
                                      <Box
                                        sx={{
                                          position: "absolute",
                                          top: 2,
                                          right: 2,
                                          width: 6,
                                          height: 6,
                                          borderRadius: "50%",
                                          bgcolor: colors.accent,
                                          boxShadow: `0 0 8px ${colors.accent}80`,
                                        }}
                                      />
                                    )}
                                  </Paper>
                                </Tooltip>
                              </Grid>
                            );
                          })}
                        </Grid>
                        
                        {sector.stocks.length > topStocks.length && (
                          <Typography
                            variant="caption"
                            sx={{
                              color: colors.textSecondary,
                              fontSize: "0.6rem",
                              display: "block",
                              textAlign: "center",
                              mt: 1,
                            }}
                          >
                            +{sector.stocks.length - topStocks.length} more stocks
                          </Typography>
                        )}
                      </Box>
                    </Collapse>
                  </Paper>
                </Grid>
              );
            })}
          </Grid>

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
              Click sectors to view individual stocks
            </Typography>
            
            <Typography
              variant="caption"
              sx={{
                color: colors.textSecondary,
                fontSize: { xs: "0.65rem", sm: "0.7rem" },
              }}
            >
              Total Stocks: {processedData.reduce((sum, s) => sum + s.stocks_count, 0)}
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }
);

Heatmap.displayName = "Heatmap";

export default Heatmap;