// hooks/useUnifiedMarketData.js - COMPLETE PRODUCTION READY VERSION

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { createContext, useContext } from "react";

const WEBSOCKET_URL = process.env.REACT_APP_WS_URL
  ? `${process.env.REACT_APP_WS_URL}/ws/unified`
  : "ws://localhost:8000/ws/unified";

const RECONNECT_INTERVALS = [1000, 2000, 4000, 8000, 16000, 32000];
const PING_INTERVAL = 30000;
const STALE_THRESHOLD = 120000; // 2 minutes

// Optimized throttle function for performance
const throttle = (func, delay) => {
  let timeoutId;
  let lastExecTime = 0;
  return function (...args) {
    const currentTime = Date.now();

    if (currentTime - lastExecTime > delay) {
      func.apply(this, args);
      lastExecTime = currentTime;
    } else {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        func.apply(this, args);
        lastExecTime = Date.now();
      }, delay - (currentTime - lastExecTime));
    }
  };
};

// Debounce function for expensive operations
const debounce = (func, delay) => {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
};

export const useUnifiedMarketData = () => {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [lastUpdate, setLastUpdate] = useState(Date.now());
  const [indicesData, setIndicesData] = useState({
    indices: [],
    major_indices: [],
    sector_indices: [],
    summary: null,
  });
  // Market data state
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
    summary: null,
  });
  const [recordMovers, setRecordMovers] = useState({
    new_highs: [],
    new_lows: [],
    summary: null,
  });

  // Connection management refs
  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef(null);
  const pingInterval = useRef(null);
  const connectionReady = useRef(false);
  const messageQueue = useRef([]);
  const subscriptionConfirmed = useRef(false);

  // Performance tracking
  const messageCount = useRef(0);
  const lastMessageTime = useRef(Date.now());

  // Safe message sending with queue management
  const safeSend = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN && connectionReady.current) {
      try {
        ws.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error("❌ Error sending message:", error);
        messageQueue.current.push(message);
        return false;
      }
    } else {
      messageQueue.current.push(message);
      return false;
    }
  }, []);

  // Process queued messages when connection is ready
  const processMessageQueue = useCallback(() => {
    let processed = 0;
    while (
      messageQueue.current.length > 0 &&
      ws.current?.readyState === WebSocket.OPEN &&
      processed < 10 // Limit batch size
    ) {
      const message = messageQueue.current.shift();
      try {
        ws.current.send(JSON.stringify(message));
        processed++;
      } catch (error) {
        console.error("❌ Error processing queued message:", error);
        messageQueue.current.unshift(message); // Put it back
        break;
      }
    }
    if (processed > 0) {
      console.log(`📤 Processed ${processed} queued messages`);
    }
  }, []);

  // Enhanced message handler with comprehensive data processing
  const handleMessage = useCallback(
    throttle((event) => {
      try {
        const data = JSON.parse(event.data);
        messageCount.current++;
        lastMessageTime.current = Date.now();
        setLastUpdate(Date.now());

        // Log message types for debugging
        if (messageCount.current % 100 === 0) {
          console.log(
            `📨 Processed ${messageCount.current} messages, type: ${data.type}`
          );
        }

        switch (data.type) {
          case "connection_established":
            console.log("🔌 Connected to unified WebSocket:", data.client_id);
            connectionReady.current = true;
            subscriptionConfirmed.current = false;
            processMessageQueue();
            break;

          case "subscription_confirmed":
            console.log("✅ Subscription confirmed for events:", data.events);
            subscriptionConfirmed.current = true;

            // Request initial data after subscription confirmation
            setTimeout(() => {
              safeSend({ type: "get_dashboard_data" });
              safeSend({ type: "get_live_prices" });
              safeSend({ type: "get_market_status" });
              safeSend({ type: "get_indices_data" });
            }, 500);
            break;

          // Handle price updates with flexible structure parsing
          case "price_update":
            if (data.data) {
              let priceData = data.data;

              // Handle nested structure from your WebSocket
              if (data.data.data && typeof data.data.data === "object") {
                priceData = data.data.data;
              }

              if (Object.keys(priceData).length > 0) {
                setMarketData((prev) => {
                  const updated = { ...prev };

                  Object.entries(priceData).forEach(([key, instrumentData]) => {
                    if (instrumentData && typeof instrumentData === "object") {
                      // Handle nested data structure
                      const finalData = instrumentData.data || instrumentData;

                      // Extract symbol with multiple fallbacks
                      const symbol =
                        finalData.symbol ||
                        finalData.trading_symbol ||
                        key.split("|").pop() ||
                        key;

                      // Process the instrument data
                      updated[key] = {
                        // Identifiers
                        instrument_key: finalData.instrument_key || key,
                        symbol: symbol,
                        name: finalData.name || symbol,
                        trading_symbol: finalData.trading_symbol || symbol,
                        exchange:
                          finalData.exchange ||
                          (key.includes("NSE")
                            ? "NSE"
                            : key.includes("MCX")
                            ? "MCX"
                            : key.includes("BSE")
                            ? "BSE"
                            : "UNKNOWN"),
                        sector: finalData.sector || "OTHER",
                        instrument_type: finalData.instrument_type || "EQ",

                        // Price data with comprehensive fallbacks
                        ltp: Number(
                          finalData.ltp ||
                            finalData.last_price ||
                            finalData.price ||
                            finalData.close ||
                            0
                        ),
                        cp: Number(
                          finalData.cp ||
                            finalData.previous_close ||
                            finalData.prev_close ||
                            finalData.ltp ||
                            0
                        ),
                        change: Number(finalData.change || 0),
                        change_percent: Number(
                          finalData.change_percent || finalData.pchange || 0
                        ),

                        // OHLCV data
                        open: Number(finalData.open || finalData.ltp || 0),
                        high: Number(finalData.high || finalData.ltp || 0),
                        low: Number(finalData.low || finalData.ltp || 0),
                        close: Number(finalData.close || finalData.ltp || 0),
                        volume: Number(
                          finalData.volume ||
                            finalData.daily_volume ||
                            finalData.vol ||
                            0
                        ),

                        // Trading data
                        avg_trade_price: Number(
                          finalData.avg_trade_price ||
                            finalData.atp ||
                            finalData.vwap ||
                            0
                        ),
                        bid_price: Number(
                          finalData.bid_price || finalData.bid || 0
                        ),
                        ask_price: Number(
                          finalData.ask_price || finalData.ask || 0
                        ),
                        bid_qty: Number(
                          finalData.bid_qty || finalData.bid_quantity || 0
                        ),
                        ask_qty: Number(
                          finalData.ask_qty || finalData.ask_quantity || 0
                        ),

                        // Market depth
                        ltq: Number(
                          finalData.ltq || finalData.last_traded_quantity || 0
                        ),
                        ltt:
                          finalData.ltt || finalData.last_traded_time || null,

                        // Derived data
                        trend: finalData.trend || "neutral",
                        volatility: finalData.volatility || "normal",
                        gap_percent: Number(finalData.gap_percent || 0),

                        // Metadata
                        timestamp: finalData.timestamp || Date.now(),
                        last_updated: finalData.last_updated || Date.now(),
                        update_count: Number(finalData.update_count || 0),
                        data_source: finalData.data_source || "websocket",

                        // Additional fields that might be present
                        market_cap_category: finalData.market_cap_category,
                        volume_category: finalData.volume_category,
                        performance_category: finalData.performance_category,
                        has_derivatives: finalData.has_derivatives,
                      };
                    }
                  });

                  return updated;
                });
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

          // Handle analytics updates
          case "top_movers_update":
            if (data.data) {
              console.log(
                "🚀 Updating top movers:",
                data.data.gainers?.length || 0,
                "gainers,",
                data.data.losers?.length || 0,
                "losers"
              );
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
            if (data.data) {
              console.log(
                "📊 Updating breakout analysis:",
                data.data.breakouts?.length || 0,
                "breakouts,",
                data.data.breakdowns?.length || 0,
                "breakdowns"
              );
              setBreakoutAnalysis({
                breakouts: data.data.breakouts || [],
                breakdowns: data.data.breakdowns || [],
                summary: data.data.summary || null,
              });
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
              console.log(
                "⚡ Updating intraday stocks:",
                data.data.all_candidates?.length || 0,
                "candidates"
              );
              setIntradayStocks({
                all_candidates: data.data.all_candidates || [],
                high_momentum: data.data.high_momentum || [],
                high_volume: data.data.high_volume || [],
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

          case "error":
            console.error(
              "❌ WebSocket server error:",
              data.message,
              data.details
            );
            break;

          default:
            // Log unknown message types for debugging
            if (data.type !== "heartbeat") {
              console.log("⚠️ Unhandled message type:", data.type);
              console.log("⚠️ Unhandled message type - data:", data.data);
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
    }, 250), // Increased throttle time to 250ms
    [processMessageQueue, safeSend]
  );

  // Enhanced connection setup
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log("🔌 Already connected");
      return;
    }

    console.log("🔌 Establishing WebSocket connection to:", WEBSOCKET_URL);
    setConnectionStatus("connecting");
    connectionReady.current = false;
    subscriptionConfirmed.current = false;

    try {
      ws.current = new WebSocket(WEBSOCKET_URL);

      ws.current.onopen = () => {
        console.log("✅ WebSocket connected successfully");
        setIsConnected(true);
        setConnectionStatus("connected");
        reconnectAttempts.current = 0;

        // Wait for connection to stabilize before sending messages
        setTimeout(() => {
          connectionReady.current = true;

          const subscriptionMessage = {
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
              "volume_analysis_update",
              "intraday_stocks_update",
              "intraday_highlights_update",
              "record_movers_update",
              "index_update",
              "market_breadth_update",
              "performance_summary_update",
              "all",
            ],
          };

          console.log(
            "📡 Subscribing to",
            subscriptionMessage.events.length,
            "event types"
          );
          safeSend(subscriptionMessage);

          // Process any queued messages
          processMessageQueue();
        }, 1000);

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
        console.log(
          `🔌 WebSocket disconnected: code=${event.code}, reason="${event.reason}"`
        );
        setIsConnected(false);
        setConnectionStatus("disconnected");
        connectionReady.current = false;
        subscriptionConfirmed.current = false;

        if (pingInterval.current) {
          clearInterval(pingInterval.current);
          pingInterval.current = null;
        }

        // Clear message queue on disconnect
        messageQueue.current = [];

        // Auto-reconnect with exponential backoff
        if (
          event.code !== 1000 && // Not a normal close
          event.code !== 1001 && // Not going away
          reconnectAttempts.current < RECONNECT_INTERVALS.length
        ) {
          const delay = RECONNECT_INTERVALS[reconnectAttempts.current] || 32000;
          reconnectAttempts.current++;

          console.log(
            `🔄 Scheduling reconnection in ${delay}ms (attempt ${reconnectAttempts.current}/${RECONNECT_INTERVALS.length})`
          );
          setConnectionStatus("reconnecting");

          reconnectTimeout.current = setTimeout(() => {
            console.log(
              `🔄 Executing reconnection attempt ${reconnectAttempts.current}`
            );
            connect();
          }, delay);
        } else {
          console.error(
            "❌ Max reconnection attempts reached or connection closed permanently"
          );
          setConnectionStatus("failed");
        }
      };

      ws.current.onerror = (error) => {
        console.error("❌ WebSocket connection error:", error);
        setConnectionStatus("error");
        connectionReady.current = false;
      };
    } catch (error) {
      console.error("❌ Failed to create WebSocket connection:", error);
      setConnectionStatus("error");
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
    console.log("🚀 Initializing market data connection");
    connect();

    // Cleanup function
    return () => {
      console.log("🧹 Cleaning up market data connection");

      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
      }
      if (ws.current) {
        connectionReady.current = false;
        ws.current.close(1000, "Component unmounting");
      }

      // Clear message queue
      messageQueue.current = [];
    };
  }, [connect]);

  // Clear message queue when disconnected
  useEffect(() => {
    if (!isConnected) {
      messageQueue.current = [];
    }
  }, [isConnected]);

  // Debug logging for performance monitoring
  useEffect(() => {
    const interval = setInterval(() => {
      if (isConnected) {
        console.log(
          `📊 Stats: ${totalStocks} stocks, ${sectors.length} sectors, ${messageCount.current} messages processed`
        );
      }
    }, 60000); // Log every minute

    return () => clearInterval(interval);
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
