// hooks/useZeroDelayMarketData.js
/**
 * 🚀 ZERO-DELAY Market Data Hook (Wired to marketStore)
 *
 * - Normalizes nested feed shapes (fullFeed.marketFF.ltpc etc)
 * - Converts to store shape and batches updates to avoid spamming Zustand
 * - Updates connection status in store
 *
 * Drop-in replacement for your previous hook.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import useMarketStore from "../store/marketStore"; // adjust path if needed

const WEBSOCKET_URL = process.env.REACT_APP_API_URL
  ? `${process.env.REACT_APP_API_URL.replace(
      /^http/,
      "ws"
    )}/api/v1/realtime/stream`
  : "ws://localhost:8000/api/v1/realtime/stream";

// ---------- helpers ----------
const normalizeKey = (instKey) => {
  if (!instKey || typeof instKey !== "string") return instKey;
  if (instKey.includes("|")) return instKey.split("|")[1];
  if (instKey.includes(".")) return instKey.split(".")[0];
  return instKey;
};

const asNumber = (v, fallback = null) => {
  if (v === undefined || v === null) return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

const pickLTP = (tick) => {
  try {
    if (!tick || typeof tick !== "object") return null;
    if (tick.lp != null) return asNumber(tick.lp);
    if (tick.ltp != null) return asNumber(tick.ltp);
    if (tick.last_price != null) return asNumber(tick.last_price);

    const ff = tick.fullFeed || tick.marketFF || tick.indexFF || null;
    const marketFF = tick.fullFeed?.marketFF || tick.fullFeed?.indexFF || ff;
    if (marketFF) {
      const ltpc = marketFF?.ltpc || marketFF?.ltp || null;
      if (
        ltpc &&
        (ltpc.ltp != null || ltpc.last_price != null || ltpc.cp != null)
      ) {
        return asNumber(ltpc.ltp ?? ltpc.last_price ?? ltpc.cp);
      }
      const ohlc = marketFF?.marketOHLC?.ohlc || marketFF?.ohlc || null;
      if (Array.isArray(ohlc) && ohlc.length > 0) {
        const last = ohlc[ohlc.length - 1];
        if (last && last.close != null) return asNumber(last.close);
      }
      const bidAsk = marketFF?.marketLevel?.bidAskQuote;
      if (Array.isArray(bidAsk) && bidAsk.length > 0) {
        const first = bidAsk[0];
        if (first.askP != null) return asNumber(first.askP);
        if (first.bidP != null) return asNumber(first.bidP);
      }
    }

    if (tick.fullFeed && tick.fullFeed.ltpc && tick.fullFeed.ltpc.ltp) {
      return asNumber(tick.fullFeed.ltpc.ltp);
    }

    return null;
  } catch (e) {
    console.error("pickLTP error", e, tick);
    return null;
  }
};

const pickOpen = (tick) => {
  try {
    if (!tick) return null;
    if (tick.open != null) return asNumber(tick.open);
    if (tick.o != null) return asNumber(tick.o);
    const ff = tick.fullFeed || tick.marketFF || tick.indexFF || null;
    const ohlc = ff?.marketOHLC?.ohlc || ff?.ohlc;
    if (Array.isArray(ohlc) && ohlc.length > 0) {
      const first = ohlc[0];
      if (first && first.open != null) return asNumber(first.open);
    }
    return null;
  } catch (e) {
    return null;
  }
};

const pickVolume = (tick) => {
  try {
    if (!tick) return 0;
    if (tick.volume != null) return asNumber(tick.volume, 0);
    if (tick.vol != null) return asNumber(tick.vol, 0);
    const ff = tick.fullFeed || tick.marketFF || tick.indexFF || null;
    if (ff?.marketFF?.vtt != null) return asNumber(ff.marketFF.vtt, 0);
    if (ff?.vtt != null) return asNumber(ff.vtt, 0);
    return 0;
  } catch (e) {
    return 0;
  }
};

const pickTimestamp = (tick, providedTs) => {
  try {
    if (providedTs) return providedTs;
    if (!tick) return new Date().toISOString();
    if (tick.timestamp) return tick.timestamp;
    const ltt =
      tick.fullFeed?.marketFF?.ltpc?.ltt ||
      tick.fullFeed?.indexFF?.ltpc?.ltt ||
      tick.ltt ||
      tick.ts;
    if (ltt) {
      const n = Number(ltt);
      if (Number.isFinite(n) && n > 1e12) return new Date(n).toISOString();
      return String(ltt);
    }
    return new Date().toISOString();
  } catch (e) {
    return new Date().toISOString();
  }
};

// ---------- batching / coalescing ----------
let pendingBatch = null;
let rafScheduled = false;

const scheduleBatchPush = () => {
  if (rafScheduled) return;
  rafScheduled = true;

  const runner = () => {
    rafScheduled = false;
    if (!pendingBatch) return;
    try {
      const batchToSend = pendingBatch;
      pendingBatch = null;
      useMarketStore.getState().updatePrices(batchToSend);
      if (process.env.NODE_ENV === "development") {
        console.debug(
          "✅ Pushed batch to store count=",
          Object.keys(batchToSend).length
        );
      }
    } catch (e) {
      console.error("scheduleBatchPush error", e);
      pendingBatch = null;
    }
  };

  if (
    typeof window !== "undefined" &&
    typeof window.requestAnimationFrame === "function"
  ) {
    window.requestAnimationFrame(runner);
  } else {
    setTimeout(runner, 16);
  }
};

// ---------- hook ----------
export const useZeroDelayMarketData = (options = {}) => {
  const {
    enabled = false, // 🚀 NEW: Default to false to prevent unnecessary background connections
    autoReconnect = true,
    maxReconnectAttempts = 5,
    reconnectInterval = 3000,
    enableStats = false,
    onDataReceived = null,
    onConnectionChange = null,
    watchlist = null, // optional: array or Set of symbols to limit updates
  } = options;

  const [marketDataLocal, setMarketDataLocal] = useState({});
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [streamingStats, setStreamingStats] = useState({});
  const [latency, setLatency] = useState(null);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const lastPingRef = useRef(null);
  const WATCHSET = useRef(null);

  useEffect(() => {
    if (!watchlist) {
      WATCHSET.current = null;
    } else if (Array.isArray(watchlist)) {
      WATCHSET.current = new Set(watchlist);
    } else if (watchlist instanceof Set) {
      WATCHSET.current = watchlist;
    } else {
      WATCHSET.current = new Set([watchlist]);
    }
  }, [watchlist]);

  const convertTickToStoreShape = (instKey, tick = {}, timestamp) => {
    const symbol = normalizeKey(instKey) || tick.symbol || String(instKey);
    const ltp = pickLTP(tick);
    const open = pickOpen(tick);
    const vol = pickVolume(tick);
    const ts = pickTimestamp(tick, timestamp);

    return {
      symbol,
      instrument_key: instKey,
      ltp: ltp != null ? ltp : 0,
      open: open != null ? open : 0,
      high: asNumber(tick?.high, 0),
      low: asNumber(tick?.low, 0),
      volume: vol != null ? vol : 0,
      change: asNumber(
        tick?.change,
        ltp != null && open != null ? ltp - open : 0
      ),
      change_percent: asNumber(tick?.change_percent, 0),
      timestamp: ts,
      raw: tick,
      last_updated: Date.now(),
    };
  };

  const calculateLatency = useCallback((timestamp) => {
    if (timestamp) {
      try {
        const serverTime = new Date(timestamp).getTime();
        if (!Number.isFinite(serverTime)) return null;
        const latencyMs = Date.now() - serverTime;
        setLatency(latencyMs);
        return latencyMs;
      } catch (e) {
        return null;
      }
    }
    return null;
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      setConnectionStatus("connecting");
      setError(null);

      wsRef.current = new WebSocket(WEBSOCKET_URL);

      wsRef.current.onopen = () => {
        console.log("✅ ZERO-DELAY WebSocket connected");
        setConnectionStatus("connected");
        reconnectAttemptsRef.current = 0;
        useMarketStore.getState().setConnectionStatus("connected");

        if (wsRef.current.readyState === WebSocket.OPEN) {
          lastPingRef.current = Date.now();
          wsRef.current.send(
            JSON.stringify({
              type: "ping",
              timestamp: new Date().toISOString(),
            })
          );
        }

        if (onConnectionChange) onConnectionChange("connected");
      };

      wsRef.current.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);
          const messageType =
            raw.type || raw.messageType || "live_price_update";
          const timestamp = raw.timestamp || new Date().toISOString();

          if (messageType === "connection_established") {
            setStreamingStats(raw.streaming_stats || {});
            return;
          }

          if (messageType === "pong") {
            if (lastPingRef.current) {
              const rtt = Date.now() - lastPingRef.current;
              setLatency(rtt);
              console.debug("🏓 WebSocket latency (rtt):", rtt);
            }
            return;
          }

          if (messageType === "streaming_stats") {
            setStreamingStats(raw.data || raw.streaming_stats || {});
            return;
          }

          // MAIN: live_price_update
          if (
            messageType === "live_price_update" ||
            messageType === "live_pric" ||
            !raw.type
          ) {
            const latencyMs = calculateLatency(timestamp);

            const feedMap = raw.data || raw.feeds || raw.payload || raw || {};
            if (!feedMap || typeof feedMap !== "object") return;

            const converted = {};
            const keys = Object.keys(feedMap);
            for (let i = 0; i < keys.length; i++) {
              const instKey = keys[i];
              try {
                const wrapper = feedMap[instKey];
                const tick =
                  wrapper && wrapper.fullFeed ? wrapper.fullFeed : wrapper;
                const symbol =
                  normalizeKey(instKey) || tick?.symbol || String(instKey);

                if (WATCHSET.current && !WATCHSET.current.has(symbol)) continue;

                const storeTick = convertTickToStoreShape(
                  instKey,
                  tick,
                  timestamp
                );
                if (latencyMs != null) storeTick.__latency = latencyMs;

                converted[storeTick.symbol] = storeTick;
              } catch (e) {
                console.error("Error converting tick for", instKey, e);
                continue;
              }
            }

            if (Object.keys(converted).length > 0) {
              if (!pendingBatch) pendingBatch = {};
              Object.assign(pendingBatch, converted);

              if (Object.keys(pendingBatch).length > 1000) {
                const toSend = pendingBatch;
                pendingBatch = null;
                useMarketStore.getState().updatePrices(toSend);
                if (process.env.NODE_ENV === "development") {
                  console.debug(
                    "Flushed large batch immediate count=",
                    Object.keys(toSend).length
                  );
                }
              } else {
                scheduleBatchPush();
              }

              setMarketDataLocal((prev) => ({ ...prev, ...converted }));
              if (latencyMs != null) setLatency(latencyMs);
              setStreamingStats((prev) => ({ ...prev, lastTickAt: timestamp }));
            }

            if (onDataReceived) {
              try {
                onDataReceived({
                  data: feedMap,
                  timestamp,
                  latency: latencyMs,
                  source: "zero_delay",
                });
              } catch (e) {
                console.error("onDataReceived error", e);
              }
            }
          }
        } catch (e) {
          console.error(
            "❌ Error parsing WS message in useZeroDelayMarketData:",
            e,
            event.data
          );
        }
      };

      wsRef.current.onclose = (ev) => {
        console.log("🔗 ZERO-DELAY WebSocket closed", ev?.code, ev?.reason);
        setConnectionStatus("disconnected");
        useMarketStore.getState().setConnectionStatus("disconnected");

        if (onConnectionChange) onConnectionChange("disconnected");

        if (
          autoReconnect &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(
            () => connect(),
            reconnectInterval
          );
          console.log(
            `🔄 Reconnect attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts} scheduled`
          );
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError("Maximum reconnection attempts reached");
          console.error("❌ Maximum reconnection attempts reached");
        }
      };

      wsRef.current.onerror = (err) => {
        console.error("❌ ZERO-DELAY WebSocket error:", err);
        setError("WebSocket connection error");
        setConnectionStatus("error");
        useMarketStore.getState().setConnectionStatus("error");
      };
    } catch (error) {
      console.error("❌ Failed to create ZERO-DELAY WebSocket:", error);
      setError(error?.message || "ws_create_error");
      setConnectionStatus("error");
      useMarketStore.getState().setConnectionStatus("error");
    }
  }, [
    autoReconnect,
    maxReconnectAttempts,
    reconnectInterval,
    onConnectionChange,
    onDataReceived,
    calculateLatency,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {
        /* ignore */
      }
      wsRef.current = null;
    }
    setConnectionStatus("disconnected");
    useMarketStore.getState().setConnectionStatus("disconnected");
    console.log("🔌 ZERO-DELAY WebSocket disconnected");
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message));
        return true;
      } catch (e) {
        console.error("sendMessage error", e);
        return false;
      }
    }
    console.warn("⚠️ Cannot send message: WebSocket not connected");
    return false;
  }, []);

  const requestStats = useCallback(() => {
    return sendMessage({ type: "get_stats" });
  }, [sendMessage]);

  const ping = useCallback(() => {
    lastPingRef.current = Date.now();
    return sendMessage({ type: "ping", timestamp: new Date().toISOString() });
  }, [sendMessage]);

  // Auto-connect on mount (if enabled)
  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, connect, disconnect]);

  // Periodic stats requests
  useEffect(() => {
    if (!enableStats || connectionStatus !== "connected") return;
    const statsInterval = setInterval(() => requestStats(), 10000);
    return () => clearInterval(statsInterval);
  }, [enableStats, connectionStatus, requestStats]);

  // Periodic ping for latency measurement
  useEffect(() => {
    if (connectionStatus !== "connected") return;
    const pingInterval = setInterval(() => ping(), 5000);
    return () => clearInterval(pingInterval);
  }, [connectionStatus, ping]);

  return {
    marketData: marketDataLocal,
    connectionStatus,
    streamingStats,
    latency,
    error,

    connect,
    disconnect,
    sendMessage,
    requestStats,
    ping,

    isConnected: connectionStatus === "connected",
    isConnecting: connectionStatus === "connecting",
    hasError: !!error,
    totalInstruments: Object.keys(marketDataLocal).length,
    lastUpdate: marketDataLocal._lastUpdate,
    dataSource: "zero_delay",
  };
};

export default useZeroDelayMarketData;
