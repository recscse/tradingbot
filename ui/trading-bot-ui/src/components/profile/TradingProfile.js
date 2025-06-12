// src/components/profile/TradingProfile.jsx
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  AppBar,
  Toolbar,
  Container,
  IconButton,
  Badge,
  Button,
  Paper,
  Alert,
  Snackbar,
  Backdrop,
  CircularProgress,
  useTheme,
  alpha,
  useMediaQuery,
  Fade,
  Slide,
  Card,
  CardContent,
  Avatar,
  Tooltip,
  Stack,
  Skeleton,
  Chip,
  LinearProgress,
  FormControl,
  Select,
  MenuItem,
  Breadcrumbs,
  Link,
} from "@mui/material";
import {
  Dashboard as DashboardIcon,
  TrendingUp as TrendingUpIcon,
  Business as BuildingIcon,
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
  Edit as EditIcon,
  Close as CloseIcon,
  Refresh as RefreshIcon,
  Error as ErrorIcon,
  AccountCircle as ProfileIcon,
  Assessment as AnalyticsIcon,
  Home as HomeIcon,
  KeyboardArrowRight as ArrowIcon,
  ExpandMore as ExpandMoreIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  Menu as MenuIcon,
} from "@mui/icons-material";

// Import improved components
import ProfileHeader from "./ProfileHeader";
import BrokerManagement from "./BrokerManagement";
import PerformanceTab from "./PerformanceTab";
import ProfileSettings from "./ProfileSettings";
import ProfileSecurity from "./ProfileSecurity";
import ProfileOverview from "./ProfileOverview";
import ProfileNotifications from "./ProfileNotifications";
import ProfileTabs from "./ProfileTabs";

import { profileService } from "../../services/profileService";
import { useNotification } from "../../hooks/useNotification";
import { toast } from "react-hot-toast";

const TradingProfile = ({
  initialTab = "overview",
  onTabChange: externalOnTabChange,
  userId = null,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const isSmallMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const isTablet = useMediaQuery(theme.breakpoints.down("lg"));

  // Enhanced state management
  const [profile, setProfile] = useState(null);
  const [editedProfile, setEditedProfile] = useState({});
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [isEditing, setIsEditing] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [brokers, setBrokers] = useState([]);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  const { showNotification } = useNotification();

  // Tab configuration with dynamic data
  const tabsConfig = useMemo(
    () => [
      {
        id: "overview",
        label: "Overview",
        icon: DashboardIcon,
        color: "primary",
        description: "Account summary, performance metrics, and quick insights",
        component: ProfileOverview,
        badge: null,
      },
      {
        id: "performance",
        label: "Performance",
        icon: AnalyticsIcon,
        color: "success",
        description: "Trading analytics, P&L reports, and performance metrics",
        component: PerformanceTab,
        badge: null,
      },
      {
        id: "brokers",
        label: "Brokers",
        icon: BuildingIcon,
        color: "info",
        description: `Manage ${
          brokers.length || 0
        } broker connections and trading accounts`,
        component: BrokerManagement,
        badge: brokers.length > 0 ? brokers.length : null,
      },
      {
        id: "settings",
        label: "Profile",
        icon: ProfileIcon,
        color: "secondary",
        description: "Personal information, preferences, and account settings",
        component: ProfileSettings,
        badge: null,
      },
      {
        id: "security",
        label: "Security",
        icon: SecurityIcon,
        color: "error",
        description:
          "Password, two-factor authentication, and security settings",
        component: ProfileSecurity,
        badge: getSecurityAlerts(),
        urgent: getSecurityAlerts() > 0,
      },
      {
        id: "notifications",
        label: "Notifications",
        icon: NotificationsIcon,
        color: "warning",
        description: "Alert preferences, notification history, and settings",
        component: ProfileNotifications,
        badge: getUnreadNotificationCount(),
      },
    ],
    [brokers.length, profile]
  );

  // Helper functions for dynamic data
  function getUnreadNotificationCount() {
    return Array.isArray(notifications)
      ? notifications.filter((n) => !n.read && !n.is_read).length
      : 0;
  }

  function getSecurityAlerts() {
    if (!profile) return 0;
    let alerts = 0;

    // Check for security issues
    if (!profile.twoFactorEnabled && !profile.two_factor_enabled) alerts++;
    if (profile.failed_login_attempts > 0) alerts++;
    if (!profile.isVerified && !profile.is_verified && !profile.email_verified)
      alerts++;

    return alerts;
  }

  // Fetch data functions with better error handling
  const fetchProfile = useCallback(
    async (showLoading = true) => {
      try {
        if (showLoading) setLoading(true);
        setError(null);

        const response = await profileService.getProfile(userId);
        if (response.success && response.data) {
          setProfile(response.data);
          setEditedProfile(response.data);
          setLastRefresh(new Date());
        } else {
          throw new Error(response.error || "Failed to fetch profile");
        }
      } catch (error) {
        console.error("Error fetching profile:", error);
        const errorMessage =
          error?.response?.data?.message ||
          error?.message ||
          "Failed to load profile data";
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        if (showLoading) setLoading(false);
      }
    },
    [userId]
  );

  const fetchNotifications = useCallback(async () => {
    try {
      const response = await profileService.getNotifications();
      if (response.success && response.data) {
        setNotifications(response.data.notifications || response.data);
      }
    } catch (error) {
      console.error("Error fetching notifications:", error);
      // Don't show error for notifications as it's not critical
    }
  }, []);

  const fetchBrokers = useCallback(async () => {
    try {
      const response = await profileService.getBrokers();
      if (response.success && response.data) {
        setBrokers(response.data.brokers || response.data);
      }
    } catch (error) {
      console.error("Error fetching brokers:", error);
      // Don't show error for brokers as it's not critical
    }
  }, []);

  // Initialize data on mount
  useEffect(() => {
    const initializeData = async () => {
      await Promise.allSettled([
        fetchProfile(),
        fetchNotifications(),
        fetchBrokers(),
      ]);
    };

    initializeData();
  }, [fetchProfile, fetchNotifications, fetchBrokers]);

  // Handle external tab changes
  useEffect(() => {
    if (externalOnTabChange) {
      externalOnTabChange(activeTab);
    }
  }, [activeTab, externalOnTabChange]);

  // Snackbar helpers
  const showSnackbar = useCallback((message, severity = "success") => {
    setSnackbar({ open: true, message, severity });
  }, []);

  const handleCloseSnackbar = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  // Profile update handlers
  const handleSaveProfile = async (profileData = editedProfile) => {
    try {
      setUpdating(true);
      const response = await profileService.updateProfile(profileData);

      if (response.success && response.data) {
        setProfile(response.data);
        setEditedProfile(response.data);
        setIsEditing(false);
        toast.success("Profile updated successfully!");
        showSnackbar("Profile updated successfully!", "success");
      } else {
        throw new Error(response.error || "Failed to update profile");
      }
    } catch (error) {
      console.error("Error updating profile:", error);
      const errorMessage =
        error?.response?.data?.message ||
        error?.message ||
        "Failed to update profile";
      toast.error(errorMessage);
      showSnackbar(errorMessage, "error");
    } finally {
      setUpdating(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedProfile(profile || {});
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    // Scroll to top when changing tabs
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleRefreshAll = async () => {
    toast.promise(
      Promise.allSettled([
        fetchProfile(false),
        fetchNotifications(),
        fetchBrokers(),
      ]),
      {
        loading: "Refreshing data...",
        success: "Data refreshed successfully!",
        error: "Some data failed to refresh",
      }
    );
  };

  // Enhanced Loading Screen Component
  const LoadingScreen = () => (
    <Backdrop
      sx={{
        color: "#fff",
        zIndex: theme.zIndex.drawer + 1,
        background: `linear-gradient(135deg, ${alpha(
          theme.palette.primary.main,
          0.8
        )} 0%, ${alpha(theme.palette.secondary.main, 0.8)} 100%)`,
        backdropFilter: "blur(20px)",
      }}
      open={loading && !profile}
    >
      <Fade in={loading && !profile} timeout={300}>
        <Paper
          elevation={0}
          sx={{
            p: 4,
            borderRadius: 4,
            backgroundColor: alpha(theme.palette.background.paper, 0.1),
            backdropFilter: "blur(10px)",
            border: `1px solid ${alpha(theme.palette.common.white, 0.1)}`,
            textAlign: "center",
            maxWidth: 400,
          }}
        >
          <CircularProgress
            size={80}
            thickness={3}
            sx={{
              color: "white",
              filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.3))",
              mb: 3,
            }}
          />

          <Typography
            variant="h5"
            sx={{
              color: "white",
              fontWeight: 700,
              textShadow: "0 2px 4px rgba(0,0,0,0.3)",
              mb: 2,
            }}
          >
            Loading Trading Profile
          </Typography>

          <Typography
            variant="body2"
            sx={{
              color: alpha(theme.palette.common.white, 0.8),
              lineHeight: 1.5,
            }}
          >
            Please wait while we fetch your trading data, broker connections,
            and account information...
          </Typography>

          <LinearProgress
            sx={{
              mt: 3,
              borderRadius: 1,
              height: 4,
              bgcolor: alpha(theme.palette.common.white, 0.2),
              "& .MuiLinearProgress-bar": {
                bgcolor: "white",
              },
            }}
          />
        </Paper>
      </Fade>
    </Backdrop>
  );

  // Enhanced Error Screen Component
  const ErrorScreen = () => (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: `linear-gradient(135deg, ${alpha(
          theme.palette.error.main,
          0.05
        )} 0%, ${alpha(theme.palette.warning.main, 0.05)} 100%)`,
        p: 2,
      }}
    >
      <Fade in={true} timeout={500}>
        <Card
          sx={{
            maxWidth: 500,
            width: "100%",
            textAlign: "center",
            borderRadius: 4,
            border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
          }}
        >
          <CardContent sx={{ p: 4 }}>
            <Avatar
              sx={{
                width: 80,
                height: 80,
                mx: "auto",
                mb: 3,
                bgcolor: alpha(theme.palette.error.main, 0.1),
                color: "error.main",
              }}
            >
              <ErrorIcon sx={{ fontSize: 40 }} />
            </Avatar>

            <Typography variant="h5" fontWeight={700} gutterBottom>
              Unable to Load Profile
            </Typography>

            <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
              {error || "Something went wrong while loading your profile data."}
            </Typography>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
              Please check your internet connection and try again. If the
              problem persists, contact support.
            </Typography>

            <Stack direction="row" spacing={2} justifyContent="center">
              <Button
                variant="outlined"
                startIcon={<HomeIcon />}
                onClick={() => (window.location.href = "/")}
                sx={{ borderRadius: 2 }}
              >
                Go Home
              </Button>

              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={() => fetchProfile()}
                sx={{ borderRadius: 2, fontWeight: 600 }}
              >
                Try Again
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Fade>
    </Box>
  );

  // Enhanced Tab Content Renderer
  const renderTabContent = () => {
    const activeTabConfig = tabsConfig.find((tab) => tab.id === activeTab);
    if (!activeTabConfig) return null;

    const TabComponent = activeTabConfig.component;
    const commonProps = {
      profile,
      loading: updating,
      error: null,
      onUpdate: handleSaveProfile,
    };

    switch (activeTab) {
      case "overview":
        return (
          <TabComponent
            {...commonProps}
            notifications={notifications}
            brokers={brokers}
            onRefresh={handleRefreshAll}
          />
        );
      case "performance":
        return <TabComponent {...commonProps} brokers={brokers} />;
      case "brokers":
        return (
          <TabComponent
            {...commonProps}
            brokers={brokers}
            onBrokersUpdate={fetchBrokers}
          />
        );
      case "settings":
        return (
          <TabComponent
            profileData={profile}
            onUpdate={handleSaveProfile}
            onDeleteAccount={async () => {
              // Handle account deletion
              toast.error("Account deletion not implemented yet");
            }}
            loading={updating}
            error={error}
          />
        );
      case "security":
        return (
          <TabComponent
            profileData={profile}
            onUpdate={async (securityData) => {
              // Handle security updates
              await handleSaveProfile({ ...profile, ...securityData });
            }}
            loading={updating}
            error={error}
          />
        );
      case "notifications":
        return (
          <TabComponent
            notifications={notifications}
            onUpdate={async (notificationSettings) => {
              // Handle notification settings update
              await handleSaveProfile({ ...profile, notificationSettings });
            }}
            onMarkAsRead={async (notificationId) => {
              // Handle mark as read
              try {
                await profileService.markNotificationAsRead(notificationId);
                await fetchNotifications();
              } catch (error) {
                console.error("Failed to mark notification as read:", error);
              }
            }}
            onDeleteNotification={async (notificationId) => {
              // Handle delete notification
              try {
                await profileService.deleteNotification(notificationId);
                await fetchNotifications();
              } catch (error) {
                console.error("Failed to delete notification:", error);
              }
            }}
            loading={updating}
            error={error}
          />
        );
      default:
        return null;
    }
  };

  // Show loading screen for initial load
  if (loading && !profile) {
    return <LoadingScreen />;
  }

  // Show error screen if critical error
  if (error && !profile) {
    return <ErrorScreen />;
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: `linear-gradient(135deg, ${alpha(
          theme.palette.primary.main,
          0.02
        )} 0%, ${alpha(theme.palette.secondary.main, 0.02)} 100%)`,
        position: "relative",
      }}
    >
      {/* Enhanced Header */}
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          backgroundColor: alpha(theme.palette.background.paper, 0.9),
          backdropFilter: "blur(20px)",
          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          color: "text.primary",
        }}
      >
        <Toolbar sx={{ px: { xs: 2, sm: 3 } }}>
          <Box sx={{ flexGrow: 1 }}>
            {/* Breadcrumb Navigation */}
            {!isSmallMobile && (
              <Breadcrumbs
                separator={<ArrowIcon fontSize="small" />}
                sx={{ mb: 1 }}
              >
                <Link
                  color="inherit"
                  href="/"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    textDecoration: "none",
                    "&:hover": { textDecoration: "underline" },
                  }}
                >
                  <HomeIcon sx={{ mr: 0.5, fontSize: 16 }} />
                  Dashboard
                </Link>
                <Typography color="text.primary" sx={{ fontWeight: 600 }}>
                  Profile
                </Typography>
              </Breadcrumbs>
            )}

            <Typography
              variant={isSmallMobile ? "h6" : "h5"}
              component="h1"
              fontWeight={700}
              sx={{
                background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Trading Profile
            </Typography>

            {!isSmallMobile && (
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="body2" color="text.secondary">
                  Manage your trading account and preferences
                </Typography>

                <Chip
                  label={`Last updated: ${lastRefresh.toLocaleTimeString()}`}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: "0.7rem", height: 20 }}
                />
              </Stack>
            )}
          </Box>

          {/* Action Buttons */}
          <Stack direction="row" alignItems="center" spacing={1}>
            <Tooltip title="Refresh Data">
              <IconButton
                color="inherit"
                onClick={handleRefreshAll}
                disabled={updating}
                sx={{
                  "&:hover": {
                    backgroundColor: alpha(theme.palette.primary.main, 0.1),
                  },
                }}
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="Notifications">
              <IconButton
                color="inherit"
                onClick={() => handleTabChange("notifications")}
                sx={{
                  "&:hover": {
                    backgroundColor: alpha(theme.palette.primary.main, 0.1),
                  },
                }}
              >
                <Badge
                  badgeContent={getUnreadNotificationCount()}
                  color="error"
                >
                  <NotificationsIcon />
                </Badge>
              </IconButton>
            </Tooltip>

            {activeTab === "settings" && (
              <Button
                variant={isEditing ? "outlined" : "contained"}
                color={isEditing ? "inherit" : "primary"}
                startIcon={isEditing ? <CloseIcon /> : <EditIcon />}
                onClick={() => setIsEditing(!isEditing)}
                disabled={updating}
                sx={{
                  borderRadius: 2,
                  fontWeight: 600,
                  px: { xs: 2, sm: 3 },
                  fontSize: { xs: "0.75rem", sm: "0.875rem" },
                }}
              >
                {isEditing ? "Cancel" : "Edit"}
              </Button>
            )}
          </Stack>
        </Toolbar>

        {/* Loading Progress Bar */}
        {updating && (
          <LinearProgress
            sx={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              height: 2,
            }}
          />
        )}
      </AppBar>

      <Container maxWidth="xl" sx={{ py: { xs: 2, sm: 4 } }}>
        {/* Profile Header */}
        <Slide direction="down" in={true} timeout={500}>
          <Box sx={{ mb: 4 }}>
            <ProfileHeader
              profile={profile}
              editedProfile={editedProfile}
              setEditedProfile={setEditedProfile}
              isEditing={isEditing}
              onSave={handleSaveProfile}
              onCancel={handleCancelEdit}
              loading={updating}
              brokers={brokers}
              securityAlerts={getSecurityAlerts()}
            />
          </Box>
        </Slide>

        {/* Enhanced Navigation Tabs */}
        <Slide direction="up" in={true} timeout={700}>
          <Box sx={{ mb: 4 }}>
            <ProfileTabs
              activeTab={activeTab}
              onTabChange={handleTabChange}
              loading={updating}
              notificationCounts={{ unread: getUnreadNotificationCount() }}
              securityAlerts={getSecurityAlerts()}
              brokerCount={brokers.length}
            />
          </Box>
        </Slide>

        {/* Tab Content */}
        <Fade in={true} timeout={1000}>
          <Box>{renderTabContent()}</Box>
        </Fade>
      </Container>

      {/* Enhanced Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{
            borderRadius: 2,
            minWidth: 300,
            boxShadow: theme.shadows[6],
          }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TradingProfile;
