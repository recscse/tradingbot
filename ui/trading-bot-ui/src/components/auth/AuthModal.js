import React, { useState, useEffect } from "react";
import {
  Drawer,
  TextField,
  Button,
  Typography,
  Box,
  IconButton,
  Link,
  Alert,
  Select,
  MenuItem,
  InputLabel,
  FormControl,
  CircularProgress,
  useTheme,
  useMediaQuery,
  InputAdornment,
  Tabs,
  Tab,
  Collapse,
  Divider,
  Avatar,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import EmailIcon from "@mui/icons-material/Email";
import LockIcon from "@mui/icons-material/Lock";
import PersonIcon from "@mui/icons-material/Person";
import PhoneIcon from "@mui/icons-material/Phone";
import GoogleIcon from "@mui/icons-material/Google";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import {
  login,
  signup,
  handleGoogleAuth,
  forgotPassword,
  resetPassword,
  verifyResetToken,
  verifyEmailOTP,
  sendEmailOTP,
} from "../../services/authService";

const countryCodes = [
  { code: "+1", country: "United States" },
  { code: "+91", country: "India" },
  { code: "+44", country: "United Kingdom" },
  { code: "+61", country: "Australia" },
  { code: "+49", country: "Germany" },
  { code: "+33", country: "France" },
];

const AuthModal = ({
  open,
  handleClose,
  onLoginSuccess,
  isLogin,
  setIsLogin,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const isMedium = useMediaQuery(theme.breakpoints.down("md"));

  const [credentials, setCredentials] = useState({
    fullname: "",
    identifier: "",
    phone: "",
    countryCode: "+1",
    password: "",
    confirmPassword: "",
    newPassword: "",
  });
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [activeTab, setActiveTab] = useState(isLogin ? 0 : 1);
  const [formValid, setFormValid] = useState(false);

  // Forgot password flow states
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotPasswordStep, setForgotPasswordStep] = useState("email");
  const [resetToken, setResetToken] = useState("");

  // Signup flow states
  const [signupStep, setSignupStep] = useState("form"); // form, email-verification
  // Removed unused emailVerificationSent variable

  // Avatar state
  const [userInitials, setUserInitials] = useState("TB");
  const [avatarColor, setAvatarColor] = useState("#4186ff");

  // Generate initials from name
  const getInitials = (name) => {
    if (!name || name.trim() === "") return "TB";
    const nameParts = name.trim().split(" ");
    if (nameParts.length === 1) return nameParts[0].charAt(0).toUpperCase();
    return (
      nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0)
    ).toUpperCase();
  };

  // Generate color from string
  const stringToColor = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    let color = "#";
    for (let i = 0; i < 3; i++) {
      const value = (hash >> (i * 8)) & 0xff;
      color += `00${value.toString(16)}`.substr(-2);
    }
    return color;
  };

  // Update initials and avatar color when name changes
  useEffect(() => {
    if (!isLogin && credentials.fullname) {
      const initials = getInitials(credentials.fullname);
      setUserInitials(initials);
      setAvatarColor(stringToColor(credentials.fullname));
    } else {
      setUserInitials("TB");
      setAvatarColor("#4186ff");
    }
  }, [isLogin, credentials.fullname]);

  // Form validation
  useEffect(() => {
    if (showForgotPassword) {
      if (forgotPasswordStep === "email") {
        setFormValid(credentials.identifier.includes("@"));
      } else if (forgotPasswordStep === "otp") {
        setFormValid(otp.length >= 4);
      } else if (forgotPasswordStep === "reset") {
        setFormValid(
          credentials.newPassword.length >= 6 &&
            credentials.newPassword === credentials.confirmPassword
        );
      }
    } else if (isLogin) {
      setFormValid(
        credentials.identifier.includes("@") && credentials.password.length >= 6
      );
    } else {
      if (signupStep === "form") {
        setFormValid(
          credentials.fullname.length >= 2 &&
            credentials.identifier.includes("@") &&
            credentials.password.length >= 6
        );
      } else if (signupStep === "email-verification") {
        setFormValid(otp.length >= 4);
      }
    }
  }, [
    credentials,
    isLogin,
    showForgotPassword,
    forgotPasswordStep,
    signupStep,
    otp,
  ]);

  // Update tab when isLogin changes
  useEffect(() => {
    setActiveTab(isLogin ? 0 : 1);
  }, [isLogin]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCredentials((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (error) setError("");
    if (successMessage) setSuccessMessage("");
  };

  // Handle tab changes
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
    setIsLogin(newValue === 0);
    resetForm();
  };

  // Reset form function
  const resetForm = () => {
    setError("");
    setSuccessMessage("");
    setShowForgotPassword(false);
    setForgotPasswordStep("email");
    setSignupStep("form");
    setOtp("");
    setResetToken("");
  };

  // Enhanced error handling function
  const handleError = (errorResponse) => {
    let errorMessage = "Something went wrong. Please try again.";

    try {
      if (typeof errorResponse === "string") {
        errorMessage = errorResponse;
      } else if (errorResponse && typeof errorResponse === "object") {
        if (errorResponse.errors && Array.isArray(errorResponse.errors)) {
          errorMessage = errorResponse.errors
            .map((err) => {
              if (typeof err === "string") return err;
              if (err.msg) return err.msg;
              if (err.message) return err.message;
              return "Validation error";
            })
            .join(", ");
        } else if (errorResponse.message) {
          errorMessage = errorResponse.message;
        } else if (errorResponse.detail) {
          if (Array.isArray(errorResponse.detail)) {
            errorMessage = errorResponse.detail
              .map((err) => {
                if (typeof err === "string") return err;
                if (err.msg) return err.msg;
                return "Validation error";
              })
              .join(", ");
          } else if (typeof errorResponse.detail === "string") {
            errorMessage = errorResponse.detail;
          }
        }
      }
    } catch (parseError) {
      errorMessage = "An unexpected error occurred. Please try again.";
    }

    setError(errorMessage);
  };

  // Forgot Password Functions
  const handleForgotPassword = async () => {
    setLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      const result = await forgotPassword(credentials.identifier);

      if (result && result.success) {
        setSuccessMessage("Password reset code sent to your email!");
        setForgotPasswordStep("otp");
      } else {
        handleError(result?.message || "Failed to send reset code");
      }
    } catch (error) {
      handleError(
        error?.message || "Failed to send reset code. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyResetToken = async () => {
    setLoading(true);
    setError("");

    try {
      const result = await verifyResetToken(credentials.identifier, otp);

      if (result && result.success) {
        setResetToken(result.token || otp);
        setForgotPasswordStep("reset");
        setSuccessMessage("Code verified! Please set your new password.");
      } else {
        handleError(result?.message || "Invalid reset code");
      }
    } catch (error) {
      handleError(error?.message || "Invalid reset code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async () => {
    setLoading(true);
    setError("");

    try {
      const result = await resetPassword(
        credentials.identifier,
        credentials.newPassword,
        resetToken
      );

      if (result && result.success) {
        setSuccessMessage(
          "Password reset successful! Please login with your new password."
        );
        setTimeout(() => {
          setShowForgotPassword(false);
          setForgotPasswordStep("email");
          setIsLogin(true);
          setActiveTab(0);
          resetForm();
        }, 2000);
      } else {
        handleError(result?.message || "Failed to reset password");
      }
    } catch (error) {
      handleError(
        error?.message || "Failed to reset password. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // Enhanced Google Sign-In handler
  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError("");

    try {
      const isSignupFlow = !isLogin;
      const loginResult = await handleGoogleAuth(isSignupFlow);

      if (loginResult && loginResult.success) {
        if (loginResult.token || loginResult.access_token) {
          localStorage.setItem(
            "token",
            loginResult.token || loginResult.access_token
          );
        }
        if (loginResult.user) {
          localStorage.setItem("userData", JSON.stringify(loginResult.user));
        }

        handleSuccess();
        return;
      }

      if (
        loginResult?.message?.includes("User not found") ||
        loginResult?.message?.includes("Please sign up first")
      ) {
        if (isLogin) {
          setError(
            "Account not found. Please use the Sign Up tab to create a new account with Google."
          );
        } else {
          setError(
            "This Google account is not registered. Please try signing up first."
          );
        }
      } else {
        setError(
          loginResult?.message ||
            "Google authentication failed. Please try again."
        );
      }
    } catch (error) {
      setError("Google authentication failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Enhanced auth handler for regular login/signup
  const handleAuth = async () => {
    setError("");
    setLoading(true);

    try {
      let response;

      if (isLogin) {
        response = await login({
          email: credentials.identifier,
          password: credentials.password,
        });

        if (response && (response.success || response.access_token)) {
          if (response.access_token) {
            localStorage.setItem("token", response.access_token);
          }
          handleSuccess();
        } else {
          handleError(response?.message || response || "Login failed");
        }
      } else {
        // Signup with email verification
        response = await signup({
          full_name: credentials.fullname,
          email: credentials.identifier,
          phone_number: credentials.phone || null,
          country_code: credentials.phone ? credentials.countryCode : null,
          password: credentials.password,
          send_email_verification: true,
        });

        if (response && response.success) {
          setSignupStep("email-verification");
          setSuccessMessage(
            "Account created! Please check your email for verification code."
          );
        } else {
          handleError(response?.message || response || "Signup failed");
        }
      }
    } catch (err) {
      handleError(
        err?.message || err || "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // Handle email verification during signup
  const handleEmailVerification = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await verifyEmailOTP(credentials.identifier, otp);

      if (response && response.success) {
        if (response.access_token) {
          localStorage.setItem("token", response.access_token);
        }
        if (response.user) {
          localStorage.setItem("userData", JSON.stringify(response.user));
        }

        setSuccessMessage("Email verified! Welcome to your account.");
        setTimeout(() => {
          handleSuccess();
        }, 1500);
      } else {
        handleError(response?.message || "Invalid verification code");
      }
    } catch (error) {
      handleError(
        error?.message || "Invalid verification code. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // Resend email verification
  const handleResendEmailVerification = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await sendEmailOTP(credentials.identifier);

      if (response && response.success) {
        setSuccessMessage("Verification code resent to your email!");
      } else {
        handleError("Failed to resend verification code");
      }
    } catch (error) {
      handleError("Failed to resend verification code");
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = () => {
    handleClose();
    setCredentials({
      fullname: "",
      identifier: "",
      phone: "",
      countryCode: "+1",
      password: "",
      confirmPassword: "",
      newPassword: "",
    });
    setOtp("");
    setError("");
    setSuccessMessage("");
    resetForm();
    window.dispatchEvent(new Event("storage"));
    onLoginSuccess();
  };

  // Get current step info for different flows
  const getCurrentStepInfo = () => {
    if (showForgotPassword) {
      switch (forgotPasswordStep) {
        case "email":
          return {
            title: "Reset Password",
            description: "Enter your email to receive a reset code",
            icon: "🔐",
          };
        case "otp":
          return {
            title: "Verify Reset Code",
            description: `Enter the code sent to ${credentials.identifier}`,
            icon: "📧",
          };
        case "reset":
          return {
            title: "Set New Password",
            description: "Create a new secure password",
            icon: "🔑",
          };
        default:
          return { title: "", description: "", icon: "" };
      }
    } else if (!isLogin && signupStep === "email-verification") {
      return {
        title: "Verify Your Email",
        description: `Enter the verification code sent to ${credentials.identifier}`,
        icon: "📧",
      };
    }
    return { title: "", description: "", icon: "" };
  };

  const shouldShowTabs =
    !showForgotPassword && !(signupStep === "email-verification");
  const shouldShowBackButton =
    showForgotPassword || signupStep === "email-verification";

  return (
    <Drawer
      anchor={isMobile ? "bottom" : "right"}
      open={open}
      onClose={handleClose}
      PaperProps={{
        sx: {
          background:
            theme.palette.mode === "dark"
              ? "linear-gradient(145deg, #111827, #1f2937)"
              : "linear-gradient(145deg, #f9fafb, #f3f4f6)",
          borderRadius: isMobile ? "16px 16px 0 0" : "0",
          boxShadow: "0 10px 30px rgba(0,0,0,0.15)",
        },
      }}
    >
      <Box
        sx={{
          width: isMobile ? "100%" : isMedium ? 400 : 450,
          maxHeight: isMobile ? "92vh" : "100%",
          overflowY: "auto",
          p: isMobile ? 3 : 4,
          position: "relative",
        }}
      >
        {/* Close button */}
        <IconButton
          onClick={handleClose}
          sx={{
            position: "absolute",
            top: 16,
            right: 16,
            backgroundColor: "rgba(0, 0, 0, 0.03)",
            "&:hover": {
              backgroundColor: "rgba(0, 0, 0, 0.07)",
            },
            zIndex: 1,
          }}
        >
          <CloseIcon />
        </IconButton>

        {/* Back button */}
        {shouldShowBackButton && (
          <IconButton
            onClick={() => {
              if (showForgotPassword) {
                setShowForgotPassword(false);
                setForgotPasswordStep("email");
              } else if (signupStep === "email-verification") {
                setSignupStep("form");
              }
              resetForm();
            }}
            sx={{
              position: "absolute",
              top: 16,
              left: 16,
              backgroundColor: "rgba(0, 0, 0, 0.03)",
              "&:hover": {
                backgroundColor: "rgba(0, 0, 0, 0.07)",
              },
              zIndex: 1,
            }}
          >
            <ArrowBackIcon />
          </IconButton>
        )}

        {/* Dynamic Avatar */}
        <Box sx={{ display: "flex", justifyContent: "center", mb: 3 }}>
          <Avatar
            sx={{
              width: 64,
              height: 64,
              bgcolor: avatarColor,
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
              fontSize: "1.6rem",
              fontWeight: 600,
              transition: "all 0.3s ease",
            }}
          >
            {showForgotPassword || signupStep === "email-verification"
              ? getCurrentStepInfo().icon
              : userInitials}
          </Avatar>
        </Box>

        {/* Title */}
        <Typography
          variant="h5"
          sx={{
            fontWeight: 700,
            mb: 0.5,
            textAlign: "center",
            backgroundImage: "linear-gradient(90deg, #3f8fff, #75b8ff)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          {showForgotPassword || signupStep === "email-verification"
            ? getCurrentStepInfo().title
            : isLogin
            ? "Welcome Back"
            : "Create Account"}
        </Typography>

        <Typography
          variant="body2"
          sx={{ color: "text.secondary", mb: 3, textAlign: "center" }}
        >
          {showForgotPassword || signupStep === "email-verification"
            ? getCurrentStepInfo().description
            : isLogin
            ? "Access your trading account"
            : "Join the algorithmic trading community"}
        </Typography>

        {/* Tab Navigation */}
        {shouldShowTabs && (
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            centered
            sx={{
              mb: 3,
              "& .MuiTabs-indicator": {
                height: 3,
                borderRadius: "2px",
              },
            }}
          >
            <Tab
              label="Login"
              sx={{
                fontWeight: activeTab === 0 ? 700 : 500,
                textTransform: "none",
                fontSize: "1rem",
                opacity: activeTab === 0 ? 1 : 0.7,
              }}
            />
            <Tab
              label="Sign Up"
              sx={{
                fontWeight: activeTab === 1 ? 700 : 500,
                textTransform: "none",
                fontSize: "1rem",
                opacity: activeTab === 1 ? 1 : 0.7,
              }}
            />
          </Tabs>
        )}

        {/* Success Message */}
        <Collapse in={!!successMessage}>
          <Alert
            severity="success"
            sx={{ mb: 2, borderRadius: "8px" }}
            onClose={() => setSuccessMessage("")}
          >
            {successMessage}
          </Alert>
        </Collapse>

        {/* Error Message */}
        <Collapse in={!!error}>
          <Alert
            severity="error"
            sx={{ mb: 2, borderRadius: "8px" }}
            onClose={() => setError("")}
          >
            {typeof error === "string"
              ? error
              : "An error occurred. Please try again."}
          </Alert>
        </Collapse>

        {/* Forgot Password Flow */}
        {showForgotPassword ? (
          <Box>
            {forgotPasswordStep === "email" && (
              <>
                <TextField
                  fullWidth
                  label="Email Address"
                  name="identifier"
                  variant="outlined"
                  value={credentials.identifier}
                  onChange={handleChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 3,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                <Button
                  fullWidth
                  variant="contained"
                  disabled={loading || !formValid}
                  onClick={handleForgotPassword}
                  sx={{
                    py: 1.5,
                    borderRadius: "10px",
                    textTransform: "none",
                    fontWeight: 600,
                    fontSize: "1rem",
                    background: formValid
                      ? "linear-gradient(90deg, #3f8fff, #75b8ff)"
                      : undefined,
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: "white" }} />
                  ) : (
                    "Send Reset Code"
                  )}
                </Button>
              </>
            )}

            {forgotPasswordStep === "otp" && (
              <>
                <TextField
                  fullWidth
                  label="Enter Reset Code"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  sx={{
                    mb: 3,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                <Button
                  fullWidth
                  variant="contained"
                  disabled={loading || !formValid}
                  onClick={handleVerifyResetToken}
                  sx={{
                    py: 1.5,
                    borderRadius: "10px",
                    textTransform: "none",
                    fontWeight: 600,
                    fontSize: "1rem",
                    background: formValid
                      ? "linear-gradient(90deg, #3f8fff, #75b8ff)"
                      : undefined,
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: "white" }} />
                  ) : (
                    "Verify Code"
                  )}
                </Button>

                <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
                  <Button
                    variant="text"
                    onClick={handleForgotPassword}
                    disabled={loading}
                    sx={{ textTransform: "none" }}
                  >
                    Resend Code
                  </Button>
                </Box>
              </>
            )}

            {forgotPasswordStep === "reset" && (
              <>
                <TextField
                  fullWidth
                  label="New Password"
                  name="newPassword"
                  type={showPassword ? "text" : "password"}
                  variant="outlined"
                  value={credentials.newPassword}
                  onChange={handleChange}
                  helperText="At least 6 characters"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon fontSize="small" />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                        >
                          {showPassword ? (
                            <VisibilityOffIcon fontSize="small" />
                          ) : (
                            <VisibilityIcon fontSize="small" />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 2,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                <TextField
                  fullWidth
                  label="Confirm New Password"
                  name="confirmPassword"
                  type={showPassword ? "text" : "password"}
                  variant="outlined"
                  value={credentials.confirmPassword}
                  onChange={handleChange}
                  error={
                    credentials.confirmPassword &&
                    credentials.newPassword !== credentials.confirmPassword
                  }
                  helperText={
                    credentials.confirmPassword &&
                    credentials.newPassword !== credentials.confirmPassword
                      ? "Passwords don't match"
                      : ""
                  }
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 3,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                <Button
                  fullWidth
                  variant="contained"
                  disabled={loading || !formValid}
                  onClick={handleResetPassword}
                  sx={{
                    py: 1.5,
                    borderRadius: "10px",
                    textTransform: "none",
                    fontWeight: 600,
                    fontSize: "1rem",
                    background: formValid
                      ? "linear-gradient(90deg, #3f8fff, #75b8ff)"
                      : undefined,
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: "white" }} />
                  ) : (
                    "Reset Password"
                  )}
                </Button>
              </>
            )}
          </Box>
        ) : signupStep === "email-verification" ? (
          /* Email Verification Step */
          <Box>
            <TextField
              fullWidth
              label="Enter Verification Code"
              value={otp}
              onChange={(e) => {
                setOtp(e.target.value);
                setError("");
              }}
              sx={{
                mb: 3,
                "& .MuiOutlinedInput-root": { borderRadius: "10px" },
              }}
            />

            <Button
              fullWidth
              variant="contained"
              disabled={loading || !formValid}
              onClick={handleEmailVerification}
              sx={{
                py: 1.5,
                borderRadius: "10px",
                textTransform: "none",
                fontWeight: 600,
                fontSize: "1rem",
                background: formValid
                  ? "linear-gradient(90deg, #3f8fff, #75b8ff)"
                  : undefined,
              }}
            >
              {loading ? (
                <CircularProgress size={24} sx={{ color: "white" }} />
              ) : (
                "Verify & Continue"
              )}
            </Button>

            <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
              <Button
                variant="text"
                onClick={handleResendEmailVerification}
                disabled={loading}
                sx={{ textTransform: "none" }}
              >
                Didn't receive code? Resend
              </Button>
            </Box>
          </Box>
        ) : (
          /* Normal Login/Signup Flow */
          <>
            {/* Login Form */}
            {isLogin && (
              <Box>
                <TextField
                  fullWidth
                  label="Email Address"
                  name="identifier"
                  variant="outlined"
                  margin="normal"
                  value={credentials.identifier}
                  onChange={handleChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 2,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                <TextField
                  fullWidth
                  label="Password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  variant="outlined"
                  margin="normal"
                  value={credentials.password}
                  onChange={handleChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon fontSize="small" />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                        >
                          {showPassword ? (
                            <VisibilityOffIcon fontSize="small" />
                          ) : (
                            <VisibilityIcon fontSize="small" />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 1,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                <Box
                  sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}
                >
                  <Link
                    component="button"
                    variant="body2"
                    onClick={() => setShowForgotPassword(true)}
                    sx={{
                      color: "primary.main",
                      textDecoration: "none",
                      "&:hover": { textDecoration: "underline" },
                    }}
                  >
                    Forgot password?
                  </Link>
                </Box>

                <Button
                  fullWidth
                  variant="contained"
                  disabled={loading || !formValid}
                  onClick={handleAuth}
                  sx={{
                    py: 1.5,
                    borderRadius: "10px",
                    textTransform: "none",
                    fontWeight: 600,
                    fontSize: "1rem",
                    background: formValid
                      ? "linear-gradient(90deg, #3f8fff, #75b8ff)"
                      : undefined,
                    boxShadow: formValid
                      ? "0 4px 12px rgba(63, 143, 255, 0.25)"
                      : "none",
                    "&:hover": {
                      background: formValid
                        ? "linear-gradient(90deg, #3080f0, #6aadff)"
                        : undefined,
                      boxShadow: formValid
                        ? "0 6px 16px rgba(63, 143, 255, 0.3)"
                        : "none",
                      transform: formValid ? "translateY(-2px)" : "none",
                    },
                    transition: "all 0.3s ease",
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: "white" }} />
                  ) : (
                    "Login"
                  )}
                </Button>

                {/* Google Login Button */}
                <Box sx={{ mt: 3, mb: 2 }}>
                  <Divider>
                    <Typography
                      variant="body2"
                      sx={{ color: "text.secondary", px: 1 }}
                    >
                      or continue with
                    </Typography>
                  </Divider>

                  <Box
                    sx={{ display: "flex", justifyContent: "center", mt: 2 }}
                  >
                    <Button
                      startIcon={<GoogleIcon />}
                      variant="outlined"
                      onClick={handleGoogleSignIn}
                      disabled={loading}
                      sx={{
                        px: 3,
                        py: 1,
                        borderRadius: "8px",
                        borderColor: "#4285f4",
                        color: "#4285f4",
                        textTransform: "none",
                        fontWeight: 500,
                        backgroundColor: "white",
                        "&:hover": {
                          backgroundColor: "#f8f9fa",
                          borderColor: "#3367d6",
                          color: "#3367d6",
                          boxShadow: "0 2px 8px rgba(66, 133, 244, 0.15)",
                        },
                      }}
                    >
                      {loading ? (
                        <CircularProgress size={20} sx={{ color: "#4285f4" }} />
                      ) : (
                        "Continue with Google"
                      )}
                    </Button>
                  </Box>
                </Box>
              </Box>
            )}

            {/* Sign Up Form */}
            {!isLogin && (
              <Box>
                <TextField
                  fullWidth
                  label="Full Name"
                  name="fullname"
                  variant="outlined"
                  margin="normal"
                  value={credentials.fullname}
                  onChange={handleChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <PersonIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 2,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                <TextField
                  fullWidth
                  label="Email Address"
                  name="identifier"
                  variant="outlined"
                  margin="normal"
                  value={credentials.identifier}
                  onChange={handleChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 2,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                {/* Optional Phone Number Fields */}
                <Box sx={{ mb: 2 }}>
                  <Typography
                    variant="body2"
                    sx={{ mb: 1, fontWeight: 500, color: "text.secondary" }}
                  >
                    Phone Number (Optional - can be added later in profile)
                  </Typography>
                  <Box
                    sx={{
                      display: "flex",
                      flexDirection: isMobile ? "column" : "row",
                      gap: 2,
                    }}
                  >
                    <FormControl
                      sx={{
                        minWidth: isMobile ? "100%" : 110,
                        "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                      }}
                    >
                      <InputLabel>Country Code</InputLabel>
                      <Select
                        name="countryCode"
                        value={credentials.countryCode}
                        onChange={handleChange}
                        label="Country Code"
                      >
                        {countryCodes.map((country) => (
                          <MenuItem key={country.code} value={country.code}>
                            {isMobile
                              ? country.code
                              : `${country.country} (${country.code})`}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <TextField
                      fullWidth
                      label="Phone Number (Optional)"
                      name="phone"
                      variant="outlined"
                      value={credentials.phone}
                      onChange={handleChange}
                      placeholder="Can be added later"
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <PhoneIcon fontSize="small" />
                          </InputAdornment>
                        ),
                      }}
                      sx={{
                        "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                      }}
                    />
                  </Box>
                </Box>

                <TextField
                  fullWidth
                  label="Password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  variant="outlined"
                  margin="normal"
                  value={credentials.password}
                  onChange={handleChange}
                  helperText="At least 6 characters"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockIcon fontSize="small" />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                        >
                          {showPassword ? (
                            <VisibilityOffIcon fontSize="small" />
                          ) : (
                            <VisibilityIcon fontSize="small" />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    mb: 2,
                    "& .MuiOutlinedInput-root": { borderRadius: "10px" },
                  }}
                />

                {/* Info Box about verification */}
                <Alert
                  severity="info"
                  sx={{
                    mb: 2,
                    borderRadius: "8px",
                    backgroundColor: "rgba(63, 143, 255, 0.05)",
                    border: "1px solid rgba(63, 143, 255, 0.2)",
                  }}
                >
                  <Typography variant="body2">
                    📧 Email verification required. Phone can be added later in
                    profile.
                  </Typography>
                </Alert>

                <Button
                  fullWidth
                  variant="contained"
                  disabled={loading || !formValid}
                  onClick={handleAuth}
                  sx={{
                    py: 1.5,
                    borderRadius: "10px",
                    textTransform: "none",
                    fontWeight: 600,
                    fontSize: "1rem",
                    background: formValid
                      ? "linear-gradient(90deg, #3f8fff, #75b8ff)"
                      : undefined,
                    boxShadow: formValid
                      ? "0 4px 12px rgba(63, 143, 255, 0.25)"
                      : "none",
                    "&:hover": {
                      background: formValid
                        ? "linear-gradient(90deg, #3080f0, #6aadff)"
                        : undefined,
                      boxShadow: formValid
                        ? "0 6px 16px rgba(63, 143, 255, 0.3)"
                        : "none",
                      transform: formValid ? "translateY(-2px)" : "none",
                    },
                    transition: "all 0.3s ease",
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: "white" }} />
                  ) : (
                    "Create Account"
                  )}
                </Button>

                {/* Google Signup Button */}
                <Box sx={{ mt: 3, mb: 2 }}>
                  <Divider>
                    <Typography
                      variant="body2"
                      sx={{ color: "text.secondary", px: 1 }}
                    >
                      or sign up with
                    </Typography>
                  </Divider>

                  <Box
                    sx={{ display: "flex", justifyContent: "center", mt: 2 }}
                  >
                    <Button
                      startIcon={<GoogleIcon />}
                      variant="outlined"
                      onClick={handleGoogleSignIn}
                      disabled={loading}
                      sx={{
                        px: 3,
                        py: 1,
                        borderRadius: "8px",
                        borderColor: "#4285f4",
                        color: "#4285f4",
                        textTransform: "none",
                        fontWeight: 500,
                        backgroundColor: "white",
                        "&:hover": {
                          backgroundColor: "#f8f9fa",
                          borderColor: "#3367d6",
                          color: "#3367d6",
                          boxShadow: "0 2px 8px rgba(66, 133, 244, 0.15)",
                        },
                      }}
                    >
                      {loading ? (
                        <CircularProgress size={20} sx={{ color: "#4285f4" }} />
                      ) : (
                        "Continue with Google"
                      )}
                    </Button>
                  </Box>
                </Box>

                {/* Terms and Conditions */}
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    textAlign: "center",
                    mt: 2,
                    color: "text.secondary",
                  }}
                >
                  By signing up, you agree to our{" "}
                  <Link href="#" sx={{ fontWeight: 500 }}>
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="#" sx={{ fontWeight: 500 }}>
                    Privacy Policy
                  </Link>
                </Typography>
              </Box>
            )}
          </>
        )}
      </Box>
    </Drawer>
  );
};

export default AuthModal;
