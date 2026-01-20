import React, { useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Box,
  Chip,
  Collapse,
  Alert,
} from "@mui/material";
import {
  Info,
  Warning,
  Error,
  CheckCircle,
  ExpandMore,
  ExpandLess,
  Clear,
  ClearAll,
} from "@mui/icons-material";
import { useEnhancedMarket } from "../../context/EnhancedMarketProvider";

const NotificationCenter = () => {
  const { notifications, removeNotification } = useEnhancedMarket();
  const [expanded, setExpanded] = useState(true);

  const getNotificationIcon = (type) => {
    switch (type) {
      case "success":
        return <CheckCircle color="success" />;
      case "error":
        return <Error color="error" />;
      case "warning":
        return <Warning color="warning" />;
      case "info":
      default:
        return <Info color="info" />;
    }
  };

  const getNotificationColor = (type) => {
    switch (type) {
      case "success":
        return "success";
      case "error":
        return "error";
      case "warning":
        return "warning";
      case "info":
      default:
        return "info";
    }
  };

  const handleClearAll = () => {
    notifications.forEach((notification) => {
      removeNotification(notification.id);
    });
  };

  const formatTime = (timestamp) => {
    const now = new Date();
    const notificationTime = new Date(timestamp);
    const diffMs = now - notificationTime;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return notificationTime.toLocaleDateString();
  };

  const recentNotifications = notifications.slice(0, 10);

  return (
    <Card elevation={3}>
      <CardContent>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6" component="div">
              Notifications
            </Typography>
            <Chip label={notifications.length} color="primary" size="small" />
          </Box>

          <Box display="flex" alignItems="center" gap={1}>
            {notifications.length > 0 && (
              <IconButton size="small" onClick={handleClearAll}>
                <ClearAll />
              </IconButton>
            )}
            <IconButton size="small" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Box>
        </Box>

        <Collapse in={expanded}>
          {notifications.length === 0 ? (
            <Alert severity="info">No notifications at the moment.</Alert>
          ) : (
            <List dense>
              {recentNotifications.map((notification) => (
                <ListItem
                  key={notification.id}
                  sx={{
                    border: `1px solid`,
                    borderColor:
                      getNotificationColor(notification.type) + ".light",
                    borderRadius: 1,
                    mb: 1,
                    bgcolor: getNotificationColor(notification.type) + ".light",
                    "&:hover": {
                      bgcolor:
                        getNotificationColor(notification.type) + ".main",
                      "& .MuiTypography-root": {
                        color: "white",
                      },
                    },
                  }}
                >
                  <ListItemIcon>
                    {getNotificationIcon(notification.type)}
                  </ListItemIcon>

                  <ListItemText
                    primary={
                      <Typography variant="subtitle2">
                        {notification.title || "Notification"}
                      </Typography>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2">
                          {notification.message}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {formatTime(notification.timestamp)}
                        </Typography>
                      </Box>
                    }
                  />

                  <IconButton
                    size="small"
                    onClick={() => removeNotification(notification.id)}
                  >
                    <Clear />
                  </IconButton>
                </ListItem>
              ))}
            </List>
          )}

          {notifications.length > 10 && (
            <Box mt={1}>
              <Typography variant="caption" color="textSecondary">
                Showing {recentNotifications.length} of {notifications.length}{" "}
                notifications
              </Typography>
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default NotificationCenter;
