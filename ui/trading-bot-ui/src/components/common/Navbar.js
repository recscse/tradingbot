import React, { useState, useEffect } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  Avatar,
  Menu,
  MenuItem,
  useTheme,
  useMediaQuery,
  Divider,
  Tooltip,
  Button,
  Chip,
  Stack,
  Paper,
  Fade,
  Slide,
  BottomNavigation,
  BottomNavigationAction,
} from "@mui/material";
import {
  DashboardRounded,
  ShowChartRounded,
  HistoryRounded,
  DescriptionRounded,
  SmartToyRounded,
  SettingsRounded,
  LogoutRounded,
  PersonRounded,
  NotificationsRounded,
  RefreshRounded,
  CloseRounded,
  MarkEmailReadRounded,
  DeleteRounded,
  CandlestickChartRounded,
  MoreHorizRounded,
  SpeedRounded,
  AutoGraphRounded,
  AssessmentRounded,
  DnsRounded,
} from "@mui/icons-material";
import { useNavigate, useLocation } from "react-router-dom";
import { toast } from "react-hot-toast";
import ThemeToggle from "../settings/ThemeToggle";
import { logout, getCurrentUser } from "../../services/authService";
import { useNotifications } from "../../context/NotificationContext";

const Navbar = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const isXs = useMediaQuery(theme.breakpoints.down("sm"));
  const isSm = useMediaQuery(theme.breakpoints.down("md"));
  const isMd = useMediaQuery(theme.breakpoints.down("lg"));
  const isLg = useMediaQuery(theme.breakpoints.down("xl"));
  const isVerySmall = useMediaQuery("(max-width:350px)");

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const {
    notifications,
    unreadCount,
    loading: notificationLoading,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    fetchNotifications,
  } = useNotifications();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(null);
  const [notificationMenuOpen, setNotificationMenuOpen] = useState(null);
  const [marketStatus, setMarketStatus] = useState("loading");

  useEffect(() => {
    const loadUserData = async () => {
      try {
        const userData = getCurrentUser();
        if (userData) {
          setUser(userData);
        }
      } catch (error) {
        console.error("Error loading user data:", error);
      } finally {
        setLoading(false);
      }
    };
    loadUserData();
  }, []);

  const navItems = [
    {
      name: "Dashboard",
      path: "/dashboard",
      icon: <DashboardRounded />,
      color: "#3b82f6", // Blue
      shortName: "Home",
    },
    {
      name: "Trade Control",
      path: "/trade-control",
      icon: <ShowChartRounded />,
      color: "#10b981", // Emerald
      shortName: "Trade",
    },
    {
      name: "Analytics",
      path: "/analysis",
      icon: <AutoGraphRounded />,
      color: "#f59e0b", // Amber
      shortName: "Charts",
    },
    {
      name: "Performance",
      path: "/performance-analytics",
      icon: <AssessmentRounded />,
      color: "#8b5cf6", // Violet
      shortName: "Metrics",
    },
    {
      name: "Backtesting",
      path: "/backtesting",
      icon: <HistoryRounded />,
      color: "#ec4899", // Pink
      shortName: "History",
    },
    {
      name: "Paper Trading",
      path: "/papertrading",
      icon: <DescriptionRounded />,
      color: "#ef4444", // Red
      shortName: "Paper",
    },
    {
      name: "Auto Trading",
      path: "/auto-trading",
      icon: <SmartToyRounded />,
      color: "#06b6d4", // Cyan
      shortName: "Auto",
    },
    {
      name: "System Health",
      path: "/system-health",
      icon: <DnsRounded />,
      color: "#6366f1", // Indigo
      shortName: "Health",
    },
    {
      name: "Settings",
      path: "/config",
      icon: <SettingsRounded />,
      color: "#64748b", // Slate
      shortName: "Config",
    },
  ];

  useEffect(() => {
    const checkMarketStatus = () => {
      const now = new Date();
      const day = now.getDay();
      const hours = now.getHours();
      const minutes = now.getMinutes();
      const time = hours * 100 + minutes;

      if (day === 0 || day === 6) {
        setMarketStatus("closed");
        return;
      }

      if (time >= 915 && time <= 1530) {
        setMarketStatus("open");
      } else if (time > 1530 && time <= 1800) {
        setMarketStatus("post");
      } else if (time >= 600 && time < 915) {
        setMarketStatus("pre");
      } else {
        setMarketStatus("closed");
      }
    };

    checkMarketStatus();
    const interval = setInterval(checkMarketStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  const isActive = (path) => location.pathname === path;

  const getUserInitials = () => {
    if (!user?.full_name && !user?.name) return "U";
    const name = user?.full_name || user?.name || "User";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const getMarketStatusInfo = () => {
    switch (marketStatus) {
      case "open":
        return {
          label: isVerySmall ? "Live" : "Open",
          color: "success",
          icon: "🟢",
        };
      case "closed":
        return {
          label: "Closed",
          color: "error",
          icon: "🔴",
        };
      case "pre":
        return {
          label: isVerySmall ? "Pre" : "Pre-Market",
          color: "warning",
          icon: "🟡",
        };
      case "post":
        return {
          label: isVerySmall ? "Post" : "After Hours",
          color: "info",
          icon: "🔵",
        };
      default:
        return {
          label: "Loading...",
          color: "default",
          icon: "⏳",
        };
    }
  };

  const handleNotificationMenuOpen = (event) => {
    setNotificationMenuOpen(event.currentTarget);
  };

  const handleNotificationClick = async (notification) => {
    if (!notification.is_read) {
      await markAsRead(notification.id);
    }
    toast(notification.message || notification.title, {
      duration: 4000,
      position: "top-right",
      icon: getNotificationIcon(notification.type),
    });
    setNotificationMenuOpen(null);
  };

  const handleRefresh = async () => {
    toast.loading("Refreshing market data...", { id: "refresh" });
    try {
      await fetchNotifications();
      setTimeout(() => {
        toast.success("Market data updated!", { id: "refresh" });
      }, 1200);
    } catch (error) {
      toast.error("Failed to refresh data", { id: "refresh" });
    }
  };

  const handleLogout = () => {
    toast.success("Logged out successfully!");
    setTimeout(() => {
      logout();
      navigate("/");
    }, 1000);
  };

  const handleMarkAllAsRead = async () => {
    try {
      await markAllAsRead();
      setNotificationMenuOpen(null);
    } catch (error) {
      toast.error("Failed to mark all as read");
    }
  };

  const handleDeleteNotification = async (e, notificationId) => {
    e.stopPropagation();
    try {
      await deleteNotification(notificationId);
    } catch (error) {
      toast.error("Failed to delete notification");
    }
  };

  const getNotificationIcon = (type) => {
    const icons = {
      success: "✅",
      error: "❌",
      warning: "⚠️",
      info: "ℹ️",
      trade: "📈",
      profit: "💰",
      loss: "📉",
    };
    return icons[type] || "📢";
  };

  const getNotificationColor = (type) => {
    const colors = {
      success: theme.palette.success.main,
      error: theme.palette.error.main,
      warning: theme.palette.warning.main,
      info: theme.palette.info.main,
      trade: theme.palette.primary.main,
      profit: theme.palette.success.main,
      loss: theme.palette.error.main,
    };
    return colors[type] || theme.palette.text.secondary;
  };

  const formatNotificationTime = (timestamp) => {
    if (!timestamp) return "Just now";

    const now = new Date();
    const notificationTime = new Date(timestamp);
    const diff = now - notificationTime;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return "Just now";
  };

  const statusInfo = getMarketStatusInfo();

  if (loading) {
    return null;
  }

  // Mobile Bottom Navigation Items
  const mobileNavItems = navItems.slice(0, 4); // First 4 items directly accessible
  const isMoreActive = navItems.slice(4).some(item => isActive(item.path));

  return (
    <>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          bgcolor:
            theme.palette.mode === "dark"
              ? "rgba(15, 23, 42, 0.85)" // Slate 900 with transparency
              : "rgba(255, 255, 255, 0.85)",
          backdropFilter: "blur(24px)",
          borderBottom: `1px solid ${theme.palette.divider}`,
          zIndex: theme.zIndex.appBar,
          width: "100%",
          left: 0,
          right: 0,
        }}
      >
        <Toolbar
          disableGutters
          sx={{
            height: { xs: 56, sm: 64, md: 72 },
            justifyContent: "space-between",
            px: { xs: 1, sm: 2, md: 3 },
            minHeight: "auto !important",
            gap: { xs: 0.5, sm: 1 },
            width: "100%",
            maxWidth: "none",
          }}
        >
          {/* Logo Section */}
          <Box
            onClick={() => navigate("/dashboard")}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: { xs: 1, sm: 1.5 },
              cursor: "pointer",
              userSelect: "none",
              flex: "0 0 auto",
              minWidth: 0,
              "&:hover": {
                transform: "scale(1.02)",
                transition: "transform 0.2s ease",
              },
            }}
          >
            <Box
              sx={{
                width: { xs: 32, sm: 38, md: 44 },
                height: { xs: 32, sm: 38, md: 44 },
                borderRadius: "12px", // Squircle
                background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: `0 8px 16px -4px ${theme.palette.primary.main}50`,
                position: "relative",
              }}
            >
              <CandlestickChartRounded
                sx={{
                  color: "white",
                  fontSize: { xs: 18, sm: 22, md: 26 },
                  zIndex: 1,
                }}
              />
            </Box>

            {!isVerySmall && (
              <Box sx={{ minWidth: 0, overflow: "hidden" }}>
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 800,
                    fontSize: {
                      xs: "1rem",
                      sm: "1.2rem",
                      md: "1.4rem",
                    },
                    background: `linear-gradient(135deg, ${theme.palette.text.primary}, ${theme.palette.text.secondary})`,
                    backgroundClip: "text",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    letterSpacing: "-0.03em",
                    lineHeight: 1,
                    whiteSpace: "nowrap",
                  }}
                >
                  GrowthQuantix
                </Typography>
                {!isXs && (
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                      fontSize: { sm: "0.65rem", md: "0.7rem" },
                      fontWeight: 600,
                      letterSpacing: "0.05em",
                      textTransform: "uppercase",
                      display: "block",
                      mt: 0.25,
                      opacity: 0.8,
                    }}
                  >
                    AI Trading System
                  </Typography>
                )}
              </Box>
            )}
          </Box>

          {/* Desktop Navigation */}
          {!isMd && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                bgcolor: "transparent",
                flex: "1 1 auto",
                maxWidth: "800px",
                mx: 2,
                overflow: "hidden",
                justifyContent: "center",
              }}
            >
              {navItems.map((item) => {
                const showFullText = !isLg;
                const showTooltip = isLg && !isActive(item.path);

                const pillContent = (
                  <Box
                    onClick={() => navigate(item.path)}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: showFullText ? 1 : 0,
                      px: showFullText ? 2 : 1.5,
                      py: 1,
                      borderRadius: "12px",
                      cursor: "pointer",
                      userSelect: "none",
                      transition: "all 0.2s ease-out",
                      position: "relative",
                      overflow: "hidden",
                      minWidth: showFullText ? "auto" : 40,
                      justifyContent: "center",

                      bgcolor: isActive(item.path)
                        ? `${item.color}15`
                        : "transparent",
                      color: isActive(item.path) ? item.color : "text.secondary",
                      border: isActive(item.path)
                        ? `1px solid ${item.color}30`
                        : "1px solid transparent",

                      "&:hover": {
                        bgcolor: isActive(item.path)
                          ? `${item.color}25`
                          : theme.palette.action.hover,
                        color: isActive(item.path) ? item.color : "text.primary",
                        transform: "translateY(-1px)",
                      },
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: isActive(item.path)
                          ? item.color
                          : "text.secondary",
                        "& svg": {
                          fontSize: { lg: 20, xl: 22 },
                          transition: "all 0.2s ease",
                        },
                      }}
                    >
                      {item.icon}
                    </Box>

                    {showFullText && (
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: isActive(item.path) ? 700 : 600,
                          fontSize: { lg: "0.85rem", xl: "0.9rem" },
                          color: "inherit",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {isLg ? item.shortName : item.name}
                      </Typography>
                    )}

                    {isActive(item.path) && !showFullText && (
                      <Box
                        sx={{
                          position: "absolute",
                          bottom: -8,
                          left: "50%",
                          transform: "translateX(-50%)",
                          width: 4,
                          height: 4,
                          borderRadius: "50%",
                          bgcolor: item.color,
                          boxShadow: `0 0 8px ${item.color}`,
                        }}
                      />
                    )}
                  </Box>
                );

                return showTooltip ? (
                  <Tooltip
                    key={item.path}
                    title={item.name}
                    arrow
                    placement="bottom"
                    enterDelay={200}
                    leaveDelay={100}
                    PopperProps={{
                      sx: {
                        "& .MuiTooltip-tooltip": {
                          bgcolor:
                            theme.palette.mode === "dark"
                              ? "rgba(255, 255, 255, 0.95)"
                              : "rgba(0, 0, 0, 0.9)",
                          color:
                            theme.palette.mode === "dark" ? "black" : "white",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          borderRadius: 2,
                          px: 1.5,
                          py: 0.75,
                          backdropFilter: "blur(10px)",
                          border: `1px solid ${theme.palette.divider}`,
                        },
                      },
                    }}
                  >
                    {pillContent}
                  </Tooltip>
                ) : (
                  <React.Fragment key={item.path}>{pillContent}</React.Fragment>
                );
              })}
            </Box>
          )}

          {/* Right Actions */}
          <Stack
            direction="row"
            spacing={{ xs: 0.5, sm: 1 }}
            alignItems="center"
            sx={{ flex: "0 0 auto" }}
          >
            {/* Status Chip */}
            <Chip
              icon={
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <span style={{ fontSize: "8px" }}>{statusInfo.icon}</span>
                </Box>
              }
              label={statusInfo.label}
              size="small"
              sx={{
                height: { xs: 24, sm: 28 },
                color: "white",
                fontWeight: 700,
                fontSize: { xs: "0.65rem", sm: "0.7rem" },
                bgcolor: `${statusInfo.color}.main`,
                border: "none",
                "& .MuiChip-icon": {
                  color: "white",
                  mr: 0.5,
                },
                "& .MuiChip-label": {
                  px: 1,
                },
              }}
            />

            <Stack direction="row" spacing={0.5}>
              {!isVerySmall && (
                <Tooltip title="Refresh Data">
                  <IconButton
                    size="small"
                    onClick={handleRefresh}
                    disabled={notificationLoading}
                    sx={{
                      width: { xs: 32, sm: 36, md: 40 },
                      height: { xs: 32, sm: 36, md: 40 },
                      bgcolor: "action.hover",
                      borderRadius: "10px",
                      "&:hover": {
                        bgcolor: "action.selected",
                        color: "primary.main",
                      },
                      transition: "all 0.2s ease",
                    }}
                  >
                    <RefreshRounded
                      sx={{
                        fontSize: { xs: 18, sm: 20, md: 22 },
                        animation: notificationLoading
                          ? "spin 1s linear infinite"
                          : "none",
                        "@keyframes spin": {
                          "0%": { transform: "rotate(0deg)" },
                          "100%": { transform: "rotate(360deg)" },
                        },
                      }}
                    />
                  </IconButton>
                </Tooltip>
              )}

              <Tooltip title="Notifications">
                <IconButton
                  size="small"
                  onClick={handleNotificationMenuOpen}
                  sx={{
                    width: { xs: 32, sm: 36, md: 40 },
                    height: { xs: 32, sm: 36, md: 40 },
                    bgcolor: "action.hover",
                    borderRadius: "10px",
                    "&:hover": {
                      bgcolor: "action.selected",
                      color: "primary.main",
                    },
                    transition: "all 0.2s ease",
                  }}
                >
                  <Badge
                    badgeContent={unreadCount}
                    color="error"
                    sx={{
                      "& .MuiBadge-badge": {
                        fontSize: "0.6rem",
                        height: 16,
                        minWidth: 16,
                      },
                    }}
                  >
                    <NotificationsRounded
                      sx={{ fontSize: { xs: 18, sm: 20, md: 22 } }}
                    />
                  </Badge>
                </IconButton>
              </Tooltip>

              {!isSm && <ThemeToggle />}

              <Tooltip title="Profile">
                <IconButton
                  onClick={(e) => setProfileMenuOpen(e.currentTarget)}
                  size="small"
                  sx={{
                    ml: 0.5,
                    p: 0,
                    border: `2px solid ${theme.palette.divider}`,
                    borderRadius: "50%",
                    "&:hover": {
                      borderColor: theme.palette.primary.main,
                    },
                  }}
                >
                  <Avatar
                    sx={{
                      width: { xs: 30, sm: 34, md: 38 },
                      height: { xs: 30, sm: 34, md: 38 },
                      bgcolor: "primary.main",
                      fontSize: { xs: "0.75rem", sm: "0.85rem" },
                      fontWeight: 700,
                    }}
                  >
                    {getUserInitials()}
                  </Avatar>
                </IconButton>
              </Tooltip>
            </Stack>
          </Stack>
        </Toolbar>
      </AppBar>

      {/* Mobile Bottom Navigation - Premium Glassmorphism */}
      {isMd && (
        <Paper
          sx={{
            position: "fixed",
            bottom: 0,
            left: 0,
            right: 0,
            zIndex: theme.zIndex.appBar,
            borderTop: `1px solid ${theme.palette.divider}`,
            background:
              theme.palette.mode === "dark"
                ? "rgba(15, 23, 42, 0.9)"
                : "rgba(255, 255, 255, 0.9)",
            backdropFilter: "blur(20px)",
            pb: "safe-area-inset-bottom", // Support for iPhone Home indicator
          }}
          elevation={4}
        >
          <BottomNavigation
            value={isMoreActive ? "more" : location.pathname}
            onChange={(event, newValue) => {
              if (newValue === "more") {
                setDrawerOpen(true);
              } else {
                navigate(newValue);
              }
            }}
            sx={{
              bgcolor: "transparent",
              height: 64, // Taller touch targets
              "& .MuiBottomNavigationAction-root": {
                minWidth: "auto",
                color: "text.secondary",
                padding: "6px 0 8px",
                "&.Mui-selected": {
                  color: theme.palette.primary.main,
                },
              },
              "& .MuiBottomNavigationAction-label": {
                fontSize: "0.7rem",
                fontWeight: 600,
                marginTop: 0.5,
                "&.Mui-selected": {
                  fontSize: "0.75rem",
                },
              },
            }}
          >
            {mobileNavItems.map((item) => (
              <BottomNavigationAction
                key={item.path}
                label={item.shortName}
                value={item.path}
                icon={
                  <Box
                    sx={{
                      p: 0.5,
                      borderRadius: "10px",
                      bgcolor: isActive(item.path)
                        ? `${item.color}20`
                        : "transparent",
                      color: isActive(item.path) ? item.color : "inherit",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {React.cloneElement(item.icon, {
                      fontSize: isActive(item.path) ? "medium" : "small",
                    })}
                  </Box>
                }
              />
            ))}
            <BottomNavigationAction
              label="More"
              value="more"
              icon={
                <Box
                  sx={{
                    p: 0.5,
                    borderRadius: "10px",
                    bgcolor: isMoreActive
                      ? `${theme.palette.primary.main}20`
                      : "transparent",
                    color: isMoreActive
                      ? theme.palette.primary.main
                      : "inherit",
                  }}
                >
                  <MoreHorizRounded />
                </Box>
              }
            />
          </BottomNavigation>
        </Paper>
      )}

      {/* Menus and Drawers (Profile, Notifications, Mobile Drawer) */}
      <Menu
        anchorEl={profileMenuOpen}
        open={Boolean(profileMenuOpen)}
        onClose={() => setProfileMenuOpen(null)}
        TransitionComponent={Fade}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        PaperProps={{
          elevation: 16,
          sx: {
            mt: 1.5,
            minWidth: { xs: 220, sm: 240, md: 260 },
            borderRadius: 4,
            bgcolor: "background.paper",
            border: `1px solid ${theme.palette.divider}`,
            boxShadow: `0 16px 40px ${theme.palette.action.hover}`,
            "& .MuiMenuItem-root": {
              px: 3,
              py: 1.5,
              borderRadius: 2,
              mx: 1,
              my: 0.5,
              fontWeight: 500,
              fontSize: "0.9rem",
            },
          },
        }}
      >
        <Box
          sx={{
            px: 3,
            py: 3,
            borderBottom: `1px solid ${theme.palette.divider}`,
            textAlign: "center",
          }}
        >
          <Avatar
            sx={{
              width: { xs: 48, sm: 56 },
              height: { xs: 48, sm: 56 },
              mx: "auto",
              mb: 1.5,
              bgcolor: "primary.main",
              fontSize: { xs: "1.25rem", sm: "1.35rem" },
              fontWeight: 700,
            }}
          >
            {getUserInitials()}
          </Avatar>
          <Typography
            variant="subtitle1"
            fontWeight={700}
            sx={{
              mb: 0.5,
              fontSize: "1rem",
            }}
          >
            {user?.full_name || user?.name || "User"}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {user?.email || "user@example.com"}
          </Typography>
          <Chip
            label={user?.role || "Trader"}
            size="small"
            color="primary"
            variant="outlined"
            sx={{ fontWeight: 600 }}
          />
        </Box>

        <MenuItem
          onClick={() => {
            navigate("/profile");
            setProfileMenuOpen(null);
          }}
        >
          <ListItemIcon>
            <PersonRounded fontSize="small" />
          </ListItemIcon>
          Profile Settings
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleLogout();
            setProfileMenuOpen(null);
          }}
        >
          <ListItemIcon>
            <LogoutRounded fontSize="small" />
          </ListItemIcon>
          Sign Out
        </MenuItem>
      </Menu>

      <Menu
        anchorEl={notificationMenuOpen}
        open={Boolean(notificationMenuOpen)}
        onClose={() => setNotificationMenuOpen(null)}
        TransitionComponent={Slide}
        TransitionProps={{ direction: "down" }}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        PaperProps={{
          elevation: 16,
          sx: {
            mt: 1.5,
            width: {
              xs: Math.min(window.innerWidth - 20, 320),
              sm: 360,
              md: 400,
            },
            maxHeight: { xs: "80vh", sm: 520 },
            borderRadius: 4,
            bgcolor: "background.paper",
            border: `1px solid ${theme.palette.divider}`,
            boxShadow: `0 16px 40px ${theme.palette.action.hover}`,
          },
        }}
      >
        <Box
          sx={{
            p: { xs: 2, sm: 3 },
            borderBottom: `1px solid ${theme.palette.divider}`,
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Typography variant="h6" fontWeight={700}>
                Notifications
              </Typography>
              {unreadCount > 0 && (
                <Chip
                  label={unreadCount}
                  size="small"
                  color="error"
                  sx={{ fontSize: "0.7rem", height: 20, fontWeight: 700 }}
                />
              )}
            </Box>
            {notifications.length > 0 && (
              <Button
                size="small"
                onClick={handleMarkAllAsRead}
                startIcon={<MarkEmailReadRounded sx={{ fontSize: 14 }} />}
                sx={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  borderRadius: 2,
                }}
              >
                Mark All Read
              </Button>
            )}
          </Box>
        </Box>

        <Box sx={{ maxHeight: { xs: "60vh", sm: 400 }, overflow: "auto" }}>
          {notificationLoading ? (
            <Box sx={{ p: 4, textAlign: "center" }}>
              <SpeedRounded
                sx={{
                  fontSize: 40,
                  color: "text.disabled",
                  mb: 2,
                  animation: "pulse 1.5s infinite",
                }}
              />
              <Typography variant="body2" color="text.secondary">
                Loading notifications...
              </Typography>
            </Box>
          ) : notifications.length === 0 ? (
            <Box sx={{ p: 6, textAlign: "center" }}>
              <NotificationsRounded
                sx={{
                  fontSize: 48,
                  color: "text.disabled",
                  mb: 2,
                }}
              />
              <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>
                All caught up!
              </Typography>
              <Typography variant="body2" color="text.secondary">
                No new notifications
              </Typography>
            </Box>
          ) : (
            notifications.map((notification, index) => (
              <Box
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                sx={{
                  px: { xs: 2, sm: 3 },
                  py: 2,
                  borderBottom: `1px solid ${theme.palette.divider}`,
                  cursor: "pointer",
                  "&:hover": { bgcolor: "action.hover" },
                  bgcolor: !notification.is_read
                    ? `${theme.palette.primary.main}08`
                    : "transparent",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 2,
                  }}
                >
                  <Box
                    sx={{
                      p: 0.5,
                      borderRadius: "50%",
                      bgcolor: `${getNotificationColor(notification.type)}15`,
                      color: getNotificationColor(notification.type),
                    }}
                  >
                    {/* Simplified icon usage */}
                    <NotificationsRounded fontSize="small" />
                  </Box>

                  <Box sx={{ flex: 1 }}>
                    <Typography variant="subtitle2" fontWeight={600}>
                      {notification.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {notification.message}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ mt: 0.5, display: "block" }}
                    >
                      {formatNotificationTime(notification.created_at)}
                    </Typography>
                  </Box>
                  <IconButton
                    size="small"
                    onClick={(e) =>
                      handleDeleteNotification(e, notification.id)
                    }
                  >
                    <DeleteRounded fontSize="small" />
                  </IconButton>
                </Box>
              </Box>
            ))
          )}
        </Box>
      </Menu>

      <Drawer
        anchor="bottom" // Bottom sheet on mobile, Right drawer on desktop (custom logic needed if splitting)
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            width: { xs: "100%", md: 360 },
            height: { xs: "auto", md: "100%" },
            maxHeight: { xs: "85vh", md: "100%" },
            bgcolor: "background.paper",
            borderRadius: { xs: "24px 24px 0 0", md: 0 },
            bottom: { xs: 0, md: "auto" },
            right: { xs: 0, md: 0 },
            position: "fixed",
          },
        }}
        // Using "bottom" anchor for simple mobile drawer, but logic above handles desktop/mobile styles
        // Actually, let's stick to Right anchor for simplicity or switch based on screen
      >
        <Box sx={{ p: 3, height: "100%", overflow: "auto" }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 3,
            }}
          >
            <Typography variant="h5" fontWeight={700}>
              Menu
            </Typography>
            <IconButton onClick={() => setDrawerOpen(false)}>
              <CloseRounded />
            </IconButton>
          </Box>

          <List>
            {navItems.map((item) => (
              <ListItemButton
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setDrawerOpen(false);
                }}
                selected={isActive(item.path)}
                sx={{
                  borderRadius: 3,
                  mb: 1,
                  bgcolor: isActive(item.path)
                    ? `${item.color}15`
                    : "transparent",
                  color: isActive(item.path) ? item.color : "text.primary",
                }}
              >
                <ListItemIcon
                  sx={{
                    color: "inherit",
                    minWidth: 40,
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.name}
                  primaryTypographyProps={{ fontWeight: 600 }}
                />
              </ListItemButton>
            ))}
          </List>
          
           <Divider sx={{ my: 2 }} />
           
           <Box sx={{ px: 2 }}>
             <Typography variant="subtitle2" color="text.secondary" gutterBottom>
               Settings
             </Typography>
             <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="body2" fontWeight={500}>Appearance</Typography>
                <ThemeToggle />
             </Box>
           </Box>
        </Box>
      </Drawer>

      <Box sx={{ height: { xs: 56, sm: 64, md: 72 } }} />
      {/* Spacer for Bottom Navigation on Mobile */}
      {isMd && <Box sx={{ height: 64, pb: "safe-area-inset-bottom" }} />}
    </>
  );
};

export default Navbar;
