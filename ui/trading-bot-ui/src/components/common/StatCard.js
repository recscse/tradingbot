// src/components/common/StatCard.jsx
import React from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  useTheme,
  alpha,
  Grow,
} from "@mui/material";
import { TrendingUp, TrendingDown, Minimize } from "@mui/icons-material";

const StatCard = ({
  title,
  value,
  icon: Icon,
  trend,
  subtitle,
  color = "text.primary",
  variant = "default", // default, gradient, outlined, elevated
  animate = true,
  size = "medium", // small, medium, large
}) => {
  const theme = useTheme();

  const getTrendIcon = () => {
    const iconProps = {
      fontSize: size === "small" ? "small" : "medium",
      sx: { ml: 1 },
    };

    if (trend === "up") {
      return (
        <TrendingUp
          {...iconProps}
          sx={{ ...iconProps.sx, color: "success.main" }}
        />
      );
    }
    if (trend === "down") {
      return (
        <TrendingDown
          {...iconProps}
          sx={{ ...iconProps.sx, color: "error.main" }}
        />
      );
    }
    if (trend === "neutral") {
      return (
        <Minimize
          {...iconProps}
          sx={{ ...iconProps.sx, color: "text.secondary" }}
        />
      );
    }
    return null;
  };

  const getTrendColor = () => {
    if (trend === "up") return "success.main";
    if (trend === "down") return "error.main";
    return color;
  };

  const sizeProps = {
    small: {
      padding: 2,
      iconSize: 20,
      titleVariant: "caption",
      valueVariant: "h6",
      subtitleVariant: "caption",
    },
    medium: {
      padding: 3,
      iconSize: 24,
      titleVariant: "body2",
      valueVariant: "h4",
      subtitleVariant: "body2",
    },
    large: {
      padding: 4,
      iconSize: 28,
      titleVariant: "body1",
      valueVariant: "h3",
      subtitleVariant: "body1",
    },
  };

  const currentSize = sizeProps[size] || sizeProps.medium;

  const getCardStyles = () => {
    const baseStyles = {
      height: "100%",
      transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
      cursor: "default",
      "&:hover": {
        transform: animate ? "translateY(-4px)" : "none",
        boxShadow: theme.shadows[8],
      },
    };

    switch (variant) {
      case "gradient":
        return {
          ...baseStyles,
          background: `linear-gradient(135deg, ${alpha(
            theme.palette.primary.main,
            0.1
          )} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
          border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
          "&:hover": {
            ...baseStyles["&:hover"],
            background: `linear-gradient(135deg, ${alpha(
              theme.palette.primary.main,
              0.15
            )} 0%, ${alpha(theme.palette.secondary.main, 0.15)} 100%)`,
          },
        };
      case "outlined":
        return {
          ...baseStyles,
          border: `2px solid ${alpha(theme.palette.divider, 0.1)}`,
          backgroundColor: alpha(theme.palette.background.paper, 0.8),
          backdropFilter: "blur(10px)",
          "&:hover": {
            ...baseStyles["&:hover"],
            border: `2px solid ${alpha(theme.palette.primary.main, 0.3)}`,
          },
        };
      case "elevated":
        return {
          ...baseStyles,
          boxShadow: theme.shadows[4],
          "&:hover": {
            ...baseStyles["&:hover"],
            boxShadow: theme.shadows[12],
          },
        };
      default:
        return {
          ...baseStyles,
          boxShadow: theme.shadows[1],
          "&:hover": {
            ...baseStyles["&:hover"],
            boxShadow: theme.shadows[4],
          },
        };
    }
  };

  const CardWrapper = animate ? Grow : Box;
  const wrapperProps = animate ? { in: true, timeout: 300 } : {};

  return (
    <CardWrapper {...wrapperProps}>
      <Card sx={getCardStyles()} elevation={0}>
        <CardContent sx={{ p: currentSize.padding }}>
          {/* Header with Icon and Title */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 2,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {Icon && (
                <Icon
                  sx={{
                    fontSize: currentSize.iconSize,
                    color: "text.secondary",
                  }}
                />
              )}
              <Typography
                variant={currentSize.titleVariant}
                sx={{
                  color: "text.secondary",
                  fontWeight: 500,
                  textTransform: "uppercase",
                  letterSpacing: 0.5,
                }}
              >
                {title}
              </Typography>
            </Box>
            {getTrendIcon()}
          </Box>

          {/* Main Value */}
          <Typography
            variant={currentSize.valueVariant}
            component="div"
            sx={{
              color: getTrendColor(),
              fontWeight: 700,
              mb: subtitle ? 1 : 0,
              wordBreak: "break-word",
              lineHeight: 1.2,
            }}
          >
            {value}
          </Typography>

          {/* Subtitle */}
          {subtitle && (
            <Typography
              variant={currentSize.subtitleVariant}
              sx={{
                color: "text.secondary",
                opacity: 0.8,
                mt: 1,
              }}
            >
              {subtitle}
            </Typography>
          )}
        </CardContent>
      </Card>
    </CardWrapper>
  );
};

// Enhanced StatCard with more features
export const StatCardEnhanced = ({
  title,
  value,
  icon: Icon,
  trend,
  subtitle,
  color = "text.primary",
  variant = "default",
  animate = true,
  size = "medium",
  loading = false,
  prefix = "",
  suffix = "",
  percentage,
  compareValue,
}) => {
  return (
    <StatCard
      title={title}
      value={loading ? "Loading..." : `${prefix}${value}${suffix}`}
      icon={Icon}
      trend={trend}
      subtitle={
        loading
          ? "Please wait..."
          : compareValue
          ? `${subtitle} (vs ${compareValue})`
          : percentage
          ? `${subtitle} (${percentage > 0 ? "+" : ""}${percentage}%)`
          : subtitle
      }
      color={color}
      variant={variant}
      animate={animate}
      size={size}
    />
  );
};

// Specialized StatCards for common use cases
export const PnLStatCard = ({ value, title = "P&L", ...props }) => (
  <StatCard
    title={title}
    value={`₹${Math.abs(value).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
    })}`}
    trend={value > 0 ? "up" : value < 0 ? "down" : "neutral"}
    color={
      value > 0 ? "success.main" : value < 0 ? "error.main" : "text.primary"
    }
    {...props}
  />
);

export const PercentageStatCard = ({ value, title, ...props }) => (
  <StatCard
    title={title}
    value={`${value.toFixed(2)}%`}
    trend={value > 0 ? "up" : value < 0 ? "down" : "neutral"}
    color={
      value > 0 ? "success.main" : value < 0 ? "error.main" : "text.primary"
    }
    {...props}
  />
);

export const CountStatCard = ({ value, title, ...props }) => (
  <StatCard title={title} value={value.toLocaleString()} {...props} />
);

export default StatCard;
