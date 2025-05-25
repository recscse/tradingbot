// services/googleAuthService.js
// Using Google Identity Services (GIS) - the modern approach

class GoogleAuthService {
  constructor() {
    this.isInitialized = false;
    this.clientId = null;
    this.tokenClient = null;
    this.debugEnvironment();
  }

  // Debug method to check environment variables
  debugEnvironment() {
    console.log("🔍 Debugging Environment Variables:");
    console.log("NODE_ENV:", process.env.NODE_ENV);
    console.log(
      "REACT_APP_GOOGLE_CLIENT_ID exists:",
      !!process.env.REACT_APP_GOOGLE_CLIENT_ID
    );
    console.log(
      "REACT_APP_GOOGLE_CLIENT_ID value (first 20 chars):",
      process.env.REACT_APP_GOOGLE_CLIENT_ID
        ? process.env.REACT_APP_GOOGLE_CLIENT_ID.substring(0, 20) + "..."
        : "undefined"
    );
  }

  // Validate client ID
  validateClientId() {
    this.clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;

    if (!this.clientId) {
      console.error("❌ Google Client ID not found in environment variables");
      console.log(
        "📝 Make sure REACT_APP_GOOGLE_CLIENT_ID is set in your .env file"
      );
      return false;
    }

    if (
      this.clientId.length < 50 ||
      !this.clientId.includes(".apps.googleusercontent.com")
    ) {
      console.error("❌ Invalid Google Client ID format");
      console.log(
        "Expected format: xxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
      );
      console.log("Received:", this.clientId);
      return false;
    }

    console.log("✅ Google Client ID validated successfully");
    return true;
  }

  // Initialize Google Identity Services
  async initializeGoogleAuth() {
    return new Promise((resolve, reject) => {
      if (!this.validateClientId()) {
        reject(
          new Error(
            "Invalid or missing Google Client ID. Please check your .env file."
          )
        );
        return;
      }

      if (this.isInitialized) {
        resolve();
        return;
      }

      // Load Google Identity Services script
      if (!window.google?.accounts) {
        const script = document.createElement("script");
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;

        script.onload = () => {
          console.log("📦 Google Identity Services script loaded");
          this.setupGoogleAuth().then(resolve).catch(reject);
        };

        script.onerror = () => {
          reject(new Error("Failed to load Google Identity Services script"));
        };

        document.head.appendChild(script);
      } else {
        this.setupGoogleAuth().then(resolve).catch(reject);
      }
    });
  }

  // Setup Google Auth using the new Identity Services
  async setupGoogleAuth() {
    try {
      // Initialize the token client for OAuth2
      this.tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: this.clientId,
        scope: "profile email openid",
        callback: (response) => {
          console.log("🔐 OAuth2 token received:", response);
        },
      });

      this.isInitialized = true;
      console.log("✅ Google Identity Services initialized successfully");
    } catch (error) {
      console.error("❌ Failed to setup Google Auth:", error);
      throw error;
    }
  }

  // FIXED: Enhanced sign in with popup
  async signInWithPopup() {
    return new Promise(async (resolve, reject) => {
      try {
        if (!this.isInitialized) {
          await this.initializeGoogleAuth();
        }

        // Create a timeout to handle cases where user doesn't respond
        const timeout = setTimeout(() => {
          reject(new Error("Google sign-in timeout"));
        }, 60000); // 60 seconds timeout

        // Request access token
        this.tokenClient.callback = async (response) => {
          clearTimeout(timeout);

          if (response.error) {
            console.error("❌ OAuth2 error:", response);

            // Handle specific error cases
            if (response.error === "popup_closed_by_user") {
              reject(new Error("Sign-in cancelled by user"));
            } else if (response.error === "access_denied") {
              reject(new Error("Access denied by user"));
            } else {
              reject(new Error(response.error_description || response.error));
            }
            return;
          }

          try {
            // Get user info using the access token
            const userInfo = await this.getUserInfo(response.access_token);

            resolve({
              success: true,
              accessToken: response.access_token,
              tokenType: "access_token",
              user: {
                id: userInfo.id,
                name: userInfo.name,
                email: userInfo.email,
                imageUrl: userInfo.picture,
                verified_email: userInfo.verified_email,
              },
            });
          } catch (error) {
            reject(error);
          }
        };

        // Request the token with proper error handling
        try {
          this.tokenClient.requestAccessToken({
            prompt: "consent",
            hint: "select_account", // Allow account selection
          });
        } catch (requestError) {
          clearTimeout(timeout);
          reject(new Error("Failed to initiate Google sign-in"));
        }
      } catch (error) {
        console.error("❌ Sign-in initialization error:", error);
        reject(error);
      }
    });
  }

  // ENHANCED: Better One Tap implementation
  async signInWithOneTap() {
    return new Promise((resolve, reject) => {
      if (!this.isInitialized) {
        this.initializeGoogleAuth()
          .then(() => {
            this.setupOneTap(resolve, reject);
          })
          .catch(reject);
      } else {
        this.setupOneTap(resolve, reject);
      }
    });
  }

  setupOneTap(resolve, reject) {
    try {
      window.google.accounts.id.initialize({
        client_id: this.clientId,
        callback: async (response) => {
          try {
            // Decode the JWT credential
            const userInfo = this.parseJwt(response.credential);

            resolve({
              success: true,
              idToken: response.credential,
              tokenType: "id_token",
              user: {
                id: userInfo.sub,
                name: userInfo.name,
                email: userInfo.email,
                imageUrl: userInfo.picture,
                verified_email: userInfo.email_verified,
              },
            });
          } catch (error) {
            reject(error);
          }
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      // Display the One Tap prompt with timeout
      const promptTimeout = setTimeout(() => {
        console.log("One Tap prompt timeout, falling back to popup");
        this.signInWithPopup().then(resolve).catch(reject);
      }, 5000);

      window.google.accounts.id.prompt((notification) => {
        clearTimeout(promptTimeout);

        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          console.log(
            "One Tap prompt not displayed:",
            notification.getNotDisplayedReason()
          );
          // Fallback to popup
          this.signInWithPopup().then(resolve).catch(reject);
        }
      });
    } catch (error) {
      reject(error);
    }
  }

  // Enhanced user info fetching with retry
  async getUserInfo(accessToken, retries = 3) {
    for (let i = 0; i < retries; i++) {
      try {
        const response = await fetch(
          "https://www.googleapis.com/oauth2/v2/userinfo",
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch user info: ${response.status}`);
        }

        return await response.json();
      } catch (error) {
        if (i === retries - 1) throw error;
        await new Promise((resolve) => setTimeout(resolve, 1000 * (i + 1))); // Exponential backoff
      }
    }
  }

  // Parse JWT token with better error handling
  parseJwt(token) {
    try {
      const base64Url = token.split(".")[1];
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map(function (c) {
            return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
          })
          .join("")
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error("Failed to parse JWT token:", error);
      throw new Error("Invalid JWT token format");
    }
  }

  // Enhanced sign out
  async signOut() {
    try {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.disableAutoSelect();
      }

      // Also revoke the token if we have it
      const token = localStorage.getItem("google_access_token");
      if (token) {
        try {
          await fetch(`https://oauth2.googleapis.com/revoke?token=${token}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/x-www-form-urlencoded",
            },
          });
        } catch (revokeError) {
          console.warn("Failed to revoke Google token:", revokeError);
        }
        localStorage.removeItem("google_access_token");
      }

      console.log("✅ Google Sign-Out successful");
      return { success: true };
    } catch (error) {
      console.error("❌ Google Sign-Out Error:", error);
      return { success: false, error: error.message };
    }
  }

  // ENHANCED: Main sign-in method with better strategy
  async signInWithGoogle() {
    try {
      console.log("🚀 Starting Google Sign-In process...");

      // For better user experience, go directly to popup
      // One Tap can be intrusive for some users
      return await this.signInWithPopup();
    } catch (error) {
      console.error("❌ Google Sign-In Error:", error);

      // Handle specific error cases with user-friendly messages
      if (
        error.message?.includes("popup_closed_by_user") ||
        error.message?.includes("cancelled by user")
      ) {
        return {
          success: false,
          error: "Sign-in was cancelled. Please try again.",
        };
      }

      if (error.message?.includes("access_denied")) {
        return {
          success: false,
          error: "Access was denied. Please allow permissions to continue.",
        };
      }

      if (error.message?.includes("timeout")) {
        return {
          success: false,
          error: "Sign-in timed out. Please try again.",
        };
      }

      return {
        success: false,
        error: error.message || "Google sign-in failed. Please try again.",
      };
    }
  }
}

const googleAuthService = new GoogleAuthService();

export default googleAuthService;
