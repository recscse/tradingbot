// hooks/useMarketWebSocket.js
import { useState, useEffect, useCallback, useRef } from "react";

export const useMarketWebSocket = (channels = [], autoConnect = true) => {
  const [wsStatus, setWsStatus] = useState("disconnected");
  const [marketData, setMarketData] = useState({});
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const ws = useRef(null);
  const reconnectTimeout = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Message handlers
  const messageHandlers = useRef({
    indices: (data) => setMarketData((prev) => ({ ...prev, indices: data })),
    top_gainers: (data) =>
      setMarketData((prev) => ({ ...prev, topGainers: data })),
    top_losers: (data) =>
      setMarketData((prev) => ({ ...prev, topLosers: data })),
    gap_up: (data) => setMarketData((prev) => ({ ...prev, gapUp: data })),
    gap_down: (data) => setMarketData((prev) => ({ ...prev, gapDown: data })),
    intraday_boosters: (data) =>
      setMarketData((prev) => ({ ...prev, intradayBoosters: data })),
    mcx_futures: (data) =>
      setMarketData((prev) => ({ ...prev, mcxFutures: data })),
    nifty_stocks: (data) =>
      setMarketData((prev) => ({ ...prev, niftyStocks: data })),
    bank_nifty_stocks: (data) =>
      setMarketData((prev) => ({ ...prev, bankNiftyStocks: data })),
    fno_stocks: (data) =>
      setMarketData((prev) => ({ ...prev, fnoStocks: data })),
    options_call: (data) =>
      setMarketData((prev) => ({ ...prev, optionsCall: data })),
    options_put: (data) =>
      setMarketData((prev) => ({ ...prev, optionsPut: data })),
  });

  // Transform API data to consistent format
  const transformData = useCallback((rawData) => {
    if (!rawData) return [];

    return rawData.map((item) => ({
      symbol: item.symbol || item.trading_symbol,
      instrument_key: item.instrument_key,
      last_price: item.last_price || item.ltp,
      change: item.change,
      change_percent: item.change_percent,
      volume: item.volume,
      market_cap: item.market_cap,
      sector: item.sector,
      high: item.high,
      low: item.low,
      open: item.open,
      prev_close: item.prev_close || item.cp,
    }));
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      setWsStatus("connecting");
      setError(null);

      const wsUrl =
        process.env.REACT_APP_WS_URL ||
        `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${
          window.location.hostname
        }:8000/ws/market-data`;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setWsStatus("connected");
        reconnectAttempts.current = 0;

        // Subscribe to channels
        if (channels.length > 0) {
          const subscribeMessage = {
            type: "subscribe",
            channels: channels,
          };
          ws.current.send(JSON.stringify(subscribeMessage));
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          switch (message.type) {
            case "market_data":
              const { channel, data } = message;
              const handler = messageHandlers.current[channel];
              if (handler && data) {
                handler(transformData(data));
                setLastUpdate(new Date());
              }
              break;

            case "bulk_update":
              // Handle bulk updates for multiple channels
              if (message.data) {
                Object.keys(message.data).forEach((channel) => {
                  const handler = messageHandlers.current[channel];
                  if (handler) {
                    handler(transformData(message.data[channel]));
                  }
                });
                setLastUpdate(new Date());
              }
              break;

            case "error":
              setError(message.message || "WebSocket error");
              break;

            default:
              console.log("Unknown message type:", message.type);
          }
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
          setError("Failed to parse server message");
        }
      };

      ws.current.onclose = (event) => {
        setWsStatus("disconnected");

        // Only auto-reconnect if it wasn't a manual close
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts &&
          autoConnect
        ) {
          reconnectAttempts.current++;
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            30000
          );

          reconnectTimeout.current = setTimeout(() => {
            console.log(`Reconnecting... Attempt ${reconnectAttempts.current}`);
            connect();
          }, delay);
        }
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        setWsStatus("error");
        setError("Connection failed");
      };
    } catch (err) {
      console.error("Error creating WebSocket connection:", err);
      setWsStatus("error");
      setError("Failed to create connection");
    }
  }, [channels, autoConnect, transformData]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (ws.current) {
      ws.current.close(1000, "Manual disconnect");
      ws.current = null;
    }

    setWsStatus("disconnected");
  }, []);

  // Send message to WebSocket
  const sendMessage = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // Subscribe to additional channels
  const subscribe = useCallback(
    (newChannels) => {
      const subscribeMessage = {
        type: "subscribe",
        channels: Array.isArray(newChannels) ? newChannels : [newChannels],
      };
      return sendMessage(subscribeMessage);
    },
    [sendMessage]
  );

  // Unsubscribe from channels
  const unsubscribe = useCallback(
    (channelsToRemove) => {
      const unsubscribeMessage = {
        type: "unsubscribe",
        channels: Array.isArray(channelsToRemove)
          ? channelsToRemove
          : [channelsToRemove],
      };
      return sendMessage(unsubscribeMessage);
    },
    [sendMessage]
  );

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [connect, disconnect, autoConnect]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, []);

  return {
    // Connection state
    wsStatus,
    isConnected: wsStatus === "connected",
    error,

    // Data
    marketData,
    lastUpdate,

    // Methods
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,

    // Stats
    reconnectAttempts: reconnectAttempts.current,
  };
};
