// components/common/EnhancedStocksList.jsx - Enhanced with Option Chain Support
import React, { memo, useState } from "react";
import {
  Box,
  Card,
  Typography,
  Chip,
  Skeleton,
  Stack,
  useTheme,
  useMediaQuery,
  Tooltip,
  IconButton,
} from "@mui/material";
import {
  ShowChart as OptionsIcon,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import OptionChainModal from "../options/OptionChainModal";
// F&O eligible stocks (this should eventually come from API)
const FNO_STOCKS = [
  "RELIANCE",
  "TCS",
  "HDFCBANK",
  "ICICIBANK",
  "HINDUNILVR",
  "INFY",
  "ITC",
  "SBIN",
  "BHARTIARTL",
  "KOTAKBANK",
  "LT",
  "ASIANPAINT",
  "AXISBANK",
  "MARUTI",
  "BAJFINANCE",
  "WIPRO",
  "ULTRACEMCO",
  "BAJAJFINSV",
  "NESTLEIND",
  "POWERGRID",
  "NTPC",
  "ONGC",
  "TATAMOTORS",
  "TECHM",
  "SUNPHARMA",
  "COALINDIA",
  "INDUSINDBK",
  "IOC",
  "GRASIM",
  "BPCL",
  "ADANIPORTS",
  "TATASTEEL",
  "M&M",
  "HCLTECH",
  "DIVISLAB",
];
const EnhancedStocksList = memo(
  ({
    title,
    data = [],
    isLoading = false,
    titleIcon = "📊",
    emptyMessage = "No data available",
    maxItems = 20,
    showVolume = true,
    showName = true,
    showSector = false,
    showOptionsButton = true, // New prop to enable/disable options button
    layoutType = "auto", // Default to 'auto' for better responsiveness
    enableExpansion = false,
    compact = false,
    density = "standard",
    containerHeight = "auto", // Default to auto height
  }) => {
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
    const isTablet = useMediaQuery(theme.breakpoints.down("md")); // Used in getOptimalLayout function
    const navigate = useNavigate();
    // Option chain modal state
    const [optionModalOpen, setOptionModalOpen] = useState(false);
    const [selectedStock, setSelectedStock] = useState(null);
    const [fnoEligibleStocks] = useState(
      new Set(FNO_STOCKS)
    );
    // Check if stock is F&O eligible
    const isFNOEligible = (symbol) => {
      return fnoEligibleStocks.has(symbol?.toUpperCase());
    };
    // Handle options button click (modal) - keeping for potential future use
    // const handleOptionsClick = (stock, event) => {
    //   event.stopPropagation();
    //   setSelectedStock(stock);
    //   setOptionModalOpen(true);
    // };
    // Handle options button click with ctrl/cmd for full page
    const handleOptionsNavigation = (stock, event) => {
      event.stopPropagation();
      if (event.ctrlKey || event.metaKey) {
        // Open in new tab/window
        window.open(`/option-chain/${stock.symbol}`, "_blank");
      } else if (event.shiftKey) {
        // Navigate to full page
        navigate(`/option-chain/${stock.symbol}`);
      } else {
        // Default: open modal
        setSelectedStock(stock);
        setOptionModalOpen(true);
      }
    };
    // Bloomberg-inspired professional color scheme
    const colors = {
      // Bloomberg Terminal inspired dark mode
      background: theme.palette.mode === "dark" ? "#000000" : "#ffffff",
      surface: theme.palette.mode === "dark" ? "#1a1a1a" : "#f8f9fa",
      surfaceHover: theme.palette.mode === "dark" ? "#2a2a2a" : "#e9ecef",
      text: theme.palette.mode === "dark" ? "#ffffff" : "#000000",
      textSecondary: theme.palette.mode === "dark" ? "#cccccc" : "#666666",
      textMuted: theme.palette.mode === "dark" ? "#999999" : "#888888",
      // Bloomberg-style accent colors
      positive: theme.palette.mode === "dark" ? "#00ff00" : "#008000", // Bright green
      negative: theme.palette.mode === "dark" ? "#ff4500" : "#dc3545", // Orange-red / Red
      neutral: theme.palette.mode === "dark" ? "#ffff00" : "#ffc107", // Yellow
      // Professional header styling
      header: theme.palette.mode === "dark" ? "#00aaff" : "#0066cc", // Bright blue
      headerSecondary: theme.palette.mode === "dark" ? "#ff8c00" : "#ff6b35", // Orange
      // Clean borders and dividers
      border: theme.palette.mode === "dark" ? "#333333" : "#dee2e6",
      borderLight: theme.palette.mode === "dark" ? "#222222" : "#f1f3f4",
      // Card and container backgrounds
      cardBackground: theme.palette.mode === "dark" ? "#0d1117" : "#ffffff",
      cardBackgroundHover:
        theme.palette.mode === "dark" ? "#161b22" : "#f8f9fa",
      // Bloomberg orange accent
      accent: theme.palette.mode === "dark" ? "#ff8c00" : "#ff6b35",
      accentMuted: theme.palette.mode === "dark" ? "#cc7000" : "#e55a2b",
      // Volume and additional data colors
      volume: theme.palette.mode === "dark" ? "#6495ed" : "#4169e1", // Cornflower blue
      info: theme.palette.mode === "dark" ? "#17a2b8" : "#0dcaf0", // Teal
      // Options button color
      options: theme.palette.mode === "dark" ? "#ff6b35" : "#ff4500", // Orange-red
    };
    // Bloomberg-inspired density configuration with professional spacing
    const densityConfig = {
      compact: {
        cardPadding: { xs: 0, sm: 0 },
        tablePadding: { xs: "4px 8px", sm: "6px 10px" },
        fontSize: { xs: "0.75rem", sm: "0.8rem" }, // Slightly smaller font
        rowHeight: { xs: 36, sm: 40 },
        avatarSize: { xs: 28, sm: 32 },
        borderRadius: 0,
      },
      standard: {
        cardPadding: { xs: 0, sm: 0 },
        tablePadding: { xs: "6px 10px", sm: "8px 12px" },
        fontSize: { xs: "0.8rem", sm: "0.85rem" }, // Standard font
        rowHeight: { xs: 40, sm: 44 },
        avatarSize: { xs: 32, sm: 36 },
        borderRadius: 0,
      },
      comfortable: {
        cardPadding: { xs: 0.5, sm: 0.75 },
        tablePadding: { xs: "8px 12px", sm: "10px 14px" },
        fontSize: { xs: "0.85rem", sm: "0.9rem" }, // Larger font
        rowHeight: { xs: 44, sm: 48 },
        avatarSize: { xs: 36, sm: 40 },
        borderRadius: 0,
      },
    };
    const currentDensity = densityConfig[density] || densityConfig.standard;
    // Dynamic layout optimization based on data size and screen size
    const getOptimalLayout = () => {
      // Determine effective layout type
      let effectiveLayoutType = layoutType;
      if (layoutType === "auto") {
        // On mobile, prefer cards for better readability
        if (isMobile) {
          effectiveLayoutType = "cards";
        } else if (isTablet) {
          // On tablet, cards if data is small, table if large
          effectiveLayoutType = data.length <= 15 ? "cards" : "table";
        } else {
          // On desktop, prefer table
          effectiveLayoutType = "table";
        }
      }

      const dataLength = data.length;
      if (effectiveLayoutType === "cards" || isMobile) {
        // Card layout optimizations
        return {
          layoutType: "cards",
          itemsPerRow: 1, // Always 1 card per row for list feel
          cardMinHeight: dataLength <= 5 ? "auto" : "65px", // Adjust height based on data
          showMoreDetails: dataLength <= 10, // Show more details if less data
          fontSize: dataLength <= 10 ? "0.85rem" : "0.8rem", // Adjust font size
          rowHeight: currentDensity.rowHeight.xs, // Use mobile row height for cards
        };
      } else {
        // Table layout optimizations (desktop/tablet)
        return {
          layoutType: "table",
          itemsPerRow: 1, // Not used for table
          cardMinHeight: "auto", // Not used for table
          showMoreDetails: true, // Always show details in table
          tableRowHeight:
            dataLength <= 15
              ? currentDensity.rowHeight.sm + 8 // Slightly taller rows for less data
              : currentDensity.rowHeight.sm, // Standard row height
          fontSize: dataLength <= 20 ? "0.85rem" : "0.8rem", // Adjust font size
          rowHeight: currentDensity.rowHeight.sm, // Use standard row height
        };
      }
    };
    const optimalLayout = getOptimalLayout();
    // Format price
    const formatPrice = (price) => {
      return typeof price === "number"
        ? price.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })
        : "N/A";
    };
    // Format volume
    const formatVolume = (volume) => {
      if (!volume || volume === 0) return "0";
      if (volume >= 1000000) {
        return `${(volume / 1000000).toFixed(1)}M`;
      }
      if (volume >= 1000) {
        return `${(volume / 1000).toFixed(1)}K`;
      }
      return volume.toString();
    };
    // Loading skeleton
    if (isLoading) {
      return (
        <Card
          sx={{
            height: containerHeight === "auto" ? "auto" : containerHeight,
            maxHeight: containerHeight === "auto" ? "none" : containerHeight, // Ensure maxHeight is set
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            bgcolor: colors.cardBackground,
            border: `1px solid ${colors.border}`,
            borderRadius: 0,
            boxShadow: "none",
          }}
        >
          <Box
            sx={{
              p: { xs: 0.5, sm: 0.75 },
              borderBottom: `1px solid ${colors.border}`,
            }}
          >
            <Skeleton variant="text" width="40%" height={20} />
          </Box>
          <Box sx={{ flex: 1, p: 1 }}>
            {Array.from(new Array(5)).map((_, index) => (
              <Box key={index} sx={{ mb: 1 }}>
                <Skeleton variant="rectangular" height={40} sx={{ mb: 0.5 }} />
              </Box>
            ))}
          </Box>
        </Card>
      );
    }
    return (
      <>
        <Card
          sx={{
            height: containerHeight === "auto" ? "auto" : containerHeight,
            maxHeight: containerHeight === "auto" ? "none" : containerHeight, // Ensure maxHeight is set
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            bgcolor: colors.cardBackground,
            border: `1px solid ${colors.border}`,
            borderRadius: 0,
            boxShadow: "none",
            maxWidth: "100%",
          }}
        >
          <Box
            sx={{
              p: { xs: 0.5, sm: 0.75 },
              pb: 0.25,
              flexShrink: 0,
              bgcolor: colors.surface,
              borderBottom: `1px solid ${colors.border}`,
            }}
          >
            <Typography
              variant="h6"
              sx={{
                mb: 0,
                color: colors.header,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                fontSize: { xs: "0.75rem", sm: "0.8rem" },
                lineHeight: 1.1,
                fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
                textTransform: "uppercase",
                letterSpacing: "0.75px",
              }}
            >
              {titleIcon} {title}
            </Typography>
          </Box>
          {data.length === 0 ? (
            <Box
              sx={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                p: 3,
              }}
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ textAlign: "center" }}
              >
                {emptyMessage}
              </Typography>
            </Box>
          ) : (
            <>
              {/* Scrollable Content Area */}
              <Box
                sx={{
                  flex: 1,
                  overflow: "auto",
                  px: { xs: 1.25, sm: 1.5 },
                  pb: { xs: 1.25, sm: 1.5 },
                  // Hide scrollbars
                  "&::-webkit-scrollbar": {
                    display: "none",
                  },
                  "&": {
                    msOverflowStyle: "none",
                    scrollbarWidth: "none",
                  },
                }}
              >
                <Stack spacing={0.5}>
                  {data.slice(0, maxItems).map((item, index) => {
                    const isPositive = (item.change || 0) >= 0;
                    const changePercent = Math.abs(item.change_percent || 0);
                    const changeValue = item.change || 0;
                    const changePercentValue = item.change_percent || 0;
                    const isStockFNOEligible = isFNOEligible(item.symbol);
                    return (
                      <Box
                        key={item.instrument_key || item.symbol || index}
                        sx={{
                          bgcolor: "transparent",
                          borderRadius: 0,
                          border: "none",
                          borderLeft: `2px solid ${
                            isPositive ? colors.positive : colors.negative
                          }`,
                          borderBottom: `1px solid ${colors.borderLight}`,
                          boxShadow: "none",
                          transition: "all 0.15s ease",
                          "&:hover": {
                            bgcolor: colors.surfaceHover,
                            borderLeft: `3px solid ${
                              isPositive ? colors.positive : colors.negative
                            }`,
                          },
                        }}
                      >
                        <Box sx={{ p: { xs: 0.75, sm: 1 } }}>
                          {/* Ultra-Clean Compact Row */}
                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              mb: 0.5,
                              minHeight: optimalLayout.cardMinHeight,
                            }}
                          >
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 0.75,
                                flex: 1,
                              }}
                            >
                              <Box
                                sx={{
                                  width: 16,
                                  height: 16,
                                  borderRadius: 0,
                                  bgcolor: "transparent",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  fontSize: "0.7rem",
                                  fontWeight: "bold",
                                  color: isPositive
                                    ? colors.positive
                                    : colors.negative,
                                }}
                              >
                                {isPositive ? "▲" : "▼"}
                              </Box>
                              <Box>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontWeight: 600,
                                    color: colors.text,
                                    fontSize: {
                                      xs: optimalLayout.fontSize,
                                      sm: "0.9rem",
                                    },
                                    lineHeight: 1.1,
                                    fontFamily:
                                      '"SF Pro Display", "Segoe UI", sans-serif',
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 0.5,
                                  }}
                                >
                                  {item.symbol || "N/A"}
                                  {changePercent > 5 && (
                                    <Box
                                      component="span"
                                      sx={{
                                        ml: 0.25,
                                        color: colors.accent,
                                        fontSize: "0.7rem",
                                      }}
                                    >
                                      ●
                                    </Box>
                                  )}
                                  {/* F&O Badge */}
                                  {isStockFNOEligible && (
                                    <Chip
                                      label="F&O"
                                      size="small"
                                      sx={{
                                        height: 16,
                                        fontSize: "0.6rem",
                                        fontWeight: "bold",
                                        backgroundColor: colors.options,
                                        color: "white",
                                        "& .MuiChip-label": {
                                          px: 0.5,
                                        },
                                        ml: 0.5, // Add some space before the badge
                                      }}
                                    />
                                  )}
                                </Typography>
                                {showName && item.name && (
                                  <Typography
                                    variant="caption"
                                    sx={{
                                      display: "block",
                                      color: "text.secondary",
                                      fontSize: "0.65rem",
                                      lineHeight: 1,
                                      overflow: "hidden",
                                      textOverflow: "ellipsis",
                                      whiteSpace: "nowrap",
                                      maxWidth: "120px",
                                    }}
                                  >
                                    {item.name}
                                  </Typography>
                                )}
                              </Box>
                            </Box>
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 0.75,
                              }}
                            >
                              {/* Options Button */}
                              {showOptionsButton && isStockFNOEligible && (
                                <Tooltip title="Options: Click=Modal, Shift+Click=Full Page, Ctrl+Click=New Tab">
                                  <IconButton
                                    size="small"
                                    onClick={(e) =>
                                      handleOptionsNavigation(item, e)
                                    }
                                    sx={{
                                      width: 24,
                                      height: 24,
                                      backgroundColor: `${colors.options}20`,
                                      color: colors.options,
                                      border: `1px solid ${colors.options}40`,
                                      "&:hover": {
                                        backgroundColor: `${colors.options}30`,
                                        transform: "scale(1.05)",
                                      },
                                      transition: "all 0.2s ease",
                                      mr: 0.5, // Add space after the button
                                    }}
                                  >
                                    <OptionsIcon
                                      sx={{ fontSize: "0.875rem" }}
                                    />
                                  </IconButton>
                                </Tooltip>
                              )}
                              {/* Price */}
                              <Box
                                sx={{ textAlign: "right", minWidth: "90px" }}
                              >
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontWeight: 600,
                                    fontSize: { xs: "0.9rem", sm: "0.95rem" },
                                    color: colors.text,
                                    fontFamily:
                                      '"SF Mono", "Consolas", monospace',
                                    lineHeight: 1.1,
                                  }}
                                >
                                  ₹{formatPrice(item.last_price || item.ltp)}
                                </Typography>
                              </Box>
                            </Box>
                          </Box>
                          {/* Inline Performance Strip */}
                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              p: 0.375,
                              bgcolor: isPositive
                                ? `${colors.positive}08`
                                : `${colors.negative}08`,
                              borderRadius: 0.75,
                              border: `1px solid ${
                                isPositive ? colors.positive : colors.negative
                              }20`,
                            }}
                          >
                            {/* Change Display - Inline */}
                            <Typography
                              variant="body2"
                              sx={{
                                fontWeight: 600,
                                color: isPositive
                                  ? colors.positive
                                  : colors.negative,
                                fontSize: { xs: "0.8rem", sm: "0.85rem" },
                                fontFamily: '"SF Mono", "Consolas", monospace',
                              }}
                            >
                              {changeValue >= 0 ? "+" : ""}
                              {changeValue.toFixed(2)} (
                              {changePercentValue >= 0 ? "+" : ""}
                              {changePercentValue.toFixed(2)}%)
                            </Typography>
                            {/* Minimal Info Icons */}
                            <Box
                              sx={{
                                display: "flex",
                                gap: 0.75,
                                alignItems: "center",
                              }}
                            >
                              {showVolume && item.volume && (
                                <Typography
                                  variant="caption"
                                  sx={{
                                    fontFamily:
                                      '"SF Mono", "Consolas", monospace',
                                    fontSize: "0.58rem",
                                    color: colors.volume,
                                    opacity: 0.9,
                                  }}
                                >
                                  {formatVolume(item.volume)}
                                </Typography>
                              )}
                              {showSector && item.sector && (
                                <Typography
                                  variant="caption"
                                  sx={{
                                    fontSize: "0.6rem",
                                    color: colors.header,
                                    opacity: 0.8,
                                    maxWidth: "50px",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                  }}
                                >
                                  {item.sector}
                                </Typography>
                              )}
                            </Box>
                          </Box>
                        </Box>
                      </Box>
                    );
                  })}
                </Stack>
              </Box>
              {/* Fixed Footer */}
              {data.length > maxItems && (
                <Box
                  sx={{
                    flexShrink: 0,
                    borderTop: `1px solid ${colors.border}`,
                    p: { xs: 0.5, sm: 0.75 },
                    textAlign: "center",
                    bgcolor: colors.surface,
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      color: colors.textMuted,
                      fontSize: "0.65rem",
                      fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
                    }}
                  >
                    Showing {maxItems} of {data.length} stocks
                  </Typography>
                </Box>
              )}
            </>
          )}
        </Card>
        {/* Option Chain Modal */}
        <OptionChainModal
          open={optionModalOpen}
          onClose={() => setOptionModalOpen(false)}
          symbol={selectedStock?.symbol}
          stockData={selectedStock}
        />
      </>
    );
  }
);
export default EnhancedStocksList;
