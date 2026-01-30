import React from 'react';
import SystemHealthDashboard from '../components/dashboard/SystemHealthDashboard';
import { ShieldCheck, Activity } from 'lucide-react';

const SystemHealthPage = () => {
  return (
    <div className="tw-min-h-screen tw-bg-gray-50/50 tw-p-4 md:tw-p-8">
      <div className="tw-max-w-7xl tw-mx-auto tw-space-y-8">
        {/* Header Section */}
        <div className="tw-flex tw-flex-col md:tw-flex-row md:tw-items-end tw-justify-between tw-gap-4">
          <div className="tw-space-y-2">
            <div className="tw-flex tw-items-center tw-gap-2 tw-text-blue-600 tw-font-bold tw-uppercase tw-tracking-widest tw-text-xs">
              <ShieldCheck className="tw-w-4 tw-h-4" />
              Security & Monitoring
            </div>
            <h1 className="tw-text-3xl md:tw-text-4xl tw-font-black tw-text-gray-900 tw-tracking-tight tw-flex tw-items-center tw-gap-3">
              System Health 
              <span className="tw-text-gray-300 tw-font-light">|</span>
              <span className="tw-text-blue-600">Core Matrix</span>
            </h1>
            <p className="tw-text-gray-500 tw-font-medium tw-max-w-2xl">
              Real-time telemetry from system infrastructure, execution engines, and automated business logic. 
              Monitor health, latency, and live operational logs.
            </p>
          </div>
          
          <div className="tw-flex tw-items-center tw-gap-3 tw-bg-white tw-px-4 tw-py-2 tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100">
            <div className="tw-w-2 tw-h-2 tw-rounded-full tw-bg-green-500 tw-animate-pulse"></div>
            <span className="tw-text-xs tw-font-bold tw-text-gray-600 tw-uppercase tw-tracking-tighter tw-flex tw-items-center tw-gap-2">
              <Activity className="tw-w-3.5 tw-h-3.5" /> Live Matrix Active
            </span>
          </div>
        </div>

        {/* Dashboard Component */}
        <SystemHealthDashboard />
      </div>
    </div>
  );
};

export default SystemHealthPage;
