import React from "react";
import {
  Box,
  Typography,
  IconButton,
  Chip,
  useTheme,
  alpha,
} from "@mui/material";
import {
  Close as CloseIcon,
  Circle as CircleIcon,
  TrendingUp,
  TrendingDown,
  Warning,
  Info,
  CheckCircle,
} from "@mui/icons-material";
import { formatDistanceToNow } from "date-fns";

const NotificationItem = ({
  notification,
  onMarkAsRead,
  onDelete,
  onClick,
}) => {
  const theme = useTheme();

  const getNotificationIcon = (type) => {
    switch (type) {
      case "trade_executed":
        return <TrendingUp sx={{ color: "success.main" }} />;
      case "price_alert":
        return <TrendingDown sx={{ color: "info.main" }} />;
      case "stop_loss":
        return <Warning sx={{ color: "warning.main" }} />;
      case "error":
        return <Warning sx={{ color: "error.main" }} />;
      case "success":
        return <CheckCircle sx={{ color: "success.main" }} />;
      default:
        return <Info sx={{ color: "info.main" }} />;
    }
  };

  const getNotificationColor = (type) => {
    switch (type) {
      case "trade_executed":
      case "success":
        return theme.palette.success.main;
      case "price_alert":
      case "info":
        return theme.palette.info.main;
      case "stop_loss":
      case "warning":
        return theme.palette.warning.main;
      case "error":
        return theme.palette.error.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const handleItemClick = () => {
    if (!notification.is_read) {
      onMarkAsRead(notification.id);
    }
    onClick?.(notification);
  };

  const formatTimeAgo = (dateString) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch (error) {
      return "Recently";
    }
  };

  return (
    <Box
      sx={{
        position: "relative",
        p: 2,
        borderBottom: `1px solid ${theme.palette.divider}`,
        bgcolor: notification.is_read
          ? "transparent"
          : alpha(getNotificationColor(notification.type), 0.05),
        cursor: "pointer",
        transition: "background-color 0.2s ease",
        "&:hover": {
          bgcolor: alpha(theme.palette.action.hover, 0.5),
        },
        "&:last-child": {
          borderBottom: "none",
        },
      }}
      onClick={handleItemClick}
    >
      {/* Unread indicator */}
      {!notification.is_read && (
        <Box
          sx={{
            position: "absolute",
            left: 8,
            top: "50%",
            transform: "translateY(-50%)",
            width: 8,
            height: 8,
            borderRadius: "50%",
            bgcolor: getNotificationColor(notification.type),
          }}
        />
      )}

      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          gap: 2,
          pl: notification.is_read ? 0 : 2,
        }}
      >
        {/* Icon */}
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            bgcolor: alpha(getNotificationColor(notification.type), 0.1),
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          {getNotificationIcon(notification.type)}
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              mb: 0.5,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{
                fontWeight: notification.is_read ? 400 : 600,
                color: "text.primary",
              }}
            >
              {notification.title}
            </Typography>

            {/* Priority chip */}
            {notification.priority === "high" && (
              <Chip
                label="High"
                size="small"
                color="error"
                variant="outlined"
                sx={{ ml: 1, fontSize: "0.6rem", height: 20 }}
              />
            )}
          </Box>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mb: 1,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {notification.message}
          </Typography>

          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Typography variant="caption" color="text.secondary">
              {formatTimeAgo(notification.created_at)}
            </Typography>

            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {/* Category tag */}
              {notification.category && (
                <Chip
                  label={notification.category}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: "0.6rem", height: 20 }}
                />
              )}

              {/* Delete button */}
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(notification.id);
                }}
                sx={{
                  opacity: 0.7,
                  "&:hover": { opacity: 1 },
                }}
              >
                <CloseIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default NotificationItem;
