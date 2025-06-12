import apiClient from "./api";

export const profileService = {
  // Get user profile
  async getProfile() {
    try {
      const response = await apiClient.get("/profile");
      return response;
    } catch (error) {
      console.error("Profile service - getProfile error:", error);
      throw error;
    }
  },

  // Update user profile
  async updateProfile(profileData) {
    try {
      const response = await apiClient.put("/profile", profileData);
      return response;
    } catch (error) {
      console.error("Profile service - updateProfile error:", error);
      throw error;
    }
  },

  // Upload avatar
  async uploadAvatar(formData) {
    try {
      const response = await apiClient.post(
        "/profile/upload-avatar",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      return response;
    } catch (error) {
      console.error("Profile service - uploadAvatar error:", error);
      throw error;
    }
  },

  // Get trading statistics
  async getTradingStats() {
    try {
      const response = await apiClient.get("/profile/stats");
      return response;
    } catch (error) {
      console.error("Profile service - getTradingStats error:", error);
      throw error;
    }
  },

  // Update security settings (change password)
  async updateSecuritySettings(settings) {
    try {
      const response = await apiClient.post(
        "/profile/change-password",
        settings
      );
      return response;
    } catch (error) {
      console.error("Profile service - updateSecuritySettings error:", error);
      throw error;
    }
  },

  // Get notifications (placeholder - implement if needed)
  async getNotifications() {
    try {
      const response = await apiClient.get("/profile/notifications");
      return response;
    } catch (error) {
      console.error("Profile service - getNotifications error:", error);
      throw error;
    }
  },

  // Mark notification as read (placeholder - implement if needed)
  async markNotificationRead(notificationId) {
    try {
      const response = await apiClient.patch(
        `/profile/notifications/${notificationId}/read`
      );
      return response;
    } catch (error) {
      console.error("Profile service - markNotificationRead error:", error);
      throw error;
    }
  },

  // Get API keys (placeholder - implement if needed)
  async getApiKeys() {
    try {
      const response = await apiClient.get("/profile/api-keys");
      return response;
    } catch (error) {
      console.error("Profile service - getApiKeys error:", error);
      throw error;
    }
  },

  // Generate new API key (placeholder - implement if needed)
  async generateApiKey(keyData) {
    try {
      const response = await apiClient.post("/profile/api-keys", keyData);
      return response;
    } catch (error) {
      console.error("Profile service - generateApiKey error:", error);
      throw error;
    }
  },

  // Delete API key (placeholder - implement if needed)
  async deleteApiKey(keyId) {
    try {
      const response = await apiClient.delete(`/profile/api-keys/${keyId}`);
      return response;
    } catch (error) {
      console.error("Profile service - deleteApiKey error:", error);
      throw error;
    }
  },
};
