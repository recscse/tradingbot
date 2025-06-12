import React from "react";
import {
  Menu,
  Box,
  Typography,
  Button,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  useTheme,
} from "@mui/material";
import {
  MarkEmailRead as MarkAllReadIcon,
  Refresh as RefreshIcon,
  OpenInNew as ViewAllIcon,
} from "@mui/icons-material";
import { useNotifications } from "../../contexts/NotificationContext";
import NotificationItem from "./NotificationItem";
import { useNavigate } from "react-router-dom";

const NotificationMenu = ({ anchorEl, open, onClose }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const {
    notifications,
    unreadCount,
    loading,
    error,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    fetchNotifications,
    clearError,
  } = useNotifications();

  const handleNotificationClick = (notification) => {
    // Navigate to relevant page based on notification type
    switch (notification.type) {
      case "trade_executed":
        navigate("/trade-control");
        break;
      case "price_alert":
        navigate("/dashboard");
        break;
      case "stop_loss":
        navigate("/analysis");
        break;
      default:
        break;
    }
    onClose();
  };

  const handleViewAll = () => {
    navigate("/notifications");
    onClose();
  };

  const handleMarkAllAsRead = async () => {
    await markAllAsRead();
  };

  const handleRefresh = async () => {
    clearError();
    await fetchNotifications();
  };

  const recentNotifications = notifications.slice(0, 5);

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      transformOrigin={{ vertical: "top", horizontal: "right" }}
      PaperProps={{
        elevation: 8,
        sx: {
          mt: 1,
          width: 400,
          maxHeight: 500,
          borderRadius: 2,
          bgcolor: "background.paper",
          border: `1px solid ${theme.palette.divider}`,
          overflow: "hidden",
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: `1px solid ${theme.palette.divider}`,
          bgcolor:
            theme.palette.mode === "dark"
              ? "rgba(255, 255, 255, 0.02)"
              : "rgba(0, 0, 0, 0.02)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="h6" fontWeight={600}>
            Notifications
            {unreadCount > 0 && (
              <Box
                component="span"
                sx={{
                  ml: 1,
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                  bgcolor: "error.main",
                  color: "white",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                }}
              >
                {unreadCount}
              </Box>
            )}
          </Typography>

          <Box sx={{ display: "flex", gap: 0.5 }}>
            <IconButton size="small" onClick={handleRefresh} disabled={loading}>
              <RefreshIcon sx={{ fontSize: 18 }} />
            </IconButton>

            {unreadCount > 0 && (
              <IconButton size="small" onClick={handleMarkAllAsRead}>
                <MarkAllReadIcon sx={{ fontSize: 18 }} />
              </IconButton>
            )}
          </Box>
        </Box>
      </Box>

      {/* Content */}
      <Box sx={{ maxHeight: 350, overflow: "auto" }}>
        {loading && notifications.length === 0 ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : error ? (
          <Box sx={{ p: 2 }}>
            <Alert
              severity="error"
              action={
                <Button size="small" onClick={handleRefresh}>
                  Retry
                </Button>
              }
            >
              {error}
            </Alert>
          </Box>
        ) : recentNotifications.length === 0 ? (
          <Box sx={{ p: 4, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No notifications yet
            </Typography>
            <Typography variant="caption" color="text.secondary">
              You'll see trading alerts and updates here
            </Typography>
          </Box>
        ) : (
          recentNotifications.map((notification) => (
            <NotificationItem
              key={notification.id}
              notification={notification}
              onMarkAsRead={markAsRead}
              onDelete={deleteNotification}
              onClick={handleNotificationClick}
            />
          ))
        )}
      </Box>

      {/* Footer */}
      {recentNotifications.length > 0 && (
        <>
          <Divider />
          <Box sx={{ p: 1 }}>
            <Button
              fullWidth
              variant="text"
              size="small"
              onClick={handleViewAll}
              endIcon={<ViewAllIcon sx={{ fontSize: 16 }} />}
              sx={{ textTransform: "none", fontWeight: 500 }}
            >
              View All Notifications
            </Button>
          </Box>
        </>
      )}
    </Menu>
  );
};

export default NotificationMenu;
