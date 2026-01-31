import React, { useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  RefreshCw, 
  Plus, 
  Wallet, 
  ShieldCheck, 
  Zap, 
  ChevronRight,
  PieChart,
  BarChart3,
  ExternalLink,
  Info
} from "lucide-react";
import BrokerAccountCard from "./BrokerAccountCard";
import RecentActivityFeed from "./RecentActivityFeed";
import TradingPerformanceWidget from "./TradingPerformanceWidget";
import PortfolioHealthIndicator from "./PortfolioHealthIndicator";

const StatCard = ({ title, value, subtitle, icon: Icon, colorClass, trend }) => (
  <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-2xl tw-p-5 tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm hover:tw-shadow-md tw-transition-all tw-duration-300 tw-group">
    <div className="tw-flex tw-justify-between tw-items-start tw-mb-4">
      <div className={`tw-p-2.5 tw-rounded-xl ${colorClass} tw-bg-opacity-10 group-hover:tw-scale-110 tw-transition-transform`}>
        <Icon className={`tw-w-5 tw-h-5 ${colorClass.replace('tw-bg-', 'tw-text-')}`} />
      </div>
      {trend && (
        <span className={`tw-flex tw-items-center tw-text-[10px] tw-font-bold tw-px-1.5 tw-py-0.5 tw-rounded-lg ${
          trend === 'up' ? 'tw-bg-green-50 tw-text-green-600' : 'tw-bg-red-50 tw-text-red-600'
        }`}>
          {trend === 'up' ? <TrendingUp className="tw-w-3 tw-h-3 tw-mr-0.5" /> : <TrendingDown className="tw-w-3 tw-h-3 tw-mr-0.5" />}
          {trend === 'up' ? '+2.4%' : '-1.2%'}
        </span>
      )}
    </div>
    <div>
      <h4 className="tw-text-xs tw-font-bold tw-text-slate-400 tw-uppercase tw-tracking-wider tw-mb-1">{title}</h4>
      <div className="tw-text-2xl tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight">{value}</div>
      <p className="tw-text-[10px] tw-text-slate-500 tw-mt-1 tw-font-medium">{subtitle}</p>
    </div>
  </div>
);

const QuickAction = ({ icon: Icon, label, onClick }) => (
  <button 
    onClick={onClick}
    className="tw-flex tw-items-center tw-gap-3 tw-p-3 tw-rounded-xl tw-bg-slate-50 tw-dark:bg-slate-800/50 tw-border tw-border-slate-100 tw-dark:border-slate-800 hover:tw-border-indigo-500/30 hover:tw-bg-indigo-50/30 tw-transition-all tw-group tw-w-full"
  >
    <div className="tw-p-2 tw-rounded-lg tw-bg-white tw-dark:bg-slate-800 tw-shadow-sm group-hover:tw-text-indigo-600 tw-transition-colors">
      <Icon className="tw-w-4 tw-h-4" />
    </div>
    <span className="tw-text-sm tw-font-bold tw-text-slate-700 tw-dark:text-slate-300">{label}</span>
    <ChevronRight className="tw-w-4 tw-h-4 tw-ml-auto tw-text-slate-300 group-hover:tw-text-indigo-500 tw-transition-colors" />
  </button>
);

const ProfileOverview = ({
  profileData,
  tradingStats,
  brokerAccounts,
  onRefresh,
}) => {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const todayPnl = tradingStats?.today_pnl || profileData?.todayPnl || 0;

  return (
    <div className="tw-space-y-6">
      {/* Performance Stats Grid */}
      <div className="tw-grid tw-grid-cols-1 sm:tw-grid-cols-2 lg:tw-grid-cols-4 tw-gap-4">
        <StatCard 
          title="Portfolio Value" 
          value={formatCurrency(tradingStats?.total_portfolio_value || 0)}
          subtitle="Aggregate across all brokers"
          icon={Wallet}
          colorClass="tw-bg-indigo-500"
        />
        <StatCard 
          title="Today's P&L" 
          value={formatCurrency(todayPnl)}
          subtitle="Current session performance"
          icon={todayPnl >= 0 ? TrendingUp : TrendingDown}
          colorClass={todayPnl >= 0 ? "tw-bg-emerald-500" : "tw-bg-rose-500"}
          trend={todayPnl >= 0 ? "up" : "down"}
        />
        <StatCard 
          title="Total Trades" 
          value={tradingStats?.total_trades || 0}
          subtitle="Lifetime execution count"
          icon={Activity}
          colorClass="tw-bg-blue-500"
        />
        <StatCard 
          title="Win Rate" 
          value={`${tradingStats?.win_rate || 0}%`}
          subtitle="Success probability"
          icon={Zap}
          colorClass={tradingStats?.win_rate >= 50 ? "tw-bg-amber-500" : "tw-bg-slate-500"}
        />
      </div>

      <div className="tw-grid tw-grid-cols-1 lg:tw-grid-cols-12 tw-gap-6">
        {/* Main Dashboard Column */}
        <div className="lg:tw-col-span-8 tw-space-y-6">
          
          {/* Trading Performance Analytics Widget */}
          <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-3xl tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm tw-overflow-hidden">
            <div className="tw-p-6 tw-border-b tw-border-slate-50 tw-dark:border-slate-800 tw-flex tw-items-center tw-justify-between">
              <div className="tw-flex tw-items-center tw-gap-3">
                <div className="tw-p-2 tw-bg-indigo-50 tw-dark:bg-indigo-950/30 tw-rounded-xl text-indigo-600">
                  <BarChart3 className="tw-w-5 tw-h-5" />
                </div>
                <h3 className="tw-text-lg tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight">Equity Curve</h3>
              </div>
              <button className="tw-text-xs tw-font-bold tw-text-indigo-600 hover:tw-text-indigo-700 tw-flex tw-items-center tw-gap-1">
                Full Analytics <ExternalLink className="tw-w-3 tw-h-3" />
              </button>
            </div>
            <div className="tw-p-6">
              <TradingPerformanceWidget tradingStats={tradingStats} />
            </div>
          </div>

          <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 tw-gap-6">
            {/* Broker Status */}
            <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-3xl tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm tw-p-6">
              <div className="tw-flex tw-items-center tw-justify-between tw-mb-6">
                <h3 className="tw-text-base tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight tw-flex tw-items-center tw-gap-2">
                  <ShieldCheck className="tw-w-4 tw-h-4 tw-text-blue-500" />
                  Active Brokers
                </h3>
                <button className="tw-p-1.5 tw-bg-slate-50 tw-dark:bg-slate-800 tw-rounded-lg text-slate-400 hover:text-indigo-600 transition-colors">
                  <Plus className="tw-w-4 tw-h-4" />
                </button>
              </div>
              
              <div className="tw-space-y-4">
                {brokerAccounts && brokerAccounts.length > 0 ? (
                  brokerAccounts.slice(0, 3).map((account) => (
                    <BrokerAccountCard key={account.id} account={account} variant="compact" />
                  ))
                ) : (
                  <div className="tw-text-center tw-py-8">
                    <div className="tw-w-12 tw-h-12 tw-bg-slate-50 tw-dark:bg-slate-800 tw-rounded-full tw-flex tw-items-center tw-justify-center tw-mx-auto tw-mb-3">
                      <Wallet className="tw-w-6 tw-h-6 tw-text-slate-300" />
                    </div>
                    <p className="tw-text-xs tw-text-slate-500 tw-font-medium">No brokers connected</p>
                  </div>
                )}
              </div>
            </div>

            {/* Portfolio Health */}
            <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-3xl tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm tw-p-6">
              <h3 className="tw-text-base tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight tw-mb-6 tw-flex tw-items-center tw-gap-2">
                <PieChart className="tw-w-4 tw-h-4 tw-text-purple-500" />
                Risk Health
              </h3>
              <PortfolioHealthIndicator
                portfolioData={{ brokerAccounts }}
                tradingStats={tradingStats}
              />
            </div>
          </div>
        </div>

        {/* Sidebar Column */}
        <div className="lg:tw-col-span-4 tw-space-y-6">
          
          {/* Quick Actions Card */}
          <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-3xl tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm tw-p-6">
            <h3 className="tw-text-base tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight tw-mb-4">Shortcuts</h3>
            <div className="tw-space-y-2">
              <QuickAction icon={BarChart3} label="Download P&L Report" onClick={() => {}} />
              <QuickAction icon={ShieldCheck} label="Audit Security Logs" onClick={() => {}} />
              <QuickAction icon={Info} label="Knowledge Base" onClick={() => {}} />
              <button 
                onClick={handleRefresh}
                disabled={refreshing}
                className="tw-w-full tw-mt-4 tw-py-3 tw-bg-indigo-600 hover:tw-bg-indigo-700 disabled:tw-opacity-50 tw-text-white tw-rounded-xl tw-text-sm tw-font-bold tw-shadow-lg tw-shadow-indigo-200 tw-dark:tw-shadow-none tw-transition-all tw-flex tw-items-center tw-justify-center tw-gap-2"
              >
                <RefreshCw className={`tw-w-4 tw-h-4 ${refreshing ? 'tw-animate-spin' : ''}`} />
                {refreshing ? "Refreshing..." : "Sync All Data"}
              </button>
            </div>
          </div>

          {/* Activity Feed */}
          <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-3xl tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm tw-overflow-hidden">
            <div className="tw-p-6 tw-border-b tw-border-slate-50 tw-dark:border-slate-800">
              <h3 className="tw-text-base tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight">Timeline</h3>
            </div>
            <div className="tw-p-2">
              <RecentActivityFeed activities={tradingStats?.recentActivity || []} maxItems={5} />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ProfileOverview;