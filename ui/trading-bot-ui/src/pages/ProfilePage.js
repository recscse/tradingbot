// src/pages/ProfilePage.jsx
import React, { useState, useEffect } from "react";
import {
  Box,
  Container,
  CircularProgress,
  Typography,
  Backdrop,
  Card,
  Button,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  Error as ErrorIcon,
} from "@mui/icons-material";
import { toast } from "react-hot-toast";
import ProfileHeader from "../components/profile/ProfileHeader";
import ProfileTabs from "../components/profile/ProfileTabs";
import ProfileOverview from "../components/profile/ProfileOverview";
import ProfileSettings from "../components/profile/ProfileSettings";
import ProfileSecurity from "../components/profile/ProfileSecurity";
import ProfileNotifications from "../components/profile/ProfileNotifications";
import BrokerManagement from "../components/profile/BrokerManagement";
import PerformanceTab from "../components/profile/PerformanceTab";
import { profileService } from "../services/profileService";

const ProfilePage = () => {
  // const theme = useTheme();

  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [tradingStats, setTradingStats] = useState(null);
  const [brokerAccounts, setBrokerAccounts] = useState([]);
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    fetchProfileData();
  }, []);

  const fetchProfileData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [profile, stats, notifications] = await Promise.all([
        profileService.getProfile(),
        profileService.getTradingStats(),
        profileService.getNotifications(),
      ]);

      setProfileData(profile.data);
      setTradingStats(stats.data);
      setBrokerAccounts(profile.data.brokerAccounts || []);
      setNotifications(notifications.data.notifications || []);
    } catch (error) {
      console.error("Error fetching profile data:", error);
      setError("Unable to load profile data");
      toast.error("Failed to load profile data");
    } finally {
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
        return <BrokerManagement />;
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

  // Simple Loading
  if (loading) {
    return (
      <Backdrop
        open={true}
        sx={{ zIndex: 9999, bgcolor: "rgba(255,255,255,0.9)" }}
      >
        <Box sx={{ textAlign: "center" }}>
          <CircularProgress size={50} />
          <Typography sx={{ mt: 2, color: "text.primary" }}>
            Loading...
          </Typography>
        </Box>
      </Backdrop>
    );
  }

  // Simple Error
  if (error) {
    return (
      <Container maxWidth="sm" sx={{ py: 8, textAlign: "center" }}>
        <ErrorIcon sx={{ fontSize: 64, color: "error.main", mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Error Loading Profile
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          {error}
        </Typography>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={fetchProfileData}
        >
          Retry
        </Button>
      </Container>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Container
        maxWidth="xl"
        sx={{
          py: { xs: 2, sm: 3 },
          px: { xs: 1, sm: 2 },
        }}
      >
        {/* Profile Header */}
        <Box sx={{ mb: { xs: 2, sm: 3 } }}>
          <ProfileHeader
            profileData={profileData}
            onAvatarUpload={handleAvatarUpload}
          />
        </Box>

        {/* Main Content */}
        <Card
          sx={{
            borderRadius: { xs: 1, sm: 2 },
            overflow: "hidden",
          }}
        >
          <Box sx={{ p: { xs: 2, sm: 3 } }}>
            <ProfileTabs activeTab={activeTab} onTabChange={setActiveTab} />

            <Box sx={{ mt: { xs: 2, sm: 3 } }}>{renderTabContent()}</Box>
          </Box>
        </Card>
      </Container>
    </Box>
  );
};

export default ProfilePage;
