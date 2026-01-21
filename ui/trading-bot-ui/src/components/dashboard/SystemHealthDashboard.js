import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Typography,
  Chip,
  LinearProgress,
  Card,
  CardContent,
  Stack,
  IconButton,
  Alert,
  AlertTitle,
  Button
} from '@mui/material';
import {
  CheckCircleRounded,
  WarningRounded,
  ErrorRounded,
  RefreshRounded,
  StorageRounded,
  MemoryRounded,
  SettingsInputComponentRounded,
  CloudQueueRounded
} from '@mui/icons-material';

const StatusChip = ({ status, label }) => {
  let color = 'default';
  let icon = null;

  const normalizedStatus = String(status).toLowerCase();

  if (['connected', 'healthy', 'active', 'running', 'complete', 'enabled', 'ready'].includes(normalizedStatus)) {
    color = 'success';
    icon = <CheckCircleRounded fontSize="small" />;
  } else if (['degraded', 'warning', 'pending', 'initializing'].includes(normalizedStatus)) {
    color = 'warning';
    icon = <WarningRounded fontSize="small" />;
  } else if (['disconnected', 'error', 'failed', 'critical', 'disabled', 'inactive', 'stopped'].includes(normalizedStatus)) {
    color = 'error';
    icon = <ErrorRounded fontSize="small" />;
  }

  return (
    <Chip
      icon={icon}
      label={label || status || 'Unknown'}
      color={color}
      size="small"
      variant="outlined"
      sx={{ fontWeight: 600, textTransform: 'uppercase' }}
    />
  );
};

const ResourceGauge = ({ label, value, unit = '%', color = 'primary' }) => (
  <Box sx={{ mb: 2 }}>
    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
      <Typography variant="caption" fontWeight="600" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="caption" fontWeight="700">
        {value}{unit}
      </Typography>
    </Box>
    <LinearProgress 
      variant="determinate" 
      value={Math.min(Number(value) || 0, 100)} 
      color={value > 90 ? 'error' : value > 70 ? 'warning' : color}
      sx={{ height: 6, borderRadius: 3 }}
    />
  </Box>
);

const DetailItem = ({ label, value }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5, borderBottom: '1px dashed rgba(0,0,0,0.1)' }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2" fontWeight="500">{value !== null && value !== undefined ? String(value) : 'N/A'}</Typography>
  </Box>
);

const SystemHealthDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/system/status`);
      if (!response.ok) throw new Error('Failed to fetch status');
      const result = await response.json();
      setData(result);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error("Health check fetch error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        <AlertTitle>System Check Failed</AlertTitle>
        {error}
        <Box sx={{ mt: 1 }}>
          <Button size="small" variant="outlined" onClick={fetchData}>Retry</Button>
        </Box>
      </Alert>
    );
  }

  if (!data && loading) return <LinearProgress />;
  if (!data) return null;

  const { health_status, business_logic, live_operations, infrastructure, errors } = data;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight="700" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            System Health Monitor
            <StatusChip status={health_status} />
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Last Updated: {lastUpdated?.toLocaleTimeString()}
          </Typography>
        </Box>
        <IconButton onClick={fetchData} disabled={loading} color="primary">
          <RefreshRounded />
        </IconButton>
      </Box>

      {/* Errors Section */}
      {errors && errors.length > 0 && (
        <Alert severity="error" sx={{ mb: 3 }} icon={<ErrorRounded />}>
          <AlertTitle>System Issues Detected</AlertTitle>
          <Stack spacing={0.5}>
            {errors.map((err, idx) => (
              <Typography key={idx} variant="body2">
                • <strong>{err.component}:</strong> {err.error}
              </Typography>
            ))}
          </Stack>
        </Alert>
      )}

      <Grid container spacing={3}>
        
        {/* Infrastructure Column */}
        <Grid item xs={12} md={4}>
          <Card elevation={2} sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <StorageRounded color="primary" /> Infrastructure
              </Typography>
              
              <Box sx={{ mb: 3 }}>
                <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                  <StatusChip status={infrastructure?.database?.status} label="DB" />
                  <StatusChip status={infrastructure?.redis?.status} label="REDIS" />
                </Stack>
                
                <DetailItem label="DB Latency" value={`${infrastructure?.database?.latency_ms || 0} ms`} />
                <DetailItem label="Redis Latency" value={`${infrastructure?.redis?.latency_ms || 0} ms`} />
              </Box>

              <Typography variant="subtitle2" gutterBottom sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <MemoryRounded fontSize="small" color="action" /> Resources
              </Typography>
              
              <ResourceGauge label="CPU Usage" value={infrastructure?.resources?.cpu_percent} />
              <ResourceGauge label="Memory" value={infrastructure?.resources?.memory?.percent} />
              <ResourceGauge label="Disk Space" value={infrastructure?.resources?.disk?.percent} />
            </CardContent>
          </Card>
        </Grid>

        {/* Business Logic Column */}
        <Grid item xs={12} md={4}>
          <Card elevation={2} sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <SettingsInputComponentRounded color="secondary" /> Business Logic
              </Typography>

              {/* Stock Selection */}
              <Box sx={{ mb: 3, p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold">Stock Selection</Typography>
                  <StatusChip status={business_logic?.stock_selection?.status} />
                </Box>
                <DetailItem label="Phase" value={business_logic?.stock_selection?.phase} />
                <DetailItem label="Selected Count" value={business_logic?.stock_selection?.selected_count} />
                <DetailItem label="Sentiment" value={business_logic?.stock_selection?.sentiment?.toUpperCase()} />
              </Box>

              {/* Tokens */}
              <Box sx={{ mb: 3, p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold">Broker Tokens</Typography>
                  <StatusChip status={business_logic?.token_status?.status} />
                </Box>
                <DetailItem label="Active" value={business_logic?.token_status?.active_tokens} />
                <DetailItem label="Expired" value={business_logic?.token_status?.expired_count} />
                <DetailItem label="Critical" value={business_logic?.token_status?.critical_count} />
              </Box>

              {/* Scheduler */}
              <Box sx={{ p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold">Scheduler</Typography>
                  <StatusChip status={business_logic?.market_schedule?.is_running ? 'running' : 'stopped'} />
                </Box>
                <DetailItem label="Trading Session" value={business_logic?.market_schedule?.trading_sessions_active ? 'Active' : 'Inactive'} />
              </Box>

            </CardContent>
          </Card>
        </Grid>

        {/* Live Operations Column */}
        <Grid item xs={12} md={4}>
          <Card elevation={2} sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <CloudQueueRounded color="info" /> Live Operations
              </Typography>

              {/* Live Feed */}
              <Box sx={{ mb: 3, p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold">Live Feed</Typography>
                  <StatusChip status={live_operations?.feed_status?.connected ? 'connected' : 'disconnected'} />
                </Box>
                <DetailItem label="Subscriptions" value={live_operations?.feed_status?.subscribed_count} />
                <DetailItem label="Uptime" value={`${Math.floor((live_operations?.feed_status?.connection_uptime || 0) / 60)} min`} />
                <DetailItem label="Mode" value={live_operations?.feed_status?.mode} />
              </Box>

              {/* Instruments */}
              <Box sx={{ mb: 3, p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold">Instruments</Typography>
                  <StatusChip status={live_operations?.instrument_service?.initialized ? 'ready' : 'initializing'} />
                </Box>
                <DetailItem label="Total Loaded" value={live_operations?.instrument_service?.total_instruments} />
              </Box>

              {/* Strategy */}
              <Box sx={{ p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight="bold">Strategy Engine</Typography>
                  <StatusChip status={live_operations?.strategy_status?.system_state} />
                </Box>
                <DetailItem label="Active Sessions" value={live_operations?.strategy_status?.active_sessions} />
                <DetailItem label="Trades Today" value={live_operations?.strategy_status?.system_metrics?.total_trades_today || 0} />
              </Box>

            </CardContent>
          </Card>
        </Grid>

      </Grid>
    </Box>
  );
};

export default SystemHealthDashboard;
