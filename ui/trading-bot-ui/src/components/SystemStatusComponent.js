import React, { useState, useEffect } from "react";
import { useMarket } from "../contexts/MarketContext";

const SystemStatusComponent = () => {
  const {
    systemMode,
    connectionStatus,
    systemCapabilities,
    dataMetrics,
    switchToCentralizedMode,
    switchToLegacyMode,
    switchToAutoMode,
    forceReconnect,
    getSystemHealth,
    selectedStocks,
  } = useMarket();

  const [systemHealth, setSystemHealth] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  // Fetch system health periodically
  useEffect(() => {
    const fetchHealth = async () => {
      const health = await getSystemHealth();
      setSystemHealth(health);
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, [getSystemHealth]);

  const getStatusColor = (status) => {
    switch (status) {
      case "connected":
        return "text-green-600";
      case "connecting":
        return "text-yellow-600";
      case "disconnected":
        return "text-gray-500";
      case "error":
        return "text-red-600";
      default:
        return "text-gray-400";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "connected":
        return "🟢";
      case "connecting":
        return "🟡";
      case "disconnected":
        return "⚪";
      case "error":
        return "🔴";
      default:
        return "⚫";
    }
  };

  const getModeDisplayName = (mode) => {
    switch (mode) {
      case "centralized":
        return "NEW Centralized System";
      case "legacy":
        return "Legacy System";
      case "auto":
        return "Auto-Detection";
      default:
        return mode;
    }
  };

  const getModeDescription = (mode) => {
    switch (mode) {
      case "centralized":
        return "✅ Using single admin WebSocket connection. Unlimited users, no rate limits, automatic market closure handling.";
      case "legacy":
        return "⚠️ Using individual WebSocket connections. Limited by rate limits and manual market closure handling.";
      case "auto":
        return "🔍 Automatically detecting and selecting the best available system.";
      default:
        return "Unknown mode";
    }
  };

  const getRecommendation = () => {
    if (
      systemCapabilities.centralized_ws_available &&
      systemCapabilities.admin_token_configured
    ) {
      if (systemMode !== "centralized") {
        return {
          type: "upgrade",
          message:
            "🚀 Upgrade Recommended: Switch to NEW Centralized System for better performance!",
          action: switchToCentralizedMode,
          actionText: "Switch to Centralized",
        };
      }
      return {
        type: "optimal",
        message: "✅ Optimal: You're using the best available system!",
      };
    } else if (systemCapabilities.centralized_ws_available) {
      return {
        type: "setup",
        message:
          "⚙️ Setup Required: Centralized system available but admin token not configured.",
      };
    } else {
      return {
        type: "legacy",
        message:
          "ℹ️ Legacy Mode: Centralized system not available, using legacy WebSocket.",
      };
    }
  };

  const recommendation = getRecommendation();

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-800">
          Market Data System Status
        </h3>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          {showDetails ? "Hide Details" : "Show Details"}
        </button>
      </div>

      {/* Current Mode */}
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-gray-600">
              Current Mode:
            </span>
            <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
              {getModeDisplayName(systemMode)}
            </span>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={switchToAutoMode}
              className={`px-3 py-1 text-xs rounded ${
                systemMode === "auto"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              Auto
            </button>
            {systemCapabilities.centralized_ws_available && (
              <button
                onClick={switchToCentralizedMode}
                className={`px-3 py-1 text-xs rounded ${
                  systemMode === "centralized"
                    ? "bg-green-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                Centralized
              </button>
            )}
            <button
              onClick={switchToLegacyMode}
              className={`px-3 py-1 text-xs rounded ${
                systemMode === "legacy"
                  ? "bg-orange-600 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              Legacy
            </button>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          {getModeDescription(systemMode)}
        </p>
      </div>

      {/* Recommendation */}
      <div
        className={`p-3 rounded-lg mb-4 ${
          recommendation.type === "upgrade"
            ? "bg-blue-50 border border-blue-200"
            : recommendation.type === "optimal"
            ? "bg-green-50 border border-green-200"
            : recommendation.type === "setup"
            ? "bg-yellow-50 border border-yellow-200"
            : "bg-gray-50 border border-gray-200"
        }`}
      >
        <p className="text-sm">{recommendation.message}</p>
        {recommendation.action && (
          <button
            onClick={recommendation.action}
            className="mt-2 px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
          >
            {recommendation.actionText}
          </button>
        )}
      </div>

      {/* Connection Status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {systemMode === "centralized" && (
          <>
            <div className="text-center">
              <div
                className={`text-sm font-medium ${getStatusColor(
                  connectionStatus.centralized_dashboard
                )}`}
              >
                {getStatusIcon(connectionStatus.centralized_dashboard)}{" "}
                Dashboard
              </div>
              <div className="text-xs text-gray-500">All Stocks</div>
            </div>
            <div className="text-center">
              <div
                className={`text-sm font-medium ${getStatusColor(
                  connectionStatus.centralized_trading
                )}`}
              >
                {getStatusIcon(connectionStatus.centralized_trading)} Trading
              </div>
              <div className="text-xs text-gray-500">
                {selectedStocks.length} Stocks
              </div>
            </div>
          </>
        )}
        {systemMode === "legacy" && (
          <div className="text-center">
            <div
              className={`text-sm font-medium ${getStatusColor(
                connectionStatus.legacy
              )}`}
            >
              {getStatusIcon(connectionStatus.legacy)} Legacy
            </div>
            <div className="text-xs text-gray-500">Individual Connections</div>
          </div>
        )}
        {systemMode === "auto" && (
          <div className="text-center">
            <div
              className={`text-sm font-medium ${getStatusColor(
                connectionStatus.auto_detection
              )}`}
            >
              {getStatusIcon(connectionStatus.auto_detection)} Detection
            </div>
            <div className="text-xs text-gray-500">Auto-detecting</div>
          </div>
        )}
      </div>

      {/* Data Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="text-center">
          <div className="text-lg font-bold text-gray-800">
            {dataMetrics.updates_per_minute}
          </div>
          <div className="text-xs text-gray-500">Updates/min</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-gray-800">
            {dataMetrics.instruments_count}
          </div>
          <div className="text-xs text-gray-500">Instruments</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-gray-800">
            {dataMetrics.latency_ms}ms
          </div>
          <div className="text-xs text-gray-500">Latency</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-gray-800">
            {dataMetrics.data_source?.split("_")[0] || "N/A"}
          </div>
          <div className="text-xs text-gray-500">Source</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex space-x-2 mb-4">
        <button
          onClick={forceReconnect}
          className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          🔄 Reconnect
        </button>
        <button
          onClick={() =>
            window.open(`${process.env.REACT_APP_API_URL}/health`, "_blank")
          }
          className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
        >
          📊 System Health
        </button>
      </div>

      {/* Detailed Information */}
      {showDetails && (
        <div className="border-t pt-4">
          <h4 className="font-medium text-gray-800 mb-3">
            System Capabilities
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <div className="flex items-center">
              <span
                className={
                  systemCapabilities.centralized_ws_available
                    ? "text-green-600"
                    : "text-red-600"
                }
              >
                {systemCapabilities.centralized_ws_available ? "✅" : "❌"}
              </span>
              <span className="ml-2 text-sm">
                Centralized WebSocket Available
              </span>
            </div>
            <div className="flex items-center">
              <span
                className={
                  systemCapabilities.admin_token_configured
                    ? "text-green-600"
                    : "text-red-600"
                }
              >
                {systemCapabilities.admin_token_configured ? "✅" : "❌"}
              </span>
              <span className="ml-2 text-sm">Admin Token Configured</span>
            </div>
            <div className="flex items-center">
              <span
                className={
                  systemCapabilities.market_closure_aware
                    ? "text-green-600"
                    : "text-red-600"
                }
              >
                {systemCapabilities.market_closure_aware ? "✅" : "❌"}
              </span>
              <span className="ml-2 text-sm">Market Closure Aware</span>
            </div>
            <div className="flex items-center">
              <span
                className={
                  systemCapabilities.unlimited_scaling
                    ? "text-green-600"
                    : "text-red-600"
                }
              >
                {systemCapabilities.unlimited_scaling ? "✅" : "❌"}
              </span>
              <span className="ml-2 text-sm">Unlimited Scaling</span>
            </div>
            <div className="flex items-center">
              <span
                className={
                  systemCapabilities.rate_limit_protection
                    ? "text-green-600"
                    : "text-red-600"
                }
              >
                {systemCapabilities.rate_limit_protection ? "✅" : "❌"}
              </span>
              <span className="ml-2 text-sm">Rate Limit Protection</span>
            </div>
          </div>

          {systemHealth && (
            <>
              <h4 className="font-medium text-gray-800 mb-3">System Health</h4>
              <div className="bg-gray-50 p-3 rounded text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <strong>Overall Status:</strong>
                    <span
                      className={`ml-1 ${
                        systemHealth.overall_status === "healthy"
                          ? "text-green-600"
                          : systemHealth.overall_status === "degraded"
                          ? "text-yellow-600"
                          : "text-red-600"
                      }`}
                    >
                      {systemHealth.overall_status?.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <strong>Health Score:</strong>
                    <span className="ml-1">
                      {systemHealth.overall_health_score || 0}/100
                    </span>
                  </div>
                  <div>
                    <strong>Architecture:</strong>
                    <span className="ml-1">{systemHealth.architecture}</span>
                  </div>
                  <div>
                    <strong>Version:</strong>
                    <span className="ml-1">{systemHealth.version}</span>
                  </div>
                </div>
              </div>
            </>
          )}

          <div className="mt-4">
            <h4 className="font-medium text-gray-800 mb-2">Data Flow</h4>
            <div className="text-sm text-gray-600">
              {systemMode === "centralized" ? (
                <div>
                  <p>
                    📊 <strong>Dashboard:</strong> Admin WebSocket → All market
                    data → Instant display
                  </p>
                  <p>
                    🎯 <strong>Trading:</strong> Admin WebSocket → Filtered data
                    → Selected stocks only
                  </p>
                  <p>
                    ⚡ <strong>Benefits:</strong> No rate limits, unlimited
                    users, automatic market closure handling
                  </p>
                </div>
              ) : systemMode === "legacy" ? (
                <div>
                  <p>
                    🔄 <strong>Legacy:</strong> Individual WebSocket per user →
                    Rate limited → Manual handling
                  </p>
                  <p>
                    ⚠️ <strong>Limitations:</strong> Connection limits, rate
                    limits, manual market closure handling
                  </p>
                </div>
              ) : (
                <div>
                  <p>
                    🔍 <strong>Auto:</strong> Detecting best available system...
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="mt-4">
            <h4 className="font-medium text-gray-800 mb-2">Last Update</h4>
            <div className="text-sm text-gray-600">
              {dataMetrics.last_update_time ? (
                <>
                  {new Date(dataMetrics.last_update_time).toLocaleTimeString()}
                  <span className="ml-2">({dataMetrics.data_source})</span>
                </>
              ) : (
                "No data received yet"
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemStatusComponent;
