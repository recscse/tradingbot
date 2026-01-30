import React, { useRef, useState } from "react";
import {
  Camera,
  Activity,
  ShieldCheck,
  Zap,
  TrendingUp,
  TrendingDown
} from "lucide-react";
import { motion } from "framer-motion";

const ProfileHeader = ({ profileData, onAvatarUpload }) => {
  const fileInputRef = useRef(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setUploadingAvatar(true);
      try {
        await onAvatarUpload(file);
      } finally {
        setUploadingAvatar(false);
      }
    }
  };

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0.00";
    return `₹${Math.abs(amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  };

  const getInitials = (name) => {
    if (!name) return "TR";
    return name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const pnl = profileData?.todayPnl || 0;
  const isProfit = pnl >= 0;

  return (
    <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-3xl tw-border tw-border-slate-100 tw-dark:border-slate-800 tw-shadow-sm tw-overflow-hidden">
      <div className="tw-p-6 md:tw-p-8">
        <div className="tw-flex tw-flex-col lg:tw-flex-row tw-gap-8 tw-items-start lg:tw-items-center">
          
          {/* User Identity Section */}
          <div className="tw-flex tw-items-center tw-gap-6 tw-w-full lg:tw-auto lg:tw-max-w-[400px] tw-flex-shrink-0 tw-min-w-0">
            <div className="tw-relative tw-group tw-flex-shrink-0">
              <motion.div 
                whileHover={{ scale: 1.05 }}
                onClick={handleAvatarClick}
                className="tw-w-24 tw-h-24 tw-rounded-3xl tw-bg-slate-50 tw-dark:bg-slate-800 tw-border-2 tw-border-slate-100 tw-dark:border-slate-700 tw-flex tw-items-center tw-justify-center tw-overflow-hidden tw-cursor-pointer tw-relative tw-shadow-inner"
              >
                {uploadingAvatar && (
                  <div className="tw-absolute tw-inset-0 tw-bg-black/50 tw-flex tw-items-center tw-justify-center tw-z-10">
                    <div className="tw-w-6 tw-h-6 tw-border-2 tw-border-white tw-border-t-transparent tw-rounded-full tw-animate-spin" />
                  </div>
                )}
                {profileData?.avatar ? (
                  <img src={profileData.avatar} alt="Profile" className="tw-w-full tw-h-full tw-object-cover" />
                ) : (
                  <span className="tw-text-3xl tw-font-black tw-text-indigo-600 tw-dark:text-indigo-400 tw-font-mono">{getInitials(profileData?.full_name)}</span>
                )}
                <div className="tw-absolute tw-inset-0 tw-bg-black/60 tw-opacity-0 group-hover:tw-opacity-100 tw-transition-opacity tw-flex tw-items-center tw-justify-center">
                  <Camera className="tw-text-white tw-w-6 tw-h-6" />
                </div>
              </motion.div>
              <div className={`tw-absolute tw--bottom-1 tw--right-1 tw-w-6 tw-h-6 tw-rounded-full tw-border-4 tw-border-white tw-dark:border-slate-900 ${profileData?.is_active ? "tw-bg-green-500" : "tw-bg-slate-400 shadow-sm"}`} />
            </div>

            <div className="tw-flex-1 tw-min-w-0">
              <div className="tw-flex tw-items-center tw-gap-2 tw-mb-1">
                <span className="tw-px-2 tw-py-0.5 tw-rounded-lg tw-bg-indigo-50 tw-dark:tw-bg-indigo-950/30 tw-text-[10px] tw-font-black tw-text-indigo-600 tw-dark:text-indigo-400 tw-uppercase tw-tracking-widest">
                  {profileData?.role || "TRADER PRO"}
                </span>
                {profileData?.isVerified && (
                  <ShieldCheck className="tw-w-4 tw-h-4 tw-text-emerald-500" />
                )}
              </div>
              <h1 className="tw-text-2xl tw-font-black tw-text-slate-900 tw-dark:text-white tw-truncate tw-tracking-tight tw-leading-none">
                {profileData?.full_name || "Anonymous Trader"}
              </h1>
              <p className="tw-text-xs tw-font-bold tw-text-slate-400 tw-mt-2 tw-flex tw-items-center tw-gap-1">
                <ShieldCheck className="tw-w-3 tw-h-3" /> Standard Account Verified
              </p>
            </div>
          </div>

          {/* Divider */}
          <div className="tw-hidden lg:tw-block tw-w-px tw-h-16 tw-bg-slate-100 tw-dark:bg-slate-800" />

          {/* Dynamic Stats Grid */}
          <div className="tw-flex tw-flex-wrap tw-gap-x-12 tw-gap-y-6 tw-items-center tw-w-full">
            
            <div className="tw-flex tw-flex-col tw-min-w-0">
              <span className="tw-text-[10px] tw-text-slate-400 tw-uppercase tw-tracking-widest tw-font-black tw-mb-2">
                Today's P&L
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <div className={`tw-p-1.5 tw-rounded-lg ${isProfit ? 'tw-bg-emerald-50 tw-text-emerald-600' : 'tw-bg-rose-50 tw-text-rose-600'}`}>
                  {isProfit ? <TrendingUp className="tw-w-4 tw-h-4" /> : <TrendingDown className="tw-w-4 tw-h-4" />}
                </div>
                <span className={`tw-text-xl tw-font-black tw-font-mono tw-tracking-tighter ${isProfit ? "tw-text-emerald-600" : "tw-text-rose-600"}`}>
                  {isProfit ? "+" : "-"}{formatCurrency(pnl)}
                </span>
              </div>
            </div>

            <div className="tw-flex tw-flex-col tw-min-w-0">
              <span className="tw-text-[10px] tw-text-slate-400 tw-uppercase tw-tracking-widest tw-font-black tw-mb-2">
                System Health
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <div className="tw-p-1.5 tw-rounded-lg tw-bg-blue-50 tw-text-blue-600">
                  <Activity className="tw-w-4 tw-h-4" />
                </div>
                <span className="tw-text-sm tw-font-black tw-text-slate-900 tw-dark:text-white tw-uppercase tw-tracking-tight">
                  Operational
                </span>
              </div>
            </div>

            <div className="tw-flex tw-flex-col tw-min-w-0">
              <span className="tw-text-[10px] tw-text-slate-400 tw-uppercase tw-tracking-widest tw-font-black tw-mb-2">
                Trading Mode
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <div className="tw-p-1.5 tw-rounded-lg tw-bg-amber-50 tw-text-amber-600">
                  <Zap className="tw-w-4 tw-h-4" />
                </div>
                <span className="tw-text-sm tw-font-black tw-text-slate-900 tw-dark:text-white tw-uppercase tw-tracking-tight">
                  Auto-Paper
                </span>
              </div>
            </div>

            <div className="tw-flex tw-flex-col tw-min-w-0 lg:tw-ml-auto">
              <span className="tw-text-[10px] tw-text-slate-400 tw-uppercase tw-tracking-widest tw-font-black tw-mb-2">
                Account Status
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <div className="tw-flex tw--space-x-2">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="tw-w-8 tw-h-8 tw-rounded-full tw-bg-slate-100 tw-border-2 tw-border-white tw-dark:tw-border-slate-900 tw-flex tw-items-center tw-justify-center tw-text-[10px] tw-font-bold tw-text-slate-400">
                      {i}
                    </div>
                  ))}
                </div>
                <span className="tw-text-[10px] tw-font-bold tw-text-slate-500 tw-ml-2">
                  {profileData?.brokerAccounts?.length || 0} Brokers Active
                </span>
              </div>
            </div>

          </div>
        </div>
      </div>
      <div className={`tw-h-1.5 tw-w-full ${isProfit ? "tw-bg-emerald-500" : "tw-bg-rose-500"}`} />
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} className="tw-hidden" />
    </div>
  );
};

export default ProfileHeader;
