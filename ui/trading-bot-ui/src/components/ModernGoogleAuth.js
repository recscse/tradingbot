// components/NewGoogleAuth.jsx - FIXED VERSION
import React, { useState, useEffect, useRef, useCallback } from "react";
import GoogleAuthService from "../services/googleAuthService";

const NewGoogleAuth = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");
  const [isInitialized, setIsInitialized] = useState(false);
  const buttonRef = useRef(null);

  // FIXED: Enhanced error handling for all backend error formats
  const handleError = (err) => {
    console.error("🔍 Auth error details:", err);

    let message = "An error occurred";

    try {
      if (typeof err === "string") {
        message = err;
      } else if (err?.message) {
        message = err.message;
      } else if (err?.error) {
        message = typeof err.error === "string" ? err.error : err.error.message;
      } else if (err?.detail) {
        // Handle FastAPI/Pydantic validation errors
        if (Array.isArray(err.detail)) {
          message = err.detail
            .map((error) => {
              if (typeof error === "string") return error;
              if (error.msg)
                return `${error.loc?.join(".") || "Field"}: ${error.msg}`;
              return "Validation error";
            })
            .join(", ");
        } else if (typeof err.detail === "string") {
          message = err.detail;
        }
      }
    } catch (parseError) {
      console.error("Error parsing error:", parseError);
      message = "An unexpected error occurred";
    }

    setError(message);
    console.error("📝 Final error message:", message);
  };

  // FIXED: Enhanced backend communication with proper error handling
  const sendToBackend = useCallback(async (authResult) => {
    try {
      const apiUrl =
        process.env.REACT_APP_API_URL || "http://localhost:8000/api";

      console.log("📤 Sending to backend:", {
        tokenType: authResult.tokenType,
        user: authResult.user,
        // Don't log the actual token for security
      });

      const payload = {
        token: authResult.idToken || authResult.accessToken,
        tokenType: authResult.tokenType || "id_token",
        user: authResult.user,
        isSignUp: false, // Adjust based on your flow
      };

      const response = await fetch(`${apiUrl}/auth/google/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json();
      console.log("🔍 Backend response:", {
        status: response.status,
        data: responseData,
      });

      if (!response.ok) {
        // Handle different error response formats
        if (response.status === 422) {
          // Handle validation errors (your backend format)
          if (responseData.errors && Array.isArray(responseData.errors)) {
            const messages = responseData.errors.map((err) => {
              if (typeof err === "string") return err;
              if (err.msg) return err.msg;
              if (err.message) return err.message;
              return "Validation error";
            });
            throw new Error(messages.join(", "));
          } else if (responseData.detail) {
            // FastAPI validation format
            throw new Error(responseData.detail);
          } else {
            throw new Error("Validation error occurred");
          }
        }

        // Handle other HTTP errors
        const errorMessage =
          responseData.message ||
          responseData.error ||
          responseData.detail ||
          `Server error (${response.status})`;
        throw new Error(errorMessage);
      }

      // Success - store token and user data
      if (responseData.access_token || responseData.token) {
        const token = responseData.access_token || responseData.token;
        localStorage.setItem("access_token", token);
        console.log("✅ Token stored successfully");
      }

      if (responseData.user) {
        localStorage.setItem("user_data", JSON.stringify(responseData.user));
        console.log("✅ User data stored successfully");
      }

      console.log("✅ Backend authentication successful");
    } catch (err) {
      console.error("❌ Backend error:", err);
      throw new Error(`Authentication failed: ${err.message}`);
    }
  }, []);

  // FIXED: Proper credential response handler
  const handleCredentialResponse = useCallback(async (response) => {
    setIsLoading(true);
    setError("");

    try {
      console.log("🔐 Received Google credential response");

      // Parse the JWT token
      const userInfo = GoogleAuthService.parseJwt(response.credential);

      const authResult = {
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
      };

      console.log("✅ Parsed user info:", authResult.user);

      setUser(authResult.user);
      await sendToBackend(authResult);
    } catch (err) {
    } finally {
      setIsLoading(false);
    }
  }, [sendToBackend]);

  // FIXED: Proper Google button setup with credential callback
  const setupGoogleButton = useCallback(() => {
    if (!window.google?.accounts?.id || !buttonRef.current) return;

    try {
      // Clear any existing button
      buttonRef.current.innerHTML = "";

      // Initialize with proper callback
      window.google.accounts.id.initialize({
        client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse, // Use our local callback
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      // Render the Google Sign-In button
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        type: "standard",
        text: "signin_with",
        shape: "rectangular",
        logo_alignment: "left",
        width: 280,
      });

      console.log("✅ Google button setup complete");
    } catch (err) {
      console.error("❌ Error setting up button:", err);
      handleError("Failed to setup Google button");
    }
  }, [handleCredentialResponse]);

  useEffect(() => {
    const initAuth = async () => {
      try {
        await GoogleAuthService.initializeGoogleAuth();
        setIsInitialized(true);
        setupGoogleButton();
      } catch (err) {
        handleError(err);
      }
    };
    initAuth();
  }, [setupGoogleButton]);

  // Alternative manual sign-in (using popup flow)
  const handleManualSignIn = async () => {
    setIsLoading(true);
    setError("");

    try {
      const result = await GoogleAuthService.signInWithGoogle();

      if (result?.success) {
        setUser(result.user);
        await sendToBackend(result);
      } else {
        handleError(result?.error || "Sign-in failed");
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignOut = async () => {
    setIsLoading(true);
    try {
      await GoogleAuthService.signOut();
      setUser(null);
      setError("");
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_data");

      // Re-setup the button for next sign-in
      setTimeout(setupGoogleButton, 100);

      console.log("✅ Sign out successful");
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state
  if (!isInitialized && !error) {
    return (
      <div
        style={{
          padding: "20px",
          textAlign: "center",
          border: "1px solid #e0e0e0",
          borderRadius: "8px",
          backgroundColor: "#f9f9f9",
        }}
      >
        <div style={{ fontSize: "24px", marginBottom: "10px" }}>🔄</div>
        <p>Loading Google Authentication...</p>
        <small style={{ color: "#666" }}>
          Initializing Google Identity Services...
        </small>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        style={{
          padding: "20px",
          border: "2px solid #f44336",
          backgroundColor: "#ffebee",
          borderRadius: "8px",
          margin: "10px 0",
        }}
      >
        <h3 style={{ color: "#d32f2f", margin: "0 0 10px 0" }}>
          ❌ Authentication Error
        </h3>
        <p style={{ margin: "0 0 15px 0", color: "#d32f2f" }}>{error}</p>
        <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
          <button
            onClick={() => {
              setError("");
              setupGoogleButton();
            }}
            style={{
              padding: "8px 16px",
              backgroundColor: "#1976d2",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            🔄 Retry
          </button>
          <button
            onClick={() => {
              setError("");
              window.location.reload();
            }}
            style={{
              padding: "8px 16px",
              backgroundColor: "#666",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            🔄 Reload Page
          </button>
        </div>
      </div>
    );
  }

  // Signed in state
  if (user) {
    return (
      <div
        style={{
          padding: "20px",
          border: "2px solid #4caf50",
          backgroundColor: "#e8f5e8",
          borderRadius: "8px",
          margin: "10px 0",
        }}
      >
        <h3 style={{ color: "#2e7d32", margin: "0 0 15px 0" }}>
          ✅ Welcome, {user.name}!
        </h3>

        <div style={{ marginBottom: "15px" }}>
          <p style={{ margin: "5px 0" }}>
            <strong>Email:</strong> {user.email}
          </p>
          <p style={{ margin: "5px 0" }}>
            <strong>ID:</strong> {user.id}
          </p>
          {user.verified_email !== undefined && (
            <p style={{ margin: "5px 0" }}>
              <strong>Verified:</strong>{" "}
              {user.verified_email ? "✅ Yes" : "❌ No"}
            </p>
          )}
        </div>

        {user.imageUrl && (
          <img
            src={user.imageUrl}
            alt="Profile"
            style={{
              width: 60,
              height: 60,
              borderRadius: "50%",
              marginBottom: "15px",
              border: "2px solid #4caf50",
            }}
          />
        )}

        <br />
        <button
          onClick={handleSignOut}
          disabled={isLoading}
          style={{
            padding: "10px 20px",
            backgroundColor: isLoading ? "#ccc" : "#f44336",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: isLoading ? "not-allowed" : "pointer",
          }}
        >
          {isLoading ? "🔄 Signing out..." : "🚪 Sign Out"}
        </button>
      </div>
    );
  }

  // Sign in state
  return (
    <div
      style={{
        padding: "20px",
        border: "2px solid #1976d2",
        borderRadius: "8px",
        margin: "10px 0",
        textAlign: "center",
      }}
    >
      <h3 style={{ margin: "0 0 15px 0", color: "#1565c0" }}>
        🔐 Google Authentication
      </h3>

      <p style={{ margin: "0 0 20px 0", color: "#666" }}>
        Sign in with your Google account using secure authentication
      </p>

      {/* Google Sign-In Button */}
      <div
        ref={buttonRef}
        style={{
          display: "flex",
          justifyContent: "center",
          marginBottom: "15px",
          minHeight: "44px", // Reserve space for button
        }}
      />

      {/* Fallback manual button */}
      <button
        onClick={handleManualSignIn}
        disabled={isLoading}
        style={{
          padding: "10px 20px",
          backgroundColor: isLoading ? "#ccc" : "#4285f4",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: isLoading ? "not-allowed" : "pointer",
          marginTop: "10px",
        }}
      >
        {isLoading ? "🔄 Signing in..." : "🔄 Alternative Sign-In"}
      </button>

      <p style={{ margin: "15px 0 0 0", fontSize: "12px", color: "#999" }}>
        ✨ Uses Google Identity Services - Modern & Secure
      </p>

      {/* Debug info */}
      {process.env.NODE_ENV === "development" && (
        <details style={{ marginTop: "15px", textAlign: "left" }}>
          <summary style={{ cursor: "pointer", fontSize: "12px" }}>
            🔍 Debug Info
          </summary>
          <div
            style={{
              fontSize: "11px",
              fontFamily: "monospace",
              marginTop: "5px",
              padding: "10px",
              backgroundColor: "#f5f5f5",
              borderRadius: "4px",
            }}
          >
            <div>
              Client ID:{" "}
              {process.env.REACT_APP_GOOGLE_CLIENT_ID ? "✅ Set" : "❌ Missing"}
            </div>
            <div>Initialized: {isInitialized ? "✅ Yes" : "❌ No"}</div>
            <div>
              Google API:{" "}
              {window.google?.accounts ? "✅ Loaded" : "❌ Not loaded"}
            </div>
            <div>
              Button Ref: {buttonRef.current ? "✅ Ready" : "❌ Not ready"}
            </div>
          </div>
        </details>
      )}
    </div>
  );
};

export default NewGoogleAuth;