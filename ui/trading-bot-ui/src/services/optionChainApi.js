// services/optionChainApi.js - Option Chain API Client

class OptionChainAPI {
  constructor() {
    const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    this.baseURL = `${BASE_URL}/api/v1/options`;
  }

  // Get auth headers
  getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  // Handle API response
  async handleResponse(response) {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      
      if (response.status === 401) {
        throw new Error('Authentication required. Please login again.');
      }
      
      if (response.status === 400) {
        throw new Error(errorData.detail || 'Invalid request');
      }
      
      if (response.status === 404) {
        throw new Error(errorData.detail || 'Resource not found');
      }
      
      throw new Error(errorData.detail || `API Error: ${response.statusText}`);
    }
    
    return response.json();
  }

  // Get F&O eligible instruments
  async getFNOInstruments() {
    try {
      const response = await fetch(`${this.baseURL}/instruments`, {
        headers: this.getAuthHeaders()
      });
      
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error fetching F&O instruments:', error);
      throw error;
    }
  }

  // Check if symbol is F&O eligible
  async checkFNOEligibility(symbol) {
    try {
      const response = await fetch(`${this.baseURL}/check/${symbol}`, {
        headers: this.getAuthHeaders()
      });
      
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error checking F&O eligibility for ${symbol}:`, error);
      throw error;
    }
  }

  // Get option contracts for symbol
  async getOptionContracts(symbol) {
    try {
      const response = await fetch(`${this.baseURL}/contracts/${symbol}`, {
        headers: this.getAuthHeaders()
      });
      
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error fetching option contracts for ${symbol}:`, error);
      throw error;
    }
  }

  // Get option chain for symbol
  async getOptionChain(symbol, expiry = null) {
    try {
      let url = `${this.baseURL}/chain/${symbol}`;
      if (expiry) {
        url += `?expiry=${encodeURIComponent(expiry)}`;
      }
      
      const response = await fetch(url, {
        headers: this.getAuthHeaders()
      });
      
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error fetching option chain for ${symbol}:`, error);
      throw error;
    }
  }

  // Get futures contracts for symbol
  async getFuturesContracts(symbol) {
    try {
      const response = await fetch(`${this.baseURL}/futures/${symbol}`, {
        headers: this.getAuthHeaders()
      });
      
      return this.handleResponse(response);
    } catch (error) {
      console.error(`Error fetching futures contracts for ${symbol}:`, error);
      throw error;
    }
  }

  // Clear option service cache (admin only)
  async clearCache() {
    try {
      const response = await fetch(`${this.baseURL}/cache/clear`, {
        method: 'POST',
        headers: this.getAuthHeaders()
      });
      
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error clearing option cache:', error);
      throw error;
    }
  }

  // Get option service health
  async getHealth() {
    try {
      const response = await fetch(`${this.baseURL}/health`, {
        headers: this.getAuthHeaders()
      });
      
      return this.handleResponse(response);
    } catch (error) {
      console.error('Error checking option service health:', error);
      throw error;
    }
  }

  // Batch operations
  async getCompleteOptionData(symbol, expiry = null) {
    try {
      const [optionChain, futuresData] = await Promise.all([
        this.getOptionChain(symbol, expiry),
        this.getFuturesContracts(symbol)
      ]);

      return {
        optionChain,
        futures: futuresData.futures || [],
        symbol,
        expiry,
        retrievedAt: new Date().toISOString()
      };
    } catch (error) {
      console.error(`Error fetching complete option data for ${symbol}:`, error);
      throw error;
    }
  }

  // Helper methods for data processing
  processOptionChainData(optionChain) {
    if (!optionChain || !optionChain.options) return null;

    const processed = {
      ...optionChain,
      strikeMap: {},
      expiryMap: {},
      callStrikes: [],
      putStrikes: []
    };

    // Process options by strike and expiry
    Object.entries(optionChain.options).forEach(([strike, optionData]) => {
      const strikePrice = parseFloat(strike);
      
      processed.strikeMap[strike] = optionData;
      
      Object.entries(optionData).forEach(([optionType, contract]) => {
        const expiry = contract.expiry;
        
        if (!processed.expiryMap[expiry]) {
          processed.expiryMap[expiry] = {};
        }
        
        if (!processed.expiryMap[expiry][strike]) {
          processed.expiryMap[expiry][strike] = {};
        }
        
        processed.expiryMap[expiry][strike][optionType] = contract;
        
        if (optionType === 'CE') {
          processed.callStrikes.push(strikePrice);
        } else if (optionType === 'PE') {
          processed.putStrikes.push(strikePrice);
        }
      });
    });

    // Sort strikes
    processed.callStrikes = [...new Set(processed.callStrikes)].sort((a, b) => a - b);
    processed.putStrikes = [...new Set(processed.putStrikes)].sort((a, b) => a - b);

    return processed;
  }

  // Calculate option metrics
  calculateOptionMetrics(optionChain, livePrices = {}) {
    if (!optionChain || !optionChain.options) return null;

    const spotPrice = optionChain.spot_price;
    let totalCallOI = 0;
    let totalPutOI = 0;
    let totalCallVolume = 0;
    let totalPutVolume = 0;
    let totalCallValue = 0;
    let totalPutValue = 0;

    Object.entries(optionChain.options).forEach(([strike, options]) => {
      const callOption = options.CE;
      const putOption = options.PE;
      
      if (callOption) {
        const callLTP = livePrices[callOption.instrument_key]?.ltp || 0;
        const callOI = callOption.open_interest || 0;
        const callVolume = livePrices[callOption.instrument_key]?.volume || 0;
        
        totalCallOI += callOI;
        totalCallVolume += callVolume;
        totalCallValue += callLTP * callOI;
      }
      
      if (putOption) {
        const putLTP = livePrices[putOption.instrument_key]?.ltp || 0;
        const putOI = putOption.open_interest || 0;
        const putVolume = livePrices[putOption.instrument_key]?.volume || 0;
        
        totalPutOI += putOI;
        totalPutVolume += putVolume;
        totalPutValue += putLTP * putOI;
      }
    });

    return {
      totalCallOI,
      totalPutOI,
      putCallRatio: totalCallOI > 0 ? totalPutOI / totalCallOI : 0,
      totalCallVolume,
      totalPutVolume,
      volumeRatio: totalCallVolume > 0 ? totalPutVolume / totalCallVolume : 0,
      totalCallValue,
      totalPutValue,
      valueRatio: totalCallValue > 0 ? totalPutValue / totalCallValue : 0,
      spotPrice,
      calculatedAt: new Date().toISOString()
    };
  }

  // Find ATM strikes
  findATMStrikes(strikes, spotPrice, range = 5) {
    if (!strikes || !spotPrice) return [];
    
    const sortedStrikes = [...strikes].sort((a, b) => a - b);
    const closestStrike = sortedStrikes.reduce((prev, curr) => 
      Math.abs(curr - spotPrice) < Math.abs(prev - spotPrice) ? curr : prev
    );
    
    const closestIndex = sortedStrikes.indexOf(closestStrike);
    const startIndex = Math.max(0, closestIndex - range);
    const endIndex = Math.min(sortedStrikes.length - 1, closestIndex + range);
    
    return sortedStrikes.slice(startIndex, endIndex + 1);
  }
}

// Create singleton instance
const optionChainAPI = new OptionChainAPI();

export default optionChainAPI;

// Named exports for convenience
export const {
  getFNOInstruments,
  checkFNOEligibility,
  getOptionContracts,
  getOptionChain,
  getFuturesContracts,
  clearCache,
  getHealth,
  getCompleteOptionData,
  processOptionChainData,
  calculateOptionMetrics,
  findATMStrikes
} = optionChainAPI;