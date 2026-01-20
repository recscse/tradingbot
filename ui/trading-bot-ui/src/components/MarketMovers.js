import React, { useState, useEffect, useRef, useCallback } from "react";

function TopGainersLosers() {
  // Separate states for different data segments
  const [topGainers, setTopGainers] = useState([]);
  const [topLosers, setTopLosers] = useState([]);
  const [summary, setSummary] = useState({ total_gainers: 0, total_losers: 0 });
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsStatus, setWsStatus] = useState("disconnected");

  // Use refs for data that doesn't need to trigger re-renders
  const socketRef = useRef(null);
  const mountedRef = useRef(true);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const heartbeatInterval = useRef(null);

  // Bloomberg-style color scheme
  const bloombergColors = {
    background: "#0f0f12",
    text: "#e6e6e6",
    positive: "#00ff00",
    negative: "#ff0000",
    neutral: "#ffff00",
    header: "#00b0f0",
    border: "#333333",
    tableHeader: "#1a1a1a",
    tableRowEven: "#141414",
    tableRowOdd: "#1a1a1a",
    cardBackground: "#1a1a1a",
  };

  // WebSocket message handlers
  const handleWebSocketMessage = (data) => {
    try {
      const message = JSON.parse(data);
      console.log("📊 Received WebSocket message:", message.type);

      setUpdatedAt(new Date(message.timestamp));

      switch (message.type) {
        case "initial_data":
          // Handle comprehensive initial data
          if (message.data.top_movers) {
            setTopGainers(message.data.top_movers.gainers || []);
            setTopLosers(message.data.top_movers.losers || []);
            setSummary({
              total_gainers: message.data.top_movers.gainers?.length || 0,
              total_losers: message.data.top_movers.losers?.length || 0,
            });
          }
          setLoading(false);
          break;

        case "top_movers_data":
        case "top_movers_update":
          if (message.data.gainers) setTopGainers(message.data.gainers);
          if (message.data.losers) setTopLosers(message.data.losers);
          if (message.data.gainers || message.data.losers) {
            setSummary({
              total_gainers: message.data.gainers?.length || topGainers.length,
              total_losers: message.data.losers?.length || topLosers.length,
            });
          }
          break;

        case "periodic_update":
          // Handle periodic updates
          if (message.data.top_movers) {
            setTopGainers(message.data.top_movers.gainers || []);
            setTopLosers(message.data.top_movers.losers || []);
            setSummary({
              total_gainers: message.data.top_movers.gainers?.length || 0,
              total_losers: message.data.top_movers.losers?.length || 0,
            });
          }
          break;

        case "subscription_confirmed":
          console.log("✅ Subscription confirmed:", message.subscriptions);
          break;

        case "pong":
          // Heartbeat response
          console.log("💓 Heartbeat response received");
          break;

        case "error":
          console.error("❌ WebSocket error:", message.message);
          setError(message.message);
          break;

        default:
          console.log("📊 Unknown message type:", message.type);
      }
    } catch (error) {
      console.error("❌ Error parsing WebSocket message:", error);
    }
  };

  // Send WebSocket message
  const sendWebSocketMessage = (message) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  };

  // Initialize WebSocket connection
  const initializeWebSocket = () => {
    try {
      const wsUrl = `${
        process.env.REACT_APP_WS_URL || "ws://localhost:8000"
      }/ws/market-analytics`;
      console.log("📊 Connecting to WebSocket:", wsUrl);

      socketRef.current = new WebSocket(wsUrl);

      socketRef.current.onopen = () => {
        console.log("✅ WebSocket connected");
        setWsStatus("connected");
        setError(null);
        reconnectAttempts.current = 0;

        // Subscribe to updates
        sendWebSocketMessage({
          type: "subscribe",
          types: ["top_movers"],
          interval: 30,
        });

        // Start heartbeat
        heartbeatInterval.current = setInterval(() => {
          sendWebSocketMessage({ type: "ping" });
        }, 30000);
      };

      socketRef.current.onmessage = (event) => {
        handleWebSocketMessage(event.data);
      };

      socketRef.current.onclose = (event) => {
        console.log("📊 WebSocket disconnected:", event.code, event.reason);
        setWsStatus("disconnected");

        // Clear heartbeat
        if (heartbeatInterval.current) {
          clearInterval(heartbeatInterval.current);
          heartbeatInterval.current = null;
        }

        // Attempt reconnection if not intentional close
        if (
          event.code !== 1000 &&
          mountedRef.current &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            10000
          );
          setWsStatus("connecting");

          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              reconnectAttempts.current++;
              initializeWebSocket();
            }
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError(
            "Connection failed after multiple attempts. Please refresh the page."
          );
          setWsStatus("error");
        }
      };

      socketRef.current.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        setError("WebSocket connection error");
        setWsStatus("error");
      };
    } catch (error) {
      console.error("❌ Error initializing WebSocket:", error);
      setError("Failed to initialize WebSocket connection");
      setWsStatus("setup_error");
    }
  };

  // Load initial data from backend API (updated to match first component)
  useEffect(() => {
    const fetchTopMoversData = async () => {
      try {
        setLoading(true);
        setError(null);

        const apiUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";

        console.log("📡 Loading data via REST API...");

        // Use the same endpoint as the first component
        const response = await fetch(
          `${apiUrl}/api/analytics/top-movers?limit=20`
        );

        if (!response.ok) {
          throw new Error(`API request failed with status ${response.status}`);
        }

        const responseData = await response.json();

        if (responseData.success && responseData.data) {
          const data = responseData.data;
          setTopGainers(data.gainers || []);
          setTopLosers(data.losers || []);
          setSummary({
            total_gainers: data.gainers?.length || 0,
            total_losers: data.losers?.length || 0,
          });
          setUpdatedAt(data.updated_at || new Date().toISOString());
          console.log("✅ Loaded top movers from backend API");
        } else {
          throw new Error(responseData.message || "Invalid response format");
        }
      } catch (error) {
        console.error("Error fetching top movers data:", error);
        setError(`Failed to load top movers data: ${error.message}`);

        // Use mock data as fallback
        const mockData = {
          gainers: [
            {
              symbol: "RELIANCE",
              name: "Reliance Industries Ltd",
              price: 2875.45,
              change_percent: 4.56,
              volume: 3456789,
              sector: "Energy",
            },
            {
              symbol: "INFY",
              name: "Infosys Ltd",
              price: 1765.3,
              change_percent: 5.35,
              volume: 2345678,
              sector: "Technology",
            },
          ],
          losers: [
            {
              symbol: "BAJFINANCE",
              name: "Bajaj Finance Ltd",
              price: 6543.2,
              change_percent: -4.24,
              volume: 2134567,
              sector: "Financial Services",
            },
            {
              symbol: "LT",
              name: "Larsen & Toubro Ltd",
              price: 3456.75,
              change_percent: -4.33,
              volume: 1876543,
              sector: "Construction",
            },
          ],
        };

        setTopGainers(mockData.gainers);
        setTopLosers(mockData.losers);
        setSummary({
          total_gainers: mockData.gainers.length,
          total_losers: mockData.losers.length,
        });
        setUpdatedAt(new Date().toISOString());
        console.log("📝 Using mock data as fallback");
      } finally {
        setLoading(false);
      }
    };

    fetchTopMoversData();
  }, []);

  // Initialize connection on mount
  useEffect(() => {
    initializeWebSocket();

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current);
      }

      if (socketRef.current) {
        socketRef.current.close(1000, "Component unmounting");
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fallback to REST API if WebSocket fails
  useEffect(() => {
    const fallbackTimeout = setTimeout(() => {
      if (wsStatus !== "connected" && loading) {
        console.log("⚠️ WebSocket not connected, using REST API fallback");
        // Trigger a data reload
        window.location.reload();
      }
    }, 15000); // Wait 15 seconds for WebSocket

    return () => clearTimeout(fallbackTimeout);
  }, [wsStatus, loading]);

  // Manual refresh function
  const handleRefresh = useCallback(() => {
    if (wsStatus === "connected") {
      console.log("🔄 Manual refresh via WebSocket");
      sendWebSocketMessage({ type: "get_top_movers", limit: 20 });
    } else {
      console.log("🔄 Manual refresh via page reload");
      window.location.reload();
    }
  }, [wsStatus]);

  // Formatting functions
  const formatPrice = (price) => {
    return typeof price === "number"
      ? price.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : "N/A";
  };

  const formatVolume = (volume) => {
    if (!volume) return "N/A";
    if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
    if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  const renderStockTable = (stocks, title, isGainers = true) => (
    <div style={{ marginBottom: "30px" }}>
      <h2 style={{ color: bloombergColors.header, marginBottom: "10px" }}>
        {title}
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ backgroundColor: bloombergColors.tableHeader }}>
            <th style={{ padding: "8px 12px", textAlign: "left" }}>RANK</th>
            <th style={{ padding: "8px 12px", textAlign: "left" }}>SYMBOL</th>
            <th style={{ padding: "8px 12px", textAlign: "right" }}>LAST</th>
            <th style={{ padding: "8px 12px", textAlign: "right" }}>%CHG</th>
            <th style={{ padding: "8px 12px", textAlign: "right" }}>VOLUME</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock, index) => {
            const isPositive = (stock.change_percent || 0) >= 0;
            return (
              <tr
                key={stock.symbol || index}
                style={{
                  backgroundColor:
                    index % 2 === 0
                      ? bloombergColors.tableRowEven
                      : bloombergColors.tableRowOdd,
                }}
              >
                <td style={{ padding: "8px 12px", fontWeight: "bold" }}>
                  {index + 1}
                </td>
                <td style={{ padding: "8px 12px", fontWeight: "bold" }}>
                  <div>{stock.symbol || "N/A"}</div>
                  {stock.name && (
                    <div
                      style={{
                        fontSize: "10px",
                        color: bloombergColors.text + "80",
                        fontWeight: "normal",
                      }}
                    >
                      {stock.name}
                    </div>
                  )}
                </td>
                <td style={{ padding: "8px 12px", textAlign: "right" }}>
                  ₹{formatPrice(stock.price || stock.last_price)}
                </td>
                <td
                  style={{
                    padding: "8px 12px",
                    textAlign: "right",
                    color: isPositive
                      ? bloombergColors.positive
                      : bloombergColors.negative,
                    fontWeight: "bold",
                    fontSize: "15px",
                  }}
                >
                  {typeof stock.change_percent === "number"
                    ? (stock.change_percent >= 0 ? "+" : "") +
                      stock.change_percent.toFixed(2) +
                      "%"
                    : "N/A"}
                </td>
                <td style={{ padding: "8px 12px", textAlign: "right" }}>
                  {formatVolume(stock.volume)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  return (
    <div
      className="top-gainers-losers"
      style={{
        backgroundColor: bloombergColors.background,
        color: bloombergColors.text,
        minHeight: "100vh",
        padding: "20px",
        fontFamily: "'Courier New', monospace",
        fontSize: "14px",
      }}
    >
      {/* Header and status indicator */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "15px",
        }}
      >
        <h1 style={{ color: bloombergColors.header, margin: 0 }}>
          TOP GAINERS & LOSERS
        </h1>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button
            onClick={handleRefresh}
            disabled={loading}
            style={{
              padding: "5px 15px",
              background: bloombergColors.header,
              color: bloombergColors.background,
              border: "none",
              cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "'Courier New', monospace",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "LOADING..." : "REFRESH"}
          </button>
          <div
            style={{
              padding: "5px 10px",
              background:
                wsStatus === "connected"
                  ? bloombergColors.positive
                  : wsStatus === "connecting"
                  ? bloombergColors.neutral
                  : bloombergColors.negative,
              color: bloombergColors.background,
            }}
          >
            {wsStatus.toUpperCase()}
          </div>
        </div>
      </div>

      {error && (
        <div
          style={{
            color: bloombergColors.negative,
            marginBottom: "15px",
            padding: "10px",
            backgroundColor: bloombergColors.cardBackground,
            border: `1px solid ${bloombergColors.negative}`,
          }}
        >
          ERROR: {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>
          LOADING TOP MOVERS DATA...
        </div>
      ) : (
        <>
          {/* Enhanced Summary Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "20px",
              marginBottom: "30px",
            }}
          >
            <div
              style={{
                padding: "15px",
                backgroundColor: bloombergColors.cardBackground,
                border: `2px solid ${bloombergColors.positive}`,
              }}
            >
              <h3
                style={{
                  color: bloombergColors.positive,
                  margin: "0 0 10px 0",
                }}
              >
                🚀 TOP GAINERS SUMMARY
              </h3>
              <div>
                <div>Market Gainers: {summary.total_gainers} stocks</div>
                <div>Showing Top: {topGainers.length}</div>
                <div>
                  Leader:{" "}
                  {topGainers.length > 0
                    ? `${
                        topGainers[0]?.symbol
                      } (+${topGainers[0]?.change_percent?.toFixed(2)}%)`
                    : "N/A"}
                </div>
              </div>
            </div>
            <div
              style={{
                padding: "15px",
                backgroundColor: bloombergColors.cardBackground,
                border: `2px solid ${bloombergColors.negative}`,
              }}
            >
              <h3
                style={{
                  color: bloombergColors.negative,
                  margin: "0 0 10px 0",
                }}
              >
                📉 TOP LOSERS SUMMARY
              </h3>
              <div>
                <div>Market Losers: {summary.total_losers} stocks</div>
                <div>Showing Top: {topLosers.length}</div>
                <div>
                  Worst:{" "}
                  {topLosers.length > 0
                    ? `${
                        topLosers[0]?.symbol
                      } (${topLosers[0]?.change_percent?.toFixed(2)}%)`
                    : "N/A"}
                </div>
              </div>
            </div>
          </div>

          {/* Two-column layout for Gainers and Losers */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "30px",
            }}
          >
            <div>{renderStockTable(topGainers, "🚀 TOP GAINERS", true)}</div>
            <div>{renderStockTable(topLosers, "📉 TOP LOSERS", false)}</div>
          </div>

          {/* Footer with enhanced info */}
          <div
            style={{
              marginTop: "20px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              DATA SOURCE:{" "}
              {wsStatus === "connected" ? "REAL-TIME WebSocket" : "REST API"} |
              REFRESH: AUTO
            </div>
            <div>
              LAST UPDATE:{" "}
              {updatedAt ? new Date(updatedAt).toLocaleTimeString() : "N/A"}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default TopGainersLosers;
