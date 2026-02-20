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
  return 'tw-text-slate-400';
};

const formatTime = (dateString) => {
    if (!dateString) return "N/A";
    try {
        const date = new Date(dateString);
        return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
        return dateString;
    }
};

const ActivePositionCard = memo(({ position, onClose }) => {
  const isProfit = position.current_pnl >= 0;
  const optionType = position.option_type || (position.signal_type?.includes("CE") ? "CE" : "PE");
  const strikeDisplay = position.strike_price ? parseFloat(position.strike_price).toFixed(0) : "N/A";
  
  return (
    <div className="tw-relative tw-bg-slate-900/30 hover:tw-bg-slate-800/60 tw-border tw-border-slate-800/40 hover:tw-border-cyan-500/30 tw-rounded-xl tw-transition-all tw-duration-200">
      {/* Visual Indicator - Profit/Loss */}
      <div className={`tw-absolute tw-left-0 tw-top-2 tw-bottom-2 tw-w-1 tw-rounded-r-full ${isProfit ? 'tw-bg-emerald-500' : 'tw-bg-rose-500'}`} />

      <div className="tw-p-4 tw-pl-6">
        <div className="tw-grid tw-grid-cols-1 lg:tw-grid-cols-12 tw-gap-4 tw-items-center">
          
          {/* Col 1: Instrument & Identity (3 units) */}
          <div className="tw-col-span-3">
            <div className="tw-flex tw-items-center tw-gap-2">
              <span className="tw-text-base tw-font-black tw-text-white tw-tracking-tight">{position.symbol}</span>
              <span className={`tw-text-[10px] tw-px-1.5 tw-py-0.5 tw-rounded tw-font-black ${
                optionType === "CE" ? 'tw-bg-emerald-500/10 tw-text-emerald-400' : 'tw-bg-rose-500/10 tw-text-rose-400'
              }`}>
                {strikeDisplay} {optionType}
              </span>
            </div>
            <div className="tw-flex tw-items-center tw-gap-2 tw-mt-1.5">
              <span className="tw-text-[10px] tw-text-slate-500 tw-font-bold tw-uppercase">{position.expiry_date}</span>
              <span className="tw-text-slate-800">•</span>
              <span className="tw-text-[10px] tw-text-slate-400 tw-font-mono">{formatTime(position.entry_time)}</span>
            </div>
          </div>

          {/* Col 2: Position Details (2 units) */}
          <div className="tw-col-span-2">
            <div className="tw-flex tw-flex-col">
              <span className="tw-text-[10px] tw-text-slate-600 tw-font-black tw-uppercase tw-tracking-widest">Quantity</span>
              <div className="tw-flex tw-items-baseline tw-gap-1.5">
                <span className="tw-text-sm tw-font-black tw-text-slate-200">{position.quantity}</span>
                <span className="tw-text-[10px] tw-text-slate-500">({Math.round(position.quantity/position.lot_size)} Lots)</span>
              </div>
              <span className="tw-text-[9px] tw-text-slate-600 tw-mt-0.5">Lot Size: {position.lot_size}</span>
            </div>
          </div>

          {/* Col 3: Price, SL, Tgt (2 units) */}
          <div className="tw-col-span-2">
            <div className="tw-space-y-1">
              <div className="tw-flex tw-justify-between tw-items-center lg:tw-block">
                <span className="tw-text-[9px] tw-text-slate-600 tw-uppercase tw-font-black">Entry Prem: </span>
                <span className="tw-text-xs tw-font-bold tw-text-slate-300">₹{safeNum(position.entry_price).toFixed(2)}</span>
              </div>
              <div className="tw-flex tw-justify-between tw-items-center lg:tw-block">
                <span className="tw-text-[9px] tw-text-rose-600/60 tw-uppercase tw-font-black">SL: </span>
                <span className="tw-text-xs tw-font-bold tw-text-rose-400/80">₹{safeNum(position.stop_loss).toFixed(2)}</span>
              </div>
              <div className="tw-flex tw-justify-between tw-items-center lg:tw-block">
                <span className="tw-text-[9px] tw-text-emerald-600/60 tw-uppercase tw-font-black">Tgt: </span>
                <span className="tw-text-xs tw-font-bold tw-text-emerald-400/80">₹{safeNum(position.target).toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Col 4: LTP & Market (2 units) */}
          <div className="tw-col-span-2">
            <span className="tw-text-[10px] tw-text-slate-600 tw-font-black tw-uppercase tw-tracking-widest">Live Premium</span>
            <div className="tw-flex tw-items-center tw-gap-2">
              <span className="tw-text-sm tw-font-black tw-text-cyan-400">₹{safeNum(position.current_price).toFixed(2)}</span>
              <span className="tw-relative tw-flex tw-h-1.5 tw-w-1.5">
                <span className="tw-animate-ping tw-absolute tw-inline-flex tw-h-full tw-w-full tw-rounded-full tw-bg-cyan-400 tw-opacity-75"></span>
                <span className="tw-relative tw-inline-flex tw-rounded-full tw-h-1.5 tw-w-1.5 tw-bg-cyan-500"></span>
              </span>
            </div>
            {position.trailing_stop_active && (
              <div className="tw-mt-1 tw-inline-flex tw-items-center tw-px-1.5 tw-py-0.5 tw-bg-amber-500/5 tw-border tw-border-amber-500/20 tw-rounded">
                <span className="tw-text-[8px] tw-font-black tw-text-amber-500 tw-uppercase tw-animate-pulse">TSL Active</span>
              </div>
            )}
          </div>

          {/* Col 5: PnL & Action (3 units) */}
          <div className="tw-col-span-3 tw-flex tw-items-center tw-justify-between tw-pl-4 tw-border-l tw-border-slate-800/50">
            <div className="tw-text-right">
              <div className={`tw-text-xl tw-font-black tw-leading-none tw-tracking-tight ${getPnlColor(position.current_pnl)}`}>
                {formatCurrency(position.current_pnl)}
              </div>
              <div className={`tw-text-xs tw-font-black tw-mt-1 ${getPnlColor(position.current_pnl_percentage)}`}>
                {formatPercentage(position.current_pnl_percentage)}
              </div>
            </div>
            <button
              onClick={() => onClose(position.position_id)}
              className="tw-px-4 tw-py-2 tw-bg-slate-800 hover:tw-bg-rose-600/20 tw-text-slate-400 hover:tw-text-rose-400 tw-rounded-lg tw-text-[10px] tw-font-black tw-uppercase tw-tracking-widest tw-transition-all tw-duration-200 tw-border tw-border-slate-700 hover:tw-border-rose-500/40"
            >
              Square Off
            </button>
          </div>

        </div>
      </div>
    </div>
  );
});

const safeNum = (val) => {
  const n = parseFloat(val);
  return isNaN(n) ? 0 : n;
};

export default ActivePositionCard;
