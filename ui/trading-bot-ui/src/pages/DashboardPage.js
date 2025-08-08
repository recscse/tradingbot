// pages/DashboardPage.jsx - FULLY RESPONSIVE & REDESIGNED VERSION (SINGLE COLUMN FOR PAIRED SECTIONS)
import React, { useState, useMemo, useCallback, useEffect } from "react";
import {
  useTheme,
  useMediaQuery,
  Box,
  Grid,
  Stack,
  Paper,
  Typography,
  Chip,
  Button,
  Select,
  MenuItem,
  InputBase,
  AppBar,
  Toolbar,
  Container,
  IconButton,
  Card,
  CardContent,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
} from "@mui/icons-material";
import StocksList from "../components/common/StocksList";
import TipRanksHeatmap from "../components/common/TipRanksHeatmap";
import FinancialHeatmap from "../components/common/FinancialHeatmap";
import { useMarket } from "../hooks/useUnifiedMarketData";
// PERFORMANCE FIX: Memoized components to prevent unnecessary re-renders
const MemoizedStocksList = React.memo(StocksList);
// MODERN THEME COLORS - Enhanced design system
const DASHBOARD_COLORS = {
  // Dark theme
  dark: {
    background: "#0a0e1a",
    surface: "#1e293b",
    surfaceHover: "#334155",
    text: "#e2e8f0",
    textSecondary: "#94a3b8",
    positive: "#22c55e",
    negative: "#ef4444",
    neutral: "#f59e0b",
    primary: "#3b82f6",
    secondary: "#8b5cf6",
    accent: "#06b6d4",
    border: "#475569",
    cardBackground: "#1e293b",
    gradient: "linear-gradient(135deg, #1e293b 0%, #334155 100%)",
    header: "#3b82f6", // Added for consistency
  },
  // Light theme
  light: {
    background: "#f8fafc",
    surface: "#ffffff",
    surfaceHover: "#f1f5f9",
    text: "#1e293b",
    textSecondary: "#64748b",
    positive: "#16a34a",
    negative: "#dc2626",
    neutral: "#d97706",
    primary: "#2563eb",
    secondary: "#7c3aed",
    accent: "#0891b2",
    border: "#e2e8f0",
    cardBackground: "#ffffff",
    gradient: "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)",
    header: "#2563eb", // Added for consistency
  },
};
// Section navigation - moved outside component
const SECTIONS = [
  { id: "overview", label: "OVERVIEW", icon: "📊" },
  { id: "search", label: "SEARCH", icon: "🔍" },
  { id: "sectors", label: "SECTORS", icon: "🏢" },
  { id: "movers", label: "TOP MOVERS", icon: "🚀" },
  { id: "gaps", label: "GAP ANALYSIS", icon: "📈" },
  { id: "indices", label: "INDICES", icon: "🏛️" },
  { id: "mcx", label: "MCX & F&O", icon: "💰" },
  { id: "fno", label: "FNO STOCKS", icon: "📋" },
  { id: "analytics", label: "ANALYTICS", icon: "🔍" },
];
// FIXED: Helper function to safely extract numeric values
const safeNumber = (value, defaultValue = 0) => {
  if (value === null || value === undefined || value === "")
    return defaultValue;
  const num = Number(value);
  return isNaN(num) ? defaultValue : num;
};
// FIXED: Helper function to process market data consistently
const processMarketDataEntry = (key, data) => {
  if (!data || typeof data !== "object") return null;
  return {
    instrument_key: key,
    symbol: data.symbol || data.trading_symbol || key.split("|").pop() || key,
    name: data.name || data.symbol || key.split("|").pop() || key,
    last_price: safeNumber(data.ltp || data.last_price || data.price),
    change: safeNumber(data.change),
    change_percent: safeNumber(data.change_percent || data.pchange),
    volume: safeNumber(data.volume || data.daily_volume || data.vol),
    high: safeNumber(data.high),
    low: safeNumber(data.low),
    open: safeNumber(data.open),
    close: safeNumber(data.close),
    sector: data.sector || "OTHER",
    exchange:
      data.exchange ||
      (key.includes("NSE")
        ? "NSE"
        : key.includes("MCX")
        ? "MCX"
        : key.includes("BSE")
        ? "BSE"
        : "UNKNOWN"),
    instrument_type: data.instrument_type || "EQ",
    timestamp: data.timestamp || data.last_updated || Date.now(),
  };
};
// Component for Fixed/Sticky Section Navigation
const SectionNavigation = ({
  activeSection,
  handleSectionChange,
  colors,
  isMobile,
}) => {
  const theme = useTheme();
  const isExtraSmall = useMediaQuery(theme.breakpoints.down("xs"));
  const [isScrolled, setIsScrolled] = React.useState(false);
  const scrollContainerRef = React.useRef(null);
  
  // Handle scroll effect for sticky header
  React.useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 100);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-scroll to active tab on mobile
  React.useEffect(() => {
    if (isMobile && scrollContainerRef.current) {
      const activeButton = scrollContainerRef.current.querySelector(
        `[data-section="${activeSection}"]`
      );
      if (activeButton) {
        activeButton.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "center",
        });
      }
    }
  }, [activeSection, isMobile]);

  return (
    <Box
      sx={{
        position: "sticky",
        top: 0,
        zIndex: 1000,
        bgcolor: "background.paper",
        borderBottom: `1px solid ${colors.border}`,
        backdropFilter: "blur(10px)",
        boxShadow: isScrolled ? theme.shadows[2] : "none",
        transition: "all 0.2s ease",
      }}
    >
      <Container maxWidth="xl">
        <Box
          sx={{
            py: { xs: 0.75, sm: 1 },
            px: { xs: 1, sm: 2 },
          }}
        >
          {/* Mobile Horizontal Scroll Layout */}
          {isMobile ? (
            <Box
              ref={scrollContainerRef}
              sx={{
                display: "flex",
                overflowX: "auto",
                overflowY: "hidden",
                gap: 0.75,
                pb: 0.5,
                "&::-webkit-scrollbar": {
                  height: 3,
                },
                "&::-webkit-scrollbar-track": {
                  backgroundColor: colors.border,
                  borderRadius: 2,
                },
                "&::-webkit-scrollbar-thumb": {
                  backgroundColor: colors.primary,
                  borderRadius: 2,
                },
              }}
            >
              {SECTIONS.map((section) => (
                <Button
                  key={section.id}
                  onClick={() => handleSectionChange(section.id)}
                  data-section={section.id}
                  variant={activeSection === section.id ? "contained" : "outlined"}
                  size="small"
                  sx={{
                    minWidth: isExtraSmall ? 70 : 85,
                    flexShrink: 0,
                    px: 1.5,
                    py: 0.75,
                    height: 36,
                    fontSize: "0.7rem",
                    fontWeight: activeSection === section.id ? 600 : 500,
                    borderRadius: 2,
                    textTransform: "none",
                    whiteSpace: "nowrap",
                    transition: "all 0.2s ease",
                    position: "relative",
                    
                    // Clean active state
                    ...(activeSection === section.id && {
                      bgcolor: colors.primary,
                      borderColor: colors.primary,
                      color: "white",
                      boxShadow: `0 2px 8px ${colors.primary}40`,
                      "&::after": {
                        content: '""',
                        position: "absolute",
                        bottom: -1,
                        left: "50%",
                        transform: "translateX(-50%)",
                        width: "60%",
                        height: 2,
                        bgcolor: colors.accent,
                        borderRadius: 1,
                      },
                    }),

                    "&:hover": {
                      transform: "translateY(-1px)",
                      ...(activeSection === section.id ? {
                        boxShadow: `0 4px 12px ${colors.primary}50`,
                      } : {
                        bgcolor: colors.surfaceHover,
                        borderColor: colors.primary,
                      }),
                    },
                    
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                  }}
                >
                  <span style={{ fontSize: "0.9rem" }}>{section.icon}</span>
                  {!isExtraSmall && (
                    <span>{section.label.length > 7 ? section.label.substring(0, 5) + "..." : section.label}</span>
                  )}
                </Button>
              ))}
            </Box>
          ) : (
            /* Desktop/Tablet Clean Grid Layout */
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  sm: "repeat(3, 1fr)",
                  md: "repeat(4, 1fr)",
                  lg: "repeat(5, 1fr)",
                  xl: "repeat(9, 1fr)",
                },
                gap: { xs: 0.75, sm: 1 },
                maxWidth: "100%",
              }}
            >
              {SECTIONS.map((section) => (
                <Button
                  key={section.id}
                  onClick={() => handleSectionChange(section.id)}
                  data-section={section.id}
                  variant={activeSection === section.id ? "contained" : "outlined"}
                  size="small"
                  sx={{
                    minWidth: 0,
                    px: { xs: 1, sm: 1.5 },
                    py: { xs: 1, sm: 1.25 },
                    height: { xs: 40, sm: 44 },
                    fontSize: { xs: "0.7rem", sm: "0.75rem" },
                    fontWeight: activeSection === section.id ? 600 : 500,
                    borderRadius: 2,
                    textTransform: "none",
                    transition: "all 0.2s ease",
                    position: "relative",
                    
                    // Clean active state
                    ...(activeSection === section.id && {
                      bgcolor: colors.primary,
                      borderColor: colors.primary,
                      color: "white",
                      boxShadow: `0 3px 10px ${colors.primary}40`,
                      "&::after": {
                        content: '""',
                        position: "absolute",
                        bottom: -1,
                        left: "50%",
                        transform: "translateX(-50%)",
                        width: "70%",
                        height: 2,
                        bgcolor: colors.accent,
                        borderRadius: 1,
                      },
                    }),

                    "&:hover": {
                      transform: "translateY(-2px)",
                      ...(activeSection === section.id ? {
                        boxShadow: `0 6px 16px ${colors.primary}50`,
                      } : {
                        bgcolor: colors.surfaceHover,
                        borderColor: colors.primary,
                        boxShadow: `0 2px 8px ${colors.border}30`,
                      }),
                    },
                    
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 0.5,
                  }}
                >
                  <span style={{ fontSize: { xs: "1rem", sm: "1.1rem" } }}>{section.icon}</span>
                  <span style={{ 
                    fontSize: "inherit", 
                    lineHeight: 1.1,
                    textAlign: "center"
                  }}>
                    {section.label}
                  </span>
                </Button>
              ))}
            </Box>
          )}
        </Box>
      </Container>
    </Box>
  );
};
const DashboardPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md")); // Unused currently
  // const isSmallScreen = useMediaQuery(theme.breakpoints.down("md")); // Not used anymore
  // Get current theme colors
  const colors = DASHBOARD_COLORS[theme.palette.mode] || DASHBOARD_COLORS.light;
  const {
    isConnected,
    connectionStatus,
    marketData,
    marketStatus,
    totalStocks,
    sectors,
    topMovers,
    gapAnalysis,
    breakoutAnalysis,
    marketSentiment,
    heatmap,
    volumeAnalysis,
    intradayStocks,
    recordMovers,
    isStale,
    reconnect,
    getStocksBySector,
    searchStocks,
    getMarketSummary,
    indicesData,
    totalIndices,
    majorIndicesCount,
    getIndicesByPerformance,
    getMarketSentimentFromIndices,
    getIndicesSummary,
  } = useMarket();
  const [activeSection, setActiveSection] = useState("overview");
  const [expandedSection, setExpandedSection] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSector, setSelectedSector] = useState("ALL");
  const [fnoStockList, setFnoStockList] = useState({
    securities: [],
    total_count: 0,
  });
  const [fnoLoading, setFnoLoading] = useState(false);
  // REMOVED: Using Material-UI useMediaQuery for responsive detection
  // Fetch FNO stocks from API
  const fetchFnoStocks = useCallback(async () => {
    if (fnoLoading) return;
    setFnoLoading(true);
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/api/instruments/fno-stocks`
      );
      const data = await response.json();
      if (data.success && data.stocks) {
        setFnoStockList({
          securities: data.stocks,
          total_count: data.count || data.stocks.length,
        });
      }
    } catch (error) {
      console.error("Failed to fetch FNO stocks:", error);
    } finally {
      setFnoLoading(false);
    }
  }, [fnoLoading]);
  // Load FNO stocks when component mounts or when FNO section is accessed
  useEffect(() => {
    if (activeSection === "fno" && fnoStockList.securities.length === 0) {
      fetchFnoStocks();
    }
  }, [activeSection, fetchFnoStocks, fnoStockList.securities.length]);
  // PERFORMANCE FIX: Memoized market summary
  const marketSummary = useMemo(() => getMarketSummary(), [getMarketSummary]);
  // PERFORMANCE FIX: Memoized search results
  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return [];
    return searchStocks(searchQuery);
  }, [searchQuery, searchStocks]);
  // PERFORMANCE FIX: Memoized sector stocks
  const sectorStocks = useMemo(() => {
    if (selectedSector === "ALL") return Object.values(marketData || {});
    const stocksBySector = getStocksBySector();
    return stocksBySector[selectedSector] || [];
  }, [selectedSector, getStocksBySector, marketData]);
  const indicesSummary = useMemo(
    () => getIndicesSummary(),
    [getIndicesSummary]
  );
  const indicesPerformance = useMemo(
    () => getIndicesByPerformance(),
    [getIndicesByPerformance]
  );
  const indicesSentiment = useMemo(
    () => getMarketSentimentFromIndices(),
    [getMarketSentimentFromIndices]
  );
  // Helper function to identify indices
  const isIndexSymbol = useCallback((symbol, name) => {
    if (!symbol && !name) return false;
    const symbolLower = (symbol || "").toLowerCase();
    const nameLower = (name || "").toLowerCase();
    // Common index identifiers
    const indexKeywords = [
      "nifty",
      "sensex",
      "banknifty",
      "finnifty",
      "midcpnifty",
      "index",
    ];
    return (
      indexKeywords.some(
        (keyword) =>
          symbolLower.includes(keyword) || nameLower.includes(keyword)
      ) || symbolLower.match(/^(nifty|sensex|banknifty|finnifty|midcpnifty)/)
    );
  }, []);
  // PERFORMANCE FIX: Memoized FNO stocks processing with categorization
  const fnoStocksData = useMemo(() => {
    const processedStocks = fnoStockList.securities.map((stock, index) => ({
      instrument_key: `${stock.exchange || "NSE"}|${stock.symbol}`,
      symbol: stock.symbol,
      name: stock.name,
      exchange: stock.exchange || "NSE",
      last_price: 0,
      change: 0,
      change_percent: 0,
      volume: 0,
      sector: "F&O",
      timestamp: Date.now(),
      is_index: isIndexSymbol(stock.symbol, stock.name),
    }));
    // Sort: indices first (alphabetically), then stocks (alphabetically)
    return processedStocks.sort((a, b) => {
      if (a.is_index && !b.is_index) return -1;
      if (!a.is_index && b.is_index) return 1;
      return (a.name || a.symbol).localeCompare(b.name || b.symbol);
    });
  }, [fnoStockList.securities, isIndexSymbol]);
  // Separate indices and stocks for categorized display
  const { fnoIndices, fnoStocks } = useMemo(() => {
    const indices = fnoStocksData.filter((stock) => stock.is_index);
    const stocks = fnoStocksData.filter((stock) => !stock.is_index);
    return {
      fnoIndices: indices,
      fnoStocks: stocks,
    };
  }, [fnoStocksData]);
  // Process live data for categorized stocks
  const { fnoIndicesWithLiveData, fnoStocksWithLiveData } = useMemo(() => {
    const addLiveData = (stocksArray) => {
      if (!marketData || Object.keys(marketData).length === 0) {
        return stocksArray;
      }
      return stocksArray.map((stock) => {
        const liveDataKey = Object.keys(marketData).find(
          (key) =>
            key.includes(stock.symbol) ||
            key.toLowerCase().includes(stock.symbol.toLowerCase())
        );
        if (liveDataKey && marketData[liveDataKey]) {
          const liveData = marketData[liveDataKey];
          return {
            ...stock,
            last_price: safeNumber(
              liveData.ltp || liveData.last_price || liveData.price
            ),
            change: safeNumber(liveData.change),
            change_percent: safeNumber(
              liveData.change_percent || liveData.pchange
            ),
            volume: safeNumber(liveData.volume),
            high: safeNumber(liveData.high),
            low: safeNumber(liveData.low),
            open: safeNumber(liveData.open), // Fixed typo: opcoloren -> open
            close: safeNumber(liveData.close),
          };
        }
        return stock;
      });
    };
    return {
      fnoIndicesWithLiveData: addLiveData(fnoIndices),
      fnoStocksWithLiveData: addLiveData(fnoStocks),
    };
  }, [fnoIndices, fnoStocks, marketData]);
  // FIXED: Heavily optimized data processing
  const processedData = useMemo(() => {
    const marketDataEntries = Object.entries(marketData || {});
    const analyticsIndices = indicesData?.indices || [];
    const majorIndices = indicesData?.major_indices || [];
    const sectorIndices = indicesData?.sector_indices || [];
    // FIXED: Improved index detection with multiple criteria
    const manualIndices =
      analyticsIndices.length === 0
        ? marketDataEntries
            .map(([key, data]) => processMarketDataEntry(key, data))
            .filter((item) => {
              if (!item || !item.last_price) return false;
              const keyLower = item.instrument_key.toLowerCase();
              const symbolLower = item.symbol.toLowerCase();
              const nameLower = (item.name || "").toLowerCase();
              const indexIndicators = [
                keyLower.includes("index"),
                keyLower.includes("nifty"),
                keyLower.includes("sensex"),
                keyLower.includes("banknifty"),
                keyLower.includes("finnifty"),
                keyLower.includes("midcpnifty"),
                symbolLower.match(
                  /^(nifty|sensex|banknifty|finnifty|midcpnifty)$/
                ),
                nameLower.includes("index"),
                item.instrument_type === "INDEX",
                item.exchange === "INDEX",
              ];
              return indexIndicators.some(Boolean);
            })
            .sort(
              (a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent)
            )
        : [];
    const indices =
      analyticsIndices.length > 0 ? analyticsIndices : manualIndices;
    // FIXED: Improved equity filtering with better exclusion (commented out as unused)
    // const equityStocks = marketDataEntries
    //   .map(([key, data]) => processMarketDataEntry(key, data))
    //   .filter((item) => {
    //     if (!item || !item.last_price) return false;
    //     const keyLower = item.instrument_key.toLowerCase();
    //     const symbolLower = item.symbol.toLowerCase();
    //     const isIndex = [
    //       keyLower.includes("index"),
    //       keyLower.includes("nifty"),
    //       keyLower.includes("sensex"),
    //       keyLower.includes("banknifty"),
    //       keyLower.includes("finnifty"),
    //       keyLower.includes("midcpnifty"),
    //       symbolLower.match(/^(nifty|sensex|banknifty|finnifty|midcpnifty)$/),
    //     ].some(Boolean);
    //     const isEquity =
    //       (keyLower.includes("nse") || keyLower.includes("eq")) && !isIndex;
    //     return isEquity;
    //   })
    //   .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent));
    // Process MCX data
    const mcxStocks = marketDataEntries
      .map(([key, data]) => processMarketDataEntry(key, data))
      .filter((item) => {
        return item && item.exchange === "MCX" && item.last_price;
      })
      .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent));
    // FIXED: Better analytics data extraction with comprehensive error handling
    const extractAnalyticsData = (analyticsObject, arrayKey, limit = 50) => {
      try {
        if (!analyticsObject || typeof analyticsObject !== "object") {
          return [];
        }
        let data = analyticsObject[arrayKey];
        if (!data && analyticsObject.data) {
          data = analyticsObject.data[arrayKey];
        }
        if (!Array.isArray(data)) {
          return [];
        }
        const validData = data
          .filter((item) => item && typeof item === "object" && item.symbol)
          .map((item) => ({
            symbol: item.symbol || item.trading_symbol || "N/A",
            name: item.name || item.symbol || item.trading_symbol || "N/A",
            last_price: safeNumber(item.last_price || item.ltp || item.price),
            change: safeNumber(item.change),
            change_percent: safeNumber(item.change_percent || item.pchange),
            volume: safeNumber(item.volume || item.daily_volume),
            sector: item.sector || "OTHER",
            exchange: item.exchange || "NSE",
            instrument_key: item.instrument_key || `${item.symbol}_KEY`,
            ...item,
          }))
          .slice(0, limit);
        return validData;
      } catch (error) {
        return [];
      }
    };
    const topGainers = extractAnalyticsData(topMovers, "gainers", 20);
    const topLosers = extractAnalyticsData(topMovers, "losers", 20);
    const gapUp = extractAnalyticsData(gapAnalysis, "gap_up", 20);
    const gapDown = extractAnalyticsData(gapAnalysis, "gap_down", 20);
    const intradayBoosters = extractAnalyticsData(
      intradayStocks,
      "all_candidates",
      30
    );
    const volumeLeaders = extractAnalyticsData(
      volumeAnalysis,
      "volume_leaders",
      25
    );
    const newHighs = extractAnalyticsData(recordMovers, "new_highs", 20);
    const newLows = extractAnalyticsData(recordMovers, "new_lows", 20);
    const breakouts = extractAnalyticsData(breakoutAnalysis, "breakouts", 20);
    const breakdowns = extractAnalyticsData(breakoutAnalysis, "breakdowns", 20);
    return {
      indices,
      majorIndices,
      sectorIndices,
      // equityStocks, // Commented out since variable is commented
      mcxStocks,
      topGainers,
      topLosers,
      gapUp,
      gapDown,
      intradayBoosters,
      volumeLeaders,
      newHighs,
      newLows,
      breakouts,
      breakdowns,
    };
  }, [
    marketData,
    indicesData,
    topMovers,
    gapAnalysis,
    intradayStocks,
    volumeAnalysis,
    recordMovers,
    breakoutAnalysis,
  ]);

  // Destructure processed data to make it available in component scope
  const {
    indices,
    majorIndices,
    sectorIndices,
    // equityStocks, // Commented out - reserved for equity stocks filtering
    mcxStocks,
    topGainers,
    topLosers,
    gapUp,
    gapDown,
    intradayBoosters,
    volumeLeaders,
    newHighs,
    newLows,
    breakouts,
    breakdowns,
  } = processedData;

  // PERFORMANCE FIX: Memoized market status display
  const marketStatusDisplay = useMemo(() => {
    switch (marketStatus) {
      case "normal_open":
      case "open":
        return {
          text: "MARKET OPEN",
          color: colors.positive,
          icon: "🟢",
        };
      case "pre_market":
        return {
          text: "PRE-MARKET",
          color: colors.neutral,
          icon: "🟡",
        };
      case "after_market":
        return {
          text: "AFTER-MARKET",
          color: colors.accent,
          icon: "🔵",
        };
      case "closed":
      default:
        return {
          text: "MARKET CLOSED",
          color: colors.negative,
          icon: "🔴",
        };
    }
  }, [marketStatus, colors]);
  // PERFORMANCE FIX: Memoized callback functions
  const toggleExpanded = useCallback(
    (section) =>
      setExpandedSection(expandedSection === section ? null : section),
    [expandedSection]
  );
  const handleSectionChange = useCallback((sectionId) => {
    setActiveSection(sectionId);
    // Smooth scroll to top when changing sections
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);
  const handleSearchChange = useCallback(
    (e) => setSearchQuery(e.target.value),
    []
  );
  const handleSectorChange = useCallback(
    (e) => setSelectedSector(e.target.value),
    []
  );
  // Render function for the header (RESPONSIVE MARKET LIVE TERMINAL)
  const renderHeader = () => (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: "background.paper",
        color: "text.primary",
        borderBottom: `1px solid ${colors.border}`,
        backdropFilter: "blur(10px)",
        background: `linear-gradient(135deg, ${colors.cardBackground}95 0%, ${colors.surface}95 100%)`,
      }}
    >
      <Container maxWidth="xl">
        <Toolbar
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "stretch",
            py: { xs: 0.75, sm: 1 },
            px: { xs: 1, sm: 2 },
            minHeight: "auto",
          }}
        >
          {/* Bloomberg-Style Terminal Header */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              minHeight: { xs: 40, sm: 48 },
              flexWrap: "nowrap",
              overflow: "hidden",
            }}
          >
            {/* Terminal Title with Professional Styling */}
            <Box sx={{ display: "flex", alignItems: "center", flex: 1, minWidth: 0 }}>
              <Typography
                variant={isMobile ? "h6" : "h5"}
                component="div"
                sx={{
                  fontWeight: 700,
                  fontSize: { xs: "1rem", sm: "1.25rem", md: "1.5rem" },
                  fontFamily: '"SF Pro Display", "Segoe UI", sans-serif',
                  background: `linear-gradient(135deg, ${colors.primary}, ${colors.accent})`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  letterSpacing: { xs: "0.5px", sm: "1px" },
                  textTransform: "uppercase",
                  display: "flex",
                  alignItems: "center",
                  gap: 0.75,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                <Box
                  component="span"
                  sx={{
                    fontSize: { xs: "1.2rem", sm: "1.5rem" },
                    filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.3))",
                  }}
                >
                  📈
                </Box>
                {isMobile ? "TERMINAL" : "LIVE MARKET TERMINAL"}
              </Typography>
              
              {/* Live Indicator */}
              <Box
                sx={{
                  ml: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 0.5,
                }}
              >
                <Box
                  sx={{
                    width: { xs: 6, sm: 8 },
                    height: { xs: 6, sm: 8 },
                    borderRadius: "50%",
                    bgcolor: isConnected ? colors.positive : colors.negative,
                    animation: isConnected ? "pulse 2s infinite" : "none",
                    boxShadow: isConnected 
                      ? `0 0 10px ${colors.positive}50` 
                      : `0 0 10px ${colors.negative}50`,
                    "@keyframes pulse": {
                      "0%": { opacity: 1, transform: "scale(1)" },
                      "50%": { opacity: 0.7, transform: "scale(1.1)" },
                      "100%": { opacity: 1, transform: "scale(1)" },
                    },
                  }}
                />
              </Box>
            </Box>

            {/* Status Indicators - Professional Bloomberg Style */}
            <Box sx={{ 
              display: "flex", 
              gap: { xs: 0.5, sm: 0.75, md: 1 }, 
              flexShrink: 0,
              alignItems: "center",
            }}>
              {/* Market Status */}
              <Chip
                icon={<span style={{ fontSize: "0.8rem" }}>{marketStatusDisplay.icon}</span>}
                label={
                  isMobile && marketStatusDisplay.text.length > 8
                    ? marketStatusDisplay.text.substring(0, 6)
                    : marketStatusDisplay.text
                }
                size="small"
                sx={{
                  bgcolor: marketStatusDisplay.color,
                  color: "white",
                  fontWeight: 600,
                  fontSize: { xs: "0.65rem", sm: "0.7rem" },
                  height: { xs: 22, sm: 26 },
                  borderRadius: 1,
                  boxShadow: `0 2px 8px ${marketStatusDisplay.color}30`,
                  "& .MuiChip-icon": {
                    color: "white",
                    ml: 0.25,
                    mr: -0.25,
                  },
                  "& .MuiChip-label": {
                    px: { xs: 0.75, sm: 1 },
                    fontFamily: '"SF Mono", "Consolas", monospace',
                  },
                }}
              />
              
              {/* Connection Status */}
              <Chip
                label={
                  isMobile ? (isConnected ? "CONN" : "DISC") : connectionStatus
                }
                size="small"
                sx={{
                  bgcolor: isConnected ? colors.positive : colors.negative,
                  color: "white",
                  fontWeight: 600,
                  fontSize: { xs: "0.65rem", sm: "0.7rem" },
                  height: { xs: 22, sm: 26 },
                  borderRadius: 1,
                  boxShadow: isConnected 
                    ? `0 2px 8px ${colors.positive}30` 
                    : `0 2px 8px ${colors.negative}30`,
                  cursor: !isConnected ? "pointer" : "default",
                  transition: "all 0.2s ease",
                  "&:hover": !isConnected ? {
                    transform: "translateY(-1px)",
                    boxShadow: isConnected 
                      ? `0 3px 12px ${colors.positive}40` 
                      : `0 3px 12px ${colors.negative}40`,
                  } : {},
                  "& .MuiChip-label": {
                    px: { xs: 0.75, sm: 1 },
                    fontFamily: '"SF Mono", "Consolas", monospace',
                  },
                }}
                onClick={!isConnected ? reconnect : undefined}
              />

              {/* Refresh Button for Disconnected State */}
              {!isConnected && (
                <IconButton
                  size="small"
                  onClick={reconnect}
                  sx={{
                    width: { xs: 24, sm: 28 },
                    height: { xs: 24, sm: 28 },
                    bgcolor: colors.primary,
                    color: "white",
                    borderRadius: 1,
                    "&:hover": {
                      bgcolor: colors.accent,
                      transform: "translateY(-1px)",
                      boxShadow: `0 4px 12px ${colors.primary}40`,
                    },
                    transition: "all 0.2s ease",
                  }}
                >
                  <RefreshIcon sx={{ fontSize: { xs: 14, sm: 16 } }} />
                </IconButton>
              )}

              {/* Data Staleness Indicator */}
              {isStale && (
                <Chip
                  label="STALE"
                  size="small"
                  sx={{
                    bgcolor: colors.neutral,
                    color: "white",
                    fontWeight: 600,
                    fontSize: { xs: "0.6rem", sm: "0.65rem" },
                    height: { xs: 20, sm: 24 },
                    borderRadius: 1,
                    "& .MuiChip-label": {
                      px: 0.5,
                      fontFamily: '"SF Mono", "Consolas", monospace',
                    },
                  }}
                />
              )}
            </Box>
          </Box>

          {/* Market Statistics - Professional Terminal Style */}
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: { xs: 0.5, sm: 0.75 },
              justifyContent: "flex-start",
              mt: { xs: 0.75, sm: 1 },
              pt: { xs: 0.75, sm: 1 },
              borderTop: `1px solid ${colors.border}30`,
            }}
          >
            {[
              { icon: "📊", value: totalStocks, label: "STOCKS", color: colors.primary },
              { icon: "🏢", value: sectors.length, label: "SECTORS", color: colors.secondary },
              { icon: "📈", value: totalIndices || indices.length, label: "INDICES", color: colors.accent },
              ...(majorIndicesCount > 0 ? [{ icon: "🏛️", value: majorIndicesCount, label: "MAJOR", color: colors.positive }] : []),
              ...(isConnected ? [{ icon: "⚡", value: "LIVE", label: "DATA", color: colors.positive }] : []),
            ].map((stat, index) => (
              <Chip
                key={index}
                icon={<span style={{ fontSize: "0.75rem" }}>{stat.icon}</span>}
                label={`${stat.value} ${stat.label}`}
                size="small"
                variant="outlined"
                sx={{
                  fontSize: { xs: "0.6rem", sm: "0.65rem" },
                  height: { xs: 20, sm: 24 },
                  borderColor: stat.color,
                  color: stat.color,
                  bgcolor: `${stat.color}08`,
                  fontWeight: 600,
                  borderRadius: 1,
                  "& .MuiChip-icon": {
                    color: stat.color,
                    ml: 0.25,
                    mr: -0.25,
                  },
                  "& .MuiChip-label": {
                    px: { xs: 0.5, sm: 0.75 },
                    fontFamily: '"SF Mono", "Consolas", monospace',
                  },
                  transition: "all 0.2s ease",
                  "&:hover": {
                    bgcolor: `${stat.color}15`,
                    borderColor: stat.color,
                    transform: "translateY(-1px)",
                  },
                }}
              />
            ))}
            
            {/* Current Time Display */}
            <Box sx={{ ml: "auto", display: "flex", alignItems: "center" }}>
              <Typography
                variant="caption"
                sx={{
                  color: colors.textSecondary,
                  fontSize: { xs: "0.6rem", sm: "0.65rem" },
                  fontFamily: '"SF Mono", "Consolas", monospace',
                  px: 1,
                  py: 0.25,
                  bgcolor: colors.surface,
                  borderRadius: 1,
                  border: `1px solid ${colors.border}`,
                }}
              >
                {new Date().toLocaleTimeString()}
              </Typography>
            </Box>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
  // Render function for the overview section (RESPONSIVE - SINGLE COLUMN FOR PAIRED LISTS)
  const renderOverviewSection = () => (
    <Stack spacing={2}>
      {marketSummary && (
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
          }}
        >
          <Typography
            variant="h6"
            sx={{ mb: 1.5, color: colors.primary, fontWeight: 700 }}
          >
            📊 ADVANCE DECLINE RATIO
          </Typography>
          <Grid container spacing={1}>
            {[
              {
                value: marketSummary.advancing,
                label: "ADV",
                color: colors.positive,
              },
              {
                value: marketSummary.declining,
                label: "DEC",
                color: colors.negative,
              },
              {
                value: marketSummary.unchanged,
                label: "UNCH",
                color: colors.neutral,
              },
              {
                value: marketSummary.advanceDeclineRatio,
                label: "A/D",
                color: colors.primary,
              },
              {
                value: `${marketSummary.marketBreadth}%`,
                label: "BRDTH",
                color: colors.text,
              },
              ...(indicesSentiment.sentiment !== "unknown"
                ? [
                    {
                      value: indicesSentiment.sentiment
                        .toUpperCase()
                        .substring(0, 4),
                      label: "INDX",
                      color: indicesSentiment.sentiment.includes("bullish")
                        ? colors.positive
                        : indicesSentiment.sentiment.includes("bearish")
                        ? colors.negative
                        : colors.neutral,
                    },
                  ]
                : []),
            ].map((item, index) => (
              <Grid item xs={4} sm={2} md={1} key={index}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color: item.color,
                      fontWeight: 700,
                      fontSize: { xs: "0.9rem", sm: "1rem" },
                    }}
                  >
                    {item.value}
                  </Typography>
                  <Typography variant="caption">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}
      {/* Clean Major Indices Cards */}
      {majorIndices.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent sx={{ p: { xs: 1.5, sm: 2 } }}>
            <Typography
              variant="h6"
              sx={{
                mb: { xs: 1, sm: 1.5 },
                color: colors.header,
                fontWeight: 700,
                fontSize: { xs: "1rem", sm: "1.1rem" },
                display: "flex",
                alignItems: "center",
                gap: 0.75,
              }}
            >
              🏛️ MAJOR INDICES ({majorIndices.length})
            </Typography>
            {isMobile ? (
              // Mobile: Clean horizontal scroll cards
              <Box
                sx={{
                  display: "flex",
                  overflowX: "auto",
                  gap: 1,
                  pb: 1,
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
                {majorIndices.slice(0, 8).map((index, i) => {
                  const isPositive = (index.change_percent || 0) >= 0;
                  return (
                    <Card
                      key={i}
                      sx={{
                        minWidth: 120,
                        flexShrink: 0,
                        bgcolor: colors.cardBackground,
                        borderRadius: 2,
                        border: `1px solid ${colors.border}30`,
                        borderLeft: `3px solid ${
                          isPositive ? colors.positive : colors.negative
                        }`,
                        "&:hover": {
                          transform: "translateY(-2px)",
                          boxShadow: theme.shadows[2],
                        },
                        transition: "all 0.2s ease",
                      }}
                    >
                      <CardContent
                        sx={{ p: 1.25, "&:last-child": { pb: 1.25 } }}
                      >
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 700,
                            color: colors.header,
                            mb: 0.5,
                            fontSize: "0.8rem",
                            textAlign: "center",
                            lineHeight: 1.2,
                          }}
                          noWrap
                        >
                          {index.symbol}
                        </Typography>
                        <Typography
                          variant="body1"
                          sx={{
                            fontWeight: 700,
                            color: "text.primary",
                            mb: 0.5,
                            fontSize: "0.85rem",
                            textAlign: "center",
                            fontFamily: "monospace",
                          }}
                        >
                          ₹{index.last_price?.toFixed(2)}
                        </Typography>
                        <Box
                          sx={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            gap: 0.25,
                          }}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              color: isPositive
                                ? colors.positive
                                : colors.negative,
                              fontWeight: 700,
                              fontSize: "0.75rem",
                              fontFamily: "monospace",
                            }}
                          >
                            {isPositive ? "+" : ""}
                            {(index.change_percent || 0).toFixed(2)}%
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{
                              color: "text.secondary",
                              fontSize: "0.65rem",
                              fontFamily: "monospace",
                            }}
                          >
                            {isPositive ? "+" : ""}
                            {(index.change || 0).toFixed(2)}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  );
                })}
              </Box>
            ) : (
              // Desktop: Grid layout
              <Grid container spacing={2}>
                {majorIndices.slice(0, 6).map((index, i) => {
                  const isPositive = (index.change_percent || 0) >= 0;
                  return (
                    <Grid item xs={6} sm={4} md={2} key={i}>
                      <Card
                        sx={{
                          bgcolor: colors.cardBackground,
                          borderRadius: 2,
                          border: `1px solid ${colors.border}`,
                          borderLeft: `3px solid ${
                            isPositive ? colors.positive : colors.negative
                          }`,
                          "&:hover": {
                            transform: "translateY(-2px)",
                            boxShadow: theme.shadows[4],
                          },
                          transition: "all 0.2s ease",
                        }}
                      >
                        <CardContent
                          sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 700,
                              color: colors.header,
                              mb: 0.75,
                              fontSize: "0.85rem",
                              textAlign: "center",
                            }}
                            noWrap
                          >
                            {index.symbol}
                          </Typography>
                          <Typography
                            variant="h6"
                            sx={{
                              fontWeight: 700,
                              color: "text.primary",
                              mb: 0.5,
                              fontSize: "1rem",
                              textAlign: "center",
                              fontFamily: "monospace",
                            }}
                          >
                            ₹{index.last_price?.toFixed(2)}
                          </Typography>
                          <Box sx={{ textAlign: "center" }}>
                            <Typography
                              variant="body2"
                              sx={{
                                color: isPositive
                                  ? colors.positive
                                  : colors.negative,
                                fontWeight: 700,
                                fontSize: "0.8rem",
                                fontFamily: "monospace",
                              }}
                            >
                              {isPositive ? "+" : ""}
                              {(index.change_percent || 0).toFixed(2)}%
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                color: "text.secondary",
                                display: "block",
                                fontSize: "0.7rem",
                                fontFamily: "monospace",
                              }}
                            >
                              {isPositive ? "+" : ""}
                              {(index.change || 0).toFixed(2)} pts
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            )}
          </CardContent>
        </Card>
      )}
      {/* INDICES LIST */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <MemoizedStocksList
          title={`🏛️ INDICES (${indices.length})`}
          data={indices}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={!isMobile} // Hide volume on mobile
          isLoading={!isConnected}
          maxItems={isMobile ? 8 : 12} // Show fewer items on mobile
          density="compact" // Use compact density
          compact={true}
          // Remove fixed containerHeight to allow natural flow
          // containerHeight={isMobile ? "50vh" : "55vh"}
        />
      </Paper>

      {/* GAINERS/LOSERS - Stack vertically on ALL screens */}
      <Stack spacing={2}>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <MemoizedStocksList
            title={`🚀 GAINERS (${topGainers.length})`}
            data={topGainers}
            layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
            showVolume={!isMobile} // Hide volume on mobile
            showSector={!isMobile} // Show sector on larger screens if table
            maxItems={isMobile ? 5 : 8} // Show fewer items on mobile
            isLoading={!isConnected}
            density="compact" // Use compact density
            compact={true}
            // Remove fixed containerHeight to allow natural flow
            // containerHeight={isMobile ? "55vh" : "60vh"}
          />
        </Paper>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <MemoizedStocksList
            title={`📉 LOSERS (${topLosers.length})`}
            data={topLosers}
            layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
            showVolume={!isMobile} // Hide volume on mobile
            showSector={!isMobile} // Show sector on larger screens if table
            maxItems={isMobile ? 5 : 8} // Show fewer items on mobile
            isLoading={!isConnected}
            density="compact" // Use compact density
            compact={true}
            // Remove fixed containerHeight to allow natural flow
            // containerHeight={isMobile ? "55vh" : "60vh"}
          />
        </Paper>
      </Stack>

      {/* BOOSTERS/VOLUME - Stack vertically on ALL screens */}
      <Stack spacing={2}>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <MemoizedStocksList
            title={`⚡ BOOSTERS (${intradayBoosters.length})`}
            data={intradayBoosters}
            layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
            showVolume={!isMobile} // Hide volume on mobile
            showSector={false} // Generally hide sector for these lists
            maxItems={isMobile ? 5 : 10} // Show fewer items on mobile
            isLoading={!isConnected}
            density="compact" // Use compact density
            compact={true}
            // Remove fixed containerHeight to allow natural flow
            // containerHeight={isMobile ? "55vh" : "60vh"}
          />
        </Paper>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <MemoizedStocksList
            title={`📊 VOLUME (${volumeLeaders.length})`}
            data={volumeLeaders}
            layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
            showVolume={!isMobile} // Hide volume on mobile
            showSector={false} // Generally hide sector for these lists
            maxItems={isMobile ? 5 : 10} // Show fewer items on mobile
            isLoading={!isConnected}
            density="compact" // Use compact density
            compact={true}
            // Remove fixed containerHeight to allow natural flow
            // containerHeight={isMobile ? "55vh" : "60vh"}
          />
        </Paper>
      </Stack>
    </Stack>
  );
  // Render function for the search section (RESPONSIVE)
  const renderSearchSection = () => (
    <Stack spacing={2}>
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <Typography
          variant="h6"
          sx={{ mb: 1.5, color: colors.primary, fontWeight: 700 }}
        >
          🔍 SEARCH STOCKS
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", width: "100%" }}>
          <InputBase
            placeholder="Symbol or company name..."
            value={searchQuery}
            onChange={handleSearchChange}
            sx={{
              flex: 1,
              p: "4px 8px",
              border: `1px solid ${colors.border}`,
              borderRadius: 2,
              bgcolor: "background.default",
              fontSize: "0.875rem",
            }}
            startAdornment={
              <SearchIcon sx={{ mr: 1, color: "text.secondary" }} />
            }
          />
        </Box>
      </Paper>
      {searchResults.length > 0 && (
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
          }}
        >
          <MemoizedStocksList
            title={`📊 RESULTS (${searchResults.length})`}
            data={searchResults}
            layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
            showVolume={!isMobile} // Hide volume on mobile
            showName={true}
            showSector={!isMobile} // Show sector on larger screens if table
            maxItems={50} // Keep maxItems for search results
            isLoading={!isConnected}
            density="standard" // Use standard density for search results
            // Remove fixed containerHeight to allow natural flow
            // containerHeight="70vh"
          />
        </Paper>
      )}
    </Stack>
  );
  // Render function for the sectors section (RESPONSIVE)
  const renderSectorsSection = () => (
    <Stack spacing={2}>
      {/* Financial Sector Heatmap - Using correct component for sector data */}
      <FinancialHeatmap
        data={heatmap?.sectors || []}
        marketData={marketData}
        title="🔥 SECTOR HEATMAP"
        isLoading={!isConnected}
        maxItems={isMobile ? 20 : 30}
      />
      {/* TipRanks-style Stock Heatmap - Using raw market data */}
      <TipRanksHeatmap
        data={[]} // This prop is not used by the component
        marketData={marketData}
        title="🔥 STOCK HEATMAP"
        isLoading={!isConnected}
        maxItems={isMobile ? 30 : 50}
      />
      {/* Sector Selection and Stocks */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <Box sx={{ mb: 2 }}>
          <Typography
            variant="h6"
            sx={{ mb: 1.5, color: colors.primary, fontWeight: 700 }}
          >
            🏢 SECTOR ANALYSIS
          </Typography>
          <Select
            value={selectedSector}
            onChange={handleSectorChange}
            fullWidth
            size="small"
            sx={{
              bgcolor: "background.default",
              borderRadius: 2,
              border: `1px solid ${colors.border}`,
              "& .MuiSelect-select": {
                py: 1,
                pl: 1.5,
                pr: 3,
              },
            }}
          >
            <MenuItem value="ALL">ALL SECTORS</MenuItem>
            {sectors.map((sector) => (
              <MenuItem key={sector} value={sector}>
                {sector}
              </MenuItem>
            ))}
          </Select>
        </Box>
        <MemoizedStocksList
          title={`📊 ${
            selectedSector === "ALL" ? "ALL STOCKS" : selectedSector
          } (${sectorStocks.length})`}
          data={sectorStocks}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={!isMobile} // Hide volume on mobile
          showName={true}
          showSector={selectedSector === "ALL" && !isMobile} // Show sector on larger screens if table and showing all
          maxItems={50} // Keep maxItems for sector stocks
          isLoading={!isConnected}
          // Remove fixed containerHeight to allow natural flow
        />
      </Paper>
    </Stack>
  );
  // Render function for the indices section (RESPONSIVE - SINGLE COLUMN FOR PAIRED LISTS)
  const renderIndicesSection = () => (
    <Stack spacing={2}>
      {/* Indices Summary Stats */}
      {indicesSummary && Object.keys(indicesSummary).length > 0 && (
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
          }}
        >
          <Typography
            variant="h6"
            sx={{ mb: 1.5, color: colors.primary, fontWeight: 700 }}
          >
            📊 INDICES OVERVIEW
          </Typography>
          <Grid container spacing={1}>
            {[
              {
                value: indicesSummary.total_indices || 0,
                label: "TOTAL",
                color: colors.primary,
              },
              {
                value: indicesSummary.major_up || 0,
                label: "MAJ UP",
                color: colors.positive,
              },
              {
                value: indicesSummary.major_down || 0,
                label: "MAJ DN",
                color: colors.negative,
              },
              {
                value: indicesSummary.sector_up || 0,
                label: "SEC UP",
                color: colors.positive,
              },
              {
                value: indicesSummary.sector_down || 0,
                label: "SEC DN",
                color: colors.negative,
              },
              ...(indicesSentiment.sentiment !== "unknown"
                ? [
                    {
                      value: `${indicesSentiment.confidence}%`,
                      label: "CONF",
                      color: colors.accent,
                    },
                  ]
                : []),
            ].map((item, index) => (
              <Grid item xs={4} sm={2} md={1} key={index}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color: item.color,
                      fontWeight: 700,
                      fontSize: { xs: "0.9rem", sm: "1rem" },
                    }}
                  >
                    {item.value}
                  </Typography>
                  <Typography variant="caption">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}
      {/* Major Market Indices */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <MemoizedStocksList
          title={`🏛️ MAJOR INDICES (${majorIndices.length})`}
          data={majorIndices}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={false} // Hide volume for indices
          showName={true}
          showSector={false} // Hide sector for indices
          maxItems={isMobile ? 8 : 20} // Show fewer items on mobile
          isLoading={!isConnected}
          // Remove fixed containerHeight to allow natural flow
        />
      </Paper>
      {/* Sector Indices */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <MemoizedStocksList
          title={`🏢 SECTOR INDICES (${sectorIndices.length})`}
          data={sectorIndices}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={false} // Hide volume for indices
          showName={true}
          showSector={false} // Hide sector for indices
          maxItems={isMobile ? 8 : 30} // Show fewer items on mobile
          isLoading={!isConnected}
          // Remove fixed containerHeight to allow natural flow
        />
      </Paper>
      {/* Top Performing Indices - Stack vertically on ALL screens */}
      <Stack spacing={2}>
        {indicesPerformance && indicesPerformance.gainers.length > 0 && (
          <Paper
            elevation={2}
            sx={{
              p: 2,
              borderRadius: 3,
              border: `1px solid ${colors.border}`,
              bgcolor: "background.paper",
              width: "100%",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <MemoizedStocksList
              title={`📈 TOP GAINING INDICES (${indicesPerformance.gainers.length})`}
              data={indicesPerformance.gainers.slice(0, isMobile ? 5 : 10)}
              layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
              showVolume={false} // Hide volume for indices
              showName={true}
              showSector={false} // Hide sector for indices
              maxItems={isMobile ? 5 : 10} // Show fewer items on mobile
              isLoading={!isConnected}
              // Remove fixed containerHeight to allow natural flow
            />
          </Paper>
        )}
        {indicesPerformance && indicesPerformance.losers.length > 0 && (
          <Paper
            elevation={2}
            sx={{
              p: 2,
              borderRadius: 3,
              border: `1px solid ${colors.border}`,
              bgcolor: "background.paper",
              width: "100%",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <MemoizedStocksList
              title={`📉 TOP LOSING INDICES (${indicesPerformance.losers.length})`}
              data={indicesPerformance.losers.slice(0, isMobile ? 5 : 10)}
              layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
              showVolume={false} // Hide volume for indices
              showName={true}
              showSector={false} // Hide sector for indices
              maxItems={isMobile ? 5 : 10} // Show fewer items on mobile
              isLoading={!isConnected}
              // Remove fixed containerHeight to allow natural flow
            />
          </Paper>
        )}
      </Stack>
      {/* All Indices Table */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <MemoizedStocksList
          title={`🏛️ ALL INDICES (${indices.length})`}
          data={indices}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={!isMobile} // Hide volume on mobile
          showName={true}
          showSector={false} // Hide sector for indices
          maxItems={isMobile ? 8 : 100} // Show fewer items on mobile, more on desktop
          isLoading={!isConnected}
          // Remove fixed containerHeight to allow natural flow
        />
      </Paper>
    </Stack>
  );
  // Render function for the movers section (RESPONSIVE - SINGLE COLUMN FOR PAIRED LISTS)
  const renderMoversSection = () => (
    <Stack spacing={2}>
      {/* GAINERS/LOSERS - Stack vertically on ALL screens (same logic as overview) */}
      <Stack spacing={2}>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            position: "relative",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 1,
            }}
          >
            <Typography
              variant="h6"
              sx={{ color: colors.primary, fontWeight: 700 }}
            >
              🚀 TOP GAINERS ({topGainers.length})
            </Typography>
            <Button
              size="small"
              onClick={() => toggleExpanded("gainers")}
              startIcon={
                expandedSection === "gainers" ? (
                  <ExpandLessIcon />
                ) : (
                  <ExpandMoreIcon />
                )
              }
              sx={{ minWidth: 0, px: 1 }}
            >
              {expandedSection === "gainers" ? "COMPACT" : "EXPAND"}
            </Button>
          </Box>
          <MemoizedStocksList
            title="" // Title already shown above
            data={topGainers}
            layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
            showVolume={!isMobile} // Hide volume on mobile
            showSector={!isMobile} // Show sector on larger screens if table
            maxItems={
              expandedSection === "gainers"
                ? isMobile
                  ? 20
                  : 50
                : isMobile
                ? 10
                : 15
            }
            isLoading={!isConnected}
            compact={true} // Pass compact prop if your StocksList supports it
            // Remove fixed containerHeight to allow natural flow
          />
        </Paper>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            position: "relative",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 1,
            }}
          >
            <Typography
              variant="h6"
              sx={{ color: colors.primary, fontWeight: 700 }}
            >
              📉 TOP LOSERS ({topLosers.length})
            </Typography>
            <Button
              size="small"
              onClick={() => toggleExpanded("losers")}
              startIcon={
                expandedSection === "losers" ? (
                  <ExpandLessIcon />
                ) : (
                  <ExpandMoreIcon />
                )
              }
              sx={{ minWidth: 0, px: 1 }}
            >
              {expandedSection === "losers" ? "COMPACT" : "EXPAND"}
            </Button>
          </Box>
          <MemoizedStocksList
            title="" // Title already shown above
            data={topLosers}
            layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
            showVolume={!isMobile} // Hide volume on mobile
            showSector={!isMobile} // Show sector on larger screens if table
            maxItems={
              expandedSection === "losers"
                ? isMobile
                  ? 20
                  : 50
                : isMobile
                ? 10
                : 15
            }
            isLoading={!isConnected}
            compact={true} // Pass compact prop if your StocksList supports it
            // Remove fixed containerHeight to allow natural flow
          />
        </Paper>
      </Stack>
      {/* Volume Leaders - Single list */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <MemoizedStocksList
          title={`📊 VOLUME LEADERS (${volumeLeaders.length})`}
          data={volumeLeaders}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={!isMobile} // Hide volume on mobile
          showSector={!isMobile} // Show sector on larger screens if table
          maxItems={isMobile ? 15 : 20} // Show fewer items on mobile
          isLoading={!isConnected}
          // Remove fixed containerHeight to allow natural flow
        />
      </Paper>
    </Stack>
  );
  // Render function for the gaps section (RESPONSIVE - SINGLE COLUMN FOR PAIRED LISTS)
  const renderGapsSection = () => (
    <Stack spacing={2}>
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
          width: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <MemoizedStocksList
          title={`📈 GAP UP (${gapUp.length})`}
          data={gapUp}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={!isMobile} // Hide volume on mobile
          showSector={!isMobile} // Show sector on larger screens if table
          maxItems={isMobile ? 15 : 20} // Show fewer items on mobile
          isLoading={!isConnected}
          // Remove fixed containerHeight to allow natural flow
        />
      </Paper>
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
          width: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <MemoizedStocksList
          title={`📉 GAP DOWN (${gapDown.length})`}
          data={gapDown}
          layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
          showVolume={!isMobile} // Hide volume on mobile
          showSector={!isMobile} // Show sector on larger screens if table
          maxItems={isMobile ? 15 : 20} // Show fewer items on mobile
          isLoading={!isConnected}
          // Remove fixed containerHeight to allow natural flow
        />
      </Paper>
    </Stack>
  );
  // Enhanced MCX trading symbol parser using proper data fields
  const parseMcxTradingSymbol = (stock) => {
    const tradingSymbol = stock.symbol || stock.name || '';
    const instrumentType = stock.instrument_type || '';
    const strikePrice = stock.strike_price || null;
    const expiry = stock.expiry || null;
    
    // Extract commodity from trading symbol (first part before space)
    const parts = tradingSymbol.split(' ');
    const commodity = parts[0]; // CRUDEOIL, GOLD, SILVER, etc.
    
    const isOption = instrumentType === 'CE' || instrumentType === 'PE';
    const isFuture = instrumentType === 'FUT' || instrumentType === 'FUTCOM';
    
    if (isOption && strikePrice) {
      // Use actual strike_price field and parse expiry from trading symbol
      const expiryText = parts.length >= 5 ? parts.slice(-3).join(' ') : 'N/A';
      return {
        commodity,
        displayName: `${commodity} ${strikePrice} ${instrumentType}`,
        fullName: `${commodity} ${expiryText} ₹${strikePrice} ${instrumentType === 'CE' ? 'Call' : 'Put'}`,
        type: instrumentType === 'CE' ? 'Call' : 'Put',
        strike: strikePrice,
        strikeFormatted: `₹${strikePrice.toLocaleString()}`,
        expiry: expiryText,
        isOption: true,
        isFuture: false,
        sortKey: `${commodity}_OPT_${strikePrice}_${instrumentType}`
      };
    } else if (isFuture) {
      // Future parsing from trading symbol
      const expiryText = parts.slice(2).join(' '); // Everything after "FUT"
      return {
        commodity,
        displayName: `${commodity} FUT`,
        fullName: `${commodity} ${expiryText} Futures`,
        type: 'Future',
        expiry: expiryText,
        isOption: false,
        isFuture: true,
        sortKey: `${commodity}_FUT_${expiry || '0'}`
      };
    }
    
    // Fallback for unrecognized formats
    return {
      commodity: commodity || tradingSymbol,
      displayName: tradingSymbol,
      fullName: tradingSymbol,
      type: instrumentType || 'Unknown',
      isOption: instrumentType === 'CE' || instrumentType === 'PE',
      isFuture: instrumentType === 'FUT' || instrumentType === 'FUTCOM',
      sortKey: tradingSymbol
    };
  };

  // Enhanced MCX processing with futures/options separation
  const processMcxStocks = () => {
    const processed = mcxStocks.map(stock => ({
      ...stock,
      parsed: parseMcxTradingSymbol(stock)
    }));

    // Group by commodity type
    const crudeStocks = processed.filter(stock => 
      stock.parsed.commodity?.toUpperCase().includes('CRUDE') ||
      stock.name?.toUpperCase().includes('CRUDE')
    );
    
    const goldStocks = processed.filter(stock => 
      stock.parsed.commodity?.toUpperCase().includes('GOLD') || 
      stock.name?.toUpperCase().includes('GOLD')
    );
    
    const silverStocks = processed.filter(stock => 
      stock.parsed.commodity?.toUpperCase().includes('SILVER') ||
      stock.name?.toUpperCase().includes('SILVER')
    );
    
    const otherStocks = processed.filter(stock => 
      !crudeStocks.includes(stock) && 
      !goldStocks.includes(stock) && 
      !silverStocks.includes(stock)
    );

    return { crudeStocks, goldStocks, silverStocks, otherStocks };
  };

  // Enhanced commodity section renderer with futures/options separation
  const renderCommoditySection = (title, stocks, bgColor, textColor) => {
    if (!stocks || stocks.length === 0) return null;

    // Separate futures and options
    const futures = stocks.filter(stock => stock.parsed.isFuture).slice(0, 5);
    const options = stocks.filter(stock => stock.parsed.isOption).slice(0, 15);

    return (
      <Paper
        elevation={1}
        sx={{
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
          overflow: "hidden"
        }}
      >
        {/* Section Header */}
        <Box sx={{ 
          p: 2, 
          backgroundColor: bgColor + '10',
          borderBottom: `1px solid ${colors.border}`
        }}>
          <Typography variant="h6" sx={{ 
            color: textColor, 
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 1
          }}>
            {title} ({stocks.length})
          </Typography>
          <Typography variant="caption" sx={{ color: colors.textSecondary }}>
            {futures.length} Futures • {options.length} Options
          </Typography>
        </Box>

        <Stack spacing={1.5} sx={{ p: 2 }}>
          {/* Futures Section */}
          {futures.length > 0 && (
            <Box>
              <Typography variant="subtitle2" sx={{ 
                color: colors.text, 
                fontWeight: 500, 
                mb: 1,
                display: "flex",
                alignItems: "center",
                gap: 1
              }}>
                📈 Futures ({futures.length})
              </Typography>
              <Stack spacing={0.5}>
                {futures.map((stock, index) => (
                  <Box key={`future-${index}`} sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    p: 1,
                    borderRadius: 1,
                    bgcolor: colors.surface + '50',
                    border: `1px solid ${colors.border}50`
                  }}>
                    <Box>
                      <Typography variant="body2" sx={{ 
                        color: colors.text,
                        fontWeight: 500
                      }}>
                        {stock.parsed.displayName}
                      </Typography>
                      <Typography variant="caption" sx={{ color: colors.textSecondary }}>
                        Exp: {stock.parsed.expiry || 'N/A'}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="body2" sx={{ 
                        color: colors.text,
                        fontWeight: 500
                      }}>
                        ₹{stock.last_price?.toLocaleString() || 'N/A'}
                      </Typography>
                      <Typography variant="caption" sx={{ 
                        color: stock.change_percent >= 0 ? colors.positive : colors.negative,
                        fontWeight: 500
                      }}>
                        {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent?.toFixed(2) || '0.00'}%
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Stack>
            </Box>
          )}

          {/* Options Section */}
          {options.length > 0 && (
            <Box>
              <Typography variant="subtitle2" sx={{ 
                color: colors.text, 
                fontWeight: 500, 
                mb: 1,
                display: "flex",
                alignItems: "center",
                gap: 1
              }}>
                📊 Options Chain ({options.length})
              </Typography>
              
              {/* Option Chain Display */}
              <Box sx={{ maxHeight: isMobile ? 250 : 300, overflowY: 'auto' }}>
                <Stack spacing={0.5}>
                  {options.map((stock, index) => (
                    <Box key={`option-${index}`} sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      p: 1,
                      borderRadius: 1,
                      bgcolor: stock.parsed.type === 'Call' ? 
                        colors.positive + '10' : colors.negative + '10',
                      border: `1px solid ${stock.parsed.type === 'Call' ? colors.positive + '30' : colors.negative + '30'}`
                    }}>
                      <Box>
                        <Typography variant="body2" sx={{ 
                          color: colors.text,
                          fontWeight: 500
                        }}>
                          {stock.parsed.displayName}
                        </Typography>
                        <Typography variant="caption" sx={{ color: colors.textSecondary }}>
                          Strike: {stock.parsed.strikeFormatted || `₹${stock.parsed.strike || 'N/A'}`} • {stock.parsed.type}
                        </Typography>
                      </Box>
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="body2" sx={{ 
                          color: colors.text,
                          fontWeight: 500
                        }}>
                          ₹{stock.last_price?.toLocaleString() || 'N/A'}
                        </Typography>
                        <Typography variant="caption" sx={{ 
                          color: stock.change_percent >= 0 ? colors.positive : colors.negative,
                          fontWeight: 500
                        }}>
                          {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent?.toFixed(2) || '0.00'}%
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </Stack>
              </Box>
            </Box>
          )}
        </Stack>
      </Paper>
    );
  };

  // Render function for the MCX section (RESPONSIVE) - Enhanced with Futures & Options Display
  const renderMcxSection = () => {
    const { crudeStocks, goldStocks, silverStocks, otherStocks } = processMcxStocks();
    
    if (!mcxStocks || mcxStocks.length === 0) {
      return (
        <Paper
          elevation={2}
          sx={{
            p: 3,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            textAlign: "center"
          }}
        >
          <Typography variant="h6" sx={{ mb: 1, color: colors.text }}>
            🏭 MCX Commodities
          </Typography>
          <Typography sx={{ color: colors.textSecondary }}>
            No MCX data available
          </Typography>
          <Typography variant="caption" sx={{ mt: 1, display: "block", color: colors.textSecondary }}>
            Waiting for Gold, Crude Oil, Silver & Copper live data...
          </Typography>
        </Paper>
      );
    }
    
    return (
      <Stack spacing={2}>
        {/* Main MCX Header */}
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
          }}
        >
          <Typography variant="h6" sx={{ 
            color: colors.text, 
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 1,
            mb: 1
          }}>
            🏭 MCX Commodities ({mcxStocks.length})
          </Typography>
          <Typography variant="caption" sx={{ color: colors.textSecondary }}>
            Live futures and options for precious metals and energy commodities
          </Typography>
          
          {/* Commodity Summary Chips */}
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 2 }}>
            {goldStocks.length > 0 && (
              <Chip 
                label={`🥇 Gold: ${goldStocks.length}`} 
                size="small" 
                sx={{ 
                  backgroundColor: '#FFD70020', 
                  color: '#B8860B',
                  fontWeight: 500
                }}
              />
            )}
            {crudeStocks.length > 0 && (
              <Chip 
                label={`🛢️ Crude: ${crudeStocks.length}`} 
                size="small" 
                sx={{ 
                  backgroundColor: '#2F4F4F40', 
                  color: '#708090',
                  fontWeight: 500
                }}
              />
            )}
            {silverStocks.length > 0 && (
              <Chip 
                label={`🥈 Silver: ${silverStocks.length}`} 
                size="small" 
                sx={{ 
                  backgroundColor: '#C0C0C030', 
                  color: '#778899',
                  fontWeight: 500
                }}
              />
            )}
            {otherStocks.length > 0 && (
              <Chip 
                label={`Other: ${otherStocks.length}`} 
                size="small" 
                sx={{ 
                  backgroundColor: colors.primary + '20', 
                  color: colors.primary,
                  fontWeight: 500
                }}
              />
            )}
          </Box>
        </Paper>
        
        {/* Enhanced Commodity Display with Futures & Options */}
        {renderCommoditySection('🥇 Gold', goldStocks, '#FFD700', '#B8860B')}
        {renderCommoditySection('🛢️ Crude Oil', crudeStocks, '#2F4F4F', '#708090')}
        {renderCommoditySection('🥈 Silver', silverStocks, '#C0C0C0', '#778899')}
        
        {/* Other MCX Commodities */}
        {otherStocks.length > 0 && renderCommoditySection('🏭 Other MCX', otherStocks, colors.primary, colors.primary)}
      </Stack>
    );
  };
  // Render function for the FNO stocks section (RESPONSIVE)
  const renderFnoSection = () => {
    return (
      <Stack spacing={2}>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
          }}
        >
          <Box sx={{ mb: 2 }}>
            <Typography
              variant="h6"
              sx={{ mb: 1, color: colors.primary, fontWeight: 700 }}
            >
              📋 F&O STOCKS REFERENCE LIST
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              Complete F&O list: {fnoIndices.length} indices +{" "}
              {fnoStocks.length} stocks = {fnoStockList.total_count} total
              securities.
              {Object.keys(marketData || {}).length > 0
                ? " Live prices shown when available from market feed."
                : " Connect to market feed to see live prices."}
            </Typography>
            <Grid container spacing={1}>
              <Grid item xs={4} sm={2} md={1}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: colors.primary, fontWeight: 700 }}
                  >
                    {fnoIndices.length}
                  </Typography>
                  <Typography variant="caption">INDICES</Typography>
                </Paper>
              </Grid>
              <Grid item xs={4} sm={2} md={1}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: colors.primary, fontWeight: 700 }}
                  >
                    {fnoStocks.length}
                  </Typography>
                  <Typography variant="caption">STOCKS</Typography>
                </Paper>
              </Grid>
              <Grid item xs={4} sm={2} md={1}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: colors.accent, fontWeight: 700 }}
                  >
                    {
                      [
                        ...fnoIndicesWithLiveData,
                        ...fnoStocksWithLiveData,
                      ].filter((s) => s.last_price > 0).length
                    }
                  </Typography>
                  <Typography variant="caption">LIVE</Typography>
                </Paper>
              </Grid>
              <Grid item xs={4} sm={2} md={1}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: colors.positive, fontWeight: 700 }}
                  >
                    {
                      [
                        ...fnoIndicesWithLiveData,
                        ...fnoStocksWithLiveData,
                      ].filter((s) => s.change_percent > 0).length
                    }
                  </Typography>
                  <Typography variant="caption">UP</Typography>
                </Paper>
              </Grid>
              <Grid item xs={4} sm={2} md={1}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ color: colors.negative, fontWeight: 700 }}
                  >
                    {
                      [
                        ...fnoIndicesWithLiveData,
                        ...fnoStocksWithLiveData,
                      ].filter((s) => s.change_percent < 0).length
                    }
                  </Typography>
                  <Typography variant="caption">DOWN</Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>
          {/* Indices Section */}
          {fnoIndices.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <MemoizedStocksList
                title={`🏛️ F&O INDICES (${fnoIndices.length})`}
                data={fnoIndicesWithLiveData}
                layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
                showVolume={false} // Hide volume for indices
                showName={true}
                showSector={false} // Hide sector for indices
                maxItems={fnoIndices.length} // Show all indices
                isLoading={fnoLoading}
                emptyMessage="No F&O indices found"
                density="compact" // Use compact density
                compact={true}
                // Remove fixed containerHeight to allow natural flow
              />
            </Box>
          )}
          {/* Stocks Section */}
          {fnoStocks.length > 0 && (
            <MemoizedStocksList
              title={`📈 F&O STOCKS (${fnoStocks.length})`}
              data={fnoStocksWithLiveData}
              layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
              showVolume={!isMobile} // Hide volume on mobile
              showName={true}
              showSector={false} // Hide sector for F&O stocks
              maxItems={isMobile ? fnoStocks.length : fnoStocks.length} // Show all on mobile, limit on desktop if needed
              isLoading={fnoLoading}
              emptyMessage="No F&O stocks found"
              density="compact" // Use compact density
              compact={true}
              // Remove fixed containerHeight to allow natural flow
              // containerHeight={isMobile ? "55vh" : "60vh"}
            />
          )}
        </Paper>
      </Stack>
    );
  };
  // FIXED: Analytics section renderer with comprehensive data display (RESPONSIVE - SINGLE COLUMN FOR PAIRED LISTS)
  const renderAnalyticsSection = () => (
    <Stack spacing={2}>
      {/* Market Sentiment */}
      {marketSentiment && Object.keys(marketSentiment).length > 0 && (
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
          }}
        >
          <Typography
            variant="h6"
            sx={{ mb: 1.5, color: colors.primary, fontWeight: 700 }}
          >
            📊 MARKET SENTIMENT
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={4} sm={2} md={1}>
              <Paper
                sx={{
                  p: 1,
                  textAlign: "center",
                  bgcolor: "background.default",
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    color:
                      marketSentiment.sentiment === "bullish"
                        ? colors.positive
                        : marketSentiment.sentiment === "bearish"
                        ? colors.negative
                        : colors.neutral,
                    fontWeight: 700,
                    textTransform: "uppercase",
                  }}
                >
                  {marketSentiment.sentiment
                    ? marketSentiment.sentiment.substring(0, 4)
                    : "NEUT"}
                </Typography>
                <Typography variant="caption">SENT</Typography>
              </Paper>
            </Grid>
            <Grid item xs={4} sm={2} md={1}>
              <Paper
                sx={{
                  p: 1,
                  textAlign: "center",
                  bgcolor: "background.default",
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ color: colors.primary, fontWeight: 700 }}
                >
                  {marketSentiment.confidence || 0}%
                </Typography>
                <Typography variant="caption">CONF</Typography>
              </Paper>
            </Grid>
            {marketSentiment.market_breadth && (
              <>
                <Grid item xs={4} sm={2} md={1}>
                  <Paper
                    sx={{
                      p: 1,
                      textAlign: "center",
                      bgcolor: "background.default",
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{ color: colors.positive, fontWeight: 700 }}
                    >
                      {marketSentiment.market_breadth.advancing || 0}
                    </Typography>
                    <Typography variant="caption">ADV</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={4} sm={2} md={1}>
                  <Paper
                    sx={{
                      p: 1,
                      textAlign: "center",
                      bgcolor: "background.default",
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{ color: colors.negative, fontWeight: 700 }}
                    >
                      {marketSentiment.market_breadth.declining || 0}
                    </Typography>
                    <Typography variant="caption">DEC</Typography>
                  </Paper>
                </Grid>
              </>
            )}
            {marketSentiment.sentiment_score !== undefined && (
              <Grid item xs={4} sm={2} md={1}>
                <Paper
                  sx={{
                    p: 1,
                    textAlign: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color:
                        marketSentiment.sentiment_score > 0
                          ? colors.positive
                          : marketSentiment.sentiment_score < 0
                          ? colors.negative
                          : colors.neutral,
                      fontWeight: 700,
                    }}
                  >
                    {marketSentiment.sentiment_score.toFixed(2)}
                  </Typography>
                  <Typography variant="caption">SCORE</Typography>
                </Paper>
              </Grid>
            )}
          </Grid>
        </Paper>
      )}
      {/* Breakout Analysis - Stack vertically on ALL screens */}
      <Stack spacing={2}>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {breakouts.length > 0 ? (
            <MemoizedStocksList
              title={`📈 BREAKOUTS (${breakouts.length})`}
              data={breakouts}
              layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
              showVolume={!isMobile} // Hide volume on mobile
              showSector={!isMobile} // Show sector on larger screens if table
              maxItems={isMobile ? 15 : 15} // Show fewer items on mobile
              isLoading={!isConnected}
              // Remove fixed containerHeight to allow natural flow
            />
          ) : (
            <Box sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="h6" sx={{ color: colors.primary, mb: 1 }}>
                📈 BREAKOUTS (0)
              </Typography>
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", fontStyle: "italic" }}
              >
                Stocks breaking above resistance
                <br />
                No data available
              </Typography>
            </Box>
          )}
        </Paper>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {breakdowns.length > 0 ? (
            <MemoizedStocksList
              title={`📉 BREAKDOWNS (${breakdowns.length})`}
              data={breakdowns}
              layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
              showVolume={!isMobile} // Hide volume on mobile
              showSector={!isMobile} // Show sector on larger screens if table
              maxItems={isMobile ? 15 : 15} // Show fewer items on mobile
              isLoading={!isConnected}
              // Remove fixed containerHeight to allow natural flow
            />
          ) : (
            <Box sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="h6" sx={{ color: colors.primary, mb: 1 }}>
                📉 BREAKDOWNS (0)
              </Typography>
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", fontStyle: "italic" }}
              >
                Stocks breaking below support
                <br />
                No data available
              </Typography>
            </Box>
          )}
        </Paper>
      </Stack>
      {/* Record Movers - Stack vertically on ALL screens */}
      <Stack spacing={2}>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {newHighs.length > 0 ? (
            <MemoizedStocksList
              title={`🎯 NEW HIGHS (${newHighs.length})`}
              data={newHighs}
              layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
              showVolume={!isMobile} // Hide volume on mobile
              showSector={!isMobile} // Show sector on larger screens if table
              maxItems={isMobile ? 15 : 15} // Show fewer items on mobile
              isLoading={!isConnected}
              // Remove fixed containerHeight to allow natural flow
            />
          ) : (
            <Box sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="h6" sx={{ color: colors.primary, mb: 1 }}>
                🎯 NEW HIGHS (0)
              </Typography>
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", fontStyle: "italic" }}
              >
                Stocks hitting new 52-week highs
                <br />
                No data available
              </Typography>
            </Box>
          )}
        </Paper>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            borderRadius: 3,
            border: `1px solid ${colors.border}`,
            bgcolor: "background.paper",
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {newLows.length > 0 ? (
            <MemoizedStocksList
              title={`⬇️ NEW LOWS (${newLows.length})`}
              data={newLows}
              layoutType={isMobile ? "cards" : "table"} // Use cards on mobile
              showVolume={!isMobile} // Hide volume on mobile
              showSector={!isMobile} // Show sector on larger screens if table
              maxItems={isMobile ? 15 : 15} // Show fewer items on mobile
              isLoading={!isConnected}
              // Remove fixed containerHeight to allow natural flow
            />
          ) : (
            <Box sx={{ textAlign: "center", py: 2 }}>
              <Typography variant="h6" sx={{ color: colors.primary, mb: 1 }}>
                ⬇️ NEW LOWS (0)
              </Typography>
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", fontStyle: "italic" }}
              >
                Stocks hitting new 52-week lows
                <br />
                No data available
              </Typography>
            </Box>
          )}
        </Paper>
      </Stack>
      {/* Additional Analytics Summary */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          borderRadius: 3,
          border: `1px solid ${colors.border}`,
          bgcolor: "background.paper",
        }}
      >
        <Typography
          variant="h6"
          sx={{ mb: 1.5, color: colors.primary, fontWeight: 700 }}
        >
          📈 ANALYTICS SUMMARY
        </Typography>
        <Grid container spacing={1}>
          <Grid item xs={4} sm={2} md={1}>
            <Paper
              sx={{ p: 1, textAlign: "center", bgcolor: "background.default" }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: colors.positive,
                  fontWeight: 700,
                  fontSize: "1.1rem",
                }}
              >
                {topGainers.length}
              </Typography>
              <Typography variant="caption">GAINERS</Typography>
            </Paper>
          </Grid>
          <Grid item xs={4} sm={2} md={1}>
            <Paper
              sx={{ p: 1, textAlign: "center", bgcolor: "background.default" }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: colors.negative,
                  fontWeight: 700,
                  fontSize: "1.1rem",
                }}
              >
                {topLosers.length}
              </Typography>
              <Typography variant="caption">LOSERS</Typography>
            </Paper>
          </Grid>
          <Grid item xs={4} sm={2} md={1}>
            <Paper
              sx={{ p: 1, textAlign: "center", bgcolor: "background.default" }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: colors.primary,
                  fontWeight: 700,
                  fontSize: "1.1rem",
                }}
              >
                {volumeLeaders.length}
              </Typography>
              <Typography variant="caption">VOLUME</Typography>
            </Paper>
          </Grid>
          <Grid item xs={4} sm={2} md={1}>
            <Paper
              sx={{ p: 1, textAlign: "center", bgcolor: "background.default" }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: colors.neutral,
                  fontWeight: 700,
                  fontSize: "1.1rem",
                }}
              >
                {intradayBoosters.length}
              </Typography>
              <Typography variant="caption">BOOST</Typography>
            </Paper>
          </Grid>
          <Grid item xs={4} sm={2} md={1}>
            <Paper
              sx={{ p: 1, textAlign: "center", bgcolor: "background.default" }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: colors.accent,
                  fontWeight: 700,
                  fontSize: "1.1rem",
                }}
              >
                {gapUp.length + gapDown.length}
              </Typography>
              <Typography variant="caption">GAPS</Typography>
            </Paper>
          </Grid>
          <Grid item xs={4} sm={2} md={1}>
            <Paper
              sx={{ p: 1, textAlign: "center", bgcolor: "background.default" }}
            >
              <Typography
                variant="body2"
                sx={{ color: colors.text, fontWeight: 700, fontSize: "1.1rem" }}
              >
                {breakouts.length +
                  breakdowns.length}
              </Typography>
              <Typography variant="caption">BREAK</Typography>
            </Paper>
          </Grid>
        </Grid>
      </Paper>
    </Stack>
  );
  // Render function for the footer (RESPONSIVE)
  const renderFooter = () => (
    <Paper
      elevation={3}
      sx={{
        position: "sticky",
        bottom: 0,
        left: 0,
        right: 0,
        py: 1,
        px: 2,
        bgcolor: "background.paper",
        borderTop: `1px solid ${colors.border}`,
        zIndex: 10,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 1,
        fontSize: "0.75rem",
      }}
    >
      <Typography variant="caption" sx={{ flexShrink: 0 }}>
        🔴 LIVE | {totalStocks} inst | {sectors.length} sec
      </Typography>
      <Typography variant="caption" sx={{ flexShrink: 0 }}>
        G: {topGainers.length} | L:{" "}
        {topLosers.length}
      </Typography>
      <Typography variant="caption" sx={{ flexGrow: 1, textAlign: "right" }}>
        {new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}{" "}
        | {isConnected ? "LIVE" : "OFF"}
        {marketSummary && (
          <span style={{ marginLeft: 8 }}>
            | A/D: {marketSummary.advanceDeclineRatio} | B:{" "}
            {marketSummary.marketBreadth}%
          </span>
        )}
      </Typography>
    </Paper>
  );
  // Main render function
  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default",
        color: "text.primary",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {renderHeader()}
      {/* Sticky Section Navigation */}
      <SectionNavigation
        activeSection={activeSection}
        handleSectionChange={handleSectionChange}
        colors={colors}
        isMobile={isMobile}
      />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          py: 2,
          px: { xs: 1, sm: 2 },
          bgcolor: "background.default",
          overflowX: "hidden", // Prevent horizontal scroll on main container
        }}
      >
        <Container maxWidth="xl">
          {activeSection === "overview" && renderOverviewSection()}
          {activeSection === "search" && renderSearchSection()}
          {activeSection === "sectors" && renderSectorsSection()}
          {activeSection === "indices" && renderIndicesSection()}
          {activeSection === "movers" && renderMoversSection()}
          {activeSection === "gaps" && renderGapsSection()}
          {activeSection === "mcx" && renderMcxSection()}
          {activeSection === "fno" && renderFnoSection()}
          {activeSection === "analytics" && renderAnalyticsSection()}
        </Container>
      </Box>
      {renderFooter()}
    </Box>
  );
};
export default DashboardPage;
