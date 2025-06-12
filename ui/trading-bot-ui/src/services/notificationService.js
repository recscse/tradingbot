import api from "./api";

export const notificationService = {
  // Get all notifications
  getNotifications: async (params = {}) => {
    const queryParams = new URLSearchParams({
      page: params.page || 1,
      limit: params.limit || 20,
      type: params.type || "",
      is_read: params.is_read || "",
      ...params,
    });

    const response = await api.get(`/notifications?${queryParams}`);
    return response.data;
  },

  // Mark notification as read
  markAsRead: async (notificationId) => {
    const response = await api.patch(`/notifications/${notificationId}/read`);
    return response.data;
  },

  // Mark all notifications as read
  markAllAsRead: async () => {
    const response = await api.patch("/notifications/mark-all-read");
    return response.data;
  },

  // Delete notification
  deleteNotification: async (notificationId) => {
    const response = await api.delete(`/notifications/${notificationId}`);
    return response.data;
  },

  // Get notification settings
  getSettings: async () => {
    const response = await api.get("/notifications/settings");
    return response.data;
  },

  // Update notification settings
  updateSettings: async (settings) => {
    const response = await api.patch("/notifications/settings", settings);
    return response.data;
  },
};
