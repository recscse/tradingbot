// src/components/common/LoadingSpinner.jsx
import React from "react";
import {
  Box,
  CircularProgress,
  Typography,
  useTheme,
  alpha,
} from "@mui/material";

const LoadingSpinner = ({
  size = "large",
  text = "Loading...",
  color = "primary",
  variant = "indeterminate",
}) => {
  const theme = useTheme();

  const sizeMap = {
    small: 20,
    medium: 40,
    large: 60,
  };

  const textSizeMap = {
    small: "caption",
    medium: "body2",
    large: "body1",
  };

  const spinnerSize = sizeMap[size] || sizeMap.large;
  const textVariant = textSizeMap[size] || textSizeMap.large;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        p: { xs: 4, sm: 6, md: 8 },
        minHeight: { xs: "200px", sm: "250px" },
        gap: { xs: 2, sm: 3 },
      }}
    >
      {/* Modern Spinning Loader */}
      <Box
        sx={{
          position: "relative",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Background Circle */}
        <CircularProgress
          variant="determinate"
          value={100}
          size={spinnerSize}
          thickness={4}
          sx={{
            color: alpha(theme.palette[color].main, 0.1),
            position: "absolute",
          }}
        />

        {/* Animated Circle */}
        <CircularProgress
          variant={variant}
          size={spinnerSize}
          thickness={4}
          sx={{
            color: theme.palette[color].main,
            animationDuration: "1.5s",
            filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.1))",
          }}
        />
      </Box>

      {/* Loading Text */}
      {text && (
        <Typography
          variant={textVariant}
          sx={{
            color: "text.secondary",
            textAlign: "center",
            fontWeight: 500,
            opacity: 0.8,
            mt: 1,
            px: 2,
            maxWidth: "300px",
          }}
        >
          {text}
        </Typography>
      )}
    </Box>
  );
};

// Enhanced version with more features
export const LoadingSpinnerEnhanced = ({
  size = "large",
  text = "Loading...",
  subtitle,
  color = "primary",
  variant = "indeterminate",
  showProgress = false,
  progress = 0,
}) => {
  const theme = useTheme();

  const sizeMap = {
    small: 20,
    medium: 40,
    large: 60,
    xlarge: 80,
  };

  const spinnerSize = sizeMap[size] || sizeMap.large;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        p: { xs: 4, sm: 6, md: 8 },
        minHeight: { xs: "200px", sm: "300px" },
        gap: { xs: 2, sm: 3 },
        background: `linear-gradient(135deg, ${alpha(
          theme.palette.primary.main,
          0.02
        )} 0%, ${alpha(theme.palette.secondary.main, 0.02)} 100%)`,
        borderRadius: 2,
        position: "relative",
        overflow: "hidden",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background:
            "radial-gradient(circle at center, rgba(255,255,255,0.1) 0%, transparent 70%)",
          pointerEvents: "none",
        },
      }}
    >
      {/* Enhanced Spinning Loader with Glow Effect */}
      <Box
        sx={{
          position: "relative",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          "&::before": {
            content: '""',
            position: "absolute",
            width: spinnerSize + 20,
            height: spinnerSize + 20,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${alpha(
              theme.palette[color].main,
              0.1
            )} 0%, transparent 70%)`,
            animation: "pulse 2s ease-in-out infinite",
          },
        }}
      >
        {/* Background Circle */}
        <CircularProgress
          variant="determinate"
          value={100}
          size={spinnerSize}
          thickness={3}
          sx={{
            color: alpha(theme.palette[color].main, 0.1),
            position: "absolute",
          }}
        />

        {/* Animated Circle */}
        <CircularProgress
          variant={showProgress ? "determinate" : variant}
          value={showProgress ? progress : undefined}
          size={spinnerSize}
          thickness={3}
          sx={{
            color: theme.palette[color].main,
            animationDuration: "1.2s",
            filter: "drop-shadow(0 0 8px rgba(0,0,0,0.2))",
            zIndex: 1,
          }}
        />

        {/* Progress Text Inside Circle */}
        {showProgress && (
          <Box
            sx={{
              position: "absolute",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: theme.palette[color].main,
                fontWeight: 600,
                fontSize: size === "small" ? "0.6rem" : "0.75rem",
              }}
            >
              {Math.round(progress)}%
            </Typography>
          </Box>
        )}
      </Box>

      {/* Loading Text */}
      {text && (
        <Box sx={{ textAlign: "center", maxWidth: "400px" }}>
          <Typography
            variant={size === "small" ? "body2" : "h6"}
            sx={{
              color: "text.primary",
              fontWeight: 600,
              mb: subtitle ? 1 : 0,
              background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            {text}
          </Typography>

          {subtitle && (
            <Typography
              variant="body2"
              sx={{
                color: "text.secondary",
                opacity: 0.7,
                px: 2,
              }}
            >
              {subtitle}
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
};

export default LoadingSpinner;
