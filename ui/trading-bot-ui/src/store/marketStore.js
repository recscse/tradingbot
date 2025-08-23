// store/marketStore.js - Zustand store for ultra-fast live price updates
import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

// Helper function to validate price data
const validatePriceData = (data) => {
  // Check if data exists and is an object
  if (!data || typeof data !== "object") return false;

  // Accept data if it has ltp OR last_price field
  const priceField = data.ltp !== undefined ? data.ltp : data.last_price;

  // Debug logging for indices (development only)
  if (
    process.env.NODE_ENV === "development" &&
    data.symbol &&
    ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"].includes(data.symbol)
  ) {
    console.log(`🔍 VALIDATING INDEX: ${data.symbol}`, {
      hasLtp: data.ltp !== undefined,
      hasLastPrice: data.last_price !== undefined,
      priceField,
      isValid:
        priceField !== undefined &&
        priceField !== null &&
        !isNaN(Number(priceField)),
    });
  }

  return (
    priceField !== undefined &&
    priceField !== null &&
    !isNaN(Number(priceField))
  );
};

// Helper function to sanitize price data
const sanitizePriceData = (data) => {
  if (!validatePriceData(data)) return null;

  // Use ltp field if available, otherwise use last_price
  const priceValue = data.ltp !== undefined ? data.ltp : data.last_price;

  return {
    symbol: data.symbol || "",
    instrument_key: data.instrument_key || "",
    ltp: Number(priceValue) || 0,
    change: Number(data.change) || 0,
    change_percent: Number(data.change_percent) || 0,
    volume: Number(data.volume) || 0,
    high: Number(data.high) || 0,
    low: Number(data.low) || 0,
    open: Number(data.open) || 0,
    sector: data.sector || "OTHER",
    exchange: data.exchange || "NSE",
    timestamp: data.timestamp || new Date().toISOString(),
    last_updated: Date.now(),
  };
};

// Create Zustand store with selector middleware for granular subscriptions
const useMarketStore = create(
  subscribeWithSelector((set, get) => ({
    // 🚀 Core price data - optimized for fast updates
    prices: {},

    // Performance metrics
    updateCount: 0,
    lastUpdate: null,
    connectionStatus: "disconnected",

    // Subscription management
    subscribedSymbols: new Set(),

    // 🚀 ULTRA-FAST: Update single price (called for each real-time tick)
    updatePrice: (priceData) => {
      const sanitizedData = sanitizePriceData(priceData);
      if (!sanitizedData) return;

      const symbol = sanitizedData.symbol;
      if (!symbol) return;

      // Debug logging for indices (development only)
      if (
        process.env.NODE_ENV === "development" &&
        (sanitizedData.sector === "INDEX" ||
          ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"].includes(symbol))
      ) {
        console.log(
          `🏛️ SINGLE INDEX UPDATE: ${symbol} = ₹${sanitizedData.ltp} (${sanitizedData.change_percent}%)`
        );
      }

      set((state) => {
        // Only update if the price is actually different (avoid unnecessary renders)
        const currentPrice = state.prices[symbol];
        if (
          currentPrice &&
          currentPrice.ltp === sanitizedData.ltp &&
          currentPrice.volume === sanitizedData.volume
        ) {
          return state; // No change needed
        }

        return {
          prices: {
            ...state.prices,
            [symbol]: sanitizedData,
          },
          updateCount: state.updateCount + 1,
          lastUpdate: Date.now(),
        };
      });
    },

    // 🚀 BATCH UPDATE: Update multiple prices efficiently
    updatePrices: (pricesData) => {
      if (!pricesData || typeof pricesData !== "object") return;

      const sanitizedPrices = {};
      let hasValidUpdates = false;
      

      // Process all price updates
      Object.entries(pricesData).forEach(([key, data]) => {
        const sanitizedData = sanitizePriceData(data);
        if (sanitizedData && sanitizedData.symbol) {
          sanitizedPrices[sanitizedData.symbol] = sanitizedData;
          hasValidUpdates = true;

          // Debug logging for indices (development only)
          if (
            process.env.NODE_ENV === "development" &&
            (sanitizedData.sector === "INDEX" ||
              key.includes("INDEX") ||
              ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"].includes(
                sanitizedData.symbol
              ))
          ) {
            console.log(
              `🏛️ INDEX UPDATE: ${sanitizedData.symbol} = ₹${sanitizedData.ltp} (${sanitizedData.change_percent}%)`
            );
          }
        }
      });

      if (!hasValidUpdates) return;

      set((state) => {
        const newPrices = {
          ...state.prices,
          ...sanitizedPrices,
        };
        
        
        return {
          prices: newPrices,
          updateCount: state.updateCount + Object.keys(sanitizedPrices).length,
          lastUpdate: Date.now(),
        };
      });
    },

    // Get price for specific symbol
    getPrice: (symbol) => {
      return get().prices[symbol] || null;
    },

    // Get prices for multiple symbols
    getPrices: (symbols) => {
      const state = get();
      return symbols.reduce((acc, symbol) => {
        if (state.prices[symbol]) {
          acc[symbol] = state.prices[symbol];
        }
        return acc;
      }, {});
    },

    // Get all prices (use sparingly)
    getAllPrices: () => {
      return get().prices;
    },

    // Filter prices by criteria
    getFilteredPrices: (filterFn) => {
      const state = get();
      return Object.values(state.prices).filter(filterFn);
    },

    // Get prices by sector
    getPricesBySector: (sector) => {
      const state = get();
      return Object.values(state.prices).filter(
        (price) => price.sector === sector
      );
    },

    // Get top gainers
    getTopGainers: (limit = 10) => {
      const state = get();
      return Object.values(state.prices)
        .filter((price) => price.change_percent > 0)
        .sort((a, b) => b.change_percent - a.change_percent)
        .slice(0, limit);
    },

    // Get top losers
    getTopLosers: (limit = 10) => {
      const state = get();
      return Object.values(state.prices)
        .filter((price) => price.change_percent < 0)
        .sort((a, b) => a.change_percent - b.change_percent)
        .slice(0, limit);
    },

    // Subscription management
    addSubscription: (symbol) => {
      set((state) => ({
        subscribedSymbols: new Set([...state.subscribedSymbols, symbol]),
      }));
    },

    removeSubscription: (symbol) => {
      set((state) => {
        const newSubscriptions = new Set(state.subscribedSymbols);
        newSubscriptions.delete(symbol);
        return { subscribedSymbols: newSubscriptions };
      });
    },

    // Connection status
    setConnectionStatus: (status) => {
      set({ connectionStatus: status });
    },

    // Clear all data (useful for cleanup)
    clearPrices: () => {
      set({
        prices: {},
        updateCount: 0,
        lastUpdate: null,
      });
    },

    // Get store statistics
    getStats: () => {
      const state = get();
      const priceArray = Object.values(state.prices);

      return {
        totalSymbols: priceArray.length,
        updateCount: state.updateCount,
        lastUpdate: state.lastUpdate,
        connectionStatus: state.connectionStatus,
        subscribedSymbols: state.subscribedSymbols.size,
        positiveChanges: priceArray.filter((p) => p.change > 0).length,
        negativeChanges: priceArray.filter((p) => p.change < 0).length,
        avgVolume:
          priceArray.reduce((sum, p) => sum + p.volume, 0) /
            priceArray.length || 0,
      };
    },
  }))
);

// Selectors for common use cases (optimized for performance)
export const selectPrice = (symbol) => (state) => state.prices[symbol];
export const selectPriceField = (symbol, field) => (state) =>
  state.prices[symbol]?.[field];
export const selectAllPrices = (state) => state.prices;
export const selectConnectionStatus = (state) => state.connectionStatus;
export const selectUpdateCount = (state) => state.updateCount;

// Custom hook for subscribing to specific symbol
export const useSymbolPrice = (symbol) => {
  return useMarketStore(selectPrice(symbol));
};

// Custom hook for subscribing to specific price field
export const useSymbolPriceField = (symbol, field) => {
  return useMarketStore(selectPriceField(symbol, field));
};

// Custom hook for multiple symbols
export const useSymbolPrices = (symbols) => {
  return useMarketStore((state) =>
    symbols.reduce((acc, symbol) => {
      if (state.prices[symbol]) {
        acc[symbol] = state.prices[symbol];
      }
      return acc;
    }, {})
  );
};

export default useMarketStore;
