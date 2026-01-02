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

const TradeHistoryItem = memo(({ trade }) => {
  const isProfitable = trade.net_pnl >= 0;
  
  return (
    <div className={`tw-bg-gradient-to-r tw-rounded-xl tw-p-5 tw-border tw-transition-all tw-duration-300 hover:tw-shadow-xl ${isProfitable ? 'tw-from-green-900/20 tw-to-slate-900/80 tw-border-green-700/30 hover:tw-border-green-500/50' : 'tw-from-red-900/20 tw-to-slate-900/80 tw-border-red-700/30 hover:tw-border-red-500/50'}`}>
      <div className="tw-grid tw-grid-cols-12 tw-gap-4 tw-items-center">
        {/* Symbol & Type */}
        <div className="tw-col-span-3">
          <div className="tw-text-2xl tw-font-extrabold tw-text-white tw-mb-1">{trade.symbol}</div>
          <div className="tw-flex tw-items-center tw-gap-2">
            <span className={`tw-inline-block tw-px-3 tw-py-1 tw-rounded-md tw-text-xs tw-font-bold ${trade.signal_type?.includes("CE") ? 'tw-bg-green-600 tw-text-white' : 'tw-bg-red-600 tw-text-white'}`}>
              {trade.signal_type}
            </span>
            <span className="tw-text-xs tw-text-slate-400">{trade.broker_name}</span>
          </div>
          <div className="tw-text-[10px] tw-text-slate-500 tw-mt-1">
            Strat: {trade.strategy_name} | ID: {trade.trade_id}
          </div>
        </div>

        {/* Entry & Exit Prices */}
        <div className="tw-col-span-3">
          <div className="tw-text-xs tw-text-slate-400 tw-uppercase tw-mb-1">Entry → Exit</div>
          <div className="tw-flex tw-items-center tw-gap-2">
            <span className="tw-text-base tw-font-bold tw-text-white">{formatCurrency(trade.entry_price)}</span>
            <svg className="tw-w-4 tw-h-4 tw-text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            <span className="tw-text-base tw-font-bold tw-text-cyan-400">{formatCurrency(trade.exit_price)}</span>
          </div>
          <div className="tw-text-[10px] tw-text-slate-500 tw-mt-0.5">
            {trade.entry_time_str} → {trade.exit_time_str}
          </div>
        </div>

        {/* P&L Amount */}
        <div className="tw-col-span-3">
          <div className="tw-text-xs tw-text-slate-400 tw-uppercase tw-mb-1">Net P&L</div>
          <div className={`tw-text-2xl tw-font-extrabold ${isProfitable ? 'tw-text-green-400' : 'tw-text-red-400'}`}>
            {formatCurrency(trade.net_pnl)}
          </div>
          <div className="tw-text-[10px] tw-text-slate-500 tw-mt-1">
            Invest: {formatCurrency(trade.total_investment || (trade.entry_price * trade.quantity))}
          </div>
        </div>

        {/* P&L % & Exit Reason */}
        <div className="tw-col-span-3 tw-text-right">
          <div className={`tw-inline-block tw-px-4 tw-py-2 tw-rounded-lg tw-text-lg tw-font-extrabold tw-mb-2 ${isProfitable ? 'tw-bg-green-600 tw-text-white' : 'tw-bg-red-600 tw-text-white'}`}>
            {formatPercentage(trade.pnl_percentage)}
          </div>
          <div className="tw-text-xs tw-text-slate-400 tw-mt-1">{trade.exit_reason}</div>
        </div>
      </div>
    </div>
  );
});

export default TradeHistoryItem;