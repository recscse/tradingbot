// hooks/useIndicesWithLivePrices.js
/**
 * 🚀 Enhanced hook that combines existing indices data with ZERO-DELAY live prices
 * 
 * This hook takes the existing indices data structure and enhances it with 
 * real-time prices from the ZERO-DELAY streaming service without breaking 
 * the existing functionality.
 */

import { useMemo } from 'react';
import { useZeroDelayMarketData } from './useZeroDelayMarketData';

export const useIndicesWithLivePrices = (existingIndicesData = []) => {
  // Get live data from ZERO-DELAY streaming
  const { 
    marketData: liveData, 
    isConnected, 
    lastUpdate 
  } = useZeroDelayMarketData({
    enableStats: false // Disable stats for this hook to reduce overhead
  });

  // Enhance existing indices data with live prices
  const enhancedIndices = useMemo(() => {
    if (!existingIndicesData || existingIndicesData.length === 0) {
      return [];
    }

    if (!liveData || Object.keys(liveData).length === 0) {
      // No live data available, return existing data as-is
      console.log('🔍 No live data available for indices enhancement');
      return existingIndicesData.map(index => ({
        ...index,
        _live_data_available: false,
        _source: 'analytics_only'
      }));
    }

    // Debug: Log available live data keys for indices
    const indexKeys = Object.keys(liveData).filter(key => 
      key.includes('INDEX') || key.includes('NIFTY') || key.includes('SENSEX')
    );
    console.log('🔍 Available INDEX keys in live data:', indexKeys.slice(0, 10));

    return existingIndicesData.map(index => {
      const symbol = index.symbol || index.name;
      
      // Quick key matching - try common patterns
      const possibleKeys = [
        `NSE_INDEX|${symbol}`,
        `BSE_INDEX|${symbol}`,
        index.instrument_key,
        // Common mappings
        symbol === 'NIFTY' ? 'NSE_INDEX|Nifty 50' : null,
        symbol === 'NIFTY 50' ? 'NSE_INDEX|Nifty 50' : null,
        symbol === 'SENSEX' ? 'BSE_INDEX|SENSEX' : null,
        symbol === 'BANKNIFTY' ? 'NSE_INDEX|Nifty Bank' : null,
        symbol === 'NIFTY BANK' ? 'NSE_INDEX|Nifty Bank' : null,
      ].filter(Boolean);

      // Find live data
      let liveDataEntry = null;
      let matchedKey = null;
      for (const key of possibleKeys) {
        if (liveData[key]) {
          liveDataEntry = liveData[key];
          matchedKey = key;
          break;
        }
      }

      if (liveDataEntry) {
        // Extract live price
        const livePrice = parseFloat(liveDataEntry.lp || liveDataEntry.last_price || 0);
        
        if (livePrice > 0) {
          // Return enhanced data with live price
          return {
            ...index,
            last_price: livePrice,
            ltp: livePrice,
            current_price: livePrice,
            _live_data_available: true,
            _matched_key: matchedKey,
            _source: 'enhanced_with_live'
          };
        }
      }

      // Return original data if no live price found
      return {
        ...index,
        _live_data_available: false,
        _source: 'analytics_only'
      };
    });
  }, [existingIndicesData, liveData]);

  // Calculate summary stats
  const summary = useMemo(() => {
    const liveCount = enhancedIndices.filter(i => i._live_data_available).length;
    const totalCount = enhancedIndices.length;
    const livePercentage = totalCount > 0 ? Math.round((liveCount / totalCount) * 100) : 0;

    return {
      total: totalCount,
      live: liveCount,
      livePercentage,
      lastUpdate
    };
  }, [enhancedIndices, lastUpdate]);

  return {
    indices: enhancedIndices,
    isConnected,
    summary
  };
};