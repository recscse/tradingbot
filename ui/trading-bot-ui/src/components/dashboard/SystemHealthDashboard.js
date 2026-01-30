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
  Terminal,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronRight,
  ChevronDown
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

const LogItem = ({ log }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const levelColors = {
    'INFO': 'tw-text-blue-600',
    'WARNING': 'tw-text-yellow-600',
    'ERROR': 'tw-text-red-600',
    'CRITICAL': 'tw-text-red-800 tw-font-bold tw-bg-red-50'
  };

  const Icon = log.level === 'ERROR' || log.level === 'CRITICAL' ? AlertCircle : 
               log.level === 'WARNING' ? AlertTriangle : Terminal;

  return (
    <div className={`tw-border-b tw-border-gray-100 last:tw-border-0 tw-transition-colors tw-duration-150 ${isExpanded ? 'tw-bg-gray-50' : ''}`}>
      <div 
        className="tw-flex tw-items-center tw-p-3 tw-cursor-pointer hover:tw-bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="tw-mr-3 tw-mt-0.5">
          <Icon className={`tw-w-4 tw-h-4 ${levelColors[log.level] || 'tw-text-gray-400'}`} />
        </div>
        <div className="tw-flex-1 tw-min-w-0">
          <div className="tw-flex tw-items-center tw-justify-between">
            <span className={`tw-text-[10px] tw-font-bold tw-uppercase tw-tracking-wider ${levelColors[log.level] || 'tw-text-gray-500'}`}>
              {log.level}
            </span>
            <span className="tw-text-[10px] tw-text-gray-400 tw-flex tw-items-center">
              <Clock className="tw-w-3 tw-h-3 tw-mr-1" />
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="tw-text-sm tw-text-gray-800 tw-truncate tw-font-medium">
            {log.message}
          </div>
          <div className="tw-text-[10px] tw-text-gray-500 tw-mt-0.5 tw-flex tw-items-center">
            <span className="tw-bg-gray-100 tw-px-1.5 tw-py-0.5 tw-rounded tw-mr-2">{log.component}</span>
            {log.latency_ms > 0 && <span className="tw-text-blue-500 tw-font-medium">{log.latency_ms}ms</span>}
          </div>
        </div>
        <div className="tw-ml-2">
          {isExpanded ? <ChevronDown className="tw-w-4 tw-h-4 tw-text-gray-400" /> : <ChevronRight className="tw-w-4 tw-h-4 tw-text-gray-400" />}
        </div>
      </div>
      <AnimatePresence>
        {isExpanded && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="tw-overflow-hidden tw-bg-gray-900 tw-p-4"
          >
            <pre className="tw-text-xs tw-text-green-400 tw-overflow-x-auto tw-font-mono tw-whitespace-pre-wrap tw-leading-relaxed">
              {JSON.stringify(log.additional_data || { message: log.message }, null, 2)}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const SystemHealthDashboard = () => {
  const [statusData, setStatusData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [logLevelFilter, setLogLevelFilter] = useState('');

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

  const fetchLogs = async (level = '') => {
    setLogsLoading(true);
    try {
      const url = new URL(`${process.env.REACT_APP_API_URL}/api/system/logs`);
      url.searchParams.append('limit', '50');
      if (level) url.searchParams.append('level', level);
      
      const response = await fetch(url.toString());
      if (!response.ok) throw new Error('Logs fetch failed');
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      console.error("Log fetch error:", err);
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    fetchLogs();
    const statusInterval = setInterval(fetchData, 30000);
    const logsInterval = setInterval(() => fetchLogs(logLevelFilter), 10000);
    
    return () => {
      clearInterval(statusInterval);
      clearInterval(logsInterval);
    };
  }, [logLevelFilter]);

  const handleLogLevelChange = (level) => {
    setLogLevelFilter(level);
    fetchLogs(level);
  };

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

          <div className="tw-bg-gradient-to-br tw-from-indigo-600 tw-to-blue-700 tw-rounded-2xl tw-shadow-lg tw-p-5 tw-text-white tw-overflow-hidden tw-relative tw-group">
            <div className="tw-relative tw-z-10">
              <h3 className="tw-text-base tw-font-bold tw-mb-4 tw-flex tw-items-center tw-opacity-90">
                <ShieldCheck className="tw-w-5 tw-h-5 tw-mr-2" />
                Security & Health
              </h3>
              <div className="tw-space-y-3">
                <div className="tw-flex tw-justify-between tw-items-center tw-bg-white/10 tw-p-2 tw-rounded-lg tw-backdrop-blur-sm">
                  <span className="tw-text-xs tw-font-medium tw-opacity-80 tw-uppercase tw-tracking-wide">Automation</span>
                  <span className="tw-text-xs tw-font-bold">{stats?.automation?.toUpperCase() || 'OFF'}</span>
                </div>
                <div className="tw-flex tw-justify-between tw-items-center tw-bg-white/10 tw-p-2 tw-rounded-lg tw-backdrop-blur-sm">
                  <span className="tw-text-xs tw-font-medium tw-opacity-80 tw-uppercase tw-tracking-wide">Environment</span>
                  <span className="tw-text-xs tw-font-bold tw-font-mono">{statusData.environment}</span>
                </div>
                <div className="tw-flex tw-justify-between tw-items-center tw-bg-white/10 tw-p-2 tw-rounded-lg tw-backdrop-blur-sm">
                  <span className="tw-text-xs tw-font-medium tw-opacity-80 tw-uppercase tw-tracking-wide">Latency Cap</span>
                  <span className="tw-text-xs tw-font-bold">500ms</span>
                </div>
              </div>
            </div>
            <Activity className="tw-absolute tw--bottom-6 tw--right-6 tw-w-24 tw-h-24 tw-opacity-10 tw-rotate-12 group-hover:tw-scale-110 tw-transition-transform tw-duration-500" />
          </div>
        </div>

        {/* Business Logic & Live Operations */}
        <div className="md:tw-col-span-4 tw-space-y-6">
          <div className="tw-bg-white tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100 tw-p-5 tw-group hover:tw-shadow-md tw-transition-shadow">
            <h3 className="tw-text-base tw-font-bold tw-text-gray-900 tw-mb-4 tw-flex tw-items-center group-hover:tw-text-purple-600 tw-transition-colors">
              <div className="tw-p-1.5 tw-bg-purple-50 tw-text-purple-600 tw-rounded-lg tw-mr-2">
                <Zap className="tw-w-4 tw-h-4" />
              </div>
              Business Engine
            </h3>
            
            <div className="tw-space-y-4">
              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100 tw-relative group/card">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Stock Selection</span>
                  <StatusBadge status={business_logic?.stock_selection?.status} />
                </div>
                <div className="tw-grid tw-grid-cols-2 tw-gap-2 tw-mt-1">
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase">Selected: <span className="tw-text-gray-900 tw-font-bold tw-tracking-tight tw-text-sm tw-ml-1">{business_logic?.stock_selection?.selected_count}</span></div>
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase tw-text-right">Sentiment: <span className="tw-text-purple-600 tw-font-bold tw-text-xs tw-ml-1 tw-uppercase">{business_logic?.stock_selection?.sentiment}</span></div>
                </div>
                {business_logic?.stock_selection?.last_error && (
                  <div className="tw-mt-2 tw-text-[9px] tw-text-red-500 tw-bg-red-50 tw-p-1 tw-rounded tw-border tw-border-red-100">
                    <span className="tw-font-bold tw-uppercase tw-mr-1">Error:</span>
                    {business_logic.stock_selection.last_error}
                  </div>
                )}
                <div className="tw-mt-2 tw-h-1 tw-w-full tw-bg-gray-200 tw-rounded-full tw-overflow-hidden">
                  <div className="tw-h-full tw-bg-purple-500 tw-w-full tw-opacity-30"></div>
                </div>
              </div>

              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Automation Service</span>
                  <StatusBadge status={business_logic?.automation?.status} />
                </div>
                <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase tw-mb-1">
                  Last Sync: <span className="tw-text-gray-900 tw-font-bold">{business_logic?.automation?.last_run?.split('T')[1]?.split('.')[0] || 'Never'}</span>
                </div>
                <div className="tw-text-[10px] tw-text-gray-600">
                  {business_logic?.automation?.message || 'Ready for scheduled refresh'}
                </div>
                {business_logic?.automation?.error && (
                  <div className="tw-mt-2 tw-text-[9px] tw-text-red-500 tw-bg-red-50 tw-p-1 tw-rounded tw-border tw-border-red-100">
                    <span className="tw-font-bold tw-uppercase tw-mr-1">Failure:</span>
                    {business_logic.automation.error}
                  </div>
                )}
              </div>

              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Broker Auth Tokens</span>
                  <StatusBadge status={business_logic?.token_status?.status} />
                </div>
                <div className="tw-flex tw-gap-4 tw-mt-1">
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase tw-font-medium">Valid: <span className="tw-text-green-600 tw-font-bold tw-ml-1">{business_logic?.token_status?.active_tokens}</span></div>
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase tw-font-medium">Expired: <span className="tw-text-red-600 tw-font-bold tw-ml-1">{business_logic?.token_status?.expired_count}</span></div>
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase tw-font-medium">Auto-Refresh: <span className="tw-text-blue-600 tw-font-bold tw-ml-1">{business_logic?.automation?.token_refresh_active ? 'ON' : 'OFF'}</span></div>
                </div>
              </div>

              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Option Service</span>
                  <StatusBadge status={business_logic?.option_service?.status} />
                </div>
                <MetricRow label="API Calls" value={business_logic?.option_service?.api_calls || 0} subValue={`Cache Size: ${business_logic?.option_service?.cache_size || 0}`} />
                {business_logic?.option_service?.last_error && (
                  <div className="tw-mt-2 tw-text-[9px] tw-text-red-500 tw-bg-red-50 tw-p-1 tw-rounded tw-border tw-border-red-100">
                    {business_logic.option_service.last_error}
                  </div>
                )}
              </div>

              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Market Scheduler</span>
                  <StatusBadge status={business_logic?.market_schedule?.is_running ? 'running' : 'stopped'} />
                </div>
                <MetricRow label="Trading Sessions" value={business_logic?.market_schedule?.trading_sessions_active ? 'ACTIVE' : 'INACTIVE'} />
                <MetricRow label="Task Errors" value={Object.keys(business_logic?.market_schedule?.task_errors || {}).length} />
              </div>

              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Trade Preparation</span>
                  <StatusBadge status={business_logic?.trade_prep?.status || 'active'} />
                </div>
                <div className="tw-grid tw-grid-cols-2 tw-gap-2 tw-mt-1">
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase">Total Prep: <span className="tw-text-gray-900 font-bold ml-1">{business_logic?.trade_prep?.stats?.total_preparations || 0}</span></div>
                  <div className="tw-text-[10px] tw-text-gray-500 tw-uppercase text-right">Success: <span className="tw-text-green-600 font-bold ml-1">{business_logic?.trade_prep?.stats?.successful_preparations || 0}</span></div>
                </div>
                {business_logic?.trade_prep?.last_error && (
                  <div className="tw-mt-2 tw-text-[9px] tw-text-red-500 tw-bg-red-50 tw-p-1 tw-rounded tw-truncate">
                    {business_logic.trade_prep.last_error}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="tw-bg-white tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100 tw-p-5 tw-group hover:tw-shadow-md tw-transition-shadow">
            <h3 className="tw-text-base tw-font-bold tw-text-gray-900 tw-mb-4 tw-flex tw-items-center group-hover:tw-text-cyan-600 tw-transition-colors">
              <div className="tw-p-1.5 tw-bg-cyan-50 tw-text-cyan-600 tw-rounded-lg tw-mr-2">
                <Activity className="tw-w-4 tw-h-4" />
              </div>
              Live Operations
            </h3>
            <div className="tw-space-y-3">
              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100 tw-mb-3">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Analytics Engine</span>
                  <StatusBadge status={live_operations?.analytics_engine?.is_ready ? 'ready' : 'initializing'} />
                </div>
                <MetricRow label="Instruments" value={live_operations?.analytics_engine?.total_instruments || 0} subValue={`${live_operations?.analytics_engine?.total_stocks_with_data || 0} with live data`} />
                <MetricRow label="Latency" value={`${Math.round(live_operations?.analytics_engine?.calculation_latency_ms || 0)}ms`} />
              </div>

              <div className="tw-bg-gray-50 tw-rounded-xl tw-p-3 tw-border tw-border-gray-100">
                <div className="tw-flex tw-justify-between tw-items-center tw-mb-2">
                  <span className="tw-text-xs tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-tight">Instrument Service</span>
                  <StatusBadge status={live_operations?.instrument_service?.status || (live_operations?.instrument_service?.initialized ? 'healthy' : 'pending')} />
                </div>
                <MetricRow label="Total Loaded" value={live_operations?.instrument_service?.total_instruments || 0} subValue={`Refreshed: ${live_operations?.instrument_service?.last_refresh?.split('T')[1]?.split('.')[0] || 'Never'}`} />
                {live_operations?.instrument_service?.last_error && (
                  <div className="tw-mt-2 tw-text-[9px] tw-text-red-500 tw-bg-red-50 tw-p-1 tw-rounded tw-border tw-border-red-100">
                    {live_operations.instrument_service.last_error}
                  </div>
                )}
              </div>

              <div className="tw-flex tw-items-center tw-justify-between tw-p-2 tw-rounded-lg tw-bg-gray-50 tw-border tw-border-gray-100 tw-shadow-inner">
                <span className="tw-text-xs tw-font-semibold tw-text-gray-500 tw-uppercase tw-tracking-tight">Live Feed Uptime</span>
                <span className="tw-text-sm tw-font-black tw-text-gray-900 tw-font-mono tw-tracking-tighter">{Math.floor((live_operations?.feed_status?.connection_uptime || 0) / 60)}m {Math.floor((live_operations?.feed_status?.connection_uptime || 0) % 60)}s</span>
              </div>
              <MetricRow label="Active Connections" value={live_operations?.feed_status?.subscribed_count} />
              <MetricRow label="Auto-Trade Feed" value={live_operations?.feed_status?.feed_service?.is_running ? 'RUNNING' : 'STOPPED'} subValue={`${live_operations?.feed_status?.feed_service?.instruments_tracked || 0} instruments`} />
              <MetricRow label="Strategy State" value={live_operations?.strategy_status?.system_state} subValue={`${live_operations?.strategy_status?.active_sessions} active sessions`} />
              
              {live_operations?.feed_status?.last_error && (
                <div className="tw-mt-2 tw-text-[9px] tw-text-red-500 tw-bg-red-50 tw-p-1 tw-rounded tw-border tw-border-red-100">
                  <span className="tw-font-bold tw-uppercase tw-mr-1">Last Error:</span>
                  {live_operations.feed_status.last_error}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Live Logs Section */}
        <div className="md:tw-col-span-4 tw-h-full tw-min-h-[600px] md:tw-min-h-0 tw-flex tw-flex-col">
          <div className="tw-bg-white tw-rounded-2xl tw-shadow-sm tw-border tw-border-gray-100 tw-overflow-hidden tw-flex tw-flex-col tw-h-full hover:tw-shadow-md tw-transition-shadow">
            <div className="tw-p-5 tw-border-b tw-border-gray-100 tw-bg-gray-50/50 tw-flex tw-flex-col tw-gap-4">
              <div className="tw-flex tw-items-center tw-justify-between">
                <h3 className="tw-text-base tw-font-bold tw-text-gray-900 tw-flex tw-items-center">
                  <Terminal className="tw-w-5 tw-h-5 tw-mr-2 tw-text-gray-600" />
                  Live System Logs
                </h3>
                <div className="tw-flex tw-items-center tw-gap-2">
                  <span className={`tw-w-2 tw-h-2 tw-rounded-full ${logsLoading ? 'tw-bg-blue-500 tw-animate-pulse' : 'tw-bg-green-500'}`}></span>
                  <span className="tw-text-[10px] tw-font-bold tw-text-gray-400 tw-uppercase tw-tracking-wider">Live Polling</span>
                </div>
              </div>
              
              <div className="tw-flex tw-gap-2">
                <div className="tw-relative tw-flex-1">
                  <Filter className="tw-absolute tw-left-2.5 tw-top-2.5 tw-w-3.5 tw-h-3.5 tw-text-gray-400" />
                  <select 
                    value={logLevelFilter}
                    onChange={(e) => handleLogLevelChange(e.target.value)}
                    className="tw-w-full tw-pl-8 tw-pr-3 tw-py-1.5 tw-text-xs tw-border tw-border-gray-200 tw-rounded-lg tw-bg-white focus:tw-outline-none focus:tw-ring-2 focus:tw-ring-blue-500/20 tw-appearance-none tw-font-medium tw-text-gray-600 tw-shadow-sm"
                  >
                    <option value="">All Levels</option>
                    <option value="INFO">Info</option>
                    <option value="WARNING">Warning</option>
                    <option value="ERROR">Error</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
                <button 
                  onClick={() => fetchLogs(logLevelFilter)}
                  className="tw-p-1.5 tw-bg-white tw-border tw-border-gray-200 tw-rounded-lg hover:tw-bg-gray-50 active:tw-scale-95 tw-transition-all tw-shadow-sm"
                >
                  <RefreshCw className={`tw-w-4 tw-h-4 tw-text-gray-500 ${logsLoading ? 'tw-animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            <div className="tw-flex-1 tw-overflow-y-auto tw-max-h-[600px] tw-scrollbar-thin tw-scrollbar-thumb-gray-200">
              {logs.length > 0 ? (
                <div className="tw-divide-y tw-divide-gray-50">
                  {logs.map((log) => (
                    <LogItem key={log.id} log={log} />
                  ))}
                </div>
              ) : (
                <div className="tw-flex tw-flex-col tw-items-center tw-justify-center tw-h-full tw-py-20 tw-px-10 tw-text-center tw-opacity-50 tw-grayscale">
                  <Terminal className="tw-w-12 tw-h-12 tw-text-gray-300 tw-mb-4" />
                  <p className="tw-text-sm tw-font-medium tw-text-gray-500 tw-italic">Listening for system events...</p>
                </div>
              )}
            </div>
            
            <div className="tw-p-3 tw-bg-gray-50 tw-border-t tw-border-gray-100 tw-text-center">
              <button 
                onClick={() => fetchLogs(logLevelFilter)}
                className="tw-text-[10px] tw-font-bold tw-text-blue-600 hover:tw-text-blue-700 tw-uppercase tw-tracking-widest tw-flex tw-items-center tw-justify-center tw-mx-auto tw-transition-all active:tw-scale-95"
              >
                View Full Archive <ChevronRight className="tw-w-3 tw-h-3 tw-ml-1" />
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default SystemHealthDashboard;
