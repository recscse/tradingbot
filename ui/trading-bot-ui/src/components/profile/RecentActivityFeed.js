import React, { useMemo } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Wallet, 
  Shield, 
  LogIn, 
  Activity
} from "lucide-react";

const RecentActivityFeed = ({
  activities = [],
  loading = false,
  error = null,
  maxItems = 20,
}) => {

  const getActivityData = (activity) => {
    if (!activity) return { icon: Activity, color: "tw-text-slate-400", bg: "tw-bg-slate-50", label: "Event" };

    const type = activity.type?.toLowerCase() || "";
    const description = activity.description?.toLowerCase() || "";
    const action = activity.action?.toLowerCase() || "";

    if (description.includes("buy") || action === "buy") {
      return { icon: TrendingUp, color: "tw-text-emerald-600", bg: "tw-bg-emerald-50", label: "BUY" };
    }
    if (description.includes("sell") || action === "sell") {
      return { icon: TrendingDown, color: "tw-text-rose-600", bg: "tw-bg-rose-50", label: "SELL" };
    }
    if (type === "security" || description.includes("password")) {
      return { icon: Shield, color: "tw-text-amber-600", bg: "tw-bg-amber-50", label: "SECURITY" };
    }
    if (type === "broker" || description.includes("broker")) {
      return { icon: Wallet, color: "tw-text-blue-600", bg: "tw-bg-blue-50", label: "BROKER" };
    }
    if (type === "login") {
      return { icon: LogIn, color: "tw-text-indigo-600", bg: "tw-bg-indigo-50", label: "LOGIN" };
    }
    
    return { icon: Activity, color: "tw-text-slate-600", bg: "tw-bg-slate-50", label: "SYSTEM" };
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return "Recent";
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  };

  const filteredActivities = useMemo(() => {
    return (activities || []).slice(0, maxItems);
  }, [activities, maxItems]);

  if (loading) {
    return (
      <div className="tw-space-y-4 tw-p-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="tw-flex tw-gap-3 tw-animate-pulse">
            <div className="tw-w-10 tw-h-10 tw-bg-slate-100 tw-rounded-full" />
            <div className="tw-flex-1 tw-space-y-2">
              <div className="tw-h-3 tw-bg-slate-100 tw-rounded tw-w-1/4" />
              <div className="tw-h-4 tw-bg-slate-100 tw-rounded tw-w-3/4" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!activities?.length) {
    return (
      <div className="tw-py-12 tw-text-center">
        <Clock className="tw-w-10 tw-h-10 tw-text-slate-200 tw-mx-auto tw-mb-3" />
        <p className="tw-text-sm tw-text-slate-400 tw-font-medium">No recent activity found</p>
      </div>
    );
  }

  return (
    <div className="tw-divide-y tw-divide-slate-50 tw-dark:divide-slate-800">
      {filteredActivities.map((activity, idx) => {
        const data = getActivityData(activity);
        const Icon = data.icon;
        
        return (
          <div key={idx} className="tw-p-4 hover:tw-bg-slate-50/50 tw-dark:hover:tw-bg-slate-800/30 tw-transition-colors tw-group">
            <div className="tw-flex tw-items-start tw-gap-4">
              <div className={`tw-p-2 tw-rounded-xl ${data.bg} tw-dark:tw-bg-opacity-10 ${data.color} tw-flex-shrink-0`}>
                <Icon className="tw-w-4 tw-h-4" />
              </div>
              <div className="tw-flex-1 tw-min-w-0">
                <div className="tw-flex tw-items-center tw-justify-between tw-mb-1">
                  <span className={`tw-text-[10px] tw-font-black tw-uppercase tw-tracking-widest ${data.color}`}>
                    {data.label}
                  </span>
                  <span className="tw-text-[10px] tw-text-slate-400 tw-font-bold tw-flex tw-items-center tw-gap-1">
                    <Clock className="tw-w-3 tw-h-3" />
                    {formatTime(activity.timestamp || activity.created_at)}
                  </span>
                </div>
                <p className="tw-text-xs tw-font-bold tw-text-slate-700 tw-dark:text-slate-300 tw-leading-relaxed tw-truncate">
                  {activity.description || activity.message}
                </p>
                {activity.status && (
                  <span className={`tw-inline-block tw-mt-2 tw-px-1.5 tw-py-0.5 tw-rounded tw-text-[9px] tw-font-black tw-uppercase tw-tracking-tighter ${
                    activity.status === 'completed' ? 'tw-bg-green-100 tw-text-green-700' : 'tw-bg-slate-100 tw-text-slate-600'
                  }`}>
                    {activity.status}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default RecentActivityFeed;