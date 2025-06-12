class CustomGoogleAuth {
  constructor() {
    this.clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
    this.redirectUri = `${window.location.origin}/auth/google/callback`;
  }

  async signInWithPopup() {
    return new Promise((resolve, reject) => {
      const state = this.generateState();

      const params = new URLSearchParams({
        client_id: this.clientId,
        redirect_uri: this.redirectUri,
        response_type: "code",
        scope: "email profile openid",
        state: state,
        prompt: "select_account",
      });

      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

      // Popup window settings
      const width = 500;
      const height = 600;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;

      const popup = window.open(
        authUrl,
        "google-signin",
        `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
      );

      if (!popup) {
        reject(new Error("Popup blocked"));
        return;
      }

      // Listen for messages from popup
      const messageHandler = (event) => {
        if (event.origin !== window.location.origin) return;

        if (event.data.type === "GOOGLE_AUTH_SUCCESS") {
          cleanup();
          resolve(event.data);
        } else if (event.data.type === "GOOGLE_AUTH_ERROR") {
          cleanup();
          reject(new Error(event.data.error));
        }
      };

      const cleanup = () => {
        window.removeEventListener("message", messageHandler);
        clearInterval(checkClosed);
        if (!popup.closed) popup.close();
      };

      // Check if popup closed manually
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          cleanup();
          reject(new Error("Authentication cancelled"));
        }
      }, 1000);

      window.addEventListener("message", messageHandler);

      // Timeout
      setTimeout(() => {
        cleanup();
        reject(new Error("Authentication timeout"));
      }, 300000);
    });
  }

  generateState() {
    return Math.random().toString(36).substring(2) + Date.now().toString(36);
  }
}

const customGoogleAuth = new CustomGoogleAuth();
export default customGoogleAuth;
