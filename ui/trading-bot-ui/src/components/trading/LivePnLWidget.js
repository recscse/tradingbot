import React, { useState, useEffect, useCallback } from "react";
import { useUnifiedMarketData } from "../../hooks/useUnifiedMarketData";
import {
  Minimize2,
  Maximize2,
  TrendingUp,
  TrendingDown,
  X,
} from "lucide-react";
import "./LivePnLWidget.css";

/** -------------------------------------
 * SAFE NUMBER HELPER
 * ----------------------------------- */
const safeNum = (value, fallback = 0) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
};

const LivePnLWidget = () => {
  const { marketData, isConnected } = useUnifiedMarketData();
  const [positions, setPositions] = useState([]);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [totalPnL, setTotalPnL] = useState(0);

  const fetch_active_positions = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/api/v1/trading/execution/active-positions`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();

        if (Array.isArray(data)) {
          setPositions(data);
        } else if (data && Array.isArray(data.active_positions)) {
          setPositions(data.active_positions);
        } else if (data && typeof data === "object") {
          setPositions([data]);
        } else {
          setPositions([]);
        }
      }
    } catch (error) {
      console.error("Error fetching positions:", error);
      setPositions([]);
    }
  }, []);

  /** -------------------------------------
   * TOTAL PNL CALCULATION
   * ----------------------------------- */
  const calculate_total_pnl = useCallback(() => {
    let total = 0;

    positions.forEach((position) => {
      const entry_price = safeNum(position.entry_price ?? position.avg_price);
      const quantity = safeNum(position.quantity, 1);
      const signal_type = position.signal_type || position.trade_type || "BUY";

      const marketLtpByKey =
        position.instrument_key && marketData
          ? marketData[position.instrument_key]?.ltp
          : undefined;

      const marketLtpBySymbol =
        position.symbol && marketData
          ? marketData[position.symbol]?.ltp
          : undefined;

      const current_price = safeNum(
        marketLtpByKey ??
          marketLtpBySymbol ??
          position.current_price ??
          entry_price
      );

      const direction = signal_type === "BUY" ? 1 : -1;
      const pnl = (current_price - entry_price) * quantity * direction;

      total += pnl;
    });

    setTotalPnL(total);
  }, [positions, marketData]);

  useEffect(() => {
    fetch_active_positions();
  }, [fetch_active_positions]);

  useEffect(() => {
    if (positions.length > 0) {
      calculate_total_pnl();
    }
  }, [positions, marketData, calculate_total_pnl]);

  /** -------------------------------------
   * SINGLE POSITION PNL
   * ----------------------------------- */
  const get_position_pnl = (position) => {
    const instrumentKey = position.instrument_key;
    const symbol = position.symbol || position.trading_symbol;

    const marketLtpByKey =
      instrumentKey && marketData ? marketData[instrumentKey]?.ltp : undefined;

    const marketLtpBySymbol =
      symbol && marketData ? marketData[symbol]?.ltp : undefined;

    const entry_price = safeNum(position.entry_price ?? position.avg_price);
    const quantity = safeNum(position.quantity, 1);
    const signal_type = position.signal_type || position.trade_type || "BUY";

    const current_price = safeNum(
      marketLtpByKey ??
        marketLtpBySymbol ??
        position.current_price ??
        entry_price
    );

    const direction = signal_type === "BUY" ? 1 : -1;
    const pnl = (current_price - entry_price) * quantity * direction;

    const pnl_percent =
      entry_price > 0
        ? ((current_price - entry_price) / entry_price) * 100 * direction
        : 0;

    return {
      pnl,
      pnl_percent,
      current_price,
      signal_type,
    };
  };

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="tw-fixed tw-bottom-4 tw-right-4 tw-z-50 tw-bg-gradient-to-r tw-from-blue-600 tw-to-blue-700 tw-text-white tw-px-4 tw-py-2 tw-rounded-lg tw-shadow-lg hover:tw-shadow-xl tw-transition-all tw-duration-200 tw-flex tw-items-center tw-gap-2"
      >
        <TrendingUp className="tw-w-4 tw-h-4" />
        <span className="tw-text-sm tw-font-semibold">Show P&L</span>
      </button>
    );
  }

  return (
    <div className="tw-fixed tw-bottom-4 tw-right-4 tw-z-50 tw-w-80 sm:tw-w-96 tw-max-w-full">
      <div className="tw-bg-gradient-to-br tw-from-gray-900 tw-to-gray-800 tw-rounded-lg tw-shadow-2xl tw-border tw-border-gray-700 tw-overflow-hidden">
        {/* HEADER */}
        <div className="tw-bg-gradient-to-r tw-from-blue-600 tw-to-blue-700 tw-px-3 tw-py-2 tw-flex tw-items-center tw-justify-between">
          <div className="tw-flex tw-items-center tw-gap-2">
            <div
              className={`tw-w-2 tw-h-2 tw-rounded-full ${
                isConnected ? "tw-bg-green-400 tw-animate-pulse" : "tw-bg-red-400"
              }`}
            />
            <h3 className="tw-text-white tw-text-sm tw-font-bold">Live P&L</h3>
          </div>

          <div className="tw-flex tw-items-center tw-gap-2">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="tw-text-white hover:tw-bg-blue-600 tw-rounded tw-p-1 tw-transition-colors"
            >
              {isMinimized ? (
                <Maximize2 className="tw-w-4 tw-h-4" />
              ) : (
                <Minimize2 className="tw-w-4 tw-h-4" />
              )}
            </button>
            <button
              onClick={() => setIsVisible(false)}
              className="tw-text-white hover:tw-bg-blue-600 tw-rounded tw-p-1 tw-transition-colors"
            >
              <X className="tw-w-4 tw-h-4" />
            </button>
          </div>
        </div>

        {/* TOTAL PNL BAR */}
        <div className="tw-px-3 tw-py-2 tw-bg-gray-800 tw-border-b tw-border-gray-700">
          <div className="tw-flex tw-items-center tw-justify-between">
            <span className="tw-text-gray-300 tw-text-xs tw-font-medium">Total P&L</span>

            <div className="tw-flex tw-items-center tw-gap-1">
              {totalPnL > 0 ? (
                <TrendingUp className="tw-w-4 tw-h-4 tw-text-emerald-400" />
              ) : totalPnL < 0 ? (
                <TrendingDown className="tw-w-4 tw-h-4 tw-text-rose-400" />
              ) : (
                <TrendingUp className="tw-w-4 tw-h-4 tw-text-gray-400" />
              )}

              <span
                className={`tw-text-lg tw-font-bold ${
                  totalPnL > 0 ? "tw-text-emerald-400" : totalPnL < 0 ? "tw-text-rose-400" : "tw-text-gray-400"
                }`}
              >
                ₹{safeNum(totalPnL).toFixed(2)}
              </span>
            </div>
          </div>

          <div className="tw-text-gray-400 tw-text-xs tw-mt-1">
            {positions.length} Active Position
            {positions.length !== 1 ? "s" : ""}
          </div>
        </div>

        {/* POSITIONS LIST */}
        {!isMinimized && (
          <div className="tw-max-h-64 tw-overflow-y-auto custom-scrollbar">
            {positions.length === 0 ? (
              <div className="tw-px-3 tw-py-4 tw-text-center tw-text-gray-400 tw-text-sm">
                No active positions
              </div>
            ) : (
              <div className="tw-divide-y tw-divide-gray-700">
                {positions.map((position, index) => {
                  if (!position) return null;
                  const { pnl, pnl_percent, current_price, signal_type } =
                    get_position_pnl(position);

                  return (
                    <div
                      key={position.position_id || index}
                      className="tw-px-3 tw-py-2 hover:tw-bg-gray-700 tw-transition-colors"
                    >
                      <div className="tw-flex tw-items-center tw-justify-between tw-mb-1">
                        <div className="tw-flex tw-items-center tw-gap-2">
                          <span className="tw-text-white tw-text-sm tw-font-semibold tw-truncate tw-max-w-[120px]">
                            {position.symbol || position.trading_symbol}
                          </span>

                          <span
                            className={`tw-text-xs tw-px-1.5 tw-py-0.5 tw-rounded tw-whitespace-nowrap ${
                              signal_type === "BUY"
                                ? "tw-bg-emerald-500/20 tw-text-emerald-400"
                                : "tw-bg-rose-500/20 tw-text-rose-400"
                            }`}
                          >
                            {signal_type}
                          </span>
                        </div>

                        <div
                          className={`tw-text-sm tw-font-bold ${
                            pnl > 0 ? "tw-text-emerald-400" : pnl < 0 ? "tw-text-rose-400" : "tw-text-gray-400"
                          }`}
                        >
                          {pnl >= 0 ? "+" : ""}₹{safeNum(pnl).toFixed(2)}
                        </div>
                      </div>

                      <div className="tw-flex tw-items-center tw-justify-between tw-text-xs tw-text-gray-400">
                        <div className="tw-flex tw-items-center tw-gap-3">
                          <span>Qty: {safeNum(position.quantity)}</span>
                          <span>
                            Entry: ₹
                            {safeNum(
                              position.entry_price ?? position.avg_price
                            ).toFixed(2)}
                          </span>
                        </div>

                        <div
                          className={`tw-flex tw-items-center tw-gap-1 ${
                            pnl > 0 ? "tw-text-emerald-400" : pnl < 0 ? "tw-text-rose-400" : "tw-text-gray-400"
                          }`}
                        >
                          <span>₹{safeNum(current_price).toFixed(2)}</span>

                          <span className="tw-font-medium">
                            ({pnl_percent >= 0 ? "+" : ""}
                            {safeNum(pnl_percent).toFixed(2)}%)
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* FOOTER */}
        <div className="tw-px-3 tw-py-1.5 tw-bg-gray-900 tw-border-t tw-border-gray-700 tw-flex tw-items-center tw-justify-between">
          <button
            onClick={fetch_active_positions}
            className="tw-text-blue-400 hover:tw-text-blue-300 tw-text-xs tw-font-medium tw-transition-colors"
          >
            Refresh
          </button>

          <span className="tw-text-gray-500 tw-text-xs">
            {isConnected ? "Live" : "Disconnected"}
          </span>
        </div>
      </div>
    </div>
  );
};

export default LivePnLWidget;