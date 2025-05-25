// services/authService.js
import GoogleAuthService from "./googleAuthService";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// ✅ Enhanced error message formatting
const formatErrorMessage = (errorData, statusCode) => {
  console.log("🔍 Formatting error:", { errorData, statusCode });

  // Handle string errors
  if (typeof errorData === "string") {
    return errorData;
  }

  // Handle object errors with different formats
  if (typeof errorData === "object" && errorData !== null) {
    // Check for our backend's standard format
    if (errorData.message) {
      return errorData.message;
    }

    // Handle FastAPI validation errors
    if (errorData.detail) {
      if (Array.isArray(errorData.detail)) {
        return errorData.detail
          .map((err) => {
            if (typeof err === "string") return err;
            if (err.msg) return `${err.loc?.join(".") || "Field"}: ${err.msg}`;
            return "Validation error";
          })
          .join(", ");
      } else if (typeof errorData.detail === "string") {
        return errorData.detail;
      }
    }

    // Handle validation errors array
    if (errorData.errors && Array.isArray(errorData.errors)) {
      return errorData.errors
        .map((err) => {
          if (typeof err === "string") return err;
          return err.msg || err.message || "Validation error";
        })
        .join(", ");
    }
  }

  // Handle specific status codes
  switch (statusCode) {
    case 422:
      return "Invalid data provided. Please check your input.";
    case 401:
      return "Authentication failed. Please check your credentials.";
    case 403:
      return "Access denied. Please verify your account.";
    case 404:
      return "Resource not found.";
    case 500:
      return "Server error. Please try again later.";
    default:
      return "An unexpected error occurred. Please try again.";
  }
};

// ✅ Enhanced API response handler
const handleApiResponse = async (response) => {
  try {
    let data;
    const contentType = response.headers.get("content-type");

    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = { message: text };
    }

    console.log("🔍 Raw API Response:", {
      status: response.status,
      statusText: response.statusText,
      data: data,
    });

    if (!response.ok) {
      console.error("❌ API Error Response:", {
        status: response.status,
        statusText: response.statusText,
        data: data,
      });

      return {
        success: false,
        message: formatErrorMessage(data, response.status),
        errors: data?.errors || [],
        status: response.status,
        rawData: data,
      };
    }

    // Success response
    return {
      success: true,
      ...data,
    };
  } catch (error) {
    console.error("❌ Failed to parse API response:", error);
    return {
      success: false,
      message: "Invalid server response",
      error: error.message,
    };
  }
};

// ✅ Enhanced API call helper
const apiCall = async (endpoint, options = {}) => {
  try {
    const defaultHeaders = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };

    // Add auth token if available
    const token = getAccessToken();
    if (token) {
      defaultHeaders.Authorization = `Bearer ${token}`;
    }

    console.log(`📤 Making API call to: ${API_URL}${endpoint}`, {
      method: options.method || "GET",
      hasToken: !!token,
    });

    const response = await fetch(`${API_URL}${endpoint}`, {
      headers: { ...defaultHeaders, ...options.headers },
      ...options,
    });

    return await handleApiResponse(response);
  } catch (error) {
    console.error("❌ API call failed:", error);
    return {
      success: false,
      message: "Network error. Please check your connection.",
      error: error.message,
    };
  }
};

// ✅ Enhanced Signup Function
export const signup = async (userData) => {
  try {
    console.log("📝 Attempting signup with data:", {
      ...userData,
      password: "[HIDDEN]",
    });

    const response = await apiCall("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(userData),
    });

    console.log("✅ Signup response:", response);
    return response;
  } catch (error) {
    console.error("❌ Signup error:", error);
    throw error;
  }
};

// ✅ Enhanced Login Function
export const login = async (credentials) => {
  try {
    console.log("🔐 Login attempt:", { email: credentials.email });

    const result = await apiCall("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: credentials.email,
        password: credentials.password,
      }),
    });

    console.log("🔍 Login result:", result);

    // Store tokens if login successful
    if (result.success && result.access_token) {
      localStorage.setItem("access_token", result.access_token);
      if (result.refresh_token) {
        localStorage.setItem("refresh_token", result.refresh_token);
      }
      if (result.user) {
        localStorage.setItem("userData", JSON.stringify(result.user));
      }
      localStorage.setItem("isLoggedIn", "true");

      // Trigger storage event for other components
      window.dispatchEvent(new Event("storage"));
    }

    return result;
  } catch (error) {
    console.error("❌ Login error:", error);
    return {
      success: false,
      message: "Network error. Please try again later.",
    };
  }
};

// ✅ Enhanced OTP Verification
export const verifyOtp = async (phone, countryCode, otp) => {
  try {
    console.log("📱 SMS OTP verification:", {
      phone: `${countryCode}${phone}`,
    });

    const result = await apiCall("/api/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify({
        phone_number: phone,
        country_code: countryCode,
        otp: otp,
      }),
    });

    console.log("🔍 SMS OTP result:", result);
    return result;
  } catch (error) {
    console.error("❌ OTP verification error:", error);
    return {
      success: false,
      message: "Network error. Please try again later.",
    };
  }
};

// ✅ Enhanced Resend OTP
export const resendOtp = async (phone_number, country_code) => {
  try {
    const result = await apiCall("/api/auth/resend-otp", {
      method: "POST",
      body: JSON.stringify({ phone_number, country_code }),
    });

    return result;
  } catch (error) {
    console.error("❌ Resend OTP Error:", error);
    return { success: false, message: "Failed to resend OTP" };
  }
};

// ✅ Enhanced Google Authentication
export const handleGoogleAuth = async (isSignup = false) => {
  try {
    console.log("🚀 Starting Google authentication...", { isSignup });

    // Get Google auth result
    const googleResult = await GoogleAuthService.signInWithGoogle();

    if (!googleResult || !googleResult.success) {
      console.log("❌ Google sign-in failed:", googleResult);
      return {
        success: false,
        message: googleResult?.error || "Google authentication failed",
      };
    }

    console.log("✅ Google sign-in successful, sending to backend...");

    // Prepare payload for backend
    const payload = {
      token: googleResult.idToken || googleResult.accessToken,
      tokenType: googleResult.idToken ? "id_token" : "access_token",
      user: {
        id: googleResult.user.id,
        name: googleResult.user.name,
        email: googleResult.user.email,
        imageUrl: googleResult.user.imageUrl,
      },
      isSignUp: isSignup,
    };

    console.log("📤 Sending to backend:", {
      endpoint: isSignup ? "/api/auth/google/signup" : "/api/auth/google/login",
      tokenType: payload.tokenType,
      userEmail: payload.user.email,
      isSignUp: payload.isSignUp,
    });

    // Try the appropriate endpoint
    let endpoint = isSignup
      ? "/api/auth/google/signup"
      : "/api/auth/google/login";
    let backendResult = await apiCall(endpoint, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    console.log("🔍 Backend result:", backendResult);

    // Handle fallback from login to signup
    const shouldTrySignup =
      !backendResult.success &&
      !isSignup &&
      (backendResult.message?.toLowerCase().includes("user not found") ||
        backendResult.message?.toLowerCase().includes("please sign up first") ||
        backendResult.rawData?.message
          ?.toLowerCase()
          .includes("user not found"));

    if (shouldTrySignup) {
      console.log("🔄 TRIGGERING FALLBACK: User not found, trying signup...");

      payload.isSignUp = true;
      backendResult = await apiCall("/api/auth/google/signup", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      console.log("🔍 Signup fallback result:", backendResult);
    }

    if (backendResult.success) {
      console.log("✅ Backend Google auth successful");

      // Store tokens and user data
      if (backendResult.access_token) {
        localStorage.setItem("access_token", backendResult.access_token);
      }

      if (backendResult.refresh_token) {
        localStorage.setItem("refresh_token", backendResult.refresh_token);
      }

      if (backendResult.user) {
        localStorage.setItem("userData", JSON.stringify(backendResult.user));
      }

      localStorage.setItem("isLoggedIn", "true");
      window.dispatchEvent(new Event("storage"));

      return {
        success: true,
        user: backendResult.user,
        token: backendResult.access_token,
        message: backendResult.message || "Google authentication successful",
      };
    } else {
      console.log("❌ Final backend result failed:", backendResult);
      return {
        success: false,
        message: backendResult.message || "Backend authentication failed",
        suggest_signup: backendResult.suggest_signup,
      };
    }
  } catch (error) {
    console.error("❌ Google auth error:", error);
    return {
      success: false,
      message: error.message || "Google authentication failed",
    };
  }
};

// ✅ Enhanced Token Refresh
export const refreshAccessToken = async () => {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    console.warn("No refresh token found.");
    return null;
  }

  try {
    const response = await fetch(`${API_URL}/api/auth/refresh-token`, {
      method: "POST",
      headers: {
        "Refresh-Token": refreshToken,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.warn("Refresh token failed.");
      return null;
    }

    const data = await response.json();
    setAccessToken(data.access_token);
    return data.access_token;
  } catch (error) {
    console.error("Token refresh error:", error);
    return null;
  }
};

// ✅ Enhanced Logout Function
export const logout = async () => {
  try {
    // Call backend logout if needed
    await apiCall("/api/auth/logout", {
      method: "POST",
    });

    // Clear local storage regardless of backend response
    clearTokens();
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("userData");

    // Sign out from Google
    await GoogleAuthService.signOut();

    console.log("✅ Logout successful");
    window.location.href = "/";
    return { success: true };
  } catch (error) {
    console.error("❌ Logout error:", error);

    // Still clear local storage even if logout call fails
    clearTokens();
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("userData");

    window.location.href = "/";
    return { success: false, message: error.message };
  }
};

// ✅ Token Management Functions
export const getAccessToken = () => localStorage.getItem("access_token");
export const getRefreshToken = () => localStorage.getItem("refresh_token");

export const setAccessToken = (token) =>
  localStorage.setItem("access_token", token);
export const setRefreshToken = (token) =>
  localStorage.setItem("refresh_token", token);

export const clearTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};

// ✅ Authentication Check
export const isAuthenticated = () => {
  const token = getAccessToken();
  return !!token;
};

// ✅ Get Current User Data
export const getCurrentUser = () => {
  try {
    const userData = localStorage.getItem("userData");
    return userData ? JSON.parse(userData) : null;
  } catch (error) {
    console.error("Error parsing user data:", error);
    return null;
  }
};

// ✅ API Request with Authentication & Auto Token Refresh
export const fetchWithAuth = async (url, options = {}) => {
  try {
    const token = getAccessToken();
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });

    if (response.status === 401) {
      console.warn("🔄 Access token expired! Refreshing...");
      const newToken = await refreshAccessToken();
      if (!newToken) {
        console.error("❌ Token refresh failed");
        logout();
        return null;
      }

      // Retry the request with new token
      return fetch(url, {
        ...options,
        headers: {
          ...headers,
          Authorization: `Bearer ${newToken}`,
        },
        credentials: "include",
      });
    }

    return response.json();
  } catch (error) {
    console.error("❌ API request failed:", error);
    return null;
  }
};

export const verifyEmailOTP = async (email, otp) => {
  try {
    console.log("📧 Verifying email OTP for:", email);

    const result = await apiCall("/api/auth/verify-email-otp", {
      method: "POST",
      body: JSON.stringify({ email, otp }),
    });

    console.log("🔍 Verify email OTP result:", result);
    return result;
  } catch (error) {
    console.error("❌ Verify email OTP error:", error);
    return {
      success: false,
      message: "Failed to verify email OTP. Please try again.",
    };
  }
};

// ✅ WhatsApp OTP Functions
export const sendWhatsAppOTP = async (phoneNumber, countryCode = "+1") => {
  try {
    console.log("📱 Sending WhatsApp OTP to:", `${countryCode}${phoneNumber}`);

    const result = await apiCall("/api/auth/send-whatsapp-otp", {
      method: "POST",
      body: JSON.stringify({
        phone_number: phoneNumber,
        country_code: countryCode,
      }),
    });

    console.log("🔍 Send WhatsApp OTP result:", result);
    return result;
  } catch (error) {
    console.error("❌ Send WhatsApp OTP error:", error);
    return {
      success: false,
      message: "Failed to send WhatsApp OTP. Please try again.",
    };
  }
};

export const verifyWhatsAppOTP = async (
  phoneNumber,
  otp,
  countryCode = "+1"
) => {
  try {
    console.log(
      "📱 Verifying WhatsApp OTP for:",
      `${countryCode}${phoneNumber}`
    );

    const result = await apiCall("/api/auth/verify-whatsapp-otp", {
      method: "POST",
      body: JSON.stringify({
        phone_number: phoneNumber,
        otp: otp,
        country_code: countryCode,
      }),
    });

    console.log("🔍 Verify WhatsApp OTP result:", result);
    return result;
  } catch (error) {
    console.error("❌ Verify WhatsApp OTP error:", error);
    return {
      success: false,
      message: "Failed to verify WhatsApp OTP. Please try again.",
    };
  }
};

// Add these new functions to your existing authService.js file

// Forgot Password Functions
export const forgotPassword = async (email) => {
  try {
    console.log("🔐 Sending password reset request for:", email);

    const response = await apiCall("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });

    console.log("📧 Forgot password response:", response);
    return response;
  } catch (error) {
    console.error("❌ Forgot password error:", error);
    throw error;
  }
};

export const verifyResetToken = async (email, token) => {
  try {
    console.log("🔍 Verifying reset token for:", email);

    const response = await apiCall("/api/auth/verify-reset-token", {
      method: "POST",
      body: JSON.stringify({
        email,
        token: token,
        otp: token, // Some backends might expect 'otp' instead of 'token'
      }),
    });

    console.log("✅ Reset token verification response:", response);
    return response;
  } catch (error) {
    console.error("❌ Reset token verification error:", error);
    throw error;
  }
};

export const resetPassword = async (email, newPassword, token) => {
  try {
    console.log("🔑 Resetting password for:", email);

    const response = await apiCall("/api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({
        email,
        new_password: newPassword,
        password: newPassword, // Some backends might expect 'password'
        token: token,
        reset_token: token, // Some backends might expect 'reset_token'
      }),
    });

    console.log("🎉 Password reset response:", response);
    return response;
  } catch (error) {
    console.error("❌ Password reset error:", error);
    throw error;
  }
};

// Enhanced Email OTP Functions for signup verification
export const sendEmailOTP = async (email) => {
  try {
    console.log("📧 Sending email OTP to:", email);

    const result = await apiCall("/api/auth/send-email-otp", {
      method: "POST",
      body: JSON.stringify({ email }),
    });

    console.log("🔍 Send email OTP result:", result);
    return result;
  } catch (error) {
    console.error("❌ Send email OTP error:", error);
    return {
      success: false,
      message: "Failed to send email OTP. Please try again.",
    };
  }
};

// Profile verification functions (for later use in profile settings)
export const sendPhoneVerification = async (phoneNumber, countryCode) => {
  try {
    const response = await apiCall("/api/auth/send-phone-verification", {
      method: "POST",
      body: JSON.stringify({
        phone_number: phoneNumber,
        country_code: countryCode,
      }),
    });
    return response;
  } catch (error) {
    console.error("❌ Send phone verification error:", error);
    throw error;
  }
};

export const verifyPhone = async (phoneNumber, countryCode, otp) => {
  try {
    const response = await apiCall("/api/auth/verify-phone", {
      method: "POST",
      body: JSON.stringify({
        phone_number: phoneNumber,
        country_code: countryCode,
        otp,
      }),
    });
    return response;
  } catch (error) {
    console.error("❌ Phone verification error:", error);
    throw error;
  }
};

export const updateProfile = async (profileData) => {
  try {
    const response = await apiCall("/api/auth/profile", {
      method: "PUT",
      body: JSON.stringify(profileData),
    });

    if (response?.user) {
      localStorage.setItem("userData", JSON.stringify(response.user));
    }

    return response;
  } catch (error) {
    console.error("❌ Profile update error:", error);
    throw error;
  }
};
