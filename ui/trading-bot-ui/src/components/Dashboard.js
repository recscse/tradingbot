import React, { useState, useEffect, useRef, useCallback } from "react";

// Mock data for development/testing
const mockData = {
  indices: [
    {
      instrument_key: "NSE_INDEX|Nifty 50",
      symbol: "NIFTY",
      last_price: 24568.75,
      change: 245.3,
      change_percent: 1.01,
    },
    {
      instrument_key: "NSE_INDEX|Nifty Bank",
      symbol: "BANKNIFTY",
      last_price: 49876.5,
      change: -123.25,
      change_percent: -0.25,
    },
  ],
  top_stocks: [
    {
      instrument_key: "NSE_EQ|INE002A01018",
      symbol: "RELIANCE",
      last_price: 2875.45,
      change: 37.5,
      change_percent: 1.32,
      volume: 3456789,
    },
    {
      instrument_key: "NSE_EQ|INE009A01021",
      symbol: "INFY",
      last_price: 1765.3,
      change: -25.7,
      change_percent: -1.43,
      volume: 2345678,
    },
    {
      instrument_key: "NSE_EQ|INE238A01034",
      symbol: "TCS",
      last_price: 3987.6,
      change: 42.3,
      change_percent: 1.07,
      volume: 1234567,
    },
    {
      instrument_key: "NSE_EQ|INE155A01022",
      symbol: "HDFCBANK",
      last_price: 1678.9,
      change: -12.4,
      change_percent: -0.73,
      volume: 3456789,
    },
  ],
  updated_at: new Date().toISOString(),
};

function Dashboard() {
  // Use separate states for different data segments to minimize re-renders
  const [indices, setIndices] = useState([]);
  const [topStocks, setTopStocks] = useState([]);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsStatus, setWsStatus] = useState("disconnected");

  // Use refs for data that doesn't need to trigger re-renders
  const socketRef = useRef(null);
  const lastUpdateRef = useRef(null);

  // Memoized transform function
  const transformDashboardData = useCallback((apiData) => {
    const transformed = {
      indices: [],
      top_stocks: [],
      updated_at: apiData.updated_at || new Date().toISOString(),
    };

    // Transform indices
    if (apiData.indices && Array.isArray(apiData.indices)) {
      transformed.indices = apiData.indices.map((index) => ({
        instrument_key: index.instrument_key,
        symbol: index.symbol || index.trading_symbol,
        last_price: index.last_price || index.ltp,
        change: index.change,
        change_percent: index.change_percent,
      }));
    }

    // Transform top stocks
    if (apiData.top_stocks && Array.isArray(apiData.top_stocks)) {
      transformed.top_stocks = apiData.top_stocks.map((stock) => ({
        instrument_key: stock.instrument_key,
        symbol: stock.symbol || stock.trading_symbol,
        last_price: stock.last_price || stock.ltp,
        change: stock.change,
        change_percent: stock.change_percent,
        volume: stock.volume,
      }));
    }

    return transformed;
  }, []);

  // Memoized normalize function
  const normalizeMarketData = useCallback((instrumentKey, data) => {
    if (!data) return null;

    // Handle different data formats (same as before)
    if (data.ltp !== undefined) {
      return {
        last_price: data.ltp,
        change: data.change || (data.cp ? data.ltp - data.cp : undefined),
        change_percent:
          data.change_percent ||
          (data.cp && data.cp !== 0
            ? ((data.ltp - data.cp) / data.cp) * 100
            : undefined),
        volume: data.volume || data.vtt,
      };
    } else if (data.fullFeed) {
      const fullFeed = data.fullFeed;
      if (fullFeed.indexFF) {
        const indexFF = fullFeed.indexFF;
        const ltpc = indexFF.ltpc || {};
        return {
          last_price: ltpc.ltp,
          change: ltpc.ltp && ltpc.cp ? ltpc.ltp - ltpc.cp : undefined,
          change_percent:
            ltpc.ltp && ltpc.cp && ltpc.cp !== 0
              ? ((ltpc.ltp - ltpc.cp) / ltpc.cp) * 100
              : undefined,
        };
      } else if (fullFeed.marketFF) {
        const marketFF = fullFeed.marketFF;
        const ltpc = marketFF.ltpc || {};
        return {
          last_price: ltpc.ltp,
          change: ltpc.ltp && ltpc.cp ? ltpc.ltp - ltpc.cp : undefined,
          change_percent:
            ltpc.ltp && ltpc.cp && ltpc.cp !== 0
              ? ((ltpc.ltp - ltpc.cp) / ltpc.cp) * 100
              : undefined,
          volume: marketFF.vtt,
        };
      }
    } else if (data.ltpc) {
      const ltpc = data.ltpc;
      return {
        last_price: ltpc.ltp,
        change: ltpc.ltp && ltpc.cp ? ltpc.ltp - ltpc.cp : undefined,
        change_percent:
          ltpc.ltp && ltpc.cp && ltpc.cp !== 0
            ? ((ltpc.ltp - ltpc.cp) / ltpc.cp) * 100
            : undefined,
        volume: data.vtt,
      };
    }

    return {
      last_price: data.last_price || data.ltp,
      change: data.change,
      change_percent: data.change_percent,
      volume: data.volume || data.vtt,
    };
  }, []);

  // Load initial data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        const apiBaseUrl =
          process.env.REACT_APP_API_URL || "http://localhost:8000";
        const response = await fetch(
          `${apiBaseUrl}/api/v1/dashboard/market-data`
        );
        const responseData = await response.json();

        if (!responseData.success || !responseData.data) {
          console.log("Using mock data for development");
          setIndices(mockData.indices);
          setTopStocks(mockData.top_stocks);
          setUpdatedAt(mockData.updated_at);
        } else {
          const transformedData = transformDashboardData(responseData.data);
          setIndices(transformedData.indices);
          setTopStocks(transformedData.top_stocks);
          setUpdatedAt(transformedData.updated_at);
        }
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        setError(`Failed to load dashboard data: ${error.message}`);
        setIndices(mockData.indices);
        setTopStocks(mockData.top_stocks);
        setUpdatedAt(mockData.updated_at);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();

    const interval = setInterval(fetchDashboardData, 60000);
    return () => clearInterval(interval);
  }, [transformDashboardData]);

  // WebSocket for real-time updates
  useEffect(() => {
    const setupWebSocket = async () => {
      try {
        setWsStatus("connecting");

        const apiBaseUrl =
          process.env.REACT_APP_API_URL || "http://localhost:8000";
        const keysResponse = await fetch(
          `${apiBaseUrl}/api/v1/websocket-keys/dashboard`
        );
        const keysData = await keysResponse.json();

        let subscriptionKeys = keysData.keys || [];
        if (!Array.isArray(subscriptionKeys) || subscriptionKeys.length === 0) {
          subscriptionKeys = mockData.indices
            .map((i) => i.instrument_key)
            .concat(mockData.top_stocks.map((s) => s.instrument_key));
        }

        let wsUrl;
        if (process.env.REACT_APP_WS_URL) {
          wsUrl = `${process.env.REACT_APP_WS_URL}/ws/dashboard`;
        } else {
          const wsProtocol =
            window.location.protocol === "https:" ? "wss:" : "ws:";
          const wsHost = window.location.hostname;
          const wsPort = "8000";
          wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws/dashboard`;
        }

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setWsStatus("connected");
          const subscriptionMessage = JSON.stringify({
            type: "subscribe",
            keys: subscriptionKeys,
          });
          ws.send(subscriptionMessage);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (
              data.type === "market_data" ||
              data.type === "dashboard_update"
            ) {
              const marketData = data.data || {};
              const now = new Date().toISOString();

              // Only update if we have new data and it's been at least 100ms since last update
              if (
                Object.keys(marketData).length > 0 &&
                (!lastUpdateRef.current ||
                  Date.now() - lastUpdateRef.current > 100)
              ) {
                lastUpdateRef.current = Date.now();

                // Update indices
                setIndices((prevIndices) => {
                  return prevIndices.map((index) => {
                    const update = marketData[index.instrument_key];
                    if (update) {
                      const normalizedUpdate = normalizeMarketData(
                        index.instrument_key,
                        update
                      );
                      return normalizedUpdate
                        ? { ...index, ...normalizedUpdate }
                        : index;
                    }
                    return index;
                  });
                });

                // Update top stocks
                setTopStocks((prevStocks) => {
                  return prevStocks.map((stock) => {
                    const update = marketData[stock.instrument_key];
                    if (update) {
                      const normalizedUpdate = normalizeMarketData(
                        stock.instrument_key,
                        update
                      );
                      return normalizedUpdate
                        ? { ...stock, ...normalizedUpdate }
                        : stock;
                    }
                    return stock;
                  });
                });

                setUpdatedAt(data.timestamp || now);
              }
            } else if (data.type === "subscription_status") {
              setWsStatus(
                data.status === "subscribed" ? "subscribed" : "connected"
              );
            } else if (data.type === "error") {
              setWsStatus("error");
            }
          } catch (error) {
            console.error("Error processing WebSocket message:", error);
          }
        };

        ws.onclose = (event) => {
          setWsStatus("disconnected");
          if (event.code !== 1000) {
            setTimeout(setupWebSocket, 5000);
          }
        };

        ws.onerror = () => {
          setWsStatus("error");
        };

        socketRef.current = ws;
      } catch (error) {
        console.error("Error setting up WebSocket:", error);
        setWsStatus("setup_error");
        setTimeout(setupWebSocket, 10000);
      }
    };

    setupWebSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.close(1000);
      }
    };
  }, [normalizeMarketData]);

  // Bloomberg-style color scheme and formatting functions remain the same
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

  const formatPrice = (price) => {
    return typeof price === "number"
      ? price.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : "N/A";
  };

  const formatChange = (change, percent) => {
    const isPositive = (change || 0) >= 0;
    const arrow = isPositive ? "▲" : "▼";
    const color = isPositive
      ? bloombergColors.positive
      : bloombergColors.negative;

    return (
      <span style={{ color }}>
        {arrow} {typeof change === "number" ? change.toFixed(2) : "N/A"} (
        {typeof percent === "number" ? percent.toFixed(2) : "N/A"}%)
      </span>
    );
  };

  return (
    <div
      className="dashboard"
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
          MARKET DASHBOARD
        </h1>
        <div
          style={{
            padding: "5px 10px",
            background:
              wsStatus === "connected" || wsStatus === "subscribed"
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

      {error && (
        <div style={{ color: bloombergColors.negative, marginBottom: "15px" }}>
          ERROR: {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>
          LOADING MARKET DATA...
        </div>
      ) : (
        <>
          {/* Market Indices Section */}
          <div style={{ marginBottom: "30px" }}>
            <h2 style={{ color: bloombergColors.header, marginBottom: "10px" }}>
              MARKET INDICES
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                gap: "10px",
              }}
            >
              {indices.map((index) => (
                <div
                  key={index.instrument_key}
                  style={{
                    padding: "12px",
                    backgroundColor: bloombergColors.cardBackground,
                  }}
                >
                  <div
                    style={{ display: "flex", justifyContent: "space-between" }}
                  >
                    <span style={{ fontWeight: "bold" }}>
                      {index.symbol || "N/A"}
                    </span>
                    <span>{formatPrice(index.last_price)}</span>
                  </div>
                  <div>{formatChange(index.change, index.change_percent)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Stocks Section */}
          <div>
            <h2 style={{ color: bloombergColors.header, marginBottom: "10px" }}>
              TOP STOCKS
            </h2>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ backgroundColor: bloombergColors.tableHeader }}>
                  <th style={{ padding: "8px 12px", textAlign: "left" }}>
                    SYMBOL
                  </th>
                  <th style={{ padding: "8px 12px", textAlign: "right" }}>
                    LAST
                  </th>
                  <th style={{ padding: "8px 12px", textAlign: "right" }}>
                    CHG
                  </th>
                  <th style={{ padding: "8px 12px", textAlign: "right" }}>
                    %CHG
                  </th>
                  <th style={{ padding: "8px 12px", textAlign: "right" }}>
                    VOLUME
                  </th>
                </tr>
              </thead>
              <tbody>
                {topStocks.map((stock, index) => {
                  const isPositive = (stock.change || 0) >= 0;
                  return (
                    <tr
                      key={stock.instrument_key}
                      style={{
                        backgroundColor:
                          index % 2 === 0
                            ? bloombergColors.tableRowEven
                            : bloombergColors.tableRowOdd,
                      }}
                    >
                      <td style={{ padding: "8px 12px" }}>
                        {stock.symbol || "N/A"}
                      </td>
                      <td style={{ padding: "8px 12px", textAlign: "right" }}>
                        {formatPrice(stock.last_price)}
                      </td>
                      <td
                        style={{
                          padding: "8px 12px",
                          textAlign: "right",
                          color: isPositive
                            ? bloombergColors.positive
                            : bloombergColors.negative,
                        }}
                      >
                        {typeof stock.change === "number"
                          ? stock.change.toFixed(2)
                          : "N/A"}
                      </td>
                      <td
                        style={{
                          padding: "8px 12px",
                          textAlign: "right",
                          color: isPositive
                            ? bloombergColors.positive
                            : bloombergColors.negative,
                        }}
                      >
                        {typeof stock.change_percent === "number"
                          ? stock.change_percent.toFixed(2) + "%"
                          : "N/A"}
                      </td>
                      <td style={{ padding: "8px 12px", textAlign: "right" }}>
                        {stock.volume ? stock.volume.toLocaleString() : "N/A"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div style={{ marginTop: "20px", textAlign: "right" }}>
            LAST UPDATE:{" "}
            {updatedAt ? new Date(updatedAt).toLocaleTimeString() : "N/A"}
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;
