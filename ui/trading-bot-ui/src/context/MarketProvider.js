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

// Single WebSocket connection
let marketWs = null;
let pingInterval = null;
let reconnectTimeout = null;

export const MarketProvider = ({ children }) => {
  const [groupedStocks, setGroupedStocks] = useState({});
  const [ltps, setLtps] = useState({});
  const [marketStatus, setMarketStatus] = useState("loading");
  const [tokenExpired, setTokenExpired] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");

  const connectingRef = useRef(false);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const resetTokenExpired = useCallback(() => {
    setTokenExpired(false);
  }, []);

  const disconnectWebSocket = useCallback(() => {
    console.log("🧹 Cleaning up WebSocket...");

    if (marketWs) {
      marketWs.close();
      marketWs = null;
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
    setConnectionStatus("disconnected");
  }, []);

  const connectWebSocket = useCallback(() => {
    if (
      marketWs ||
      connectingRef.current ||
      Object.keys(groupedStocks).length === 0
    ) {
      return;
    }

    const token = localStorage.getItem("access_token");
    if (!token) return;

    console.log("🔄 Connecting to WebSocket...");

    const wsUrl = `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/ws/market?token=${token}`;
    marketWs = getSocket(wsUrl);
    connectingRef.current = true;

    marketWs.onopen = () => {
      console.log("✅ WebSocket connected");
      connectingRef.current = false;
      reconnectAttempts.current = 0;
      setConnectionStatus("connected");

      pingInterval = setInterval(() => {
        if (marketWs?.readyState === WebSocket.OPEN) {
          marketWs.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    };

    marketWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "error" && msg.reason === "token_expired") {
          setTokenExpired(true);
          disconnectWebSocket();
          return;
        }

        if (msg.type === "market_info") {
          const status = msg.marketStatus?.toLowerCase() || "closed";
          setMarketStatus(status);
        }

        if (msg.type === "dashboard_update") {
          const updates = msg.data || {};
          console.log("📊 Dashboard update received:", updates);

          setLtps((prev) => {
            const newLtps = { ...prev };
            Object.entries(updates).forEach(([key, parsed]) => {
              if (parsed?.ltp !== undefined) {
                const isIndexKey =
                  key.startsWith("NSE_INDEX|") || key.startsWith("BSE_INDEX|");
                const finalKey = isIndexKey ? key : key.toUpperCase();
                newLtps[finalKey] = {
                  ltp: parsed.ltp,
                  cp: parsed.cp,
                  change: parsed.change,
                  change_percent: parsed.change_percent,
                  ltq: parsed.ltq,
                  last_trade_time: parsed.last_trade_time,
                  volume: parsed.volume,
                  oi: parsed.oi,
                  iv: parsed.iv,
                  atp: parsed.atp,
                  ohlc: parsed.ohlc || [],
                  bid_ask: parsed.bid_ask || [],
                  greeks: parsed.greeks || {},
                  tbq: parsed.tbq,
                  tsq: parsed.tsq,
                };
              }
            });
            console.log("📈 Dashboard updated:", newLtps);
            return newLtps;
          });
        }

        if (msg.type === "live_feed" && msg.data) {
          setLtps((prev) => {
            const updates = { ...prev };

            Object.entries(msg.data).forEach(([key, parsed]) => {
              if (parsed?.ltp !== undefined) {
                const isIndexKey =
                  key.startsWith("NSE_INDEX|") || key.startsWith("BSE_INDEX|");
                const finalKey = isIndexKey ? key : key.toUpperCase();

                updates[finalKey] = {
                  ltp: parsed.ltp,
                  cp: parsed.cp,
                  change: parsed.change,
                  change_percent: parsed.change_percent,
                  ltq: parsed.ltq,
                  last_trade_time: parsed.last_trade_time,
                  volume: parsed.volume,
                  oi: parsed.oi,
                  iv: parsed.iv,
                  atp: parsed.atp,
                  ohlc: parsed.ohlc || [],
                  bid_ask: parsed.bid_ask || [],
                  greeks: parsed.greeks || {},
                  tbq: parsed.tbq,
                  tsq: parsed.tsq,
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

    marketWs.onclose = () => {
      console.warn("❌ WebSocket closed");
      setConnectionStatus("disconnected");

      if (reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current += 1;
        const delay = Math.min(
          1000 * Math.pow(2, reconnectAttempts.current),
          30000
        );

        console.log(
          `🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`
        );

        reconnectTimeout = setTimeout(() => {
          connectWebSocket();
        }, delay);
      }
    };

    marketWs.onerror = (error) => {
      console.error("💥 WebSocket error:", error);
      setConnectionStatus("error");
    };
  }, [groupedStocks, disconnectWebSocket]);

  // Fetch stock groups
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

  // Connect when stocks are loaded
  useEffect(() => {
    if (Object.keys(groupedStocks).length > 0) {
      connectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, [groupedStocks, connectWebSocket, disconnectWebSocket]);

  const contextValue = {
    groupedStocks,
    ltps,
    marketStatus,
    tokenExpired,
    connectionStatus,
    resetTokenExpired,
  };

  return (
    <MarketContext.Provider value={contextValue}>
      {children}
    </MarketContext.Provider>
  );
};

export default MarketProvider;
