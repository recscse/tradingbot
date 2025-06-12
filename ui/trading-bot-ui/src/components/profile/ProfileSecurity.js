// src/components/profile/ProfileSecurity.jsx
import React, { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  InputAdornment,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  Avatar,
  Alert,
  Divider,
  useTheme,
  alpha,
  Fade,
  useMediaQuery,
  CircularProgress,
  Grid,
  Stack,
  Paper,
  Skeleton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import {
  Security as SecurityIcon,
  Lock as LockIcon,
  VpnKey as KeyIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Warning as AlertIcon,
  PhoneIphone as SmartphoneIcon,
  Settings as SettingsIcon,
  Login as LoginIcon,
  Shield as ShieldIcon,
  VerifiedUser as VerifiedIcon,
  History as HistoryIcon,
  QrCode as QrCodeIcon,
} from "@mui/icons-material";
import { toast } from "react-hot-toast";
import { profileService } from "../../services/profileService";

const ProfileSecurity = ({
  profileData = {},
  onUpdate = () => {},
  loading = false,
  error = null,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md"));

  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [updating, setUpdating] = useState(false);
  const [twoFactorDialog, setTwoFactorDialog] = useState(false);
  const [localError, setLocalError] = useState("");
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  // Password strength requirements
  const passwordRequirements = [
    { test: (pwd) => pwd.length >= 8, label: "At least 8 characters" },
    { test: (pwd) => /[A-Z]/.test(pwd), label: "One uppercase letter" },
    { test: (pwd) => /[a-z]/.test(pwd), label: "One lowercase letter" },
    { test: (pwd) => /[0-9]/.test(pwd), label: "One number" },
    { test: (pwd) => /[^A-Za-z0-9]/.test(pwd), label: "One special character" },
  ];

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordForm((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear local error when user starts typing
    if (localError) setLocalError("");
  };

  const validatePassword = () => {
    if (!passwordForm.current_password?.trim()) {
      setLocalError("Current password is required");
      return false;
    }
    if (!passwordForm.new_password?.trim()) {
      setLocalError("New password is required");
      return false;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setLocalError("New passwords do not match");
      return false;
    }
    if (passwordForm.new_password.length < 8) {
      setLocalError("Password must be at least 8 characters long");
      return false;
    }
    const passedRequirements = passwordRequirements.filter((req) =>
      req.test(passwordForm.new_password)
    ).length;
    if (passedRequirements < 4) {
      setLocalError("Password must meet at least 4 requirements");
      return false;
    }
    return true;
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();

    if (!validatePassword()) return;

    setUpdating(true);
    setLocalError("");

    try {
      await profileService.updateSecuritySettings(passwordForm);
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
      toast.success("Password updated successfully");
      if (onUpdate) await onUpdate();
    } catch (error) {
      console.error("Password update error:", error);
      const errorMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        "Failed to update password";
      setLocalError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setUpdating(false);
    }
  };

  const togglePasswordVisibility = (field) => {
    setShowPasswords((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const getPasswordStrength = (password) => {
    if (!password) return 0;
    return passwordRequirements.filter((req) => req.test(password)).length;
  };

  const getStrengthInfo = (strength) => {
    switch (strength) {
      case 0:
      case 1:
        return { label: "Very Weak", color: "error", value: 20 };
      case 2:
        return { label: "Weak", color: "error", value: 40 };
      case 3:
        return { label: "Fair", color: "warning", value: 60 };
      case 4:
        return { label: "Strong", color: "success", value: 80 };
      case 5:
        return { label: "Very Strong", color: "success", value: 100 };
      default:
        return { label: "Very Weak", color: "error", value: 20 };
    }
  };

  // Safe date formatting with relative time
  const formatLastLogin = (dateString) => {
    if (!dateString) return "Never";
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffInHours = Math.floor((now - date) / (1000 * 60 * 60));

      if (diffInHours < 1) return "Just now";
      if (diffInHours < 24) return `${diffInHours} hours ago`;
      if (diffInHours < 168) return `${Math.floor(diffInHours / 24)} days ago`;

      return date.toLocaleDateString("en-IN", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (error) {
      return "Invalid date";
    }
  };

  // Safe verification status
  const getVerificationStatus = () => {
    const isVerified =
      profileData?.isVerified ||
      profileData?.is_verified ||
      profileData?.email_verified;
    return {
      isVerified,
      label: isVerified ? "Verified" : "Pending Verification",
      description: isVerified
        ? "Your email address has been verified"
        : "Please verify your email address for better security",
    };
  };

  const passwordStrength = getPasswordStrength(passwordForm.new_password);
  const strengthInfo = getStrengthInfo(passwordStrength);
  const passwordsMatch =
    passwordForm.new_password === passwordForm.confirm_password;
  const verificationStatus = getVerificationStatus();

  // Enhanced security items with better data handling
  const securityItems = [
    {
      title: "Last Login",
      description: formatLastLogin(profileData?.last_login),
      icon: LoginIcon,
      status: "info",
      detail: profileData?.last_login_ip
        ? `from ${profileData.last_login_ip}`
        : null,
    },
    {
      title: "Failed Login Attempts",
      description: `${
        profileData?.failed_login_attempts || 0
      } recent failed attempts`,
      icon: AlertIcon,
      status:
        (profileData?.failed_login_attempts || 0) === 0 ? "success" : "warning",
      badge:
        (profileData?.failed_login_attempts || 0) === 0 ? "Secure" : "Monitor",
      detail:
        (profileData?.failed_login_attempts || 0) > 0
          ? "Consider changing your password"
          : null,
    },
    {
      title: "Email Verification",
      description: verificationStatus.description,
      icon: VerifiedIcon,
      status: verificationStatus.isVerified ? "success" : "warning",
      badge: verificationStatus.label,
      action: !verificationStatus.isVerified ? "Verify Now" : null,
    },
    {
      title: "Account Created",
      description: formatLastLogin(profileData?.created_at),
      icon: HistoryIcon,
      status: "info",
    },
  ];

  // Handle Two-Factor Authentication toggle
  const handleTwoFactorToggle = async () => {
    try {
      setUpdating(true);
      const newStatus = !profileData?.twoFactorEnabled;

      if (newStatus) {
        // Show setup dialog for enabling 2FA
        setTwoFactorDialog(true);
      } else {
        // Directly disable 2FA
        await profileService.toggleTwoFactor(false);
        toast.success("Two-factor authentication disabled");
        if (onUpdate) await onUpdate();
      }
    } catch (error) {
      console.error("2FA toggle error:", error);
      toast.error("Failed to update two-factor authentication");
    } finally {
      setUpdating(false);
    }
  };

  // Loading skeleton
  if (loading) {
    return (
      <Box sx={{ py: { xs: 2, sm: 4 } }}>
        <Skeleton
          variant="rectangular"
          height={120}
          sx={{ borderRadius: 2, mb: 3 }}
        />
        <Skeleton
          variant="rectangular"
          height={400}
          sx={{ borderRadius: 2, mb: 3 }}
        />
        <Skeleton
          variant="rectangular"
          height={300}
          sx={{ borderRadius: 2, mb: 3 }}
        />
        <Skeleton variant="rectangular" height={200} sx={{ borderRadius: 2 }} />
      </Box>
    );
  }

  return (
    <Box sx={{ py: { xs: 2, sm: 4 } }}>
      {/* Header */}
      <Fade in={true} timeout={300}>
        <Card
          sx={{
            mb: 4,
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            background: `linear-gradient(135deg, 
              ${alpha(theme.palette.background.paper, 0.9)} 0%, 
              ${alpha(theme.palette.error.main, 0.02)} 100%
            )`,
            backdropFilter: "blur(20px)",
            borderRadius: 3,
          }}
          elevation={0}
        >
          <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
            <Stack direction="row" alignItems="center" spacing={2}>
              <Avatar
                sx={{
                  bgcolor: alpha(theme.palette.error.main, 0.1),
                  color: "error.main",
                  width: { xs: 40, sm: 48 },
                  height: { xs: 40, sm: 48 },
                }}
              >
                <SecurityIcon />
              </Avatar>
              <Box>
                <Typography
                  variant={isMobile ? "h5" : "h4"}
                  component="h2"
                  fontWeight={700}
                  sx={{
                    background: `linear-gradient(135deg, ${theme.palette.error.main} 0%, ${theme.palette.warning.main} 100%)`,
                    backgroundClip: "text",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  Security Settings
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Manage your account security and authentication preferences
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Fade>

      {/* Error Alert */}
      {(error || localError) && (
        <Alert
          severity="error"
          sx={{
            mb: 3,
            borderRadius: 2,
            "& .MuiAlert-icon": {
              alignItems: "center",
            },
          }}
        >
          {error || localError}
        </Alert>
      )}

      {/* Password Change Section */}
      <Fade in={true} timeout={500}>
        <Card
          sx={{
            mb: 4,
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            background: alpha(theme.palette.background.paper, 0.8),
            backdropFilter: "blur(20px)",
            borderRadius: 3,
          }}
          elevation={0}
        >
          <Box
            sx={{
              p: { xs: 3, sm: 4 },
              borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
              display: "flex",
              alignItems: "center",
              gap: 2,
            }}
          >
            <LockIcon sx={{ color: "primary.main" }} />
            <Typography variant="h6" fontWeight={600}>
              Change Password
            </Typography>
            {updating && <CircularProgress size={20} />}
          </Box>

          <Box
            component="form"
            onSubmit={handlePasswordSubmit}
            sx={{ p: { xs: 3, sm: 4 } }}
          >
            <Grid container spacing={3}>
              {/* Current Password */}
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type={showPasswords.current ? "text" : "password"}
                  name="current_password"
                  label="Current Password"
                  value={passwordForm.current_password}
                  onChange={handlePasswordChange}
                  required
                  disabled={updating}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => togglePasswordVisibility("current")}
                          edge="end"
                          disabled={updating}
                        >
                          {showPasswords.current ? (
                            <VisibilityOffIcon />
                          ) : (
                            <VisibilityIcon />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiInputBase-root": {
                      borderRadius: 2,
                    },
                  }}
                />
              </Grid>

              {/* New Password */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type={showPasswords.new ? "text" : "password"}
                  name="new_password"
                  label="New Password"
                  value={passwordForm.new_password}
                  onChange={handlePasswordChange}
                  required
                  disabled={updating}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <KeyIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => togglePasswordVisibility("new")}
                          edge="end"
                          disabled={updating}
                        >
                          {showPasswords.new ? (
                            <VisibilityOffIcon />
                          ) : (
                            <VisibilityIcon />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiInputBase-root": {
                      borderRadius: 2,
                    },
                  }}
                />

                {/* Password Strength Indicator */}
                {passwordForm.new_password && (
                  <Box sx={{ mt: 2 }}>
                    <Stack
                      direction="row"
                      alignItems="center"
                      spacing={2}
                      mb={1}
                    >
                      <LinearProgress
                        variant="determinate"
                        value={strengthInfo.value}
                        color={strengthInfo.color}
                        sx={{ flex: 1, height: 6, borderRadius: 3 }}
                      />
                      <Chip
                        label={strengthInfo.label}
                        color={strengthInfo.color}
                        size="small"
                        sx={{ fontSize: "0.7rem", height: 22, fontWeight: 600 }}
                      />
                    </Stack>

                    {/* Password Requirements */}
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        bgcolor: alpha(theme.palette.background.paper, 0.5),
                      }}
                    >
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mb: 1, display: "block" }}
                      >
                        Password Requirements:
                      </Typography>
                      <Grid container spacing={1}>
                        {passwordRequirements.map((req, index) => {
                          const isValid = req.test(passwordForm.new_password);
                          return (
                            <Grid item xs={12} sm={6} key={index}>
                              <Stack
                                direction="row"
                                alignItems="center"
                                spacing={1}
                              >
                                {isValid ? (
                                  <CheckIcon
                                    sx={{ color: "success.main", fontSize: 16 }}
                                  />
                                ) : (
                                  <CloseIcon
                                    sx={{ color: "error.main", fontSize: 16 }}
                                  />
                                )}
                                <Typography
                                  variant="caption"
                                  color={
                                    isValid ? "success.main" : "text.secondary"
                                  }
                                  sx={{ fontSize: "0.75rem" }}
                                >
                                  {req.label}
                                </Typography>
                              </Stack>
                            </Grid>
                          );
                        })}
                      </Grid>
                    </Paper>
                  </Box>
                )}
              </Grid>

              {/* Confirm Password */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type={showPasswords.confirm ? "text" : "password"}
                  name="confirm_password"
                  label="Confirm New Password"
                  value={passwordForm.confirm_password}
                  onChange={handlePasswordChange}
                  required
                  disabled={updating}
                  error={passwordForm.confirm_password && !passwordsMatch}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <KeyIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => togglePasswordVisibility("confirm")}
                          edge="end"
                          disabled={updating}
                        >
                          {showPasswords.confirm ? (
                            <VisibilityOffIcon />
                          ) : (
                            <VisibilityIcon />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiInputBase-root": {
                      borderRadius