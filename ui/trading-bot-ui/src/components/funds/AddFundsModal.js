import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Plus, ShieldCheck } from "lucide-react";
import { toast } from "react-hot-toast";
import api from "../../services/api";

const AddFundsModal = ({ isOpen, onClose, onFundAdded }) => {
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);

  const presetAmounts = [10000, 50000, 100000, 500000];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!amount || isNaN(amount) || amount <= 0) {
      toast.error("Please enter a valid amount");
      return;
    }

    setLoading(true);
    try {
      const response = await api.post(
        `/v1/trading/execution/funds/add-paper-funds?amount=${amount}`,
      );
      if (response.data.success) {
        toast.success(
          `Successfully added ₹${parseFloat(amount).toLocaleString()} to paper account`,
        );
        onFundAdded(response.data.new_balance);
        onClose();
        setAmount("");
      } else {
        toast.error(response.data.error || "Failed to add funds");
      }
    } catch (error) {
      console.error("Error adding funds:", error);
      toast.error("An error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="tw-fixed tw-inset-0 tw-z-[100] tw-flex tw-items-end sm:tw-items-center tw-justify-center tw-p-0 sm:tw-p-4 tw-bg-slate-950/80 tw-backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, y: "100%" }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="tw-bg-slate-900 tw-border-t sm:tw-border tw-border-slate-800 tw-rounded-t-3xl sm:tw-rounded-2xl tw-shadow-2xl tw-max-w-md tw-w-full tw-overflow-hidden"
          >
            {/* Mobile Handle */}
            <div className="tw-flex sm:tw-hidden tw-justify-center tw-pt-3">
              <div className="tw-w-12 tw-h-1 tw-bg-slate-700 tw-rounded-full" />
            </div>

            {/* Header */}
            <div className="tw-p-6 tw-border-b tw-border-slate-800 tw-flex tw-items-center tw-justify-between">
              <div className="tw-flex tw-items-center tw-gap-3">
                <div className="tw-p-2 tw-bg-indigo-500/10 tw-rounded-lg">
                  <Plus className="tw-w-5 tw-h-5 tw-text-indigo-400" />
                </div>
                <div>
                  <h3 className="tw-text-xl tw-font-bold tw-text-white">
                    Add Paper Funds
                  </h3>
                  <p className="tw-text-slate-400 tw-text-xs sm:tw-text-sm">
                    Increase your virtual capital
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="tw-p-2 tw-text-slate-400 hover:tw-text-white tw-transition-colors"
              >
                <X className="tw-w-6 tw-h-6" />
              </button>
            </div>

            <form
              onSubmit={handleSubmit}
              className="tw-p-6 tw-pb-10 sm:tw-pb-6"
            >
              {/* Presets */}
              <div className="tw-mb-6">
                <label className="tw-block tw-text-xs tw-font-bold tw-text-slate-500 tw-uppercase tw-tracking-widest tw-mb-3">
                  Quick Presets
                </label>
                <div className="tw-grid tw-grid-cols-2 tw-gap-3">
                  {presetAmounts.map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setAmount(amt.toString())}
                      className="tw-py-3 tw-px-4 tw-bg-slate-800/50 hover:tw-bg-indigo-600/20 hover:tw-border-indigo-500/50 tw-border tw-border-slate-700 tw-rounded-xl tw-text-white tw-text-sm tw-font-bold tw-transition-all active:tw-scale-95"
                    >
                      ₹{amt.toLocaleString()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Amount */}
              <div className="tw-mb-6">
                <label className="tw-block tw-text-xs tw-font-bold tw-text-slate-500 tw-uppercase tw-tracking-widest tw-mb-2">
                  Enter Amount
                </label>
                <div className="tw-relative">
                  <div className="tw-absolute tw-left-4 tw-top-1/2 -tw-translate-y-1/2 tw-text-slate-500 tw-font-black tw-text-xl">
                    ₹
                  </div>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    className="tw-w-full tw-bg-slate-950 tw-border tw-border-slate-700 tw-rounded-xl tw-py-4 tw-pl-10 tw-pr-4 tw-text-white tw-text-2xl tw-font-black focus:tw-outline-none focus:tw-border-indigo-500 focus:tw-ring-1 focus:tw-ring-indigo-500 tw-transition-all"
                    required
                  />
                </div>
              </div>

              {/* Safety Info */}
              <div className="tw-mb-8 tw-p-4 tw-bg-indigo-500/5 tw-border tw-border-indigo-500/10 tw-rounded-xl tw-flex tw-items-start tw-gap-3">
                <ShieldCheck className="tw-w-5 tw-h-5 tw-text-indigo-400 tw-flex-shrink-0 tw-mt-0.5" />
                <p className="tw-text-[11px] tw-text-slate-400 tw-leading-relaxed">
                  <span className="tw-text-indigo-400 tw-font-bold">
                    Virtual Capital:
                  </span>{" "}
                  This will update your paper trading balance instantly. No real
                  bank transactions are involved.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="tw-w-full tw-py-4 tw-bg-indigo-600 hover:tw-bg-indigo-700 disabled:tw-opacity-50 tw-text-white tw-rounded-xl tw-font-bold tw-text-lg tw-transition-all tw-flex tw-items-center tw-justify-center tw-gap-2 tw-shadow-lg tw-shadow-indigo-900/20 active:tw-scale-[0.98]"
              >
                {loading ? (
                  <div className="tw-w-6 tw-h-6 tw-border-2 tw-border-white/20 tw-border-t-white tw-rounded-full tw-animate-spin" />
                ) : (
                  <>
                    <Plus className="tw-w-5 tw-h-5" />
                    Confirm Deposit
                  </>
                )}
              </button>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default AddFundsModal;
