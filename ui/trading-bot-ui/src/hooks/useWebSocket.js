// Custom React Hook for WebSocket connections
// File: hooks/useWebSocket.js

import { useState, useEffect, useRef, useCallback } from "react";

export const useWebSocket = (url, options = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [connectionState, setConnectionState] = useState("CONNECTING"); // CONNECTING, CONNECTED, DISCONNECTED, ERROR
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const messageQueueRef = useRef([]);

  const {
    onOpen,
    onMessage,
    onClose,
    onError,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    debug = false,
  } = options;

  const log = useCallback(
    (message) => {
      if (debug) {
        console.log(`[WebSocket] ${message}`);
      }
    },
    [debug]
  );

  const connect = useCallback(() => {
    try {
      setConnectionState("CONNECTING");
      socketRef.current = new WebSocket(url);

      socketRef.current.onopen = (event) => {
        log("Connection opened");
        setIsConnected(true);
        setConnectionState("CONNECTED");

        // Send any queued messages
        while (messageQueueRef.current.length > 0) {
          const message = messageQueueRef.current.shift();
          socketRef.current.send(message);
        }

        if (onOpen) onOpen(event);
      };

      socketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          if (onMessage) onMessage(data);
        } catch (error) {
          log(`Error parsing message: ${error.message}`);
          setLastMessage({ raw: event.data });
          if (onMessage) onMessage({ raw: event.data });
        }
      };

      socketRef.current.onclose = (event) => {
        log(`Connection closed: ${event.code} - ${event.reason}`);
        setIsConnected(false);
        setConnectionState("DISCONNECTED");

        if (onClose) onClose(event);

        // Auto-reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttempts > 0) {
          log(`Reconnecting in ${reconnectInterval}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      socketRef.current.onerror = (error) => {
        log(`Connection error: ${error}`);
        setConnectionState("ERROR");
        if (onError) onError(error);
      };
    } catch (error) {
      log(`Failed to create WebSocket: ${error.message}`);
      setConnectionState("ERROR");
    }
  }, [
    url,
    onOpen,
    onMessage,
    onClose,
    onError,
    reconnectAttempts,
    reconnectInterval,
    log,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (socketRef.current) {
      socketRef.current.close(1000, "Manual disconnect");
    }
  }, []);

  const sendMessage = useCallback(
    (message) => {
      const messageStr =
        typeof message === "string" ? message : JSON.stringify(message);

      if (
        socketRef.current &&
        socketRef.current.readyState === WebSocket.OPEN
      ) {
        socketRef.current.send(messageStr);
        log(`Message sent: ${messageStr}`);
      } else {
        // Queue message for when connection is established
        messageQueueRef.current.push(messageStr);
        log(`Message queued: ${messageStr}`);
      }
    },
    [log]
  );

  // Auto-connect on mount
  useEffect(() => {
    connect();

    // Setup heartbeat
    const heartbeatTimer = setInterval(() => {
      if (isConnected) {
        sendMessage({ type: "ping" });
      }
    }, heartbeatInterval);

    return () => {
      clearInterval(heartbeatTimer);
      disconnect();
    };
  }, [connect, disconnect, isConnected, sendMessage, heartbeatInterval]);

  return {
    isConnected,
    connectionState,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
};

// Specialized hook for Scanner & Signal WebSocket
export const useScannerSignalWebSocket = () => {
  const [scannerData, setScannerData] = useState({});
  const [signalData, setSignalData] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({});

  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case "scanner_results":
      case "scanner_update":
        setScannerData(data.data || {});
        break;

      case "trading_signals":
      case "signal_update":
        setSignalData(data.signals || []);

        // Create notifications for high-confidence signals
        if (data.signals) {
          const highConfidence = data.signals.filter((s) => s.confidence >= 80);
          if (highConfidence.length > 0) {
            addNotification(
              `${highConfidence.length} high-confidence signals detected!`,
              "success"
            );
          }
        }
        break;

      case "buy_signals":
        if (data.signals) {
          addNotification(`${data.signals.length} new BUY signals`, "buy");
        }
        break;

      case "sell_signals":
        if (data.signals) {
          addNotification(`${data.signals.length} new SELL signals`, "sell");
        }
        break;

      case "scanner_error":
      case "signal_error":
        addNotification(data.message || "An error occurred", "error");
        break;

      case "subscription_status":
        if (data.status === "subscribed") {
          addNotification(`Subscribed to ${data.type} updates`, "info");
        }
        break;

      default:
        console.log("Unknown message type:", data.type);
    }
  }, []);

  const addNotification = useCallback((message, type = "info") => {
    const notification = {
      id: Date.now() + Math.random(),
      message,
      type,
      timestamp: new Date(),
    };

    setNotifications((prev) => [notification, ...prev.slice(0, 4)]);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== notification.id));
    }, 5000);
  }, []);

  const wsUrl =
    process.env.NODE_ENV === "production"
      ? "wss://your-production-domain.com"
      : "ws://localhost:8000";

  const { isConnected, connectionState, sendMessage, connect, disconnect } =
    useWebSocket(wsUrl, {
      onMessage: handleMessage,
      onOpen: () => {
        // Subscribe to all updates on connection
        sendMessage({ type: "subscribe_to_scanner_updates" });
        sendMessage({ type: "subscribe_to_signal_updates" });

        // Request initial data
        sendMessage({ type: "get_scanner_results" });
        sendMessage({ type: "get_trading_signals" });
      },
      reconnectAttempts: 10,
      reconnectInterval: 3000,
      debug: process.env.NODE_ENV === "development",
    });

  // Methods to interact with the WebSocket
  const requestScannerResults = useCallback(() => {
    sendMessage({ type: "get_scanner_results" });
  }, [sendMessage]);

  const requestTradingSignals = useCallback(() => {
    sendMessage({ type: "get_trading_signals" });
  }, [sendMessage]);

  const subscribeToScanner = useCallback(() => {
    sendMessage({ type: "subscribe_to_scanner_updates" });
  }, [sendMessage]);

  const subscribeToSignals = useCallback(() => {
    sendMessage({ type: "subscribe_to_signal_updates" });
  }, [sendMessage]);

  const removeNotification = useCallback((notificationId) => {
    setNotifications((prev) => prev.filter((n) => n.id !== notificationId));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return {
    // Connection state
    isConnected,
    connectionState,

    // Data
    scannerData,
    signalData,
    notifications,
    stats,

    // Actions
    requestScannerResults,
    requestTradingSignals,
    subscribeToScanner,
    subscribeToSignals,
    removeNotification,
    clearAllNotifications,
    connect,
    disconnect,

    // Raw WebSocket
    sendMessage,
  };
};

// Hook for fetching REST API data
export const useScannerSignalAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const apiCall = useCallback(async (endpoint, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/scanner-signals${endpoint}`, {
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setLoading(false);

      return data;
    } catch (err) {
      setError(err.message);
      setLoading(false);
      throw err;
    }
  }, []);

  // Scanner API methods
  const getScannerStatus = useCallback(() => {
    return apiCall("/scanner/status");
  }, [apiCall]);

  const getScannerResults = useCallback(
    (scannerName = "") => {
      const endpoint = scannerName
        ? `/scanner/results/${scannerName}`
        : "/scanner/results";
      return apiCall(endpoint);
    },
    [apiCall]
  );

  const enableScanner = useCallback(
    (scannerName) => {
      return apiCall(`/scanner/${scannerName}/enable`, { method: "POST" });
    },
    [apiCall]
  );

  const disableScanner = useCallback(
    (scannerName) => {
      return apiCall(`/scanner/${scannerName}/disable`, { method: "POST" });
    },
    [apiCall]
  );

  // Signal API methods
  const getSignalStatus = useCallback(() => {
    return apiCall("/signals/status");
  }, [apiCall]);

  const getActiveSignals = useCallback(() => {
    return apiCall("/signals/active");
  }, [apiCall]);

  const getBuySignals = useCallback(() => {
    return apiCall("/signals/buy");
  }, [apiCall]);

  const getSellSignals = useCallback(() => {
    return apiCall("/signals/sell");
  }, [apiCall]);

  const generateSignals = useCallback(() => {
    return apiCall("/signals/generate");
  }, [apiCall]);

  const updateSignalParameters = useCallback(
    (params) => {
      return apiCall("/signals/parameters", {
        method: "POST",
        body: JSON.stringify(params),
      });
    },
    [apiCall]
  );

  // Dashboard API methods
  const getDashboard = useCallback(() => {
    return apiCall("/dashboard");
  }, [apiCall]);

  const getHealth = useCallback(() => {
    return apiCall("/health");
  }, [apiCall]);

  return {
    loading,
    error,

    // Scanner methods
    getScannerStatus,
    getScannerResults,
    enableScanner,
    disableScanner,

    // Signal methods
    getSignalStatus,
    getActiveSignals,
    getBuySignals,
    getSellSignals,
    generateSignals,
    updateSignalParameters,

    // Dashboard methods
    getDashboard,
    getHealth,

    // Generic API call
    apiCall,
  };
};

// Combined hook that provides both WebSocket and API functionality
export const useScannerSignals = () => {
  const webSocket = useScannerSignalWebSocket();
  const api = useScannerSignalAPI();

  return {
    ...webSocket,
    api,

    // Combined refresh method
    refreshAll: async () => {
      try {
        webSocket.requestScannerResults();
        webSocket.requestTradingSignals();

        // Also fetch via API as backup
        await api.getScannerResults();
        await api.getActiveSignals();
      } catch (error) {
        console.error("Error refreshing data:", error);
      }
    },
  };
};
