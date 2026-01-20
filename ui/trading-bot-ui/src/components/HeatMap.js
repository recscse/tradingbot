import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Search,
  TrendingUp,
  TrendingDown,
  Activity,
  RefreshCw,
  Settings,
  Wifi,
  WifiOff,
} from "lucide-react";

const EnhancedHeatmapComponent = () => {
  const [heatmapData, setHeatmapData] = useState(null);
  const [sectorSummary, setSectorSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [hoveredCell, setHoveredCell] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [wsConnected, setWsConnected] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Settings
  const [settings, setSettings] = useState({
    width: 1200,
    height: 800,
    colorMetric: "change_percent",
    sizeMetric: "market_cap",
    autoRefresh: true,
    refreshInterval: 30,
    minChange: null,
    minVolume: null,
    selectedSectors: [],
  });

  const containerRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws/heatmap`;

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log("🔥 Heatmap WebSocket connected");
        setWsConnected(true);
        setReconnectAttempts(0);
        setError(null);

        // Send initial message to get data
        wsRef.current.send(
          JSON.stringify({
            type: "get_heatmap",
            width: settings.width,
            height: settings.height,
          })
        );
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log("🔥 Heatmap WebSocket closed:", event.code, event.reason);
        setWsConnected(false);

        // Attempt to reconnect
        if (reconnectAttempts < 5) {
          const timeout = Math.min(
            1000 * Math.pow(2, reconnectAttempts),
            30000
          );
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts((prev) => prev + 1);
            connectWebSocket();
          }, timeout);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("🔥 Heatmap WebSocket error:", error);
        setError("WebSocket connection error");
      };
    } catch (err) {
      console.error("Error creating WebSocket connection:", err);
      setError("Failed to create WebSocket connection");
    }
  }, [settings.width, settings.height, reconnectAttempts]);

  // Handle WebSocket messages
  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case "initial_heatmap":
        setHeatmapData(message.data.heatmap.data);
        setSectorSummary(message.data.sector_summary.data);
        setLoading(false);
        break;

      case "heatmap_update":
        setHeatmapData(message.data.heatmap.data);
        setSectorSummary(message.data.sector_summary.data);
        break;

      case "heatmap_data":
        setHeatmapData(message.data.data);
        setLoading(false);
        break;

      case "sector_summary":
        setSectorSummary(message.data.data);
        break;

      case "preferences_updated":
        setHeatmapData(message.data.heatmap.data);
        break;

      case "error":
        setError(message.message);
        setLoading(false);
        break;

      default:
        console.log("Unknown message type:", message.type);
    }
  };

  // REST API fallback
  const fetchHeatmapData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        width: settings.width,
        height: settings.height,
      });

      if (settings.minChange !== null)
        params.append("min_change", settings.minChange);
      if (settings.minVolume !== null)
        params.append("min_volume", settings.minVolume);
      if (settings.selectedSectors.length > 0) {
        params.append("sectors", settings.selectedSectors.join(","));
      }

      const response = await fetch(`/api/heatmap/enhanced?${params}`);
      const result = await response.json();

      if (result.success) {
        setHeatmapData(result.data);
      } else {
        setError(result.message || "Failed to fetch heatmap data");
      }
    } catch (err) {
      setError("Error connecting to server: " + err.message);
    } finally {
      setLoading(false);
    }
  }, [settings]);

  // Initialize connections
  useEffect(() => {
    if (settings.autoRefresh) {
      connectWebSocket();
    } else {
      fetchHeatmapData();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [settings.autoRefresh, connectWebSocket, fetchHeatmapData]);

  // Update WebSocket preferences when settings change
  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "update_preferences",
          preferences: {
            width: settings.width,
            height: settings.height,
            refresh_interval: settings.refreshInterval,
          },
        })
      );
    }
  }, [settings.width, settings.height, settings.refreshInterval]);

  // Filter cells based on search term and settings
  const filteredCells =
    heatmapData?.cells?.filter((cell) => {
      const matchesSearch =
        !searchTerm ||
        cell.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        cell.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        cell.sector.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesMinChange =
        settings.minChange === null ||
        Math.abs(cell.change_percent || 0) >= settings.minChange;

      const matchesMinVolume =
        settings.minVolume === null || (cell.volume || 0) >= settings.minVolume;

      const matchesSectors =
        settings.selectedSectors.length === 0 ||
        settings.selectedSectors.includes(cell.sector_key);

      return (
        matchesSearch && matchesMinChange && matchesMinVolume && matchesSectors
      );
    }) || [];

  // Handle cell hover
  const handleCellHover = (cell, event) => {
    if (event) {
      const rect = containerRef.current?.getBoundingClientRect();
      setTooltipPosition({
        x: event.clientX - (rect?.left || 0),
        y: event.clientY - (rect?.top || 0),
      });
    }
    setHoveredCell(cell);
  };

  // Handle cell click
  const handleCellClick = (cell) => {
    console.log("Cell clicked:", cell);
    // You can add navigation to stock details page here
    // Example: navigate(`/stock/${cell.symbol}`);
  };

  // Manual refresh
  const handleRefresh = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "get_heatmap",
          width: settings.width,
          height: settings.height,
        })
      );
    } else {
      fetchHeatmapData();
    }
  };

  // Toggle WebSocket connection
  const toggleConnection = () => {
    if (wsConnected) {
      if (wsRef.current) {
        wsRef.current.close();
      }
      setSettings((prev) => ({ ...prev, autoRefresh: false }));
    } else {
      setSettings((prev) => ({ ...prev, autoRefresh: true }));
      connectWebSocket();
    }
  };

  // Update settings
  const updateSettings = (newSettings) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
  };

  // Format number for display
  const formatNumber = (num, decimals = 2) => {
    if (num === null || num === undefined) return "N/A";
    if (num >= 1e9) return (num / 1e9).toFixed(1) + "B";
    if (num >= 1e6) return (num / 1e6).toFixed(1) + "M";
    if (num >= 1e3) return (num / 1e3).toFixed(1) + "K";
    return Number(num).toFixed(decimals);
  };

  // Format percentage
  const formatPercent = (num) => {
    if (num === null || num === undefined) return "N/A";
    const sign = num >= 0 ? "+" : "";
    return `${sign}${Number(num).toFixed(2)}%`;
  };

  // Get cell font size based on cell dimensions
  const getCellFontSize = (width, height) => {
    const area = width * height;
    if (area > 15000) return "16px";
    if (area > 10000) return "14px";
    if (area > 5000) return "12px";
    if (area > 2000) return "10px";
    return "8px";
  };

  // Get text color based on background
  const getTextColor = (backgroundColor) => {
    const hex = backgroundColor.replace("#", "");
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? "#000000" : "#ffffff";
  };

  const stats = heatmapData?.stats || {};
  const availableSectors =
    sectorSummary?.sectors?.map((s) => ({ key: s.key, name: s.sector })) || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-900 text-white">
        <div className="flex items-center space-x-3">
          <RefreshCw className="w-6 h-6 animate-spin" />
          <span className="text-lg">Loading Heatmap...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 text-gray-100 min-h-screen font-sans">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-100">
                  Market Heatmap
                </h1>
                <p className="text-sm text-gray-400">
                  Real-time sector and stock performance
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              {wsConnected ? (
                <Wifi className="w-4 h-4 text-green-400" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-400" />
              )}
              <span
                className={`text-xs ${
                  wsConnected ? "text-green-400" : "text-red-400"
                }`}
              >
                {wsConnected ? "Live" : "Offline"}
              </span>
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search stocks, sectors..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:border-blue-500 w-64"
              />
            </div>

            {/* Settings Button */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="px-3 py-2 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-lg transition-colors flex items-center space-x-2"
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>

            {/* Connection Toggle */}
            <button
              onClick={toggleConnection}
              className={`px-4 py-2 rounded-lg transition-colors flex items-center space-x-2 ${
                wsConnected
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-red-600 hover:bg-red-700"
              }`}
            >
              {wsConnected ? (
                <Wifi className="w-4 h-4" />
              ) : (
                <WifiOff className="w-4 h-4" />
              )}
              <span>{wsConnected ? "Disconnect" : "Connect"}</span>
            </button>

            {/* Refresh Button */}
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors flex items-center space-x-2"
            >
              <RefreshCw
                className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
              />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Dimensions
              </label>
              <div className="flex space-x-2">
                <input
                  type="number"
                  placeholder="Width"
                  value={settings.width}
                  onChange={(e) =>
                    updateSettings({ width: parseInt(e.target.value) || 1200 })
                  }
                  className="w-20 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm"
                />
                <input
                  type="number"
                  placeholder="Height"
                  value={settings.height}
                  onChange={(e) =>
                    updateSettings({ height: parseInt(e.target.value) || 800 })
                  }
                  className="w-20 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Min Change %
              </label>
              <input
                type="number"
                step="0.1"
                placeholder="Any"
                value={settings.minChange || ""}
                onChange={(e) =>
                  updateSettings({
                    minChange: e.target.value
                      ? parseFloat(e.target.value)
                      : null,
                  })
                }
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Min Volume
              </label>
              <input
                type="number"
                placeholder="Any"
                value={settings.minVolume || ""}
                onChange={(e) =>
                  updateSettings({
                    minVolume: e.target.value ? parseInt(e.target.value) : null,
                  })
                }
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Sectors
              </label>
              <select
                multiple
                value={settings.selectedSectors}
                onChange={(e) =>
                  updateSettings({
                    selectedSectors: Array.from(
                      e.target.selectedOptions,
                      (option) => option.value
                    ),
                  })
                }
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm"
                size="1"
              >
                <option value="">All Sectors</option>
                {availableSectors.map((sector) => (
                  <option key={sector.key} value={sector.key}>
                    {sector.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Auto Refresh
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={settings.autoRefresh}
                  onChange={(e) =>
                    updateSettings({ autoRefresh: e.target.checked })
                  }
                  className="rounded bg-gray-700 border-gray-600"
                />
                <span className="text-sm">Enabled</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Bar */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-3">
        <div className="flex justify-between items-center">
          <div className="flex space-x-6 text-sm">
            <div className="flex items-center space-x-2">
              <span className="text-gray-400">Total Stocks:</span>
              <span className="font-mono font-semibold">
                {stats.total_stocks || 0}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <span className="text-green-400 font-mono font-semibold">
                {stats.gainers || 0}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <TrendingDown className="w-4 h-4 text-red-400" />
              <span className="text-red-400 font-mono font-semibold">
                {stats.losers || 0}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-gray-400">Unchanged:</span>
              <span className="text-gray-400 font-mono font-semibold">
                {stats.unchanged || 0}
              </span>
            </div>
            {searchTerm && (
              <div className="flex items-center space-x-2">
                <span className="text-gray-400">Filtered:</span>
                <span className="text-blue-400 font-mono font-semibold">
                  {filteredCells.length}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-4 text-xs">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-600 rounded"></div>
              <span>Strong Positive (&gt;5%)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-400 rounded"></div>
              <span>Positive (&gt;2%)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-gray-500 rounded"></div>
              <span>Neutral</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-400 rounded"></div>
              <span>Negative (&lt;-2%)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-600 rounded"></div>
              <span>Strong Negative (&lt;-5%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-900 border-l-4 border-red-500 p-4 mx-6 mt-4 rounded">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-300">{error}</p>
            </div>
            <div className="ml-auto">
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-300"
              >
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Heatmap Container */}
      <div
        ref={containerRef}
        className="relative bg-gray-900 overflow-hidden"
        style={{ height: "calc(100vh - 220px)" }}
        onMouseLeave={() => setHoveredCell(null)}
      >
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${settings.width} ${settings.height}`}
          className="w-full h-full"
        >
          {filteredCells.map((cell, index) => {
            const fontSize = getCellFontSize(cell.width, cell.height);
            const textColor = getTextColor(cell.color);
            const isSmallCell = cell.width < 80 || cell.height < 50;
            const isMediumCell = cell.width < 120 || cell.height < 70;

            return (
              <g key={`${cell.symbol}-${index}`}>
                {/* Cell Rectangle */}
                <rect
                  x={cell.x}
                  y={cell.y}
                  width={cell.width}
                  height={cell.height}
                  fill={cell.color}
                  stroke="#131722"
                  strokeWidth="1"
                  className="cursor-pointer transition-all duration-200 hover:stroke-blue-400 hover:stroke-2"
                  onMouseEnter={(e) => handleCellHover(cell, e.nativeEvent)}
                  onClick={() => handleCellClick(cell)}
                />

                {/* Cell Content */}
                {!isSmallCell && (
                  <>
                    {/* Symbol */}
                    <text
                      x={cell.x + 6}
                      y={cell.y + 18}
                      fontSize={fontSize}
                      fontFamily="JetBrains Mono, monospace"
                      fontWeight="600"
                      fill={textColor}
                      className="pointer-events-none select-none"
                    >
                      {cell.symbol}
                    </text>

                    {/* Change Percentage */}
                    <text
                      x={cell.x + cell.width - 6}
                      y={cell.y + 18}
                      fontSize={parseInt(fontSize) - 1 + "px"}
                      fontFamily="JetBrains Mono, monospace"
                      fontWeight="600"
                      fill={textColor}
                      textAnchor="end"
                      className="pointer-events-none select-none"
                    >
                      {formatPercent(cell.change_percent)}
                    </text>

                    {/* Company Name (for larger cells) */}
                    {!isMediumCell && (
                      <text
                        x={cell.x + 6}
                        y={cell.y + 36}
                        fontSize={parseInt(fontSize) - 2 + "px"}
                        fill={textColor}
                        className="pointer-events-none select-none"
                        style={{ opacity: 0.8 }}
                      >
                        {cell.name.length > 20
                          ? cell.name.substring(0, 17) + "..."
                          : cell.name}
                      </text>
                    )}

                    {/* Price */}
                    <text
                      x={cell.x + 6}
                      y={cell.y + cell.height - 10}
                      fontSize={parseInt(fontSize) - 1 + "px"}
                      fontFamily="JetBrains Mono, monospace"
                      fontWeight="600"
                      fill={textColor}
                      className="pointer-events-none select-none"
                    >
                      ₹{formatNumber(cell.price)}
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {hoveredCell && (
          <div
            className="absolute bg-gray-800 border border-gray-600 rounded-lg p-4 shadow-xl z-50 pointer-events-none min-w-64"
            style={{
              left: tooltipPosition.x + 15,
              top: tooltipPosition.y - 15,
              transform:
                tooltipPosition.x > settings.width * 0.6
                  ? "translateX(-100%)"
                  : "none",
            }}
          >
            <div className="font-semibold text-gray-100 mb-3 text-lg">
              {hoveredCell.symbol}
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Company:</span>
                <span className="text-gray-100 font-medium max-w-40 truncate">
                  {hoveredCell.name}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Sector:</span>
                <span className="text-blue-400 font-medium">
                  {hoveredCell.sector}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Price:</span>
                <span className="text-gray-100 font-mono font-semibold">
                  ₹{formatNumber(hoveredCell.price)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Change:</span>
                <span
                  className={`font-mono font-semibold ${
                    hoveredCell.change_percent >= 0
                      ? "text-green-400"
                      : "text-red-400"
                  }`}
                >
                  {formatPercent(hoveredCell.change_percent)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Volume:</span>
                <span className="text-gray-100 font-mono">
                  {formatNumber(hoveredCell.volume)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Market Cap:</span>
                <span className="text-gray-100 font-mono">
                  ₹{formatNumber(hoveredCell.market_cap)} Cr
                </span>
              </div>
              {hoveredCell.lot_size > 0 && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Lot Size:</span>
                  <span className="text-gray-100 font-mono">
                    {hoveredCell.lot_size}
                  </span>
                </div>
              )}
              {hoveredCell.subcategory && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Category:</span>
                  <span className="text-gray-100">
                    {hoveredCell.subcategory}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Loading Overlay */}
        {loading && (
          <div className="absolute inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center">
            <div className="flex items-center space-x-3 text-white">
              <RefreshCw className="w-8 h-8 animate-spin" />
              <span className="text-xl">Updating Heatmap...</span>
            </div>
          </div>
        )}

        {/* No Data Message */}
        {!loading && filteredCells.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-gray-400">
              <Activity className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <h3 className="text-xl mb-2">No Data Available</h3>
              <p className="text-sm mb-4">
                {searchTerm ||
                settings.minChange ||
                settings.minVolume ||
                settings.selectedSectors.length > 0
                  ? "No stocks match your filter criteria"
                  : "No market data available"}
              </p>
              {(searchTerm ||
                settings.minChange ||
                settings.minVolume ||
                settings.selectedSectors.length > 0) && (
                <button
                  onClick={() => {
                    setSearchTerm("");
                    updateSettings({
                      minChange: null,
                      minVolume: null,
                      selectedSectors: [],
                    });
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                  Clear All Filters
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Sector Summary Panel */}
      {sectorSummary?.sectors && (
        <div className="absolute top-32 left-4 space-y-2 z-40 max-h-96 overflow-y-auto bg-gray-800 bg-opacity-95 rounded-lg p-3">
          <h4 className="font-semibold text-gray-100 mb-2 text-sm">
            Sector Performance
          </h4>
          {sectorSummary.sectors.slice(0, 12).map((sector, index) => (
            <div
              key={sector.key}
              className="bg-gray-700 bg-opacity-80 border border-gray-600 rounded px-3 py-2 text-xs hover:bg-gray-600 transition-colors cursor-pointer"
              style={{ minWidth: "200px" }}
              onClick={() => {
                const sectorFilter = settings.selectedSectors.includes(
                  sector.key
                )
                  ? settings.selectedSectors.filter((s) => s !== sector.key)
                  : [...settings.selectedSectors, sector.key];
                updateSettings({ selectedSectors: sectorFilter });
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-2">
                  <span>{sector.icon}</span>
                  <span className="font-medium">{sector.sector}</span>
                </div>
                <span
                  className={`font-mono font-semibold ${
                    sector.avg_change >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {formatPercent(sector.avg_change)}
                </span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>{sector.total_stocks} stocks</span>
                <div className="flex space-x-2">
                  <span className="text-green-400">{sector.gainers}↑</span>
                  <span className="text-red-400">{sector.losers}↓</span>
                </div>
              </div>
              {settings.selectedSectors.includes(sector.key) && (
                <div className="text-blue-400 text-xs mt-1">✓ Filtered</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Status Bar */}
      <div className="absolute bottom-4 right-4 bg-gray-800 bg-opacity-95 border border-gray-600 rounded-lg px-3 py-2 text-xs">
        <div className="flex items-center space-x-4 text-gray-400">
          <span>
            Last Update:{" "}
            {heatmapData?.timestamp
              ? new Date(heatmapData.timestamp).toLocaleTimeString()
              : "Never"}
          </span>
          <span>•</span>
          <span>{wsConnected ? "Live Updates" : "Manual Refresh"}</span>
          {wsConnected && (
            <>
              <span>•</span>
              <span className="text-green-400">Connected</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnhancedHeatmapComponent;