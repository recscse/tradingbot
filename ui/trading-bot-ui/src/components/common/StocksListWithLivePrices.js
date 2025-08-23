// components/common/StocksListWithLivePrices.js
/**
 * 🚀 Enhanced StocksList component with ZERO-DELAY live prices
 * 
 * This is a wrapper around the existing StocksList component that enhances 
 * the data with live prices from the ZERO-DELAY streaming service.
 * It maintains full compatibility with the existing component.
 */

import React from 'react';
import StocksList from './StocksList';
import { useIndicesWithLivePrices } from '../../hooks/useIndicesWithLivePrices';
import useMarketStore from '../../store/marketStore';
import { Box, Chip, Tooltip } from '@mui/material';
import { SignalWifi4Bar, SignalWifi0Bar } from '@mui/icons-material';
import { green, grey } from '@mui/material/colors';

const StocksListWithLivePrices = ({ 
  data = [], 
  title = '',
  enhanceWithLivePrices = true,
  showLiveIndicator = true,
  ...stocksListProps 
}) => {
  // Get all live prices from Zustand store
  const allLivePrices = useMarketStore((state) => state.prices);
  const connectionStatus = useMarketStore((state) => state.connectionStatus);
  
  // Get enhanced data with live prices from hook (fallback)
  const { indices: enhancedData, isConnected } = useIndicesWithLivePrices(
    enhanceWithLivePrices ? data : []
  );
  
  // Enhanced data processing: prioritize Zustand store data over hook data
  const finalData = React.useMemo(() => {
    if (!enhanceWithLivePrices) return data;
    
    // Debug: Log available symbols in Zustand store (development only)
    if (process.env.NODE_ENV === 'development') {
      const zustandSymbols = Object.keys(allLivePrices).filter(key => 
        ['NIFTY', 'SENSEX', 'BANKNIFTY', 'FINNIFTY'].includes(key) || key.includes('INDEX')
      );
      if (zustandSymbols.length > 0) {
        console.log('🏛️ INDEX SYMBOLS in Zustand store:', zustandSymbols);
      }
    }
    
    return data.map(item => {
      const symbol = item.symbol || item.name;
      
      // Debug logging (development only)
      if (process.env.NODE_ENV === 'development') {
        console.log(`🔍 Processing item: ${symbol}`, item);
      }
      
      // Try to get live data from Zustand store first
      const livePrice = allLivePrices[symbol];
      if (livePrice) {
        // Debug logging (development only)
        if (process.env.NODE_ENV === 'development') {
          console.log(`✅ Using Zustand data for ${symbol}:`, livePrice);
        }
        return {
          ...item,
          last_price: livePrice.ltp,
          ltp: livePrice.ltp,
          current_price: livePrice.ltp,
          change: livePrice.change,
          change_percent: livePrice.change_percent,
          volume: livePrice.volume,
          _live_data_available: true,
          _source: 'zustand_store'
        };
      }
      
      // Fallback to enhanced data from hook
      const hookItem = enhancedData.find(e => e.symbol === symbol || e.name === symbol);
      if (hookItem && hookItem._live_data_available) {
        // Debug logging (development only)
        if (process.env.NODE_ENV === 'development') {
          console.log(`🔄 Using hook data for ${symbol}:`, hookItem);
        }
        return hookItem;
      }
      
      // Return original data
      if (process.env.NODE_ENV === 'development') {
        console.log(`❌ No live data for ${symbol}, using original`);
      }
      return {
        ...item,
        _live_data_available: false,
        _source: 'analytics_only'
      };
    });
  }, [data, allLivePrices, enhancedData, enhanceWithLivePrices]);
  
  // Calculate summary stats for enhanced data
  const enhancedSummary = React.useMemo(() => {
    const liveCount = finalData.filter(item => item._live_data_available).length;
    const totalCount = finalData.length;
    const livePercentage = totalCount > 0 ? Math.round((liveCount / totalCount) * 100) : 0;
    
    return {
      total: totalCount,
      live: liveCount,
      livePercentage
    };
  }, [finalData]);
  
  // Enhanced title with live indicator
  const enhancedTitle = React.useMemo(() => {
    if (!enhanceWithLivePrices || !showLiveIndicator) {
      return title;
    }
    
    const liveCount = enhancedSummary.live;
    const totalCount = enhancedSummary.total;
    
    if (liveCount === 0) {
      return title;
    }
    
    return (
      <Box display="flex" alignItems="center" gap={1}>
        <span>{title}</span>
        {(isConnected || connectionStatus === 'connected') && liveCount > 0 && (
          <Tooltip title={`${liveCount}/${totalCount} indices with live prices (${enhancedSummary.livePercentage}%)`}>
            <Chip
              size="small"
              icon={<SignalWifi4Bar />}
              label={`${liveCount} LIVE`}
              sx={{
                backgroundColor: green[500],
                color: 'white',
                fontSize: '0.7rem',
                height: '20px',
                '& .MuiChip-icon': {
                  fontSize: '14px',
                  color: 'white'
                }
              }}
            />
          </Tooltip>
        )}
        {!isConnected && connectionStatus !== 'connected' && (
          <Tooltip title="Not connected to live data stream">
            <Chip
              size="small"
              icon={<SignalWifi0Bar />}
              label="OFFLINE"
              sx={{
                backgroundColor: grey[500],
                color: 'white',
                fontSize: '0.7rem',
                height: '20px',
                '& .MuiChip-icon': {
                  fontSize: '14px',
                  color: 'white'
                }
              }}
            />
          </Tooltip>
        )}
      </Box>
    );
  }, [title, enhanceWithLivePrices, showLiveIndicator, enhancedSummary, isConnected, connectionStatus]);
  
  return (
    <StocksList
      {...stocksListProps}
      data={finalData}
      title={enhancedTitle}
    />
  );
};

export default StocksListWithLivePrices;