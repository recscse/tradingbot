import React, { createContext, useContext, useReducer, useEffect } from "react";
import { toast } from "react-hot-toast";
import api from "../services/api";

const NotificationContext = createContext();

// Action types
const NOTIFICATION_ACTIONS = {
  SET_NOTIFICATIONS: "SET_NOTIFICATIONS",
  ADD_NOTIFICATION: "ADD_NOTIFICATION",
  MARK_AS_READ: "MARK_AS_READ",
  MARK_ALL_AS_READ: "MARK_ALL_AS_READ",
  DELETE_NOTIFICATION: "DELETE_NOTIFICATION",
  SET_LOADING: "SET_LOADING",
  SET_ERROR: "SET_ERROR",
  CLEAR_ERROR: "CLEAR_ERROR",
  SET_UNREAD_COUNT: "SET_UNREAD_COUNT",
  SET_PREFERENCES: "SET_PREFERENCES",
  SET_TOKEN_STATUS: "SET_TOKEN_STATUS",
};

// Initial state
const initialState = {
  notifications: [],
  unreadCount: 0,
  loading: false,
  error: null,
  lastFetched: null,
  preferences: null,
  tokenStatus: null,
  stats: null,
};

// Reducer
const notificationReducer = (state, action) => {
  switch (action.type) {
    case NOTIFICATION_ACTIONS.SET_NOTIFICATIONS:
      return {
        ...state,
        notifications: action.payload,
        unreadCount: action.payload.filter((n) => !n.is_read).length,
        loading: false,
        lastFetched: new Date(),
      };

    case NOTIFICATION_ACTIONS.ADD_NOTIFICATION:
      const newNotifications = [action.payload, ...state.notifications];
      return {
        ...state,
        notifications: newNotifications,
        unreadCount: newNotifications.filter((n) => !n.is_read).length,
      };

    case NOTIFICATION_ACTIONS.MARK_AS_READ:
      const updatedNotifications = state.notifications.map((n) =>
        n.id === action.payload ? { ...n, is_read: true } : n
      );
      return {
        ...state,
        notifications: updatedNotifications,
        unreadCount: updatedNotifications.filter((n) => !n.is_read).length,
      };

    case NOTIFICATION_ACTIONS.MARK_ALL_AS_READ:
      const allReadNotifications = state.notifications.map((n) => ({
        ...n,
        is_read: true,
      }));
      return {
        ...state,
        notifications: allReadNotifications,
        unreadCount: 0,
      };

    case NOTIFICATION_ACTIONS.DELETE_NOTIFICATION:
      const filteredNotifications = state.notifications.filter(
        (n) => n.id !== action.payload
      );
      return {
        ...state,
        notifications: filteredNotifications,
        unreadCount: filteredNotifications.filter((n) => !n.is_read).length,
      };

    case NOTIFICATION_ACTIONS.SET_LOADING:
      return { ...state, loading: action.payload };

    case NOTIFICATION_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload, loading: false };

    case NOTIFICATION_ACTIONS.CLEAR_ERROR:
      return { ...state, error: null };

    case NOTIFICATION_ACTIONS.SET_UNREAD_COUNT:
      return { ...state, unreadCount: action.payload };

    case NOTIFICATION_ACTIONS.SET_PREFERENCES:
      return { ...state, preferences: action.payload };

    case NOTIFICATION_ACTIONS.SET_TOKEN_STATUS:
      return { ...state, tokenStatus: action.payload };

    default:
      return state;
  }
};

export const NotificationProvider = ({ children }) => {
  const [state, dispatch] = useReducer(notificationReducer, initialState);

  // Fetch notifications
  const fetchNotifications = async (options = {}) => {
    try {
      dispatch({ type: NOTIFICATION_ACTIONS.SET_LOADING, payload: true });

      const params = new URLSearchParams({
        limit: options.limit || 20,
        page: options.page || 1,
        ...(options.type && { type: options.type }),
        ...(options.is_read !== undefined && { is_read: options.is_read }),
        ...(options.priority && { priority: options.priority }),
      });

      const response = await api.get(`/notifications?${params}`);

      dispatch({
        type: NOTIFICATION_ACTIONS.SET_NOTIFICATIONS,
        payload: response.data.notifications || [],
      });

      if (response.data.unread_count !== undefined) {
        dispatch({
          type: NOTIFICATION_ACTIONS.SET_UNREAD_COUNT,
          payload: response.data.unread_count,
        });
      }
    } catch (error) {
      console.error("Error fetching notifications:", error);
      dispatch({
        type: NOTIFICATION_ACTIONS.SET_ERROR,
        payload: "Failed to fetch notifications",
      });
    }
  };

  // Mark notification as read
  const markAsRead = async (notificationId) => {
    try {
      await api.patch(`/notifications/${notificationId}/read`);
      dispatch({
        type: NOTIFICATION_ACTIONS.MARK_AS_READ,
        payload: notificationId,
      });
    } catch (error) {
      console.error("Error marking notification as read:", error);
      toast.error("Failed to mark notification as read");
    }
  };

  // Mark all notifications as read
  const markAllAsRead = async () => {
    try {
      await api.patch("/notifications/mark-all-read");
      dispatch({ type: NOTIFICATION_ACTIONS.MARK_ALL_AS_READ });
      toast.success("All notifications marked as read");
    } catch (error) {
      console.error("Error marking all notifications as read:", error);
      toast.error("Failed to mark all notifications as read");
    }
  };

  // Delete notification
  const deleteNotification = async (notificationId) => {
    try {
      await api.delete(`/notifications/${notificationId}`);
      dispatch({
        type: NOTIFICATION_ACTIONS.DELETE_NOTIFICATION,
        payload: notificationId,
      });
      toast.success("Notification deleted");
    } catch (error) {
      console.error("Error deleting notification:", error);
      toast.error("Failed to delete notification");
    }
  };

  // Add notification
  const addNotification = (notification) => {
    dispatch({
      type: NOTIFICATION_ACTIONS.ADD_NOTIFICATION,
      payload: notification,
    });

    const toastOptions = { duration: 5000, position: "top-right" };
    switch (notification.type) {
      case "success":
        toast.success(notification.title, toastOptions);
        break;
      case "error":
        toast.error(notification.title, toastOptions);
        break;
      case "warning":
        toast(notification.title, { ...toastOptions, icon: "⚠️" });
        break;
      case "info":
      default:
        toast(notification.title, { ...toastOptions, icon: "ℹ️" });
        break;
    }
  };

  // ✅ Safe fetchPreferences (no crash if backend 405)
  const fetchPreferences = async () => {
    try {
      const response = await api.get("/notifications/preferences");
      dispatch({
        type: NOTIFICATION_ACTIONS.SET_PREFERENCES,
        payload: response.data,
      });
      return response.data;
    } catch (error) {
      console.error("Error fetching notification preferences:", error);
      return null;
    }
  };

  const updatePreferences = async (preferences) => {
    try {
      const response = await api.patch(
        "/notifications/preferences",
        preferences
      );
      await fetchPreferences();
      toast.success("Notification preferences updated");
      return response.data;
    } catch (error) {
      console.error("Error updating notification preferences:", error);
      toast.error("Failed to update preferences");
      return null;
    }
  };

  // ✅ Safe fetchTokenStatus
  const fetchTokenStatus = async () => {
    try {
      const response = await api.get("/notifications/tokens/status");
      dispatch({
        type: NOTIFICATION_ACTIONS.SET_TOKEN_STATUS,
        payload: response.data,
      });
      return response.data;
    } catch (error) {
      console.error("Error fetching token status:", error);
      return null;
    }
  };

  // Send test notification
  const sendTestNotification = async (type, channel = "all") => {
    try {
      const response = await api.post("/notifications/test", {
        type,
        channel,
      });
      toast.success(`Test notification sent via ${channel}`);
      await fetchNotifications();
      return response.data;
    } catch (error) {
      console.error("Error sending test notification:", error);
      toast.error("Failed to send test notification");
      return null;
    }
  };

  // Get stats
  const getNotificationStats = async (days = 7) => {
    try {
      const response = await api.get(`/notifications/stats?days=${days}`);
      return response.data;
    } catch (error) {
      console.error("Error fetching stats:", error);
      return null;
    }
  };

  // Polling
  useEffect(() => {
    fetchNotifications();
    fetchPreferences();
    fetchTokenStatus();

    const pollInterval = setInterval(() => {
      fetchNotifications();
      fetchTokenStatus();
    }, 30000);

    return () => clearInterval(pollInterval);
  }, []);

  const value = {
    ...state,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    addNotification,
    fetchPreferences,
    updatePreferences,
    fetchTokenStatus,
    sendTestNotification,
    getNotificationStats,
    clearError: () => dispatch({ type: NOTIFICATION_ACTIONS.CLEAR_ERROR }),
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error(
      "useNotifications must be used within a NotificationProvider"
    );
  }
  return context;
};
