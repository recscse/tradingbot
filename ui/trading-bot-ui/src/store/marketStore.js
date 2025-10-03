// store/marketStore.js - Zustand store for ultra-fast live price updates
// NOTE: This version defers the actual `set(...)` calls for updatePrice/updatePrices
// to the microtask queue to avoid "setState during render" React errors.
// It also stores each sanitized price under multiple canonical keys so UI lookups
// by instrument_key OR symbol OR compact forms succeed.

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

// Helper: compact key (remove whitespace, dashes/underscores, uppercase)
const compactKey = (s) => {
  if (s === undefined || s === null) return "";
  return String(s)
    .replace(/[\s_-]+/g, "")
    .toUpperCase();
};

// Helper: get RHS from pipe-delimited instrument_key (e.g. "NSE_INDEX|Nifty 50" -> "Nifty 50")
const rhsFromPipe = (s) => {
  if (!s) return "";
  try {
    const parts = String(s)
      .split("|")
      .map((p) => p.trim())
      .filter(Boolean);
    return parts.length > 1 ? parts[parts.length - 1] : parts[0] || "";
  } catch (e) {
    return String(s);
  }
};

// Helper function to validate price data
const validatePriceData = (data) => {
  if (!data || typeof data !== "object") return false;
  const priceField = data.ltp !== undefined ? data.ltp : data.last_price;

  if (
    process.env.NODE_ENV === "development" &&
    data.symbol &&
    ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"].includes(
      String(data.symbol).toUpperCase()
    )
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

// ⚡ CRITICAL FIX: Batching mechanism to prevent update storms
let updateQueue = [];
let batchTimeout = null;
const BATCH_DELAY = 50; // 50ms batching window (20 updates/sec max)

const deferSet = (fn) => {
  updateQueue.push(fn);

  // Clear existing timeout
  if (batchTimeout) {
    clearTimeout(batchTimeout);
  }

  // Batch updates within 50ms window
  batchTimeout = setTimeout(() => {
    const queue = updateQueue;
    updateQueue = [];
    batchTimeout = null;

    // Execute all queued updates in one microtask
    Promise.resolve().then(() => {
      queue.forEach(fn => {
        try {
          fn();
        } catch (e) {
          console.error("Deferred set error:", e);
        }
      });
    });
  }, BATCH_DELAY);
};

// Small utility: produce canonical keys for storing a sanitizedData instance
const buildStoreKeysForSanitized = (sanitizedData, feedKey = null) => {
  const keys = new Set();

  const symbol = sanitizedData.symbol || "";
  const instKey = sanitizedData.instrument_key || "";

  if (instKey) keys.add(instKey);
  if (symbol) keys.add(symbol);
  if (symbol) keys.add(compactKey(symbol));
  if (instKey) keys.add(rhsFromPipe(instKey));
  if (feedKey) keys.add(feedKey);

  // Also add compact form of RHS (to match feed/popular names compacted)
  if (instKey) keys.add(compactKey(rhsFromPipe(instKey)));

  // Debug for indices
  if (instKey?.includes('INDEX')) {
    console.log(`📍 Storing index under keys:`, Array.from(keys), `for symbol: ${symbol}`);
  }

  // Ensure non-empty keys only
  return Array.from(keys).filter(
    (k) => k !== undefined && k !== null && String(k) !== ""
  );
};

// Create Zustand store with subscribeWithSelector for granular subscriptions
const useMarketStore = create(
  subscribeWithSelector((set, get) => ({
    // Core price data - optimized for fast updates
    prices: {},

    // Performance metrics
    updateCount: 0,
    lastUpdate: null,
    connectionStatus: "disconnected",

    // Subscription management
    subscribedSymbols: new Set(),

    // ULTRA-FAST: Update single price (called for each real-time tick)
    // Accepts optional second param `feedKey` (raw key used in feed) to help mapping
    updatePrice: (priceData, feedKey = null) => {
      const sanitizedData = sanitizePriceData(priceData);
      if (!sanitizedData) return;

      const symbol = sanitizedData.symbol;
      if (!symbol) return;

      if (
        process.env.NODE_ENV === "development" &&
        (sanitizedData.sector === "INDEX" ||
          ["NIFTY", "SENSEX", "BANKNIFTY", "FINNIFTY"].includes(
            String(symbol).toUpperCase()
          ))
      ) {
        console.log(
          `🏛️ SINGLE INDEX UPDATE: ${symbol} = ₹${sanitizedData.ltp} (${sanitizedData.change_percent}%)`
        );
      }

      const keysToStore = buildStoreKeysForSanitized(sanitizedData, feedKey);

      // Defer the actual state mutation to microtask to avoid setState-in-render errors
      deferSet(() =>
        set((state) => {
          // If no effective change for the canonical symbol, we still want to update
          // because there could be a new feedKey mapping. We'll compare canonical symbol entry
          const canonicalKey = sanitizedData.symbol;
          const currentPriceForCanonical = state.prices[canonicalKey];

          if (
            currentPriceForCanonical &&
            currentPriceForCanonical.ltp === sanitizedData.ltp &&
            currentPriceForCanonical.volume === sanitizedData.volume
          ) {
            // but still ensure keysToStore exist in map pointing to that same object
            const newPrices = { ...state.prices };
            let anyNewKey = false;
            keysToStore.forEach((k) => {
              if (!newPrices[k]) {
                newPrices[k] = sanitizedData;
                anyNewKey = true;
              }
            });
            if (!anyNewKey) {
              return state; // nothing changed
            }
            return {
              prices: newPrices,
              updateCount: state.updateCount + 1,
              lastUpdate: Date.now(),
            };
          }

          // Otherwise merge sanitizedData under all candidate keys
          const newPrices = { ...state.prices };
          keysToStore.forEach((k) => {
            newPrices[k] = sanitizedData;
          });

          return {
            prices: newPrices,
            updateCount: state.updateCount + 1,
            lastUpdate: Date.now(),
          };
        })
      );
    },

    // BATCH UPDATE: Update multiple prices efficiently
    // pricesData is expected to be an object mapping feedKey -> rawData
    updatePrices: (pricesData) => {
      if (!pricesData || typeof pricesData !== "object") return;

      // Map of storeKey -> sanitizedData
      const sanitizedMap = {};
      let hasValidUpdates = false;

      Object.entries(pricesData).forEach(([feedKey, raw]) => {
        const sanitizedData = sanitizePriceData(raw);
        if (!sanitizedData) return;

        hasValidUpdates = true;

        // Build store keys for this sanitized entry
        const keys = buildStoreKeysForSanitized(sanitizedData, feedKey);
        keys.forEach((k) => {
          // last write wins within this batch for key
          sanitizedMap[k] = sanitizedData;
        });

        // Also ensure canonical symbol key present
        if (sanitizedData.symbol) {
          sanitizedMap[sanitizedData.symbol] = sanitizedData;
        }
      });

      if (!hasValidUpdates) return;

      // Defer merge to microtask with batching
      deferSet(() =>
        set((state) => {
          const newPrices = { ...state.prices, ...sanitizedMap };

          return {
            prices: newPrices,
            updateCount: state.updateCount + 1, // ⚡ FIX: Increment by 1, not by count
            lastUpdate: Date.now(),
          };
        })
      );
    },

    // Get price for specific symbol or instrument_key (tries multiple lookups)
    getPrice: (symbolOrKey) => {
      if (!symbolOrKey) return null;

      const state = get();

      // Try exact match first
      if (state.prices[symbolOrKey]) {
        return state.prices[symbolOrKey];
      }

      // Try compact key
      const compact = compactKey(symbolOrKey);
      if (compact && state.prices[compact]) {
        return state.prices[compact];
      }

      // Try RHS from pipe (for instrument_key format)
      const rhs = rhsFromPipe(symbolOrKey);
      if (rhs && state.prices[rhs]) {
        return state.prices[rhs];
      }

      // Try compact RHS
      const compactRhs = compactKey(rhs);
      if (compactRhs && state.prices[compactRhs]) {
        return state.prices[compactRhs];
      }

      return null;
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

    // Get real-time top movers (combines gainers and losers)
    getRealTimeTopMovers: (limit = 10) => {
      const state = get();
      const allPrices = Object.values(state.prices);

      // Deduplicate by symbol (in case same price stored under multiple keys)
      const uniquePrices = new Map();
      allPrices.forEach(price => {
        if (price.symbol && !uniquePrices.has(price.symbol)) {
          uniquePrices.set(price.symbol, price);
        }
      });

      const uniqueArray = Array.from(uniquePrices.values());

      const gainers = uniqueArray
        .filter((price) => price.change_percent > 0)
        .sort((a, b) => b.change_percent - a.change_percent)
        .slice(0, limit);

      const losers = uniqueArray
        .filter((price) => price.change_percent < 0)
        .sort((a, b) => a.change_percent - b.change_percent)
        .slice(0, limit);

      return { gainers, losers };
    },

    // Get volume leaders (highest volume stocks)
    getVolumeLeaders: (limit = 10) => {
      const state = get();
      const allPrices = Object.values(state.prices);

      // Deduplicate by symbol
      const uniquePrices = new Map();
      allPrices.forEach(price => {
        if (price.symbol && !uniquePrices.has(price.symbol)) {
          uniquePrices.set(price.symbol, price);
        }
      });

      return Array.from(uniquePrices.values())
        .filter((price) => price.volume > 0)
        .sort((a, b) => b.volume - a.volume)
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
      // connection status is OK to set synchronously - not heavy
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
