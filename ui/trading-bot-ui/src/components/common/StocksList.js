// components/common/StocksList.jsx - OPTIMIZED RESPONSIVE VERSION WITH BETTER SPACE UTILIZATION
import React, { memo, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Skeleton,
  Grid,
  Stack,
  useTheme,
  useMediaQuery,
  Tooltip,
} from "@mui/material";
import { Info, ShowChart as OptionsIcon } from "@mui/icons-material";
import { motion } from "framer-motion";
import OptionChainModal from "../options/OptionChainModal";

const StocksList = memo(
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
    showTimestamp = false, // New prop for showing breakout timestamps
    layoutType = "auto",
    enableExpansion = false,
    compact = false,
    density = "standard", // compact, standard, comfortable
    containerHeight = "70vh", // Default container height
    showOptionChain = false, // New prop to enable option chain integration
  }) => {
    // Debug logging (defensive)
    if (process.env.NODE_ENV === "development") {
      let titlePreview = "";
      try {
        if (typeof title === "string") {
          titlePreview =
            title.length > 20 ? title.substring(0, 20) + "..." : title;
        } else if (title == null) {
          titlePreview = "<<no-title>>";
        } else if (typeof title === "object") {
          // show small JSON preview for objects (avoid huge dumps)
          const j = JSON.stringify(title);
          titlePreview = j.length > 20 ? j.substring(0, 20) + "..." : j;
        } else {
          titlePreview = String(title);
        }
      } catch (e) {
        titlePreview = "<<error>>";
      }

      console.log("🔍 StocksList Debug:", {
        title: titlePreview,
        showOptionChain,
        dataLength: Array.isArray(data) ? data.length : 0,
        hasData: Array.isArray(data) ? data.length > 0 : false,
      });
    }

    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
    const isTablet = useMediaQuery(theme.breakpoints.down("md"));

    // Option chain modal state
    const [optionChainOpen, setOptionChainOpen] = useState(false);
    const [selectedStock, setSelectedStock] = useState(null);

    // Handle option chain click
    const handleOptionChainClick = (stock) => {
      setSelectedStock(stock);
      setOptionChainOpen(true);
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
      positive: theme.palette.mode === "dark" ? "#00ff00" : "#008000",
      negative: theme.palette.mode === "dark" ? "#ff4500" : "#dc3545",
      neutral: theme.palette.mode === "dark" ? "#ffff00" : "#ffc107",
      // Professional header styling
      header: theme.palette.mode === "dark" ? "#00aaff" : "#0066cc",
      headerSecondary: theme.palette.mode === "dark" ? "#ff8c00" : "#ff6b35",
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
      volume: theme.palette.mode === "dark" ? "#6495ed" : "#4169e1",
      info: theme.palette.mode === "dark" ? "#17a2b8" : "#0dcaf0",
    };

    // Bloomberg-inspired density configuration with professional spacing
    const densityConfig = {
      compact: {
        cardPadding: { xs: 0, sm: 0 },
        tablePadding: { xs: "4px 8px", sm: "6px 10px" },
        fontSize: { xs: "0.8rem", sm: "0.85rem" },
        rowHeight: { xs: 36, sm: 40 },
        avatarSize: { xs: 28, sm: 32 },
        borderRadius: 0,
      },
      standard: {
        cardPadding: { xs: 0, sm: 0 },
        tablePadding: { xs: "6px 10px", sm: "8px 12px" },
        fontSize: { xs: "0.85rem", sm: "0.9rem" },
        rowHeight: { xs: 40, sm: 44 },
        avatarSize: { xs: 32, sm: 36 },
        borderRadius: 0,
      },
      comfortable: {
        cardPadding: { xs: 0.5, sm: 0.75 },
        tablePadding: { xs: "8px 12px", sm: "10px 14px" },
        fontSize: { xs: "0.9rem", sm: "0.95rem" },
        rowHeight: { xs: 44, sm: 48 },
        avatarSize: { xs: 36, sm: 40 },
        borderRadius: 0,
      },
    };

    const currentDensity = densityConfig[density] || densityConfig.standard;

    // Dynamic layout optimization based on data size
    const getOptimalLayout = () => {
      const dataLength = data.length;
      if (isMobile) {
        return {
          itemsPerRow: 1,
          cardMinHeight: dataLength <= 5 ? "auto" : "65px",
          showMoreDetails: dataLength <= 10,
          fontSize: dataLength <= 10 ? "0.9rem" : "0.85rem",
        };
      }

      if (isTablet) {
        return {
          itemsPerRow: dataLength <= 10 ? 2 : 1,
          cardMinHeight: "auto",
          showMoreDetails: dataLength <= 20,
          fontSize: "0.9rem",
        };
      }

      // Desktop
      return {
        itemsPerRow: 1,
        cardMinHeight: "auto",
        showMoreDetails: true,
        tableRowHeight:
          dataLength <= 15
            ? currentDensity.rowHeight.sm + 8
            : currentDensity.rowHeight.sm,
        fontSize: dataLength <= 20 ? "0.95rem" : "0.9rem",
      };
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

    // Format volume for display
    const formatVolume = (volume) => {
      if (!volume) return "N/A";

      if (volume >= 10000000) {
        return `${(volume / 10000000).toFixed(1)}Cr`;
      }
      if (volume >= 100000) {
        return `${(volume / 100000).toFixed(1)}L`;
      }
      return volume.toLocaleString();
    };

    // Enhanced loading state with skeleton
    if (isLoading) {
      return (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Skeleton variant="text" width="40%" height={32} sx={{ mb: 2 }} />
            <Grid container spacing={2}>
              {[...Array(isMobile ? 4 : 6)].map((_, i) => (
                <Grid item xs={12} sm={6} md={4} key={i}>
                  <Skeleton
                    variant="rectangular"
                    height={120}
                    sx={{ borderRadius: 1 }}
                  />
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      );
    }

    // CLEAN MOBILE CARD LAYOUT - Fixed container with clean scrolling
    if (isMobile) {
      return (
        <Box
          sx={{
            mb: 0.5,
            height: containerHeight,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            bgcolor: colors.cardBackground,
            border: "none",
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

                    return (
                      <motion.div
                        key={item.instrument_key || item.symbol || index}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.2, delay: index * 0.05 }}
                      >
                      <Box
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

                            <Box sx={{ textAlign: "right", minWidth: "90px" }}>
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

                              {/* Option Chain Button - All stocks are F&O eligible */}
                              {showOptionChain && (
                                <Tooltip
                                  title="View Option Chain"
                                  placement="top"
                                >
                                  <Box
                                    component="button"
                                    onClick={() => handleOptionChainClick(item)}
                                    sx={{
                                      background: "none",
                                      border: "none",
                                      cursor: "pointer",
                                      display: "flex",
                                      alignItems: "center",
                                      padding: 0.25,
                                      borderRadius: 0.5,
                                      color: colors.accent,
                                      "&:hover": {
                                        bgcolor: `${colors.accent}20`,
                                        transform: "scale(1.1)",
                                      },
                                      transition: "all 0.15s ease",
                                    }}
                                  >
                                    <OptionsIcon sx={{ fontSize: "0.75rem" }} />
                                  </Box>
                                </Tooltip>
                              )}

                              {showTimestamp &&
                                item.breakout_time &&
                                item.breakout_time !== "N/A" && (
                                  <Box
                                    sx={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 0.5,
                                    }}
                                  >
                                    {item.is_fresh && (
                                      <Typography
                                        sx={{
                                          fontSize: "0.6rem",
                                          color: colors.accent,
                                        }}
                                      >
                                        🔥
                                      </Typography>
                                    )}
                                    <Typography
                                      variant="caption"
                                      sx={{
                                        fontSize: "0.6rem",
                                        color: item.is_fresh
                                          ? colors.accent
                                          : colors.textSecondary,
                                        fontWeight: 600,
                                      }}
                                    >
                                      {item.breakout_time}
                                    </Typography>
                                  </Box>
                                )}
                            </Box>
                          </Box>
                        </Box>
                      </Box>
                      </motion.div>
                    );
                  })}
                </Stack>
              </Box>

              {/* Fixed Footer */}
              <Box
                sx={{
                  flexShrink: 0,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  p: { xs: 1, sm: 1.5 },
                  pt: { xs: 0.75, sm: 1 },
                  borderTop: `1px solid ${colors.border}30`,
                  bgcolor: "background.paper",
                }}
              >
                <Chip
                  label={`${Math.min(data.length, maxItems)} / ${data.length}`}
                  size="small"
                  color="primary"
                  variant="outlined"
                  sx={{
                    fontSize: { xs: "0.6rem", sm: "0.65rem" },
                    height: { xs: 20, sm: 24 },
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{
                    color: "text.secondary",
                    fontSize: { xs: "0.55rem", sm: "0.6rem" },
                    opacity: 0.8,
                  }}
                >
                  {new Date().toLocaleTimeString()}
                </Typography>
              </Box>
            </>
          )}
        </Box>
      );
    }

    // BLOOMBERG-STYLE PROFESSIONAL TABLE LAYOUT
    return (
      <>
        <Box
          sx={{
            mb: 0.5,
            height: containerHeight,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            bgcolor: colors.cardBackground,
            border: "none",
            borderRadius: 0,
            boxShadow: "none",
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
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 1,
                flexWrap: "wrap",
                gap: 1,
              }}
            >
              <Typography
                variant={isTablet ? "h6" : "h5"}
                sx={{
                  color: colors.header,
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: 0.75,
                  fontSize: isTablet ? "0.9rem" : "1rem",
                  fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                {titleIcon} {title}
              </Typography>

              {/* Table Summary Stats */}
              <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                <Chip
                  label={`${data.length} items`}
                  size="small"
                  variant="outlined"
                  color="primary"
                  sx={{ fontSize: "0.65rem" }}
                />
                {data.length > 0 && (
                  <Chip
                    label={`${Math.round(
                      (data.filter((item) => (item.change || 0) > 0).length /
                        data.length) *
                        100
                    )}% ↑`}
                    size="small"
                    sx={{
                      bgcolor: colors.positive,
                      color: "white",
                      fontSize: "0.65rem",
                      fontFamily: '"SF Mono", "Consolas", monospace',
                    }}
                  />
                )}
              </Box>
            </Box>
          </Box>

          {data.length === 0 ? (
            <Box
              sx={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                p: 4,
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
              <Box
                sx={{
                  flex: 1,
                  overflow: "hidden",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <TableContainer
                  component={Paper}
                  sx={{
                    flex: 1,
                    overflowY: "auto",
                    overflowX: "auto",
                    bgcolor: colors.cardBackground,
                    borderRadius: 0,
                    border: "none",
                    // Hide scrollbars but keep functionality
                    "&::-webkit-scrollbar": {
                      display: "none",
                    },
                    "&": {
                      msOverflowStyle: "none",
                      scrollbarWidth: "none",
                    },
                  }}
                >
                  <Table
                    size={compact || isTablet ? "small" : "medium"}
                    stickyHeader
                    sx={{
                      minWidth: isTablet ? 500 : 650,
                      "& .MuiTableCell-root": {
                        borderBottom: `1px solid ${colors.border}`,
                        fontSize: currentDensity.fontSize,
                        padding: currentDensity.tablePadding,
                        color: colors.text,
                      },
                      "& .MuiTableCell-head": {
                        backgroundColor: colors.surface,
                        fontWeight: 600,
                        fontSize: {
                          xs: "0.65rem",
                          sm: "0.7rem",
                          md: "0.75rem",
                        },
                        color: colors.header,
                        borderBottom: `1px solid ${colors.border}`,
                        borderTop: "none",
                        textTransform: "uppercase",
                        letterSpacing: { xs: "0.75px", md: "1px" },
                        position: "sticky",
                        top: 0,
                        zIndex: 1,
                        fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
                        py: { xs: 0.75, md: 1 },
                        px: { xs: 0.75, md: 1 },
                      },
                      "& .MuiTableRow-root": {
                        height:
                          optimalLayout.tableRowHeight ||
                          currentDensity.rowHeight,
                        "&:hover": {
                          backgroundColor: colors.surfaceHover,
                          transform: isTablet ? "none" : "translateY(-1px)",
                          transition: "all 0.15s ease",
                        },
                        "&:nth-of-type(even)": {
                          backgroundColor: colors.surface,
                        },
                        "&:nth-of-type(odd)": {
                          backgroundColor: colors.cardBackground,
                        },
                      },
                    }}
                  >
                    <TableHead>
                      <TableRow>
                        <TableCell
                          sx={{
                            minWidth: isTablet ? 90 : 100,
                            maxWidth: isTablet ? 130 : 150,
                            width: isTablet ? "18%" : "auto",
                          }}
                        >
                          SYMBOL
                        </TableCell>
                        {showName && !isTablet && (
                          <TableCell
                            sx={{
                              minWidth: 120,
                              maxWidth: 200,
                              width: "20%",
                            }}
                          >
                            NAME
                          </TableCell>
                        )}
                        <TableCell
                          align="right"
                          sx={{
                            minWidth: isTablet ? 80 : 100,
                            width: isTablet ? "20%" : "15%",
                          }}
                        >
                          PRICE
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{
                            minWidth: isTablet ? 60 : 80,
                            width: isTablet ? "15%" : "12%",
                          }}
                        >
                          CHG
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{
                            minWidth: isTablet ? 70 : 80,
                            width: isTablet ? "15%" : "12%",
                          }}
                        >
                          CHG%
                        </TableCell>
                        {showVolume && (
                          <TableCell
                            align="right"
                            sx={{
                              minWidth: isTablet ? 70 : 100,
                              width: isTablet ? "15%" : "12%",
                            }}
                          >
                            VOL
                          </TableCell>
                        )}
                        {showSector && !isTablet && (
                          <TableCell
                            sx={{
                              minWidth: 100,
                              maxWidth: 120,
                              width: "15%",
                            }}
                          >
                            SECTOR
                          </TableCell>
                        )}
                        {showTimestamp && !isTablet && (
                          <TableCell
                            align="center"
                            sx={{
                              minWidth: 120,
                              maxWidth: 140,
                              width: "15%",
                            }}
                          >
                            TIME
                          </TableCell>
                        )}
                        {showOptionChain && (
                          <TableCell
                            align="center"
                            sx={{
                              minWidth: 60,
                              maxWidth: 80,
                              width: "8%",
                            }}
                          >
                            OPTIONS
                          </TableCell>
                        )}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.slice(0, maxItems).map((stock, index) => {
                        const isPositive = (stock.change || 0) >= 0;
                        const changePercent = Math.abs(
                          stock.change_percent || 0
                        );

                        return (
                          <motion.tr
                            key={stock.instrument_key || stock.symbol || index}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.2, delay: index * 0.03 }}
                            component={TableRow}
                            hover
                            sx={{
                              cursor: "pointer",
                              "&:hover .stock-actions": {
                                opacity: 1,
                              },
                            }}
                          >
                            <TableCell>
                              <Box
                                sx={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 0.5,
                                }}
                              >
                                <Box
                                  sx={{
                                    width: 14,
                                    height: 14,
                                    borderRadius: "50%",
                                    bgcolor: isPositive
                                      ? colors.positive
                                      : colors.negative,
                                    mr: 0.75,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: "0.6rem",
                                    fontWeight: "bold",
                                    color: "white",
                                  }}
                                >
                                  {isPositive ? "▲" : "▼"}
                                </Box>
                                <Box>
                                  <Typography
                                    variant="body2"
                                    sx={{
                                      fontWeight: 600,
                                      fontSize: "inherit",
                                      lineHeight: 1.2,
                                      fontFamily:
                                        '"SF Pro Display", "Segoe UI", sans-serif',
                                    }}
                                  >
                                    {stock.symbol || "N/A"}
                                    {changePercent > 5 && (
                                      <Box
                                        component="span"
                                        sx={{
                                          ml: 0.5,
                                          color: colors.accent,
                                          fontSize: "0.7rem",
                                        }}
                                      >
                                        ●
                                      </Box>
                                    )}
                                  </Typography>
                                  {showName && isTablet && stock.name && (
                                    <Typography
                                      variant="caption"
                                      sx={{
                                        color: "text.secondary",
                                        fontSize: "0.65rem",
                                        lineHeight: 1,
                                        display: "block",
                                        overflow: "hidden",
                                        textOverflow: "ellipsis",
                                        whiteSpace: "nowrap",
                                        maxWidth: "100px",
                                      }}
                                    >
                                      {stock.name}
                                    </Typography>
                                  )}
                                </Box>
                              </Box>
                            </TableCell>

                            {showName && !isTablet && (
                              <TableCell>
                                <Tooltip title={stock.name || "N/A"} arrow>
                                  <Typography
                                    variant="body2"
                                    sx={{
                                      overflow: "hidden",
                                      textOverflow: "ellipsis",
                                      whiteSpace: "nowrap",
                                      color: "text.secondary",
                                      fontSize: "inherit",
                                    }}
                                  >
                                    {stock.name || "N/A"}
                                  </Typography>
                                </Tooltip>
                              </TableCell>
                            )}

                            <TableCell align="right">
                              <Typography
                                variant="body2"
                                sx={{
                                  fontWeight: 600,
                                  fontFamily:
                                    '"SF Mono", "Consolas", monospace',
                                  fontSize: "inherit",
                                  lineHeight: 1.2,
                                }}
                              >
                                ₹{formatPrice(stock.last_price || stock.ltp)}
                              </Typography>
                            </TableCell>

                            <TableCell align="right">
                              <Typography
                                variant="body2"
                                sx={{
                                  fontWeight: 600,
                                  color: isPositive
                                    ? colors.positive
                                    : colors.negative,
                                  fontFamily:
                                    '"SF Mono", "Consolas", monospace',
                                  fontSize: "inherit",
                                }}
                              >
                                {typeof stock.change === "number"
                                  ? (stock.change >= 0 ? "+" : "") +
                                    stock.change.toFixed(2)
                                  : "N/A"}
                              </Typography>
                            </TableCell>

                            <TableCell align="right">
                              <Typography
                                variant="body2"
                                sx={{
                                  fontWeight: 600,
                                  color: isPositive
                                    ? colors.positive
                                    : colors.negative,
                                  fontFamily:
                                    '"SF Mono", "Consolas", monospace',
                                  fontSize: "inherit",
                                }}
                              >
                                {typeof stock.change_percent === "number"
                                  ? (stock.change_percent >= 0 ? "+" : "") +
                                    stock.change_percent.toFixed(2) +
                                    "%"
                                  : "N/A"}
                              </Typography>
                            </TableCell>

                            {showVolume && (
                              <TableCell align="right">
                                <Box
                                  sx={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "flex-end",
                                    gap: 0.25,
                                  }}
                                >
                                  <Typography
                                    variant="body2"
                                    sx={{
                                      fontFamily:
                                        '"SF Mono", "Consolas", monospace',
                                      color: colors.volume,
                                      fontSize: "inherit",
                                      opacity: 0.9,
                                    }}
                                  >
                                    {formatVolume(stock.volume)}
                                  </Typography>
                                </Box>
                              </TableCell>
                            )}

                            {showSector && !isTablet && (
                              <TableCell>
                                {stock.sector ? (
                                  <Chip
                                    label={stock.sector}
                                    size="small"
                                    variant="outlined"
                                    sx={{
                                      fontSize: "0.65rem",
                                      height: 20,
                                      maxWidth: "100%",
                                      "& .MuiChip-label": {
                                        px: 0.5,
                                        overflow: "hidden",
                                        textOverflow: "ellipsis",
                                      },
                                    }}
                                  />
                                ) : (
                                  <Typography
                                    variant="body2"
                                    color="text.secondary"
                                    sx={{ fontSize: "inherit" }}
                                  >
                                    —
                                  </Typography>
                                )}
                              </TableCell>
                            )}

                            {showTimestamp && !isTablet && (
                              <TableCell align="center">
                                <Box>
                                  {stock.breakout_time &&
                                  stock.breakout_time !== "N/A" ? (
                                    <Box>
                                      <Typography
                                        variant="body2"
                                        sx={{
                                          fontSize: "0.7rem",
                                          fontWeight: 600,
                                          color: stock.is_fresh
                                            ? colors.accent
                                            : "text.primary",
                                          display: "flex",
                                          alignItems: "center",
                                          justifyContent: "center",
                                          gap: 0.5,
                                        }}
                                      >
                                        {stock.is_fresh && "🔥"}{" "}
                                        {stock.breakout_time}
                                      </Typography>
                                      {stock.time_ago &&
                                        stock.time_ago !== "N/A" && (
                                          <Typography
                                            variant="caption"
                                            sx={{
                                              fontSize: "0.6rem",
                                              color: "text.secondary",
                                              display: "block",
                                            }}
                                          >
                                            {stock.time_ago}
                                          </Typography>
                                        )}
                                    </Box>
                                  ) : (
                                    <Typography
                                      variant="body2"
                                      color="text.secondary"
                                      sx={{ fontSize: "inherit" }}
                                    >
                                      —
                                    </Typography>
                                  )}
                                </Box>
                              </TableCell>
                            )}

                            {/* Option Chain Button Column */}
                            {showOptionChain && (
                              <TableCell align="center">
                                <Tooltip
                                  title="View Option Chain"
                                  placement="left"
                                >
                                  <Box
                                    component="button"
                                    onClick={() =>
                                      handleOptionChainClick(stock)
                                    }
                                    sx={{
                                      background: "none",
                                      border: "none",
                                      cursor: "pointer",
                                      display: "flex",
                                      alignItems: "center",
                                      justifyContent: "center",
                                      padding: 0.5,
                                      borderRadius: 0.5,
                                      color: colors.accent,
                                      width: "100%",
                                      "&:hover": {
                                        bgcolor: `${colors.accent}20`,
                                        transform: "scale(1.1)",
                                      },
                                      transition: "all 0.15s ease",
                                    }}
                                  >
                                    <OptionsIcon sx={{ fontSize: "1.1rem" }} />
                                  </Box>
                                </Tooltip>
                              </TableCell>
                            )}
                          </motion.tr>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>

              {/* Fixed Table Footer */}
              <Box
                sx={{
                  flexShrink: 0,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  p: 1.5,
                  pt: 1,
                  bgcolor: "background.paper",
                  borderTop: `1px solid ${colors.border}`,
                  flexWrap: "wrap",
                  gap: 1,
                }}
              >
                <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                  <Chip
                    label={`${Math.min(data.length, maxItems)} / ${
                      data.length
                    }`}
                    size="small"
                    color="primary"
                    variant="outlined"
                    sx={{ fontSize: "0.65rem" }}
                  />
                  {data.length > maxItems && (
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary", fontSize: "0.6rem" }}
                    >
                      Top {maxItems}
                    </Typography>
                  )}
                </Box>

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    fontSize: "0.6rem",
                  }}
                >
                  <Info sx={{ fontSize: 10 }} />
                  {new Date().toLocaleTimeString()}
                </Typography>
              </Box>
            </>
          )}
        </Box>

        {/* Option Chain Modal */}
        {showOptionChain && (
          <OptionChainModal
            open={optionChainOpen}
            onClose={() => {
              setOptionChainOpen(false);
              setSelectedStock(null);
            }}
            symbol={selectedStock?.symbol}
            stockData={selectedStock}
          />
        )}
      </>
    );
  }
);

StocksList.displayName = "StocksList";

export default StocksList;
