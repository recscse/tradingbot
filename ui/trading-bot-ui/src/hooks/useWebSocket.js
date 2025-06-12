import { useEffect, useRef } from "react";
import { useNotifications } from "../contexts/NotificationContext";

export const useWebSocket = (url, options = {}) => {
  const ws = useRef(null);
  const { addNotification } = useNotifications();
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log("WebSocket connected");
        reconnectAttempts.current = 0;
        options.onOpen?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle different message types
          switch (data.type) {
            case "notification":
              addNotification(data.payload);
              break;
            case "trade_update":
              // Handle trade updates
              options.onTradeUpdate?.(data.payload);
              break;
            case "market_data":
              // Handle market data updates
              options.onMarketData?.(data.payload);
              break;
            default:
              options.onMessage?.(data);
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        options.onError?.(error);
      };

      ws.current.onclose = (event) => {
        console.log("WebSocket disconnected:", event.code, event.reason);

        // Attempt to reconnect if not intentionally closed
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          reconnectAttempts.current++;
          const timeout = Math.pow(2, reconnectAttempts.current) * 1000; // Exponential backoff

          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(
              `Attempting to reconnect... (${reconnectAttempts.current}/${maxReconnectAttempts})`
            );
            connect();
          }, timeout);
        }

        options.onClose?.(event);
      };
    } catch (error) {
      console.error("Error creating WebSocket connection:", error);
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (ws.current) {
      ws.current.close(1000, "Component unmounting");
    }
  };

  const sendMessage = (message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket is not connected");
    }
  };

  useEffect(() => {
    connect();
    return disconnect;
  }, [url]);

  return {
    sendMessage,
    disconnect,
    readyState: ws.current?.readyState,
  };
};
