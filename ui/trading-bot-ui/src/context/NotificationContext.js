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
};

// Initial state
const initialState = {
  notifications: [],
  unreadCount: 0,
  loading: false,
  error: null,
  lastFetched: null,
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

    default:
      return state;
  }
};

export const NotificationProvider = ({ children }) => {
  const [state, dispatch] = useReducer(notificationReducer, initialState);

  // Fetch notifications
  const fetchNotifications = async () => {
    try {
      dispatch({ type: NOTIFICATION_ACTIONS.SET_LOADING, payload: true });
      const response = await api.get("/notifications");
      dispatch({
        type: NOTIFICATION_ACTIONS.SET_NOTIFICATIONS,
        payload: response.data.notifications || [],
      });
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

  // Add notification (for real-time updates)
  const addNotification = (notification) => {
    dispatch({
      type: NOTIFICATION_ACTIONS.ADD_NOTIFICATION,
      payload: notification,
    });

    // Show toast for new notifications
    const toastOptions = {
      duration: 5000,
      position: "top-right",
    };

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

  // Initial fetch and polling
  useEffect(() => {
    fetchNotifications();

    // Poll for new notifications every 30 seconds
    const pollInterval = setInterval(fetchNotifications, 30000);

    return () => clearInterval(pollInterval);
  }, []);

  const value = {
    ...state,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    addNotification,
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
