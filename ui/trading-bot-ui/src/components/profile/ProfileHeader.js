// src/components/profile/ProfileHeader.jsx
import React, { useRef, useState } from "react";
import {
  Camera,
  Wallet,
  Activity,
  ShieldCheck,
  AlertCircle
} from "lucide-react";

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
    <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-2xl tw-border tw-border-slate-200 tw-dark:border-slate-800 tw-shadow-sm tw-overflow-hidden">
      <div className="tw-p-6">
        <div className="tw-flex tw-flex-col tw-lg:flex-row tw-gap-8 tw-items-start tw-lg:items-center">
          
          {/* User Identity Section */}
          <div className="tw-flex tw-items-center tw-gap-5 tw-w-full tw-lg:w-auto tw-lg:max-w-[350px] tw-flex-shrink-0 tw-min-w-0">
            <div className="tw-relative tw-group tw-flex-shrink-0">
              <div 
                onClick={handleAvatarClick}
                className="tw-w-20 tw-h-20 tw-rounded-xl tw-bg-slate-100 tw-dark:bg-slate-800 tw-border-2 tw-border-slate-200 tw-dark:border-slate-700 tw-flex tw-items-center tw-justify-center tw-overflow-hidden tw-cursor-pointer tw-relative"
              >
                {uploadingAvatar && (
                  <div className="tw-absolute tw-inset-0 tw-bg-black/50 tw-flex tw-items-center tw-justify-center tw-z-10">
                    <div className="tw-w-6 tw-h-6 tw-border-2 tw-border-white tw-border-t-transparent tw-rounded-full tw-animate-spin" />
                  </div>
                )}
                {profileData?.avatar ? (
                  <img src={profileData.avatar} alt="Profile" className="tw-w-full tw-h-full tw-object-cover" />
                ) : (
                  <span className="tw-text-2xl tw-font-bold tw-text-slate-500 tw-dark:text-slate-400 tw-font-mono">{getInitials(profileData?.full_name)}</span>
                )}
                <div className="tw-absolute tw-inset-0 tw-bg-black/60 tw-opacity-0 group-hover:tw-opacity-100 tw-transition-opacity tw-flex tw-items-center tw-justify-center">
                  <Camera className="tw-text-white tw-w-6 tw-h-6" />
                </div>
              </div>
              <div className={`tw-absolute tw--bottom-1 tw--right-1 tw-w-4 tw-h-4 tw-rounded-full tw-border-2 tw-border-white tw-dark:border-slate-900 ${profileData?.is_active ? "tw-bg-emerald-500" : "tw-bg-slate-400"}`} />
            </div>

            <div className="tw-flex-1 tw-min-w-0">
              <h1 className="tw-text-xl tw-font-bold tw-text-slate-900 tw-dark:text-white tw-truncate tw-leading-tight">
                {profileData?.full_name || "Trader"}
              </h1>
              <div className="tw-flex tw-items-center tw-gap-2 tw-mt-1">
                <span className="tw-px-2 tw-py-0.5 tw-rounded tw-bg-slate-100 tw-dark:bg-slate-800 tw-text-xs tw-font-mono tw-text-slate-500 tw-dark:text-slate-400 tw-uppercase">
                  {profileData?.role || "PRO"}
                </span>
                {profileData?.isVerified && (
                  <span className="tw-flex tw-items-center tw-gap-1 tw-text-emerald-600 tw-dark:text-emerald-500 tw-text-xs tw-font-medium">
                    <ShieldCheck className="tw-w-3 tw-h-3" /> Verified
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="tw-hidden tw-lg:block tw-w-px tw-h-12 tw-bg-slate-200 tw-dark:bg-slate-800" />

          {/* Stats Section - Grouped to stay near the identity section */}
          <div className="tw-flex tw-flex-wrap tw-gap-x-10 tw-gap-y-6 tw-items-center">
            
            {/* 1. P&L */}
            <div className="tw-flex tw-flex-col tw-min-w-0">
              <span className="tw-text-[10px] tw-text-slate-500 tw-dark:text-slate-400 tw-uppercase tw-tracking-wider tw-font-bold tw-mb-1">
                Today's P&L
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <span className={`tw-text-lg tw-lg:tw-text-xl tw-font-mono tw-font-bold ${isProfit ? "tw-text-emerald-600 tw-dark:tw-text-emerald-500" : "tw-text-rose-600 tw-dark:tw-text-rose-500"}`}>
                  {isProfit ? "+" : "-"}{formatCurrency(pnl)}
                </span>
              </div>
            </div>

            {/* 2. Status */}
            <div className="tw-flex tw-flex-col tw-min-w-0">
              <span className="tw-text-[10px] tw-text-slate-500 tw-dark:text-slate-400 tw-uppercase tw-tracking-wider tw-font-bold tw-mb-1">
                System Status
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <Activity className="tw-w-4 tw-h-4 tw-text-emerald-500" />
                <span className="tw-text-xs tw-lg:tw-text-sm tw-font-bold tw-text-emerald-600 tw-dark:tw-text-emerald-500">
                  Operational
                </span>
              </div>
            </div>

            {/* 3. Brokers */}
            <div className="tw-flex tw-flex-col tw-min-w-0">
              <span className="tw-text-[10px] tw-text-slate-500 tw-dark:text-slate-400 tw-uppercase tw-tracking-wider tw-font-bold tw-mb-1">
                Brokers
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <Wallet className="tw-w-4 tw-h-4 tw-text-slate-400" />
                <span className="tw-text-lg tw-lg:tw-text-xl tw-font-mono tw-font-bold tw-text-slate-900 tw-dark:text-white">
                  {profileData?.brokerAccounts?.length || 0}
                </span>
              </div>
            </div>

            {/* 4. Alerts */}
            <div className="tw-flex tw-flex-col tw-min-w-0">
              <span className="tw-text-[10px] tw-text-slate-500 tw-dark:text-slate-400 tw-uppercase tw-tracking-wider tw-font-bold tw-mb-1">
                Alerts
              </span>
              <div className="tw-flex tw-items-center tw-gap-2">
                <span className={`tw-text-lg tw-lg:tw-text-xl tw-font-mono tw-font-bold ${(profileData?.securityAlerts || 0) > 0 ? "tw-text-amber-500" : "tw-text-slate-400"}`}>
                  {profileData?.securityAlerts || 0}
                </span>
                {(profileData?.securityAlerts || 0) > 0 && <AlertCircle className="tw-w-4 tw-h-4 tw-text-amber-500 tw-animate-pulse" />}
              </div>
            </div>

          </div>
        </div>
      </div>
      <div className={`tw-h-1 tw-w-full ${isProfit ? "tw-bg-emerald-500" : "tw-bg-rose-500"}`} />
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} className="tw-hidden" />
    </div>
  );
};

export default ProfileHeader;