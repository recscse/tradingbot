// src/pages/ProfilePage.jsx
import React, { useState, useEffect } from "react";
import { toast } from "react-hot-toast";
import { motion, AnimatePresence } from "framer-motion";
import { 
  RefreshCcw, 
  AlertCircle,
  Layout
} from "lucide-react";

import ProfileHeader from "../components/profile/ProfileHeader";
import ProfileTabs from "../components/profile/ProfileTabs";
import ProfileOverview from "../components/profile/ProfileOverview";
import ProfileSettings from "../components/profile/ProfileSettings";
import ProfileSecurity from "../components/profile/ProfileSecurity";
import ProfileNotifications from "../components/profile/ProfileNotifications";
import EnhancedBrokerManagement from "../components/profile/EnhancedBrokerManagement";
import PerformanceTab from "../components/profile/PerformanceTab";
import FundsTab from "../components/profile/FundsTab";
import { profileService } from "../services/profileService";

const ProfilePage = () => {
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

      const progressInterval = setInterval(() => {
        setLoadingProgress((prev) => Math.min(prev + 10, 90));
      }, 100);

      const [profile, stats, notificationsRes] = await Promise.all([
        profileService.getProfile(),
        profileService.getTradingStats(),
        profileService.getNotifications(),
      ]);

      clearInterval(progressInterval);
      setLoadingProgress(100);

      setProfileData(profile.data);
      setTradingStats(stats.data);
      setBrokerAccounts(profile.data.brokerAccounts || []);
      setNotifications(notificationsRes.data.notifications || []);

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
    const contentVariants = {
      hidden: { opacity: 0, x: 20 },
      visible: { opacity: 1, x: 0, transition: { duration: 0.3 } },
      exit: { opacity: 0, x: -20, transition: { duration: 0.2 } }
    };

    switch (activeTab) {
      case "overview":
        return (
          <motion.div variants={contentVariants} initial="hidden" animate="visible" exit="exit">
            <ProfileOverview
              profileData={profileData}
              tradingStats={tradingStats}
              brokerAccounts={brokerAccounts}
              onRefresh={fetchProfileData}
            />
          </motion.div>
        );
      case "performance":
        return (
          <motion.div variants={contentVariants} initial="hidden" animate="visible" exit="exit">
            <PerformanceTab profile={profileData} loading={loading} />
          </motion.div>
        );
      case "funds":
        return (
          <motion.div variants={contentVariants} initial="hidden" animate="visible" exit="exit">
            <FundsTab />
          </motion.div>
        );
      case "brokers":
        return (
          <motion.div variants={contentVariants} initial="hidden" animate="visible" exit="exit">
            <EnhancedBrokerManagement />
          </motion.div>
        );
      case "settings":
        return (
          <motion.div variants={contentVariants} initial="hidden" animate="visible" exit="exit">
            <ProfileSettings
              profileData={profileData}
              onUpdate={handleProfileUpdate}
              onAvatarUpload={handleAvatarUpload}
            />
          </motion.div>
        );
      case "security":
        return (
          <motion.div variants={contentVariants} initial="hidden" animate="visible" exit="exit">
            <ProfileSecurity
              profileData={profileData}
              onUpdate={handleProfileUpdate}
            />
          </motion.div>
        );
      case "notifications":
        return (
          <motion.div variants={contentVariants} initial="hidden" animate="visible" exit="exit">
            <ProfileNotifications
              notifications={notifications}
              onUpdate={setNotifications}
            />
          </motion.div>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="tw-min-h-screen tw-bg-slate-50 tw-dark:bg-slate-900 tw-flex tw-items-center tw-justify-center tw-p-4">
        <div className="tw-bg-white tw-dark:bg-slate-800 tw-p-8 tw-rounded-2xl tw-border tw-border-slate-200 tw-dark:border-slate-700 tw-shadow-xl tw-w-full tw-max-w-md tw-text-center">
          <motion.div 
            animate={{ scale: [1, 1.1, 1], rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="tw-inline-block tw-mb-6"
          >
            <Layout className="tw-w-16 tw-h-16 tw-text-indigo-600 tw-dark:text-indigo-400" />
          </motion.div>
          <h2 className="tw-text-xl tw-font-bold tw-text-slate-800 tw-dark:text-slate-100 tw-mb-4">
            Loading Command Center
          </h2>
          <div className="tw-w-full tw-h-2 tw-bg-slate-100 tw-dark:bg-slate-700 tw-rounded-full tw-overflow-hidden tw-mb-3">
            <motion.div 
              className="tw-h-full tw-bg-indigo-600"
              initial={{ width: "0%" }}
              animate={{ width: `${loadingProgress}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tw-min-h-screen tw-bg-slate-50 tw-dark:bg-slate-900 tw-flex tw-items-center tw-justify-center tw-p-4">
        <div className="tw-bg-white tw-dark:bg-slate-800 tw-p-8 tw-rounded-2xl tw-border tw-border-red-200 tw-dark:border-red-900/30 tw-shadow-xl tw-text-center">
          <AlertCircle className="tw-w-12 tw-h-12 tw-text-red-500 tw-mx-auto tw-mb-4" />
          <h2 className="tw-text-xl tw-font-bold tw-text-slate-800 tw-dark:text-slate-100 tw-mb-2">
            Connection Error
          </h2>
          <p className="tw-text-slate-500 tw-mb-6">{error}</p>
          <button
            onClick={fetchProfileData}
            className="tw-inline-flex tw-items-center tw-gap-2 tw-px-6 tw-py-2.5 tw-bg-indigo-600 tw-text-white tw-rounded-lg tw-font-medium tw-transition-colors tw-hover:bg-indigo-700"
          >
            <RefreshCcw className="tw-w-4 tw-h-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="tw-min-h-screen tw-bg-slate-50 tw-dark:bg-slate-950 tw-pb-12">
      <div className="tw-max-w-[1600px] tw-mx-auto tw-px-4 tw-sm:px-6 tw-lg:px-8 tw-py-6">
        
        {/* Header Section */}
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="tw-mb-6"
        >
          <ProfileHeader
            profileData={profileData}
            onAvatarUpload={handleAvatarUpload}
          />
        </motion.div>

        {/* Dashboard Grid Layout */}
        <div className="tw-grid tw-grid-cols-1 tw-lg:grid-cols-12 tw-gap-6 tw-items-start">
          
          {/* Sidebar Navigation (Desktop) / Tabs (Mobile) */}
          <motion.div 
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="tw-lg:col-span-3 tw-sticky tw-top-6"
          >
            <div className="tw-bg-white tw-dark:bg-slate-900 tw-rounded-2xl tw-border tw-border-slate-200 tw-dark:border-slate-800 tw-shadow-sm tw-p-2">
              <ProfileTabs
                activeTab={activeTab}
                onTabChange={setActiveTab}
                brokerCount={brokerAccounts?.length || 0}
                notificationCounts={{
                  unread: notifications?.filter((n) => !n.read)?.length || 0,
                }}
                securityAlerts={profileData?.securityAlerts || 0}
              />
            </div>
          </motion.div>

          {/* Main Content Area */}
          <motion.div 
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="tw-lg:col-span-9"
          >
            {/* Dynamic Content Header */}
            <div className="tw-mb-6">
              <h2 className="tw-text-2xl tw-font-bold tw-text-slate-900 tw-dark:text-white tw-capitalize">
                {activeTab}
              </h2>
              <p className="tw-text-slate-500 tw-dark:text-slate-400">
                {activeTab === "overview" && "Comprehensive view of your trading performance and account status."}
                {activeTab === "performance" && "Detailed analytics, P&L reports, and trade history."}
                {activeTab === "funds" && "Manage your trading capital, add funds, and view transaction logs."}
                {activeTab === "brokers" && "Manage your connected brokerage accounts and API keys."}
                {activeTab === "settings" && "Update your personal information and preferences."}
                {activeTab === "security" && "Manage password, 2FA, and security logs."}
                {activeTab === "notifications" && "View system alerts and activity logs."}
              </p>
            </div>

            <div className="tw-min-h-[600px]">
              <AnimatePresence mode="wait">
                {renderTabContent()}
              </AnimatePresence>
            </div>
          </motion.div>
          
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
