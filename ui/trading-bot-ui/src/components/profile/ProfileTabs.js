// src/components/profile/ProfileTabs.jsx
import React from "react";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  LineChart,
  Coins,
  Briefcase,
  User,
  Shield,
  Bell,
  ChevronRight,
} from "lucide-react";

const ProfileTabs = ({
  activeTab,
  onTabChange,
  notificationCounts = {},
  securityAlerts = 0,
  brokerCount = 0,
}) => {
  const tabs = [
    {
      id: "overview",
      label: "Overview",
      description: "Summary & P&L",
      icon: LayoutDashboard,
      color: "tw-text-indigo-500",
      alert: false,
    },
    {
      id: "performance",
      label: "Performance",
      description: "Trade Analytics",
      icon: LineChart,
      color: "tw-text-emerald-500",
      alert: false,
    },
    {
      id: "funds",
      label: "Funds",
      description: "Capital & Ledger",
      icon: Coins,
      color: "tw-text-orange-500",
      alert: false,
    },
    {
      id: "brokers",
      label: "Brokers",
      description: "Manage Accounts",
      icon: Briefcase,
      color: "tw-text-blue-500",
      count: brokerCount > 0 ? brokerCount : null,
      alert: false,
    },
    {
      id: "settings",
      label: "Profile",
      description: "Personal Details",
      icon: User,
      color: "tw-text-purple-500",
      alert: false,
    },
    {
      id: "security",
      label: "Security",
      description: "2FA & Password",
      icon: Shield,
      color: "tw-text-rose-500",
      count: securityAlerts > 0 ? securityAlerts : null,
      alert: securityAlerts > 0,
    },
    {
      id: "notifications",
      label: "Notifications",
      description: "Alerts & Logs",
      icon: Bell,
      color: "tw-text-amber-500",
      count: notificationCounts?.unread || null,
      alert: false,
    },
  ];

  // Mobile Tab Item (Pill Shape)
  const MobileTabItem = ({ tab, isActive }) => (
    <button
      onClick={() => onTabChange(tab.id)}
      className={`tw-relative tw-flex-shrink-0 tw-flex tw-items-center tw-gap-2 tw-px-4 tw-py-2.5 tw-rounded-full tw-text-sm tw-font-medium tw-transition-all tw-duration-200 tw-outline-none ${
        isActive
          ? "tw-text-white"
          : "tw-bg-white tw-dark:bg-slate-800 tw-text-slate-600 tw-dark:text-slate-400 tw-border tw-border-slate-200 tw-dark:border-slate-700"
      }`}
    >
      {isActive && (
        <motion.div
          layoutId="activeMobileTab"
          className="tw-absolute tw-inset-0 tw-bg-indigo-600 tw-rounded-full"
          transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
        />
      )}

      <span className="tw-relative tw-z-10 tw-flex tw-items-center tw-gap-2">
        <tab.icon
          className={`tw-w-4 tw-h-4 ${isActive ? "tw-text-white" : tab.color}`}
        />
        {tab.label}
        {tab.count && (
          <span
            className={`tw-text-[10px] tw-px-1.5 tw-rounded-full ${
              isActive
                ? "tw-bg-white/20 tw-text-white"
                : "tw-bg-slate-100 tw-dark:bg-slate-700 tw-text-slate-600"
            }`}
          >
            {tab.count}
          </span>
        )}
      </span>
    </button>
  );

  // Desktop Sidebar Item (Rich List Item)
  const DesktopTabItem = ({ tab, isActive }) => (
    <button
      onClick={() => onTabChange(tab.id)}
      className={`tw-group tw-relative tw-flex tw-items-center tw-gap-4 tw-px-4 tw-py-4 tw-w-full tw-text-left tw-rounded-xl tw-transition-all tw-duration-200 tw-outline-none ${
        isActive
          ? "tw-bg-slate-50 tw-dark:bg-slate-800/80"
          : "tw-hover:bg-slate-50 tw-dark:tw-hover:bg-slate-800/50"
      }`}
    >
      {isActive && (
        <motion.div
          layoutId="activeDesktopTab"
          className="tw-absolute tw-left-0 tw-top-2 tw-bottom-2 tw-w-1 tw-bg-indigo-600 tw-rounded-r-full"
          transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
        />
      )}

      <div
        className={`tw-p-2 tw-rounded-lg tw-transition-colors ${
          isActive
            ? "tw-bg-white tw-dark:bg-slate-700 tw-shadow-sm"
            : "tw-bg-slate-100 tw-dark:bg-slate-800 tw-text-slate-400 tw-dark:text-slate-500 group-hover:tw-text-slate-600"
        }`}
      >
        <tab.icon
          className={`tw-w-5 tw-h-5 ${isActive ? tab.color : "tw-text-current"}`}
        />
      </div>

      <div className="tw-flex-1">
        <div className="tw-flex tw-items-center tw-justify-between">
          <span
            className={`tw-text-sm tw-font-semibold ${
              isActive
                ? "tw-text-slate-900 tw-dark:text-white"
                : "tw-text-slate-600 tw-dark:text-slate-400"
            }`}
          >
            {tab.label}
          </span>
          {tab.count && (
            <span
              className={`tw-text-[10px] tw-font-bold tw-px-2 tw-py-0.5 tw-rounded-full ${
                tab.alert
                  ? "tw-bg-rose-100 tw-text-rose-600 tw-animate-pulse"
                  : "tw-bg-slate-200 tw-text-slate-600 tw-dark:bg-slate-700 tw-dark:text-slate-300"
              }`}
            >
              {tab.count}
            </span>
          )}
        </div>
        <p className="tw-text-xs tw-text-slate-500 tw-dark:text-slate-500 tw-font-medium">
          {tab.description}
        </p>
      </div>

      {isActive && (
        <ChevronRight className="tw-w-4 tw-h-4 tw-text-indigo-600 tw-dark:text-indigo-400" />
      )}
    </button>
  );

  return (
    <div className="tw-w-full">
      {/* Mobile Horizontal Scroll */}
      <div className="tw-lg:hidden tw-mb-6">
        <div className="tw-flex tw-overflow-x-auto tw-pb-2 tw-gap-3 tw-no-scrollbar tw-mask-linear-fade">
          {tabs.map((tab) => (
            <MobileTabItem
              key={tab.id}
              tab={tab}
              isActive={activeTab === tab.id}
            />
          ))}
        </div>
      </div>

      {/* Desktop Vertical Sidebar */}
      <div className="tw-hidden tw-lg:flex tw-flex-col tw-gap-1">
        <div className="tw-px-4 tw-mb-2">
          <h3 className="tw-text-xs tw-font-bold tw-text-slate-400 tw-dark:text-slate-500 tw-uppercase tw-tracking-wider">
            Menu
          </h3>
        </div>
        {tabs.map((tab) => (
          <DesktopTabItem
            key={tab.id}
            tab={tab}
            isActive={activeTab === tab.id}
          />
        ))}
      </div>
    </div>
  );
};

export default ProfileTabs;
