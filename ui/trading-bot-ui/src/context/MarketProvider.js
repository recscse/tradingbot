import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  useCallback,
} from "react";
import axios from "axios";
import { getSocket } from "../utils/socket";

const MarketContext = createContext();
export const useMarket = () => useContext(MarketContext);

// 🆕 Enhanced WebSocket Management
let centralizedDashboardWs = null; // NEW: Centralized dashboard WebSocket
let centralizedTradingWs = null; // NEW: Centralized trading WebSocket
let legacyWs = null; // LEGACY: Backward compatibility
let pingInterval = null;
let reconnectTimeout = null;

export const MarketProvider = ({ children }) => {
  // ===== STATE MANAGEMENT =====

  // KEEP: Your existing essential state
  const [groupedStocks, setGroupedStocks] = useState({});
  const [ltps, setLtps] = useState({});
  const [marketStatus, setMarketStatus] = useState("loading");
  const [tokenExpired, setTokenExpired] = useState(false);

  // ENHANCED: Better system management
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [tradingData, setTradingData] = useState({});
  const [systemMode, setSystemMode] = useState("auto"); // "auto", "centralized", "legacy"
  const [connectionStatus, setConnectionStatus] = useState({
    centralized_dashboard: "disconnected",
    centralized_trading: "disconnected",
    legacy: "disconnected",
    auto_detection: "checking",
  });

  // NEW: Enhanced system capabilities tracking
  const [systemCapabilities, setSystemCapabilities] = useState({
    centralized_ws_available: false,
    admin_token_configured: false,
    market_closure_aware: false,
    unlimited_scaling: false,
    rate_limit_protection: false,
  });

  // NEW: Performance and data quality metrics
  const [dataMetrics, setDataMetrics] = useState({
    last_update_time: null,
    updates_per_minute: 0,
    data_source: "unknown",
    latency_ms: 0,
    instruments_count: 0,
  });

  // KEEP: Your existing refs with enhancements
  const connectingRef = useRef(false);
  const hasReceivedFeed = useRef(false);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const lastPingTime = useRef(null);
  const updateCountRef = useRef(0);

  // ===== UTILITY FUNCTIONS =====

  const resetTokenExpired = useCallback(() => {
    setTokenExpired(false);
  }, []);

  const updateDataMetrics = useCallback((dataSource, instrumentsCount = 0) => {
    const now = Date.now();
    updateCountRef.current += 1;

    setDataMetrics((prev) => {
      const timeDiff = now - (prev.last_update_time || now);
      const latency = lastPingTime.current ? now - lastPingTime.current : 0;

      return {
        last_update_time: now,
        updates_per_minute: Math.round(
          (updateCountRef.current * 60000) / Math.max(timeDiff, 1000)
        ),
        data_source: dataSource,
        latency_ms: latency,
        instruments_count: instrumentsCount,
      };
    });
  }, []);

  // ENHANCED: Complete WebSocket cleanup
  const disconnectAllWebSockets = useCallback(() => {
    console.log("🧹 Cleaning up all WebSocket connections...");

    if (centralizedDashboardWs) {
      centralizedDashboardWs.close();
      centralizedDashboardWs = null;
    }

    if (centralizedTradingWs) {
      centralizedTradingWs.close();
      centralizedTradingWs = null;
    }

    if (legacyWs) {
      legacyWs.close();
      legacyWs = null;
    }

    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }

    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }

    connectingRef.current = false;
    hasReceivedFeed.current = false;
    reconnectAttempts.current = 0;

    setConnectionStatus({
      centralized_dashboard: "disconnected",
      centralized_trading: "disconnected",
      legacy: "disconnected",
      auto_detection: "idle",
    });
  }, []);

  // NEW: Auto-detect system capabilities
  const detectSystemCapabilities = useCallback(async () => {
    try {
      console.log("🔍 Detecting system capabilities...");

      setConnectionStatus((prev) => ({ ...prev, auto_detection: "checking" }));

      // Check if centralized system is available
    //  const healthResponse = await axios.get(
     //   `${process.env.REACT_APP_API_URL}////health`
    //  );

      const systemInfo = await axios.get(`${process.env.REACT_APP_API_URL}/`);

      const capabilities = {
        centralized_ws_available:
          systemInfo.data?.new_centralized_websocket_system?.available || false,
        admin_token_configured:
          systemInfo.data?.new_centralized_websocket_system?.ws_connected ||
          false,
        market_closure_aware:
          systemInfo.data?.data_architecture?.market_closure_handling ===
          "automatic_snapshot_mode",
        unlimited_scaling:
          systemInfo.data?.new_centralized_websocket_system?.available || false,
        rate_limit_protection:
          systemInfo.data?.new_centralized_websocket_system?.available || false,
      };

      setSystemCapabilities(capabilities);

      // Auto-select best mode
      if (
        capabilities.centralized_ws_available &&
        capabilities.admin_token_configured
      ) {
        setSystemMode("centralized");
        console.log("✅ Auto-selected CENTRALIZED mode (recommended)");
      } else {
        setSystemMode("legacy");
        console.log("⚠️ Auto-selected LEGACY mode (centralized not available)");
      }

      setConnectionStatus((prev) => ({ ...prev, auto_detection: "completed" }));

      return capabilities;
    } catch (error) {
      console.error("❌ Failed to detect system capabilities:", error);
      setSystemMode("legacy");
      setConnectionStatus((prev) => ({ ...prev, auto_detection: "failed" }));
      return null;
    }
  }, []);

  // ===== WEBSOCKET CONNECTION HANDLERS =====

  // NEW: Centralized Dashboard WebSocket (All market data)
  const connectCentralizedDashboard = useCallback(() => {
    if (centralizedDashboardWs || connectingRef.current) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    console.log("🚀 Connecting to NEW Centralized Dashboard WebSocket...");

    const wsUrl = `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/api/v1/ws/dashboard?token=${token}`;

    centralizedDashboardWs = new WebSocket(wsUrl);
    connectingRef.current = true;

    centralizedDashboardWs.onopen = () => {
      console.log("✅ NEW Centralized Dashboard WebSocket connected");
      connectingRef.current = false;
      reconnectAttempts.current = 0;

      setConnectionStatus((prev) => ({
        ...prev,
        centralized_dashboard: "connected",
      }));

      // Send ping to check latency
      lastPingTime.current = Date.now();
      centralizedDashboardWs.send(JSON.stringify({ type: "ping" }));

      // Setup ping interval
      pingInterval = setInterval(() => {
        if (centralizedDashboardWs?.readyState === WebSocket.OPEN) {
          lastPingTime.current = Date.now();
          centralizedDashboardWs.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    };

    centralizedDashboardWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        // Handle token expiration
        if (msg.type === "error" && msg.reason === "token_expired") {
          setTokenExpired(true);
          console.log("❌ NEW Centralized Dashboard: Token expired");
          disconnectAllWebSockets();
          return;
        }

        // Handle pong responses
        if (msg.type === "pong") {
          const latency = Date.now() - lastPingTime.current;
          setDataMetrics((prev) => ({ ...prev, latency_ms: latency }));
          return;
        }

        // Handle connection status
        if (msg.type === "connection_status") {
          console.log("📊 NEW Centralized Dashboard connection status:", msg);
          return;
        }

        // Handle dashboard updates (all market data)
        if (msg.type === "dashboard_update" && msg.data) {
          hasReceivedFeed.current = true;
          const feeds = msg.data;

          updateDataMetrics(
            "CENTRALIZED_DASHBOARD_WS",
            Object.keys(feeds).length
          );

          console.log(
            `📊 NEW Centralized Dashboard: Received data for ${
              Object.keys(feeds).length
            } instruments`
          );

          setLtps((prev) => {
            const updates = { ...prev };

            Object.entries(feeds).forEach(([instrumentKey, tickData]) => {
              if (tickData?.ltpc?.ltp !== undefined) {
                // Handle both individual ticks and full feed data
                const ltp = tickData.ltpc?.ltp || tickData.ltp;
                const cp = tickData.ltpc?.cp || tickData.cp;
                const ltq = tickData.ltpc?.ltq || tickData.ltq;

                updates[instrumentKey.toUpperCase()] = {
                  ltp: ltp,
                  cp: cp,
                  ltq: ltq,
                  last_trade_time:
                    tickData.ltpc?.ltt || tickData.last_trade_time,
                  ohlc: tickData.ohlc || [],
                  bid_ask: tickData.bid_ask || [],
                  greeks: tickData.greeks || {},
                  iv: tickData.iv,
                  oi: tickData.oi,
                  atp: tickData.atp,
                  tbq: tickData.tbq,
                  tsq: tickData.tsq,
                  data_source: "CENTRALIZED_DASHBOARD_WS",
                  timestamp: msg.timestamp,
                  market_open: msg.market_open,
                };
              }
            });

            return updates;
          });

          // Update market status if provided
          if (msg.market_open !== undefined) {
            setMarketStatus(msg.market_open ? "open" : "closed");
          }
        }

        // Handle market info updates
        if (msg.type === "market_info") {
          const status = msg.marketStatus?.toLowerCase() || "unknown";
          setMarketStatus(status);
          console.log(
            `📈 NEW Centralized Dashboard: Market status - ${status}`
          );
        }
      } catch (error) {
        console.error(
          "⚠️ NEW Centralized Dashboard WebSocket parse error:",
          error
        );
      }
    };

    centralizedDashboardWs.onclose = (event) => {
      console.warn(
        "❌ NEW Centralized Dashboard WebSocket closed:",
        event.reason
      );
      setConnectionStatus((prev) => ({
        ...prev,
        centralized_dashboard: "disconnected",
      }));

      // Auto-reconnect logic
      if (
        reconnectAttempts.current < maxReconnectAttempts &&
        systemMode === "centralized"
      ) {
        reconnectAttempts.current += 1;
        const delay = Math.min(
          1000 * Math.pow(2, reconnectAttempts.current),
          30000
        );

        console.log(
          `🔄 Reconnecting NEW Centralized Dashboard in ${delay}ms (attempt ${reconnectAttempts.current})`
        );

        reconnectTimeout = setTimeout(() => {
          connectCentralizedDashboard();
        }, delay);
      }
    };

    centralizedDashboardWs.onerror = (error) => {
      console.error("💥 NEW Centralized Dashboard WebSocket error:", error);
      setConnectionStatus((prev) => ({
        ...prev,
        centralized_dashboard: "error",
      }));
    };
  }, [systemMode, updateDataMetrics, disconnectAllWebSockets]);

  // NEW: Centralized Trading WebSocket (Filtered data for selected stocks)
  const connectCentralizedTrading = useCallback(() => {
    if (centralizedTradingWs || selectedStocks.length === 0) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    console.log(
      `🎯 Connecting to NEW Centralized Trading WebSocket for ${selectedStocks.length} stocks...`
    );

    const wsUrl = `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/api/v1/ws/trading?token=${token}`;

    centralizedTradingWs = new WebSocket(wsUrl);

    centralizedTradingWs.onopen = () => {
      console.log("✅ NEW Centralized Trading WebSocket connected");

      setConnectionStatus((prev) => ({
        ...prev,
        centralized_trading: "connected",
      }));
    };

    centralizedTradingWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "error" && msg.reason === "token_expired") {
          setTokenExpired(true);
          console.log("❌ NEW Centralized Trading: Token expired");
          return;
        }

        if (msg.type === "trading_update" && msg.data) {
          console.log(
            `🎯 NEW Centralized Trading: Received data for ${msg.instruments_count} instruments`
          );

          updateDataMetrics("CENTRALIZED_TRADING_WS", msg.instruments_count);

          setTradingData((prev) => {
            const updates = { ...prev };

            Object.entries(msg.data).forEach(([instrumentKey, tickData]) => {
              const symbol = extractSymbolFromInstrumentKey(instrumentKey);

              if (!updates[symbol]) {
                updates[symbol] = { instruments: {} };
              }

              updates[symbol].instruments[instrumentKey] = {
                ...tickData,
                timestamp: msg.timestamp,
                data_source: "CENTRALIZED_TRADING_WS",
              };
            });

            return updates;
          });
        }

        if (msg.type === "connection_status") {
          console.log("🎯 NEW Centralized Trading connection status:", msg);
        }
      } catch (error) {
        console.error(
          "⚠️ NEW Centralized Trading WebSocket parse error:",
          error
        );
      }
    };

    centralizedTradingWs.onclose = (event) => {
      console.warn(
        "❌ NEW Centralized Trading WebSocket closed:",
        event.reason
      );
      setConnectionStatus((prev) => ({
        ...prev,
        centralized_trading: "disconnected",
      }));
    };

    centralizedTradingWs.onerror = (error) => {
      console.error("💥 NEW Centralized Trading WebSocket error:", error);
      setConnectionStatus((prev) => ({
        ...prev,
        centralized_trading: "error",
      }));
    };
  }, [selectedStocks, updateDataMetrics]);

  // LEGACY: Keep your existing WebSocket logic for backward compatibility
  const connectLegacyWebSocket = useCallback(() => {
    if (
      legacyWs ||
      connectingRef.current ||
      Object.keys(groupedStocks).length === 0
    )
      return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    console.log("🔄 Connecting to LEGACY WebSocket...");

    const wsUrl = `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/ws/market?token=${token}`;
    legacyWs = getSocket(wsUrl);
    connectingRef.current = true;

    legacyWs.onopen = () => {
      connectingRef.current = false;
      setConnectionStatus((prev) => ({ ...prev, legacy: "connected" }));

      pingInterval = setInterval(() => {
        if (legacyWs?.readyState === WebSocket.OPEN) {
          legacyWs.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);

      console.info("✅ LEGACY WebSocket connected");
    };

    legacyWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "error" && msg.reason === "token_expired") {
          setTokenExpired(true);
          disconnectAllWebSockets();
          return;
        }

        if (msg.type === "market_info") {
          const status = msg.marketStatus?.toLowerCase() || "closed";
          setMarketStatus(status);
        }

        if (msg.type === "live_feed" && msg.data) {
          hasReceivedFeed.current = true;
          const feeds = msg.data;

          updateDataMetrics("LEGACY_WS", Object.keys(feeds).length);

          setLtps((prev) => {
            const updates = { ...prev };
            Object.entries(feeds).forEach(([key, parsed]) => {
              if (parsed?.ltp !== undefined) {
                const isIndexKey =
                  key.startsWith("NSE_INDEX|") || key.startsWith("BSE_INDEX|");
                const finalKey = isIndexKey ? key : key.toUpperCase();
                updates[finalKey] = {
                  ltp: parsed.ltp ?? null,
                  cp: parsed.cp ?? null,
                  ohlc: parsed.ohlc ?? [],
                  iv: parsed.iv ?? null,
                  oi: parsed.oi ?? null,
                  atp: parsed.atp ?? null,
                  bid_ask: parsed.bid_ask ?? [],
                  greeks: parsed.greeks ?? {},
                  ltq: parsed.ltq ?? null,
                  last_trade_time: parsed.last_trade_time ?? null,
                  data_source: "LEGACY_WS",
                };
              }
            });
            return updates;
          });
        }
      } catch (e) {
        console.error("⚠️ LEGACY WebSocket parse error:", e);
      }
    };

    legacyWs.onclose = () => {
      console.warn("❌ LEGACY WebSocket closed");
      setConnectionStatus((prev) => ({ ...prev, legacy: "disconnected" }));
    };

    legacyWs.onerror = (err) => {
      console.error("💥 LEGACY WebSocket error:", err);
      setConnectionStatus((prev) => ({ ...prev, legacy: "error" }));
    };
  }, [groupedStocks, updateDataMetrics, disconnectAllWebSockets]);

  // ===== MODE SWITCHING FUNCTIONS =====

  const switchToCentralizedMode = useCallback(() => {
    console.log("🔄 Switching to NEW Centralized mode...");
    disconnectAllWebSockets();
    setSystemMode("centralized");
  }, [disconnectAllWebSockets]);

  const switchToLegacyMode = useCallback(() => {
    console.log("🔄 Switching to Legacy mode...");
    disconnectAllWebSockets();
    setSystemMode("legacy");
  }, [disconnectAllWebSockets]);

  const switchToAutoMode = useCallback(() => {
    console.log("🔄 Switching to Auto mode...");
    disconnectAllWebSockets();
    setSystemMode("auto");
  }, [disconnectAllWebSockets]);

  // ===== DATA FETCHING =====

  // Fetch grouped stocks (unchanged)
  useEffect(() => {
    const fetchGrouped = async () => {
      try {
        const res = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/stocks/top`
        );
        const stocks = res.data?.data || {};
        setGroupedStocks(stocks);
        console.log(`📊 Loaded ${Object.keys(stocks).length} stock groups`);
      } catch (err) {
        console.error("❌ Failed to fetch stock groups:", err);
      }
    };

    fetchGrouped();
  }, []);

  // Fetch selected stocks for trading
  useEffect(() => {
    const fetchSelectedStocks = async () => {
      try {
        const res = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/selected-stocks/today`
        );
        const stocks = res.data?.selectedStocks || [];
        setSelectedStocks(stocks);
        console.log(`🎯 Loaded ${stocks.length} selected stocks for trading`);
      } catch (err) {
        console.error("❌ Failed to fetch selected stocks:", err);
      }
    };

    fetchSelectedStocks();

    // Refresh every 5 minutes
    const interval = setInterval(fetchSelectedStocks, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // ===== CONNECTION MANAGEMENT =====

  // Auto-detect capabilities on startup
  useEffect(() => {
    detectSystemCapabilities();
  }, [detectSystemCapabilities]);

  // Connect based on mode
  useEffect(() => {
    if (systemMode === "auto") {
      // Auto mode will be set by detectSystemCapabilities
      return;
    }

    // Disconnect all first
    disconnectAllWebSockets();

    // Connect based on selected mode
    if (systemMode === "centralized") {
      if (Object.keys(groupedStocks).length > 0) {
        connectCentralizedDashboard();
      }
      if (selectedStocks.length > 0) {
        connectCentralizedTrading();
      }
    } else if (systemMode === "legacy") {
      connectLegacyWebSocket();
    }

    // Cleanup on unmount
    return () => {
      disconnectAllWebSockets();
    };
  }, [
    systemMode,
    groupedStocks,
    selectedStocks,
    connectCentralizedDashboard,
    connectCentralizedTrading,
    connectLegacyWebSocket,
    disconnectAllWebSockets,
  ]);

  // ===== UTILITY FUNCTIONS =====

  const extractSymbolFromInstrumentKey = (instrumentKey) => {
    try {
      return instrumentKey.split("|")[1] || instrumentKey;
    } catch {
      return instrumentKey;
    }
  };

  const triggerStockSelection = async () => {
    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/api/trigger-stock-selection`
      );

      if (response.data.success) {
        console.log("✅ Stock selection triggered manually");

        // Refresh selected stocks after a delay
        setTimeout(async () => {
          const res = await axios.get(
            `${process.env.REACT_APP_API_URL}/api/selected-stocks/today`
          );
          setSelectedStocks(res.data?.selectedStocks || []);
        }, 5000);
      }
    } catch (error) {
      console.error("❌ Failed to trigger stock selection:", error);
    }
  };

  // NEW: Get system health and status
  const getSystemHealth = useCallback(async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/health`
      );
      return response.data;
    } catch (error) {
      console.error("❌ Failed to get system health:", error);
      return null;
    }
  }, []);

  // NEW: Force reconnection
  const forceReconnect = useCallback(() => {
    console.log("🔄 Force reconnecting...");
    reconnectAttempts.current = 0;
    disconnectAllWebSockets();

    setTimeout(() => {
      if (systemMode === "centralized") {
        connectCentralizedDashboard();
        if (selectedStocks.length > 0) {
          connectCentralizedTrading();
        }
      } else if (systemMode === "legacy") {
        connectLegacyWebSocket();
      }
    }, 1000);
  }, [
    systemMode,
    selectedStocks,
    disconnectAllWebSockets,
    connectCentralizedDashboard,
    connectCentralizedTrading,
    connectLegacyWebSocket,
  ]);

  // ===== CONTEXT VALUE =====
  const contextValue = {
    // KEEP: Essential existing values
    groupedStocks,
    ltps,
    marketStatus,
    tokenExpired,
    resetTokenExpired,

    // ENHANCED: System management
    selectedStocks,
    tradingData,
    systemMode,
    connectionStatus,
    systemCapabilities,
    dataMetrics,

    // NEW: Mode switching functions
    switchToCentralizedMode,
    switchToLegacyMode,
    switchToAutoMode,

    // NEW: Utility functions
    triggerStockSelection,
    getSystemHealth,
    forceReconnect,
    detectSystemCapabilities,

    // NEW: Setters for advanced use
    setSelectedStocks,
    setSystemMode,
  };

  return (
    <MarketContext.Provider value={contextValue}>
      {children}
    </MarketContext.Provider>
  );
};

export default MarketProvider;
