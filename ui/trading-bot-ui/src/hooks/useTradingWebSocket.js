// hooks/useTradingWebSocket.js
/**
 * React Hook for Trading WebSocket Connection
 * Real-time updates for trading data, positions, and P&L
 */

import { useState, useEffect, useCallback, useRef } from "react";

const WEBSOCKET_URL = process.env.REACT_APP_WS_URL || "ws://localhost:8000/ws/trading";

export const useTradingWebSocket = (tradingMode = "PAPER", isTrading = false) => {
  const [isConnected, setIsConnected] = useState(false);
  const [portfolioUpdate, setPortfolioUpdate] = useState(null);
  const [positionUpdate, setPositionUpdate] = useState(null);
  const [tradeUpdate, setTradeUpdate] = useState(null);
  const [priceUpdate, setPriceUpdate] = useState({});
  const [lastUpdate, setLastUpdate] = useState(null);
  const [connectionError, setConnectionError] = useState(null);

  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    try {
      // Clear any existing reconnect timeout
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }

      ws.current = new WebSocket(WEBSOCKET_URL);

      ws.current.onopen = () => {
        console.log("🔌 Trading WebSocket connected");
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;

        // Subscribe to trading events
        const subscriptionMessage = {
          action: "subscribe",
          trading_mode: tradingMode,
          events: [
            "portfolio_update",
            "position_update",
            "trade_execution",
            "price_update",
            "trading_status"
          ]
        };

        ws.current.send(JSON.stringify(subscriptionMessage));
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
          setLastUpdate(new Date().toISOString());
        } catch (error) {
          console.error("❌ Error parsing trading WebSocket message:", error);
        }
      };

      ws.current.onclose = (event) => {
        console.log("🔌 Trading WebSocket disconnected", event.code, event.reason);
        setIsConnected(false);

        // Attempt to reconnect if not intentionally closed
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`🔄 Attempting to reconnect in ${delay}ms...`);
          
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setConnectionError("Maximum reconnection attempts reached");
        }
      };

      ws.current.onerror = (error) => {
        console.error("❌ Trading WebSocket error:", error);
        setConnectionError("WebSocket connection error");
      };

    } catch (error) {
      console.error("❌ Error creating trading WebSocket connection:", error);
      setConnectionError("Failed to create WebSocket connection");
    }
  }, [tradingMode]);

  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case "portfolio_update":
        setPortfolioUpdate(data.data);
        break;
        
      case "position_update":
        setPositionUpdate(data.data);
        break;
        
      case "trade_execution":
        setTradeUpdate(data.data);
        break;
        
      case "price_update":
        setPriceUpdate(prev => ({
          ...prev,
          [data.data.symbol]: {
            price: data.data.price,
            change: data.data.change,
            changePct: data.data.changePct,
            timestamp: data.data.timestamp
          }
        }));
        break;
        
      case "trading_status":
        // Handle trading status updates
        console.log("📊 Trading status update:", data.data);
        break;
        
      case "error":
        console.error("❌ Trading WebSocket error:", data.message);
        setConnectionError(data.message);
        break;
        
      default:
        console.log("📡 Unknown trading WebSocket message type:", data.type);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.close(1000, "Manual disconnect");
    }
    
    setIsConnected(false);
    setConnectionError(null);
  }, []);

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // Subscribe to specific symbol prices
  const subscribeToSymbols = useCallback((symbols) => {
    const message = {
      action: "subscribe_symbols",
      symbols: symbols
    };
    return sendMessage(message);
  }, [sendMessage]);

  // Connect when trading is active
  useEffect(() => {
    if (isTrading) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [isTrading, connect, disconnect]);

  // Reconnect when trading mode changes
  useEffect(() => {
    if (isConnected && isTrading) {
      disconnect();
      setTimeout(connect, 1000); // Small delay before reconnecting
    }
  }, [tradingMode, isConnected, isTrading, connect, disconnect]);

  return {
    // Connection status
    isConnected,
    connectionError,
    lastUpdate,
    
    // Data updates
    portfolioUpdate,
    positionUpdate,
    tradeUpdate,
    priceUpdate,
    
    // Actions
    connect,
    disconnect,
    sendMessage,
    subscribeToSymbols,
    
    // Reset functions
    clearPortfolioUpdate: () => setPortfolioUpdate(null),
    clearPositionUpdate: () => setPositionUpdate(null),
    clearTradeUpdate: () => setTradeUpdate(null),
  };
};