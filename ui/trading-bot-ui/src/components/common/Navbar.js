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
} from "@mui/material";
import {
  Menu as MenuIcon,
  Dashboard,
  Settings,
  Logout,
  Person,
  Notifications,
  Description,
  History,
  Refresh,
  Close,
  ShowChart,
  Assessment,
  Delete,
  MarkEmailRead,
  AccountBalance,
  Speed,
  AutoFixHigh,
  BarChart,
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
  const [currentTime, setCurrentTime] = useState(new Date());

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
      icon: <Dashboard />,
      color: "#1976d2",
      shortName: "Home",
    },
    {
      name: "Trade Control",
      path: "/trade-control",
      icon: <ShowChart />,
      color: "#2e7d32",
      shortName: "Trade",
    },
    {
      name: "Analytics",
      path: "/analysis",
      icon: <Assessment />,
      color: "#ed6c02",
      shortName: "Charts",
    },
    {
      name: "Performance",
      path: "/performance-analytics",
      icon: <BarChart />,
      color: "#0288d1",
      shortName: "Metrics",
    },
    {
      name: "Backtesting",
      path: "/backtesting",
      icon: <History />,
      color: "#9c27b0",
      shortName: "History",
    },
    {
      name: "Paper Trading",
      path: "/papertrading",
      icon: <Description />,
      color: "#d32f2f",
      shortName: "Paper",
    },
    {
      name: "Auto Trading",
      path: "/auto-trading",
      icon: <AutoFixHigh />,
      color: "#00796b",
      shortName: "Auto",
    },
    {
      name: "Settings",
      path: "/config",
      icon: <Settings />,
      color: "#616161",
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

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
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
      navigate("/login");
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

  return (
    <>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          bgcolor:
            theme.palette.mode === "dark"
              ? "rgba(15, 15, 15, 0.97)"
              : "rgba(255, 255, 255, 0.97)",
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
          <Box
            onClick={() => navigate("/dashboard")}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: { xs: 0.5, sm: 1, md: 1.5 },
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
                width: { xs: 28, sm: 36, md: 44 },
                height: { xs: 28, sm: 36, md: 44 },
                borderRadius: "50%",
                background: `conic-gradient(from 180deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main}, ${theme.palette.primary.main})`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: `0 4px 16px ${theme.palette.primary.main}30`,
                position: "relative",
                "&::before": {
                  content: '""',
                  position: "absolute",
                  inset: 2,
                  borderRadius: "50%",
                  background: theme.palette.background.paper,
                },
              }}
            >
              <AccountBalance
                sx={{
                  color: theme.palette.primary.main,
                  fontSize: { xs: 14, sm: 18, md: 22 },
                  zIndex: 1,
                }}
              />
            </Box>

            {!isVerySmall && (
              <Box sx={{ minWidth: 0, overflow: "hidden" }}>
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 900,
                    fontSize: {
                      xs: "0.85rem",
                      sm: "1.1rem",
                      md: "1.3rem",
                      lg: "1.4rem",
                    },
                    background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                    backgroundClip: "text",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    letterSpacing: "-0.02em",
                    lineHeight: 1.1,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  GrowthQuantix
                </Typography>
                {!isXs && (
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                      fontSize: { sm: "0.6rem", md: "0.65rem" },
                      fontWeight: 600,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      display: "block",
                      lineHeight: 1,
                      mt: -0.2,
                      whiteSpace: "nowrap",
                    }}
                  >
                    Automated Intelligent Trading System
                  </Typography>
                )}
              </Box>
            )}
          </Box>

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
                      px: showFullText ? 2.5 : 1.5,
                      py: 1.25,
                      borderRadius: 25,
                      cursor: "pointer",
                      userSelect: "none",
                      transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                      position: "relative",
                      overflow: "hidden",
                      minWidth: showFullText ? "auto" : 40,
                      justifyContent: "center",

                      bgcolor: isActive(item.path)
                        ? `${item.color}20`
                        : "transparent",
                      color: isActive(item.path) ? item.color : "text.primary",
                      border: isActive(item.path)
                        ? `1px solid ${item.color}40`
                        : "1px solid transparent",

                      "&:hover": {
                        bgcolor: isActive(item.path)
                          ? `${item.color}30`
                          : theme.palette.mode === "dark"
                          ? "rgba(255, 255, 255, 0.05)"
                          : "rgba(0, 0, 0, 0.04)",
                        transform: "translateY(-2px)",
                        boxShadow: isActive(item.path)
                          ? `0 8px 25px ${item.color}30`
                          : `0 4px 20px ${theme.palette.action.hover}`,
                      },

                      "&:active": {
                        transform: "translateY(0px)",
                      },

                      ...(isActive(item.path) && {
                        "&::before": {
                          content: '""',
                          position: "absolute",
                          inset: 0,
                          borderRadius: 25,
                          padding: "1px",
                          background: `linear-gradient(135deg, ${item.color}60, ${item.color}20)`,
                          mask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
                          maskComposite: "xor",
                          WebkitMask:
                            "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
                          WebkitMaskComposite: "xor",
                        },
                      }),
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
                          fontSize: { lg: 18, xl: 20 },
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
                          fontSize: { lg: "0.8rem", xl: "0.85rem" },
                          color: "inherit",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
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
                        "& .MuiTooltip-arrow": {
                          color:
                            theme.palette.mode === "dark"
                              ? "rgba(255, 255, 255, 0.95)"
                              : "rgba(0, 0, 0, 0.9)",
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

          <Stack
            direction="row"
            spacing={{ xs: 0.25, sm: 0.5, md: 1 }}
            alignItems="center"
            sx={{
              flex: "0 0 auto",
              minWidth: 0,
            }}
          >
            <Chip
              icon={
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <span style={{ fontSize: "6px" }}>{statusInfo.icon}</span>
                </Box>
              }
              label={statusInfo.label}
              size="small"
              sx={{
                height: { xs: 22, sm: 26, md: 28 },
                color: "white",
                fontWeight: 600,
                fontSize: { xs: "0.6rem", sm: "0.65rem", md: "0.7rem" },
                bgcolor: `${statusInfo.color}.main`,
                border: "none",
                "& .MuiChip-icon": {
                  color: "white",
                  mr: { xs: 0.25, sm: 0.5 },
                },
                "& .MuiChip-label": {
                  px: { xs: 0.5, sm: 0.75, md: 1 },
                },
              }}
            />

            <Stack direction="row" spacing={{ xs: 0.25, sm: 0.5 }}>
              {!isVerySmall && (
                <Tooltip title="Refresh Data" arrow>
                  <span>
                    <IconButton
                      size="small"
                      onClick={handleRefresh}
                      disabled={notificationLoading}
                      sx={{
                        width: { xs: 32, sm: 36, md: 40 },
                        height: { xs: 32, sm: 36, md: 40 },
                        bgcolor: "action.hover",
                        "&:hover": {
                          bgcolor: "action.selected",
                          transform: "scale(1.05)",
                        },
                        "&:disabled": {
                          bgcolor: "action.hover",
                          opacity: 0.6,
                        },
                        transition: "all 0.2s ease",
                      }}
                    >
                      <Refresh
                        sx={{
                          fontSize: { xs: 16, sm: 18, md: 20 },
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
                  </span>
                </Tooltip>
              )}

              <Tooltip title="Notifications" arrow>
                <IconButton
                  size="small"
                  onClick={handleNotificationMenuOpen}
                  sx={{
                    width: { xs: 32, sm: 36, md: 40 },
                    height: { xs: 32, sm: 36, md: 40 },
                    bgcolor: "action.hover",
                    "&:hover": {
                      bgcolor: "action.selected",
                      transform: "scale(1.05)",
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
                        minWidth: { xs: 14, sm: 16 },
                        height: { xs: 14, sm: 16 },
                        fontWeight: 700,
                      },
                    }}
                  >
                    <Notifications
                      sx={{ fontSize: { xs: 16, sm: 18, md: 20 } }}
                    />
                  </Badge>
                </IconButton>
              </Tooltip>

              {!isSm && (
                <Box>
                  <ThemeToggle />
                </Box>
              )}

              <Tooltip title={user?.full_name || user?.name || "Profile"} arrow>
                <IconButton
                  onClick={(e) => setProfileMenuOpen(e.currentTarget)}
                  size="small"
                  sx={{
                    "&:hover": {
                      transform: "scale(1.05)",
                    },
                    transition: "all 0.2s ease",
                  }}
                >
                  <Avatar
                    sx={{
                      width: { xs: 28, sm: 32, md: 36 },
                      height: { xs: 28, sm: 32, md: 36 },
                      bgcolor: "primary.main",
                      fontSize: {
                        xs: "0.7rem",
                        sm: "0.8rem",
                        md: "0.875rem",
                      },
                      fontWeight: 700,
                      border: `2px solid ${theme.palette.divider}`,
                    }}
                  >
                    {getUserInitials()}
                  </Avatar>
                </IconButton>
              </Tooltip>

              {isMd && (
                <IconButton
                  onClick={() => setDrawerOpen(true)}
                  sx={{
                    width: { xs: 32, sm: 36, md: 40 },
                    height: { xs: 32, sm: 36, md: 40 },
                    bgcolor: "action.hover",
                    "&:hover": {
                      bgcolor: "action.selected",
                    },
                  }}
                >
                  <MenuIcon sx={{ fontSize: { xs: 16, sm: 18, md: 20 } }} />
                </IconButton>
              )}
            </Stack>
          </Stack>
        </Toolbar>
      </AppBar>

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
              fontSize: "1.25rem",
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
              fontSize: { xs: "0.9rem", sm: "1rem" },
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {user?.full_name || user?.name || "User"}
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mb: 1,
              fontSize: { xs: "0.75rem", sm: "0.875rem" },
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
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
            <Person fontSize="small" />
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
            <Logout fontSize="small" />
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
              <Typography
                variant="h6"
                fontWeight={700}
                sx={{ fontSize: { xs: "1rem", sm: "1.25rem" } }}
              >
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
                startIcon={<MarkEmailRead sx={{ fontSize: 14 }} />}
                sx={{
                  fontSize: { xs: "0.7rem", sm: "0.75rem" },
                  fontWeight: 600,
                  borderRadius: 2,
                  px: { xs: 1, sm: 1.5 },
                }}
              >
                Mark All Read
              </Button>
            )}
          </Box>
        </Box>

        <Box sx={{ maxHeight: { xs: "60vh", sm: 400 }, overflow: "auto" }}>
          {notificationLoading ? (
            <Box sx={{ p: { xs: 4, sm: 6 }, textAlign: "center" }}>
              <Speed
                sx={{
                  fontSize: { xs: 36, sm: 48 },
                  color: "text.disabled",
                  mb: 2,
                  animation: "pulse 1.5s ease-in-out infinite",
                  "@keyframes pulse": {
                    "0%": { opacity: 1 },
                    "50%": { opacity: 0.5 },
                    "100%": { opacity: 1 },
                  },
                }}
              />
              <Typography variant="body2" color="text.secondary">
                Loading notifications...
              </Typography>
            </Box>
          ) : notifications.length === 0 ? (
            <Box sx={{ p: { xs: 4, sm: 6 }, textAlign: "center" }}>
              <Notifications
                sx={{
                  fontSize: { xs: 48, sm: 64 },
                  color: "text.disabled",
                  mb: 2,
                }}
              />
              <Typography
                variant="h6"
                fontWeight={600}
                sx={{
                  mb: 1,
                  fontSize: { xs: "1rem", sm: "1.25rem" },
                }}
              >
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
                  py: { xs: 1.5, sm: 2 },
                  borderBottom:
                    index < notifications.length - 1
                      ? `1px solid ${theme.palette.divider}`
                      : "none",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  "&:hover": {
                    bgcolor: "action.hover",
                    transform: "translateX(4px)",
                  },
                  position: "relative",
                  bgcolor: !notification.is_read
                    ? `${theme.palette.primary.main}08`
                    : "transparent",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: { xs: 1.5, sm: 2 },
                  }}
                >
                  <Box
                    sx={{
                      width: { xs: 28, sm: 32 },
                      height: { xs: 28, sm: 32 },
                      borderRadius: "50%",
                      bgcolor: `${getNotificationColor(notification.type)}15`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: { xs: "12px", sm: "14px" },
                      mt: 0.5,
                      border: `2px solid ${getNotificationColor(
                        notification.type
                      )}30`,
                    }}
                  >
                    {getNotificationIcon(notification.type)}
                  </Box>

                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="subtitle2"
                      fontWeight={600}
                      sx={{
                        mb: 0.5,
                        lineHeight: 1.3,
                        fontSize: { xs: "0.8rem", sm: "0.875rem" },
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {notification.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mb: 1,
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                        lineHeight: 1.4,
                        fontSize: { xs: "0.75rem", sm: "0.875rem" },
                      }}
                    >
                      {notification.message ||
                        notification.body ||
                        "No message"}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        fontWeight: 500,
                        fontSize: { xs: "0.65rem", sm: "0.7rem" },
                      }}
                    >
                      {formatNotificationTime(notification.created_at)}
                    </Typography>
                  </Box>

                  <Box
                    sx={{ display: "flex", flexDirection: "column", gap: 1 }}
                  >
                    {!notification.is_read && (
                      <Box
                        sx={{
                          width: { xs: 8, sm: 10 },
                          height: { xs: 8, sm: 10 },
                          borderRadius: "50%",
                          bgcolor: "primary.main",
                          boxShadow: `0 0 8px ${theme.palette.primary.main}50`,
                        }}
                      />
                    )}
                    <IconButton
                      size="small"
                      onClick={(e) =>
                        handleDeleteNotification(e, notification.id)
                      }
                      sx={{
                        width: { xs: 20, sm: 24 },
                        height: { xs: 20, sm: 24 },
                        opacity: 0.6,
                        "&:hover": {
                          opacity: 1,
                          bgcolor: "error.main",
                          color: "white",
                        },
                        transition: "all 0.2s ease",
                      }}
                    >
                      <Delete sx={{ fontSize: { xs: 12, sm: 16 } }} />
                    </IconButton>
                  </Box>
                </Box>
              </Box>
            ))
          )}
        </Box>
      </Menu>

      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            width: { xs: "100%", sm: 360 },
            bgcolor: "background.paper",
          },
        }}
      >
        <Box
          sx={{
            p: { xs: 2, sm: 3 },
            height: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 3,
            }}
          >
            <Typography
              variant="h5"
              fontWeight={700}
              sx={{ fontSize: { xs: "1.25rem", sm: "1.5rem" } }}
            >
              Menu
            </Typography>
            <IconButton
              onClick={() => setDrawerOpen(false)}
              sx={{
                bgcolor: "action.hover",
                "&:hover": { bgcolor: "action.selected" },
              }}
            >
              <Close />
            </IconButton>
          </Box>

          <Paper
            elevation={0}
            sx={{
              p: { xs: 2, sm: 3 },
              mb: 3,
              textAlign: "center",
              bgcolor: "action.hover",
              borderRadius: 4,
              border: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Avatar
              sx={{
                width: { xs: 64, sm: 72 },
                height: { xs: 64, sm: 72 },
                mx: "auto",
                mb: 2,
                bgcolor: "primary.main",
                fontSize: { xs: "1.5rem", sm: "1.75rem" },
                fontWeight: 700,
                border: `3px solid ${theme.palette.primary.main}20`,
              }}
            >
              {getUserInitials()}
            </Avatar>
            <Typography
              variant="h6"
              fontWeight={700}
              sx={{
                mb: 0.5,
                fontSize: { xs: "1rem", sm: "1.25rem" },
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user?.full_name || user?.name || "User"}
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                mb: 2,
                fontSize: { xs: "0.75rem", sm: "0.875rem" },
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user?.email || "user@example.com"}
            </Typography>
            <Stack
              direction="row"
              spacing={1}
              justifyContent="center"
              sx={{
                flexWrap: "wrap",
                gap: 1,
                "& > *": {
                  fontSize: { xs: "0.7rem", sm: "0.75rem" },
                },
              }}
            >
              <Chip
                label={user?.role || "Trader"}
                size="small"
                color="primary"
                variant="outlined"
                sx={{ fontWeight: 600 }}
              />
              <Chip
                icon={
                  <span style={{ fontSize: "8px" }}>{statusInfo.icon}</span>
                }
                label={statusInfo.label}
                size="small"
                color={statusInfo.color}
                variant="outlined"
                sx={{ fontWeight: 600 }}
              />
            </Stack>
          </Paper>

          <Box sx={{ flex: 1, overflow: "auto" }}>
            <List sx={{ p: 0 }}>
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
                    py: { xs: 1.5, sm: 2 },
                    px: 2,
                    transition: "all 0.3s ease",
                    "&.Mui-selected": {
                      bgcolor: `${item.color}15`,
                      borderLeft: `4px solid ${item.color}`,
                      "&:hover": { bgcolor: `${item.color}25` },
                    },
                    "&:hover": {
                      transform: "translateX(8px)",
                      bgcolor: "action.hover",
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: isActive(item.path)
                        ? item.color
                        : "text.secondary",
                      minWidth: { xs: 40, sm: 48 },
                      "& svg": {
                        fontSize: { xs: 20, sm: 24 },
                      },
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.name}
                    primaryTypographyProps={{
                      fontWeight: isActive(item.path) ? 700 : 500,
                      color: isActive(item.path) ? item.color : "text.primary",
                      fontSize: { xs: "0.9rem", sm: "1rem" },
                    }}
                  />
                  {item.path === "/dashboard" && unreadCount > 0 && (
                    <Badge badgeContent={unreadCount} color="error" />
                  )}
                </ListItemButton>
              ))}
            </List>

            <Divider sx={{ my: 3 }} />

            <List sx={{ p: 0 }}>
              <ListItemButton
                sx={{
                  borderRadius: 3,
                  py: { xs: 1.5, sm: 2 },
                  px: 2,
                  mb: 1,
                  "&:hover": {
                    transform: "translateX(8px)",
                    bgcolor: "action.hover",
                  },
                  transition: "all 0.3s ease",
                }}
              >
                <ListItemIcon sx={{ minWidth: { xs: 40, sm: 48 } }}>
                  <Settings sx={{ fontSize: { xs: 20, sm: 24 } }} />
                </ListItemIcon>
                <ListItemText
                  primary="Theme"
                  primaryTypographyProps={{
                    fontWeight: 500,
                    fontSize: { xs: "0.9rem", sm: "1rem" },
                  }}
                />
                <Box sx={{ ml: 1 }}>
                  <ThemeToggle />
                </Box>
              </ListItemButton>

              <ListItemButton
                onClick={() => {
                  handleRefresh();
                  setDrawerOpen(false);
                }}
                disabled={notificationLoading}
                sx={{
                  borderRadius: 3,
                  py: { xs: 1.5, sm: 2 },
                  px: 2,
                  mb: 1,
                  "&:hover": {
                    transform: "translateX(8px)",
                    bgcolor: "action.hover",
                  },
                  "&:disabled": {
                    opacity: 0.6,
                    "&:hover": {
                      transform: "none",
                      bgcolor: "transparent",
                    },
                  },
                  transition: "all 0.3s ease",
                }}
              >
                <ListItemIcon sx={{ minWidth: { xs: 40, sm: 48 } }}>
                  <Refresh
                    sx={{
                      fontSize: { xs: 20, sm: 24 },
                      animation: notificationLoading
                        ? "spin 1s linear infinite"
                        : "none",
                      "@keyframes spin": {
                        "0%": { transform: "rotate(0deg)" },
                        "100%": { transform: "rotate(360deg)" },
                      },
                    }}
                  />
                </ListItemIcon>
                <ListItemText
                  primary={
                    notificationLoading ? "Refreshing..." : "Refresh Data"
                  }
                  primaryTypographyProps={{
                    fontWeight: 500,
                    fontSize: { xs: "0.9rem", sm: "1rem" },
                  }}
                />
              </ListItemButton>

              <ListItemButton
                onClick={() => {
                  navigate("/profile");
                  setDrawerOpen(false);
                }}
                sx={{
                  borderRadius: 3,
                  py: { xs: 1.5, sm: 2 },
                  px: 2,
                  mb: 1,
                  "&:hover": {
                    transform: "translateX(8px)",
                    bgcolor: "action.hover",
                  },
                  transition: "all 0.3s ease",
                }}
              >
                <ListItemIcon sx={{ minWidth: { xs: 40, sm: 48 } }}>
                  <Person sx={{ fontSize: { xs: 20, sm: 24 } }} />
                </ListItemIcon>
                <ListItemText
                  primary="Profile Settings"
                  primaryTypographyProps={{
                    fontWeight: 500,
                    fontSize: { xs: "0.9rem", sm: "1rem" },
                  }}
                />
              </ListItemButton>

              <ListItemButton
                onClick={() => {
                  handleLogout();
                  setDrawerOpen(false);
                }}
                sx={{
                  borderRadius: 3,
                  py: { xs: 1.5, sm: 2 },
                  px: 2,
                  color: "error.main",
                  "&:hover": {
                    transform: "translateX(8px)",
                    bgcolor: "error.main",
                    color: "white",
                    "& .MuiListItemIcon-root": {
                      color: "white",
                    },
                  },
                  transition: "all 0.3s ease",
                }}
              >
                <ListItemIcon
                  sx={{ minWidth: { xs: 40, sm: 48 }, color: "error.main" }}
                >
                  <Logout sx={{ fontSize: { xs: 20, sm: 24 } }} />
                </ListItemIcon>
                <ListItemText
                  primary="Sign Out"
                  primaryTypographyProps={{
                    fontWeight: 500,
                    fontSize: { xs: "0.9rem", sm: "1rem" },
                  }}
                />
              </ListItemButton>
            </List>
          </Box>

          <Box sx={{ mt: 2, textAlign: "center" }}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
            >
              {currentTime.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              display="block"
              sx={{ fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
            >
              {currentTime.toLocaleDateString()}
            </Typography>
          </Box>
        </Box>
      </Drawer>

      <Box sx={{ height: { xs: 56, sm: 64, md: 72 } }} />
    </>
  );
};

export default Navbar;
