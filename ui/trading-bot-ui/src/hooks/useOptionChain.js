// hooks/useOptionChain.js - Option Chain Hook with WebSocket Integration (Modified for direct instrument_key)
import { useState, useEffect, useCallback, useMemo } from "react";
import { useUnifiedMarketData } from "./useUnifiedMarketData";

const useOptionChain = (symbolOrInstrumentKey) => {
  // Accept symbol or instrumentKey
  // State
  const [optionChainData, setOptionChainData] = useState(null);
  const [futuresData, setFuturesData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedExpiry, setSelectedExpiry] = useState("");
  const [livePrices, setLivePrices] = useState({});
  const [resolvedInstrumentKey, setResolvedInstrumentKey] = useState(null);
  const API_URL = process.env.REACT_APP_API_URL;

  // Get market data hook for live prices
  const { getStockData, /* getLivePrices, */ isConnected, subscribeToInstruments } = useUnifiedMarketData(); // getLivePrices reserved for future live price updates

  // Resolve symbol to instrument key
  const resolveInstrumentKey = useCallback(async (input) => {
    if (!input) return null;
    
    // If it's already a valid instrument_key (contains | and not a fake _KEY), use it directly
    if (input.includes('|') && !input.endsWith('_KEY')) {
      return input;
    }
    
    // Otherwise, resolve symbol to instrument_key using API
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        throw new Error("Authentication required");
      }
      
      const response = await fetch(
        `${API_URL}/api/v1/options/symbol/${encodeURIComponent(input)}/instrument-key`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to resolve instrument key for ${input}`);
      }
      
      const data = await response.json();
      return data.instrument_key;
    } catch (err) {
      console.error("Error resolving instrument key:", err);
      setError(err.message);
      return null;
    }
  }, [API_URL]);

  // API functions - Updated to use instrument_key based flow
  const fetchOptionContracts = useCallback(
    async (instKey, expiry = null) => {
      // Accept instrument key as parameter
      if (!instKey) return; // Use the passed key
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          throw new Error("Authentication required");
        }
        // Use the passed instrument key (instKey)
        const url = expiry
          ? `${API_URL}/api/v1/options/contracts?instrument_key=${encodeURIComponent(
              instKey // Use instKey here
            )}&expiry_date=${expiry}`
          : `${API_URL}/api/v1/options/contracts?instrument_key=${encodeURIComponent(
              instKey // Use instKey here
            )}`;
        const response = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
        if (!response.ok) {
          if (response.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/";
            throw new Error("Authentication failed. Please login again.");
          }
          if (response.status === 404) {
            throw new Error(
              `No option contracts found for the provided instrument key`
            );
          }
          throw new Error(
            `Failed to fetch option contracts: ${response.statusText}`
          );
        }
        const data = await response.json();
        return data;
      } catch (err) {
        console.error("Error fetching option contracts:", err);
        setError(err.message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [API_URL] // Added API_URL dependency
  );

  const fetchOptionChain = useCallback(
    async (instKey, expiryDate) => {
      // Accept instrument key as parameter
      if (!instKey || !expiryDate) return; // Use the passed key
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          throw new Error("Authentication required");
        }
        // Use the passed instrument key (instKey)
        const url = `${API_URL}/api/v1/options/chain?instrument_key=${encodeURIComponent(
          instKey // Use instKey here
        )}&expiry_date=${expiryDate}`;
        const response = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
        if (!response.ok) {
          if (response.status === 401) {
            localStorage.removeItem("token");
            window.location.href = "/";
            throw new Error("Authentication failed. Please login again.");
          }
          if (response.status === 404) {
            throw new Error(
              `No option chain found for the provided instrument key`
            );
          }
          throw new Error(
            `Failed to fetch option chain: ${response.statusText}`
          );
        }
        const data = await response.json();
        
        // Transform backend response to expected format
        if (data.status === "success" && data.data) {
          const transformedData = {
            options: {},
            strike_prices: [],
            spot_price: null,
            underlying_key: instKey,
            expiry_dates: [expiryDate]
          };
          
          data.data.forEach(item => {
            const strike = item.strike_price;
            const strikeKey = strike.toString();
            
            transformedData.strike_prices.push(strike);
            transformedData.options[strikeKey] = {};
            
            if (!transformedData.spot_price && item.underlying_spot_price) {
              transformedData.spot_price = item.underlying_spot_price;
            }
            
            // Transform call options
            if (item.call_options) {
              transformedData.options[strikeKey].CE = {
                instrument_key: item.call_options.instrument_key,
                strike_price: strike,
                option_type: "CE",
                expiry: expiryDate,
                market_data: item.call_options.market_data || {},
                option_greeks: item.call_options.option_greeks || {}
              };
            }
            
            // Transform put options  
            if (item.put_options) {
              transformedData.options[strikeKey].PE = {
                instrument_key: item.put_options.instrument_key,
                strike_price: strike,
                option_type: "PE", 
                expiry: expiryDate,
                market_data: item.put_options.market_data || {},
                option_greeks: item.put_options.option_greeks || {}
              };
            }
          });
          
          // Sort strike prices
          transformedData.strike_prices.sort((a, b) => a - b);
          
          setOptionChainData(transformedData);
          return transformedData;
        }
        
        setOptionChainData(data);
        return data;
      } catch (err) {
        console.error("Error fetching option chain:", err);
        setError(err.message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [API_URL]
  ); // Added API_URL dependency

  const fetchFuturesData = useCallback(
    async (instrumentKeyOrSymbol) => {
      // Accept instrument key or symbol
      if (!instrumentKeyOrSymbol) return;
      try {
        const token = localStorage.getItem("token");
        if (!token) return;
        
        // Use the new endpoint that handles instrument keys
        const response = await fetch(
          `${API_URL}/api/v1/options/futures/key/${encodeURIComponent(instrumentKeyOrSymbol)}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );
        
        if (response.ok) {
          const data = await response.json();
          setFuturesData(data.futures || []);
          return data.futures || [];
        } else if (response.status === 400) {
          console.log(`Instrument key/symbol ${instrumentKeyOrSymbol} is not F&O eligible for futures`);
          setFuturesData([]);
          return [];
        } else {
          console.error(`Futures API error ${response.status}: ${response.statusText}`);
        }
      } catch (err) {
        console.error("Error fetching futures data:", err);
      }
      return [];
    },
    [API_URL]
  );

  // --- Removed checkFNOEligibility function (relies on symbol) ---
  // If needed, a new function accepting instrument_key could be created if the backend supports it.

  // Get all instrument keys for live price updates
  const getAllInstrumentKeys = useMemo(() => {
    const keys = [];
    if (optionChainData?.options) {
      Object.values(optionChainData.options).forEach((strikeData) => {
        Object.values(strikeData).forEach((contract) => {
          if (contract.instrument_key) {
            keys.push(contract.instrument_key);
          }
        });
      });
    }
    if (futuresData?.length) {
      futuresData.forEach((future) => {
        if (future.instrument_key) {
          keys.push(future.instrument_key);
        }
      });
    }
    // Add underlying stock
    if (optionChainData?.underlying_key) {
      keys.push(optionChainData.underlying_key);
    }
    return keys;
  }, [optionChainData, futuresData]);

  // Update live prices using WebSocket data
  const updateLivePrices = useCallback(() => {
    if (getAllInstrumentKeys.length === 0) return;
    try {
      // Get live prices for all option and futures instruments
      const prices = {};
      getAllInstrumentKeys.forEach((key) => {
        const stockData = getStockData(key);
        if (stockData) {
          prices[key] = {
            ltp: stockData.ltp || stockData.last_price,
            change: stockData.change,
            change_percent: stockData.change_percent,
            volume: stockData.volume,
            high: stockData.high,
            low: stockData.low,
            timestamp: stockData.timestamp || Date.now(),
          };
        }
      });
      setLivePrices(prices);
    } catch (err) {
      console.error("Error updating live prices:", err);
    }
  }, [getAllInstrumentKeys, getStockData]);

  // Get live price for specific instrument
  const getLivePrice = useCallback(
    (instrumentKey) => {
      return livePrices[instrumentKey]?.ltp || null;
    },
    [livePrices]
  );

  // Get live price data for specific instrument
  const getLivePriceData = useCallback(
    (instrumentKey) => {
      return livePrices[instrumentKey] || null;
    },
    [livePrices]
  );

  // Get option data for specific strike and type
  const getOptionData = useCallback(
    (strike, optionType) => {
      if (!optionChainData?.options) return null;
      return optionChainData.options[strike]?.[optionType] || null;
    },
    [optionChainData]
  );

  // Get strikes near ATM (at-the-money)
  const getATMStrikes = useCallback(
    (range = 5) => {
      if (!optionChainData?.spot_price || !optionChainData?.strike_prices)
        return [];
      const spotPrice = optionChainData.spot_price;
      const strikes = optionChainData.strike_prices;
      // Find closest strike to spot price
      const closestStrike = strikes.reduce((prev, curr) =>
        Math.abs(curr - spotPrice) < Math.abs(prev - spotPrice) ? curr : prev
      );
      const closestIndex = strikes.indexOf(closestStrike);
      const startIndex = Math.max(0, closestIndex - range);
      const endIndex = Math.min(strikes.length - 1, closestIndex + range);
      return strikes.slice(startIndex, endIndex + 1);
    },
    [optionChainData]
  );

  // Calculate option metrics
  const getOptionMetrics = useCallback(() => {
    if (!optionChainData?.options || !optionChainData?.spot_price) return null;
    const spotPrice = optionChainData.spot_price;
    let totalCallOI = 0;
    let totalPutOI = 0;
    let totalCallVolume = 0;
    let totalPutVolume = 0;
    let maxPainStrike = 0;
    let maxPainValue = Infinity;
    Object.entries(optionChainData.options).forEach(([strike, options]) => {
      const strikePrice = parseFloat(strike);
      const callOI = options.CE?.open_interest || 0;
      const putOI = options.PE?.open_interest || 0;
      const callVolume = options.CE?.volume || 0;
      const putVolume = options.PE?.volume || 0;
      totalCallOI += callOI;
      totalPutOI += putOI;
      totalCallVolume += callVolume;
      totalPutVolume += putVolume;
      // Calculate max pain (simplified)
      const callPain = Math.max(0, spotPrice - strikePrice) * callOI;
      const putPain = Math.max(0, strikePrice - spotPrice) * putOI;
      const totalPain = callPain + putPain;
      if (totalPain < maxPainValue) {
        maxPainValue = totalPain;
        maxPainStrike = strikePrice;
      }
    });
    return {
      totalCallOI,
      totalPutOI,
      putCallRatio: totalCallOI > 0 ? totalPutOI / totalCallOI : 0,
      totalCallVolume,
      totalPutVolume,
      maxPainStrike,
      spotPrice,
    };
  }, [optionChainData]);

  // Effect to resolve symbol to instrument key
  useEffect(() => {
    const resolve = async () => {
      if (symbolOrInstrumentKey) {
        const resolved = await resolveInstrumentKey(symbolOrInstrumentKey);
        setResolvedInstrumentKey(resolved);
      } else {
        setResolvedInstrumentKey(null);
      }
    };
    resolve();
  }, [symbolOrInstrumentKey, resolveInstrumentKey]);

  // Effect to fetch data when instrument_key is resolved
  useEffect(() => {
    const fetchInitialData = async () => {
      if (resolvedInstrumentKey) {
        // Fetch option contracts to get available expiry dates
        const contractsData = await fetchOptionContracts(resolvedInstrumentKey);
        if (
          contractsData &&
          contractsData.expiry_dates &&
          contractsData.expiry_dates.length > 0
        ) {
          // Auto-select the nearest expiry date
          setSelectedExpiry(contractsData.expiry_dates[0]);
        }
        // Fetch futures data (pass resolved instrument key)
        fetchFuturesData(resolvedInstrumentKey);
      } else {
        // Reset data if no instrument key
        setOptionChainData(null);
        setFuturesData([]);
        setSelectedExpiry("");
        setError(null);
        setLoading(false);
      }
    };
    fetchInitialData();
  }, [resolvedInstrumentKey, fetchOptionContracts, fetchFuturesData]);

  // Effect to fetch data when expiry changes
  useEffect(() => {
    if (resolvedInstrumentKey && selectedExpiry) {
      fetchOptionChain(resolvedInstrumentKey, selectedExpiry);
    }
  }, [selectedExpiry, resolvedInstrumentKey, fetchOptionChain]);

  // Effect to update live prices and subscribe to option instruments
  useEffect(() => {
    if (getAllInstrumentKeys.length > 0 && isConnected) {
      // Request subscription to option instrument keys for real-time data
      console.log('🔔 Subscribing to option instruments for real-time data:', getAllInstrumentKeys.slice(0, 5), '...');
      
      // Call the backend to ensure upstream subscription
      if (subscribeToInstruments) {
        subscribeToInstruments(getAllInstrumentKeys);
      }
      
      // Initial price update
      updateLivePrices();
      
      // Set up interval for periodic updates (fallback)
      const interval = setInterval(updateLivePrices, 1000); // Update every second
      return () => {
        clearInterval(interval);
        console.log('🔕 Unsubscribed from option instruments');
      };
    }
    
    // Clear prices when disconnected
    if (!isConnected) {
      setLivePrices({});
    }
  }, [getAllInstrumentKeys, isConnected, updateLivePrices, subscribeToInstruments]);

  // Enhanced refresh function with real-time status
  const refresh = useCallback(async () => {
    console.log('🔄 Refreshing option chain data...');
    
    if (resolvedInstrumentKey) {
      setLoading(true);
      setError(null);
      
      try {
        // Refresh option chain data
        if (selectedExpiry) {
          await fetchOptionChain(resolvedInstrumentKey, selectedExpiry);
        }
        
        // Refresh futures data
        await fetchFuturesData(resolvedInstrumentKey);
        
        // Force live price update
        if (isConnected) {
          updateLivePrices();
        }
        
        console.log('✅ Option chain data refreshed successfully');
      } catch (err) {
        console.error('❌ Option chain refresh failed:', err);
        setError('Failed to refresh option chain data. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  }, [resolvedInstrumentKey, selectedExpiry, fetchOptionChain, fetchFuturesData, updateLivePrices, isConnected]);

  // Calculate connection status details
  const wsConnected = isConnected;
  const spotPrice = optionChainData?.spot_price || optionChainData?.underlying_price;
  const expiryDates = optionChainData?.expiry_dates || [];
  const totalInstruments = getAllInstrumentKeys.length;
  const liveInstruments = Object.keys(livePrices).length;
  
  return {
    // Data
    optionChainData,
    futuresData,
    livePrices,
    selectedExpiry,
    instrumentKey: resolvedInstrumentKey, // The resolved instrument_key
    spotPrice, // Current spot price for easy access
    expiryDates, // Available expiry dates
    // Status
    loading,
    error,
    isConnected,
    wsConnected, // Enhanced connection status
    totalInstruments, // Total option instruments tracked
    liveInstruments, // Instruments with live data
    // Actions - Updated API methods
    setSelectedExpiry,
    refresh,
    fetchOptionContracts, // Requires instrument_key
    fetchOptionChain, // Requires instrument_key and expiry_date
    fetchFuturesData, // Requires instrument_key
    // Removed resolveInstrumentKey
    // Removed checkFNOEligibility
    // Helpers
    getLivePrice,
    getLivePriceData,
    getOptionData,
    getATMStrikes,
    getOptionMetrics,
    // Computed values
    allInstrumentKeys: getAllInstrumentKeys,
    strikePrice: optionChainData?.strike_prices || [],
    totalStrikes: optionChainData?.total_strikes || 0,
    totalExpiries: optionChainData?.total_expiries || 0,
  };
};

export default useOptionChain;
