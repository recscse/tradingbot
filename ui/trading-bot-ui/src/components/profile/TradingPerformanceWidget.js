import React from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  Trophy
} from "lucide-react";
import { motion } from "framer-motion";

const MetricItem = ({ title, value, progress, icon: Icon, colorClass }) => (
  <div className="tw-space-y-2">
    <div className="tw-flex tw-items-center tw-justify-between">
      <div className="tw-flex tw-items-center tw-gap-2">
        <div className={`tw-p-1.5 tw-rounded-lg ${colorClass} tw-bg-opacity-10 ${colorClass.replace('tw-bg-', 'tw-text-')}`}>
          <Icon className="tw-w-3.5 tw-h-3.5" />
        </div>
        <span className="tw-text-xs tw-font-bold tw-text-slate-500 tw-uppercase tw-tracking-tight">{title}</span>
      </div>
      <span className={`tw-text-sm tw-font-black ${colorClass.replace('tw-bg-', 'tw-text-')}`}>{value}</span>
    </div>
    <div className="tw-h-1.5 tw-w-full tw-bg-slate-100 tw-dark:bg-slate-800 tw-rounded-full tw-overflow-hidden">
      <motion.div 
        initial={{ width: 0 }}
        animate={{ width: `${progress * 100}%` }}
        className={`tw-h-full ${colorClass}`}
      />
    </div>
  </div>
);

const TradingPerformanceWidget = ({ tradingStats, compact = false }) => {
  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const performanceMetrics = [
    {
      title: "Win Rate",
      value: `${tradingStats?.win_rate || 0}%`,
      progress: (tradingStats?.win_rate || 0) / 100,
      colorClass: (tradingStats?.win_rate || 0) >= 60 ? "tw-bg-emerald-500" : (tradingStats?.win_rate || 0) >= 40 ? "tw-bg-amber-500" : "tw-bg-rose-500",
      icon: Trophy,
    },
    {
      title: "Total Profit",
      value: formatCurrency(tradingStats?.total_pnl || 0),
      progress: Math.min(Math.abs(tradingStats?.total_pnl || 0) / 100000, 1),
      colorClass: (tradingStats?.total_pnl || 0) >= 0 ? "tw-bg-emerald-500" : "tw-bg-rose-500",
      icon: (tradingStats?.total_pnl || 0) >= 0 ? TrendingUp : TrendingDown,
    },
    {
      title: "Avg Return",
      value: "14.2%",
      progress: 0.75,
      colorClass: "tw-bg-blue-500",
      icon: BarChart3,
    },
  ];

  if (compact) {
    return (
      <div className="tw-grid tw-grid-cols-3 tw-gap-4">
        {performanceMetrics.map((metric, idx) => (
          <div key={idx} className="tw-text-center">
            <div className={`tw-text-base tw-font-black ${metric.colorClass.replace('tw-bg-', 'tw-text-')}`}>
              {metric.value}
            </div>
            <div className="tw-text-[10px] tw-font-bold tw-text-slate-400 tw-uppercase">
              {metric.title}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="tw-space-y-8">
      <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-3 tw-gap-8">
        {performanceMetrics.map((metric, idx) => (
          <MetricItem key={idx} {...metric} />
        ))}
      </div>

      <div className="tw-pt-6 tw-border-t tw-border-slate-50 tw-dark:border-slate-800">
        <div className="tw-grid tw-grid-cols-2 sm:tw-grid-cols-4 tw-gap-4">
          <div className="tw-p-4 tw-rounded-2xl tw-bg-slate-50/50 tw-dark:bg-slate-800/30 tw-text-center">
            <div className="tw-text-lg tw-font-black tw-text-indigo-600 tw-dark:text-indigo-400">{tradingStats?.total_trades || 0}</div>
            <div className="tw-text-[10px] tw-font-bold tw-text-slate-400 tw-uppercase tw-tracking-widest">Total Trades</div>
          </div>
          <div className="tw-p-4 tw-rounded-2xl tw-bg-slate-50/50 tw-dark:bg-slate-800/30 tw-text-center">
            <div className="tw-text-lg tw-font-black tw-text-emerald-600">{tradingStats?.profitable_trades || 0}</div>
            <div className="tw-text-[10px] tw-font-bold tw-text-slate-400 tw-uppercase tw-tracking-widest">Profitable</div>
          </div>
          <div className="tw-p-4 tw-rounded-2xl tw-bg-slate-50/50 tw-dark:bg-slate-800/30 tw-text-center">
            <div className="tw-text-lg tw-font-black tw-text-rose-600">{tradingStats?.losing_trades || 0}</div>
            <div className="tw-text-[10px] tw-font-bold tw-text-slate-400 tw-uppercase tw-tracking-widest">Losses</div>
          </div>
          <div className="tw-p-4 tw-rounded-2xl tw-bg-slate-50/50 tw-dark:bg-slate-800/30 tw-text-center">
            <div className="tw-text-lg tw-font-black tw-text-blue-600">{tradingStats?.active_positions || 0}</div>
            <div className="tw-text-[10px] tw-font-bold tw-text-slate-400 tw-uppercase tw-tracking-widest">Active Now</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingPerformanceWidget;
