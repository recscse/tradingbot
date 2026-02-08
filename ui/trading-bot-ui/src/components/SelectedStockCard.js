import React, { memo } from 'react';
import TradingViewChart from './trading/TradingViewChart';

const formatCurrency = (amount) => {
  const formatted = new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Math.abs(amount || 0));
  return `${amount < 0 ? '-' : ''}₹${formatted}`;
};

const SelectedStockCard = memo(({ stock }) => {
  const lotsToTrade = stock.position_size_lots || 1;
  const lotSize = stock.lot_size || 0;
  const totalQty = lotsToTrade * lotSize;
  const ltp = stock.live_price || stock.premium || 0;
  const capitalRequired = ltp * totalQty;
  const score = stock.selection_score || 0;

  // Prepare data for Chart
  const chartData = {
    value: ltp,
    time: Math.floor(Date.now() / 1000)
  };

  // Extract markers if in position
  const markers = stock.active_positions ? stock.active_positions.map(p => ({
    entry: p.entry,
    sl: p.sl,
    target: p.target
  })) : [];

  return (
    <div className="tw-bg-slate-900/80 tw-rounded-2xl tw-p-5 tw-border tw-border-slate-700/50 hover:tw-border-cyan-500/50 tw-transition-all tw-duration-300 hover:tw-shadow-2xl">
      <div className="tw-grid tw-grid-cols-12 tw-gap-6 tw-items-center">
        
        {/* LEFT: Info Section */}
        <div className="tw-col-span-12 lg:tw-col-span-4 tw-grid tw-grid-cols-2 tw-gap-4">
          <div className="tw-col-span-2 tw-flex tw-items-center tw-justify-between">
            <div>
              <div className="tw-text-2xl tw-font-black tw-text-white">{stock.symbol}</div>
              <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase tw-tracking-widest">
                Exp: {stock.expiry_date} • {stock.sector}
              </div>
            </div>
            <span className={`tw-px-3 tw-py-1 tw-rounded-lg tw-text-xs tw-font-black ${stock.option_type === "CE" ? 'tw-bg-emerald-500/20 tw-text-emerald-400' : 'tw-bg-rose-500/20 tw-text-rose-400'}`}>
              {stock.option_type}
            </span>
          </div>

          <div className="tw-space-y-1">
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase">Strike / LTP</div>
            <div className="tw-text-base tw-font-bold tw-text-slate-300">₹{stock.strike_price}</div>
            <div className="tw-text-xl tw-font-black tw-text-cyan-400">₹{ltp.toFixed(2)}</div>
          </div>

          <div className="tw-space-y-1">
            <div className="tw-text-[10px] tw-text-slate-500 tw-uppercase">Capital / Score</div>
            <div className="tw-text-base tw-font-bold tw-text-orange-400">{formatCurrency(capitalRequired)}</div>
            <div className="tw-text-sm tw-font-bold tw-text-slate-400">{score}/100</div>
          </div>
        </div>

        {/* CENTER: Visualization Section */}
        <div className="tw-col-span-12 lg:tw-col-span-6 tw-h-[120px] tw-bg-slate-950/50 tw-rounded-xl tw-overflow-hidden tw-border tw-border-slate-800">
          <TradingViewChart data={chartData} markers={markers} height={120} />
        </div>

        {/* RIGHT: Action Section */}
        <div className="tw-col-span-12 lg:tw-col-span-2 tw-text-right">
          <div className="tw-mb-2">
            <span className={`tw-inline-block tw-px-4 tw-py-2 tw-rounded-xl tw-text-xs tw-font-black tw-uppercase tw-tracking-wider ${
              stock.trade_status === "TRADED" ? 'tw-bg-emerald-500 tw-text-white' : 
              stock.trade_status === "IN_POSITION" ? 'tw-bg-amber-500 tw-text-white' : 
              'tw-bg-slate-800 tw-text-slate-400'
            }`}>
              {stock.trade_status || "MONITORING"}
            </span>
          </div>
          <p className="tw-text-[10px] tw-text-slate-500">{stock.lot_size} qty x {lotsToTrade} lots</p>
        </div>

        {/* BOTTOM: Reason Row */}
        {stock.selection_reason && (
          <div className="tw-col-span-12 tw-pt-3 tw-border-t tw-border-slate-800/50">
            <p className="tw-text-[11px] tw-text-slate-400 tw-italic">
              <span className="tw-font-bold tw-text-slate-600 tw-not-italic tw-uppercase tw-mr-2">Insight</span>
              {stock.selection_reason}
            </p>
          </div>
        )}
      </div>
    </div>
  );
});

export default SelectedStockCard;