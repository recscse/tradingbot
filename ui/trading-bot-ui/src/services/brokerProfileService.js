// services/brokerProfileService.js
import api from "./api";

class BrokerProfileService {
  constructor() {
    this.baseURL = "/v1/broker-profile";
  }

  /**
   * Get user profile for a specific broker
   * @param {string} brokerName - Broker name (upstox, angel, dhan)
   * @returns {Promise<Object>} Broker profile data
   */
  async getBrokerProfile(brokerName) {
    try {
      const response = await api.get(
        `${this.baseURL}/profile/${brokerName.toLowerCase()}`
      );
      return response.data;
    } catch (error) {
      console.error(`Error fetching ${brokerName} profile:`, error);
      throw this.handleError(error, `Failed to fetch ${brokerName} profile`);
    }
  }

  /**
   * Get funds and margin for a specific broker
   * @param {string} brokerName - Broker name
   * @param {string} segment - Optional segment (SEC for equity, COM for commodity)
   * @returns {Promise<Object>} Funds and margin data
   */
  async getBrokerFunds(brokerName, segment = null) {
    try {
      const params = segment ? { segment } : {};
      const response = await api.get(
        `${this.baseURL}/funds/${brokerName.toLowerCase()}`,
        { params }
      );
      return response.data;
    } catch (error) {
      console.error(`Error fetching ${brokerName} funds:`, error);
      throw this.handleError(error, `Failed to fetch ${brokerName} funds`);
    }
  }

  /**
   * Get profiles for all active brokers
   * @returns {Promise<Object>} All broker profiles
   */
  async getAllBrokerProfiles() {
    try {
      const response = await api.get(`${this.baseURL}/profile/all`);
      return response.data;
    } catch (error) {
      console.error("Error fetching all broker profiles:", error);
      throw this.handleError(error, "Failed to fetch broker profiles");
    }
  }

  /**
   * Get combined funds summary across all brokers
   * @returns {Promise<Object>} Combined funds summary
   */
  async getCombinedFundsSummary() {
    try {
      const response = await api.get(`${this.baseURL}/funds-summary`);
      return response.data;
    } catch (error) {
      console.error("Error fetching combined funds summary:", error);
      throw this.handleError(error, "Failed to fetch funds summary");
    }
  }

  /**
   * Get list of supported brokers
   * @returns {Promise<Object>} Supported brokers info
   */
  async getSupportedBrokers() {
    try {
      const response = await api.get(`${this.baseURL}/supported-brokers`);
      return response.data;
    } catch (error) {
      console.error("Error fetching supported brokers:", error);
      throw this.handleError(error, "Failed to fetch supported brokers");
    }
  }

  /**
   * Get Upstox profile (backward compatibility)
   * @returns {Promise<Object>} Upstox profile
   */
  async getUpstoxProfile() {
    return this.getBrokerProfile("upstox");
  }

  /**
   * Get Upstox funds (backward compatibility)
   * @param {string} segment - Optional segment
   * @returns {Promise<Object>} Upstox funds
   */
  async getUpstoxFunds(segment = null) {
    return this.getBrokerFunds("upstox", segment);
  }

  /**
   * Format profile data for display
   * @param {Object} profileData - Raw profile data
   * @returns {Object} Formatted profile data
   */
  formatProfileData(profileData) {
    if (!profileData?.data?.data) return null;

    const data = profileData.data.data;
    return {
      email: data.email || "N/A",
      userId: data.user_id || "N/A",
      userName: data.user_name || "N/A",
      broker: data.broker || "N/A",
      userType: data.user_type || "individual",
      isActive: data.is_active || false,
      exchanges: data.exchanges || [],
      products: data.products || [],
      orderTypes: data.order_types || [],
      poa: data.poa || false,
      ddpi: data.ddpi || false,
      lastUpdated: profileData.last_updated,
    };
  }

  /**
   * Format funds data for display
   * @param {Object} fundsData - Raw funds data
   * @returns {Object} Formatted funds data
   */
  formatFundsData(fundsData) {
    if (!fundsData?.data?.data) return null;

    const data = fundsData.data.data;
    const equity = data.equity || {};
    const commodity = data.commodity || {};

    return {
      equity: {
        availableMargin: equity.available_margin || 0,
        usedMargin: equity.used_margin || 0,
        payinAmount: equity.payin_amount || 0,
        spanMargin: equity.span_margin || 0,
        adhocMargin: equity.adhoc_margin || 0,
        notionalCash: equity.notional_cash || 0,
        exposureMargin: equity.exposure_margin || 0,
        utilization:
          equity.available_margin > 0
            ? ((equity.used_margin / equity.available_margin) * 100).toFixed(2)
            : 0,
      },
      commodity: {
        availableMargin: commodity.available_margin || 0,
        usedMargin: commodity.used_margin || 0,
        payinAmount: commodity.payin_amount || 0,
        spanMargin: commodity.span_margin || 0,
        adhocMargin: commodity.adhoc_margin || 0,
        notionalCash: commodity.notional_cash || 0,
        exposureMargin: commodity.exposure_margin || 0,
        utilization:
          commodity.available_margin > 0
            ? (
                (commodity.used_margin / commodity.available_margin) *
                100
              ).toFixed(2)
            : 0,
      },
      segment: fundsData.segment,
      lastUpdated: fundsData.last_updated,
    };
  }

  /**
   * Format combined funds summary
   * @param {Object} summaryData - Raw summary data
   * @returns {Object} Formatted summary
   */
  formatCombinedSummary(summaryData) {
    if (!summaryData?.summary) return null;

    const summary = summaryData.summary;
    return {
      totalAvailable: summary.total_available_margin || 0,
      totalUsed: summary.total_used_margin || 0,
      utilization: summary.utilization_percentage || 0,
      brokerFunds: summaryData.broker_funds || {},
      lastUpdated: summaryData.last_updated,
    };
  }

  /**
   * Handle API errors consistently
   * @param {Object} error - Error object
   * @param {string} defaultMessage - Default error message
   * @returns {Error} Formatted error
   */
  handleError(error, defaultMessage) {
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail || defaultMessage;

      switch (status) {
        case 401:
          return new Error("Authentication required. Please login again.");
        case 404:
          return new Error(
            "Broker configuration not found. Please configure your broker."
          );
        case 400:
          return new Error(detail);
        case 500:
          return new Error("Server error. Please try again later.");
        default:
          return new Error(detail);
      }
    }

    return new Error(error.message || defaultMessage);
  }

  /**
   * Check if broker profile service is available
   * @param {string} brokerName - Broker name
   * @returns {Promise<boolean>} Service availability
   */
  async isBrokerSupported(brokerName) {
    try {
      const supportedBrokers = await this.getSupportedBrokers();
      const broker =
        supportedBrokers.supported_brokers?.[brokerName.toLowerCase()];
      return broker?.profile_supported || false;
    } catch (error) {
      console.error("Error checking broker support:", error);
      return false;
    }
  }

  /**
   * Cache keys for local storage
   */
  getCacheKey(type, brokerName = "", segment = "") {
    return `broker_${type}_${brokerName}_${segment}`.replace(/__+/g, "_");
  }

  /**
   * Cache profile data temporarily (5 minutes)
   * @param {string} brokerName - Broker name
   * @param {Object} data - Profile data
   */
  cacheProfile(brokerName, data) {
    const cacheKey = this.getCacheKey("profile", brokerName);
    const cacheData = {
      data,
      timestamp: Date.now(),
      expiry: Date.now() + 5 * 60 * 1000, // 5 minutes
    };

    try {
      localStorage.setItem(cacheKey, JSON.stringify(cacheData));
    } catch (error) {
      console.warn("Failed to cache profile data:", error);
    }
  }

  /**
   * Get cached profile data if valid
   * @param {string} brokerName - Broker name
   * @returns {Object|null} Cached data or null
   */
  getCachedProfile(brokerName) {
    const cacheKey = this.getCacheKey("profile", brokerName);

    try {
      const cachedData = localStorage.getItem(cacheKey);
      if (!cachedData) return null;

      const parsed = JSON.parse(cachedData);
      if (Date.now() > parsed.expiry) {
        localStorage.removeItem(cacheKey);
        return null;
      }

      return parsed.data;
    } catch (error) {
      console.warn("Failed to get cached profile data:", error);
      return null;
    }
  }
}

// Export singleton instance
const brokerProfileService = new BrokerProfileService();
export default brokerProfileService;
