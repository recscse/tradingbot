// // hooks/useUnifiedWebSocket.js
// /**
//  * React Hook for Unified WebSocket Connection
//  * Single WebSocket for all trading features
//  */

// import { useState, useEffect, useCallback, useRef } from "react";

// const WEBSOCKET_URL = "ws://localhost:8000/ws/unified";

// export const useUnifiedWebSocket = () => {
//   const [isConnected, setIsConnected] = useState(false);
//   const [marketData, setMarketData] = useState({});
//   const [analytics, setAnalytics] = useState({});
//   const [lastUpdate, setLastUpdate] = useState(null);

//   const ws = useRef(null);
//   const reconnectAttempts = useRef(0);
//   const maxReconnectAttempts = 5;

//   const connect = useCallback(() => {
//     try {
//       ws.current = new WebSocket(WEBSOCKET_URL);

//       ws.current.onopen = () => {
//         console.log("🔌 Unified WebSocket connected");
//         setIsConnected(true);
//         reconnectAttempts.current = 0;

//         // Subscribe to all events
//         subscribeToEvents([
//           "price_update",
//           "top_movers_update",
//           "volume_analysis_update",
//           "gap_analysis_update",
//           "breakout_analysis_update",
//           "market_sentiment_update",
//           "heatmap_update",
//           "intraday_stocks_update",
//         ]);
//       };

//       ws.current.onmessage = (event) => {
//         try {
//           const data = JSON.parse(event.data);
//           handleWebSocketMessage(data);
//         } catch (error) {
//           console.error("❌ Error parsing WebSocket message:", error);
//         }
//       };

//       ws.current.onclose = () => {
//         console.log("🔌 Unified WebSocket disconnected");
//         setIsConnected(false);

//         // Attempt reconnection
//         if (reconnectAttempts.current < maxReconnectAttempts) {
//           reconnectAttempts.current++;
//           setTimeout(() => {
//             console.log(`🔄 Reconnection attempt ${reconnectAttempts.current}`);
//             connect();
//           }, 5000 * reconnectAttempts.current);
//         }
//       };

//       ws.current.onerror = (error) => {
//         console.error("❌ WebSocket error:", error);
//       };
//     } catch (error) {
//       console.error("❌ WebSocket connection error:", error);
//     }
//   }, []);

//   const handleWebSocketMessage = useCallback((data) => {
//     setLastUpdate(new Date());

//     switch (data.type) {
//       case "price_update":
//         setMarketData((prev) => ({ ...prev, ...data.data }));
//         break;

//       case "top_movers_update":
//         setAnalytics((prev) => ({
//           ...prev,
//           topMovers: data.data,
//         }));
//         break;

//       case "volume_analysis_update":
//         setAnalytics((prev) => ({
//           ...prev,
//           volumeAnalysis: data.data,
//         }));
//         break;

//       case "gap_analysis_update":
//         setAnalytics((prev) => ({
//           ...prev,
//           gapAnalysis: data.data,
//         }));
//         break;

//       case "breakout_analysis_update":
//         setAnalytics((prev) => ({
//           ...prev,
//           breakoutAnalysis: data.data,
//         }));
//         break;

//       case "market_sentiment_update":
//         setAnalytics((prev) => ({
//           ...prev,
//           marketSentiment: data.data,
//         }));
//         break;

//       case "heatmap_update":
//         setAnalytics((prev) => ({
//           ...prev,
//           heatmap: data.data,
//         }));
//         break;

//       case "intraday_stocks_update":
//         setAnalytics((prev) => ({
//           ...prev,
//           intradayStocks: data.data,
//         }));
//         break;

//       case "dashboard_data":
//         // Complete dashboard data received
//         setAnalytics(data.data);
//         break;

//       case "connection_established":
//         console.log("✅ Connection established:", data.client_id);
//         break;

//       case "error":
//         console.error("❌ WebSocket error:", data.message);
//         break;

//       default:
//         console.log("📨 Unknown message type:", data.type);
//     }
//   }, []);

//   const subscribeToEvents = useCallback((events) => {
//     if (ws.current && ws.current.readyState === WebSocket.OPEN) {
//       ws.current.send(
//         JSON.stringify({
//           type: "subscribe",
//           events: events,
//         })
//       );
//     }
//   }, []);

//   const sendMessage = useCallback((message) => {
//     if (ws.current && ws.current.readyState === WebSocket.OPEN) {
//       ws.current.send(JSON.stringify(message));
//     }
//   }, []);

//   const getDashboardData = useCallback(() => {
//     sendMessage({ type: "get_dashboard_data" });
//   }, [sendMessage]);

//   const getLivePrices = useCallback(
//     (symbols = []) => {
//       sendMessage({
//         type: "get_live_prices",
//         symbols: symbols,
//       });
//     },
//     [sendMessage]
//   );

//   const getOptionsChain = useCallback(
//     (symbol) => {
//       sendMessage({
//         type: "get_options_chain",
//         symbol: symbol,
//       });
//     },
//     [sendMessage]
//   );

//   useEffect(() => {
//     connect();

//     return () => {
//       if (ws.current) {
//         ws.current.close();
//       }
//     };
//   }, [connect]);

//   return {
//     isConnected,
//     marketData,
//     analytics,
//     lastUpdate,
//     sendMessage,
//     getDashboardData,
//     getLivePrices,
//     getOptionsChain,
//     subscribeToEvents,
//   };
// };
