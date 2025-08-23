// components/debug/DebugIndicesData.js
/**
 * 🔍 Debug component to show what indices data is available
 */

import React from 'react';
import { Box, Typography, Paper, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import { ExpandMore } from '@mui/icons-material';
import { useZeroDelayMarketData } from '../../hooks/useZeroDelayMarketData';
import { useMarket } from '../../hooks/useUnifiedMarketData';

const DebugIndicesData = () => {
  const { marketData: liveData, isConnected: liveConnected } = useZeroDelayMarketData();
  const { marketData: legacyData, isConnected: legacyConnected } = useMarket();

  // Filter for index-related data
  const liveIndexData = React.useMemo(() => {
    if (!liveData) return {};
    return Object.keys(liveData)
      .filter(key => key.includes('INDEX') || key.includes('NIFTY') || key.includes('SENSEX'))
      .reduce((acc, key) => {
        acc[key] = liveData[key];
        return acc;
      }, {});
  }, [liveData]);

  const legacyIndexData = React.useMemo(() => {
    if (!legacyData) return {};
    return Object.keys(legacyData)
      .filter(key => key.includes('INDEX') || key.includes('NIFTY') || key.includes('SENSEX'))
      .reduce((acc, key) => {
        acc[key] = legacyData[key];
        return acc;
      }, {});
  }, [legacyData]);

  return (
    <Box p={2}>
      <Typography variant="h6" gutterBottom>
        🔍 Debug: Indices Data Sources
      </Typography>
      
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>
            🚀 ZERO-DELAY Live Data (Connected: {liveConnected ? '✅' : '❌'})
            - {Object.keys(liveIndexData).length} index entries
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Paper sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
            <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(liveIndexData, null, 2)}
            </pre>
          </Paper>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>
            📊 Legacy Market Data (Connected: {legacyConnected ? '✅' : '❌'})
            - {Object.keys(legacyIndexData).length} index entries
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Paper sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
            <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(legacyIndexData, null, 2)}
            </pre>
          </Paper>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>
            🔍 All Live Data Keys (Sample)
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Paper sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
            <Typography variant="body2">
              Total keys: {liveData ? Object.keys(liveData).length : 0}
            </Typography>
            <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
              {liveData ? Object.keys(liveData).slice(0, 20).join('\n') : 'No data'}
            </pre>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default DebugIndicesData;