import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
} from "react";
import axios from "axios";
import { getSocket } from "../utils/socket";

const MarketContext = createContext();
export const useMarket = () => useContext(MarketContext);

// 🔄 Global WebSocket instances
let globalWs = null; // KEEP: Your existing WebSocket
let dashboardWs = null; // NEW: Dashboard LTP WebSocket
let tradingWs = null; // NEW: Trading focused WebSocket
let globalPingInterval = null;

export const MarketProvider = ({ children }) => {
  // KEEP: All your existing state
  const [groupedStocks, setGroupedStocks] = useState({});
  const [ltps, setLtps] = useState({});
  const [marketStatus, setMarketStatus] = useState("loading");
  const [tokenExpired, setTokenExpired] = useState(false);

  // NEW: Add minimal new state for hybrid system
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [tradingData, setTradingData] = useState({});
  const [systemMode, setSystemMode] = useState("legacy"); // "legacy" or "hybrid"
  const [connectionStatus, setConnectionStatus] = useState({
    legacy: "disconnected",
    dashboard: "disconnected",
    trading: "disconnected",
  });

  // KEEP: Your existing refs
  const connectingRef = useRef(false);
  const hasReceivedFeed = useRef(false);
  const reconnectTimeoutRef = useRef(null);

  // KEEP: Your existing function, enhanced for new WebSockets
  const resetTokenExpired = () => {
    setTokenExpired(false);
  };

  // ENHANCED: Your existing function to handle all WebSockets
  const disconnectWebSocket = () => {
    if (globalWs) globalWs.close();
    if (dashboardWs) dashboardWs.close();
    if (tradingWs) tradingWs.close();
    if (globalPingInterval) clearInterval(globalPingInterval);
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

    globalWs = null;
    dashboardWs = null;
    tradingWs = null;
    globalPingInterval = null;
    reconnectTimeoutRef.current = null;
    connectingRef.current = false;
    hasReceivedFeed.current = false;
  };

  // NEW: Add function to switch modes
  const switchToHybridMode = () => {
    console.log("🔄 Switching to hybrid mode...");
    disconnectWebSocket();
    setSystemMode("hybrid");
    setConnectionStatus({
      legacy: "disconnected",
      dashboard: "disconnected",
      trading: "disconnected",
    });
  };

  const switchToLegacyMode = () => {
    console.log("🔄 Switching to legacy mode...");
    disconnectWebSocket();
    setSystemMode("legacy");
    setConnectionStatus({
      legacy: "disconnected",
      dashboard: "disconnected",
      trading: "disconnected",
    });
  };

  // NEW: Fetch selected stocks for trading
  useEffect(() => {
    const fetchSelectedStocks = async () => {
      try {
        const res = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/selected-stocks/today`
        );
        const stocks = res.data?.selectedStocks || [];
        setSelectedStocks(stocks);
        console.log(`📊 Loaded ${stocks.length} selected stocks for trading`);
      } catch (err) {
        console.error("❌ Failed to fetch selected stocks:", err);
      }
    };

    fetchSelectedStocks();

    // Refresh every 5 minutes
    const interval = setInterval(fetchSelectedStocks, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // KEEP: Your existing stock fetching logic - UNCHANGED
  useEffect(() => {
    const fetchGrouped = async () => {
      try {
        const res = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/stocks/top`
        );
        const stocks = res.data?.data || {};
        setGroupedStocks(stocks);
      } catch (err) {
        console.error("❌ Failed to fetch stock groups:", err);
      }
    };

    fetchGrouped();
  }, []);

  // KEEP: Your existing WebSocket logic - UNCHANGED (for legacy mode)
  useEffect(() => {
    if (
      Object.keys(groupedStocks).length === 0 ||
      globalWs ||
      connectingRef.current ||
      systemMode === "hybrid" // NEW: Skip if in hybrid mode
    )
      return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    const wsUrl = `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/ws/market?token=${token}`;
    const ws = getSocket(wsUrl);
    globalWs = ws;
    connectingRef.current = true;

    ws.onopen = () => {
      connectingRef.current = false;
      setConnectionStatus((prev) => ({ ...prev, legacy: "connected" }));
      globalPingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);

      console.info("✅ WebSocket connected. Backend handles subscriptions.");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "error" && msg.reason === "token_expired") {
          setTokenExpired(true);
          console.log("❌ Token expired notification received");
          disconnectWebSocket();
          return;
        }

        if (msg.type === "market_info") {
          const status = msg.marketStatus?.toLowerCase() || "closed";
          setMarketStatus(status);
        }

        if (msg.type === "live_feed" && msg.data) {
          hasReceivedFeed.current = true;
          const feeds = msg.data;

          console.log("📡 Received live data for:", Object.keys(feeds));

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
                  data_source: "LEGACY_WS", // NEW: Add data source
                };
              }
            });
            return updates;
          });
        }
      } catch (e) {
        console.error("⚠️ WebSocket parse error:", e);
      }
    };

    ws.onclose = () => {
      console.warn("❌ WebSocket closed");
      setConnectionStatus((prev) => ({ ...prev, legacy: "disconnected" }));
      disconnectWebSocket();
    };

    ws.onerror = (err) => {
      console.error("💥 WebSocket error:", err);
      disconnectWebSocket();
    };
  }, [groupedStocks, systemMode]);

  // NEW: Dashboard WebSocket for hybrid mode (LTP API polling)
  useEffect(() => {
    if (
      Object.keys(groupedStocks).length === 0 ||
      dashboardWs ||
      connectingRef.current ||
      systemMode === "legacy"
    )
      return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    console.log("🚀 Starting dashboard WebSocket with LTP API...");

    const wsUrl = `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/ws/dashboard?token=${token}`;

    dashboardWs = new WebSocket(wsUrl);
    connectingRef.current = true;

    dashboardWs.onopen = () => {
      connectingRef.current = false;
      setConnectionStatus((prev) => ({ ...prev, dashboard: "connected" }));
      console.info("✅ Dashboard WebSocket connected (LTP API)");
    };

    dashboardWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "error" && msg.reason === "token_expired") {
          setTokenExpired(true);
          console.log("❌ Dashboard token expired");
          disconnectWebSocket();
          return;
        }

        if (msg.type === "dashboard_update" && msg.data) {
          hasReceivedFeed.current = true;
          const feeds = msg.data;

          console.log(
            "📊 Received dashboard LTP data:",
            feeds.length,
            "stocks"
          );

          setLtps((prev) => {
            const updates = { ...prev };
            feeds.forEach((stock) => {
              if (stock?.ltp !== undefined) {
                const key = stock.instrument_key.toUpperCase();
                updates[key] = {
                  ltp: stock.ltp,
                  cp: stock.change + stock.ltp, // Derived previous close
                  change: stock.change,
                  change_percent: stock.change_percent,
                  symbol: stock.symbol,
                  timestamp: stock.timestamp,
                  data_source: "LTP_API",
                };
              }
            });
            return updates;
          });
        }
      } catch (e) {
        console.error("⚠️ Dashboard WebSocket parse error:", e);
      }
    };

    dashboardWs.onclose = () => {
      console.warn("❌ Dashboard WebSocket closed");
      setConnectionStatus((prev) => ({ ...prev, dashboard: "disconnected" }));
    };

    dashboardWs.onerror = (err) => {
      console.error("💥 Dashboard WebSocket error:", err);
      setConnectionStatus((prev) => ({ ...prev, dashboard: "disconnected" }));
    };

    return () => {
      if (dashboardWs) {
        dashboardWs.close();
        dashboardWs = null;
      }
    };
  }, [groupedStocks, systemMode]);

  // NEW: Trading WebSocket for hybrid mode (focused on selected stocks)
  useEffect(() => {
    if (selectedStocks.length === 0 || tradingWs || systemMode === "legacy")
      return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    console.log(
      `🎯 Starting trading WebSocket for ${selectedStocks.length} selected stocks...`
    );

    const wsUrl = `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/ws/trading?token=${token}`;

    tradingWs = new WebSocket(wsUrl);

    tradingWs.onopen = () => {
      setConnectionStatus((prev) => ({ ...prev, trading: "connected" }));
      console.info("✅ Trading WebSocket connected (Focused)");
    };

    tradingWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "error" && msg.reason === "token_expired") {
          setTokenExpired(true);
          console.log("❌ Trading token expired");
          return;
        }

        if (msg.type === "trading_update" && msg.data) {
          console.log(
            "🎯 Received trading data:",
            msg.instruments_count,
            "instruments"
          );

          setTradingData((prev) => {
            const updates = { ...prev };

            // Handle trading data format
            if (msg.data.data && msg.data.data.feeds) {
              Object.entries(msg.data.data.feeds).forEach(
                ([instrumentKey, feedData]) => {
                  const symbol = extractSymbolFromInstrumentKey(instrumentKey);
                  if (!updates[symbol]) {
                    updates[symbol] = { instruments: {} };
                  }

                  updates[symbol].instruments[instrumentKey] = {
                    ...feedData,
                    timestamp: msg.timestamp,
                    data_source: "TRADING_WS",
                  };
                }
              );
            }

            return updates;
          });
        }
      } catch (e) {
        console.error("⚠️ Trading WebSocket parse error:", e);
      }
    };

    tradingWs.onclose = () => {
      console.warn("❌ Trading WebSocket closed");
      setConnectionStatus((prev) => ({ ...prev, trading: "disconnected" }));
    };

    tradingWs.onerror = (err) => {
      console.error("💥 Trading WebSocket error:", err);
      setConnectionStatus((prev) => ({ ...prev, trading: "disconnected" }));
    };

    return () => {
      if (tradingWs) {
        tradingWs.close();
        tradingWs = null;
      }
    };
  }, [selectedStocks, systemMode]);

  // Helper function
  const extractSymbolFromInstrumentKey = (instrumentKey) => {
    try {
      return instrumentKey.split("|")[1] || instrumentKey;
    } catch {
      return instrumentKey;
    }
  };

  // NEW: Manual trigger for stock selection
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

  return (
    <MarketContext.Provider
      value={{
        // KEEP: All your existing values
        groupedStocks,
        ltps,
        marketStatus,
        tokenExpired,
        resetTokenExpired,

        // NEW: Add new values for hybrid system
        selectedStocks,
        tradingData,
        systemMode,
        connectionStatus,
        switchToHybridMode,
        switchToLegacyMode,
        triggerStockSelection,
        setSelectedStocks,
      }}
    >
      {children}
    </MarketContext.Provider>
  );
};

export default MarketProvider;
	