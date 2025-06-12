import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  IconButton,
  Avatar,
  Divider,
  CircularProgress,
  Alert,
  InputAdornment,
  Grid,
  Card,
  CardContent,
  Chip,
  Stack,
  Paper,
  useTheme,
  alpha,
  LinearProgress,
  Tooltip,
} from "@mui/material";
import {
  Close as CloseIcon,
  Person as PersonIcon,
  Email as EmailIcon,
  Save as SaveIcon,
  Phone as PhoneIcon,
  Flag as FlagIcon,
  Verified as VerifiedIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  CalendarToday as CalendarIcon,
  Business as BusinessIcon,
  Edit as EditIcon,
  AccountCircle as AccountCircleIcon,
} from "@mui/icons-material";
import { toast } from "react-toastify";
import { profileService } from "../../services/profileService";

const ProfileModal = ({ open, onClose }) => {
  const theme = useTheme();
  const [user, setUser] = useState({});
  const [editForm, setEditForm] = useState({
    full_name: "",
    phone_number: "",
    country_code: "",
  });
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      fetchProfile();
    }
  }, [open]);

  const fetchProfile = async () => {
    try {
      setFetching(true);
      setError("");

      const response = await profileService.getUserProfile();
      if (response.success) {
        setUser(response.data);
        setEditForm({
          full_name: response.data.full_name || "",
          phone_number: response.data.phone_number || "",
          country_code: response.data.country_code || "+91",
        });
      } else {
        setError(response.error || "Failed to load profile");
      }
    } catch (error) {
      console.error("Error fetching profile:", error);
      setError("Failed to load profile data");
    } finally {
      setFetching(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();

    if (!editForm.full_name.trim()) {
      setError("Name cannot be empty");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await profileService.updateUserProfile(editForm);
      if (response.success) {
        setUser((prev) => ({ ...prev, ...editForm }));
        toast.success("Profile updated successfully!");
        onClose();
      } else {
        setError(response.error || "Failed to update profile");
      }
    } catch (error) {
      console.error("Error updating profile:", error);
      setError("Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setError("");
      onClose();
    }
  };

  // Safe initials generation
  const getInitials = (name) => {
    if (!name || typeof name !== "string") return "U";
    return name
      .trim()
      .split(" ")
      .filter((word) => word.length > 0)
      .map((word) => word[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

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

  // Get verification status with proper styling
  const getVerificationStatus = () => {
    if (user.isVerified || user.is_verified) {
      return {
        label: "Verified",
        color: "success",
        icon: <VerifiedIcon fontSize="small" />,
      };
    }
    return {
      label: "Pending Verification",
      color: "warning",
      icon: <CancelIcon fontSize="small" />,
    };
  };

  // Get account status with proper styling
  const getAccountStatus = () => {
    if (user.is_active !== undefined) {
      return {
        label: user.is_active ? "Active" : "Inactive",
        color: user.is_active ? "success" : "error",
        icon: user.is_active ? (
          <CheckCircleIcon fontSize="small" />
        ) : (
          <CancelIcon fontSize="small" />
        ),
      };
    }
    return {
      label: "Unknown",
      color: "default",
      icon: <CancelIcon fontSize="small" />,
    };
  };

  // Safe broker count
  const getBrokerCount = () => {
    if (Array.isArray(user.broker_accounts)) {
      return user.broker_accounts.length;
    }
    if (typeof user.broker_count === "number") {
      return user.broker_count;
    }
    return 0;
  };

  const verificationStatus = getVerificationStatus();
  const accountStatus = getAccountStatus();

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 4,
          minHeight: 600,
          background: alpha(theme.palette.background.paper, 0.95),
          backdropFilter: "blur(20px)",
        },
      }}
    >
      <DialogTitle sx={{ pb: 2 }}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
        >
          <Stack direction="row" alignItems="center" spacing={2}>
            <Avatar
              sx={{
                bgcolor: theme.palette.primary.main,
                width: 48,
                height: 48,
                fontSize: "1.2rem",
                fontWeight: 700,
                border: `2px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              }}
            >
              {user.full_name ? getInitials(user.full_name) : <PersonIcon />}
            </Avatar>
            <Box>
              <Typography variant="h5" component="div" fontWeight={700}>
                Profile Settings
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Manage your account information and preferences
              </Typography>
            </Box>
          </Stack>
          <Tooltip title="Close">
            <IconButton
              onClick={handleClose}
              disabled={loading}
              sx={{
                "&:hover": {
                  bgcolor: alpha(theme.palette.error.main, 0.1),
                  color: "error.main",
                },
              }}
            >
              <CloseIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </DialogTitle>

      <Divider />

      <DialogContent sx={{ p: 3 }}>
        {error && (
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
            {error}
          </Alert>
        )}

        {fetching ? (
          <Paper
            elevation={0}
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              py: 8,
              borderRadius: 3,
              bgcolor: alpha(theme.palette.primary.main, 0.02),
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            }}
          >
            <CircularProgress size={48} thickness={4} />
            <Typography variant="body1" color="text.secondary" sx={{ mt: 3 }}>
              Loading your profile...
            </Typography>
            <LinearProgress
              sx={{
                width: 200,
                mt: 2,
                borderRadius: 1,
                height: 6,
              }}
            />
          </Paper>
        ) : (
          <Box component="form" onSubmit={handleUpdate}>
            <Grid container spacing={3}>
              {/* Profile Info Card */}
              <Grid item xs={12}>
                <Card
                  variant="outlined"
                  sx={{
                    borderRadius: 3,
                    border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                    background: `linear-gradient(135deg, 
                      ${alpha(theme.palette.background.paper, 0.9)} 0%, 
                      ${alpha(theme.palette.primary.main, 0.01)} 100%
                    )`,
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Stack
                      direction="row"
                      alignItems="center"
                      spacing={2}
                      mb={3}
                    >
                      <Avatar
                        sx={{
                          bgcolor: alpha(theme.palette.primary.main, 0.1),
                          color: "primary.main",
                          width: 40,
                          height: 40,
                        }}
                      >
                        <EditIcon />
                      </Avatar>
                      <Typography variant="h6" fontWeight={700}>
                        Personal Information
                      </Typography>
                    </Stack>

                    <Grid container spacing={3}>
                      <Grid item xs={12}>
                        <TextField
                          label="Email Address"
                          value={user.email || ""}
                          fullWidth
                          disabled
                          variant="outlined"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <EmailIcon color="disabled" />
                              </InputAdornment>
                            ),
                          }}
                          helperText="Email address cannot be changed"
                          sx={{
                            "& .MuiInputBase-root": {
                              borderRadius: 2,
                            },
                          }}
                        />
                      </Grid>

                      <Grid item xs={12}>
                        <TextField
                          label="Full Name"
                          value={editForm.full_name}
                          onChange={(e) =>
                            setEditForm((prev) => ({
                              ...prev,
                              full_name: e.target.value,
                            }))
                          }
                          fullWidth
                          required
                          disabled={loading}
                          variant="outlined"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <PersonIcon color="primary" />
                              </InputAdornment>
                            ),
                          }}
                          error={
                            !editForm.full_name.trim() &&
                            editForm.full_name !== ""
                          }
                          helperText={
                            !editForm.full_name.trim() &&
                            editForm.full_name !== ""
                              ? "Name is required"
                              : "Enter your full name as it appears on official documents"
                          }
                          sx={{
                            "& .MuiInputBase-root": {
                              borderRadius: 2,
                            },
                          }}
                        />
                      </Grid>

                      <Grid item xs={4}>
                        <TextField
                          label="Country Code"
                          value={editForm.country_code}
                          onChange={(e) =>
                            setEditForm((prev) => ({
                              ...prev,
                              country_code: e.target.value,
                            }))
                          }
                          fullWidth
                          disabled={loading}
                          variant="outlined"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <FlagIcon color="primary" />
                              </InputAdornment>
                            ),
                          }}
                          placeholder="+91"
                          sx={{
                            "& .MuiInputBase-root": {
                              borderRadius: 2,
                            },
                          }}
                        />
                      </Grid>

                      <Grid item xs={8}>
                        <TextField
                          label="Phone Number"
                          value={editForm.phone_number}
                          onChange={(e) =>
                            setEditForm((prev) => ({
                              ...prev,
                              phone_number: e.target.value,
                            }))
                          }
                          fullWidth
                          disabled={loading}
                          variant="outlined"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <PhoneIcon color="primary" />
                              </InputAdornment>
                            ),
                          }}
                          placeholder="9876543210"
                          helperText="Enter your mobile number without country code"
                          sx={{
                            "& .MuiInputBase-root": {
                              borderRadius: 2,
                            },
                          }}
                        />
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>

              {/* Account Status Card */}
              <Grid item xs={12}>
                <Card
                  variant="outlined"
                  sx={{
                    borderRadius: 3,
                    border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                    background: `linear-gradient(135deg, 
                      ${alpha(theme.palette.background.paper, 0.9)} 0%, 
                      ${alpha(theme.palette.secondary.main, 0.01)} 100%
                    )`,
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Stack
                      direction="row"
                      alignItems="center"
                      spacing={2}
                      mb={3}
                    >
                      <Avatar
                        sx={{
                          bgcolor: alpha(theme.palette.secondary.main, 0.1),
                          color: "secondary.main",
                          width: 40,
                          height: 40,
                        }}
                      >
                        <AccountCircleIcon />
                      </Avatar>
                      <Typography variant="h6" fontWeight={700}>
                        Account Overview
                      </Typography>
                    </Stack>

                    <Grid container spacing={3}>
                      <Grid item xs={12} sm={6}>
                        <Paper
                          elevation={0}
                          sx={{
                            p: 2,
                            borderRadius: 2,
                            bgcolor: alpha(
                              verificationStatus.color === "success"
                                ? theme.palette.success.main
                                : theme.palette.warning.main,
                              0.05
                            ),
                            border: `1px solid ${alpha(
                              verificationStatus.color === "success"
                                ? theme.palette.success.main
                                : theme.palette.warning.main,
                              0.1
                            )}`,
                          }}
                        >
                          <Stack
                            direction="row"
                            alignItems="center"
                            spacing={1}
                            mb={1}
                          >
                            {verificationStatus.icon}
                            <Typography variant="body2" color="text.secondary">
                              Verification Status
                            </Typography>
                          </Stack>
                          <Chip
                            label={verificationStatus.label}
                            color={verificationStatus.color}
                            size="small"
                            sx={{ fontWeight: 600 }}
                          />
                        </Paper>
                      </Grid>

                      <Grid item xs={12} sm={6}>
                        <Paper
                          elevation={0}
                          sx={{
                            p: 2,
                            borderRadius: 2,
                            bgcolor: alpha(
                              accountStatus.color === "success"
                                ? theme.palette.success.main
                                : theme.palette.error.main,
                              0.05
                            ),
                            border: `1px solid ${alpha(
                              accountStatus.color === "success"
                                ? theme.palette.success.main
                                : theme.palette.error.main,
                              0.1
                            )}`,
                          }}
                        >
                          <Stack
                            direction="row"
                            alignItems="center"
                            spacing={1}
                            mb={1}
                          >
                            {accountStatus.icon}
                            <Typography variant="body2" color="text.secondary">
                              Account Status
                            </Typography>
                          </Stack>
                          <Chip
                            label={accountStatus.label}
                            color={accountStatus.color}
                            size="small"
                            sx={{ fontWeight: 600 }}
                          />
                        </Paper>
                      </Grid>

                      <Grid item xs={12} sm={6}>
                        <Paper
                          elevation={0}
                          sx={{
                            p: 2,
                            borderRadius: 2,
                            bgcolor: alpha(theme.palette.info.main, 0.05),
                            border: `1px solid ${alpha(
                              theme.palette.info.main,
                              0.1
                            )}`,
                          }}
                        >
                          <Stack
                            direction="row"
                            alignItems="center"
                            spacing={1}
                            mb={1}
                          >
                            <CalendarIcon fontSize="small" color="info" />
                            <Typography variant="body2" color="text.secondary">
                              Member Since
                            </Typography>
                          </Stack>
                          <Typography variant="body1" fontWeight={600}>
                            {formatDate(user.created_at)}
                          </Typography>
                        </Paper>
                      </Grid>

                      <Grid item xs={12} sm={6}>
                        <Paper
                          elevation={0}
                          sx={{
                            p: 2,
                            borderRadius: 2,
                            bgcolor: alpha(theme.palette.primary.main, 0.05),
                            border: `1px solid ${alpha(
                              theme.palette.primary.main,
                              0.1
                            )}`,
                          }}
                        >
                          <Stack
                            direction="row"
                            alignItems="center"
                            spacing={1}
                            mb={1}
                          >
                            <BusinessIcon fontSize="small" color="primary" />
                            <Typography variant="body2" color="text.secondary">
                              Connected Brokers
                            </Typography>
                          </Stack>
                          <Typography
                            variant="h6"
                            fontWeight={700}
                            color="primary.main"
                          >
                            {getBrokerCount()}
                          </Typography>
                        </Paper>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        )}
      </DialogContent>

      <Divider />

      <DialogActions sx={{ p: 3, gap: 2 }}>
        <Button
          onClick={handleClose}
          disabled={loading}
          variant="outlined"
          sx={{
            borderRadius: 2,
            px: 3,
            fontWeight: 600,
          }}
        >
          Cancel
        </Button>
        <Button
          onClick={handleUpdate}
          disabled={loading || fetching || !editForm.full_name.trim()}
          variant="contained"
          startIcon={loading ? <CircularProgress size={16} /> : <SaveIcon />}
          sx={{
            borderRadius: 2,
            px: 4,
            fontWeight: 700,
            boxShadow: `0 8px 24px ${alpha(theme.palette.primary.main, 0.3)}`,
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
          {loading ? "Updating..." : "Save Changes"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProfileModal;
