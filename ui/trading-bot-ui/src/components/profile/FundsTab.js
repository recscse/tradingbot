import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  Wallet, 
  Plus, 
  ArrowUpRight, 
  ArrowDownLeft, 
  History,
  Info,
  ExternalLink
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../../services/api';
import AddFundsModal from '../funds/AddFundsModal';
import FundStatementTable from '../funds/FundStatementTable';

const FundsTab = () => {
  const [tradingMode, setTradingMode] = useState('paper');
  const [balances, setBalances] = useState({
    available_margin: 0,
    used_margin: 0,
    current_balance: 0,
    total_pnl: 0
  });
  const [statement, setStatement] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAddFundsOpen, setIsAddFundsOpen] = useState(false);

  const fetchFundData = useCallback(async () => {
    setLoading(true);
    try {
      const [balanceRes, statementRes] = await Promise.all([
        api.get(`/v1/trading/execution/funds/balance?trading_mode=${tradingMode}`),
        api.get(`/v1/trading/execution/funds/statement?trading_mode=${tradingMode}&limit=20`)
      ]);

      if (balanceRes.data.success) {
        setBalances(balanceRes.data.balances);
      }
      if (statementRes.data.success) {
        setStatement(statementRes.data.statement);
      }
    } catch (error) {
      console.error("Error fetching fund data:", error);
      toast.error("Failed to load fund details");
    } finally {
      setLoading(false);
    }
  }, [tradingMode]);

  useEffect(() => {
    fetchFundData();
  }, [fetchFundData]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2
    }).format(amount || 0);
  };

  return (
    <div className="tw-space-y-6">
      {/* Trading Mode Switcher */}
      <div className="tw-flex tw-bg-slate-900/50 tw-p-1 tw-rounded-xl tw-border tw-border-slate-800 tw-w-fit">
        <button
          onClick={() => setTradingMode('paper')}
          className={`tw-px-6 tw-py-2 tw-rounded-lg tw-text-sm tw-font-bold tw-transition-all ${
            tradingMode === 'paper' 
              ? 'tw-bg-indigo-600 tw-text-white tw-shadow-lg' 
              : 'tw-text-slate-400 hover:tw-text-white'
          }`}
        >
          Paper Account
        </button>
        <button
          onClick={() => setTradingMode('live')}
          className={`tw-px-6 tw-py-2 tw-rounded-lg tw-text-sm tw-font-bold tw-transition-all ${
            tradingMode === 'live' 
              ? 'tw-bg-rose-600 tw-text-white tw-shadow-lg' 
              : 'tw-text-slate-400 hover:tw-text-white'
          }`}
        >
          Live Broker
        </button>
      </div>

      {/* Balance Overview Cards */}
      <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-3 tw-gap-4">
        {/* Available Margin */}
        <motion.div 
          whileHover={{ y: -2 }}
          className="tw-bg-slate-900/50 tw-p-6 tw-rounded-2xl tw-border tw-border-slate-800 tw-shadow-sm"
        >
          <div className="tw-flex tw-items-center tw-justify-between tw-mb-4">
            <div className="tw-p-2 tw-bg-emerald-500/10 tw-rounded-lg">
              <Wallet className="tw-w-5 tw-h-5 tw-text-emerald-400" />
            </div>
            {tradingMode === 'paper' && (
              <button 
                onClick={() => setIsAddFundsOpen(true)}
                className="tw-p-1.5 tw-bg-indigo-600 hover:tw-bg-indigo-700 tw-text-white tw-rounded-lg tw-transition-colors"
              >
                <Plus className="tw-w-4 tw-h-4" />
              </button>
            )}
          </div>
          <p className="tw-text-slate-400 tw-text-xs tw-font-bold tw-uppercase tw-tracking-wider">Available Margin</p>
          <h3 className="tw-text-2xl tw-font-black tw-text-white tw-mt-1">{formatCurrency(balances.available_margin)}</h3>
          <div className="tw-mt-4 tw-flex tw-items-center tw-gap-2 tw-text-[10px] tw-text-slate-500">
            <Info className="tw-w-3 tw-h-3" />
            <span>Funds available for new positions</span>
          </div>
        </motion.div>

        {/* Used Margin */}
        <motion.div 
          whileHover={{ y: -2 }}
          className="tw-bg-slate-900/50 tw-p-6 tw-rounded-2xl tw-border tw-border-slate-800 tw-shadow-sm"
        >
          <div className="tw-flex tw-items-center tw-justify-between tw-mb-4">
            <div className="tw-p-2 tw-bg-amber-500/10 tw-rounded-lg">
              <ArrowUpRight className="tw-w-5 tw-h-5 tw-text-amber-400" />
            </div>
          </div>
          <p className="tw-text-slate-400 tw-text-xs tw-font-bold tw-uppercase tw-tracking-wider">Used Margin</p>
          <h3 className="tw-text-2xl tw-font-black tw-text-white tw-mt-1">{formatCurrency(balances.used_margin)}</h3>
          <div className="tw-mt-4 tw-flex tw-items-center tw-gap-2 tw-text-[10px] tw-text-slate-500">
            <Info className="tw-w-3 tw-h-3" />
            <span>Capital locked in active trades</span>
          </div>
        </motion.div>

        {/* Total P&L / Balance */}
        <motion.div 
          whileHover={{ y: -2 }}
          className="tw-bg-slate-900/50 tw-p-6 tw-rounded-2xl tw-border tw-border-slate-800 tw-shadow-sm"
        >
          <div className="tw-flex tw-items-center tw-justify-between tw-mb-4">
            <div className={`tw-p-2 tw-rounded-lg ${balances.total_pnl >= 0 ? 'tw-bg-emerald-500/10' : 'tw-bg-rose-500/10'}`}>
              {balances.total_pnl >= 0 ? (
                <ArrowDownLeft className="tw-w-5 tw-h-5 tw-text-emerald-400" />
              ) : (
                <ArrowUpRight className="tw-w-5 tw-h-5 tw-text-rose-400" />
              )}
            </div>
          </div>
          <p className="tw-text-slate-400 tw-text-xs tw-font-bold tw-uppercase tw-tracking-wider">Total Realized P&L</p>
          <h3 className={`tw-text-2xl tw-font-black tw-mt-1 ${balances.total_pnl >= 0 ? 'tw-text-emerald-400' : 'tw-text-rose-400'}`}>
            {formatCurrency(balances.total_pnl)}
          </h3>
          <div className="tw-mt-4 tw-flex tw-items-center tw-gap-2 tw-text-[10px] tw-text-slate-500">
            <Info className="tw-w-3 tw-h-3" />
            <span>All-time realized profit/loss</span>
          </div>
        </motion.div>
      </div>

      {/* Live Broker Alert */}
      {tradingMode === 'live' && (
        <div className="tw-p-4 tw-bg-amber-500/5 tw-border tw-border-amber-500/20 tw-rounded-xl tw-flex tw-items-start tw-gap-3">
          <Info className="tw-w-5 tw-h-5 tw-text-amber-400 tw-flex-shrink-0 tw-mt-0.5" />
          <div>
            <p className="tw-text-sm tw-text-amber-200 tw-font-semibold">Live Fund Sync</p>
            <p className="tw-text-xs tw-text-slate-400 tw-mt-1">
              Live trading funds are managed by your connected broker. Balances shown here are fetched in real-time from your demat account.
            </p>
            <button className="tw-mt-3 tw-flex tw-items-center tw-gap-1.5 tw-text-[10px] tw-text-amber-400 tw-font-bold tw-uppercase hover:tw-underline">
              Visit Broker Dashboard <ExternalLink className="tw-w-3 tw-h-3" />
            </button>
          </div>
        </div>
      )}

      {/* Fund Statement */}
      <div className="tw-bg-slate-950/30 tw-rounded-2xl tw-border tw-border-slate-800 tw-overflow-hidden">
        <div className="tw-p-6 tw-border-b tw-border-slate-800 tw-flex tw-items-center tw-justify-between">
          <div className="tw-flex tw-items-center tw-gap-3">
            <History className="tw-w-5 tw-h-5 tw-text-indigo-400" />
            <h3 className="tw-text-lg tw-font-bold tw-text-white">Fund Statement</h3>
          </div>
          <button 
            onClick={fetchFundData}
            className="tw-text-xs tw-font-bold tw-text-slate-400 hover:tw-text-white tw-transition-colors"
          >
            Refresh
          </button>
        </div>
        <div className="tw-p-0">
          <FundStatementTable statement={statement} loading={loading} />
        </div>
      </div>

      {/* Modal */}
      <AddFundsModal 
        isOpen={isAddFundsOpen} 
        onClose={() => setIsAddFundsOpen(false)} 
        onFundAdded={() => fetchFundData()} 
      />
    </div>
  );
};

export default FundsTab;
