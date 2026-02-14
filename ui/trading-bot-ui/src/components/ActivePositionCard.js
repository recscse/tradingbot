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
  if (value > 0) return 'tw-text-emerald-400';
  if (value < 0) return 'tw-text-rose-400';
  return 'tw-text-slate-300';
};

const ActivePositionCard = memo(({ position, onClose }) => {
  const isProfit = position.current_pnl >= 0;
  const optionType = position.option_type || (position.signal_type?.includes("CE") ? "CE" : "PE");
  const strikeDisplay = position.strike_price ? parseFloat(position.strike_price).toFixed(0) : "N/A";
  
  return (
    <div
      className={`tw-relative tw-overflow-hidden tw-rounded-xl tw-border tw-bg-slate-900/60 tw-backdrop-blur-md tw-transition-all tw-duration-300 hover:tw-bg-slate-900/90 hover:tw-border-blue-500/40 ${
        isProfit ? 'tw-border-emerald-500/20' : 'tw-border-rose-500/20'
      }`}
    >
      {/* Broker-style Left Status Strip */}
      <div className={`tw-absolute tw-left-0 tw-top-0 tw-bottom-0 tw-w-1.5 ${isProfit ? 'tw-bg-emerald-500' : 'tw-bg-rose-500'}`} />

      <div className="tw-p-4 tw-pl-6">
        {/* Header: Broker Style Layout */}
        <div className="tw-flex tw-justify-between tw-items-start">
          <div className="tw-space-y-1">
            <div className="tw-flex tw-items-center tw-gap-2">
              <h3 className="tw-text-base tw-font-bold tw-text-white tw-tracking-tight">
                {position.symbol} <span className="tw-text-cyan-400 tw-ml-1">{strikeDisplay}</span> <span className="tw-text-slate-400">{optionType}</span>
              </h3>
              {position.expiry_date && (
                <span className="tw-text-[10px] tw-text-slate-500 tw-font-medium tw-bg-slate-800/50 tw-px-1.5 tw-py-0.5 tw-rounded">
                  {position.expiry_date}
                </span>
              )}
              <span className={`tw-text-[9px] tw-px-1.5 tw-py-0.5 tw-rounded tw-font-black tw-tracking-widest ${
                isProfit ? 'tw-bg-emerald-500/10 tw-text-emerald-400 tw-border tw-border-emerald-500/20' : 'tw-bg-rose-500/10 tw-text-rose-400 tw-border tw-border-rose-500/20'
              }`}>
                LONG
              </span>
            </div>
            <div className="tw-flex tw-items-center tw-gap-2">
               <span className="tw-text-[10px] tw-font-bold tw-text-slate-500 tw-uppercase tw-tracking-tighter">
                {position.broker_name || "UPSTOX"}
              </span>
              <span className="tw-w-1 tw-h-1 tw-rounded-full tw-bg-slate-700" />
              <span className={`tw-text-[10px] tw-font-bold tw-uppercase ${position.trading_mode === 'live' ? 'tw-text-rose-400' : 'tw-text-cyan-400'}`}>
                {position.trading_mode || "PAPER"}
              </span>
            </div>
          </div>

          <div className="tw-text-right">
            <div className={`tw-text-lg tw-font-black tw-leading-none tw-mb-1 ${getPnlColor(position.current_pnl)}`}>
              {formatCurrency(position.current_pnl)}
            </div>
            <div className={`tw-text-xs tw-font-bold ${getPnlColor(position.current_pnl_percentage)}`}>
              {formatPercentage(position.current_pnl_percentage)}
            </div>
          </div>
        </div>

        {/* Market Data Grid (Broker Standard) */}
        <div className="tw-grid tw-grid-cols-3 tw-gap-4 tw-mt-4 tw-pt-4 tw-border-t tw-border-slate-800/60">
          <div>
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase tw-font-bold tw-tracking-tight tw-mb-1">Qty</div>
            <div className="tw-text-sm tw-font-mono tw-font-bold tw-text-slate-200">{position.quantity}</div>
          </div>
          <div className="tw-text-center">
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase tw-font-bold tw-tracking-tight tw-mb-1">Avg. Price</div>
            <div className="tw-text-sm tw-font-mono tw-font-bold tw-text-slate-200">₹{safeNum(position.entry_price).toFixed(2)}</div>
          </div>
          <div className="tw-text-right">
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase tw-font-bold tw-tracking-tight tw-mb-1">LTP</div>
            <div className="tw-text-sm tw-font-mono tw-font-bold tw-text-cyan-400 tw-flex tw-items-center tw-justify-end tw-gap-1.5">
              ₹{safeNum(position.current_price).toFixed(2)}
              <span className="tw-relative tw-flex tw-h-1.5 tw-w-1.5">
                <span className="tw-animate-ping tw-absolute tw-inline-flex tw-h-full tw-w-full tw-rounded-full tw-bg-cyan-400 tw-opacity-75"></span>
                <span className="tw-relative tw-inline-flex tw-rounded-full tw-h-1.5 tw-w-1.5 tw-bg-cyan-500"></span>
              </span>
            </div>
          </div>
        </div>

        {/* Footer: SL, Target & Trailing */}
        <div className="tw-mt-4 tw-pt-3 tw-border-t tw-border-slate-800/40 tw-flex tw-items-center tw-justify-between">
          <div className="tw-flex tw-items-center tw-gap-4">
            <div className="tw-flex tw-items-center tw-gap-2">
              <div className="tw-w-1.5 tw-h-1.5 tw-rounded-full tw-bg-rose-500/40" />
              <span className="tw-text-[10px] tw-text-slate-500">SL <span className="tw-text-slate-300 tw-font-mono">₹{safeNum(position.stop_loss).toFixed(1)}</span></span>
            </div>
            <div className="tw-flex tw-items-center tw-gap-2">
              <div className="tw-w-1.5 tw-h-1.5 tw-rounded-full tw-bg-emerald-500/40" />
              <span className="tw-text-[10px] tw-text-slate-500">TGT <span className="tw-text-slate-300 tw-font-mono">₹{safeNum(position.target).toFixed(1)}</span></span>
            </div>
          </div>

          {position.trailing_stop_active ? (
            <div className="tw-flex tw-items-center tw-gap-1.5 tw-px-2 tw-py-0.5 tw-bg-amber-500/10 tw-rounded tw-border tw-border-amber-500/20">
              <span className="tw-text-[9px] tw-font-bold tw-text-amber-400 tw-uppercase tw-tracking-tight">Trailing Active</span>
            </div>
          ) : (
             <div className="tw-text-[9px] tw-text-slate-600 tw-font-medium">
               ID: {position.trade_id?.split('_')[1] || "..."}
             </div>
          )}
        </div>

        {/* Action Button - Professional Look */}
        <button
          onClick={() => onClose(position.position_id)}
          className="tw-w-full tw-mt-4 tw-py-2.5 tw-bg-slate-800 hover:tw-bg-rose-600 tw-text-slate-300 hover:tw-text-white tw-rounded-lg tw-text-xs tw-font-black tw-uppercase tw-tracking-widest tw-transition-all tw-duration-200 tw-border tw-border-slate-700/50 hover:tw-border-rose-500 tw-shadow-inner"
        >
          Square Off
        </button>
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
