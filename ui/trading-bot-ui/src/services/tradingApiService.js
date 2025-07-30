import axios from "axios";
import io from "socket.io-client";

class TradingApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || "http://localhost:8000";
    this.socket = null;

    // Setup axios instance with your existing auth
    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: 10000,
    });

    // Add your existing auth interceptors
    this.setupInterceptors();
  }

  setupInterceptors() {
    // Request interceptor for auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("authToken");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle auth errors with your existing auth system
          this.handleAuthError();
        }
        return Promise.reject(error);
      }
    );
  }

  handleAuthError() {
    // Integrate with your existing auth system
    console.log("Auth error - redirecting to login");
    // window.location.href = '/login';
  }

  // Market Analytics API Methods
  async getTopMovers(limit = 20) {
    const response = await this.api.get(
      `/api/analytics/top-movers?limit=${limit}`
    );
    return response.data;
  }

  async getVolumeAnalysis(limit = 50) {
    const response = await this.api.get(
      `/api/analytics/volume-analysis?limit=${limit}`
    );
    return response.data;
  }

  async getMarketSentiment() {
    const response = await this.api.get("/api/analytics/market-sentiment");
    return response.data;
  }

  async getSectorHeatmap(
    sizeMetric = "market_cap",
    colorMetric = "change_percent"
  ) {
    const response = await this.api.get(
      `/api/analytics/heatmap/sector?size_metric=${sizeMetric}&color_metric=${colorMetric}`
    );
    return response.data;
  }

  async getIntradayStocks(minChange = 2.0, minVolume = 100000, limit = 50) {
    const response = await this.api.get(
      `/api/analytics/intraday-stocks?min_change=${minChange}&min_volume=${minVolume}&limit=${limit}`
    );
    return response.data;
  }

  async getMarketOverview() {
    const response = await this.api.get("/api/analytics/market-overview");
    return response.data;
  }

  async getDashboardLiveData() {
    const response = await this.api.get("/api/dashboard/live-data");
    return response.data;
  }

  async getLiveHeatmapData(
    viewType = "sector",
    sizeMetric = "market_cap",
    colorMetric = "change_percent"
  ) {
    const response = await this.api.get(
      `/api/heatmap/live?view_type=${viewType}&size_metric=${sizeMetric}&color_metric=${colorMetric}`
    );
    return response.data;
  }

  // WebSocket Methods
  connectAnalyticsWebSocket() {
    if (this.socket) {
      this.socket.disconnect();
    }

    this.socket = io(this.baseURL, {
      transports: ["websocket", "polling"],
      timeout: 5000,
    });

    return this.socket;
  }

  subscribeToAnalytics(callback) {
    if (!this.socket) {
      this.connectAnalyticsWebSocket();
    }

    this.socket.emit("subscribe_to_analytics", {});
    this.socket.on("analytics_update", callback);
    this.socket.on("analytics_error", (error) => {
      console.error("Analytics WebSocket error:", error);
    });
  }

  disconnectWebSocket() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

export const tradingApiService = new TradingApiService();
