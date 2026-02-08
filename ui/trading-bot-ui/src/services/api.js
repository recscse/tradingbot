import axios from "axios";
import {
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  clearTokens,
} from "../services/authService";

const BASE_URL = process.env.REACT_APP_API_URL;

// ✅ Automatically add `/api/` to all API calls
const apiClient = axios.create({
  baseURL: `${BASE_URL}/api`, // 👈 Now all requests will start with /api
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // ✅ Required for CORS authentication
});

// ✅ Attach access token to API requests
apiClient.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ✅ Prevent multiple refresh requests at the same time
let isRefreshing = false;
let refreshSubscribers = [];

const onTokenRefreshed = (newToken) => {
  refreshSubscribers.forEach((callback) => callback(newToken));
  refreshSubscribers = [];
};

const addRefreshSubscriber = (callback) => {
  refreshSubscribers.push(callback);
};

// ✅ Handle 401 Unauthorized and refresh token automatically
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    console.error("📌 Axios Error:", error);

    if (!error.response) {
      console.error("🚨 Network Error: Server Unreachable");
      return Promise.reject({
        code: "ERR_NETWORK",
        message:
          "Unable to connect to the server. Please check your internet or backend server.",
      });
    }

    const originalRequest = error.config;

    if (
      error.response.status === 401 &&
      error.response.data?.code === "token_expired"
    ) {
      console.warn("🚨 Access token expired, attempting to refresh...");

      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((newToken) => {
            originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
            resolve(apiClient(originalRequest));
          });
        });
      }

      isRefreshing = true;
      const refreshToken = getRefreshToken();

      if (!refreshToken) {
        console.error("❌ Refresh token missing, logging out user.");
        clearTokens();
        window.location.href = "/";
        return Promise.reject(error);
      }

      try {
        const refreshResponse = await axios.post(
          `${BASE_URL}/api/auth/refresh-token`,
          {},
          {
            headers: {
              "Refresh-Token": refreshToken,
              "Content-Type": "application/json",
            },
            credentials: "include",
          }
        );

        if (refreshResponse.status === 200) {
          const newAccessToken = refreshResponse.data.access_token;
          console.log("🔄 Token refreshed successfully");

          setAccessToken(newAccessToken);
          isRefreshing = false;

          // Notify all subscribers about the new token
          onTokenRefreshed(newAccessToken);

          // ✅ Retry the failed request with the new token
          originalRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
          return apiClient(originalRequest);
        } else {
          throw new Error("Refresh token invalid");
        }
      } catch (refreshError) {
        console.error("❌ Token refresh failed:", refreshError);
        clearTokens();
        window.location.href = "/";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
