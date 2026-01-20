import React, { useState, useEffect, useRef } from "react";

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    background: "#0a0a0a",
    minHeight: "100vh",
    padding: "16px",
  },
  header: {
    background:
      "linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.1)",
    padding: "20px 24px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "16px",
  },
  title: {
    fontSize: "1.5rem",
    fontWeight: "bold",
    color: "#ffffff",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  connectionStatus: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "0.875rem",
  },
  statusDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    transition: "all 0.3s ease",
  },
  filters: {
    display: "flex",
    gap: "12px",
    alignItems: "center",
    flexWrap: "wrap",
  },
  filterSelect: {
    background: "#2a2a3e",
    border: "1px solid rgba(255, 255, 255, 0.3)",
    borderRadius: "6px",
    color: "#ffffff",
    padding: "8px 12px",
    fontSize: "0.875rem",
    minWidth: "120px",
  },
  refreshButton: {
    background: "linear-gradient(45deg, #667eea 0%, #764ba2 100%)",
    border: "none",
    borderRadius: "8px",
    color: "white",
    padding: "8px 16px",
    fontSize: "0.875rem",
    cursor: "pointer",
    transition: "all 0.3s ease",
    fontWeight: "500",
  },
  mainContent: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
  },
  card: {
    background:
      "linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.1)",
    backdropFilter: "blur(20px)",
    overflow: "hidden",
    height: "600px",
    display: "flex",
    flexDirection: "column",
  },
  cardHeader: {
    padding: "16px 20px",
    borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
    background: "rgba(255, 255, 255, 0.05)",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  cardTitle: {
    fontSize: "1.1rem",
    fontWeight: "bold",
    color: "white",
    margin: 0,
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  cardSubtitle: {
    fontSize: "0.75rem",
    color: "rgba(255, 255, 255, 0.6)",
    margin: "4px 0 0 0",
  },
  list: {
    flex: 1,
    overflowY: "auto",
    padding: "0",
  },
  listItem: {
    display: "flex",
    alignItems: "center",
    padding: "12px 20px",
    borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
    transition: "all 0.3s ease",
    cursor: "pointer",
    position: "relative",
  },
  rank: {
    fontSize: "0.7rem",
    fontWeight: "bold",
    color: "rgba(255, 255, 255, 0.5)",
    minWidth: "20px",
    fontFamily: "monospace",
  },
  stockInfo: {
    flex: 1,
    marginLeft: "12px",
    minWidth: "0",
  },
  symbol: {
    fontSize: "0.85rem",
    fontWeight: "bold",
    color: "white",
    margin: "0 0 2px 0",
    fontFamily: "monospace",
  },
  name: {
    fontSize: "0.7rem",
    color: "rgba(255, 255, 255, 0.6)",
    margin: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  sector: {
    fontSize: "0.6rem",
    color: "rgba(255, 255, 255, 0.5)",
    background: "rgba(255, 255, 255, 0.1)",
    borderRadius: "8px",
    padding: "1px 6px",
    marginTop: "2px",
    display: "inline-block",
  },
  metrics: {
    textAlign: "right",
    minWidth: "80px",
  },
  price: {
    fontSize: "0.8rem",
    fontWeight: "600",
    color: "white",
    margin: "0 0 2px 0",
    fontFamily: "monospace",
  },
  change: {
    fontSize: "0.75rem",
    fontWeight: "bold",
    margin: 0,
    fontFamily: "monospace",
  },
  volume: {
    fontSize: "0.6rem",
    color: "rgba(255, 255, 255, 0.5)",
    margin: "2px 0 0 0",
    fontFamily: "monospace",
  },
  loading: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    height: "200px",
    flexDirection: "column",
    gap: "12px",
  },
  spinner: {
    width: "32px",
    height: "32px",
    border: "3px solid rgba(255, 255, 255, 0.3)",
    borderTop: "3px solid white",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
  error: {
    padding: "24px",
    textAlign: "center",
    color: "rgba(255, 255, 255, 0.7)",
  },
  bottomSection: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
    marginTop: "16px",
  },
};

const TopMoversComponent = () => {
  const [gainersData, setGainersData] = useState([]);
  const [losersData, setLosersData] = useState([]);
  const [volumeData, setVolumeData] = useState([]);
  const [intradayData, setIntradayData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [timeFilter, setTimeFilter] = useState("1D");
  const [sectorFilter, setSectorFilter] = useState("ALL");
  const [sectors, setSectors] = useState(["ALL"]);
  const [connectionStatus, setConnectionStatus] = useState("Connecting...");

  const wsRef = useRef(null);
  const mountedRef = useRef(true);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const heartbeatInterval = useRef(null);

  // WebSocket message handlers
  const handleWebSocketMessage = (data) => {
    try {
      const message = JSON.parse(data);
      console.log("📊 Received WebSocket message:", message.type);

      setLastUpdate(new Date(message.timestamp));

      switch (message.type) {
        case "initial_data":
          // Handle comprehensive initial data
          if (message.data.top_movers) {
            setGainersData(message.data.top_movers.gainers || []);
            setLosersData(message.data.top_movers.losers || []);
          }
          if (message.data.volume_analysis) {
            setVolumeData(message.data.volume_analysis.volume_leaders || []);
          }
          if (message.data.intraday_stocks) {
            setIntradayData(message.data.intraday_stocks);
          }
          setLoading(false);
          break;

        case "top_movers_data":
          if (message.data.gainers) setGainersData(message.data.gainers);
          if (message.data.losers) setLosersData(message.data.losers);
          break;

        case "volume_analysis_data":
          if (message.data.volume_leaders) {
            setVolumeData(message.data.volume_leaders);
          }
          break;

        case "intraday_stocks_data":
          if (message.data.intraday_stocks) {
            setIntradayData(message.data.intraday_stocks);
          }
          break;

        case "periodic_update":
          // Handle periodic updates
          if (message.data.top_movers) {
            setGainersData(message.data.top_movers.gainers || []);
            setLosersData(message.data.top_movers.losers || []);
          }
          if (message.data.volume_analysis) {
            setVolumeData(message.data.volume_analysis.volume_leaders || []);
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
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
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

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log("✅ WebSocket connected");
        setConnected(true);
        setError(null);
        setConnectionStatus("Connected");
        reconnectAttempts.current = 0;

        // Subscribe to updates
        sendWebSocketMessage({
          type: "subscribe",
          types: ["top_movers", "volume_analysis", "intraday_stocks"],
          interval: 30,
        });

        // Start heartbeat
        heartbeatInterval.current = setInterval(() => {
          sendWebSocketMessage({ type: "ping" });
        }, 30000);
      };

      wsRef.current.onmessage = (event) => {
        handleWebSocketMessage(event.data);
      };

      wsRef.current.onclose = (event) => {
        console.log("📊 WebSocket disconnected:", event.code, event.reason);
        setConnected(false);
        setConnectionStatus("Disconnected");

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
          setConnectionStatus(`Reconnecting in ${delay / 1000}s...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              reconnectAttempts.current++;
              setConnectionStatus("Reconnecting...");
              initializeWebSocket();
            }
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError(
            "Connection failed after multiple attempts. Please refresh the page."
          );
          setConnectionStatus("Connection Failed");
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        setError("WebSocket connection error");
        setConnectionStatus("Connection Error");
      };
    } catch (error) {
      console.error("❌ Error initializing WebSocket:", error);
      setError("Failed to initialize WebSocket connection");
      setConnectionStatus("Initialization Error");
    }
  };

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

      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounting");
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load sectors from REST API
  useEffect(() => {
    fetch(`${process.env.REACT_APP_API_URL}/api/analytics/sectors`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setSectors(["ALL", ...data.data]);
        }
      })
      .catch(() => setSectors(["ALL"]));
  }, []);

  // Fallback to REST API if WebSocket fails
  useEffect(() => {
    const fallbackTimeout = setTimeout(() => {
      if (!connected && loading) {
        console.log("⚠️ WebSocket not connected, using REST API fallback");
        loadDataFallback();
      }
    }, 15000); // Wait 15 seconds for WebSocket

    return () => clearTimeout(fallbackTimeout);
  }, [connected, loading]);

  // Manual refresh function
  const refreshData = () => {
    if (connected) {
      console.log("🔄 Manual refresh via WebSocket");
      sendWebSocketMessage({ type: "get_top_movers", limit: 20 });
      sendWebSocketMessage({ type: "get_volume_analysis", limit: 20 });
      sendWebSocketMessage({
        type: "get_intraday_stocks",
        min_change: 2.0,
        min_volume: 100000,
      });
    } else {
      console.log("🔄 Manual refresh via REST API");
      loadDataFallback();
    }
  };

  // Fallback REST API call
  const loadDataFallback = async () => {
    setLoading(true);
    setError(null);

    try {
      console.log("📡 Loading data via REST API...");

      const apiUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";

      // Fetch all data in parallel
      const [gainersLosersResponse, volumeResponse, intradayResponse] =
        await Promise.all([
          fetch(`${apiUrl}/api/analytics/top-movers?limit=20`),
          fetch(`${apiUrl}/api/analytics/volume-analysis?limit=20`),
          fetch(`${apiUrl}/api/analytics/intraday-stocks`),
        ]);

      if (
        !gainersLosersResponse.ok ||
        !volumeResponse.ok ||
        !intradayResponse.ok
      ) {
        throw new Error("One or more API requests failed");
      }

      const [gainersLosersData, volumeData, intradayData] = await Promise.all([
        gainersLosersResponse.json(),
        volumeResponse.json(),
        intradayResponse.json(),
      ]);

      // Update state with the response data
      if (gainersLosersData.success) {
        setGainersData(gainersLosersData.data.gainers || []);
        setLosersData(gainersLosersData.data.losers || []);
      }

      if (volumeData.success) {
        setVolumeData(volumeData.data.volume_leaders || []);
      }

      if (intradayData.success) {
        setIntradayData(intradayData.data.intraday_stocks || []);
      }

      setLastUpdate(new Date());
      setConnectionStatus("REST API");
    } catch (err) {
      setError("Failed to load market data: " + err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    if (num >= 10000000) return `${(num / 10000000).toFixed(1)}Cr`;
    if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getChangeColor = (change) => {
    return change >= 0 ? "#4CAF50" : "#f44336";
  };

  const filterBySection = (data) => {
    return data.filter(
      (stock) => sectorFilter === "ALL" || stock.sector === sectorFilter
    );
  };

  const renderListItem = (stock, index, type = "default") => {
    return (
      <div
        key={stock.symbol}
        style={styles.listItem}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
        }}
      >
        <div style={styles.rank}>{index + 1}</div>

        <div style={styles.stockInfo}>
          <div style={styles.symbol}>{stock.symbol}</div>
          <div style={styles.name}>{stock.name || stock.symbol}</div>
          {stock.sector && <div style={styles.sector}>{stock.sector}</div>}
        </div>

        <div style={styles.metrics}>
          <div style={styles.price}>
            ₹{(stock.price || stock.last_price || 0).toFixed(2)}
          </div>
          <div
            style={{
              ...styles.change,
              color: getChangeColor(stock.change_percent),
            }}
          >
            {stock.change_percent >= 0 ? "+" : ""}
            {(stock.change_percent || 0).toFixed(2)}%
          </div>

          {type === "volume" && (
            <div style={styles.volume}>
              Vol: {formatNumber(stock.volume || 0)}
              {stock.volume_ratio && ` | ${stock.volume_ratio}x`}
            </div>
          )}

          {type === "intraday" && (
            <div style={styles.volume}>
              {stock.intraday_score && `Score: ${stock.intraday_score} | `}
              Vol: {formatNumber(stock.volume || 0)}
            </div>
          )}

          {(type === "gainers" || type === "losers" || type === "default") && (
            <div style={styles.volume}>
              Vol: {formatNumber(stock.volume || 0)}
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderCard = (title, subtitle, icon, data, type) => {
    return (
      <div style={styles.card}>
        <div style={styles.cardHeader}>
          <div>
            <div style={styles.cardTitle}>
              <span>{icon}</span>
              {title}
            </div>
            <div style={styles.cardSubtitle}>{subtitle}</div>
          </div>
        </div>

        {loading ? (
          <div style={styles.loading}>
            <div style={styles.spinner}></div>
            <div
              style={{
                color: "rgba(255, 255, 255, 0.7)",
                fontSize: "0.875rem",
              }}
            >
              Loading market data...
            </div>
          </div>
        ) : error ? (
          <div style={styles.error}>
            <div>⚠️ {error}</div>
            <button
              onClick={refreshData}
              style={{ ...styles.refreshButton, marginTop: "12px" }}
            >
              Retry Connection
            </button>
          </div>
        ) : (
          <div style={styles.list}>
            {filterBySection(data).length > 0 ? (
              filterBySection(data).map((stock, index) =>
                renderListItem(stock, index, type)
              )
            ) : (
              <div
                style={{
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "rgba(255, 255, 255, 0.5)",
                }}
              >
                No data available for {title.toLowerCase()}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          .refresh-button:hover {
            background: linear-gradient(45deg, #5a67d8 0%, #667eea 100%) !important;
            transform: translateY(-1px);
          }
          @media (max-width: 768px) {
            .main-content {
              grid-template-columns: 1fr !important;
            }
            .bottom-section {
              grid-template-columns: 1fr !important;
            }
          }
        `}
      </style>

      <div style={styles.container}>
        {/* Header with filters and connection status */}
        <div style={styles.header}>
          <div style={styles.title}>
            <span>📊</span>
            Market Terminal
          </div>

          {/* Enhanced Connection Status */}
          <div style={styles.connectionStatus}>
            <div
              style={{
                ...styles.statusDot,
                backgroundColor: connected
                  ? "#4CAF50"
                  : error
                  ? "#f44336"
                  : "#FF9800",
              }}
            ></div>
            <span
              style={{
                color: connected ? "#4CAF50" : error ? "#f44336" : "#FF9800",
                fontWeight: "500",
              }}
            >
              {connectionStatus}
            </span>
            {lastUpdate && (
              <span
                style={{ color: "rgba(255, 255, 255, 0.6)", marginLeft: "8px" }}
              >
                • {lastUpdate.toLocaleTimeString()}
              </span>
            )}
            {connected && (
              <span
                style={{ color: "rgba(255, 255, 255, 0.6)", marginLeft: "8px" }}
              >
                • WebSocket
              </span>
            )}
          </div>

          <div style={styles.filters}>
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              style={styles.filterSelect}
            >
              <option value="1D">1 Day</option>
              <option value="1W">1 Week</option>
              <option value="1M">1 Month</option>
            </select>

            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              style={styles.filterSelect}
            >
              {sectors.map((sector) => (
                <option key={sector} value={sector}>
                  {sector === "ALL"
                    ? "All Sectors"
                    : sector.charAt(0) + sector.slice(1).toLowerCase()}
                </option>
              ))}
            </select>

            <button
              onClick={refreshData}
              style={styles.refreshButton}
              className="refresh-button"
              disabled={loading}
            >
              🔄 {loading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </div>

        {/* Main content - Top Gainers and Losers side by side */}
        <div style={styles.mainContent} className="main-content">
          {renderCard(
            "Top Gainers",
            "Best performing stocks today",
            "🚀",
            gainersData,
            "gainers"
          )}

          {renderCard(
            "Top Losers",
            "Worst performing stocks today",
            "📉",
            losersData,
            "losers"
          )}
        </div>

        {/* Bottom section - Volume Leaders and Intraday Picks */}
        <div style={styles.bottomSection} className="bottom-section">
          {renderCard(
            "Volume Leaders",
            "Most actively traded stocks",
            "📊",
            volumeData,
            "volume"
          )}

          {renderCard(
            "Intraday Momentum",
            "High momentum stocks for trading",
            "🎯",
            intradayData,
            "intraday"
          )}
        </div>
      </div>
    </>
  );
};

export default TopMoversComponent;
