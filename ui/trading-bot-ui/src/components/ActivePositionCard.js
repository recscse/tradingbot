import React, { memo } from 'react';
import TradingViewChart from './trading/TradingViewChart';

const formatCurrency = (amount) => {
  const formatted = new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Math.abs(amount || 0));
  return `${amount < 0 ? '-' : ''}₹${formatted}`;
};

const formatPercentage = (value = 0) => {
  const num = Number.isFinite(value) ? value : 0;
  return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
};

const getPnlColor = (value) => {
  if (value > 0) return 'tw-text-emerald-500';
  if (value < 0) return 'tw-text-rose-500';
  return 'tw-text-slate-300';
};

const ActivePositionCard = memo(({ position, onClose }) => {
  const isProfit = position.current_pnl >= 0;

  // Prepare data for Chart
  const chartData = {
    value: position.current_price,
    time: Math.floor(Date.now() / 1000)
  };

  const markers = [{
    entry: position.entry_price,
    sl: position.stop_loss,
    target: position.target
  }];

  return (
    <div
      className={`tw-relative tw-overflow-hidden tw-rounded-2xl tw-border tw-transition-all tw-duration-300 hover:tw-shadow-2xl hover:tw-scale-[1.02] ${
        isProfit
          ? 'tw-bg-gradient-to-br tw-from-emerald-950/40 tw-to-emerald-900/20 tw-border-emerald-500/30'
          : 'tw-bg-gradient-to-br tw-from-rose-950/40 tw-to-rose-900/20 tw-border-rose-500/30'
      }`}
    >
      {/* Real-time Pulse Indicator */}
      <div className="tw-absolute tw-top-4 tw-right-4">
        <span className="tw-relative tw-flex tw-h-3 tw-w-3">
          <span className={`tw-animate-ping tw-absolute tw-inline-flex tw-h-full tw-w-full tw-rounded-full ${isProfit ? 'tw-bg-emerald-400' : 'tw-bg-rose-400'} tw-opacity-75`}></span>
          <span className={`tw-relative tw-inline-flex tw-rounded-full tw-h-3 tw-w-3 ${isProfit ? 'tw-bg-emerald-500' : 'tw-bg-rose-500'}`}></span>
        </span>
      </div>

      <div className="tw-p-6">
        {/* Header: Symbol & Type */}
        <div className="tw-flex tw-items-start tw-justify-between tw-mb-4">
          <div>
            <h3 className="tw-text-2xl tw-font-bold tw-text-white tw-mb-1">{position.symbol}</h3>
            <div className="tw-flex tw-items-center tw-gap-2">
              <span className={`tw-px-3 tw-py-1 tw-rounded-full tw-text-xs tw-font-bold ${
                position.signal_type?.includes("CE")
                  ? 'tw-bg-emerald-500/30 tw-text-emerald-200 tw-border tw-border-emerald-500/50'
                  : 'tw-bg-rose-500/30 tw-text-rose-200 tw-border tw-border-rose-500/50'
              }`}>
                {position.signal_type}
              </span>
              <span className="tw-text-xs tw-text-slate-400 tw-font-medium uppercase">
                {position.broker_name || "BROKER"}
              </span>
            </div>
          </div>

          {/* Large P&L Display */}
          <div className="tw-text-right">
            <div className={`tw-text-3xl tw-font-bold ${getPnlColor(position.current_pnl)}`}>
              {formatCurrency(position.current_pnl)}
            </div>
            <div className={`tw-text-lg tw-font-semibold ${getPnlColor(position.current_pnl_percentage)}`}>
              {formatPercentage(position.current_pnl_percentage)}
            </div>
          </div>
        </div>

        {/* Technical Chart Section */}
        <div className="tw-mb-4 tw-h-[100px] tw-bg-slate-950/50 tw-rounded-xl tw-overflow-hidden tw-border tw-border-slate-800">
          <TradingViewChart data={chartData} markers={markers} height={100} />
        </div>

        {/* Price Info Summary (Minimal) */}
        <div className="tw-flex tw-justify-between tw-text-[10px] tw-text-slate-400 tw-uppercase tw-font-bold tw-mb-4">
          <span>Entry: {formatCurrency(position.entry_price)}</span>
          <span>Current: {formatCurrency(position.current_price)}</span>
        </div>

        {/* Stats Grid */}
        <div className="tw-grid tw-grid-cols-3 tw-gap-3 tw-mb-4">
          <div className="tw-bg-slate-800/50 tw-rounded-xl tw-p-3 tw-border tw-border-slate-700/50">
            <div className="tw-text-xs tw-text-slate-400 tw-mb-1">Quantity</div>
            <div className="tw-text-lg tw-font-bold tw-text-white">{position.quantity}</div>
          </div>
          <div className="tw-bg-slate-800/50 tw-rounded-xl tw-p-3 tw-border tw-border-slate-700/50">
            <div className="tw-text-xs tw-text-slate-400 tw-mb-1">Invested</div>
            <div className="tw-text-sm tw-font-bold tw-text-cyan-400">
              {formatCurrency(position.entry_price * position.quantity)}
            </div>
          </div>
          <div className="tw-bg-slate-800/50 tw-rounded-xl tw-p-3 tw-border tw-border-slate-700/50">
            <div className="tw-text-xs tw-text-slate-400 tw-mb-1">Value</div>
            <div className="tw-text-sm tw-font-bold tw-text-white">
              {formatCurrency(position.current_price * position.quantity)}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="tw-flex tw-gap-2">
          <button
            onClick={() => onClose(position.position_id)}
            className="tw-flex-1 tw-px-4 tw-py-3 tw-bg-rose-600 hover:tw-bg-rose-700 tw-text-white tw-rounded-xl tw-font-semibold tw-transition-all tw-duration-200 tw-shadow-lg hover:tw-shadow-xl tw-flex tw-items-center tw-justify-center tw-gap-2"
          >
            <svg className="tw-w-5 tw-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Close Position
          </button>
          {position.trailing_stop_active && (
            <div className="tw-px-4 tw-py-3 tw-bg-amber-500/20 tw-border tw-border-amber-500/30 tw-rounded-xl tw-flex tw-items-center tw-justify-center" title="Trailing SL Active">
              <svg className="tw-w-5 tw-h-5 tw-text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
          )}
        </div>

        {/* Time Indicator */}
        <div className="tw-mt-3 tw-text-[10px] tw-font-bold tw-text-slate-500 tw-uppercase tw-tracking-widest tw-flex tw-items-center tw-gap-2">
          <svg className="tw-w-3 tw-h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Entry: {new Date(position.entry_time).toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
          })}
        </div>
      </div>
    </div>
  );
});

export default ActivePositionCard;