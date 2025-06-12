import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Grid,
  Alert,
  Skeleton,
  Badge,
  Tooltip,
  Button,
  LinearProgress,
  alpha,
  useTheme,
  useMediaQuery,
  Stack,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Refresh as RefreshIcon,
  Psychology as PsychologyIcon,
  Speed as SpeedIcon,
  AutoGraph as AutoGraphIcon,
} from "@mui/icons-material";
import { motion, AnimatePresence } from "framer-motion";
import { useMarket } from "../context/MarketProvider";

// Theme colors (same as your dashboard)
const colors = {
  background: "#0F1923",
  cardBg: "rgba(24, 36, 47, 0.85)",
  accent: "#00E5FF",
  accentDark: "#0097A7",
  positive: "#00E676",
  negative: "#FF5252",
  neutral: "#78909C",
  text: {
    primary: "#ECEFF1",
    secondary: "#B0BEC5",
    muted: "#607D8B",
  },
  border: "rgba(38, 50, 56, 0.6)",
  highlight: "rgba(0, 229, 255, 0.15)",
};

const SelectedStockCard = ({
  stock,
  onClick,
  isCompact = false,
  isMobile = false,
}) => {
  const confidence = stock.analysis?.confidence || stock.confidence || 0;
  const signal = stock.analysis?.signal || stock.signal || "HOLD";
  const currentPrice = stock.analysis?.current_price || stock.entry_price || 0;
  const targetPrice = stock.analysis?.target_price || stock.target_price || 0;
  const stopLoss = stock.analysis?.stop_loss || stock.stop_loss || 0;

  // Calculate potential return
  const potentialReturn =
    targetPrice && currentPrice
      ? ((targetPrice - currentPrice) / currentPrice) * 100
      : 0;

  const getSignalColor = (signal) => {
    switch (signal?.toUpperCase()) {
      case "BUY":
        return colors.positive;
      case "SELL":
        return colors.negative;
      default:
        return colors.neutral;
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return colors.positive;
    if (confidence >= 60) return colors.accent;
    if (confidence >= 40) return colors.neutral;
    return colors.negative;
  };

  return (
    <Card
      component={motion.div}
      whileHover={!isMobile ? { scale: 1.02, y: -2 } : {}}
      whileTap={{ scale: 0.98 }}
      sx={{
        bgcolor: colors.cardBg,
        backdropFilter: "blur(10px)",
        borderRadius: 2,
        border: `1px solid ${colors.border}`,
        cursor: "pointer",
        position: "relative",
        overflow: "hidden",
        transition: "all 0.3s ease",
        height: "100%", // Ensure consistent card heights
        "&:hover": {
          borderColor: colors.accent,
          boxShadow: `0 8px 32px ${alpha(colors.accent, 0.2)}`,
        },
        "&::before": {
          content: '""',
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 4,
          background: `linear-gradient(to bottom, ${getConfidenceColor(
            confidence
          )}, transparent)`,
        },
      }}
      onClick={onClick}
    >
      <CardContent
        sx={{
          p: isMobile ? 1 : isCompact ? 1.5 : 2,
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            mb: 1,
            minHeight: "48px", // Consistent header height
          }}
        >
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              variant={isMobile ? "body1" : isCompact ? "subtitle2" : "h6"}
              sx={{
                color: colors.accent,
                fontWeight: "bold",
                display: "flex",
                alignItems: "center",
                fontSize: isMobile ? "0.9rem" : undefined,
              }}
            >
              <PsychologyIcon
                sx={{
                  mr: 0.5,
                  fontSize: isMobile ? "1rem" : isCompact ? "1rem" : "1.2rem",
                  flexShrink: 0,
                }}
              />
              {stock.symbol}
            </Typography>
            <Typography
              variant="body2"
              sx={{
                color: colors.text.secondary,
                fontSize: isMobile
                  ? "0.7rem"
                  : isCompact
                  ? "0.75rem"
                  : "0.85rem",
                lineHeight: 1.2,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {stock.name || stock.stock_data?.name || "N/A"}
            </Typography>
          </Box>

          {/* Signal Badge */}
          <Chip
            label={signal}
            size="small"
            sx={{
              bgcolor: alpha(getSignalColor(signal), 0.2),
              color: getSignalColor(signal),
              fontWeight: "bold",
              fontSize: isMobile ? "0.6rem" : "0.7rem",
              height: isMobile ? 18 : isCompact ? 20 : 24,
              border: `1px solid ${alpha(getSignalColor(signal), 0.4)}`,
              ml: 1,
              flexShrink: 0,
            }}
          />
        </Box>

        {/* Price Info */}
        <Box sx={{ mb: 1.5, flex: 1 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 0.5,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: colors.text.muted,
                fontSize: isMobile ? "0.65rem" : "0.75rem",
              }}
            >
              Current Price:
            </Typography>
            <Typography
              variant={isMobile ? "caption" : isCompact ? "body2" : "subtitle1"}
              sx={{
                color: colors.text.primary,
                fontWeight: "bold",
                fontFamily: "Roboto Mono, monospace",
                fontSize: isMobile ? "0.8rem" : undefined,
              }}
            >
              ₹{currentPrice?.toFixed(2) || "0.00"}
            </Typography>
          </Box>

          {/* Target & Stop Loss - Show on mobile but in condensed format */}
          {(!isCompact || isMobile) && (
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                mb: 0.5,
                flexDirection: isMobile ? "column" : "row",
                gap: isMobile ? 0.25 : 0,
              }}
            >
              <Box sx={{ flex: 1, mr: isMobile ? 0 : 1 }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: colors.text.muted,
                    fontSize: isMobile ? "0.6rem" : "0.7rem",
                  }}
                >
                  Target: ₹{targetPrice?.toFixed(2) || "0.00"}
                </Typography>
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: colors.text.muted,
                    fontSize: isMobile ? "0.6rem" : "0.7rem",
                  }}
                >
                  Stop: ₹{stopLoss?.toFixed(2) || "0.00"}
                </Typography>
              </Box>
            </Box>
          )}
        </Box>

        {/* Confidence Bar */}
        <Box sx={{ mb: 1 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 0.5,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: colors.text.muted,
                fontSize: isMobile ? "0.6rem" : "0.7rem",
              }}
            >
              AI Confidence
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: getConfidenceColor(confidence),
                fontWeight: "bold",
                fontSize: isMobile ? "0.6rem" : "0.7rem",
              }}
            >
              {confidence?.toFixed(0)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={confidence}
            sx={{
              height: isMobile ? 3 : 4,
              borderRadius: 2,
              bgcolor: alpha(colors.text.primary, 0.1),
              "& .MuiLinearProgress-bar": {
                bgcolor: getConfidenceColor(confidence),
                borderRadius: 2,
              },
            }}
          />
        </Box>

        {/* Potential Return */}
        {potentialReturn > 0 && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              p: isMobile ? 0.25 : 0.5,
              borderRadius: 1,
              bgcolor: alpha(colors.positive, 0.1),
              mb: 0.5,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: colors.text.muted,
                fontSize: isMobile ? "0.6rem" : "0.7rem",
              }}
            >
              Potential Return:
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: colors.positive,
                fontWeight: "bold",
                fontSize: isMobile ? "0.6rem" : "0.7rem",
              }}
            >
              +{potentialReturn.toFixed(1)}%
            </Typography>
          </Box>
        )}

        {/* Analysis Timestamp - Hide on mobile to save space */}
        {!isMobile && stock.analysis?.timestamp && (
          <Typography
            variant="caption"
            sx={{
              color: colors.text.muted,
              fontSize: "0.65rem",
              fontStyle: "italic",
              mt: "auto", // Push to bottom
            }}
          >
            Analyzed: {new Date(stock.analysis.timestamp).toLocaleTimeString()}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

const SelectedStocksPanel = ({ isCompact = false, maxVisible = 6 }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const isTablet = useMediaQuery(theme.breakpoints.down("md"));

  const marketContext = useMarket();
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Safely destructure context with fallbacks
  const {
    selectedStocks = [],
    isLoading = false,
    triggerStockSelection,
    refreshMarketData,
  } = marketContext || {};

  // Adjust maxVisible based on screen size
  const responsiveMaxVisible = isMobile ? 4 : isTablet ? 6 : maxVisible;

  const handleRefresh = async () => {
    if (typeof refreshMarketData === "function") {
      setIsRefreshing(true);
      try {
        await refreshMarketData();
      } finally {
        setIsRefreshing(false);
      }
    } else {
      console.log("Refresh functionality not available");
    }
  };

  const handleTriggerSelection = async () => {
    if (typeof triggerStockSelection === "function") {
      setIsRefreshing(true);
      try {
        await triggerStockSelection();
      } finally {
        setIsRefreshing(false);
      }
    } else {
      console.log("Stock selection functionality not available");
    }
  };

  const handleStockClick = (stock) => {
    console.log("Stock clicked:", stock);
  };

  // Calculate stats
  const totalStocks = selectedStocks?.length || 0;
  const buySignals =
    selectedStocks?.filter(
      (s) => (s.analysis?.signal || s.signal)?.toUpperCase() === "BUY"
    ).length || 0;
  const sellSignals =
    selectedStocks?.filter(
      (s) => (s.analysis?.signal || s.signal)?.toUpperCase() === "SELL"
    ).length || 0;
  const avgConfidence =
    selectedStocks?.length > 0
      ? selectedStocks.reduce(
          (sum, s) => sum + (s.analysis?.confidence || s.confidence || 0),
          0
        ) / selectedStocks.length
      : 0;

  if (isLoading && totalStocks === 0) {
    return (
      <Card
        sx={{ bgcolor: colors.cardBg, border: `1px solid ${colors.border}` }}
      >
        <CardContent sx={{ p: isMobile ? 1 : 2 }}>
          <Skeleton variant="text" width="60%" height={32} sx={{ mb: 1 }} />
          <Grid container spacing={isMobile ? 1 : 2}>
            {Array.from(new Array(isMobile ? 2 : 4)).map((_, index) => (
              <Grid item xs={12} sm={6} md={3} key={index}>
                <Skeleton
                  variant="rectangular"
                  height={isMobile ? 100 : 120}
                  sx={{ borderRadius: 1 }}
                />
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        bgcolor: colors.cardBg,
        border: `1px solid ${colors.border}`,
        backdropFilter: "blur(10px)",
        borderRadius: 2,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: isMobile ? 1.5 : 2,
          borderBottom: `1px solid ${colors.border}`,
          background: `linear-gradient(135deg, ${alpha(
            colors.accent,
            0.1
          )}, transparent)`,
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 1,
            flexDirection: isMobile ? "column" : "row",
            gap: isMobile ? 1 : 0,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <AutoGraphIcon
              sx={{
                mr: 1,
                color: colors.accent,
                fontSize: isMobile ? "1.2rem" : "1.5rem",
              }}
            />
            <Typography
              variant={isMobile ? "subtitle1" : "h6"}
              sx={{
                color: colors.text.primary,
                fontWeight: "bold",
                display: "flex",
                alignItems: "center",
                fontSize: isMobile ? "1rem" : undefined,
              }}
            >
              {isMobile ? "Selected Stocks" : "Selected Stocks for Trading"}
              <Badge
                badgeContent={totalStocks}
                color="primary"
                sx={{
                  ml: 1,
                  "& .MuiBadge-badge": {
                    bgcolor: colors.accent,
                    color: colors.background,
                    fontSize: isMobile ? "0.6rem" : undefined,
                  },
                }}
              >
                <Box sx={{ width: 20 }} />
              </Badge>
            </Typography>
          </Box>

          <Stack direction="row" spacing={1}>
            {/* Refresh button */}
            {typeof refreshMarketData === "function" && (
              <Tooltip title="Refresh Data">
                <IconButton
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  sx={{
                    color: colors.text.secondary,
                    "&:hover": { color: colors.accent },
                  }}
                  size={isMobile ? "small" : "medium"}
                >
                  <RefreshIcon
                    sx={{
                      animation: isRefreshing
                        ? "spin 1s linear infinite"
                        : "none",
                      "@keyframes spin": {
                        "0%": { transform: "rotate(0deg)" },
                        "100%": { transform: "rotate(360deg)" },
                      },
                      fontSize: isMobile ? "1rem" : undefined,
                    }}
                  />
                </IconButton>
              </Tooltip>
            )}

            {/* Trigger button */}
            {typeof triggerStockSelection === "function" && (
              <Tooltip title="Trigger New Selection">
                <Button
                  onClick={handleTriggerSelection}
                  disabled={isRefreshing}
                  variant="outlined"
                  size="small"
                  sx={{
                    color: colors.accent,
                    borderColor: alpha(colors.accent, 0.5),
                    fontSize: isMobile ? "0.65rem" : "0.75rem",
                    px: isMobile ? 1 : 1.5,
                    "&:hover": {
                      borderColor: colors.accent,
                      bgcolor: alpha(colors.accent, 0.1),
                    },
                  }}
                >
                  {isMobile ? "New" : "New Selection"}
                </Button>
              </Tooltip>
            )}
          </Stack>
        </Box>

        {/* Stats Row - Stack vertically on mobile */}
        <Stack
          direction={isMobile ? "column" : "row"}
          spacing={1}
          sx={{
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Chip
            icon={<TrendingUpIcon />}
            label={`${buySignals} BUY`}
            size="small"
            sx={{
              bgcolor: alpha(colors.positive, 0.2),
              color: colors.positive,
              fontWeight: "bold",
              border: `1px solid ${alpha(colors.positive, 0.3)}`,
              fontSize: isMobile ? "0.65rem" : undefined,
            }}
          />
          <Chip
            icon={<TrendingDownIcon />}
            label={`${sellSignals} SELL`}
            size="small"
            sx={{
              bgcolor: alpha(colors.negative, 0.2),
              color: colors.negative,
              fontWeight: "bold",
              border: `1px solid ${alpha(colors.negative, 0.3)}`,
              fontSize: isMobile ? "0.65rem" : undefined,
            }}
          />
          <Chip
            icon={<SpeedIcon />}
            label={`${avgConfidence.toFixed(0)}% ${
              isMobile ? "Conf" : "Avg Confidence"
            }`}
            size="small"
            sx={{
              bgcolor: alpha(colors.accent, 0.2),
              color: colors.accent,
              fontWeight: "bold",
              border: `1px solid ${alpha(colors.accent, 0.3)}`,
              fontSize: isMobile ? "0.65rem" : undefined,
            }}
          />
        </Stack>
      </Box>

      {/* Content */}
      <CardContent sx={{ p: isMobile ? 1 : 2 }}>
        {totalStocks === 0 ? (
          <Alert
            severity="info"
            sx={{
              bgcolor: alpha(colors.accent, 0.1),
              border: `1px solid ${alpha(colors.accent, 0.3)}`,
              color: colors.text.primary,
              "& .MuiAlert-icon": {
                color: colors.accent,
              },
              fontSize: isMobile ? "0.8rem" : undefined,
            }}
          >
            {isMobile
              ? "No stocks selected yet. Trigger selection when ready."
              : "No stocks selected yet. AI will select stocks when market opens or you can trigger manual selection."}
          </Alert>
        ) : (
          <Grid container spacing={isMobile ? 1 : isCompact ? 1 : 2}>
            <AnimatePresence>
              {selectedStocks
                .slice(0, responsiveMaxVisible)
                .map((stock, index) => (
                  <Grid
                    item
                    xs={12}
                    sm={6}
                    md={isCompact ? 4 : 4}
                    lg={isCompact ? 3 : 3}
                    xl={2}
                    key={stock.symbol || index}
                  >
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <SelectedStockCard
                        stock={stock}
                        onClick={() => handleStockClick(stock)}
                        isCompact={isCompact}
                        isMobile={isMobile}
                      />
                    </motion.div>
                  </Grid>
                ))}
            </AnimatePresence>
          </Grid>
        )}

        {/* Show More Button */}
        {totalStocks > responsiveMaxVisible && (
          <Box sx={{ textAlign: "center", mt: 2 }}>
            <Button
              variant="outlined"
              sx={{
                color: colors.accent,
                borderColor: alpha(colors.accent, 0.5),
                fontSize: isMobile ? "0.8rem" : undefined,
                "&:hover": {
                  borderColor: colors.accent,
                  bgcolor: alpha(colors.accent, 0.1),
                },
              }}
            >
              View All {totalStocks} Stocks
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default SelectedStocksPanel;
