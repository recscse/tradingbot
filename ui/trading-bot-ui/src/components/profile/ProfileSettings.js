import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  InputAdornment,
  Chip,
  Avatar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  useTheme,
  alpha,
  Fade,
  useMediaQuery,
  CircularProgress,
  Stack,
  Paper,
  Skeleton,
} from "@mui/material";
import {
  Person as PersonIcon,
  Email as EmailIcon,
  Phone as PhoneIcon,
  Public as GlobeIcon,
  Save as SaveIcon,
  Edit as EditIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Warning as AlertIcon,
  CalendarToday as CalendarIcon,
  Settings as SettingsIcon,
  DeleteForever as DeleteIcon,
  AccountCircle as AccountIcon,
  Star as StarIcon,
  Verified as VerifiedIcon,
  Security as SecurityIcon,
  AccountBalance as BalanceIcon,
  Cancel as CancelIcon,
} from "@mui/icons-material";
import { toast } from "react-hot-toast";

const ProfileSettings = ({
  profileData = {},
  onUpdate = () => {},
  onDeleteAccount = () => {},
  loading = false,
  error = null,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md"));

  const [isEditing, setIsEditing] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [localError, setLocalError] = useState("");
  const [formData, setFormData] = useState({
    full_name: "",
    phone_number: "",
    country_code: "+91",
  });

  // Initialize form data when profileData changes
  useEffect(() => {
    setFormData({
      full_name: profileData?.full_name || "",
      phone_number: profileData?.phone_number || "",
      country_code: profileData?.country_code || "+91",
    });
  }, [profileData]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear local error when user starts typing
    if (localError) setLocalError("");
  };

  const validateForm = () => {
    if (!formData.full_name?.trim()) {
      setLocalError("Full name is required");
      return false;
    }
    if (formData.full_name.trim().length < 2) {
      setLocalError("Full name must be at least 2 characters long");
      return false;
    }
    if (
      formData.phone_number &&
      !/^\d{10,15}$/.test(formData.phone_number.replace(/\s+/g, ""))
    ) {
      setLocalError("Please enter a valid phone number");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setUpdating(true);
    setLocalError("");

    try {
      await onUpdate(formData);
      setIsEditing(false);
      toast.success("Profile updated successfully");
    } catch (error) {
      console.error("Profile update error:", error);
      const errorMessage =
        error?.response?.data?.message ||
        error?.message ||
        "Failed to update profile";
      setLocalError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setUpdating(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      full_name: profileData?.full_name || "",
      phone_number: profileData?.phone_number || "",
      country_code: profileData?.country_code || "+91",
    });
    setIsEditing(false);
    setLocalError("");
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== "DELETE") {
      toast.error("Please type 'DELETE' to confirm");
      return;
    }

    try {
      setUpdating(true);
      await onDeleteAccount();
      toast.success("Account deletion request submitted");
      setDeleteDialogOpen(false);
    } catch (error) {
      console.error("Account deletion error:", error);
      const errorMessage =
        error?.response?.data?.message ||
        error?.message ||
        "Failed to delete account";
      toast.error(errorMessage);
    } finally {
      setUpdating(false);
    }
  };

  // Enhanced country options with proper validation
  const countryOptions = [
    { code: "+91", label: "India", flag: "🇮🇳", country: "IN" },
    { code: "+1", label: "United States", flag: "🇺🇸", country: "US" },
    { code: "+44", label: "United Kingdom", flag: "🇬🇧", country: "GB" },
    { code: "+86", label: "China", flag: "🇨🇳", country: "CN" },
    { code: "+81", label: "Japan", flag: "🇯🇵", country: "JP" },
    { code: "+49", label: "Germany", flag: "🇩🇪", country: "DE" },
    { code: "+33", label: "France", flag: "🇫🇷", country: "FR" },
    { code: "+61", label: "Australia", flag: "🇦🇺", country: "AU" },
    { code: "+82", label: "South Korea", flag: "🇰🇷", country: "KR" },
    { code: "+65", label: "Singapore", flag: "🇸🇬", country: "SG" },
  ];

  // Safe date formatting
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    try {
      return new Date(dateString).toLocaleDateString("en-IN", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch (error) {
      return "Invalid date";
    }
  };

  // Safe account type detection
  const getAccountType = () => {
    if (profileData?.isPremium || profileData?.is_premium) {
      return { label: "Premium Account", icon: StarIcon, color: "warning" };
    }
    if (profileData?.role === "admin") {
      return { label: "Admin Account", icon: SecurityIcon, color: "error" };
    }
    return { label: "Free Account", icon: AccountIcon, color: "primary" };
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
      color: isVerified ? "success" : "warning",
      icon: isVerified ? VerifiedIcon : CancelIcon,
    };
  };

  const accountType = getAccountType();
  const verificationStatus = getVerificationStatus();

  const accountInfo = [
    {
      label: "Member Since",
      value: formatDate(profileData?.created_at),
      icon: CalendarIcon,
      color: "info",
    },
    {
      label: "Account Type",
      value: accountType.label,
      icon: accountType.icon,
      color: accountType.color,
    },
    {
      label: "User Role",
      value: profileData?.role || "Trader",
      icon: PersonIcon,
      color: "primary",
    },
    {
      label: "Connected Brokers",
      value: `${
        Array.isArray(profileData?.broker_accounts)
          ? profileData.broker_accounts.length
          : profileData?.broker_count || 0
      } brokers`,
      icon: BalanceIcon,
      color: "secondary",
    },
  ];

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
              ${alpha(theme.palette.primary.main, 0.02)} 100%
            )`,
            backdropFilter: "blur(20px)",
            borderRadius: 3,
          }}
          elevation={0}
        >
          <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "flex-start", sm: "center" }}
              spacing={3}
            >
              <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar
                  sx={{
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    color: "primary.main",
                    width: { xs: 40, sm: 48 },
                    height: { xs: 40, sm: 48 },
                  }}
                >
                  <SettingsIcon />
                </Avatar>
                <Box>
                  <Typography
                    variant={isMobile ? "h5" : "h4"}
                    component="h2"
                    fontWeight={700}
                    sx={{
                      background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                      backgroundClip: "text",
                      WebkitBackgroundClip: "text",
                      WebkitTextFillColor: "transparent",
                    }}
                  >
                    Profile Settings
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Manage your personal information and account preferences
                  </Typography>
                </Box>
              </Stack>

              {!isEditing && (
                <Button
                  variant="contained"
                  startIcon={<EditIcon />}
                  onClick={() => setIsEditing(true)}
                  sx={{
                    borderRadius: 3,
                    fontWeight: 700,
                    px: 4,
                    boxShadow: `0 8px 24px ${alpha(
                      theme.palette.primary.main,
                      0.3
                    )}`,
                    "&:hover": {
                      boxShadow: `0 12px 32px ${alpha(
                        theme.palette.primary.main,
                        0.4
                      )}`,
                      transform: "translateY(-2px)",
                    },
                    transition: "all 0.3s ease",
                  }}
                >
                  Edit Profile
                </Button>
              )}
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

      {/* Personal Information Form */}
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
            <PersonIcon sx={{ color: "primary.main" }} />
            <Typography variant="h6" fontWeight={600}>
              Personal Information
            </Typography>
            {updating && <CircularProgress size={20} />}
          </Box>

          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{ p: { xs: 3, sm: 4 } }}
          >
            <Grid container spacing={3}>
              {/* Full Name */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Full Name"
                  name="full_name"
                  value={
                    isEditing
                      ? formData.full_name
                      : profileData?.full_name || "Not provided"
                  }
                  onChange={handleInputChange}
                  disabled={!isEditing || updating}
                  required={isEditing}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <PersonIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    readOnly: !isEditing,
                  }}
                  error={isEditing && !formData.full_name?.trim()}
                  helperText={
                    isEditing && !formData.full_name?.trim()
                      ? "Full name is required"
                      : isEditing
                      ? "Enter your full legal name"
                      : null
                  }
                  sx={{
                    "& .MuiInputBase-root": {
                      borderRadius: 2,
                      bgcolor: !isEditing
                        ? alpha(theme.palette.action.selected, 0.1)
                        : "transparent",
                    },
                  }}
                />
              </Grid>

              {/* Email (Read-only) */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Email Address"
                  value={profileData?.email || ""}
                  disabled
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <Chip
                          label={verificationStatus.label}
                          color={verificationStatus.color}
                          size="small"
                          icon={<verificationStatus.icon />}
                          sx={{ fontSize: "0.7rem", height: 24 }}
                        />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiInputBase-root": {
                      borderRadius: 2,
                      bgcolor: alpha(theme.palette.action.selected, 0.1),
                    },
                  }}
                />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 1, display: "block" }}
                >
                  Email cannot be changed. Contact support if needed.
                </Typography>
              </Grid>

              {/* Phone Number */}
              <Grid item xs={12} md={6}>
                {isEditing ? (
                  <Stack direction="row" spacing={1}>
                    <FormControl sx={{ minWidth: 140 }}>
                      <InputLabel>Country</InputLabel>
                      <Select
                        name="country_code"
                        value={formData.country_code}
                        onChange={handleInputChange}
                        label="Country"
                        disabled={updating}
                        sx={{ borderRadius: 2 }}
                      >
                        {countryOptions.map((country) => (
                          <MenuItem key={country.code} value={country.code}>
                            <Stack
                              direction="row"
                              alignItems="center"
                              spacing={1}
                            >
                              <span style={{ fontSize: "1rem" }}>
                                {country.flag}
                              </span>
                              <span style={{ fontSize: "0.875rem" }}>
                                {country.code}
                              </span>
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                {country.label}
                              </Typography>
                            </Stack>
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <TextField
                      fullWidth
                      label="Phone Number"
                      name="phone_number"
                      value={formData.phone_number}
                      onChange={handleInputChange}
                      type="tel"
                      placeholder="Enter phone number"
                      disabled={updating}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <PhoneIcon sx={{ color: "text.secondary" }} />
                          </InputAdornment>
                        ),
                      }}
                      sx={{
                        "& .MuiInputBase-root": {
                          borderRadius: 2,
                        },
                      }}
                    />
                  </Stack>
                ) : (
                  <TextField
                    fullWidth
                    label="Phone Number"
                    value={
                      profileData?.phone_number
                        ? `${profileData?.country_code || "+91"} ${
                            profileData.phone_number
                          }`
                        : "Not provided"
                    }
                    disabled
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <PhoneIcon sx={{ color: "text.secondary" }} />
                        </InputAdornment>
                      ),
                    }}
                    sx={{
                      "& .MuiInputBase-root": {
                        borderRadius: 2,
                        bgcolor: alpha(theme.palette.action.selected, 0.1),
                      },
                    }}
                  />
                )}
              </Grid>

              {/* Country/Region */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Country/Region"
                  value={profileData?.country || "India"}
                  disabled
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <GlobeIcon sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiInputBase-root": {
                      borderRadius: 2,
                      bgcolor: alpha(theme.palette.action.selected, 0.1),
                    },
                  }}
                />
              </Grid>

              {/* Action Buttons */}
              {isEditing && (
                <Grid item xs={12}>
                  <Stack direction="row" spacing={2} justifyContent="flex-end">
                    <Button
                      variant="outlined"
                      startIcon={<CloseIcon />}
                      onClick={handleCancel}
                      disabled={updating}
                      sx={{ borderRadius: 2, px: 3 }}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="contained"
                      disabled={updating || !formData.full_name?.trim()}
                      startIcon={
                        updating ? <CircularProgress size={20} /> : <SaveIcon />
                      }
                      sx={{
                        borderRadius: 2,
                        fontWeight: 600,
                        px: 4,
                      }}
                    >
                      {updating ? "Saving..." : "Save Changes"}
                    </Button>
                  </Stack>
                </Grid>
              )}
            </Grid>
          </Box>
        </Card>
      </Fade>

      {/* Account Information */}
      <Fade in={true} timeout={700}>
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
            <AccountIcon sx={{ color: "info.main" }} />
            <Typography variant="h6" fontWeight={600}>
              Account Information
            </Typography>
          </Box>

          <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
            <Grid container spacing={3}>
              {/* Account Status */}
              <Grid item xs={12}>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Account Status
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip
                    icon={
                      profileData?.is_active ? <CheckIcon /> : <CancelIcon />
                    }
                    label={profileData?.is_active ? "Active" : "Inactive"}
                    color={profileData?.is_active ? "success" : "error"}
                    sx={{ fontWeight: 500 }}
                  />
                  {verificationStatus.isVerified && (
                    <Chip
                      icon={<VerifiedIcon />}
                      label="Verified"
                      color="primary"
                      sx={{ fontWeight: 500 }}
                    />
                  )}
                  {(profileData?.isPremium || profileData?.is_premium) && (
                    <Chip
                      icon={<StarIcon />}
                      label="Premium"
                      color="warning"
                      sx={{ fontWeight: 500 }}
                    />
                  )}
                </Stack>
              </Grid>

              {/* Account Info Items */}
              {accountInfo.map((item, index) => (
                <Grid item xs={12} sm={6} lg={3} key={index}>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      height: "100%",
                      display: "flex",
                      alignItems: "center",
                      gap: 2,
                      bgcolor: alpha(theme.palette[item.color].main, 0.04),
                      border: `1px solid ${alpha(
                        theme.palette[item.color].main,
                        0.1
                      )}`,
                      borderRadius: 2,
                    }}
                  >
                    <Avatar
                      sx={{
                        bgcolor: alpha(theme.palette[item.color].main, 0.1),
                        color: `${item.color}.main`,
                        width: 40,
                        height: 40,
                      }}
                    >
                      <item.icon sx={{ fontSize: 20 }} />
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: "block" }}
                      >
                        {item.label}
                      </Typography>
                      <Typography
                        variant="body2"
                        fontWeight={500}
                        sx={{
                          wordBreak: "break-word",
                          lineHeight: 1.2,
                        }}
                      >
                        {item.value}
                      </Typography>
                    </Box>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      </Fade>

      {/* Danger Zone */}
      <Fade in={true} timeout={900}>
        <Card
          sx={{
            border: `2px solid ${alpha(theme.palette.error.main, 0.2)}`,
            background: alpha(theme.palette.error.main, 0.02),
            backdropFilter: "blur(20px)",
            borderRadius: 3,
          }}
          elevation={0}
        >
          <Box
            sx={{
              p: { xs: 3, sm: 4 },
              borderBottom: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
              display: "flex",
              alignItems: "center",
              gap: 2,
            }}
          >
            <AlertIcon sx={{ color: "error.main" }} />
            <Typography variant="h6" fontWeight={600} color="error.main">
              Danger Zone
            </Typography>
          </Box>

          <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              alignItems="flex-start"
              spacing={3}
            >
              <Avatar
                sx={{
                  bgcolor: alpha(theme.palette.error.main, 0.1),
                  color: "error.main",
                  width: 48,
                  height: 48,
                }}
              >
                <DeleteIcon />
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Delete Account
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 3 }}
                >
                  Once you delete your account, there is no going back. Please
                  be certain. All your trading data, broker connections, and
                  account information will be permanently lost.
                </Typography>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<DeleteIcon />}
                  onClick={() => setDeleteDialogOpen(true)}
                  disabled={updating}
                  sx={{
                    borderRadius: 2,
                    "&:hover": {
                      bgcolor: alpha(theme.palette.error.main, 0.04),
                    },
                  }}
                >
                  Delete Account
                </Button>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Fade>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !updating && setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            background: alpha(theme.palette.background.paper, 0.95),
            backdropFilter: "blur(20px)",
          },
        }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            color: "error.main",
          }}
        >
          <AlertIcon />
          Confirm Account Deletion
        </DialogTitle>
        <DialogContent>
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            <Typography variant="body2" fontWeight={600}>
              This action cannot be undone!
            </Typography>
          </Alert>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Are you absolutely sure you want to delete your account? This will:
          </Typography>

          <Box component="ul" sx={{ mt: 2, pl: 2, mb: 3 }}>
            <Typography component="li" variant="body2" color="text.secondary">
              Permanently delete all your personal information
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Remove all broker connections and trading data
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Cancel any active subscriptions
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Make your account unrecoverable
            </Typography>
          </Box>

          <TextField
            fullWidth
            label="Type 'DELETE' to confirm"
            value={deleteConfirmText}
            onChange={(e) => setDeleteConfirmText(e.target.value)}
            disabled={updating}
            error={deleteConfirmText !== "" && deleteConfirmText !== "DELETE"}
            helperText="Type DELETE in capital letters to confirm"
            sx={{
              "& .MuiInputBase-root": {
                borderRadius: 2,
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ p: 3, gap: 1 }}>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            disabled={updating}
            sx={{ borderRadius: 2 }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={
              updating ? <CircularProgress size={16} /> : <DeleteIcon />
            }
            onClick={handleDeleteAccount}
            disabled={updating || deleteConfirmText !== "DELETE"}
            sx={{ borderRadius: 2, fontWeight: 600 }}
          >
            {updating ? "Deleting..." : "Yes, Delete My Account"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ProfileSettings;
