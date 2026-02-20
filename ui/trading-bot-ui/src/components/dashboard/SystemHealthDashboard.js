import React, { useState, useEffect, useMemo } from 'react';
import { 
  Activity, 
  Database, 
  Server, 
  Zap, 
  ShieldCheck, 
  AlertTriangle, 
  Clock, 
  RefreshCw, 
  Cpu, 
  HardDrive, 
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const StatusBadge = ({ status }) => {
  const normalizedStatus = String(status).toLowerCase();
  
  if (['connected', 'healthy', 'active', 'running', 'complete', 'enabled', 'ready', 'ok'].includes(normalizedStatus)) {
    return (
      <span className="tw-inline-flex tw-items-center tw-px-2.5 tw-py-0.5 tw-rounded-full tw-text-xs tw-font-medium tw-bg-green-100 tw-text-green-800 tw-border tw-border-green-200">
        <CheckCircle2 className="tw-w-3 tw-h-3 tw-mr-1" />
        {status}
      </span>
    );
  }
  
  if (['degraded', 'warning', 'pending', 'initializing'].includes(normalizedStatus)) {
    return (
      <span className="tw-inline-flex tw-items-center tw-px-2.5 tw-py-0.5 tw-rounded-full tw-text-xs tw-font-medium tw-bg-yellow-100 tw-text-yellow-800 tw-border tw-border-yellow-200">
        <AlertTriangle className="tw-w-3 tw-h-3 tw-mr-1" />
        {status}
      </span>
    );
  }
  
  return (
    <span className="tw-inline-flex tw-items-center tw-px-2.5 tw-py-0.5 tw-rounded-full tw-text-xs tw-font-medium tw-bg-red-100 tw-text-red-800 tw-border tw-border-red-200">
      <XCircle className="tw-w-3 tw-h-3 tw-mr-1" />
      {status || 'Error'}
    </span>
  );
};

const ResourceBar = ({ label, value, unit = '%', icon: Icon }) => {
  const percentage = Math.min(Number(value) || 0, 100);
  const colorClass = percentage > 90 ? 'tw-bg-red-500' : percentage > 70 ? 'tw-bg-yellow-500' : 'tw-bg-blue-500';
  
  return (
    <div className="tw-mb-4">
      <div className="tw-flex tw-justify-between tw-items-center tw-mb-1">
        <div className="tw-flex tw-items-center tw-text-sm tw-font-medium tw-text-gray-600">
          {Icon && <Icon className="tw-w-4 tw-h-4 tw-mr-2" />}
          {label}
        </div>
        <span className="tw-text-xs tw-font-bold tw-text-gray-900">{value}{unit}</span>
      </div>
      <div className="tw-w-full tw-bg-gray-200 tw-rounded-full tw-h-2 tw-overflow-hidden">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          className={`tw-h-full ${colorClass}`}
        />
      </div>
    </div>
  );
};

const MetricRow = ({ label, value, subValue }) => (
  <div className="tw-flex tw-justify-between tw-py-2 tw-border-b tw-border-gray-50 last:tw-border-0 hover:tw-bg-gray-50 tw-px-1 tw-rounded tw-transition-colors tw-duration-150">
    <span className="tw-text-sm tw-text-gray-500">{label}</span>
    <div className="tw-text-right">
      <div className="tw-text-sm tw-font-semibold tw-text-gray-900">{value}</div>
      {subValue && <div className="tw-text-[10px] tw-text-gray-400">{subValue}</div>}
    </div>
  </div>
);

const TaskCard = ({ title, status, message, details, icon: Icon }) => {
  const getStatusColor = (s) => {
    const norm = String(s).toLowerCase();
    if (['complete', 'running', 'success'].includes(norm)) return 'tw-bg-green-500';
    if (['pending', 'warning', 'waiting'].includes(norm)) return 'tw-bg-yellow-500';
    return 'tw-bg-red-500';
  };

  return (
    <div className="tw-bg-gray-50 tw-rounded-xl tw-p-4 tw-border tw-border-gray-100 tw-relative tw-overflow-hidden">
      <div className="tw-flex tw-justify-between tw-items-start tw-mb-3">
        <div className="tw-flex tw-items-center tw-gap-3">
          <div className="tw-p-2 tw-bg-white tw-rounded-lg tw-shadow-sm">
            <Icon className="tw-w-4 tw-h-4 tw-text-gray-600" />
          </div>
          <div>
            <h4 className="tw-text-xs tw-font-black tw-text-gray-400 tw-uppercase tw-tracking-widest">{title}</h4>
            <div className="tw-text-sm tw-font-bold tw-text-gray-900">{message}</div>
          </div>
        </div>
        <StatusBadge status={status} />
      </div>
      
      {details && (
        <div className="tw-mt-2 tw-text-[10px] tw-font-medium tw-text-gray-500 tw-bg-white/50 tw-p-2 tw-rounded-lg">
          {details}
        </div>
      )}
      
      <div className={`tw-absolute tw-bottom-0 tw-left-0 tw-h-1 tw-transition-all tw-duration-1000 ${getStatusColor(status)}`} style={{ width: '100%' }}></div>
    </div>
  );
};

const SystemHealthDashboard = () => {
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/system/status`);
      if (!response.ok) throw new Error('System status unavailable');
      const data = await response.json();
      setStatusData(data);
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const statusInterval = setInterval(fetchData, 30000);
    return () => clearInterval(statusInterval);
  }, []);

  const stats = useMemo(() => {
    if (!statusData) return null;
    return {
      health: statusData.health_status,
      ws: statusData.health?.websocket,
      db: statusData.health?.database,
      redis: statusData.health?.redis,
      scheduler: statusData.health?.scheduler,
      automation: statusData.health?.automation
    };
  }, [statusData]);

  if (error) {
    return (
      <div className="tw-p-6 tw-bg-red-50 tw-rounded-xl tw-border tw-border-red-200">
        <div className="tw-flex tw-items-center tw-text-red-800 tw-mb-4">
          <AlertCircle className="tw-w-6 tw-h-6 tw-mr-2" />
          <h2 className="tw-text-lg tw-font-bold">System Health Monitoring Offline</h2>
        </div>
        <p className="tw-text-red-600 tw-mb-4 tw-font-medium">{error}</p>
        <button 
          onClick={fetchData}
          className="tw-bg-white tw-border tw-border-red-300 tw-text-red-700 tw-px-4 tw-py-2 tw-rounded-lg tw-font-bold tw-shadow-sm hover:tw-bg-red-50 tw-transition-colors"
        >
          Try Reconnecting
        </button>
      </div>
    );
  }

  if (!statusData && loading) {
    return (
      <div className="tw-flex tw-flex-col tw-items-center tw-justify-center tw-py-20">
        <div className="tw-w-12 tw-h-12 tw-border-4 tw-border-blue-500 tw-border-t-transparent tw-rounded-full tw-animate-spin tw-mb-4 tw-shadow-lg tw-shadow-blue-100"></div>
        <p className="tw-text-gray-500 tw-font-medium tw-animate-pulse">Scanning system components...</p>
      </div>
    );
  }

  const { business_logic, live_operations, infrastructure, errors } = statusData;

  return (
    <div className="tw-space-y-6">
      {/* Top Status Bar */}
      <div className="tw-bg-white tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100 tw-p-4 md:tw-p-6 tw-overflow-hidden tw-relative">
        <div className="tw-flex tw-flex-wrap tw-items-center tw-justify-between tw-gap-4 tw-relative tw-z-10">
          <div className="tw-flex tw-items-center tw-gap-4">
            <div className={`tw-p-3 tw-rounded-2xl ${stats?.health === 'healthy' ? 'tw-bg-green-50 tw-text-green-600' : 'tw-bg-red-50 tw-text-red-600 tw-shadow-inner'}`}>
              <Activity className="tw-w-8 tw-h-8" />
            </div>
            <div>
              <h2 className="tw-text-xl tw-font-bold tw-text-gray-900 tw-flex tw-items-center tw-gap-2">
                System Status: 
                <span className={stats?.health === 'healthy' ? 'tw-text-green-600 tw-uppercase tw-tracking-tight' : 'tw-text-red-600 tw-uppercase tw-tracking-tight tw-font-black tw-animate-pulse'}>
                  {stats?.health || 'UNKNOWN'}
                </span>
              </h2>
              <p className="tw-text-sm tw-text-gray-500 tw-flex tw-items-center tw-mt-0.5">
                <Clock className="tw-w-3.5 tw-h-3.5 tw-mr-1 tw-text-gray-400" />
                Updated {lastRefresh?.toLocaleTimeString()}
              </p>
            </div>
          </div>
          <div className="tw-flex tw-flex-wrap tw-gap-2">
            <StatusBadge status={stats?.ws} />
            <StatusBadge status={stats?.db} />
            <StatusBadge status={stats?.redis} />
            <StatusBadge status={stats?.scheduler} />
            <button 
              onClick={fetchData} 
              disabled={loading}
              className="tw-ml-2 tw-p-2 hover:tw-bg-gray-100 tw-rounded-xl tw-transition-all active:tw-scale-95 tw-duration-200"
            >
              <RefreshCw className={`tw-w-5 tw-h-5 tw-text-blue-500 ${loading ? 'tw-animate-spin' : ''}`} />
            </button>
          </div>
        </div>
        
        {/* Animated Background Pulse */}
        <div className={`tw-absolute tw-top-0 tw-right-0 tw-w-64 tw-h-64 tw--mr-32 tw--mt-32 tw-rounded-full tw-opacity-5 tw-blur-3xl ${stats?.health === 'healthy' ? 'tw-bg-green-500' : 'tw-bg-red-500'}`}></div>
      </div>

      {/* Critical Alerts */}
      <AnimatePresence>
        {errors && errors.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="tw-bg-red-50 tw-border-l-4 tw-border-red-500 tw-p-4 tw-rounded-r-xl tw-shadow-md tw-border tw-border-red-100"
          >
            <div className="tw-flex tw-items-start">
              <div className="tw-flex-shrink-0">
                <AlertTriangle className="tw-h-5 tw-w-5 tw-text-red-500" />
              </div>
              <div className="tw-ml-3 tw-flex-1">
                <h3 className="tw-text-sm tw-font-bold tw-text-red-800 tw-uppercase tw-tracking-wide">System Abnormalities Detected</h3>
                <div className="tw-mt-2 tw-text-sm tw-text-red-700 tw-space-y-1">
                  {errors.map((err, idx) => (
                    <div key={idx} className="tw-flex tw-items-center tw-gap-2 tw-bg-white/50 tw-px-2 tw-py-1 tw-rounded tw-border tw-border-red-100 tw-shadow-sm">
                      <span className="tw-font-black tw-text-[10px] tw-bg-red-100 tw-px-1.5 tw-py-0.5 tw-rounded">{err.component}</span>
                      <span className="tw-font-medium tw-text-xs tw-truncate">{err.error}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="tw-grid tw-grid-cols-1 md:tw-grid-cols-12 tw-gap-6">
        
        {/* Infrastructure & Resources */}
        <div className="md:tw-col-span-4 tw-space-y-6">
          <div className="tw-bg-white tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100 tw-p-5 tw-overflow-hidden tw-group hover:tw-shadow-md tw-transition-shadow">
            <h3 className="tw-text-base tw-font-bold tw-text-gray-900 tw-mb-4 tw-flex tw-items-center group-hover:tw-text-blue-600 tw-transition-colors">
              <div className="tw-p-1.5 tw-bg-blue-50 tw-text-blue-600 tw-rounded-lg tw-mr-2">
                <Database className="tw-w-4 tw-h-4" />
              </div>
              Infrastructure
            </h3>
            <div className="tw-space-y-1">
              <MetricRow label="Database Status" value={infrastructure?.database?.status?.toUpperCase()} subValue={`${infrastructure?.database?.latency_ms || 0}ms latency`} />
              <MetricRow label="Redis Engine" value={infrastructure?.redis?.status?.toUpperCase()} subValue={`${infrastructure?.redis?.latency_ms || 0}ms latency`} />
              <MetricRow label="WebSocket" value={stats?.ws?.toUpperCase()} subValue={live_operations?.feed_status?.connected ? 'Live Data Flowing' : 'No Connection'} />
              <MetricRow label="Market Mode" value={statusData.environment?.toUpperCase()} />
            </div>
            
            <div className="tw-mt-6 tw-pt-4 tw-border-t tw-border-gray-100">
              <h4 className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-widest tw-mb-4 tw-flex tw-items-center">
                <Zap className="tw-w-3 tw-h-3 tw-mr-1" /> Performance Loads
              </h4>
              <ResourceBar label="System CPU" value={infrastructure?.resources?.cpu_percent} icon={Cpu} />
              <ResourceBar label="RAM Usage" value={infrastructure?.resources?.memory?.percent} icon={Server} />
              <ResourceBar label="Disk Space" value={infrastructure?.resources?.disk?.percent} icon={HardDrive} />
            </div>
          </div>
        </div>

        {/* Business Logic & Live Operations */}
        <div className="md:tw-col-span-4 tw-space-y-6">
          <div className="tw-bg-white tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100 tw-p-5 tw-group hover:tw-shadow-md tw-transition-shadow">
            <h3 className="tw-text-base tw-font-bold tw-text-gray-900 tw-mb-4 tw-flex tw-items-center group-hover:tw-text-purple-600 tw-transition-colors">
              <div className="tw-p-1.5 tw-bg-purple-50 tw-text-purple-600 tw-rounded-lg tw-mr-2">
                <Zap className="tw-w-4 tw-h-4" />
              </div>
              Core Status
            </h3>
            
            <div className="tw-space-y-4">
              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <MetricRow label="Analytics" value={live_operations?.analytics_engine?.is_ready ? 'READY' : 'INIT'} subValue={`${live_operations?.analytics_engine?.total_stocks_with_data || 0} stocks live`} />
                <MetricRow label="Instruments" value={live_operations?.instrument_service?.total_instruments || 0} subValue={`Refreshed: ${live_operations?.instrument_service?.last_refresh?.split('T')[1]?.split('.')[0] || 'Never'}`} />
                <MetricRow label="Scheduler" value={business_logic?.market_schedule?.is_running ? 'RUNNING' : 'STOPPED'} />
              </div>

              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Broker Auth</span>
                  <StatusBadge status={business_logic?.token_status?.status} />
                </div>
                <div className="tw-flex tw-gap-4 tw-mt-1">
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase">Valid: <span className="tw-text-green-600 tw-font-bold">{business_logic?.token_status?.active_tokens}</span></div>
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase">Expired: <span className="tw-text-red-600 tw-font-bold">{business_logic?.token_status?.expired_count}</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Daily Operations Checklist */}
        <div className="md:tw-col-span-4 tw-space-y-6">
          <div className="tw-bg-white tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100 tw-p-5 hover:tw-shadow-md tw-transition-shadow">
            <h3 className="tw-text-base tw-font-bold tw-text-gray-900 tw-mb-4 tw-flex tw-items-center">
              <div className="tw-p-1.5 tw-bg-green-50 tw-text-green-600 tw-rounded-lg tw-mr-2">
                <CheckCircle2 className="tw-w-4 tw-h-4" />
              </div>
              Daily Operational Integrity
            </h3>
            
            <div className="tw-space-y-3">
              <TaskCard 
                title="Token Refresh" 
                status={business_logic?.daily_tasks?.tasks?.token_refresh?.status}
                message={business_logic?.daily_tasks?.tasks?.token_refresh?.message}
                details={business_logic?.daily_tasks?.tasks?.token_refresh?.error}
                icon={ShieldCheck}
              />
              <TaskCard 
                title="Stock Selection" 
                status={business_logic?.daily_tasks?.tasks?.stock_selection?.status}
                message={business_logic?.daily_tasks?.tasks?.stock_selection?.message}
                icon={Filter}
              />
              <TaskCard 
                title="Options Enhancement" 
                status={business_logic?.daily_tasks?.tasks?.options_enhancement?.status}
                message={business_logic?.daily_tasks?.tasks?.options_enhancement?.message}
                icon={Zap}
              />
              <TaskCard 
                title="Auto Trading" 
                status={business_logic?.daily_tasks?.tasks?.auto_trading?.status}
                message={business_logic?.daily_tasks?.tasks?.auto_trading?.message}
                details={business_logic?.daily_tasks?.tasks?.auto_trading?.malformed_count > 0 ? 
                  `⚠️ Found ${business_logic.daily_tasks.tasks.auto_trading.malformed_count} trades with missing fields` : null}
                icon={Activity}
              />
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default SystemHealthDashboard;
