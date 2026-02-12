import React, { memo } from 'react';

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
  const optionType = position.option_type || (position.signal_type?.includes("CE") ? "CE" : "PE");
  
  return (
    <div
      className={`tw-relative tw-overflow-hidden tw-rounded-xl tw-border tw-bg-slate-900/80 tw-transition-all tw-duration-300 hover:tw-border-blue-500/50 ${
        isProfit ? 'tw-border-emerald-500/20' : 'tw-border-rose-500/20'
      }`}
    >
      {/* Broker-style Left Status Strip */}
      <div className={`tw-absolute tw-left-0 tw-top-0 tw-bottom-0 tw-w-1 ${isProfit ? 'tw-bg-emerald-500' : 'tw-bg-rose-500'}`} />

      <div className="tw-p-4 tw-pl-5">
        {/* Header: Broker Style Layout */}
        <div className="tw-flex tw-justify-between tw-items-start tw-mb-3">
          <div>
            <div className="tw-flex tw-items-center tw-gap-2">
              <h3 className="tw-text-lg tw-font-bold tw-text-slate-100">
                {position.symbol} {position.strike_price || ""} {optionType}
              </h3>
              <span className={`tw-text-[10px] tw-px-1.5 tw-py-0.5 tw-rounded tw-font-black ${
                isProfit ? 'tw-bg-emerald-500/10 tw-text-emerald-500' : 'tw-bg-rose-500/10 tw-text-rose-500'
              }`}>
                LONG
              </span>
            </div>
            <div className="tw-text-[11px] tw-text-slate-500 tw-font-medium tw-mt-0.5">
              {position.broker_name?.toUpperCase()} • {position.trading_mode?.toUpperCase()}
            </div>
          </div>

          <div className="tw-text-right">
            <div className={`tw-text-xl tw-font-bold ${getPnlColor(position.current_pnl)}`}>
              {formatCurrency(position.current_pnl)}
            </div>
            <div className={`tw-text-xs tw-font-bold ${getPnlColor(position.current_pnl_percentage)}`}>
              {formatPercentage(position.current_pnl_percentage)}
            </div>
          </div>
        </div>

        {/* Market Data Grid (Broker Standard) */}
        <div className="tw-grid tw-grid-cols-3 tw-gap-2 tw-py-3 tw-border-y tw-border-slate-800/50 tw-mb-4">
          <div>
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase tw-tracking-wider">Qty</div>
            <div className="tw-text-sm tw-font-bold tw-text-slate-200">{position.quantity}</div>
          </div>
          <div>
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase tw-tracking-wider">Avg.</div>
            <div className="tw-text-sm tw-font-bold tw-text-slate-200">₹{safeNum(position.entry_price).toFixed(2)}</div>
          </div>
          <div className="tw-text-right">
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase tw-tracking-wider">LTP</div>
            <div className="tw-text-sm tw-font-bold tw-text-cyan-400 tw-flex tw-items-center tw-justify-end tw-gap-1">
              ₹{safeNum(position.current_price).toFixed(2)}
              <span className="tw-w-1.5 tw-h-1.5 tw-rounded-full tw-bg-cyan-500 tw-animate-pulse" />
            </div>
          </div>
        </div>

        {/* Secondary Info: SL & Target */}
        <div className="tw-flex tw-justify-between tw-mb-4 tw-px-1">
          <div className="tw-flex tw-gap-4">
            <div className="tw-flex tw-items-center tw-gap-1.5">
              <div className="tw-w-1 tw-h-3 tw-bg-rose-500/50 tw-rounded-full" />
              <span className="tw-text-[10px] tw-text-slate-500">SL: <span className="tw-text-slate-300">₹{safeNum(position.stop_loss).toFixed(2)}</span></span>
            </div>
            <div className="tw-flex tw-items-center tw-gap-1.5">
              <div className="tw-w-1 tw-h-3 tw-bg-emerald-500/50 tw-rounded-full" />
              <span className="tw-text-[10px] tw-text-slate-500">TGT: <span className="tw-text-slate-300">₹{safeNum(position.target).toFixed(2)}</span></span>
            </div>
          </div>
          {position.trailing_stop_active && (
            <div className="tw-flex tw-items-center tw-gap-1 tw-text-[10px] tw-text-amber-400">
              <div className="tw-w-1.5 tw-h-1.5 tw-rounded-full tw-bg-amber-500 tw-animate-ping" />
              Trailing Active
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="tw-flex tw-gap-2">
          <button
            onClick={() => onClose(position.position_id)}
            className="tw-flex-1 tw-py-2 tw-bg-slate-800 hover:tw-bg-rose-900/40 tw-text-slate-300 hover:tw-text-rose-200 tw-rounded-lg tw-text-xs tw-font-bold tw-transition-all tw-duration-200 tw-border tw-border-slate-700 hover:tw-border-rose-500/50"
          >
            Exit Position
          </button>
        </div>
      </div>
    </div>
  );
});

// Helper for numbers
const safeNum = (val) => {
  const n = parseFloat(val);
  return isNaN(n) ? 0 : n;
};

export default ActivePositionCard;
