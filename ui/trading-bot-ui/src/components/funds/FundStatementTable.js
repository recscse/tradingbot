import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, ArrowDownLeft, Receipt, Calendar } from 'lucide-react';

const FundStatementTable = ({ statement, loading }) => {
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="tw-space-y-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="tw-h-16 tw-bg-slate-800/50 tw-rounded-xl tw-animate-pulse" />
        ))}
      </div>
    );
  }

  if (!statement || statement.length === 0) {
    return (
      <div className="tw-text-center tw-py-12 tw-bg-slate-900/50 tw-rounded-2xl tw-border tw-border-slate-800">
        <Receipt className="tw-w-12 tw-h-12 tw-text-slate-700 tw-mx-auto tw-mb-4" />
        <h3 className="tw-text-lg tw-font-semibold tw-text-slate-300">No transactions found</h3>
        <p className="tw-text-slate-500 tw-text-sm">Your fund movements will appear here.</p>
      </div>
    );
  }

  return (
    <div className="tw-overflow-hidden tw-rounded-2xl tw-border tw-border-slate-800">
      <div className="tw-overflow-x-auto">
        <table className="tw-w-full tw-text-left tw-border-collapse">
          <thead>
            <tr className="tw-bg-slate-800/50 tw-text-slate-400 tw-text-xs tw-uppercase tw-tracking-wider">
              <th className="tw-px-6 tw-py-4 tw-font-bold">Date & Description</th>
              <th className="tw-px-6 tw-py-4 tw-font-bold">Type</th>
              <th className="tw-px-6 tw-py-4 tw-font-bold tw-text-right">Amount</th>
              <th className="tw-px-6 tw-py-4 tw-font-bold tw-text-right">Running Balance</th>
            </tr>
          </thead>
          <tbody className="tw-divide-y tw-divide-slate-800">
            {statement.map((entry, index) => (
              <motion.tr
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                key={entry.id}
                className="tw-bg-slate-900/30 hover:tw-bg-slate-800/40 tw-transition-colors"
              >
                <td className="tw-px-6 tw-py-4">
                  <div className="tw-flex tw-flex-col">
                    <span className="tw-text-sm tw-font-semibold tw-text-white">{entry.description}</span>
                    <div className="tw-flex tw-items-center tw-gap-1.5 tw-mt-1">
                      <Calendar className="tw-w-3 tw-h-3 tw-text-slate-500" />
                      <span className="tw-text-[10px] tw-text-slate-500 tw-font-medium">{formatDate(entry.timestamp)}</span>
                      {entry.reference_id && (
                        <span className="tw-text-[10px] tw-bg-slate-800 tw-text-slate-400 tw-px-1.5 tw-py-0.5 tw-rounded">
                          Ref: {entry.reference_id}
                        </span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="tw-px-6 tw-py-4">
                  <div className="tw-flex tw-items-center tw-gap-2">
                    {entry.type === 'CREDIT' ? (
                      <div className="tw-p-1.5 tw-bg-emerald-500/10 tw-rounded-lg">
                        <ArrowDownLeft className="tw-w-3.5 tw-h-3.5 tw-text-emerald-400" />
                      </div>
                    ) : (
                      <div className="tw-p-1.5 tw-bg-rose-500/10 tw-rounded-lg">
                        <ArrowUpRight className="tw-w-3.5 tw-h-3.5 tw-text-rose-400" />
                      </div>
                    )}
                    <span className={`tw-text-xs tw-font-bold ${entry.type === 'CREDIT' ? 'tw-text-emerald-400' : 'tw-text-rose-400'}`}>
                      {entry.category.replace('_', ' ')}
                    </span>
                  </div>
                </td>
                <td className="tw-px-6 tw-py-4 tw-text-right">
                  <span className={`tw-text-sm tw-font-black ${entry.type === 'CREDIT' ? 'tw-text-emerald-400' : 'tw-text-rose-400'}`}>
                    {entry.type === 'CREDIT' ? '+' : '-'}{formatCurrency(entry.amount)}
                  </span>
                </td>
                <td className="tw-px-6 tw-py-4 tw-text-right">
                  <span className="tw-text-sm tw-font-bold tw-text-slate-300">
                    {formatCurrency(entry.balance_after)}
                  </span>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default FundStatementTable;
