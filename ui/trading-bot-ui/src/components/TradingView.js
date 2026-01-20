import React, { useState, useEffect } from "react";
import axios from "axios";

function TradingView({ symbol }) {
  const [tradingData, setTradingData] = useState({
    spot: null,
    options_chain: null,
    updated_at: null,
  });
  const [loading, setLoading] = useState(true);
  const [selectedExpiry, setSelectedExpiry] = useState(null);

  // Load initial data
  useEffect(() => {
    const fetchTradingData = async () => {
      try {
        setLoading(true);
        const response = await axios.get(
          `/api/instruments/trading-data/${symbol}`
        );
        setTradingData(response.data);

        // Set default expiry (nearest)
        if (
          response.data.options_chain &&
          response.data.options_chain.expirations
        ) {
          const expiryDates = Object.keys(
            response.data.options_chain.expirations
          );
          if (expiryDates.length > 0) {
            setSelectedExpiry(expiryDates[0]);
          }
        }
      } catch (error) {
        console.error("Error fetching trading data:", error);
      } finally {
        setLoading(false);
      }
    };

    if (symbol) {
      fetchTradingData();
    }
  }, [symbol]);

  // WebSocket for real-time updates
  useEffect(() => {
    const setupWebSocket = async () => {
      if (!symbol) return;

      try {
        // Get WebSocket keys for this symbol
        const keysResponse = await axios.get(
          `/api/instruments/websocket-keys/trading/${symbol}`
        );
        const { keys } = keysResponse.data;

        // Create WebSocket connection
        const wsProtocol =
          window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsHost =
          process.env.REACT_APP_WS_HOST || window.location.hostname;
        const wsPort = process.env.REACT_APP_WS_PORT || "8000";
        const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws/market-data`;
        const ws = new WebSocket(wsUrl);
        ws.onopen = () => {
          console.log(`WebSocket connected for ${symbol}`);
          // Subscribe to trading instruments
          ws.send(
            JSON.stringify({
              type: "subscribe",
              keys: keys,
            })
          );
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);

          if (data.type === "market_data") {
            // Update trading data with WebSocket updates
            setTradingData((prevData) => {
              // Create updated data structure
              const updated = { ...prevData, updated_at: data.timestamp };

              // Update spot data
              if (prevData.spot && data.data[prevData.spot.instrument_key]) {
                updated.spot = {
                  ...prevData.spot,
                  ...data.data[prevData.spot.instrument_key],
                };
              }

              // Update options chain
              // Update options chain
              if (prevData.options_chain) {
                const updatedChain = { ...prevData.options_chain };

                // Update each expiry and strike
                Object.keys(updatedChain.expirations).forEach((expiry) => {
                  const expiryData = updatedChain.expirations[expiry];

                  // Update each strike row
                  expiryData.data.forEach((strikeRow, index) => {
                    // Update call option
                    if (strikeRow.call && strikeRow.call.instrument_key) {
                      const callUpdate =
                        data.data[strikeRow.call.instrument_key];
                      if (callUpdate) {
                        updatedChain.expirations[expiry].data[index].call = {
                          ...strikeRow.call,
                          ltp: callUpdate.ltp || strikeRow.call.ltp,
                          change: callUpdate.change || strikeRow.call.change,
                          oi: callUpdate.oi || strikeRow.call.oi,
                          volume: callUpdate.volume || strikeRow.call.volume,
                        };
                      }
                    }

                    // Update put option
                    if (strikeRow.put && strikeRow.put.instrument_key) {
                      const putUpdate = data.data[strikeRow.put.instrument_key];
                      if (putUpdate) {
                        updatedChain.expirations[expiry].data[index].put = {
                          ...strikeRow.put,
                          ltp: putUpdate.ltp || strikeRow.put.ltp,
                          change: putUpdate.change || strikeRow.put.change,
                          oi: putUpdate.oi || strikeRow.put.oi,
                          volume: putUpdate.volume || strikeRow.put.volume,
                        };
                      }
                    }
                  });
                });

                updated.options_chain = updatedChain;
              }

              return updated;
            });
          }
        };

        ws.onclose = () => {
          console.log(`WebSocket disconnected for ${symbol}`);
          // Reconnect after a delay
          setTimeout(setupWebSocket, 5000);
        };

        ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          ws.close();
        };

        return () => {
          if (ws) {
            ws.close();
          }
        };
      } catch (error) {
        console.error("Error setting up WebSocket:", error);
      }
    };

    setupWebSocket();
  }, [symbol]);

  // Handle expiry selection
  const handleExpiryChange = (event) => {
    setSelectedExpiry(event.target.value);
  };

  // Render options chain for selected expiry
  const renderOptionsChain = () => {
    if (!tradingData.options_chain || !selectedExpiry) {
      return <div>No options data available</div>;
    }

    const expiryData = tradingData.options_chain.expirations[selectedExpiry];
    if (!expiryData) {
      return <div>No data for selected expiry</div>;
    }

    return (
      <div className="options-chain">
        <table className="options-table">
          <thead>
            <tr>
              <th colSpan="4">CALLS</th>
              <th rowSpan="2">Strike</th>
              <th colSpan="4">PUTS</th>
            </tr>
            <tr>
              <th>OI</th>
              <th>Volume</th>
              <th>Price</th>
              <th>Change</th>
              <th>Change</th>
              <th>Price</th>
              <th>Volume</th>
              <th>OI</th>
            </tr>
          </thead>
          <tbody>
            {expiryData.data.map((row) => (
              <tr
                key={row.strike}
                className={
                  row.strike === tradingData.spot?.last_price ? "atm-row" : ""
                }
              >
                {/* Call data */}
                <td>{row.call?.oi?.toLocaleString() || "-"}</td>
                <td>{row.call?.volume?.toLocaleString() || "-"}</td>
                <td className="price">{row.call?.ltp?.toFixed(2) || "-"}</td>
                <td
                  className={`change ${
                    (row.call?.change || 0) > 0 ? "positive" : "negative"
                  }`}
                >
                  {row.call?.change?.toFixed(2) || "-"}
                </td>

                {/* Strike price */}
                <td className="strike">{row.strike.toFixed(2)}</td>

                {/* Put data */}
                <td
                  className={`change ${
                    (row.put?.change || 0) > 0 ? "positive" : "negative"
                  }`}
                >
                  {row.put?.change?.toFixed(2) || "-"}
                </td>
                <td className="price">{row.put?.ltp?.toFixed(2) || "-"}</td>
                <td>{row.put?.volume?.toLocaleString() || "-"}</td>
                <td>{row.put?.oi?.toLocaleString() || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="trading-view">
      <h1>{symbol} Trading View</h1>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <>
          {/* Spot price section */}
          {tradingData.spot && (
            <div className="spot-section">
              <h2>Spot Price</h2>
              <div className="spot-card">
                <div className="price-large">
                  {tradingData.spot.last_price?.toFixed(2)}
                </div>
                <div
                  className={`change-large ${
                    tradingData.spot.change > 0 ? "positive" : "negative"
                  }`}
                >
                  {tradingData.spot.change?.toFixed(2)} (
                  {tradingData.spot.change_percent?.toFixed(2)}%)
                </div>
                <div className="price-details">
                  <div>Open: {tradingData.spot.open?.toFixed(2)}</div>
                  <div>High: {tradingData.spot.high?.toFixed(2)}</div>
                  <div>Low: {tradingData.spot.low?.toFixed(2)}</div>
                  <div>Close: {tradingData.spot.close?.toFixed(2)}</div>
                  <div>Volume: {tradingData.spot.volume?.toLocaleString()}</div>
                </div>
              </div>
            </div>
          )}

          {/* Options chain section */}
          {tradingData.options_chain && (
            <div className="options-section">
              <h2>Options Chain</h2>

              {/* Expiry selector */}
              <div className="expiry-selector">
                <label htmlFor="expiry">Select Expiry:</label>
                <select
                  id="expiry"
                  value={selectedExpiry || ""}
                  onChange={handleExpiryChange}
                >
                  {Object.keys(tradingData.options_chain.expirations).map(
                    (expiry) => (
                      <option key={expiry} value={expiry}>
                        {new Date(parseInt(expiry)).toLocaleDateString()}
                      </option>
                    )
                  )}
                </select>
              </div>

              {/* Options chain table */}
              {renderOptionsChain()}
            </div>
          )}

          <div className="footer">
            Last updated:{" "}
            {new Date(tradingData.updated_at).toLocaleTimeString()}
          </div>
        </>
      )}
    </div>
  );
}

export default TradingView;
