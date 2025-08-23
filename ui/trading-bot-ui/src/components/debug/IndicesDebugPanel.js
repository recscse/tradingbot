// components/debug/IndicesDebugPanel.js
/**
 * 🔍 Debug panel to show real-time indices data sources
 */

import React, { useEffect, useState } from 'react';
import { Box, Typography, Paper, Grid, Chip } from '@mui/material';
import useMarketStore from '../../store/marketStore';
import { useMarket } from '../../hooks/useUnifiedMarketData';

const IndicesDebugPanel = () => {
  const [debugInfo, setDebugInfo] = useState({});
  
  // Get data from different sources
  const allLivePrices = useMarketStore((state) => state.prices);
  const connectionStatus = useMarketStore((state) => state.connectionStatus);
  const updateCount = useMarketStore((state) => state.updateCount);
  const { indicesData, isConnected: hookConnected } = useMarket();
  
  // Filter for indices in Zustand store
  const indicesInZustand = React.useMemo(() => {
    const indexSymbols = ['NIFTY', 'SENSEX', 'BANKNIFTY', 'FINNIFTY'];
    const result = {};
    
    indexSymbols.forEach(symbol => {
      if (allLivePrices[symbol]) {
        result[symbol] = allLivePrices[symbol];
      }
    });
    
    return result;
  }, [allLivePrices]);
  
  // Get indices from analytics hook
  const indicesFromHook = React.useMemo(() => {
    return {
      major: indicesData?.major_indices || [],
      all: indicesData?.indices || []
    };
  }, [indicesData]);
  
  // Update debug info every second
  useEffect(() => {
    const interval = setInterval(() => {
      setDebugInfo({
        timestamp: new Date().toLocaleTimeString(),
        zustandCount: Object.keys(indicesInZustand).length,
        zustandUpdateCount: updateCount,
        zustandConnection: connectionStatus,
        hookConnection: hookConnected,
        majorIndicesCount: indicesFromHook.major.length,
        allIndicesCount: indicesFromHook.all.length
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [indicesInZustand, updateCount, connectionStatus, hookConnected, indicesFromHook]);
  
  return (
    <Box sx={{ p: 2, maxWidth: 800 }}>
      <Typography variant="h6" gutterBottom>
        🔍 Indices Real-Time Data Debug Panel
      </Typography>
      
      <Grid container spacing={2}>
        {/* Status Summary */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              📊 Status Summary ({debugInfo.timestamp})
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              <Chip 
                label={`Zustand: ${debugInfo.zustandConnection || 'unknown'}`}
                color={debugInfo.zustandConnection === 'connected' ? 'success' : 'error'}
                size="small"
              />
              <Chip 
                label={`Hook: ${debugInfo.hookConnection ? 'connected' : 'disconnected'}`}
                color={debugInfo.hookConnection ? 'success' : 'error'}
                size="small"
              />
              <Chip 
                label={`Updates: ${debugInfo.zustandUpdateCount || 0}`}
                color="info"
                size="small"
              />
            </Box>
          </Paper>
        </Grid>
        
        {/* Zustand Store Data */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              🚀 Zustand Store Indices ({debugInfo.zustandCount})
            </Typography>
            <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
              {Object.keys(indicesInZustand).length === 0 ? (
                <Typography color="error">❌ No indices found in Zustand store</Typography>
              ) : (
                Object.entries(indicesInZustand).map(([symbol, data]) => (
                  <Box key={symbol} sx={{ mb: 1, p: 1, bgcolor: 'background.default', borderRadius: 1 }}>
                    <Typography variant="body2" fontWeight="bold">
                      {symbol}: ₹{data.ltp} ({data.change_percent > 0 ? '+' : ''}{data.change_percent}%)
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Updated: {new Date(data.last_updated).toLocaleTimeString()}
                    </Typography>
                  </Box>
                ))
              )}
            </Box>
          </Paper>
        </Grid>
        
        {/* Hook Data */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              📊 Analytics Hook Data ({debugInfo.majorIndicesCount})
            </Typography>
            <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
              {indicesFromHook.major.length === 0 ? (
                <Typography color="warning">⚠️ No major indices from hook</Typography>
              ) : (
                indicesFromHook.major.slice(0, 5).map((index, i) => (
                  <Box key={i} sx={{ mb: 1, p: 1, bgcolor: 'background.default', borderRadius: 1 }}>
                    <Typography variant="body2" fontWeight="bold">
                      {index.symbol || index.name}: ₹{index.last_price || index.ltp || 'N/A'}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Change: {index.change_percent || 'N/A'}%
                    </Typography>
                  </Box>
                ))
              )}
            </Box>
          </Paper>
        </Grid>
        
        {/* Raw Data */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              🔍 Raw Data Comparison
            </Typography>
            <Box sx={{ maxHeight: 200, overflow: 'auto', fontFamily: 'monospace', fontSize: '0.8rem' }}>
              <pre>
                {JSON.stringify({
                  zustand_indices: Object.keys(indicesInZustand),
                  hook_major_indices: indicesFromHook.major.map(i => i.symbol || i.name),
                  debug_info: debugInfo
                }, null, 2)}
              </pre>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default IndicesDebugPanel;