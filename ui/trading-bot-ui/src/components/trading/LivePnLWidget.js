import React, { useState, useEffect } from "react";
import { useUnifiedMarketData } from "../../hooks/useUnifiedMarketData";
import { Minimize2, Maximize2, TrendingUp, TrendingDown, X } from "lucide-react";

/**
 * LivePnLWidget - Compact floating widget displaying live P&L for active positions
 *
 * Features:
 * - Always visible on screen (floating)
 * - Draggable and resizable
 * - Real-time P&L updates via WebSocket
 * - Responsive on all screen sizes
 * - Tailwind CSS styling
 */
const LivePnLWidget = () => {
  const { marketData, isConnected } = useUnifiedMarketData();
  const [positions, setPositions] = useState([]);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [totalPnL, setTotalPnL] = useState(0);

  useEffect(() => {
    fetch_active_positions();
  }, []);

  useEffect(() => {
    if (positions.length > 0 && marketData) {
      calculate_total_pnl();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positions, marketData]);

  const fetch_active_positions = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/v1/trading/execution/active-positions`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();

        if (Array.isArray(data)) {
          setPositions(data);
        } else if (data && Array.isArray(data.positions)) {
          setPositions(data.positions);
        } else if (data && typeof data === 'object') {
          setPositions([data]);
        } else {
          setPositions([]);
        }
      }
    } catch (error) {
      console.error("Error fetching positions:", error);
      setPositions([]);
    }
  };

  const calculate_total_pnl = () => {
    let total = 0;

    positions.forEach((position) => {
      const current_price = marketData[position.instrument_key]?.ltp ||
                           marketData[position.symbol]?.ltp ||
                           position.current_price ||
                           position.entry_price;

      const signal_type = position.signal_type || position.trade_type || "BUY";
      const quantity = position.quantity || 1;
      const entry_price = position.entry_price || 0;

      const pnl = (current_price - entry_price) * quantity * (signal_type === "BUY" ? 1 : -1);
      total += pnl;
    });

    setTotalPnL(total);
  };

  const get_position_pnl = (position) => {
    const current_price = marketData[position.instrument_key]?.ltp ||
                         marketData[position.symbol]?.ltp ||
                         position.current_price ||
                         position.entry_price;

    const signal_type = position.signal_type || position.trade_type || "BUY";
    const quantity = position.quantity || 1;
    const entry_price = position.entry_price || 0;

    const pnl = (current_price - entry_price) * quantity * (signal_type === "BUY" ? 1 : -1);
    const pnl_percent = ((current_price - entry_price) / entry_price) * 100 * (signal_type === "BUY" ? 1 : -1);

    return { pnl, pnl_percent, current_price, signal_type };
  };

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 right-4 z-50 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-2 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 flex items-center gap-2"
      >
        <TrendingUp className="w-4 h-4" />
        <span className="text-sm font-semibold">Show P&L</span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-80 sm:w-96 max-w-full">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-lg shadow-2xl border border-gray-700 overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-3 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
            <h3 className="text-white text-sm font-bold">Live P&L</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="text-white hover:bg-blue-600 rounded p-1 transition-colors"
            >
              {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setIsVisible(false)}
              className="text-white hover:bg-blue-600 rounded p-1 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="px-3 py-2 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <span className="text-gray-300 text-xs font-medium">Total P&L</span>
            <div className="flex items-center gap-1">
              {totalPnL >= 0 ? (
                <TrendingUp className="w-4 h-4 text-green-400" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-400" />
              )}
              <span className={`text-lg font-bold ${totalPnL >= 0 ? "text-green-400" : "text-red-400"}`}>
                ₹{totalPnL.toFixed(2)}
              </span>
            </div>
          </div>
          <div className="text-gray-400 text-xs mt-1">
            {positions.length} Active Position{positions.length !== 1 ? "s" : ""}
          </div>
        </div>

        {!isMinimized && (
          <div className="max-h-64 overflow-y-auto custom-scrollbar">
            {positions.length === 0 ? (
              <div className="px-3 py-4 text-center text-gray-400 text-sm">
                No active positions
              </div>
            ) : (
              <div className="divide-y divide-gray-700">
                {positions.map((position, index) => {
                  const { pnl, pnl_percent, current_price, signal_type } = get_position_pnl(position);
                  const is_profit = pnl >= 0;

                  return (
                    <div key={position.position_id || index} className="px-3 py-2 hover:bg-gray-700 transition-colors">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-white text-sm font-semibold truncate max-w-[120px]">
                            {position.symbol || position.trading_symbol}
                          </span>
                          <span className={`text-xs px-1.5 py-0.5 rounded whitespace-nowrap ${
                            signal_type === "BUY"
                              ? "bg-green-900 text-green-300"
                              : "bg-red-900 text-red-300"
                          }`}>
                            {signal_type}
                          </span>
                        </div>
                        <div className={`text-sm font-bold ${is_profit ? "text-green-400" : "text-red-400"}`}>
                          {is_profit ? "+" : ""}₹{pnl.toFixed(2)}
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-400">
                        <div className="flex items-center gap-3">
                          <span>Qty: {position.quantity || 0}</span>
                          <span>Entry: ₹{(position.entry_price || 0).toFixed(2)}</span>
                        </div>
                        <div className={`flex items-center gap-1 ${is_profit ? "text-green-400" : "text-red-400"}`}>
                          <span>₹{current_price.toFixed(2)}</span>
                          <span className="font-medium">({pnl_percent >= 0 ? "+" : ""}{pnl_percent.toFixed(2)}%)</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        <div className="px-3 py-1.5 bg-gray-900 border-t border-gray-700 flex items-center justify-between">
          <button
            onClick={fetch_active_positions}
            className="text-blue-400 hover:text-blue-300 text-xs font-medium transition-colors"
          >
            Refresh
          </button>
          <span className="text-gray-500 text-xs">
            {isConnected ? "Live" : "Disconnected"}
          </span>
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #1f2937;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #4b5563;
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #6b7280;
        }
      `}</style>
    </div>
  );
};

export default LivePnLWidget;
