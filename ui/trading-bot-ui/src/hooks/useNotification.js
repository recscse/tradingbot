import { useState, useCallback } from "react";

export const useNotification = () => {
  const [notifications, setNotifications] = useState([]);

  const showNotification = useCallback(
    (message, type = "info", duration = 5000) => {
      const id = Date.now();
      const notification = {
        id,
        message,
        type,
        timestamp: new Date().toISOString(),
      };

      setNotifications((prev) => [...prev, notification]);

      // Auto remove notification after duration
      setTimeout(() => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      }, duration);
    },
    []
  );

  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  return {
    notifications,
    showNotification,
    removeNotification,
  };
};
