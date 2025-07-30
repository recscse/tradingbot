// pages/DashboardPage.jsx - FIXED VERSION WITH BETTER DATA PROCESSING

import React, { useState, useMemo, useCallback } from "react";
import StocksList from "../components/common/StocksList";
// import DebugPanel from "../components/debug/DebugPanel";
import { useMarket } from "../hooks/useUnifiedMarketData";

// PERFORMANCE FIX: Memoized components to prevent unnecessary re-renders
const MemoizedStocksList = React.memo(StocksList);

// Bloomberg-style color scheme - moved outside component to prevent recreation
const BLOOMBERG_COLORS = {
  background: "#0f0f12",
  text: "#e6e6e6",
  positive: "#00ff00",
  negative: "#ff0000",
  neutral: "#ffff00",
  header: "#00b0f0",
  border: "#333333",
  tableHeader: "#1a1a1a",
  tableRowEven: "#141414",
  tableRowOdd: "#1a1a1a",
  cardBackground: "#1a1a1a",
  sectionBg: "#161618",
  warning: "#ff8c00",
  info: "#1e90ff",
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
  { id: "analytics", label: "ANALYTICS", icon: "🔍" },
];

// FIXED: Helper function to safely extract numeric values
const safeNumber = (value, defaultValue = 0) => {
  if (value === null || value === undefined || value === "")
    return defaultValue;
  const num = Number(value);
  return isNaN(num) ? defaultValue : num;
};

// FIXED: Helper function to safely extract arrays from analytics
// const safeArray = (data, key, fallback = []) => {
//   try {
//     if (!data || typeof data !== "object") return fallback;
//     const result = data[key];
//     return Array.isArray(result) ? result : fallback;
//   } catch (error) {
//     console.error(`Error extracting ${key}:`, error);
//     return fallback;
//   }
// };

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

const DashboardPage = () => {
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

    // indices-related imports
    indicesData,
    totalIndices,
    majorIndicesCount,
    // sectorIndicesCount,
    // getIndexData,
    getIndicesByPerformance,
    getMarketSentimentFromIndices,
    getIndicesSummary,
    // requestIndicesData,
  } = useMarket();

  const [activeSection, setActiveSection] = useState("overview");
  const [expandedSection, setExpandedSection] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSector, setSelectedSector] = useState("ALL");
  // const [showDebug, setShowDebug] = useState(false);

  // PERFORMANCE FIX: Memoized market summary
  const marketSummary = useMemo(() => getMarketSummary(), [getMarketSummary]);

  // PERFORMANCE FIX: Memoized search results
  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return [];
    return searchStocks(searchQuery);
  }, [searchQuery, searchStocks]);

  // PERFORMANCE FIX: Memoized sector stocks
  const sectorStocks = useMemo(() => {
    if (selectedSector === "ALL") return Object.values(marketData);
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

  // FIXED: Heavily optimized data processing with BETTER index detection and analytics handling
  const processedData = useMemo(() => {
    console.log("🔍 Processing market data...", {
      marketDataKeys: Object.keys(marketData || {}).length,
      analyticsIndicesCount: indicesData?.indices?.length || 0,
      majorIndicesCount: indicesData?.major_indices?.length || 0,
      sectorIndicesCount: indicesData?.sector_indices?.length || 0,
      topMoversStructure: topMovers ? Object.keys(topMovers) : [],
      gapAnalysisStructure: gapAnalysis ? Object.keys(gapAnalysis) : [],
      volumeAnalysisStructure: volumeAnalysis
        ? Object.keys(volumeAnalysis)
        : [],
    });

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

    // const indices = marketDataEntries
    //   .map(([key, data]) => processMarketDataEntry(key, data))
    //   .filter((item) => {
    //     if (!item || !item.last_price) return false;

    //     const keyLower = item.instrument_key.toLowerCase();
    //     const symbolLower = item.symbol.toLowerCase();
    //     const nameLower = (item.name || "").toLowerCase();

    //     // Comprehensive index detection
    //     const indexIndicators = [
    //       keyLower.includes("index"),
    //       keyLower.includes("nifty"),
    //       keyLower.includes("sensex"),
    //       keyLower.includes("banknifty"),
    //       keyLower.includes("finnifty"),
    //       keyLower.includes("midcpnifty"),
    //       symbolLower.match(/^(nifty|sensex|banknifty|finnifty|midcpnifty)$/),
    //       nameLower.includes("index"),
    //       item.instrument_type === "INDEX",
    //       item.exchange === "INDEX",
    //     ];

    //     return indexIndicators.some(Boolean);
    //   })
    //   .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent));

    // FIXED: Improved equity filtering with better exclusion
    const equityStocks = marketDataEntries
      .map(([key, data]) => processMarketDataEntry(key, data))
      .filter((item) => {
        if (!item || !item.last_price) return false;

        const keyLower = item.instrument_key.toLowerCase();
        const symbolLower = item.symbol.toLowerCase();

        // Exclude indices and non-equity instruments
        const isIndex = [
          keyLower.includes("index"),
          keyLower.includes("nifty"),
          keyLower.includes("sensex"),
          keyLower.includes("banknifty"),
          keyLower.includes("finnifty"),
          keyLower.includes("midcpnifty"),
          symbolLower.match(/^(nifty|sensex|banknifty|finnifty|midcpnifty)$/),
        ].some(Boolean);

        const isEquity =
          (keyLower.includes("nse") || keyLower.includes("eq")) && !isIndex;

        return isEquity;
      })
      .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent));

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
        console.log(`🔍 Extracting ${arrayKey} from:`, analyticsObject);

        if (!analyticsObject || typeof analyticsObject !== "object") {
          console.warn(`⚠️ ${arrayKey}: Invalid analytics object`);
          return [];
        }

        let data = analyticsObject[arrayKey];

        // Handle nested data structures
        if (!data && analyticsObject.data) {
          data = analyticsObject.data[arrayKey];
        }

        if (!Array.isArray(data)) {
          console.warn(`⚠️ ${arrayKey}: Not an array, got:`, typeof data);
          return [];
        }

        // Ensure each item has required fields
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
            ...item, // Keep all other fields
          }))
          .slice(0, limit);

        console.log(
          `✅ ${arrayKey}: Extracted ${validData.length} valid items`
        );
        return validData;
      } catch (error) {
        console.error(`❌ Error extracting ${arrayKey}:`, error);
        return [];
      }
    };

    // Extract analytics data with better error handling
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

    const result = {
      indices,
      majorIndices, // NEW: Major indices from analytics
      sectorIndices,
      equityStocks,
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

    console.log("📊 Processed data summary:", {
      indices: result.indices.length,
      majorIndices: result.majorIndices.length,
      sectorIndices: result.sectorIndices.length,
      equityStocks: result.equityStocks.length,
      mcxStocks: result.mcxStocks.length,
      topGainers: result.topGainers.length,
      topLosers: result.topLosers.length,
      gapUp: result.gapUp.length,
      gapDown: result.gapDown.length,
      intradayBoosters: result.intradayBoosters.length,
      volumeLeaders: result.volumeLeaders.length,
      newHighs: result.newHighs.length,
      newLows: result.newLows.length,
      breakouts: result.breakouts.length,
      breakdowns: result.breakdowns.length,
    });

    return result;
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

  // PERFORMANCE FIX: Memoized market status display
  const marketStatusDisplay = useMemo(() => {
    switch (marketStatus) {
      case "normal_open":
      case "open":
        return {
          text: "MARKET OPEN",
          color: BLOOMBERG_COLORS.positive,
          icon: "🟢",
        };
      case "pre_market":
        return {
          text: "PRE-MARKET",
          color: BLOOMBERG_COLORS.warning,
          icon: "🟡",
        };
      case "after_market":
        return {
          text: "AFTER-MARKET",
          color: BLOOMBERG_COLORS.info,
          icon: "🔵",
        };
      case "closed":
      default:
        return {
          text: "MARKET CLOSED",
          color: BLOOMBERG_COLORS.negative,
          icon: "🔴",
        };
    }
  }, [marketStatus]);

  // PERFORMANCE FIX: Memoized callback functions
  const toggleExpanded = useCallback(
    (section) =>
      setExpandedSection(expandedSection === section ? null : section),
    [expandedSection]
  );

  const handleSectionChange = useCallback(
    (sectionId) => setActiveSection(sectionId),
    []
  );
  const handleSearchChange = useCallback(
    (e) => setSearchQuery(e.target.value),
    []
  );
  const handleSectorChange = useCallback(
    (sector) => setSelectedSector(sector),
    []
  );
  // const handleDebugToggle = useCallback(
  //   () => setShowDebug((prev) => !prev),
  //   []
  // );

  // Render function for the header
  const renderHeader = () => (
    <div
      style={{
        background: `linear-gradient(90deg, ${BLOOMBERG_COLORS.cardBackground}, ${BLOOMBERG_COLORS.sectionBg})`,
        borderBottom: `2px solid ${BLOOMBERG_COLORS.header}`,
        padding: "15px 20px",
        position: "sticky",
        top: 0,
        zIndex: 1000,
        boxShadow: "0 2px 10px rgba(0, 180, 240, 0.3)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "15px",
        }}
      >
        <h1
          style={{
            color: BLOOMBERG_COLORS.header,
            margin: 0,
            fontSize: "24px",
            fontWeight: "bold",
            textShadow: "0 0 10px rgba(0, 180, 240, 0.5)",
          }}
        >
          📈 LIVE MARKET TERMINAL
        </h1>

        <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          {/* <button
            onClick={handleDebugToggle}
            style={{
              background: showDebug ? BLOOMBERG_COLORS.positive : "transparent",
              color: showDebug
                ? BLOOMBERG_COLORS.background
                : BLOOMBERG_COLORS.header,
              border: `1px solid ${BLOOMBERG_COLORS.header}`,
              padding: "4px 8px",
              fontSize: "10px",
              fontWeight: "bold",
              cursor: "pointer",
              borderRadius: "3px",
              fontFamily: "'Courier New', monospace",
            }}
          >
            🔧 DEBUG
          </button> */}

          <div
            style={{
              padding: "8px 15px",
              background: marketStatusDisplay.color,
              color: BLOOMBERG_COLORS.background,
              borderRadius: "4px",
              fontWeight: "bold",
              fontSize: "12px",
              display: "flex",
              alignItems: "center",
              gap: "5px",
            }}
          >
            <span>{marketStatusDisplay.icon}</span>
            {marketStatusDisplay.text}
          </div>

          <div
            style={{
              padding: "8px 15px",
              background: isConnected
                ? BLOOMBERG_COLORS.positive
                : BLOOMBERG_COLORS.negative,
              color: BLOOMBERG_COLORS.background,
              borderRadius: "4px",
              fontWeight: "bold",
              fontSize: "12px",
              textTransform: "uppercase",
              boxShadow: isConnected
                ? "0 0 10px rgba(0, 255, 0, 0.5)"
                : "0 0 10px rgba(255, 0, 0, 0.5)",
              cursor: !isConnected ? "pointer" : "default",
            }}
            onClick={!isConnected ? reconnect : undefined}
          >
            {connectionStatus} {isStale && "(STALE)"}
          </div>

          <div
            style={{
              fontSize: "12px",
              color: BLOOMBERG_COLORS.text,
              opacity: 0.8,
              display: "flex",
              gap: "10px",
            }}
          >
            <span>📊 {totalStocks} stocks</span>
            <span>🏢 {sectors.length} sectors</span>
            <span>
              📈 {totalIndices || processedData.indices.length} indices
            </span>
            {majorIndicesCount > 0 && <span>🏛️ {majorIndicesCount} major</span>}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            onClick={() => handleSectionChange(section.id)}
            style={{
              background:
                activeSection === section.id
                  ? BLOOMBERG_COLORS.header
                  : "transparent",
              color:
                activeSection === section.id
                  ? BLOOMBERG_COLORS.background
                  : BLOOMBERG_COLORS.text,
              border: `1px solid ${BLOOMBERG_COLORS.header}`,
              padding: "8px 16px",
              fontSize: "12px",
              fontWeight: "bold",
              cursor: "pointer",
              borderRadius: "4px",
              transition: "all 0.3s ease",
              fontFamily: "'Courier New', monospace",
            }}
          >
            {section.icon} {section.label}
          </button>
        ))}
      </div>
    </div>
  );

  // Render function for the overview section
  const renderOverviewSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      {marketSummary && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        >
          <h2
            style={{
              color: BLOOMBERG_COLORS.header,
              marginBottom: "15px",
              fontSize: "18px",
              fontWeight: "bold",
            }}
          >
            📊 ADVANCE DECLINE RATIO
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: "15px",
              fontSize: "14px",
            }}
          >
            {[
              {
                value: marketSummary.advancing,
                label: "ADVANCING",
                color: BLOOMBERG_COLORS.positive,
              },
              {
                value: marketSummary.declining,
                label: "DECLINING",
                color: BLOOMBERG_COLORS.negative,
              },
              {
                value: marketSummary.unchanged,
                label: "UNCHANGED",
                color: BLOOMBERG_COLORS.neutral,
              },
              {
                value: marketSummary.advanceDeclineRatio,
                label: "A/D RATIO",
                color: BLOOMBERG_COLORS.header,
              },
              {
                value: `${marketSummary.marketBreadth}%`,
                label: "BREADTH",
                color: BLOOMBERG_COLORS.text,
              },

              // NEW: Add indices sentiment
              ...(indicesSentiment.sentiment !== "unknown"
                ? [
                    {
                      value: indicesSentiment.sentiment
                        .toUpperCase()
                        .replace("_", " "),
                      label: "INDICES SENTIMENT",
                      color: indicesSentiment.sentiment.includes("bullish")
                        ? BLOOMBERG_COLORS.positive
                        : indicesSentiment.sentiment.includes("bearish")
                        ? BLOOMBERG_COLORS.negative
                        : BLOOMBERG_COLORS.neutral,
                    },
                  ]
                : []),
            ].map((item, index) => (
              <div key={index} style={{ textAlign: "center" }}>
                <div
                  style={{
                    color: item.color,
                    fontSize: "20px",
                    fontWeight: "bold",
                  }}
                >
                  {item.value}
                </div>
                <div>{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Major Indices Quick View */}
      {processedData.majorIndices.length > 0 && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        >
          <h2
            style={{
              color: BLOOMBERG_COLORS.header,
              marginBottom: "15px",
              fontSize: "18px",
              fontWeight: "bold",
            }}
          >
            🏛️ MAJOR MARKET INDICES ({processedData.majorIndices.length})
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "15px",
            }}
          >
            {processedData.majorIndices.slice(0, 6).map((index, i) => (
              <div
                key={i}
                style={{
                  background: BLOOMBERG_COLORS.cardBackground,
                  border: `1px solid ${BLOOMBERG_COLORS.border}`,
                  borderRadius: "6px",
                  padding: "15px",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontWeight: "bold",
                    fontSize: "14px",
                    color: BLOOMBERG_COLORS.text,
                    marginBottom: "5px",
                  }}
                >
                  {index.symbol}
                </div>
                <div
                  style={{
                    fontSize: "18px",
                    fontWeight: "bold",
                    color: BLOOMBERG_COLORS.text,
                    marginBottom: "5px",
                  }}
                >
                  {index.last_price?.toFixed(2)}
                </div>
                <div
                  style={{
                    color:
                      (index.change_percent || 0) >= 0
                        ? BLOOMBERG_COLORS.positive
                        : BLOOMBERG_COLORS.negative,
                    fontWeight: "bold",
                    fontSize: "14px",
                  }}
                >
                  {(index.change_percent || 0) >= 0 ? "+" : ""}
                  {(index.change_percent || 0).toFixed(2)}%
                </div>
                <div
                  style={{
                    fontSize: "12px",
                    color: BLOOMBERG_COLORS.text,
                    opacity: 0.7,
                  }}
                >
                  {(index.change || 0) >= 0 ? "+" : ""}
                  {(index.change || 0).toFixed(2)} pts
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div
        style={{
          background: BLOOMBERG_COLORS.sectionBg,
          borderRadius: "8px",
          padding: "20px",
          border: `1px solid ${BLOOMBERG_COLORS.border}`,
          boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
        }}
      >
        <MemoizedStocksList
          title={`🏛️ MARKET INDICES (${processedData.indices.length})`}
          data={processedData.indices}
          layoutType="cards"
          showVolume={false}
          isLoading={!isConnected}
          maxItems={12}
        />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(500px, 1fr))",
          gap: "20px",
        }}
      >
        {[
          { title: "🚀 TOP GAINERS", data: processedData.topGainers },
          { title: "📉 TOP LOSERS", data: processedData.topLosers },
        ].map((section, index) => (
          <div
            key={index}
            style={{
              background: BLOOMBERG_COLORS.sectionBg,
              borderRadius: "8px",
              padding: "20px",
              border: `1px solid ${BLOOMBERG_COLORS.border}`,
              boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
            }}
          >
            <MemoizedStocksList
              title={`${section.title} (${section.data.length})`}
              data={section.data}
              layoutType="table"
              showVolume={true}
              showSector={true}
              maxItems={8}
              isLoading={!isConnected}
            />
          </div>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
          gap: "20px",
        }}
      >
        {[
          {
            title: "⚡ INTRADAY BOOSTERS",
            data: processedData.intradayBoosters,
          },
          { title: "📊 VOLUME LEADERS", data: processedData.volumeLeaders },
        ].map((section, index) => (
          <div
            key={index}
            style={{
              background: BLOOMBERG_COLORS.sectionBg,
              borderRadius: "8px",
              padding: "20px",
              border: `1px solid ${BLOOMBERG_COLORS.border}`,
              boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
            }}
          >
            <MemoizedStocksList
              title={`${section.title} (${section.data.length})`}
              data={section.data}
              layoutType="table"
              showVolume={true}
              maxItems={10}
              isLoading={!isConnected}
            />
          </div>
        ))}
      </div>
    </div>
  );

  // Render function for the search section
  const renderSearchSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      <div
        style={{
          background: BLOOMBERG_COLORS.sectionBg,
          borderRadius: "8px",
          padding: "20px",
          border: `1px solid ${BLOOMBERG_COLORS.border}`,
        }}
      >
        <h2
          style={{
            color: BLOOMBERG_COLORS.header,
            marginBottom: "15px",
            fontSize: "18px",
            fontWeight: "bold",
          }}
        >
          🔍 SEARCH STOCKS
        </h2>
        <input
          type="text"
          placeholder="Search by symbol or company name..."
          value={searchQuery}
          onChange={handleSearchChange}
          style={{
            width: "100%",
            padding: "12px",
            backgroundColor: BLOOMBERG_COLORS.cardBackground,
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            borderRadius: "4px",
            color: BLOOMBERG_COLORS.text,
            fontSize: "16px",
            fontFamily: "'Courier New', monospace",
          }}
        />
      </div>

      {searchResults.length > 0 && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
          }}
        >
          <MemoizedStocksList
            title={`📊 SEARCH RESULTS (${searchResults.length})`}
            data={searchResults}
            layoutType="table"
            showVolume={true}
            showName={true}
            showSector={true}
            maxItems={50}
            isLoading={!isConnected}
          />
        </div>
      )}
    </div>
  );

  // Render function for the sectors section
  const renderSectorsSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      {/* Sector Heatmap */}
      {heatmap && heatmap.sectors && heatmap.sectors.length > 0 && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        >
          <h2
            style={{
              color: BLOOMBERG_COLORS.header,
              marginBottom: "15px",
              fontSize: "18px",
              fontWeight: "bold",
            }}
          >
            🔥 SECTOR HEATMAP ({heatmap.sectors.length} sectors)
          </h2>

          <div style={{ display: "grid", gap: "10px" }}>
            {heatmap.sectors.map((sector, index) => (
              <div
                key={index}
                style={{
                  background: BLOOMBERG_COLORS.cardBackground,
                  border: `1px solid ${BLOOMBERG_COLORS.border}`,
                  borderRadius: "6px",
                  padding: "15px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontWeight: "bold",
                      fontSize: "14px",
                      color: BLOOMBERG_COLORS.text,
                      marginBottom: "5px",
                    }}
                  >
                    {sector.sector}
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: BLOOMBERG_COLORS.text,
                      opacity: 0.8,
                    }}
                  >
                    {sector.stocks_count} stocks | Advancing: {sector.advancing}{" "}
                    | Declining: {sector.declining}
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      color:
                        sector.avg_change_percent >= 0
                          ? BLOOMBERG_COLORS.positive
                          : BLOOMBERG_COLORS.negative,
                      fontWeight: "bold",
                      fontSize: "16px",
                    }}
                  >
                    {sector.avg_change_percent >= 0 ? "+" : ""}
                    {sector.avg_change_percent}%
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: BLOOMBERG_COLORS.text,
                      opacity: 0.7,
                    }}
                  >
                    Strength: {sector.strength_score}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sector Selection and Stocks */}
      <div
        style={{
          background: BLOOMBERG_COLORS.sectionBg,
          borderRadius: "8px",
          padding: "20px",
          border: `1px solid ${BLOOMBERG_COLORS.border}`,
        }}
      >
        <div style={{ marginBottom: "20px" }}>
          <h2
            style={{
              color: BLOOMBERG_COLORS.header,
              marginBottom: "15px",
              fontSize: "18px",
              fontWeight: "bold",
            }}
          >
            🏢 SECTOR ANALYSIS
          </h2>

          <select
            value={selectedSector}
            onChange={(e) => handleSectorChange(e.target.value)}
            style={{
              padding: "10px",
              backgroundColor: BLOOMBERG_COLORS.cardBackground,
              border: `1px solid ${BLOOMBERG_COLORS.border}`,
              borderRadius: "4px",
              color: BLOOMBERG_COLORS.text,
              fontSize: "14px",
              fontFamily: "'Courier New', monospace",
              minWidth: "200px",
            }}
          >
            <option value="ALL">ALL SECTORS</option>
            {sectors.map((sector) => (
              <option key={sector} value={sector}>
                {sector}
              </option>
            ))}
          </select>
        </div>

        <MemoizedStocksList
          title={`📊 ${
            selectedSector === "ALL" ? "ALL STOCKS" : selectedSector + " SECTOR"
          } (${sectorStocks.length})`}
          data={sectorStocks}
          layoutType="table"
          showVolume={true}
          showName={true}
          showSector={selectedSector === "ALL"}
          maxItems={50}
          isLoading={!isConnected}
        />
      </div>
    </div>
  );

  // Render function for the indices section
  const renderIndicesSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      {/* Indices Summary Stats */}
      {indicesSummary && Object.keys(indicesSummary).length > 0 && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        >
          <h2
            style={{
              color: BLOOMBERG_COLORS.header,
              marginBottom: "15px",
              fontSize: "18px",
              fontWeight: "bold",
            }}
          >
            📊 INDICES OVERVIEW
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: "15px",
              fontSize: "14px",
            }}
          >
            {[
              {
                value: indicesSummary.total_indices || 0,
                label: "TOTAL INDICES",
                color: BLOOMBERG_COLORS.header,
              },
              {
                value: indicesSummary.major_up || 0,
                label: "MAJOR UP",
                color: BLOOMBERG_COLORS.positive,
              },
              {
                value: indicesSummary.major_down || 0,
                label: "MAJOR DOWN",
                color: BLOOMBERG_COLORS.negative,
              },
              {
                value: indicesSummary.sector_up || 0,
                label: "SECTOR UP",
                color: BLOOMBERG_COLORS.positive,
              },
              {
                value: indicesSummary.sector_down || 0,
                label: "SECTOR DOWN",
                color: BLOOMBERG_COLORS.negative,
              },
              ...(indicesSentiment.sentiment !== "unknown"
                ? [
                    {
                      value: `${indicesSentiment.confidence}%`,
                      label: "SENTIMENT CONFIDENCE",
                      color: BLOOMBERG_COLORS.info,
                    },
                  ]
                : []),
            ].map((item, index) => (
              <div key={index} style={{ textAlign: "center" }}>
                <div
                  style={{
                    color: item.color,
                    fontSize: "20px",
                    fontWeight: "bold",
                  }}
                >
                  {item.value}
                </div>
                <div>{item.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Major Market Indices */}
      {processedData.majorIndices.length > 0 && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        >
          <MemoizedStocksList
            title={`🏛️ MAJOR MARKET INDICES (${processedData.majorIndices.length})`}
            data={processedData.majorIndices}
            layoutType="table"
            showVolume={false}
            showName={true}
            maxItems={20}
            isLoading={!isConnected}
          />
        </div>
      )}

      {/* Sector Indices */}
      {processedData.sectorIndices.length > 0 && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        >
          <MemoizedStocksList
            title={`🏢 SECTOR INDICES (${processedData.sectorIndices.length})`}
            data={processedData.sectorIndices}
            layoutType="table"
            showVolume={false}
            showName={true}
            maxItems={30}
            isLoading={!isConnected}
          />
        </div>
      )}

      {/* Top Performing Indices */}
      {indicesPerformance &&
        (indicesPerformance.gainers.length > 0 ||
          indicesPerformance.losers.length > 0) && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(500px, 1fr))",
              gap: "20px",
            }}
          >
            {indicesPerformance.gainers.length > 0 && (
              <div
                style={{
                  background: BLOOMBERG_COLORS.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${BLOOMBERG_COLORS.border}`,
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
                }}
              >
                <MemoizedStocksList
                  title={`📈 TOP GAINING INDICES (${indicesPerformance.gainers.length})`}
                  data={indicesPerformance.gainers.slice(0, 10)}
                  layoutType="table"
                  showVolume={false}
                  showName={true}
                  maxItems={10}
                  isLoading={!isConnected}
                />
              </div>
            )}

            {indicesPerformance.losers.length > 0 && (
              <div
                style={{
                  background: BLOOMBERG_COLORS.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${BLOOMBERG_COLORS.border}`,
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
                }}
              >
                <MemoizedStocksList
                  title={`📉 TOP LOSING INDICES (${indicesPerformance.losers.length})`}
                  data={indicesPerformance.losers.slice(0, 10)}
                  layoutType="table"
                  showVolume={false}
                  showName={true}
                  maxItems={10}
                  isLoading={!isConnected}
                />
              </div>
            )}
          </div>
        )}

      {/* All Indices Table */}
      <div
        style={{
          background: BLOOMBERG_COLORS.sectionBg,
          borderRadius: "8px",
          padding: "20px",
          border: `1px solid ${BLOOMBERG_COLORS.border}`,
          boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
        }}
      >
        <MemoizedStocksList
          title={`🏛️ ALL MARKET INDICES (${processedData.indices.length})`}
          data={processedData.indices}
          layoutType="table"
          showVolume={true}
          showName={true}
          maxItems={100}
          isLoading={!isConnected}
        />
      </div>
    </div>
  );

  // Render function for the movers section
  const renderMoversSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}
      >
        {[
          {
            type: "gainers",
            title: "🚀 TOP GAINERS",
            data: processedData.topGainers,
          },
          {
            type: "losers",
            title: "📉 TOP LOSERS",
            data: processedData.topLosers,
          },
        ].map((section) => (
          <div
            key={section.type}
            style={{
              background: BLOOMBERG_COLORS.sectionBg,
              borderRadius: "8px",
              padding: "20px",
              border: `1px solid ${BLOOMBERG_COLORS.border}`,
              position: "relative",
            }}
          >
            <button
              onClick={() => toggleExpanded(section.type)}
              style={{
                position: "absolute",
                top: "15px",
                right: "15px",
                background: "transparent",
                border: `1px solid ${BLOOMBERG_COLORS.header}`,
                color: BLOOMBERG_COLORS.header,
                padding: "5px 10px",
                fontSize: "12px",
                cursor: "pointer",
                borderRadius: "4px",
              }}
            >
              {expandedSection === section.type ? "COMPACT" : "EXPAND"}
            </button>

            <MemoizedStocksList
              title={`${section.title} (${section.data.length})`}
              data={section.data}
              layoutType="table"
              showVolume={true}
              showSector={true}
              maxItems={expandedSection === section.type ? 50 : 15}
              isLoading={!isConnected}
            />
          </div>
        ))}
      </div>

      <div
        style={{
          background: BLOOMBERG_COLORS.sectionBg,
          borderRadius: "8px",
          padding: "20px",
          border: `1px solid ${BLOOMBERG_COLORS.border}`,
        }}
      >
        <MemoizedStocksList
          title={`📊 VOLUME LEADERS (${processedData.volumeLeaders.length})`}
          data={processedData.volumeLeaders}
          layoutType="table"
          showVolume={true}
          showSector={true}
          maxItems={20}
          isLoading={!isConnected}
        />
      </div>
    </div>
  );

  // Render function for the gaps section
  const renderGapsSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}
      >
        {[
          { title: "📈 GAP UP", data: processedData.gapUp },
          { title: "📉 GAP DOWN", data: processedData.gapDown },
        ].map((section, index) => (
          <div
            key={index}
            style={{
              background: BLOOMBERG_COLORS.sectionBg,
              borderRadius: "8px",
              padding: "20px",
              border: `1px solid ${BLOOMBERG_COLORS.border}`,
            }}
          >
            <MemoizedStocksList
              title={`${section.title} (${section.data.length})`}
              data={section.data}
              layoutType="table"
              showVolume={true}
              showSector={true}
              maxItems={20}
              isLoading={!isConnected}
            />
          </div>
        ))}
      </div>
    </div>
  );

  // Render function for the MCX section
  const renderMcxSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      <div
        style={{
          background: BLOOMBERG_COLORS.sectionBg,
          borderRadius: "8px",
          padding: "20px",
          border: `1px solid ${BLOOMBERG_COLORS.border}`,
          boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
        }}
      >
        <MemoizedStocksList
          title={`💰 MCX COMMODITIES (${processedData.mcxStocks.length})`}
          data={processedData.mcxStocks}
          layoutType="table"
          showVolume={true}
          maxItems={50}
          isLoading={!isConnected}
        />
      </div>
    </div>
  );

  // FIXED: Analytics section renderer with comprehensive data display
  const renderAnalyticsSection = () => (
    <div style={{ display: "grid", gap: "25px" }}>
      {/* Market Sentiment */}
      {marketSentiment && Object.keys(marketSentiment).length > 0 && (
        <div
          style={{
            background: BLOOMBERG_COLORS.sectionBg,
            borderRadius: "8px",
            padding: "20px",
            border: `1px solid ${BLOOMBERG_COLORS.border}`,
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        >
          <h2
            style={{
              color: BLOOMBERG_COLORS.header,
              marginBottom: "15px",
              fontSize: "18px",
              fontWeight: "bold",
            }}
          >
            📊 MARKET SENTIMENT
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "15px",
              fontSize: "14px",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  color:
                    marketSentiment.sentiment === "bullish"
                      ? BLOOMBERG_COLORS.positive
                      : marketSentiment.sentiment === "bearish"
                      ? BLOOMBERG_COLORS.negative
                      : BLOOMBERG_COLORS.neutral,
                  fontSize: "20px",
                  fontWeight: "bold",
                  textTransform: "uppercase",
                }}
              >
                {marketSentiment.sentiment || "NEUTRAL"}
              </div>
              <div>SENTIMENT</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  color: BLOOMBERG_COLORS.header,
                  fontSize: "20px",
                  fontWeight: "bold",
                }}
              >
                {marketSentiment.confidence || 0}%
              </div>
              <div>CONFIDENCE</div>
            </div>
            {marketSentiment.market_breadth && (
              <>
                <div style={{ textAlign: "center" }}>
                  <div
                    style={{
                      color: BLOOMBERG_COLORS.positive,
                      fontSize: "20px",
                      fontWeight: "bold",
                    }}
                  >
                    {marketSentiment.market_breadth.advancing || 0}
                  </div>
                  <div>ADVANCING</div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div
                    style={{
                      color: BLOOMBERG_COLORS.negative,
                      fontSize: "20px",
                      fontWeight: "bold",
                    }}
                  >
                    {marketSentiment.market_breadth.declining || 0}
                  </div>
                  <div>DECLINING</div>
                </div>
              </>
            )}
            {marketSentiment.sentiment_score !== undefined && (
              <div style={{ textAlign: "center" }}>
                <div
                  style={{
                    color:
                      marketSentiment.sentiment_score > 0
                        ? BLOOMBERG_COLORS.positive
                        : marketSentiment.sentiment_score < 0
                        ? BLOOMBERG_COLORS.negative
                        : BLOOMBERG_COLORS.neutral,
                    fontSize: "20px",
                    fontWeight: "bold",
                  }}
                >
                  {marketSentiment.sentiment_score.toFixed(2)}
                </div>
                <div>SENTIMENT SCORE</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Breakout Analysis */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(500px, 1fr))",
          gap: "20px",
        }}
      >
        {[
          {
            title: "📈 BREAKOUTS",
            data: processedData.breakouts,
            description: "Stocks breaking above resistance levels",
          },
          {
            title: "📉 BREAKDOWNS",
            data: processedData.breakdowns,
            description: "Stocks breaking below support levels",
          },
        ].map((section, index) => (
          <div
            key={index}
            style={{
              background: BLOOMBERG_COLORS.sectionBg,
              borderRadius: "8px",
              padding: "20px",
              border: `1px solid ${BLOOMBERG_COLORS.border}`,
              boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
            }}
          >
            {section.data.length > 0 ? (
              <MemoizedStocksList
                title={`${section.title} (${section.data.length})`}
                data={section.data}
                layoutType="table"
                showVolume={true}
                showSector={true}
                maxItems={15}
                isLoading={!isConnected}
              />
            ) : (
              <div>
                <h3
                  style={{
                    color: BLOOMBERG_COLORS.header,
                    marginBottom: "10px",
                    fontSize: "16px",
                  }}
                >
                  {section.title} (0)
                </h3>
                <div
                  style={{
                    color: BLOOMBERG_COLORS.text,
                    opacity: 0.7,
                    fontStyle: "italic",
                    textAlign: "center",
                    padding: "20px",
                  }}
                >
                  {section.description}
                  <br />
                  No data available at the moment
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Record Movers */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(500px, 1fr))",
          gap: "20px",
        }}
      >
        {[
          {
            title: "🎯 NEW HIGHS",
            data: processedData.newHighs,
            description: "Stocks hitting new 52-week highs",
          },
          {
            title: "⬇️ NEW LOWS",
            data: processedData.newLows,
            description: "Stocks hitting new 52-week lows",
          },
        ].map((section, index) => (
          <div
            key={index}
            style={{
              background: BLOOMBERG_COLORS.sectionBg,
              borderRadius: "8px",
              padding: "20px",
              border: `1px solid ${BLOOMBERG_COLORS.border}`,
              boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
            }}
          >
            {section.data.length > 0 ? (
              <MemoizedStocksList
                title={`${section.title} (${section.data.length})`}
                data={section.data}
                layoutType="table"
                showVolume={true}
                showSector={true}
                maxItems={15}
                isLoading={!isConnected}
              />
            ) : (
              <div>
                <h3
                  style={{
                    color: BLOOMBERG_COLORS.header,
                    marginBottom: "10px",
                    fontSize: "16px",
                  }}
                >
                  {section.title} (0)
                </h3>
                <div
                  style={{
                    color: BLOOMBERG_COLORS.text,
                    opacity: 0.7,
                    fontStyle: "italic",
                    textAlign: "center",
                    padding: "20px",
                  }}
                >
                  {section.description}
                  <br />
                  No data available at the moment
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Additional Analytics Summary */}
      <div
        style={{
          background: BLOOMBERG_COLORS.sectionBg,
          borderRadius: "8px",
          padding: "20px",
          border: `1px solid ${BLOOMBERG_COLORS.border}`,
          boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
        }}
      >
        <h2
          style={{
            color: BLOOMBERG_COLORS.header,
            marginBottom: "15px",
            fontSize: "18px",
            fontWeight: "bold",
          }}
        >
          📈 ANALYTICS SUMMARY
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
            fontSize: "14px",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                color: BLOOMBERG_COLORS.positive,
                fontSize: "24px",
                fontWeight: "bold",
              }}
            >
              {processedData.topGainers.length}
            </div>
            <div>TOP GAINERS</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                color: BLOOMBERG_COLORS.negative,
                fontSize: "24px",
                fontWeight: "bold",
              }}
            >
              {processedData.topLosers.length}
            </div>
            <div>TOP LOSERS</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                color: BLOOMBERG_COLORS.header,
                fontSize: "24px",
                fontWeight: "bold",
              }}
            >
              {processedData.volumeLeaders.length}
            </div>
            <div>VOLUME LEADERS</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                color: BLOOMBERG_COLORS.warning,
                fontSize: "24px",
                fontWeight: "bold",
              }}
            >
              {processedData.intradayBoosters.length}
            </div>
            <div>INTRADAY PICKS</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                color: BLOOMBERG_COLORS.info,
                fontSize: "24px",
                fontWeight: "bold",
              }}
            >
              {processedData.gapUp.length + processedData.gapDown.length}
            </div>
            <div>GAP STOCKS</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                color: BLOOMBERG_COLORS.text,
                fontSize: "24px",
                fontWeight: "bold",
              }}
            >
              {processedData.breakouts.length + processedData.breakdowns.length}
            </div>
            <div>BREAKOUT/DOWNS</div>
          </div>
        </div>
      </div>
    </div>
  );

  // Render function for the footer
  const renderFooter = () => (
    <div
      style={{
        background: BLOOMBERG_COLORS.cardBackground,
        borderTop: `1px solid ${BLOOMBERG_COLORS.border}`,
        padding: "15px 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: "12px",
        color: BLOOMBERG_COLORS.text,
        position: "sticky",
        bottom: 0,
      }}
    >
      <div>
        🔴 LIVE MARKET DATA | {totalStocks} INSTRUMENTS TRACKED |{" "}
        {sectors.length} SECTORS | GAINERS: {processedData.topGainers.length} |
        LOSERS: {processedData.topLosers.length}
      </div>
      <div>
        {new Date().toLocaleString()} | DATA: {isConnected ? "LIVE" : "OFFLINE"}
        {marketSummary && (
          <span style={{ marginLeft: "10px" }}>
            | A/D: {marketSummary.advanceDeclineRatio} | BREADTH:{" "}
            {marketSummary.marketBreadth}%
          </span>
        )}
      </div>
    </div>
  );

  // Main render function
  return (
    <div
      style={{
        backgroundColor: BLOOMBERG_COLORS.background,
        color: BLOOMBERG_COLORS.text,
        minHeight: "100vh",
        fontFamily: "'Courier New', monospace",
        fontSize: "14px",
        position: "relative",
      }}
    >
      {/* {showDebug && (
        <DebugPanel
          isConnected={isConnected}
          connectionStatus={connectionStatus}
          topMovers={topMovers}
          gapAnalysis={gapAnalysis}
          heatmap={heatmap}
          volumeAnalysis={volumeAnalysis}
          intradayStocks={intradayStocks}
          recordMovers={recordMovers}
          marketData={marketData}
          indicesData={indicesData}
          indicesSummary={indicesSummary}
        />
      )} */}

      {renderHeader()}

      <div style={{ padding: "20px" }}>
        {activeSection === "overview" && renderOverviewSection()}
        {activeSection === "search" && renderSearchSection()}
        {activeSection === "sectors" && renderSectorsSection()}
        {activeSection === "indices" && renderIndicesSection()}
        {activeSection === "movers" && renderMoversSection()}
        {activeSection === "gaps" && renderGapsSection()}
        {activeSection === "mcx" && renderMcxSection()}
        {activeSection === "analytics" && renderAnalyticsSection()}
      </div>

      {renderFooter()}
    </div>
  );
};

export default DashboardPage;
