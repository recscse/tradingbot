// components/common/StocksList.jsx - ENHANCED VERSION
import React, { memo } from "react";

const StocksList = memo(
  ({
    title,
    data = [],
    isLoading = false,
    titleIcon = "📊",
    emptyMessage = "No data available",
    maxItems = 20,
    showVolume = true,
    layoutType = "table", // "table" for stocks, "cards" for indices
  }) => {
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

    // Format price
    const formatPrice = (price) => {
      return typeof price === "number"
        ? price.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })
        : "N/A";
    };

    // Format change with color
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

    if (isLoading) {
      return (
        <div
          style={{
            textAlign: "center",
            padding: "40px",
            color: bloombergColors.text,
            background: `linear-gradient(45deg, ${bloombergColors.tableHeader}, ${bloombergColors.cardBackground})`,
            borderRadius: "4px",
            border: `1px solid ${bloombergColors.border}`,
          }}
        >
          <div
            style={{
              display: "inline-block",
              width: "30px",
              height: "30px",
              border: `3px solid ${bloombergColors.header}`,
              borderTop: "3px solid transparent",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              marginBottom: "15px",
            }}
          ></div>
          <div>LOADING {title}...</div>
          <style>
            {`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}
          </style>
        </div>
      );
    }

    // Card layout for indices (enhanced)
    if (layoutType === "cards") {
      return (
        <div>
          <h2
            style={{
              color: bloombergColors.header,
              marginBottom: "15px",
              fontSize: "18px",
              fontWeight: "bold",
              textShadow: "0 0 10px rgba(0, 180, 240, 0.5)",
              borderBottom: `2px solid ${bloombergColors.header}`,
              paddingBottom: "8px",
            }}
          >
            {title}
          </h2>

          {data.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "40px",
                color: bloombergColors.text,
                background: bloombergColors.cardBackground,
                borderRadius: "4px",
                border: `1px solid ${bloombergColors.border}`,
              }}
            >
              {emptyMessage}
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                gap: "15px",
              }}
            >
              {data.slice(0, maxItems).map((item, index) => {
                const isPositive = (item.change || 0) >= 0;
                return (
                  <div
                    key={item.instrument_key || item.symbol || index}
                    style={{
                      padding: "15px",
                      backgroundColor: bloombergColors.cardBackground,
                      border: `1px solid ${bloombergColors.border}`,
                      borderLeft: `4px solid ${
                        isPositive
                          ? bloombergColors.positive
                          : bloombergColors.negative
                      }`,
                      borderRadius: "6px",
                      transition: "all 0.3s ease",
                      cursor: "pointer",
                      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.3)",
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.transform = "translateY(-2px)";
                      e.target.style.boxShadow = `0 4px 15px ${
                        isPositive
                          ? bloombergColors.positive
                          : bloombergColors.negative
                      }30`;
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.transform = "translateY(0px)";
                      e.target.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.3)";
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "8px",
                      }}
                    >
                      <span
                        style={{
                          fontWeight: "bold",
                          fontSize: "16px",
                          color: bloombergColors.header,
                        }}
                      >
                        {item.symbol || "N/A"}
                      </span>
                      <span
                        style={{
                          fontSize: "14px",
                          color: bloombergColors.text,
                          opacity: 0.8,
                        }}
                      >
                        {Math.abs(item.change_percent || 0) > 2 ? "🔥" : ""}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: "18px",
                        fontWeight: "bold",
                        color: bloombergColors.text,
                        marginBottom: "8px",
                      }}
                    >
                      ₹{formatPrice(item.last_price || item.ltp)}
                    </div>
                    <div style={{ fontSize: "14px" }}>
                      {formatChange(item.change, item.change_percent)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    // Table layout for stocks (enhanced)
    return (
      <div>
        <h2
          style={{
            color: bloombergColors.header,
            marginBottom: "15px",
            fontSize: "18px",
            fontWeight: "bold",
            textShadow: "0 0 10px rgba(0, 180, 240, 0.5)",
            borderBottom: `2px solid ${bloombergColors.header}`,
            paddingBottom: "8px",
          }}
        >
          {title}
        </h2>

        {data.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px",
              color: bloombergColors.text,
              background: bloombergColors.cardBackground,
              borderRadius: "4px",
              border: `1px solid ${bloombergColors.border}`,
            }}
          >
            {emptyMessage}
          </div>
        ) : (
          <div
            style={{
              background: bloombergColors.cardBackground,
              borderRadius: "6px",
              overflow: "hidden",
              border: `1px solid ${bloombergColors.border}`,
              boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "14px",
              }}
            >
              <thead>
                <tr
                  style={{
                    backgroundColor: bloombergColors.tableHeader,
                    borderBottom: `2px solid ${bloombergColors.header}`,
                  }}
                >
                  <th
                    style={{
                      padding: "12px 15px",
                      textAlign: "left",
                      color: bloombergColors.header,
                      fontWeight: "bold",
                      fontSize: "13px",
                      letterSpacing: "0.5px",
                    }}
                  >
                    SYMBOL
                  </th>
                  <th
                    style={{
                      padding: "12px 15px",
                      textAlign: "right",
                      color: bloombergColors.header,
                      fontWeight: "bold",
                      fontSize: "13px",
                      letterSpacing: "0.5px",
                    }}
                  >
                    LAST
                  </th>
                  <th
                    style={{
                      padding: "12px 15px",
                      textAlign: "right",
                      color: bloombergColors.header,
                      fontWeight: "bold",
                      fontSize: "13px",
                      letterSpacing: "0.5px",
                    }}
                  >
                    CHG
                  </th>
                  <th
                    style={{
                      padding: "12px 15px",
                      textAlign: "right",
                      color: bloombergColors.header,
                      fontWeight: "bold",
                      fontSize: "13px",
                      letterSpacing: "0.5px",
                    }}
                  >
                    %CHG
                  </th>
                  {showVolume && (
                    <th
                      style={{
                        padding: "12px 15px",
                        textAlign: "right",
                        color: bloombergColors.header,
                        fontWeight: "bold",
                        fontSize: "13px",
                        letterSpacing: "0.5px",
                      }}
                    >
                      VOLUME
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, maxItems).map((stock, index) => {
                  const isPositive = (stock.change || 0) >= 0;
                  return (
                    <tr
                      key={stock.instrument_key || stock.symbol || index}
                      style={{
                        backgroundColor:
                          index % 2 === 0
                            ? bloombergColors.tableRowEven
                            : bloombergColors.tableRowOdd,
                        borderBottom: `1px solid ${bloombergColors.border}`,
                        transition: "all 0.2s ease",
                        cursor: "pointer",
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.backgroundColor = `${
                          isPositive
                            ? bloombergColors.positive
                            : bloombergColors.negative
                        }20`;
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.backgroundColor =
                          index % 2 === 0
                            ? bloombergColors.tableRowEven
                            : bloombergColors.tableRowOdd;
                      }}
                    >
                      <td
                        style={{
                          padding: "12px 15px",
                          color: bloombergColors.text,
                          fontWeight: "500",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                          }}
                        >
                          <span>
                            {stock.symbol || stock.trading_symbol || "N/A"}
                          </span>
                          {Math.abs(stock.change_percent || 0) > 5 && (
                            <span style={{ fontSize: "10px" }}>🔥</span>
                          )}
                        </div>
                      </td>
                      <td
                        style={{
                          padding: "12px 15px",
                          textAlign: "right",
                          color: bloombergColors.text,
                          fontWeight: "bold",
                        }}
                      >
                        ₹{formatPrice(stock.last_price || stock.ltp)}
                      </td>
                      <td
                        style={{
                          padding: "12px 15px",
                          textAlign: "right",
                          color: isPositive
                            ? bloombergColors.positive
                            : bloombergColors.negative,
                          fontWeight: "bold",
                        }}
                      >
                        {typeof stock.change === "number"
                          ? stock.change.toFixed(2)
                          : "N/A"}
                      </td>
                      <td
                        style={{
                          padding: "12px 15px",
                          textAlign: "right",
                          color: isPositive
                            ? bloombergColors.positive
                            : bloombergColors.negative,
                          fontWeight: "bold",
                        }}
                      >
                        {typeof stock.change_percent === "number"
                          ? stock.change_percent.toFixed(2) + "%"
                          : "N/A"}
                      </td>
                      {showVolume && (
                        <td
                          style={{
                            padding: "12px 15px",
                            textAlign: "right",
                            color: bloombergColors.text,
                            fontSize: "12px",
                          }}
                        >
                          {stock.volume
                            ? stock.volume >= 10000000
                              ? `${(stock.volume / 10000000).toFixed(1)}Cr`
                              : stock.volume >= 100000
                              ? `${(stock.volume / 100000).toFixed(1)}L`
                              : stock.volume.toLocaleString()
                            : "N/A"}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Table Footer */}
            <div
              style={{
                padding: "10px 15px",
                backgroundColor: bloombergColors.tableHeader,
                borderTop: `1px solid ${bloombergColors.border}`,
                fontSize: "12px",
                color: bloombergColors.text,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>
                Showing {Math.min(data.length, maxItems)} of {data.length}{" "}
                stocks
              </span>
              <span>Updated: {new Date().toLocaleTimeString()}</span>
            </div>
          </div>
        )}
      </div>
    );
  }
);

StocksList.displayName = "StocksList";

export default StocksList;
