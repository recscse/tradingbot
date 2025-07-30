// components/debug/DebugPanel.jsx - Add this debug component

import React from "react";

const DebugPanel = ({
  isConnected,
  connectionStatus,
  topMovers,
  gapAnalysis,
  heatmap,
  volumeAnalysis,
  intradayStocks,
  recordMovers,
  marketData,
}) => {
  const bloombergColors = {
    background: "#0f0f12",
    text: "#e6e6e6",
    positive: "#00ff00",
    negative: "#ff0000",
    header: "#00b0f0",
    border: "#333333",
    cardBackground: "#1a1a1a",
  };

  const debugInfo = {
    connection: {
      isConnected,
      status: connectionStatus,
    },
    analytics: {
      topMovers: {
        gainers: topMovers?.gainers?.length || 0,
        losers: topMovers?.losers?.length || 0,
        hasData: !!(topMovers?.gainers?.length || topMovers?.losers?.length),
      },
      gapAnalysis: {
        gap_up: gapAnalysis?.gap_up?.length || 0,
        gap_down: gapAnalysis?.gap_down?.length || 0,
        hasData: !!(
          gapAnalysis?.gap_up?.length || gapAnalysis?.gap_down?.length
        ),
      },
      heatmap: {
        sectors: heatmap?.sectors?.length || 0,
        hasData: !!heatmap?.sectors?.length,
      },
      volumeAnalysis: {
        volume_leaders: volumeAnalysis?.volume_leaders?.length || 0,
        hasData: !!volumeAnalysis?.volume_leaders?.length,
      },
      intradayStocks: {
        all_candidates: intradayStocks?.all_candidates?.length || 0,
        hasData: !!intradayStocks?.all_candidates?.length,
      },
      recordMovers: {
        new_highs: recordMovers?.new_highs?.length || 0,
        new_lows: recordMovers?.new_lows?.length || 0,
        hasData: !!(
          recordMovers?.new_highs?.length || recordMovers?.new_lows?.length
        ),
      },
    },
    marketData: {
      total_instruments: Object.keys(marketData || {}).length,
      hasData: Object.keys(marketData || {}).length > 0,
      sample_keys: Object.keys(marketData || {}).slice(0, 3),
    },
  };

  return (
    <div
      style={{
        position: "fixed",
        top: "10px",
        right: "10px",
        width: "300px",
        maxHeight: "400px",
        overflow: "auto",
        backgroundColor: bloombergColors.cardBackground,
        border: `1px solid ${bloombergColors.border}`,
        borderRadius: "6px",
        padding: "15px",
        fontSize: "11px",
        color: bloombergColors.text,
        fontFamily: "'Courier New', monospace",
        zIndex: 9999,
        boxShadow: "0 4px 15px rgba(0, 0, 0, 0.5)",
      }}
    >
      <h4
        style={{
          color: bloombergColors.header,
          marginBottom: "10px",
          fontSize: "12px",
          fontWeight: "bold",
        }}
      >
        🔧 DEBUG PANEL
      </h4>

      <div style={{ marginBottom: "10px" }}>
        <strong>Connection:</strong>
        <div
          style={{
            color: isConnected
              ? bloombergColors.positive
              : bloombergColors.negative,
            fontWeight: "bold",
          }}
        >
          {connectionStatus.toUpperCase()}
        </div>
      </div>

      <div style={{ marginBottom: "10px" }}>
        <strong>Market Data:</strong>
        <div style={{ marginLeft: "10px" }}>
          <div>Total: {debugInfo.marketData.total_instruments}</div>
          <div
            style={{
              color: debugInfo.marketData.hasData
                ? bloombergColors.positive
                : bloombergColors.negative,
            }}
          >
            Status: {debugInfo.marketData.hasData ? "✓ HAS DATA" : "✗ NO DATA"}
          </div>
          {debugInfo.marketData.sample_keys.length > 0 && (
            <div style={{ fontSize: "10px", opacity: 0.7 }}>
              Sample: {debugInfo.marketData.sample_keys.join(", ")}
            </div>
          )}
        </div>
      </div>

      <div style={{ marginBottom: "10px" }}>
        <strong>Analytics Data:</strong>
        <div style={{ marginLeft: "10px" }}>
          {Object.entries(debugInfo.analytics).map(([key, info]) => (
            <div
              key={key}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "2px",
              }}
            >
              <span>{key}:</span>
              <span
                style={{
                  color: info.hasData
                    ? bloombergColors.positive
                    : bloombergColors.negative,
                  fontWeight: "bold",
                }}
              >
                {info.hasData ? "✓" : "✗"}
                {typeof info === "object" && (
                  <span style={{ marginLeft: "5px", fontSize: "10px" }}>
                    (
                    {Object.values(info)
                      .filter((v) => typeof v === "number")
                      .reduce((a, b) => a + b, 0)}
                    )
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: "10px" }}>
        <strong>Raw Data Check:</strong>
        <div style={{ fontSize: "10px", marginLeft: "10px" }}>
          <div>Top Movers: {JSON.stringify(topMovers).slice(0, 50)}...</div>
          <div>Heatmap: {JSON.stringify(heatmap).slice(0, 50)}...</div>
        </div>
      </div>

      <div
        style={{
          fontSize: "10px",
          opacity: 0.7,
          borderTop: `1px solid ${bloombergColors.border}`,
          paddingTop: "5px",
          marginTop: "10px",
        }}
      >
        Last Update: {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
};

export default DebugPanel;
