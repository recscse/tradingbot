// pages/DashboardPage.jsx - ENHANCED WITH DEBUG AND FIXES

import React, { useState, useMemo } from "react";
import StocksList from "../components/common/StocksList";
import DebugPanel from "../components/debug/DebugPanel"; // Add debug panel
import { useMarket } from "../hooks/useUnifiedMarketData";

const DashboardPage = () => {
  // Get all data from unified market hook
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
  } = useMarket();

  const [activeSection, setActiveSection] = useState("overview");
  const [expandedSection, setExpandedSection] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSector, setSelectedSector] = useState("ALL");
  const [showDebug, setShowDebug] = useState(true); // Debug panel toggle

  // Bloomberg-style color scheme
  const bloombergColors = {
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

  // Get market summary stats
  const marketSummary = getMarketSummary();

  // Search results
  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return [];
    return searchStocks(searchQuery);
  }, [searchQuery, searchStocks]);

  // Sector-based filtering
  const sectorStocks = useMemo(() => {
    if (selectedSector === "ALL") return Object.values(marketData);
    const stocksBySector = getStocksBySector();
    return stocksBySector[selectedSector] || [];
  }, [selectedSector, getStocksBySector, marketData]);

  console.log("📊 Variables:", {
    marketSentiment,
    setSelectedSector,
    sectorStocks,
  });
  // FIXED: Enhanced data processing with better validation
  const processedData = useMemo(() => {
    console.log("🔍 Processing data for dashboard...");
    console.log("📊 Raw analytics data:", {
      topMovers: topMovers,
      gapAnalysis: gapAnalysis,
      heatmap: heatmap,
      volumeAnalysis: volumeAnalysis,
      intradayStocks: intradayStocks,
      recordMovers: recordMovers,
    });

    // FIXED: Extract indices with better filtering
    const indices = Object.entries(marketData || {})
      .filter(([key, data]) => {
        const isIndex = key.includes("INDEX") || key.includes("SENSEX");
        const hasValidData =
          data && (data.ltp || data.last_price) && data.symbol;
        return isIndex && hasValidData;
      })
      .map(([key, data]) => ({
        instrument_key: key,
        symbol: data.symbol || key.split("|").pop() || key,
        name: data.name || data.symbol,
        last_price: data.ltp || data.last_price,
        change: data.change || 0,
        change_percent: data.change_percent || 0,
        high: data.high || data.ltp || data.last_price,
        low: data.low || data.ltp || data.last_price,
        volume: data.volume || 0,
      }));

    // FIXED: Extract equity stocks with validation
    const equityStocks = Object.entries(marketData || {})
      .filter(([key, data]) => {
        const isEquity =
          (key.includes("EQ") || key.includes("NSE")) && !key.includes("INDEX");
        const hasValidData =
          data && (data.ltp || data.last_price) && data.symbol;
        return isEquity && hasValidData;
      })
      .map(([key, data]) => ({
        instrument_key: key,
        symbol: data.symbol || key.split("|").pop() || key,
        name: data.name || data.symbol,
        last_price: data.ltp || data.last_price,
        change: data.change || 0,
        change_percent: data.change_percent || 0,
        volume: data.volume || 0,
        high: data.high || data.ltp || data.last_price,
        low: data.low || data.ltp || data.last_price,
        sector: data.sector || "OTHER",
      }));

    // FIXED: Extract MCX data
    const mcxStocks = Object.entries(marketData || {})
      .filter(([key, data]) => {
        const isMCX = key.includes("MCX");
        const hasValidData =
          data && (data.ltp || data.last_price) && data.symbol;
        return isMCX && hasValidData;
      })
      .map(([key, data]) => ({
        instrument_key: key,
        symbol: data.symbol || key.split("|").pop() || key,
        last_price: data.ltp || data.last_price,
        change: data.change || 0,
        change_percent: data.change_percent || 0,
        volume: data.volume || 0,
      }));

    // FIXED: Process analytics with better validation and logging
    const getAnalyticsArray = (analyticsData, arrayKey, fallback = []) => {
      try {
        if (!analyticsData || typeof analyticsData !== "object") {
          console.warn(
            `⚠️ Invalid analytics data for ${arrayKey}:`,
            analyticsData
          );
          return fallback;
        }

        const result = analyticsData[arrayKey] || fallback;
        if (!Array.isArray(result)) {
          console.warn(`⚠️ ${arrayKey} is not an array:`, result);
          return fallback;
        }

        console.log(`✅ Extracted ${arrayKey}: ${result.length} items`);
        return result;
      } catch (error) {
        console.error(`❌ Error extracting ${arrayKey}:`, error);
        return fallback;
      }
    };

    const result = {
      indices,
      equityStocks,
      mcxStocks,
      // FIXED: Use analytics data with validation
      topGainers: getAnalyticsArray(topMovers, "gainers"),
      topLosers: getAnalyticsArray(topMovers, "losers"),
      gapUp: getAnalyticsArray(gapAnalysis, "gap_up"),
      gapDown: getAnalyticsArray(gapAnalysis, "gap_down"),
      intradayBoosters: getAnalyticsArray(intradayStocks, "all_candidates"),
      volumeLeaders: getAnalyticsArray(volumeAnalysis, "volume_leaders"),
      newHighs: getAnalyticsArray(recordMovers, "new_highs"),
      newLows: getAnalyticsArray(recordMovers, "new_lows"),
      breakouts: getAnalyticsArray(breakoutAnalysis, "breakouts"),
      breakdowns: getAnalyticsArray(breakoutAnalysis, "breakdowns"),
    };

    console.log("📊 Final processed data:", {
      indices: result.indices.length,
      equityStocks: result.equityStocks.length,
      topGainers: result.topGainers.length,
      topLosers: result.topLosers.length,
      gapUp: result.gapUp.length,
      gapDown: result.gapDown.length,
      intradayBoosters: result.intradayBoosters.length,
      volumeLeaders: result.volumeLeaders.length,
    });

    return result;
  }, [
    marketData,
    topMovers,
    gapAnalysis,
    intradayStocks,
    volumeAnalysis,
    recordMovers,
    breakoutAnalysis,
    heatmap,
  ]);

  // Section navigation
  const sections = [
    { id: "overview", label: "OVERVIEW", icon: "📊" },
    { id: "search", label: "SEARCH", icon: "🔍" },
    { id: "sectors", label: "SECTORS", icon: "🏢" },
    { id: "movers", label: "TOP MOVERS", icon: "🚀" },
    { id: "gaps", label: "GAP ANALYSIS", icon: "📈" },
    { id: "indices", label: "INDICES", icon: "🏛️" },
    { id: "mcx", label: "MCX & F&O", icon: "💰" },
    { id: "analytics", label: "ANALYTICS", icon: "🔍" },
  ];

  const toggleExpanded = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  // Get market status display
  const getMarketStatusDisplay = () => {
    switch (marketStatus) {
      case "normal_open":
      case "open":
        return {
          text: "MARKET OPEN",
          color: bloombergColors.positive,
          icon: "🟢",
        };
      case "pre_market":
        return {
          text: "PRE-MARKET",
          color: bloombergColors.warning,
          icon: "🟡",
        };
      case "after_market":
        return {
          text: "AFTER-MARKET",
          color: bloombergColors.info,
          icon: "🔵",
        };
      case "closed":
      default:
        return {
          text: "MARKET CLOSED",
          color: bloombergColors.negative,
          icon: "🔴",
        };
    }
  };

  const marketStatusDisplay = getMarketStatusDisplay();

  return (
    <div
      style={{
        backgroundColor: bloombergColors.background,
        color: bloombergColors.text,
        minHeight: "100vh",
        fontFamily: "'Courier New', monospace",
        fontSize: "14px",
        position: "relative",
      }}
    >
      {/* Debug Panel */}
      {showDebug && (
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
        />
      )}

      {/* Header Bar */}
      <div
        style={{
          background: `linear-gradient(90deg, ${bloombergColors.cardBackground}, ${bloombergColors.sectionBg})`,
          borderBottom: `2px solid ${bloombergColors.header}`,
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
              color: bloombergColors.header,
              margin: 0,
              fontSize: "24px",
              fontWeight: "bold",
              textShadow: "0 0 10px rgba(0, 180, 240, 0.5)",
            }}
          >
            📈 LIVE MARKET TERMINAL
          </h1>

          <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
            {/* Debug Toggle */}
            <button
              onClick={() => setShowDebug(!showDebug)}
              style={{
                background: showDebug
                  ? bloombergColors.positive
                  : "transparent",
                color: showDebug
                  ? bloombergColors.background
                  : bloombergColors.header,
                border: `1px solid ${bloombergColors.header}`,
                padding: "4px 8px",
                fontSize: "10px",
                fontWeight: "bold",
                cursor: "pointer",
                borderRadius: "3px",
                fontFamily: "'Courier New', monospace",
              }}
            >
              🔧 DEBUG
            </button>

            {/* Market Status */}
            <div
              style={{
                padding: "8px 15px",
                background: marketStatusDisplay.color,
                color: bloombergColors.background,
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

            {/* Connection Status */}
            <div
              style={{
                padding: "8px 15px",
                background: isConnected
                  ? bloombergColors.positive
                  : bloombergColors.negative,
                color: bloombergColors.background,
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

            {/* Enhanced Data Stats */}
            <div
              style={{
                fontSize: "12px",
                color: bloombergColors.text,
                opacity: 0.8,
                display: "flex",
                gap: "10px",
              }}
            >
              <span>📊 {totalStocks} stocks</span>
              <span>🏢 {sectors.length} sectors</span>
              <span>📈 {processedData.indices.length} indices</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              style={{
                background:
                  activeSection === section.id
                    ? bloombergColors.header
                    : "transparent",
                color:
                  activeSection === section.id
                    ? bloombergColors.background
                    : bloombergColors.text,
                border: `1px solid ${bloombergColors.header}`,
                padding: "8px 16px",
                fontSize: "12px",
                fontWeight: "bold",
                cursor: "pointer",
                borderRadius: "4px",
                transition: "all 0.3s ease",
                fontFamily: "'Courier New', monospace",
              }}
              onMouseEnter={(e) => {
                if (activeSection !== section.id) {
                  e.target.style.background = `${bloombergColors.header}40`;
                }
              }}
              onMouseLeave={(e) => {
                if (activeSection !== section.id) {
                  e.target.style.background = "transparent";
                }
              }}
            >
              {section.icon} {section.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ padding: "20px" }}>
        {/* Overview Section */}
        {activeSection === "overview" && (
          <div style={{ display: "grid", gap: "25px" }}>
            {/* Market Summary Stats */}
            {marketSummary && (
              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
                }}
              >
                <h2
                  style={{
                    color: bloombergColors.header,
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
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: bloombergColors.positive,
                        fontSize: "20px",
                        fontWeight: "bold",
                      }}
                    >
                      {marketSummary.advancing}
                    </div>
                    <div>ADVANCING</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: bloombergColors.negative,
                        fontSize: "20px",
                        fontWeight: "bold",
                      }}
                    >
                      {marketSummary.declining}
                    </div>
                    <div>DECLINING</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: bloombergColors.neutral,
                        fontSize: "20px",
                        fontWeight: "bold",
                      }}
                    >
                      {marketSummary.unchanged}
                    </div>
                    <div>UNCHANGED</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: bloombergColors.header,
                        fontSize: "20px",
                        fontWeight: "bold",
                      }}
                    >
                      {marketSummary.advanceDeclineRatio}
                    </div>
                    <div>A/D RATIO</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: bloombergColors.text,
                        fontSize: "20px",
                        fontWeight: "bold",
                      }}
                    >
                      {marketSummary.marketBreadth}%
                    </div>
                    <div>BREADTH</div>
                  </div>
                </div>
              </div>
            )}

            {/* Market Indices - Full Width */}
            <div
              style={{
                background: bloombergColors.sectionBg,
                borderRadius: "8px",
                padding: "20px",
                border: `1px solid ${bloombergColors.border}`,
                boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
              }}
            >
              <StocksList
                title="MARKET INDICES"
                data={processedData.indices}
                layoutType="cards"
                showVolume={false}
                isLoading={!isConnected}
                maxItems={12}
              />
            </div>

            {/* Top Movers Grid with Debug Info */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(500px, 1fr))",
                gap: "20px",
              }}
            >
              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
                }}
              >
                <StocksList
                  title={`🚀 TOP GAINERS (${processedData.topGainers.length})`}
                  data={processedData.topGainers}
                  layoutType="table"
                  showVolume={true}
                  showSector={true}
                  maxItems={8}
                  isLoading={!isConnected}
                />
              </div>

              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
                }}
              >
                <StocksList
                  title={`📉 TOP LOSERS (${processedData.topLosers.length})`}
                  data={processedData.topLosers}
                  layoutType="table"
                  showVolume={true}
                  showSector={true}
                  maxItems={8}
                  isLoading={!isConnected}
                />
              </div>
            </div>

            {/* Enhanced Analytics Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
                gap: "20px",
              }}
            >
              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
                }}
              >
                <StocksList
                  title={`⚡ INTRADAY BOOSTERS (${processedData.intradayBoosters.length})`}
                  data={processedData.intradayBoosters}
                  layoutType="table"
                  showVolume={true}
                  maxItems={10}
                  isLoading={!isConnected}
                />
              </div>

              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                  boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
                }}
              >
                <StocksList
                  title={`📊 VOLUME LEADERS (${processedData.volumeLeaders.length})`}
                  data={processedData.volumeLeaders}
                  layoutType="table"
                  showVolume={true}
                  maxItems={10}
                  isLoading={!isConnected}
                />
              </div>
            </div>
          </div>
        )}

        {/* Search Section */}
        {activeSection === "search" && (
          <div style={{ display: "grid", gap: "25px" }}>
            <div
              style={{
                background: bloombergColors.sectionBg,
                borderRadius: "8px",
                padding: "20px",
                border: `1px solid ${bloombergColors.border}`,
              }}
            >
              <h2
                style={{
                  color: bloombergColors.header,
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
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px",
                  backgroundColor: bloombergColors.cardBackground,
                  border: `1px solid ${bloombergColors.border}`,
                  borderRadius: "4px",
                  color: bloombergColors.text,
                  fontSize: "16px",
                  fontFamily: "'Courier New', monospace",
                }}
              />
            </div>

            {searchResults.length > 0 && (
              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                }}
              >
                <StocksList
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
        )}

        {/* Top Movers Section with Enhanced Display */}
        {activeSection === "movers" && (
          <div style={{ display: "grid", gap: "25px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "20px",
              }}
            >
              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                  position: "relative",
                }}
              >
                <button
                  onClick={() => toggleExpanded("gainers")}
                  style={{
                    position: "absolute",
                    top: "15px",
                    right: "15px",
                    background: "transparent",
                    border: `1px solid ${bloombergColors.header}`,
                    color: bloombergColors.header,
                    padding: "5px 10px",
                    fontSize: "12px",
                    cursor: "pointer",
                    borderRadius: "4px",
                  }}
                >
                  {expandedSection === "gainers" ? "COMPACT" : "EXPAND"}
                </button>

                <StocksList
                  title={`🚀 TOP GAINERS (${processedData.topGainers.length})`}
                  data={processedData.topGainers}
                  layoutType="table"
                  showVolume={true}
                  showSector={true}
                  maxItems={expandedSection === "gainers" ? 50 : 15}
                  isLoading={!isConnected}
                />
              </div>

              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                  position: "relative",
                }}
              >
                <button
                  onClick={() => toggleExpanded("losers")}
                  style={{
                    position: "absolute",
                    top: "15px",
                    right: "15px",
                    background: "transparent",
                    border: `1px solid ${bloombergColors.header}`,
                    color: bloombergColors.header,
                    padding: "5px 10px",
                    fontSize: "12px",
                    cursor: "pointer",
                    borderRadius: "4px",
                  }}
                >
                  {expandedSection === "losers" ? "COMPACT" : "EXPAND"}
                </button>

                <StocksList
                  title={`📉 TOP LOSERS (${processedData.topLosers.length})`}
                  data={processedData.topLosers}
                  layoutType="table"
                  showVolume={true}
                  showSector={true}
                  maxItems={expandedSection === "losers" ? 50 : 15}
                  isLoading={!isConnected}
                />
              </div>
            </div>

            {/* Volume Leaders */}
            <div
              style={{
                background: bloombergColors.sectionBg,
                borderRadius: "8px",
                padding: "20px",
                border: `1px solid ${bloombergColors.border}`,
              }}
            >
              <StocksList
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
        )}

        {/* Gap Analysis Section */}
        {activeSection === "gaps" && (
          <div style={{ display: "grid", gap: "25px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "20px",
              }}
            >
              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                }}
              >
                <StocksList
                  title={`📈 GAP UP (${processedData.gapUp.length})`}
                  data={processedData.gapUp}
                  layoutType="table"
                  showVolume={true}
                  showSector={true}
                  maxItems={20}
                  isLoading={!isConnected}
                />
              </div>

              <div
                style={{
                  background: bloombergColors.sectionBg,
                  borderRadius: "8px",
                  padding: "20px",
                  border: `1px solid ${bloombergColors.border}`,
                }}
              >
                <StocksList
                  title={`📉 GAP DOWN (${processedData.gapDown.length})`}
                  data={processedData.gapDown}
                  layoutType="table"
                  showVolume={true}
                  showSector={true}
                  maxItems={20}
                  isLoading={!isConnected}
                />
              </div>
            </div>
          </div>
        )}

        {/* Add other sections as needed... */}
      </div>

      {/* Enhanced Footer Status Bar */}
      <div
        style={{
          background: bloombergColors.cardBackground,
          borderTop: `1px solid ${bloombergColors.border}`,
          padding: "15px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "12px",
          color: bloombergColors.text,
          position: "sticky",
          bottom: 0,
        }}
      >
        <div>
          🔴 LIVE MARKET DATA | {totalStocks} INSTRUMENTS TRACKED |{" "}
          {sectors.length} SECTORS | GAINERS: {processedData.topGainers.length}{" "}
          | LOSERS: {processedData.topLosers.length}
        </div>
        <div>
          {new Date().toLocaleString()} | DATA:{" "}
          {isConnected ? "LIVE" : "OFFLINE"}
          {marketSummary && (
            <span style={{ marginLeft: "10px" }}>
              | A/D: {marketSummary.advanceDeclineRatio} | BREADTH:{" "}
              {marketSummary.marketBreadth}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
