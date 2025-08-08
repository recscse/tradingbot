// src/components/profile/ProfileHeader.jsx
import React, { useRef, useState } from "react";
import {
  Box,
  Avatar,
  Typography,
  Chip,
  Grid,
  Card,
  Badge,
  IconButton,
  Tooltip,
  useTheme,
  alpha,
  Skeleton,
  Backdrop,
  CircularProgress,
  Stack,
} from "@mui/material";
import {
  CameraAlt as CameraIcon,
  Verified as VerifiedIcon,
  Security as SecurityIcon,
  AccountBalance as AccountBalanceIcon,
  TrendingUp as TrendingUpIcon,
  Login as LoginIcon,
  Business as BusinessIcon,
} from "@mui/icons-material";

const ProfileHeader = ({ profileData, onAvatarUpload }) => {
  const theme = useTheme();
  const fileInputRef = useRef(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      setUploadingAvatar(true);
      try {
        await onAvatarUpload(file);
      } finally {
        setUploadingAvatar(false);
      }
    }
  };

  const getInitials = (name) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0";
    return `₹${Math.abs(amount).toLocaleString("en-IN")}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return "Today";
    try {
      return new Date(dateString).toLocaleDateString("en-IN", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return "Today";
    }
  };

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 4,
        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        overflow: "hidden",
        position: "relative",
        bgcolor: alpha(theme.palette.background.paper, 0.9),
        backdropFilter: "blur(20px)",
        boxShadow: `0 8px 32px ${alpha(theme.palette.common.black, 0.1)}`,
      }}
    >
      {/* Enhanced Header Section with trading theme */}
      <Box
        sx={{
          height: { xs: 120, sm: 140 },
          background: `linear-gradient(135deg, 
            ${theme.palette.primary.main} 0%, 
            ${theme.palette.primary.dark} 50%, 
            ${theme.palette.secondary.main} 100%)`,
          position: "relative",
          "&::before": {
            content: '""',
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M20 20c0-11.046-8.954-20-20-20v20h20zM0 20v20h20c0-11.046-8.954-20-20-20z'/%3E%3C/g%3E%3C/svg%3E")`,
          }
        }}
      />

      {/* Main Content */}
      <Box sx={{ p: { xs: 4, sm: 5 }, bgcolor: alpha(theme.palette.background.paper, 0.95) }}>
        {/* Profile Info Section */}
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={{ xs: 4, sm: 5 }}
          alignItems={{ xs: "center", sm: "flex-start" }}
          sx={{ mt: { xs: -7, sm: -8 } }}
        >
          {/* Avatar */}
          <Badge
            overlap="circular"
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            badgeContent={
              uploadingAvatar ? (
                <Box
                  sx={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    bgcolor: "background.paper",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: `3px solid ${theme.palette.background.paper}`,
                    boxShadow: theme.shadows[2],
                  }}
                >
                  <CircularProgress size={18} />
                </Box>
              ) : (
                <Tooltip title="Change Avatar">
                  <IconButton
                    onClick={handleAvatarClick}
                    sx={{
                      bgcolor: "primary.main",
                      color: "white",
                      width: 36,
                      height: 36,
                      border: `3px solid ${theme.palette.background.paper}`,
                      boxShadow: theme.shadows[2],
                      "&:hover": {
                        bgcolor: "primary.dark",
                        transform: "scale(1.05)",
                      },
                    }}
                  >
                    <CameraIcon sx={{ fontSize: 18 }} />
                  </IconButton>
                </Tooltip>
              )
            }
          >
            <Avatar
              src={profileData?.avatar}
              onClick={handleAvatarClick}
              sx={{
                width: { xs: 120, sm: 140 },
                height: { xs: 120, sm: 140 },
                fontSize: { xs: "2.8rem", sm: "3.2rem" },
                fontWeight: 700,
                bgcolor: theme.palette.primary.main,
                cursor: "pointer",
                border: `6px solid ${theme.palette.background.paper}`,
                boxShadow: `0 8px 24px ${alpha(theme.palette.common.black, 0.2)}`,
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                "&:hover": { 
                  transform: "scale(1.05) translateY(-4px)",
                  boxShadow: `0 12px 32px ${alpha(theme.palette.common.black, 0.3)}`
                },
              }}
            >
              {getInitials(profileData?.full_name)}
            </Avatar>
          </Badge>

          {/* User Info */}
          <Box
            sx={{
              flex: 1,
              textAlign: { xs: "center", sm: "left" },
              minWidth: 0,
              pt: { xs: 0, sm: 2 },
            }}
          >
            {/* Name with enhanced styling */}
            <Typography
              variant="h3"
              component="h1"
              sx={{
                fontWeight: 800,
                mb: 1.5,
                fontSize: { xs: "2.2rem", sm: "2.8rem" },
                color: "text.primary",
                lineHeight: 1.1,
                wordBreak: "break-word",
                background: `linear-gradient(135deg, ${theme.palette.text.primary} 0%, ${theme.palette.primary.main} 100%)`,
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                textShadow: "none",
              }}
            >
              {profileData?.full_name || <Skeleton width={280} />}
            </Typography>

            {/* Email */}
            {profileData?.email && (
              <Typography
                variant="h6"
                color="text.secondary"
                sx={{
                  mb: 3,
                  fontSize: { xs: "1rem", sm: "1.1rem" },
                  fontWeight: 500,
                }}
              >
                {profileData.email}
              </Typography>
            )}

            {/* Status Badges */}
            <Stack
              direction="row"
              spacing={1.5}
              justifyContent={{ xs: "center", sm: "flex-start" }}
              flexWrap="wrap"
              sx={{ gap: 1.5 }}
            >
              <Chip
                label={profileData?.is_active ? "Active" : "Inactive"}
                color={profileData?.is_active ? "success" : "default"}
                sx={{
                  fontWeight: 600,
                  fontSize: "0.875rem",
                  height: 32,
                }}
              />

              {profileData?.isVerified && (
                <Chip
                  icon={<VerifiedIcon />}
                  label="Verified"
                  color="success"
                  sx={{
                    fontWeight: 600,
                    fontSize: "0.875rem",
                    height: 32,
                  }}
                />
              )}

              {profileData?.twoFactorEnabled && (
                <Chip
                  icon={<SecurityIcon />}
                  label="2FA Secured"
                  color="secondary"
                  sx={{
                    fontWeight: 600,
                    fontSize: "0.875rem",
                    height: 32,
                  }}
                />
              )}
            </Stack>
          </Box>
        </Stack>

        {/* Enhanced Stats Grid */}
        <Grid
          container
          spacing={{ xs: 2, sm: 3 }}
          sx={{ mt: { xs: 5, sm: 6 } }}
        >
          {/* Brokers */}
          <Grid item xs={6} sm={3}>
            <Card
              variant="outlined"
              sx={{
                textAlign: "center",
                p: { xs: 2.5, sm: 3 },
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                bgcolor: alpha(theme.palette.background.paper, 0.8),
                backdropFilter: "blur(10px)",
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                borderRadius: 3,
                "&:hover": {
                  transform: "translateY(-6px)",
                  boxShadow: `0 12px 24px ${alpha(theme.palette.primary.main, 0.2)}`,
                  borderColor: alpha(theme.palette.primary.main, 0.5),
                  bgcolor: alpha(theme.palette.primary.main, 0.02),
                },
              }}
            >
              <AccountBalanceIcon
                color="primary"
                sx={{ mb: 2, fontSize: { xs: 28, sm: 32 } }}
              />
              <Typography
                variant="h4"
                fontWeight={700}
                sx={{
                  fontSize: { xs: "1.5rem", sm: "2rem" },
                  mb: 1,
                  color: "text.primary",
                }}
              >
                {profileData?.brokerAccounts?.length || 0}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontSize: { xs: "0.8rem", sm: "0.875rem" },
                  fontWeight: 500,
                }}
              >
                Brokers
              </Typography>
            </Card>
          </Grid>

          {/* Today's P&L */}
          <Grid item xs={6} sm={3}>
            <Card
              variant="outlined"
              sx={{
                textAlign: "center",
                p: { xs: 2.5, sm: 3 },
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                bgcolor: alpha(theme.palette.background.paper, 0.8),
                backdropFilter: "blur(10px)",
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                borderRadius: 3,
                "&:hover": {
                  transform: "translateY(-6px)",
                  boxShadow: `0 12px 24px ${alpha(
                    (profileData?.todayPnl || 0) >= 0 
                      ? theme.palette.success.main 
                      : theme.palette.error.main, 
                    0.2
                  )}`,
                  borderColor: alpha(
                    (profileData?.todayPnl || 0) >= 0 
                      ? theme.palette.success.main 
                      : theme.palette.error.main, 
                    0.5
                  ),
                  bgcolor: alpha(
                    (profileData?.todayPnl || 0) >= 0 
                      ? theme.palette.success.main 
                      : theme.palette.error.main, 
                    0.02
                  ),
                },
              }}
            >
              <TrendingUpIcon
                color={(profileData?.todayPnl || 0) >= 0 ? "success" : "error"}
                sx={{ mb: 2, fontSize: { xs: 28, sm: 32 } }}
              />
              <Typography
                variant="h4"
                fontWeight={700}
                sx={{
                  fontSize: { xs: "1.5rem", sm: "2rem" },
                  mb: 1,
                  color:
                    (profileData?.todayPnl || 0) >= 0
                      ? "success.main"
                      : "error.main",
                }}
              >
                {formatCurrency(profileData?.todayPnl)}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontSize: { xs: "0.8rem", sm: "0.875rem" },
                  fontWeight: 500,
                }}
              >
                Today's P&L
              </Typography>
            </Card>
          </Grid>

          {/* Last Login */}
          <Grid item xs={6} sm={3}>
            <Card
              variant="outlined"
              sx={{
                textAlign: "center",
                p: { xs: 2.5, sm: 3 },
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                bgcolor: alpha(theme.palette.background.paper, 0.8),
                backdropFilter: "blur(10px)",
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                borderRadius: 3,
                "&:hover": {
                  transform: "translateY(-6px)",
                  boxShadow: `0 12px 24px ${alpha(theme.palette.info.main, 0.2)}`,
                  borderColor: alpha(theme.palette.info.main, 0.5),
                  bgcolor: alpha(theme.palette.info.main, 0.02),
                },
              }}
            >
              <LoginIcon
                color="info"
                sx={{ mb: 2, fontSize: { xs: 28, sm: 32 } }}
              />
              <Typography
                variant="h4"
                fontWeight={700}
                sx={{
                  fontSize: { xs: "1.5rem", sm: "2rem" },
                  mb: 1,
                  color: "text.primary",
                }}
              >
                {formatDate(profileData?.last_login)}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontSize: { xs: "0.8rem", sm: "0.875rem" },
                  fontWeight: 500,
                }}
              >
                Last Login
              </Typography>
            </Card>
          </Grid>

          {/* Account Type */}
          <Grid item xs={6} sm={3}>
            <Card
              variant="outlined"
              sx={{
                textAlign: "center",
                p: { xs: 2.5, sm: 3 },
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                bgcolor: alpha(theme.palette.background.paper, 0.8),
                backdropFilter: "blur(10px)",
                border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                borderRadius: 3,
                "&:hover": {
                  transform: "translateY(-6px)",
                  boxShadow: `0 12px 24px ${alpha(theme.palette.warning.main, 0.2)}`,
                  borderColor: alpha(theme.palette.warning.main, 0.5),
                  bgcolor: alpha(theme.palette.warning.main, 0.02),
                },
              }}
            >
              <BusinessIcon
                color="warning"
                sx={{ mb: 2, fontSize: { xs: 28, sm: 32 } }}
              />
              <Typography
                variant="h4"
                fontWeight={700}
                sx={{
                  fontSize: { xs: "1.5rem", sm: "2rem" },
                  mb: 1,
                  color: "text.primary",
                }}
              >
                {profileData?.role || "Trader"}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontSize: { xs: "0.8rem", sm: "0.875rem" },
                  fontWeight: 500,
                }}
              >
                Account Type
              </Typography>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Upload Backdrop */}
      <Backdrop
        open={uploadingAvatar}
        sx={{
          position: "absolute",
          zIndex: theme.zIndex.modal,
          bgcolor: alpha("#000", 0.5),
          borderRadius: 3,
        }}
      >
        <CircularProgress color="primary" />
      </Backdrop>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
    </Card>
  );
};

export default ProfileHeader;
