import React, { useState } from "react";
import { 
  ShieldCheck, 
  ShieldAlert, 
  ExternalLink, 
  MoreVertical,
  Trash2,
  Edit2
} from "lucide-react";

const BrokerAccountCard = ({
  account,
  onEdit,
  onDelete,
  onView,
  onToggleStatus,
  variant = "default",
}) => {
  const [showMenu, setShowMenu] = useState(false);

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const brokerColors = {
    zerodha: "tw-bg-orange-500",
    upstox: "tw-bg-indigo-600",
    dhan: "tw-bg-amber-500",
    fyers: "tw-bg-emerald-500",
    angel: "tw-bg-blue-600",
  };

  const getBrokerColor = (name) => {
    const key = name?.toLowerCase().split(" ")[0];
    return brokerColors[key] || "tw-bg-slate-600";
  };

  if (variant === "compact") {
    return (
      <div className="tw-group tw-flex tw-items-center tw-gap-3 tw-p-3 tw-rounded-2xl tw-bg-slate-50 tw-dark:bg-slate-800/50 tw-border tw-border-slate-100 tw-dark:border-slate-800 hover:tw-border-indigo-500/30 tw-transition-all">
        <div className={`tw-w-10 tw-h-10 tw-rounded-xl ${getBrokerColor(account.broker_name)} tw-text-white tw-flex tw-items-center tw-justify-center tw-font-black tw-text-sm tw-shadow-sm`}>
          {account.broker_name?.[0].toUpperCase()}
        </div>
        <div className="tw-flex-1 tw-min-w-0">
          <div className="tw-text-xs tw-font-black tw-text-slate-900 tw-dark:text-white tw-truncate">
            {account.broker_name}
          </div>
          <div className="tw-text-[10px] tw-font-bold tw-text-indigo-600 tw-dark:text-indigo-400">
            {formatCurrency(account.balance)}
          </div>
        </div>
        <div className={`tw-w-2 tw-h-2 tw-rounded-full ${account.is_active ? 'tw-bg-green-500' : 'tw-bg-slate-300'}`} />
      </div>
    );
  }

  return (
    <div className="tw-relative tw-bg-white tw-dark:bg-slate-900 tw-rounded-3xl tw-p-6 tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm group hover:tw-shadow-md tw-transition-all">
      <div className="tw-flex tw-items-start tw-justify-between tw-mb-6">
        <div className="tw-flex tw-items-center tw-gap-4">
          <div className={`tw-w-12 tw-h-12 tw-rounded-2xl ${getBrokerColor(account.broker_name)} tw-text-white tw-flex tw-items-center tw-justify-center tw-font-black tw-text-xl tw-shadow-lg`}>
            {account.broker_name?.[0].toUpperCase()}
          </div>
          <div>
            <h3 className="tw-text-lg tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight">{account.broker_name}</h3>
            <div className="tw-flex tw-items-center tw-gap-2">
              <span className={`tw-flex tw-items-center tw-gap-1 tw-text-[10px] tw-font-black tw-uppercase ${account.is_active ? 'tw-text-green-600' : 'tw-text-slate-400'}`}>
                {account.is_active ? <ShieldCheck className="tw-w-3 tw-h-3" /> : <ShieldAlert className="tw-w-3 tw-h-3" />}
                {account.is_active ? 'Connected' : 'Offline'}
              </span>
            </div>
          </div>
        </div>
        
        <div className="tw-relative">
          <button 
            onClick={() => setShowMenu(!showMenu)}
            className="tw-p-2 tw-rounded-xl hover:tw-bg-slate-50 tw-dark:hover:tw-bg-slate-800 tw-text-slate-400 tw-transition-colors"
          >
            <MoreVertical className="tw-w-5 tw-h-5" />
          </button>
          
          {showMenu && (
            <div className="tw-absolute tw-right-0 tw-mt-2 tw-w-48 tw-bg-white tw-dark:bg-slate-800 tw-rounded-2xl tw-shadow-xl tw-border tw-border-slate-100 tw-dark:border-slate-700 tw-z-50 tw-overflow-hidden">
              <button className="tw-w-full tw-flex tw-items-center tw-gap-3 tw-px-4 tw-py-3 tw-text-xs tw-font-bold tw-text-slate-600 tw-dark:text-slate-300 hover:tw-bg-slate-50 tw-dark:hover:tw-bg-slate-700/50 tw-transition-colors">
                <ExternalLink className="tw-w-4 tw-h-4" /> View Details
              </button>
              <button className="tw-w-full tw-flex tw-items-center tw-gap-3 tw-px-4 tw-py-3 tw-text-xs tw-font-bold tw-text-slate-600 tw-dark:text-slate-300 hover:tw-bg-slate-50 tw-dark:hover:tw-bg-slate-700/50 tw-transition-colors">
                <Edit2 className="tw-w-4 tw-h-4" /> Edit Account
              </button>
              <button className="tw-w-full tw-flex tw-items-center tw-gap-3 tw-px-4 tw-py-3 tw-text-xs tw-font-bold tw-text-rose-600 hover:tw-bg-rose-50 tw-dark:hover:tw-bg-rose-900/20 tw-transition-colors">
                <Trash2 className="tw-w-4 tw-h-4" /> Remove
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="tw-space-y-4">
        <div className="tw-p-4 tw-rounded-2xl tw-bg-slate-50 tw-dark:bg-slate-800/50 tw-border tw-border-slate-100 tw-dark:border-slate-800">
          <div className="tw-text-[10px] tw-font-black tw-text-slate-400 tw-uppercase tw-tracking-widest tw-mb-1">Current Balance</div>
          <div className="tw-text-2xl tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tight">
            {formatCurrency(account.balance)}
          </div>
        </div>
        
        <div className="tw-grid tw-grid-cols-2 tw-gap-3">
          <div className="tw-p-3 tw-rounded-xl tw-bg-white tw-dark:bg-slate-900 tw-border tw-border-slate-100 tw-dark:border-slate-800">
            <div className="tw-text-[9px] tw-font-bold tw-text-slate-400 tw-uppercase tw-mb-1">Daily P&L</div>
            <div className="tw-text-xs tw-font-black tw-text-green-600">+₹2,450</div>
          </div>
          <div className="tw-p-3 tw-rounded-xl tw-bg-white tw-dark:bg-slate-900 tw-border tw-border-slate-100 tw-dark:border-slate-800">
            <div className="tw-text-[9px] tw-font-bold tw-text-slate-400 tw-uppercase tw-mb-1">Margin Used</div>
            <div className="tw-text-xs tw-font-black tw-text-slate-900 tw-dark:text-white">₹12,000</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BrokerAccountCard;