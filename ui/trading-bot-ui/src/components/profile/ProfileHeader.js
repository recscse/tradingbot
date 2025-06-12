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
        borderRadius: 3,
        border: `1px solid ${theme.palette.divider}`,
        overflow: "hidden",
        position: "relative",
        bgcolor: "background.paper",
      }}
    >
      {/* Header Section */}
      <Box
        sx={{
          height: { xs: 100, sm: 120 },
          background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
          position: "relative",
        }}
      />

      {/* Main Content */}
      <Box sx={{ p: { xs: 3, sm: 4 }, bgcolor: "background.paper" }}>
        {/* Profile Info Section */}
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={{ xs: 3, sm: 4 }}
          alignItems={{ xs: "center", sm: "flex-start" }}
          sx={{ mt: { xs: -6, sm: -7 } }}
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
                width: { xs: 110, sm: 130 },
                height: { xs: 110, sm: 130 },
                fontSize: { xs: "2.5rem", sm: "3rem" },
                fontWeight: 700,
                bgcolor: theme.palette.primary.main,
                cursor: "pointer",
                border: `5px solid ${theme.palette.background.paper}`,
                boxShadow: theme.shadows[6],
                transition: "transform 0.2s ease",
                "&:hover": { transform: "scale(1.02)" },
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
            {/* Name */}
            <Typography
              variant="h3"
              component="h1"
              sx={{
                fontWeight: 800,
                mb: 1,
                fontSize: { xs: "2rem", sm: "2.5rem" },
                color: "text.primary",
                lineHeight: 1.2,
                wordBreak: "break-word",
              }}
            >
              {profileData?.full_name || <Skeleton width={250} />}
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

        {/* Stats Grid */}
        <Grid
          container
          spacing={{ xs: 2, sm: 3 }}
          sx={{ mt: { xs: 4, sm: 5 } }}
        >
          {/* Brokers */}
          <Grid item xs={6} sm={3}>
            <Card
              variant="outlined"
              sx={{
                textAlign: "center",
                p: { xs: 2, sm: 3 },
                transition: "all 0.3s ease",
                bgcolor: "background.paper",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow: theme.shadows[8],
                  borderColor: "primary.main",
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
                p: { xs: 2, sm: 3 },
                transition: "all 0.3s ease",
                bgcolor: "background.paper",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow: theme.shadows[8],
                  borderColor:
                    (profileData?.todayPnl || 0) >= 0
                      ? "success.main"
                      : "error.main",
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
                p: { xs: 2, sm: 3 },
                transition: "all 0.3s ease",
                bgcolor: "background.paper",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow: theme.shadows[8],
                  borderColor: "info.main",
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
                p: { xs: 2, sm: 3 },
                transition: "all 0.3s ease",
                bgcolor: "background.paper",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow: theme.shadows[8],
                  borderColor: "warning.main",
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
