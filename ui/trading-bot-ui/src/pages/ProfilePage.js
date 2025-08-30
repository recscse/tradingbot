// src/pages/ProfilePage.jsx
import React, { useState, useEffect } from "react";
import {
  Box,
  Container, // Reserved for loading states
  /* CircularProgress, */ Typography, // Reserved for modal backgrounds // Reserved for card layouts
  /* Backdrop, */ /* Card, */ Button,
  useTheme,
  alpha,
  Paper,
  Fade,
  LinearProgress,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  Error as ErrorIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import { toast } from "react-hot-toast";
import ProfileHeader from "../components/profile/ProfileHeader";
import ProfileTabs from "../components/profile/ProfileTabs";
import ProfileOverview from "../components/profile/ProfileOverview";
import ProfileSettings from "../components/profile/ProfileSettings";
import ProfileSecurity from "../components/profile/ProfileSecurity";
import ProfileNotifications from "../components/profile/ProfileNotifications";
// import BrokerManagement from "../components/profile/BrokerManagement";
import EnhancedBrokerManagement from "../components/profile/EnhancedBrokerManagement";
import PerformanceTab from "../components/profile/PerformanceTab";
import { profileService } from "../services/profileService";

const ProfilePage = () => {
  const theme = useTheme();

  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [tradingStats, setTradingStats] = useState(null);
  const [brokerAccounts, setBrokerAccounts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loadingProgress, setLoadingProgress] = useState(0);

  useEffect(() => {
    fetchProfileData();
  }, []);

  const fetchProfileData = async () => {
    try {
      setLoading(true);
      setError(null);
      setLoadingProgress(0);

      // Simulate loading progress for better UX
      const progressInterval = setInterval(() => {
        setLoadingProgress((prev) => Math.min(prev + 10, 90));
      }, 100);

      const [profile, stats, notifications] = await Promise.all([
        profileService.getProfile(),
        profileService.getTradingStats(),
        profileService.getNotifications(),
      ]);

      clearInterval(progressInterval);
      setLoadingProgress(100);

      setProfileData(profile.data);
      setTradingStats(stats.data);
      setBrokerAccounts(profile.data.brokerAccounts || []);
      setNotifications(notifications.data.notifications || []);

      // Brief delay to show completion
      setTimeout(() => {
        setLoading(false);
      }, 300);
    } catch (error) {
      console.error("Error fetching profile data:", error);
      setError("Unable to load profile data");
      toast.error("Failed to load profile data");
      setLoading(false);
    }
  };

  const handleProfileUpdate = async (updatedData) => {
    try {
      const response = await profileService.updateProfile(updatedData);
      setProfileData((prev) => ({ ...prev, ...response.data }));
      toast.success("Profile updated successfully");
    } catch (error) {
      console.error("Error updating profile:", error);
      toast.error("Failed to update profile");
    }
  };

  const handleAvatarUpload = async (file) => {
    try {
      const formData = new FormData();
      formData.append("avatar", file);
      const response = await profileService.uploadAvatar(formData);
      setProfileData((prev) => ({ ...prev, avatar: response.data.avatarUrl }));
      toast.success("Avatar updated successfully");
    } catch (error) {
      console.error("Error uploading avatar:", error);
      toast.error("Failed to upload avatar");
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case "overview":
        return (
          <ProfileOverview
            profileData={profileData}
            tradingStats={tradingStats}
            brokerAccounts={brokerAccounts}
            onRefresh={fetchProfileData}
          />
        );
      case "performance":
        return <PerformanceTab profile={profileData} loading={loading} />;
      case "brokers":
        return <EnhancedBrokerManagement />;
      case "settings":
        return (
          <ProfileSettings
            profileData={profileData}
            onUpdate={handleProfileUpdate}
            onAvatarUpload={handleAvatarUpload}
          />
        );
      case "security":
        return (
          <ProfileSecurity
            profileData={profileData}
            onUpdate={handleProfileUpdate}
          />
        );
      case "notifications":
        return (
          <ProfileNotifications
            notifications={notifications}
            onUpdate={setNotifications}
          />
        );
      default:
        return null;
    }
  };

  // Enhanced Loading with progress
  if (loading) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "background.default",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: 6,
            borderRadius: 4,
            textAlign: "center",
            bgcolor: alpha(theme.palette.background.paper, 0.9),
            backdropFilter: "blur(20px)",
            border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
            minWidth: 300,
          }}
        >
          <TrendingUpIcon
            sx={{
              fontSize: 48,
              color: "primary.main",
              mb: 2,
              animation: "pulse 2s infinite",
            }}
          />
          <Typography
            variant="h6"
            sx={{
              mb: 3,
              color: "text.primary",
              fontWeight: 600,
            }}
          >
            Loading Your Trading Profile
          </Typography>
          <Box sx={{ width: "100%", mb: 2 }}>
            <LinearProgress
              variant="determinate"
              value={loadingProgress}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                "& .MuiLinearProgress-bar": {
                  borderRadius: 4,
                  background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                },
              }}
            />
          </Box>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ fontSize: "0.875rem" }}
          >
            {loadingProgress < 30
              ? "Connecting to servers..."
              : loadingProgress < 60
              ? "Fetching account data..."
              : loadingProgress < 90
              ? "Loading trading statistics..."
              : "Almost ready..."}
          </Typography>
        </Paper>
        <style jsx global>{`
          @keyframes pulse {
            0% {
              transform: scale(1);
              opacity: 1;
            }
            50% {
              transform: scale(1.1);
              opacity: 0.7;
            }
            100% {
              transform: scale(1);
              opacity: 1;
            }
          }
        `}</style>
      </Box>
    );
  }

  // Enhanced Error State
  if (error) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "background.default",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: 6,
            borderRadius: 4,
            textAlign: "center",
            bgcolor: alpha(theme.palette.background.paper, 0.9),
            backdropFilter: "blur(20px)",
            border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
            maxWidth: 400,
            mx: 2,
          }}
        >
          <ErrorIcon
            sx={{
              fontSize: 64,
              color: "error.main",
              mb: 2,
              opacity: 0.8,
            }}
          />
          <Typography
            variant="h5"
            gutterBottom
            sx={{
              fontWeight: 600,
              color: "text.primary",
            }}
          >
            Oops! Something went wrong
          </Typography>
          <Typography
            color="text.secondary"
            sx={{
              mb: 4,
              fontSize: "1rem",
              lineHeight: 1.6,
            }}
          >
            {error}
          </Typography>
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={fetchProfileData}
            size="large"
            sx={{
              px: 4,
              py: 1.5,
              borderRadius: 3,
              textTransform: "none",
              fontWeight: 600,
              boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.3)}`,
              "&:hover": {
                transform: "translateY(-2px)",
                boxShadow: `0 6px 16px ${alpha(
                  theme.palette.primary.main,
                  0.4
                )}`,
              },
            }}
          >
            Try Again
          </Button>
        </Paper>
      </Box>
    );
  }

  return (
    <Fade in={true} timeout={600}>
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "background.default",
          backgroundImage: `radial-gradient(circle at 20% 80%, ${alpha(
            theme.palette.primary.main,
            0.05
          )} 0%, transparent 50%),
                           radial-gradient(circle at 80% 20%, ${alpha(
                             theme.palette.secondary.main,
                             0.05
                           )} 0%, transparent 50%)`,
        }}
      >
        <Container
          maxWidth="xl"
          sx={{
            py: { xs: 3, sm: 4 },
            px: { xs: 2, sm: 3 },
          }}
        >
          {/* Profile Header */}
          <Box sx={{ mb: { xs: 3, sm: 4 } }}>
            <ProfileHeader
              profileData={profileData}
              onAvatarUpload={handleAvatarUpload}
            />
          </Box>

          {/* Main Content with enhanced styling */}
          <Paper
            elevation={0}
            sx={{
              borderRadius: { xs: 2, sm: 3 },
              overflow: "hidden",
              bgcolor: alpha(theme.palette.background.paper, 0.8),
              backdropFilter: "blur(20px)",
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              boxShadow: `0 8px 32px ${alpha(theme.palette.common.black, 0.1)}`,
            }}
          >
            <Box sx={{ p: { xs: 3, sm: 4 } }}>
              <ProfileTabs
                activeTab={activeTab}
                onTabChange={setActiveTab}
                brokerCount={brokerAccounts?.length || 0}
                notificationCounts={{
                  unread: notifications?.filter((n) => !n.read)?.length || 0,
                }}
                securityAlerts={profileData?.securityAlerts || 0}
              />

              <Box sx={{ mt: { xs: 3, sm: 4 } }}>
                <Fade in={true} key={activeTab} timeout={300}>
                  <Box>{renderTabContent()}</Box>
                </Fade>
              </Box>
            </Box>
          </Paper>
        </Container>
      </Box>
    </Fade>
  );
};

export default ProfilePage;
