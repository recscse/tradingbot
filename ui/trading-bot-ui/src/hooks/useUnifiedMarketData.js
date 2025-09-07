// hooks/useUnifiedMarketData.js - OPTIMIZED WITH ZUSTAND FOR REAL-TIME PERFORMANCE

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { createContext, useContext } from "react";
import useMarketStore from '../store/marketStore';

// Enhanced logging utility for performance
const DEBUG_ENABLED = process.env.NODE_ENV === "development";
const DEBUG_VERBOSE = process.env.REACT_APP_DEBUG_WEBSOCKET === "true";

const debugLog = (level, message, data) => {
  if (!DEBUG_ENABLED) return;

  const timestamp = new Date().toISOString().split("T")[1].split(".")[0];
  const prefix = `[${timestamp}]`;

  switch (level) {
    case "info":
      if (DEBUG_VERBOSE) console.log(`${prefix} ℹ️ ${message}`, data || "");
      break;
    case "warn":
      console.warn(`${prefix} ⚠️ ${message}`, data || "");
      break;
    case "error":
      console.error(`${prefix} ❌ ${message}`, data || "");
      break;
    case "debug":
      if (DEBUG_VERBOSE) console.debug(`${prefix} 🐛 ${message}`, data || "");
      break;
    default:
      if (DEBUG_VERBOSE) console.log(`${prefix} ${message}`, data || "");
  }
};

const WEBSOCKET_URL = process.env.REACT_APP_API_URL
  ? `${process.env.REACT_APP_API_URL}/ws/unified`.replace('http', 'ws')
  : "ws://localhost:8000/ws/unified";

const RECONNECT_INTERVALS = [1000, 2000, 4000, 8000, 16000, 32000];
const PING_INTERVAL = 30000;
const STALE_THRESHOLD = 120000; // 2 minutes
const MAX_CACHE_SIZE = 10000; // Maximum cached instruments
const MAX_MESSAGE_QUEUE = 100; // Maximum queued messages

// Data validation utilities
const validatePrice = (price) => {
  return typeof price === "number" && price >= 0 && price < 1000000;
};

const validatePercentage = (percent) => {
  return typeof percent === "number" && percent >= -100 && percent <= 1000;
};

const validateVolume = (volume) => {
  return typeof volume === "number" && volume >= 0;
};

const validateInstrumentData = (data) => {
  if (!data || typeof data !== "object") return false;

  // Basic structure validation
  if (data.last_price !== undefined && !validatePrice(data.last_price))
    return false;
  if (
    data.change_percent !== undefined &&
    !validatePercentage(data.change_percent)
  )
    return false;
  if (data.volume !== undefined && !validateVolume(data.volume)) return false;

  return true;
};

const sanitizeInstrumentData = (data) => {
  if (!validateInstrumentData(data)) return null;

  const sanitized = { ...data };

  // Ensure numeric fields are properly typed
  if (sanitized.last_price !== undefined) {
    sanitized.last_price = Math.max(0, Number(sanitized.last_price) || 0);
  }
  if (sanitized.change_percent !== undefined) {
    sanitized.change_percent = Math.max(
      -100,
      Math.min(1000, Number(sanitized.change_percent) || 0)
    );
  }
  if (sanitized.volume !== undefined) {
    sanitized.volume = Math.max(0, Number(sanitized.volume) || 0);
  }

  // Add timestamp if missing
  if (!sanitized.timestamp) {
    sanitized.timestamp = Date.now();
  }

  return sanitized;
};
// Memory-aware cache with size limits
const createBoundedCache = (maxSize = MAX_CACHE_SIZE) => {
  const cache = new Map();
  const accessTimes = new Map();

  const cleanup = () => {
    if (cache.size <= maxSize) return;

    // Remove oldest 20% of entries based on access time
    const entries = Array.from(accessTimes.entries())
      .sort((a, b) => a[1] - b[1])
      .slice(0, Math.floor(maxSize * 0.2));

    entries.forEach(([key]) => {
      cache.delete(key);
      accessTimes.delete(key);
    });

    debugLog(
      "debug",
      `Cache cleanup: removed ${entries.length} entries, size now: ${cache.size}`
    );
  };

  return {
    get: (key) => {
      const value = cache.get(key);
      if (value !== undefined) {
        accessTimes.set(key, Date.now());
      }
      return value;
    },
    set: (key, value) => {
      cache.set(key, value);
      accessTimes.set(key, Date.now());
      if (cache.size > maxSize) {
        cleanup();
      }
    },
    has: (key) => cache.has(key),
    delete: (key) => {
      cache.delete(key);
      accessTimes.delete(key);
    },
    clear: () => {
      cache.clear();
      accessTimes.clear();
    },
    size: () => cache.size,
  };
};

export const useUnifiedMarketData = () => {
  // Connection state with optimized initial values
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [lastUpdate, setLastUpdate] = useState(Date.now());
  const [indicesData, setIndicesData] = useState({
    indices: [],
    major_indices: [],
    sector_indices: [],
    summary: null,
  });

  // Market data state with memory management
  const marketDataCache = useRef(createBoundedCache(MAX_CACHE_SIZE));
  const [marketData, setMarketData] = useState({});
  const [marketStatus, setMarketStatus] = useState("loading");

  // Analytics state - using useState for proper reactivity
  const [topMovers, setTopMovers] = useState({
    gainers: [],
    losers: [],
    analysis: null,
  });
  const [gapAnalysis, setGapAnalysis] = useState({
    gap_up: [],
    gap_down: [],
    summary: null,
  });
  const [breakoutAnalysis, setBreakoutAnalysis] = useState({
    breakouts: [],
    breakdowns: [],
    summary: null,
  });
  const [marketSentiment, setMarketSentiment] = useState({
    sentiment: "neutral",
    confidence: 0,
    sentiment_score: 0,
    market_breadth: null,
    interpretation: null,
  });
  const [heatmap, setHeatmap] = useState({ sectors: [], summary: null });
  const [volumeAnalysis, setVolumeAnalysis] = useState({
    volume_leaders: [],
    unusual_volume: [],
    volume_statistics: null,
    sector_volumes: null,
  });
  const [intradayStocks, setIntradayStocks] = useState({
    all_candidates: [],
    high_momentum: [],
    high_volume: [],
    fno_candidates: [],
    fno_momentum: [],
    fno_volume: [],
    summary: null,
  });
  const [recordMovers, setRecordMovers] = useState({
    new_highs: [],
    new_lows: [],
    summary: null,
  });

  // Connection management refs with cleanup tracking
  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef(null);
  const pingInterval = useRef(null);
  const connectionReady = useRef(false);
  const messageQueue = useRef([]);
  const subscriptionConfirmed = useRef(false);
  const cleanupFunctions = useRef([]);

  // Performance tracking with throttling
  const messageCount = useRef(0);
  const lastMessageTime = useRef(Date.now());
  const performanceMetrics = useRef({
    messagesPerSecond: 0,
    avgProcessingTime: 0,
    lastMetricsUpdate: Date.now(),
  });

  // Safe message sending with enhanced queue management
  const safeSend = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN && connectionReady.current) {
      try {
        ws.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        debugLog("error", "Error sending message", error);

        // Only queue if under limit
        if (messageQueue.current.length < MAX_MESSAGE_QUEUE) {
          messageQueue.current.push(message);
        } else {
          debugLog("warn", "Message queue full, dropping oldest messages");
          messageQueue.current = messageQueue.current.slice(
            -MAX_MESSAGE_QUEUE + 1
          );
          messageQueue.current.push(message);
        }
        return false;
      }
    } else {
      // Only queue if under limit
      if (messageQueue.current.length < MAX_MESSAGE_QUEUE) {
        messageQueue.current.push(message);
      }
      return false;
    }
  }, []);

  // Process queued messages when connection is ready
  const processMessageQueue = useCallback(() => {
    let processed = 0;
    const maxBatch = 10; // Limit batch size

    while (
      messageQueue.current.length > 0 &&
      ws.current?.readyState === WebSocket.OPEN &&
      processed < maxBatch
    ) {
      const message = messageQueue.current.shift();
      try {
        ws.current.send(JSON.stringify(message));
        processed++;
      } catch (error) {
        debugLog("error", "Error processing queued message", error);
        messageQueue.current.unshift(message); // Put it back
        break;
      }
    }
    if (processed > 0) {
      debugLog("debug", `Processed ${processed} queued messages`);
    }
  }, []);

  // Optimized message handler with validation and performance tracking
  const handleMessageRaw = useCallback(
    (event) => {
      const startTime = Date.now();

      try {
        const data = JSON.parse(event.data);

        // Basic validation
        if (!data || typeof data !== "object" || !data.type) {
          debugLog("warn", "Invalid message format received", data);
          return;
        }

        messageCount.current++;
        lastMessageTime.current = startTime;

        // Update performance metrics (throttled)
        const now = startTime;
        const timeSinceLastMetrics =
          now - performanceMetrics.current.lastMetricsUpdate;
        if (timeSinceLastMetrics > 5000) {
          // Update every 5 seconds
          performanceMetrics.current.messagesPerSecond =
            messageCount.current / (timeSinceLastMetrics / 1000);
          performanceMetrics.current.lastMetricsUpdate = now;

          debugLog(
            "debug",
            `WebSocket metrics: ${performanceMetrics.current.messagesPerSecond.toFixed(
              1
            )} msg/s, ` +
              `total: ${messageCount.current}, queue: ${messageQueue.current.length}`
          );
        }

        // Log important message types for debugging real-time data flow
        if (
          [
            "price_update",
            "dashboard_update",
            "intraday_stocks_update",
            "top_movers_update",
            "market_status_update",
          ].includes(data.type)
        ) {
          debugLog("debug", `Received ${data.type}`, {
            hasData: !!data.data,
            dataSize: data.data
              ? Array.isArray(data.data)
                ? data.data.length
                : Object.keys(data.data).length
              : 0,
          });
        }

        setLastUpdate(now);

        switch (data.type) {
          case "connection_established":
            debugLog("info", "Connected to unified WebSocket", data.client_id);
            connectionReady.current = true;
            subscriptionConfirmed.current = false;
            processMessageQueue();
            break;

          case "subscription_confirmed":
            debugLog(
              "info",
              "Subscription confirmed for events",
              data.events?.length || 0
            );
            subscriptionConfirmed.current = true;

            // Request initial data after subscription confirmation
            setTimeout(() => {
              safeSend({ type: "get_dashboard_data" });
              safeSend({ type: "get_live_prices" });
              safeSend({ type: "get_market_status" });
              safeSend({ type: "get_indices_data" });
            }, 50); // 🚀 ULTRA FAST: Reduced to 50ms for immediate data
            break;

          // 🚀 REAL-TIME PRICE UPDATE: Direct to Zustand store for maximum speed
          case "price_update":
            if (data.data) {
              // 🚀 ULTRA-FAST: Single price update directly to Zustand
              if (data.realtime && data.data.symbol) {
                // Real-time individual price update
                useMarketStore.getState().updatePrice(data.data);
                debugLog("debug", `🚀 Real-time price: ${data.data.symbol} = ${data.data.ltp}`);
              } else if (Array.isArray(data.data)) {
                // Array format - update each price
                data.data.forEach((item) => {
                  if (item && item.symbol) {
                    useMarketStore.getState().updatePrice(item);
                  }
                });
                debugLog("debug", `🚀 Batch price update: ${data.data.length} instruments`);
              } else if (typeof data.data === "object") {
                // Object format - batch update
                useMarketStore.getState().updatePrices(data.data);
                debugLog("debug", `🚀 Object price update: ${Object.keys(data.data).length} instruments`);
              }
              
              // Also update legacy marketData for backward compatibility (analytics)
              if (typeof data.data === "object" && !Array.isArray(data.data)) {
                const legacyUpdates = {};
                Object.entries(data.data).forEach(([key, item]) => {
                  if (item && typeof item === "object") {
                    legacyUpdates[key] = { ...item, timestamp: Date.now() };
                  }
                });
                if (Object.keys(legacyUpdates).length > 0) {
                  setMarketData((prev) => ({ ...prev, ...legacyUpdates }));
                }
              }
            }
            break;

          case "live_prices_enriched":
            if (data.data && typeof data.data === "object") {
              const enrichedData = {};
              let validCount = 0;

              Object.entries(data.data).forEach(([key, instrumentData]) => {
                const sanitized = sanitizeInstrumentData(instrumentData);
                if (sanitized) {
                  enrichedData[key] = sanitized;
                  marketDataCache.current.set(key, sanitized);
                  validCount++;
                }
              });

              if (validCount > 0) {
                setMarketData((prev) => ({ ...prev, ...enrichedData }));
                debugLog(
                  "debug",
                  `Live prices enriched: ${validCount} instruments updated`
                );
              }
            }
            break;

          case "indices_data_update":
            if (data.data) {
              console.log(
                "📈 Updating indices data:",
                data.data.indices?.length || 0,
                "total indices,",
                data.data.major_indices?.length || 0,
                "major indices"
              );
              setIndicesData({
                indices: data.data.indices || [],
                major_indices: data.data.major_indices || [],
                sector_indices: data.data.sector_indices || [],
                summary: data.data.summary || null,
              });
            }
            break;

          // ⚡ ZERO-DELAY: Analytics updates with instant processing
          case "top_movers_update":
            if (data.data) {
              debugLog("debug", `⚡ ZERO-DELAY top movers: ${data.data.gainers?.length || 0} gainers, ${data.data.losers?.length || 0} losers`);

              // ⚡ INSTANT UPDATE: Direct state assignment for maximum speed
              setTopMovers({
                gainers: data.data.gainers || [],
                losers: data.data.losers || [],
                analysis: data.data.analysis || null,
              });
            }
            break;

          case "gap_analysis_update":
            if (data.data) {
              console.log(
                "📈 Updating gap analysis:",
                data.data.gap_up?.length || 0,
                "gap up,",
                data.data.gap_down?.length || 0,
                "gap down"
              );
              setGapAnalysis({
                gap_up: data.data.gap_up || [],
                gap_down: data.data.gap_down || [],
                summary: data.data.summary || null,
              });
            }
            break;

          case "breakout_analysis_update":
          case "enhanced_breakout_update":
          case "breakout_update":
            if (data.data) {
              console.log(
                "🚀 Updating enhanced breakout analysis:",
                data.data.breakouts?.length || 0,
                "total breakouts,",
                data.data.recent_breakouts?.length || 0,
                "recent,",
                data.data.total_today || 0,
                "today"
              );
              
              // Handle both legacy and enhanced breakout data formats
              const enhancedData = {
                // Legacy format support
                breakouts: data.data.breakouts || [],
                breakdowns: data.data.breakdowns || [],
                summary: data.data.summary || {},
                
                // Enhanced format support
                recent_breakouts: data.data.recent_breakouts || [],
                top_breakouts: data.data.top_breakouts || [],
                breakouts_by_type: data.data.breakouts_by_type || {},
                total_breakouts_today: data.data.total_today || data.data.total_breakouts_today || 0,
                engine_metrics: data.data.engine_metrics || data.data.metrics || {},
                
                // Unified timestamp
                timestamp: data.data.timestamp || new Date().toISOString()
              };
              
              setBreakoutAnalysis(enhancedData);
            }
            break;

          case "market_sentiment_update":
            if (data.data) {
              console.log(
                "📊 Updating market sentiment:",
                data.data.sentiment,
                "with",
                data.data.confidence + "% confidence"
              );
              setMarketSentiment((prev) => ({
                ...prev,
                ...data.data,
              }));
            }
            break;

          case "sector_heatmap_update":
            if (data.data) {
              console.log(
                "🔥 Updating sector heatmap:",
                data.data.sectors?.length || 0,
                "sectors"
              );
              setHeatmap({
                sectors: data.data.sectors || [],
                summary: data.data.summary || null,
              });
            }
            break;

          case "volume_analysis_update":
            if (data.data) {
              console.log(
                "📊 Updating volume analysis:",
                data.data.volume_leaders?.length || 0,
                "volume leaders"
              );
              setVolumeAnalysis({
                volume_leaders: data.data.volume_leaders || [],
                unusual_volume: data.data.unusual_volume || [],
                volume_statistics: data.data.volume_statistics || null,
                sector_volumes: data.data.sector_volumes || null,
              });
            }
            break;

          case "intraday_highlights_update":
          case "intraday_stocks_update":
            if (data.data) {
              debugLog("debug", `⚡ ZERO-DELAY intraday: ${data.data.all_candidates?.length || 0} total, ${data.data.fno_candidates?.length || 0} FNO candidates`);

              // ⚡ INSTANT UPDATE: Direct assignment for maximum trading speed
              setIntradayStocks({
                all_candidates: data.data.all_candidates || [],
                high_momentum: data.data.high_momentum || [],
                high_volume: data.data.high_volume || [],
                fno_candidates: data.data.fno_candidates || [],
                fno_momentum: data.data.fno_momentum || [],
                fno_volume: data.data.fno_volume || [],
                summary: data.data.summary || null,
              });
            }
            break;

          case "record_movers_update":
            if (data.data) {
              console.log(
                "📈 Updating record movers:",
                data.data.new_highs?.length || 0,
                "new highs,",
                data.data.new_lows?.length || 0,
                "new lows"
              );
              setRecordMovers({
                new_highs: data.data.new_highs || [],
                new_lows: data.data.new_lows || [],
                summary: data.data.summary || null,
              });
            }
            break;

          case "market_status_update":
            if (data.data?.status) {
              setMarketStatus(data.data.status);
              console.log("🏛️ Market status updated:", data.data.status);
            }
            break;

          case "index_update":
            console.log("index_data --->", data.data);
            if (data.data) {
              console.log(
                "🏛️ Updating indices:",
                Object.keys(data.data).length,
                "indices"
              );
              setMarketData((prev) => ({ ...prev, ...data.data }));
            }
            break;

          // ⚡ ZERO-DELAY: Dashboard updates with MAXIMUM SPEED processing
          case "dashboard_update":
            if (data.data && typeof data.data === "object") {
              const dataSize = Array.isArray(data.data) ? data.data.length : Object.keys(data.data).length;
              console.log("📡 DASHBOARD UPDATE: Received", dataSize, "instruments");
              debugLog("debug", `⚡ ZERO-DELAY dashboard: ${dataSize} instruments`);

              // ⚡ ULTRA-FAST PATH: Skip validation for maximum speed
              let instrumentData;
              
              if (Array.isArray(data.data)) {
                // Array format - convert to object quickly
                instrumentData = {};
                data.data.forEach((item) => {
                  if (item?.instrument_key) {
                    instrumentData[item.instrument_key] = item;
                  }
                });
              } else {
                // Object format - use directly
                instrumentData = data.data;
              }

              // ⚡ DIRECT UPDATE: Skip validation for maximum trading speed
              const fastUpdates = {};
              let updateCount = 0;

              Object.entries(instrumentData).forEach(([key, item]) => {
                if (item && typeof item === "object") {
                  fastUpdates[key] = {
                    ...item,
                    timestamp: Date.now(),
                  };
                  updateCount++;
                }
              });

              if (updateCount > 0) {
                // ⚡ INSTANT STATE UPDATE: No delays, no caching overhead
                setMarketData((prev) => ({ ...prev, ...fastUpdates }));
                
                // 🔧 CRITICAL FIX: Also update Zustand store for getRealTimeTopMovers
                // Convert instrument_key format to symbol-based format for Zustand
                const zustandUpdates = {};
                Object.entries(fastUpdates).forEach(([key, item]) => {
                  if (item && item.symbol) {
                    // Convert from instrument_key format to symbol-based format
                    zustandUpdates[item.symbol] = {
                      ...item,
                      ltp: item.ltp || item.last_price || 0,
                      change: item.change || 0,
                      change_percent: item.change_percent || 0,
                      symbol: item.symbol,
                    };
                  }
                });
                
                if (Object.keys(zustandUpdates).length > 0) {
                  console.log("🔧 ZUSTAND UPDATE: Adding", Object.keys(zustandUpdates).length, "symbols to store");
                  useMarketStore.getState().updatePrices(zustandUpdates);
                  const storeSize = Object.keys(useMarketStore.getState().prices).length;
                  console.log("🔧 ZUSTAND UPDATE: Store now has", storeSize, "total symbols");
                }
              }

              // Separately update indices data for better tracking
              const indicesKeys = Object.keys(instrumentData).filter(
                (key) =>
                  key.includes("NIFTY") ||
                  key.includes("SENSEX") ||
                  key.includes("BANKEX") ||
                  key.includes("INDEX") ||
                  key.includes("FINNIFTY") ||
                  key.includes("MIDCPNIFTY")
              );

              if (indicesKeys.length > 0) {
                const validIndicesData = {};
                indicesKeys.forEach((key) => {
                  const sanitized = sanitizeInstrumentData(instrumentData[key]);
                  if (sanitized) {
                    validIndicesData[key] = sanitized;
                  }
                });

                debugLog(
                  "debug",
                  `Indices in dashboard update: ${
                    Object.keys(validIndicesData).length
                  } keys`
                );

                // Update indices data state with validation
                setIndicesData((prev) => ({
                  ...prev,
                  indices: [...(prev.indices || [])]
                    .map((idx) => {
                      const key = idx.instrument_key;
                      return validIndicesData[key]
                        ? { ...idx, ...validIndicesData[key] }
                        : idx;
                    })
                    .concat(
                      // Add new indices not in existing list
                      Object.keys(validIndicesData)
                        .filter(
                          (key) =>
                            !prev.indices?.some(
                              (idx) => idx.instrument_key === key
                            )
                        )
                        .map((key) => ({
                          instrument_key: key,
                          ...validIndicesData[key],
                        }))
                    ),
                }));
              }

              // Update market status if provided
              if (data.market_open !== undefined) {
                const status = data.market_open ? "open" : "closed";
                setMarketStatus(status);
              }

              setLastUpdate(Date.now());
            }
            break;

          case "market_breadth_update":
            if (data.data) {
              console.log("📊 Updating market breadth");
              setMarketSentiment((prev) => ({
                ...prev,
                market_breadth: data.data,
              }));
            }
            break;

          // Handle initial data packages
          case "initial_data":
          case "dashboard_data":
            console.log("📦 Processing initial/dashboard data package");

            const sourceData = data.data || data;

            // Process market data
            if (sourceData.market_data) {
              console.log(
                "📊 Loading",
                Object.keys(sourceData.market_data).length,
                "instruments from initial data"
              );
              setMarketData(sourceData.market_data);
            } else if (sourceData.live_prices) {
              console.log(
                "📊 Loading",
                Object.keys(sourceData.live_prices).length,
                "live prices"
              );
              setMarketData(sourceData.live_prices);
            } else if (sourceData.prices) {
              console.log(
                "📊 Loading",
                Object.keys(sourceData.prices).length,
                "prices"
              );
              setMarketData(sourceData.prices);
            }

            // Process analytics data with comprehensive error handling
            try {
              if (sourceData.top_movers) {
                setTopMovers({
                  gainers: sourceData.top_movers.gainers || [],
                  losers: sourceData.top_movers.losers || [],
                  analysis: sourceData.top_movers.analysis || null,
                });
              }

              if (sourceData.gap_analysis) {
                setGapAnalysis({
                  gap_up: sourceData.gap_analysis.gap_up || [],
                  gap_down: sourceData.gap_analysis.gap_down || [],
                  summary: sourceData.gap_analysis.summary || null,
                });
              }

              if (sourceData.volume_analysis) {
                setVolumeAnalysis({
                  volume_leaders:
                    sourceData.volume_analysis.volume_leaders || [],
                  unusual_volume:
                    sourceData.volume_analysis.unusual_volume || [],
                  volume_statistics:
                    sourceData.volume_analysis.volume_statistics || null,
                  sector_volumes:
                    sourceData.volume_analysis.sector_volumes || null,
                });
              }

              if (
                sourceData.intraday_highlights ||
                sourceData.intraday_stocks
              ) {
                const intradayData =
                  sourceData.intraday_highlights || sourceData.intraday_stocks;
                setIntradayStocks({
                  all_candidates: intradayData.all_candidates || [],
                  high_momentum: intradayData.high_momentum || [],
                  high_volume: intradayData.high_volume || [],
                  fno_candidates: intradayData.fno_candidates || [],
                  fno_momentum: intradayData.fno_momentum || [],
                  fno_volume: intradayData.fno_volume || [],
                  summary: intradayData.summary || null,
                });
              }

              if (sourceData.record_movers) {
                setRecordMovers({
                  new_highs: sourceData.record_movers.new_highs || [],
                  new_lows: sourceData.record_movers.new_lows || [],
                  summary: sourceData.record_movers.summary || null,
                });
              }

              if (sourceData.market_sentiment) {
                setMarketSentiment((prev) => ({
                  ...prev,
                  ...sourceData.market_sentiment,
                }));
              }

              if (sourceData.sector_heatmap) {
                setHeatmap({
                  sectors: sourceData.sector_heatmap.sectors || [],
                  summary: sourceData.sector_heatmap.summary || null,
                });
              }

              if (sourceData.breakout_analysis) {
                setBreakoutAnalysis({
                  breakouts: sourceData.breakout_analysis.breakouts || [],
                  breakdowns: sourceData.breakout_analysis.breakdowns || [],
                  summary: sourceData.breakout_analysis.summary || null,
                });
              }
            } catch (error) {
              console.error("❌ Error processing analytics data:", error);
            }

            if (sourceData.indices_data) {
              console.log(
                "📈 Loading indices data:",
                sourceData.indices_data.indices?.length || 0,
                "total indices"
              );
              setIndicesData({
                indices: sourceData.indices_data.indices || [],
                major_indices: sourceData.indices_data.major_indices || [],
                sector_indices: sourceData.indices_data.sector_indices || [],
                summary: sourceData.indices_data.summary || null,
              });
            }

            break;

          case "pong":
            // Keep-alive response
            break;

          case "trigger_analytics":
            debugLog(
              "debug",
              `Analytics trigger received: ${data.reason || "no reason"}`
            );
            // This is a trigger message to refresh analytics data
            // Request fresh analytics data when triggered
            if (connectionReady.current && subscriptionConfirmed.current) {
              debugLog(
                "debug",
                "Requesting fresh data after analytics trigger"
              );
              safeSend({ type: "get_dashboard_data" });
              safeSend({ type: "get_live_prices" });
              safeSend({ type: "get_market_status" });
              safeSend({ type: "get_indices_data" });
            } else {
              debugLog(
                "warn",
                `Cannot request data: ready=${connectionReady.current}, confirmed=${subscriptionConfirmed.current}`
              );
            }
            break;

          // NEW: Handle vectorized analytics updates from backend
          case "analytics_update":
            if (data.data) {
              debugLog(
                "debug",
                "Received vectorized analytics update from backend"
              );
              // This could be used to update a global analytics state
              // For now, just log that we received it
              console.log("📊 Real-time vectorized analytics:", data.data);
            }
            break;

          // NEW: Handle auto-trading signals from backend
          case "trading_signals":
            if (data.signals && Array.isArray(data.signals)) {
              debugLog(
                "info",
                `Received ${data.signals.length} trading signals from backend`
              );
              console.log("🎯 Real-time trading signals:", data.signals);
              // These signals could be displayed in a trading signals component
            }
            break;

          // NEW: Handle real-time gap signals from backend
          case "gap_signals_update":
            if (data.signals && Array.isArray(data.signals)) {
              debugLog(
                "info",
                `Received ${data.signals.length} gap signals from backend`
              );
              console.log("🚨 Real-time gap signals:", data.signals);

              // Update gap analysis data with new signals
              setGapAnalysis((prevGaps) => {
                const updatedGaps = { ...prevGaps };

                // Add new signals to appropriate arrays
                data.signals.forEach((signal) => {
                  if (signal.gap_type === "gap_up") {
                    updatedGaps.gap_up = updatedGaps.gap_up || [];
                    // Add if not already present (check by symbol)
                    if (
                      !updatedGaps.gap_up.find(
                        (g) => g.symbol === signal.symbol
                      )
                    ) {
                      updatedGaps.gap_up.unshift(signal); // Add to beginning
                    }
                  } else if (signal.gap_type === "gap_down") {
                    updatedGaps.gap_down = updatedGaps.gap_down || [];
                    if (
                      !updatedGaps.gap_down.find(
                        (g) => g.symbol === signal.symbol
                      )
                    ) {
                      updatedGaps.gap_down.unshift(signal); // Add to beginning
                    }
                  }
                });

                // Update summary
                updatedGaps.summary = {
                  ...updatedGaps.summary,
                  total_gap_up: updatedGaps.gap_up?.length || 0,
                  total_gap_down: updatedGaps.gap_down?.length || 0,
                  market_open_detected: true,
                  gap_detection_active: true,
                  last_update: new Date().toISOString(),
                };

                return updatedGaps;
              });
            }
            break;

          // NEW: Handle real-time breakout signals from backend
          case "breakout_signals_update":
            if (data.signals && Array.isArray(data.signals)) {
              debugLog(
                "info",
                `Received ${data.signals.length} breakout signals from backend`
              );
              console.log("⚡ Real-time breakout signals:", data.signals);

              // Update breakout analysis data with new signals
              setBreakoutAnalysis((prevBreakouts) => {
                const updatedBreakouts = { ...prevBreakouts };

                // Add new signals to appropriate arrays
                data.signals.forEach((signal) => {
                  if (signal.breakout_type === "breakout") {
                    updatedBreakouts.breakouts =
                      updatedBreakouts.breakouts || [];
                    // Add if not already present (check by symbol and timestamp)
                    if (
                      !updatedBreakouts.breakouts.find(
                        (b) =>
                          b.symbol === signal.symbol &&
                          Math.abs(
                            new Date(b.timestamp) - new Date(signal.timestamp)
                          ) < 60000 // 1 minute
                      )
                    ) {
                      updatedBreakouts.breakouts.unshift(signal); // Add to beginning
                      // Keep only latest 50 breakouts
                      if (updatedBreakouts.breakouts.length > 50) {
                        updatedBreakouts.breakouts =
                          updatedBreakouts.breakouts.slice(0, 50);
                      }
                    }
                  } else if (signal.breakout_type === "breakdown") {
                    updatedBreakouts.breakdowns =
                      updatedBreakouts.breakdowns || [];
                    if (
                      !updatedBreakouts.breakdowns.find(
                        (b) =>
                          b.symbol === signal.symbol &&
                          Math.abs(
                            new Date(b.timestamp) - new Date(signal.timestamp)
                          ) < 60000
                      )
                    ) {
                      updatedBreakouts.breakdowns.unshift(signal); // Add to beginning
                      // Keep only latest 50 breakdowns
                      if (updatedBreakouts.breakdowns.length > 50) {
                        updatedBreakouts.breakdowns =
                          updatedBreakouts.breakdowns.slice(0, 50);
                      }
                    }
                  }
                });

                // Update summary
                updatedBreakouts.summary = {
                  ...updatedBreakouts.summary,
                  total_breakouts: updatedBreakouts.breakouts?.length || 0,
                  total_breakdowns: updatedBreakouts.breakdowns?.length || 0,
                  detection_active: true,
                  is_trading_hours: data.market_hours || false,
                  last_update: new Date().toISOString(),
                };

                return updatedBreakouts;
              });
            }
            break;

          // Handle WebSocket route responses
          case "vectorized_analytics_response":
          case "trading_signals_response":
            debugLog("debug", `Received ${data.type} response`);
            console.log(`📡 ${data.type}:`, data.data);
            break;

          case "error":
            debugLog("error", "WebSocket server error", data.message);
            if (data.details) {
              debugLog("error", "Error details", data.details);
            }
            // Don't disconnect on error, just log it and continue
            break;

          default:
            // Log unknown message types for debugging
            if (data.type !== "heartbeat") {
              debugLog("warn", `Unhandled message type: ${data.type}`, data);
            }
        }
      } catch (error) {
        console.error(
          "❌ Error parsing WebSocket message:",
          error,
          "Raw data:",
          event.data?.substring(0, 200)
        );
      }
    },
    [processMessageQueue, safeSend]
  );

  // Separate throttled handler for non-critical messages (moved up for proper dependency order)
  // const throttledMessageHandler = useMemo(
  //   () => throttle(handleMessageRaw, 100), // 100ms for non-critical data
  //   [handleMessageRaw]
  // );

  // Real-time message handler with selective throttling - MEMORY OPTIMIZED
  const handleMessage = useCallback(
    (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("data" + data);

        // All messages processed immediately for maximum responsiveness
        handleMessageRaw(event);
      } catch (error) {
        console.error("Message parsing error:", error);
      }
    },
    [handleMessageRaw]
  );

  // Helper functions moved above for proper dependency order

  // Enhanced connection setup
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      debugLog("debug", "Already connected");
      return;
    }

    debugLog("info", `Establishing WebSocket connection to: ${WEBSOCKET_URL}`);
    setConnectionStatus("connecting");
    connectionReady.current = false;
    subscriptionConfirmed.current = false;

    try {
      ws.current = new WebSocket(WEBSOCKET_URL);

      ws.current.onopen = () => {
        debugLog("info", "WebSocket connected successfully");
        setIsConnected(true);
        setConnectionStatus("connected");
        reconnectAttempts.current = 0;

        // Wait for connection to stabilize before sending messages
        setTimeout(() => {
          connectionReady.current = true;

          const subscriptionMessage = {
            type: "subscribe",
            real_time: true, // Enable real-time mode for immediate updates
            events: [
              "price_update",
              "dashboard_update",
              "live_prices_enriched",
              "market_status_update",
              "top_movers_update",
              "gap_analysis_update",
              "breakout_analysis_update",
              "market_sentiment_update",
              "sector_heatmap_update",
              "volume_analysis_update",
              "intraday_stocks_update",
              "intraday_highlights_update",
              "record_movers_update",
              "index_update",
              "market_breadth_update",
              "performance_summary_update",
              "trigger_analytics",
              // FIXED EVENT NAMES for real-time integration
              "analytics_update", // Backend sends this for vectorized analytics
              "trading_signals", // Backend sends this for auto-trading signals
              "vectorized_analytics_response", // For WebSocket route responses
              "trading_signals_response", // For WebSocket route responses
              "all",
            ],
          };

          debugLog(
            "info",
            `Subscribing to ${subscriptionMessage.events.length} event types`
          );
          safeSend(subscriptionMessage);

          // Process any queued messages
          processMessageQueue();
        }, 100); // FIXED: Reduced from 1000ms to 100ms for faster startup

        // Setup keepalive ping
        pingInterval.current = setInterval(() => {
          if (
            ws.current?.readyState === WebSocket.OPEN &&
            connectionReady.current
          ) {
            safeSend({ type: "ping" });
          }
        }, PING_INTERVAL);
      };

      ws.current.onmessage = handleMessage;

      ws.current.onclose = (event) => {
        debugLog(
          "warn",
          `WebSocket disconnected: code=${event.code}, reason="${event.reason}"`
        );
        setIsConnected(false);
        setConnectionStatus("disconnected");
        connectionReady.current = false;
        subscriptionConfirmed.current = false;

        if (pingInterval.current) {
          clearInterval(pingInterval.current);
          pingInterval.current = null;
        }

        // Clear message queue on disconnect but preserve some critical messages
        const criticalMessages = messageQueue.current.filter(
          (msg) =>
            msg.type === "get_dashboard_data" || msg.type === "get_live_prices"
        );
        messageQueue.current = criticalMessages;

        // Enhanced auto-reconnect with exponential backoff
        if (
          event.code !== 1000 && // Not a normal close
          event.code !== 1001 && // Not going away
          reconnectAttempts.current < RECONNECT_INTERVALS.length
        ) {
          const delay = RECONNECT_INTERVALS[reconnectAttempts.current] || 32000;
          reconnectAttempts.current++;

          debugLog(
            "info",
            `Scheduling reconnection in ${delay}ms (attempt ${reconnectAttempts.current}/${RECONNECT_INTERVALS.length})`
          );
          setConnectionStatus("reconnecting");

          reconnectTimeout.current = setTimeout(() => {
            debugLog(
              "info",
              `Executing reconnection attempt ${reconnectAttempts.current}`
            );
            connect();
          }, delay);
        } else {
          debugLog(
            "error",
            "Max reconnection attempts reached or connection closed permanently"
          );
          setConnectionStatus("failed");
        }
      };

      ws.current.onerror = (error) => {
        debugLog("error", "WebSocket connection error", error);
        setConnectionStatus("error");
        connectionReady.current = false;
      };
    } catch (error) {
      debugLog("error", "Failed to create WebSocket connection", error);
      setConnectionStatus("error");

      // Fallback: try again after a delay if not at max attempts
      if (reconnectAttempts.current < RECONNECT_INTERVALS.length) {
        const delay = RECONNECT_INTERVALS[reconnectAttempts.current] || 5000;
        reconnectAttempts.current++;
        setTimeout(() => connect(), delay);
      }
    }
  }, [handleMessage, safeSend, processMessageQueue]);

  // Manual reconnect function
  const reconnect = useCallback(() => {
    console.log("🔄 Manual reconnection requested");

    // Clear existing connection
    if (ws.current) {
      ws.current.close(1000, "Manual reconnect");
    }

    // Clear timeouts
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    // Reset counters
    reconnectAttempts.current = 0;
    messageQueue.current = [];

    // Connect immediately
    setTimeout(connect, 100);
  }, [connect]);

  // Send message function
  const sendMessage = useCallback(
    (message) => {
      const success = safeSend(message);
      if (!success) {
        console.warn(
          "⚠️ Message queued due to connection not ready:",
          message.type
        );
      }
      return success;
    },
    [safeSend]
  );

  // Optimized utility functions
  const getStocksBySector = useCallback(() => {
    const sectorGroups = {};
    let totalProcessed = 0;

    Object.values(marketData).forEach((stock) => {
      if (!stock || typeof stock !== "object") return;

      const sector = stock.sector || "OTHER";
      if (!sectorGroups[sector]) {
        sectorGroups[sector] = [];
      }
      sectorGroups[sector].push(stock);
      totalProcessed++;
    });

    // Sort each sector by change percentage (descending)
    Object.keys(sectorGroups).forEach((sector) => {
      sectorGroups[sector].sort(
        (a, b) => (b.change_percent || 0) - (a.change_percent || 0)
      );
    });

    console.log(
      `📊 Grouped ${totalProcessed} stocks into ${
        Object.keys(sectorGroups).length
      } sectors`
    );
    return sectorGroups;
  }, [marketData]);

  // Enhanced search with multiple criteria
  const searchStocks = useCallback(
    (query) => {
      if (!query || query.length < 1) return [];

      const upperQuery = query.toUpperCase();
      const results = [];

      Object.values(marketData).forEach((stock) => {
        if (!stock) return;

        const matchScore =
          (stock.symbol?.toUpperCase().includes(upperQuery) ? 10 : 0) +
          (stock.symbol?.toUpperCase().startsWith(upperQuery) ? 5 : 0) +
          (stock.name?.toUpperCase().includes(upperQuery) ? 3 : 0) +
          (stock.trading_symbol?.toUpperCase().includes(upperQuery) ? 8 : 0);

        if (matchScore > 0) {
          results.push({ ...stock, matchScore });
        }
      });

      // Sort by match score and then by change percentage
      return results
        .sort((a, b) => {
          if (b.matchScore !== a.matchScore) {
            return b.matchScore - a.matchScore;
          }
          return (b.change_percent || 0) - (a.change_percent || 0);
        })
        .slice(0, 25);
    },
    [marketData]
  );

  // Enhanced market summary with more metrics
  const getMarketSummary = useCallback(() => {
    const stocks = Object.values(marketData).filter(
      (stock) =>
        stock &&
        typeof stock === "object" &&
        typeof stock.change_percent === "number" &&
        !stock.instrument_key?.includes("INDEX") // Exclude indices from market summary
    );

    if (stocks.length === 0) return null;

    const advancing = stocks.filter((s) => s.change_percent > 0).length;
    const declining = stocks.filter((s) => s.change_percent < 0).length;
    const unchanged = stocks.length - advancing - declining;

    const totalVolume = stocks.reduce((sum, s) => sum + (s.volume || 0), 0);
    const avgChange =
      stocks.reduce((sum, s) => sum + (s.change_percent || 0), 0) /
      stocks.length;

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
      totalVolume,
      avgChange: avgChange.toFixed(2),
      timestamp: Date.now(),
    };
  }, [marketData]);

  // Get specific stock data
  const getStockData = useCallback(
    (symbol) => {
      if (!symbol) return null;

      const upperSymbol = symbol.toUpperCase();

      // Try exact matches first
      const exactMatch = Object.values(marketData).find(
        (stock) =>
          stock?.symbol?.toUpperCase() === upperSymbol ||
          stock?.trading_symbol?.toUpperCase() === upperSymbol
      );

      if (exactMatch) return exactMatch;

      // Try partial matches
      const partialMatch = Object.entries(marketData).find(
        ([key, stock]) =>
          key.toUpperCase().includes(upperSymbol) ||
          stock?.symbol?.toUpperCase().includes(upperSymbol)
      );

      return partialMatch ? partialMatch[1] : null;
    },
    [marketData]
  );

  const getIndexData = useCallback(
    (symbol) => {
      if (!symbol) return null;

      const upperSymbol = symbol.toUpperCase();

      // Try exact matches first in major indices
      const majorMatch = indicesData.major_indices.find(
        (index) => index?.symbol?.toUpperCase() === upperSymbol
      );

      if (majorMatch) return majorMatch;

      // Try sector indices
      const sectorMatch = indicesData.sector_indices.find(
        (index) => index?.symbol?.toUpperCase() === upperSymbol
      );

      if (sectorMatch) return sectorMatch;

      // Try all indices
      const allMatch = indicesData.indices.find(
        (index) =>
          index?.symbol?.toUpperCase() === upperSymbol ||
          index?.name?.toUpperCase().includes(upperSymbol)
      );

      return allMatch || null;
    },
    [indicesData]
  );

  // Get indices by performance
  const getIndicesByPerformance = useCallback(() => {
    const sortedIndices = [...indicesData.indices].sort(
      (a, b) => (b.change_percent || 0) - (a.change_percent || 0)
    );

    return {
      gainers: sortedIndices.filter((idx) => (idx.change_percent || 0) > 0),
      losers: sortedIndices.filter((idx) => (idx.change_percent || 0) < 0),
      unchanged: sortedIndices.filter((idx) => (idx.change_percent || 0) === 0),
    };
  }, [indicesData.indices]);

  // Get major market sentiment from indices
  const getMarketSentimentFromIndices = useCallback(() => {
    if (!indicesData.major_indices || indicesData.major_indices.length === 0) {
      return { sentiment: "unknown", confidence: 0 };
    }

    const majorChanges = indicesData.major_indices
      .map((idx) => idx.change_percent || 0)
      .filter((change) => change !== 0);

    if (majorChanges.length === 0) {
      return { sentiment: "neutral", confidence: 50 };
    }

    const avgChange =
      majorChanges.reduce((sum, change) => sum + change, 0) /
      majorChanges.length;
    const positiveCount = majorChanges.filter((change) => change > 0).length;
    const confidence = Math.min(
      100,
      Math.abs(avgChange) * 20 + (positiveCount / majorChanges.length) * 30
    );

    let sentiment;
    if (avgChange > 1.5) {
      sentiment = "very_bullish";
    } else if (avgChange > 0.5) {
      sentiment = "bullish";
    } else if (avgChange < -1.5) {
      sentiment = "very_bearish";
    } else if (avgChange < -0.5) {
      sentiment = "bearish";
    } else {
      sentiment = "neutral";
    }

    return {
      sentiment,
      confidence: Math.round(confidence),
      avgChange: Math.round(avgChange * 100) / 100,
      positiveRatio: Math.round((positiveCount / majorChanges.length) * 100),
    };
  }, [indicesData.major_indices]);

  // Request specific indices data
  const requestIndicesData = useCallback(() => {
    return sendMessage({ type: "get_indices_data" });
  }, [sendMessage]);

  // Get indices summary with quick stats
  const getIndicesSummary = useCallback(() => {
    const summary = indicesData.summary || {};
    const majorIndices = indicesData.major_indices || [];
    const sectorIndices = indicesData.sector_indices || [];

    // Calculate real-time stats
    const majorUp = majorIndices.filter(
      (idx) => (idx.change_percent || 0) > 0
    ).length;
    const majorDown = majorIndices.filter(
      (idx) => (idx.change_percent || 0) < 0
    ).length;
    const sectorUp = sectorIndices.filter(
      (idx) => (idx.change_percent || 0) > 0
    ).length;
    const sectorDown = sectorIndices.filter(
      (idx) => (idx.change_percent || 0) < 0
    ).length;

    return {
      ...summary,
      major_up: majorUp,
      major_down: majorDown,
      major_unchanged: majorIndices.length - majorUp - majorDown,
      sector_up: sectorUp,
      sector_down: sectorDown,
      sector_unchanged: sectorIndices.length - sectorUp - sectorDown,
      total_indices: indicesData.indices.length,
      last_updated: Date.now(),
    };
  }, [indicesData]);

  // Calculate derived values for indices
  const totalIndices = indicesData.indices.length;
  const majorIndicesCount = indicesData.major_indices.length;
  const sectorIndicesCount = indicesData.sector_indices.length;

  // Get live prices for multiple symbols
  const getLivePrices = useCallback(
    (symbols) => {
      if (!Array.isArray(symbols)) return {};

      const prices = {};
      symbols.forEach((symbol) => {
        const data = getStockData(symbol);
        if (data) {
          prices[symbol] = {
            ltp: data.ltp || 0,
            change: data.change || 0,
            change_percent: data.change_percent || 0,
            volume: data.volume || 0,
            high: data.high || 0,
            low: data.low || 0,
            timestamp: data.timestamp || Date.now(),
          };
        }
      });
      return prices;
    },
    [getStockData]
  );

  // Calculate derived values
  const totalStocks = Object.keys(marketData).length;
  const sectors = Object.keys(getStocksBySector());
  const isStale = Date.now() - lastUpdate > STALE_THRESHOLD;

  // Connection health check
  const connectionHealth = useMemo(() => {
    const timeSinceLastMessage = Date.now() - lastMessageTime.current;
    return {
      isHealthy: isConnected && timeSinceLastMessage < 60000,
      lastMessageAge: timeSinceLastMessage,
      messageRate:
        messageCount.current / ((Date.now() - lastUpdate) / 1000 || 1),
      queueSize: messageQueue.current.length,
    };
  }, [isConnected, lastUpdate]);

  // Initialize connection on mount
  useEffect(() => {
    debugLog("info", "Initializing market data connection");
    connect();

    // Copy ref value for cleanup function
    const currentCache = marketDataCache.current;

    // Cleanup function with comprehensive resource cleanup
    return () => {
      debugLog("info", "Cleaning up market data connection");

      // Clear all timeouts and intervals
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
        pingInterval.current = null;
      }

      // Close WebSocket connection
      if (ws.current) {
        connectionReady.current = false;
        try {
          ws.current.close(1000, "Component unmounting");
        } catch (e) {
          debugLog("warn", "Error closing WebSocket", e);
        }
        ws.current = null;
      }

      // Clean up all resources
      messageQueue.current = [];
      subscriptionConfirmed.current = false;

      // Run all registered cleanup functions
      cleanupFunctions.current.forEach((cleanup) => {
        try {
          if (typeof cleanup === "function") cleanup();
        } catch (e) {
          debugLog("warn", "Error in cleanup function", e);
        }
      });
      cleanupFunctions.current = [];

      // Clear cache using copied ref value
      if (currentCache) {
        currentCache.clear();
      }
    };
  }, [connect]);

  // Clear message queue when disconnected
  useEffect(() => {
    if (!isConnected) {
      messageQueue.current = [];
    }
  }, [isConnected]);

  // Performance monitoring with proper cleanup
  useEffect(() => {
    let interval = null;

    if (DEBUG_VERBOSE) {
      interval = setInterval(() => {
        if (isConnected) {
          debugLog(
            "debug",
            `Performance stats: ${totalStocks} stocks, ${sectors.length} sectors, ` +
              `${
                messageCount.current
              } messages, cache: ${marketDataCache.current.size()}`
          );
        }
      }, 60000); // Log every minute

      // Register cleanup function
      cleanupFunctions.current.push(() => {
        if (interval) clearInterval(interval);
      });
    }

    return () => {
      if (interval) {
        clearInterval(interval);
        interval = null;
      }
    };
  }, [isConnected, totalStocks, sectors.length]);

  return {
    // Connection state
    isConnected,
    connectionStatus,
    isStale,
    reconnect,
    connectionHealth,

    // Market data
    marketData,
    marketStatus,
    totalStocks,
    sectors,

    // Analytics data
    topMovers,
    gapAnalysis,
    breakoutAnalysis,
    marketSentiment,
    heatmap,
    volumeAnalysis,
    intradayStocks,
    recordMovers,

    // NEW: Indices data and functions
    indicesData,
    totalIndices,
    majorIndicesCount,
    sectorIndicesCount,
    getIndexData,
    getIndicesByPerformance,
    getMarketSentimentFromIndices,
    requestIndicesData,
    getIndicesSummary,

    // Utility functions
    sendMessage,
    getStockData,
    getLivePrices,
    getStocksBySector,
    searchStocks,
    getMarketSummary,

    // Performance metrics
    messageCount: messageCount.current,
    lastUpdate,
    queueSize: messageQueue.current.length,

    // Legacy compatibility
    ltps: marketData,
    groupedStocks: getStocksBySector(),
    tokenExpired: false,
    resetTokenExpired: () => {},
  };
};

// Context wrapper for easy consumption
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
