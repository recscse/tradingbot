// hooks/useUnifiedMarketData.js
/**
 * FIXED: WebSocket connection and data processing issues
 */

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { createContext, useContext } from "react";

const WEBSOCKET_URL = process.env.REACT_APP_WS_URL
  ? `${process.env.REACT_APP_WS_URL}/ws/unified`
  : "ws://localhost:8000/ws/unified";

const RECONNECT_INTERVALS = [1000, 2000, 4000, 8000, 16000];

export const useUnifiedMarketData = () => {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");

  // Market data state
  const [marketData, setMarketData] = useState({});
  const [marketStatus, setMarketStatus] = useState("loading");

  // Analytics state
  const [topMovers, setTopMovers] = useState({ gainers: [], losers: [] });
  const [gapAnalysis, setGapAnalysis] = useState({ gap_up: [], gap_down: [] });
  const [breakoutAnalysis, setBreakoutAnalysis] = useState({
    breakouts: [],
    breakdowns: [],
  });
  const [marketSentiment, setMarketSentiment] = useState({
    sentiment: "neutral",
    confidence: 0,
  });
  const [heatmap, setHeatmap] = useState({ sectors: [] });
  const [volumeAnalysis, setVolumeAnalysis] = useState({ volume_leaders: [] });
  const [intradayStocks, setIntradayStocks] = useState({ all_candidates: [] });
  const [recordMovers, setRecordMovers] = useState({
    new_highs: [],
    new_lows: [],
  });

  // Refs for stable references
  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef(null);
  const pingInterval = useRef(null);
  const [lastUpdate, setLastUpdate] = useState(Date.now());
  const connectionReady = useRef(false); // FIXED: Track connection readiness

  // FIXED: Safe message sending with queue for connection delay
  const messageQueue = useRef([]);

  const safeSend = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN && connectionReady.current) {
      ws.current.send(JSON.stringify(message));
      return true;
    } else {
      // Queue message if not connected
      messageQueue.current.push(message);
      return false;
    }
  }, []);

  // FIXED: Process queued messages when connection is ready
  const processMessageQueue = useCallback(() => {
    while (
      messageQueue.current.length > 0 &&
      ws.current?.readyState === WebSocket.OPEN
    ) {
      const message = messageQueue.current.shift();
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  // FIXED: Enhanced message handler with better error handling
  // FIXED: Enhanced message handler with better error handling
  const handleMessage = useCallback(
    (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastUpdate(Date.now());

        // Use requestIdleCallback for non-critical updates
        const updateState = () => {
          console.log("📨 Received message type:", data.type);

          // CRITICAL FIX: Handle dashboard_data with detailed logging
          if (data.type === "dashboard_data") {
            console.log("📊 Processing dashboard data directly");
            console.log("📊 Dashboard data keys:", Object.keys(data));

            // FIXED: Extract and validate each analytics component
            const extractAndSet = (key, setter, fallback = {}) => {
              try {
                const value = data[key];
                if (value && typeof value === "object") {
                  console.log(`✅ Setting ${key}:`, value);
                  setter(value);
                  return true;
                } else {
                  console.warn(`⚠️ ${key} is missing or invalid:`, value);
                  setter(fallback);
                  return false;
                }
              } catch (error) {
                console.error(`❌ Error setting ${key}:`, error);
                setter(fallback);
                return false;
              }
            };

            // Extract all analytics with validation
            extractAndSet("top_movers", setTopMovers, {
              gainers: [],
              losers: [],
            });
            extractAndSet("gap_analysis", setGapAnalysis, {
              gap_up: [],
              gap_down: [],
            });
            extractAndSet("breakout_analysis", setBreakoutAnalysis, {
              breakouts: [],
              breakdowns: [],
            });
            extractAndSet("market_sentiment", setMarketSentiment, {
              sentiment: "neutral",
              confidence: 0,
            });
            extractAndSet("sector_heatmap", setHeatmap, { sectors: [] });
            extractAndSet("volume_analysis", setVolumeAnalysis, {
              volume_leaders: [],
            });

            // Handle intraday data (try both possible keys)
            const intradayData =
              data.intraday_highlights || data.intraday_stocks;
            if (intradayData) {
              console.log("✅ Setting intraday stocks:", intradayData);
              setIntradayStocks(intradayData);
            } else {
              console.warn("⚠️ No intraday data found");
              setIntradayStocks({ all_candidates: [] });
            }

            extractAndSet("record_movers", setRecordMovers, {
              new_highs: [],
              new_lows: [],
            });

            return;
          }

          // CRITICAL FIX: Handle initial_data package
          if (data.type === "initial_data" && data.data) {
            console.log("📊 Processing initial data package");
            console.log("📊 Available features:", Object.keys(data.data));

            // FIXED: Process nested data structure
            const analyticsData = data.data;

            // Extract each component with better error handling
            if (analyticsData.top_movers) {
              console.log(
                "✅ Setting top movers from initial data:",
                analyticsData.top_movers
              );
              setTopMovers((prev) => ({
                gainers: analyticsData.top_movers.gainers || prev.gainers || [],
                losers: analyticsData.top_movers.losers || prev.losers || [],
              }));
            }

            if (analyticsData.gap_analysis) {
              console.log(
                "✅ Setting gap analysis from initial data:",
                analyticsData.gap_analysis
              );
              setGapAnalysis((prev) => ({
                gap_up: analyticsData.gap_analysis.gap_up || prev.gap_up || [],
                gap_down:
                  analyticsData.gap_analysis.gap_down || prev.gap_down || [],
              }));
            }

            if (analyticsData.breakout_analysis) {
              setBreakoutAnalysis((prev) => ({
                breakouts:
                  analyticsData.breakout_analysis.breakouts ||
                  prev.breakouts ||
                  [],
                breakdowns:
                  analyticsData.breakout_analysis.breakdowns ||
                  prev.breakdowns ||
                  [],
              }));
            }

            if (analyticsData.market_sentiment) {
              setMarketSentiment((prev) => ({
                ...prev,
                ...analyticsData.market_sentiment,
              }));
            }

            if (analyticsData.sector_heatmap) {
              console.log(
                "✅ Setting sector heatmap from initial data:",
                analyticsData.sector_heatmap
              );
              setHeatmap(analyticsData.sector_heatmap);
            }

            if (analyticsData.volume_analysis) {
              setVolumeAnalysis((prev) => ({
                volume_leaders:
                  analyticsData.volume_analysis.volume_leaders ||
                  prev.volume_leaders ||
                  [],
              }));
            }

            // Handle intraday data
            const intradayData =
              analyticsData.intraday_highlights ||
              analyticsData.intraday_stocks;
            if (intradayData) {
              setIntradayStocks((prev) => ({
                high_momentum: intradayData.high_momentum || [],
                high_volume: intradayData.high_volume || [],
                all_candidates: intradayData.all_candidates || [
                  ...(intradayData.high_momentum || []),
                  ...(intradayData.high_volume || []),
                ],
              }));
            }

            if (analyticsData.record_movers) {
              setRecordMovers((prev) => ({
                new_highs:
                  analyticsData.record_movers.new_highs || prev.new_highs || [],
                new_lows:
                  analyticsData.record_movers.new_lows || prev.new_lows || [],
              }));
            }

            return;
          }

          // CRITICAL FIX: Handle live_prices_enriched for market data
          if (data.type === "live_prices_enriched" && data.data) {
            console.log(
              "📊 Processing enriched market data:",
              Object.keys(data.data).length,
              "instruments"
            );

            // FIXED: Validate and process market data
            if (data.data && typeof data.data === "object") {
              const validInstruments = Object.entries(data.data).filter(
                ([key, value]) => {
                  return (
                    value &&
                    typeof value === "object" &&
                    value.symbol &&
                    (value.ltp || value.last_price)
                  );
                }
              );

              console.log(
                `📊 Valid instruments: ${validInstruments.length}/${
                  Object.keys(data.data).length
                }`
              );

              if (validInstruments.length > 0) {
                const processedData = Object.fromEntries(validInstruments);
                setMarketData((prev) => ({ ...prev, ...processedData }));
              } else {
                console.warn("⚠️ No valid instruments found in enriched data");
              }
            } else {
              console.warn("⚠️ Invalid enriched data structure:", data);
            }
            return;
          }

          // Handle individual analytics updates with improved validation
          const updateHandlers = {
            top_movers_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating top movers:", updateData);
                setTopMovers((prev) => ({
                  gainers: updateData.gainers || prev.gainers || [],
                  losers: updateData.losers || prev.losers || [],
                }));
              }
            },

            gap_analysis_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating gap analysis:", updateData);
                setGapAnalysis((prev) => ({
                  gap_up: updateData.gap_up || prev.gap_up || [],
                  gap_down: updateData.gap_down || prev.gap_down || [],
                }));
              }
            },

            breakout_analysis_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating breakout analysis:", updateData);
                setBreakoutAnalysis((prev) => ({
                  breakouts: updateData.breakouts || prev.breakouts || [],
                  breakdowns: updateData.breakdowns || prev.breakdowns || [],
                }));
              }
            },

            market_sentiment_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating market sentiment:", updateData);
                setMarketSentiment((prev) => ({
                  sentiment:
                    updateData.sentiment || prev.sentiment || "neutral",
                  confidence:
                    updateData.sentiment_score ||
                    updateData.confidence ||
                    prev.confidence ||
                    0,
                  advancing: updateData.advancing || prev.advancing,
                  declining: updateData.declining || prev.declining,
                  total: updateData.total || prev.total,
                  sentiment_score:
                    updateData.sentiment_score || prev.sentiment_score,
                }));
              }
            },

            sector_heatmap_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating sector heatmap:", updateData);
                setHeatmap(updateData);
              }
            },

            heatmap_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating heatmap:", updateData);
                setHeatmap(updateData);
              }
            },

            volume_analysis_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating volume analysis:", updateData);
                setVolumeAnalysis((prev) => ({
                  volume_leaders:
                    updateData.volume_leaders || prev.volume_leaders || [],
                }));
              }
            },

            intraday_stocks_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating intraday stocks:", updateData);
                setIntradayStocks((prev) => ({
                  high_momentum: updateData.high_momentum || [],
                  high_volume: updateData.high_volume || [],
                  all_candidates: updateData.all_candidates || [
                    ...(updateData.high_momentum || []),
                    ...(updateData.high_volume || []),
                  ],
                }));
              }
            },

            intraday_highlights_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating intraday highlights:", updateData);
                setIntradayStocks((prev) => ({
                  high_momentum: updateData.high_momentum || [],
                  high_volume: updateData.high_volume || [],
                  all_candidates: updateData.all_candidates || [
                    ...(updateData.high_momentum || []),
                    ...(updateData.high_volume || []),
                  ],
                }));
              }
            },

            record_movers_update: (updateData) => {
              if (updateData && typeof updateData === "object") {
                console.log("📊 Updating record movers:", updateData);
                setRecordMovers((prev) => ({
                  new_highs: updateData.new_highs || prev.new_highs || [],
                  new_lows: updateData.new_lows || prev.new_lows || [],
                }));
              }
            },
          };

          // Handle standard message types
          switch (data.type) {
            case "connection_established":
              console.log("🔌 Connected to unified WebSocket:", data.client_id);
              connectionReady.current = true;
              processMessageQueue();
              break;

            case "subscription_confirmed":
              console.log("✅ Subscription confirmed for events:", data.events);
              break;

            case "price_update":
              if (data.data && typeof data.data === "object") {
                setMarketData((prev) => ({ ...prev, ...data.data }));
              }
              break;

            case "market_status_update":
              setMarketStatus(data.data?.status || "unknown");
              break;

            case "pong":
              // Handle heartbeat response
              break;

            case "error":
              console.error("❌ WebSocket error:", data.message);
              break;

            default:
              // Check if it's an analytics update
              const handler = updateHandlers[data.type];
              if (handler && data.data) {
                handler(data.data);
              } else {
                console.log("📨 Unknown message:", data.type, data);
              }
          }
        };

        // FIXED: Better scheduling for updates
        if (window.requestIdleCallback) {
          window.requestIdleCallback(updateState, { timeout: 1000 });
        } else {
          setTimeout(updateState, 0);
        }
      } catch (error) {
        console.error("❌ Error parsing WebSocket message:", error, event.data);
      }
    },
    [processMessageQueue]
  );

  // FIXED: Enhanced connection with better data requests
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    console.log("🔌 Connecting to unified WebSocket...");
    setConnectionStatus("connecting");
    connectionReady.current = false;

    try {
      ws.current = new WebSocket(WEBSOCKET_URL);

      ws.current.onopen = () => {
        console.log("✅ Unified WebSocket connected");
        setIsConnected(true);
        setConnectionStatus("connected");
        reconnectAttempts.current = 0;

        // FIXED: Enhanced connection setup
        setTimeout(() => {
          connectionReady.current = true;

          // 1. Subscribe to all analytics events
          console.log("📡 Subscribing to analytics events...");
          safeSend({
            type: "subscribe",
            events: [
              "price_update",
              "live_prices_enriched",
              "market_status_update",
              "top_movers_update",
              "gap_analysis_update",
              "breakout_analysis_update",
              "market_sentiment_update",
              "sector_heatmap_update",
              "heatmap_update",
              "volume_analysis_update",
              "intraday_stocks_update",
              "intraday_highlights_update",
              "record_movers_update",
              "all", // Subscribe to all events
            ],
          });

          // 2. Request dashboard data first
          console.log("📊 Requesting complete dashboard data...");
          safeSend({
            type: "get_dashboard_data",
          });

          // 3. Request live market data
          console.log("📊 Requesting enriched live prices...");
          safeSend({
            type: "get_live_prices",
          });

          // Process any queued messages
          processMessageQueue();
        }, 500); // Increased delay for stability

        // Setup heartbeat
        pingInterval.current = setInterval(() => {
          safeSend({ type: "ping" });
        }, 30000);
      };

      ws.current.onmessage = handleMessage;

      ws.current.onclose = (event) => {
        console.log("🔌 WebSocket disconnected:", event.code);
        setIsConnected(false);
        setConnectionStatus("disconnected");
        connectionReady.current = false;

        if (pingInterval.current) {
          clearInterval(pingInterval.current);
          pingInterval.current = null;
        }

        // Reconnect with exponential backoff
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < RECONNECT_INTERVALS.length
        ) {
          const delay = RECONNECT_INTERVALS[reconnectAttempts.current] || 16000;
          reconnectAttempts.current++;

          console.log(
            `🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`
          );
          setConnectionStatus("reconnecting");

          reconnectTimeout.current = setTimeout(connect, delay);
        } else {
          setConnectionStatus("failed");
        }
      };

      ws.current.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        setConnectionStatus("error");
        connectionReady.current = false;
      };
    } catch (error) {
      console.error("❌ WebSocket connection error:", error);
      setConnectionStatus("error");
    }
  }, [handleMessage, safeSend, processMessageQueue]);

  const logAnalyticsData = useCallback(() => {
    console.log("📊 Current Analytics State:");
    console.log("- Top Movers:", {
      gainers: topMovers.gainers?.length || 0,
      losers: topMovers.losers?.length || 0,
    });
    console.log("- Gap Analysis:", {
      gap_up: gapAnalysis.gap_up?.length || 0,
      gap_down: gapAnalysis.gap_down?.length || 0,
    });
    console.log("- Heatmap:", {
      sectors: heatmap.sectors?.length || 0,
    });
    console.log("- Volume Analysis:", {
      volume_leaders: volumeAnalysis.volume_leaders?.length || 0,
    });
    console.log("- Intraday Stocks:", {
      all_candidates: intradayStocks.all_candidates?.length || 0,
    });
    console.log("- Record Movers:", {
      new_highs: recordMovers.new_highs?.length || 0,
      new_lows: recordMovers.new_lows?.length || 0,
    });
  }, [
    topMovers,
    gapAnalysis,
    heatmap,
    volumeAnalysis,
    intradayStocks,
    recordMovers,
  ]);

  useEffect(() => {
    logAnalyticsData();
  }, [
    topMovers,
    gapAnalysis,
    heatmap,
    volumeAnalysis,
    intradayStocks,
    recordMovers,
    logAnalyticsData,
  ]);

  // FIXED: Improved market data processing with null safety
  const processedMarketData = useMemo(() => {
    const processed = {};

    console.log(
      "🔍 Processing market data:",
      Object.keys(marketData).length,
      "instruments"
    );

    Object.entries(marketData).forEach(([key, data]) => {
      // FIXED: Better validation and data structure handling
      if (
        data &&
        typeof data === "object" &&
        data.symbol &&
        (typeof data.ltp === "number" || typeof data.last_price === "number")
      ) {
        const ltp = data.ltp || data.last_price;

        processed[key] = {
          // Core identifiers
          instrument_key: data.instrument_key || key,
          symbol: data.symbol,
          name: data.name || data.symbol,
          trading_symbol: data.trading_symbol || data.symbol,
          exchange: data.exchange || "NSE",
          sector: data.sector || "OTHER",

          // Price data with fallbacks
          ltp: Number(ltp),
          cp: Number(data.cp || data.previous_close || 0),
          change: Number(data.change || 0),
          change_percent: Number(data.change_percent || 0),

          // Trading data with fallbacks
          volume: Number(data.volume || 0),
          high: Number(data.high || ltp),
          low: Number(data.low || ltp),
          open: Number(data.open || ltp),

          // Metadata
          timestamp: data.timestamp || Date.now(),
          last_updated: data.last_updated,
          trend: data.trend || "neutral",
          volatility: data.volatility || "normal",
        };
      } else {
        // Log problematic data for debugging
        if (data && typeof data === "object") {
          console.warn("⚠️ Skipping incomplete data for", key, ":", {
            hasSymbol: !!data.symbol,
            hasLTP: !!(data.ltp || data.last_price),
            dataKeys: Object.keys(data),
          });
        }
      }
    });

    console.log(
      "✅ Processed market data:",
      Object.keys(processed).length,
      "valid instruments"
    );
    return processed;
  }, [marketData]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    reconnectAttempts.current = 0;
    connect();
  }, [connect]);

  // Send message to WebSocket
  const sendMessage = useCallback(
    (message) => {
      return safeSend(message);
    },
    [safeSend]
  );

  // ✅ NEW: Sector-based grouping
  const getStocksBySector = useCallback(() => {
    const sectorGroups = {};

    Object.values(processedMarketData).forEach((stock) => {
      const sector = stock.sector || "OTHER";
      if (!sectorGroups[sector]) {
        sectorGroups[sector] = [];
      }
      sectorGroups[sector].push(stock);
    });

    // Sort each sector by performance
    Object.keys(sectorGroups).forEach((sector) => {
      sectorGroups[sector].sort(
        (a, b) => (b.change_percent || 0) - (a.change_percent || 0)
      );
    });

    return sectorGroups;
  }, [processedMarketData]);

  // ✅ NEW: Search stocks by name or symbol
  const searchStocks = useCallback(
    (query) => {
      if (!query) return [];

      const upperQuery = query.toUpperCase();
      return Object.values(processedMarketData)
        .filter(
          (stock) =>
            stock.symbol.includes(upperQuery) ||
            stock.name.toUpperCase().includes(upperQuery)
        )
        .slice(0, 10); // Limit to 10 results
    },
    [processedMarketData]
  );

  // ✅ NEW: Get market summary
  const getMarketSummary = useCallback(() => {
    const stocks = Object.values(processedMarketData);

    if (stocks.length === 0) return null;

    const advancing = stocks.filter((s) => s.change_percent > 0).length;
    const declining = stocks.filter((s) => s.change_percent < 0).length;
    const unchanged = stocks.length - advancing - declining;

    return {
      total: stocks.length,
      advancing,
      declining,
      unchanged,
      advanceDeclineRatio:
        declining > 0 ? (advancing / declining).toFixed(2) : "∞",
      marketBreadth: (((advancing - declining) / stocks.length) * 100).toFixed(
        1
      ),
    };
  }, [processedMarketData]);

  // Get specific stock data
  const getStockData = useCallback(
    (symbol) => {
      if (!symbol) return null;

      const upperSymbol = symbol.toUpperCase();
      const keys = Object.keys(processedMarketData);
      const stockKey = keys.find(
        (key) =>
          key.includes(upperSymbol) ||
          key.endsWith(`|${upperSymbol}`) ||
          key.includes(`|${upperSymbol}|`)
      );
      return stockKey ? processedMarketData[stockKey] : null;
    },
    [processedMarketData]
  );

  // Get live prices for symbols
  const getLivePrices = useCallback(
    (symbols) => {
      if (!Array.isArray(symbols)) return {};

      const prices = {};
      symbols.forEach((symbol) => {
        const data = getStockData(symbol);
        if (data) {
          prices[symbol] = {
            ltp: data.ltp || 0,
            change_percent: data.change_percent || 0,
            volume: data.volume || 0,
          };
        }
      });
      return prices;
    },
    [getStockData]
  );

  // Connection status check
  const isStale = Date.now() - lastUpdate.current > 120000;

  // Initialize connection
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
      }
      if (ws.current) {
        connectionReady.current = false;
        ws.current.close(1000);
      }
    };
  }, [connect]);

  // FIXED: Clear message queue on disconnect
  useEffect(() => {
    if (!isConnected) {
      messageQueue.current = [];
    }
  }, [isConnected]);

  return {
    // Connection state
    isConnected,
    connectionStatus,
    isStale,
    reconnect,
    // Market data (✅ ENHANCED)
    marketData: processedMarketData,
    marketStatus,
    totalStocks: Object.keys(processedMarketData).length, // ✅ NEW
    sectors: Object.keys(getStocksBySector()), // ✅ NEW
    // Analytics data
    topMovers,
    gapAnalysis,
    breakoutAnalysis,
    marketSentiment,
    heatmap,
    volumeAnalysis,
    intradayStocks,
    recordMovers,
    // Utility functions (✅ ENHANCED)
    sendMessage,
    getStockData,
    getLivePrices,
    getStocksBySector, // ✅ NEW: Group by sector
    searchStocks, // ✅ NEW: Search functionality
    getMarketSummary, // ✅ NEW: Market overview
    // Legacy compatibility
    ltps: processedMarketData,
    groupedStocks: getStocksBySector(), // ✅ NOW POPULATED
    tokenExpired: false,
    resetTokenExpired: () => {},
  };
};

// Context wrapper for existing code compatibility
const UnifiedMarketContext = createContext();

export const UnifiedMarketProvider = ({ children }) => {
  const marketData = useUnifiedMarketData();

  return (
    <UnifiedMarketContext.Provider value={marketData}>
      {children}
    </UnifiedMarketContext.Provider>
  );
};

export const useMarket = () => {
  const context = useContext(UnifiedMarketContext);
  if (!context) {
    throw new Error("useMarket must be used within UnifiedMarketProvider");
  }
  return context;
};

export default useUnifiedMarketData;
