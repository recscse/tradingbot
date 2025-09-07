// store/optimizedMarketStore.js - Optimized Market Data Store
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

const useOptimizedMarketStore = create(
  subscribeWithSelector((set, get) => ({
    // Core market data
    prices: new Map(), // Use Map for better performance
    indices: new Map(),
    analytics: {},
    
    // Connection status
    isConnected: false,
    lastUpdate: Date.now(),
    
    // Performance metrics
    updateCount: 0,
    errorCount: 0,
    
    // Actions
    updatePrice: (priceData) => {
      if (!priceData || !priceData.symbol) return;
      
      const currentPrices = get().prices;
      const newPrices = new Map(currentPrices);
      
      // Normalize price data
      const normalizedData = {
        symbol: priceData.symbol,
        ltp: priceData.ltp || priceData.last_price || 0,
        change: priceData.change || 0,
        change_percent: priceData.change_percent || 0,
        volume: priceData.volume || 0,
        high: priceData.high || 0,
        low: priceData.low || 0,
        timestamp: Date.now(),
        ...priceData
      };
      
      newPrices.set(priceData.symbol, normalizedData);
      
      set({ 
        prices: newPrices,
        lastUpdate: Date.now(),
        updateCount: get().updateCount + 1
      });
    },
    
    updatePrices: (pricesData) => {
      if (!pricesData || typeof pricesData !== 'object') return;
      
      const currentPrices = get().prices;
      const newPrices = new Map(currentPrices);
      let updateCount = 0;
      
      // Handle different data formats
      const entries = pricesData instanceof Map ? 
        pricesData.entries() : 
        Object.entries(pricesData);
      
      for (const [key, priceData] of entries) {
        if (!priceData || typeof priceData !== 'object') continue;
        
        const symbol = priceData.symbol || key;
        if (!symbol) continue;
        
        const normalizedData = {
          symbol: symbol,
          ltp: priceData.ltp || priceData.last_price || 0,
          change: priceData.change || 0,
          change_percent: priceData.change_percent || 0,
          volume: priceData.volume || 0,
          high: priceData.high || 0,
          low: priceData.low || 0,
          timestamp: Date.now(),
          ...priceData
        };
        
        newPrices.set(symbol, normalizedData);
        updateCount++;
      }
      
      if (updateCount > 0) {
        set({ 
          prices: newPrices,
          lastUpdate: Date.now(),
          updateCount: get().updateCount + updateCount
        });
      }
    },
    
    updateIndex: (indexData) => {
      if (!indexData || !indexData.symbol) return;
      
      const currentIndices = get().indices;
      const newIndices = new Map(currentIndices);
      
      newIndices.set(indexData.symbol, {
        ...indexData,
        timestamp: Date.now()
      });
      
      set({ 
        indices: newIndices,
        lastUpdate: Date.now()
      });
    },
    
    updateAnalytics: (analyticsData) => {
      if (!analyticsData || typeof analyticsData !== 'object') return;
      
      set({ 
        analytics: {
          ...get().analytics,
          ...analyticsData,
          timestamp: Date.now()
        },
        lastUpdate: Date.now()
      });
    },
    
    setConnectionStatus: (connected) => {
      set({ isConnected: connected });
    },
    
    // Getters
    getPrice: (symbol) => {
      if (!symbol) return null;
      return get().prices.get(symbol) || null;
    },
    
    getPrices: () => {
      return Object.fromEntries(get().prices);
    },
    
    getIndex: (symbol) => {
      if (!symbol) return null;
      return get().indices.get(symbol) || null;
    },
    
    getIndices: () => {
      return Object.fromEntries(get().indices);
    },
    
    getTopMovers: (count = 10) => {
      const prices = Array.from(get().prices.values());
      
      const gainers = prices
        .filter(p => p.change_percent > 0)
        .sort((a, b) => b.change_percent - a.change_percent)
        .slice(0, count);
        
      const losers = prices
        .filter(p => p.change_percent < 0)
        .sort((a, b) => a.change_percent - b.change_percent)
        .slice(0, count);
        
      return { gainers, losers };
    },
    
    getMarketSummary: () => {
      const prices = Array.from(get().prices.values());
      if (prices.length === 0) return null;
      
      const advancing = prices.filter(p => p.change_percent > 0).length;
      const declining = prices.filter(p => p.change_percent < 0).length;
      const unchanged = prices.length - advancing - declining;
      
      return {
        total: prices.length,
        advancing,
        declining,
        unchanged,
        advanceDeclineRatio: declining > 0 ? (advancing / declining).toFixed(2) : '∞',
        marketBreadth: (((advancing - declining) / prices.length) * 100).toFixed(1)
      };
    },
    
    // Utility actions
    clearData: () => {
      set({
        prices: new Map(),
        indices: new Map(),
        analytics: {},
        updateCount: 0,
        errorCount: 0
      });
    },
    
    incrementErrorCount: () => {
      set({ errorCount: get().errorCount + 1 });
    },
    
    getStats: () => ({
      priceCount: get().prices.size,
      indexCount: get().indices.size,
      updateCount: get().updateCount,
      errorCount: get().errorCount,
      lastUpdate: get().lastUpdate,
      isConnected: get().isConnected
    })
  }))
);

export default useOptimizedMarketStore;