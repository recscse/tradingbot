// src/components/profile/BrokerAccountCard.jsx
import React, { useState } from "react";
import {
  Card,
  CardContent,
  Box,
  Typography,
  Avatar,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  useTheme,
  Tooltip,
} from "@mui/material";
import {
  Business as BusinessIcon,
  CheckCircle as CheckIcon,
  Cancel as XIcon,
  Settings as SettingsIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  AccountBalance as AccountBalanceIcon,
} from "@mui/icons-material";

const BrokerAccountCard = ({
  account,
  onEdit,
  onDelete,
  onView,
  onToggleStatus,
  variant = "default",
  showActions = true,
}) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleMenuAction = (action) => {
    handleMenuClose();
    switch (action) {
      case "edit":
        onEdit?.(account);
        break;
      case "delete":
        onDelete?.(account);
        break;
      case "view":
        onView?.(account);
        break;
      case "toggle":
        onToggleStatus?.(account);
        break;
      default:
        break;
    }
  };

  const getBrokerIcon = () => {
    const name = account.broker_name?.toLowerCase();
    switch (name) {
      case "zerodha":
        return "Z";
      case "upstox":
        return "U";
      case "angel one":
      case "angel broking":
        return "A";
      case "iifl":
        return "I";
      case "dhan":
        return "D";
      case "fyers":
        return "F";
      default:
        return <BusinessIcon />;
    }
  };

  const getBrokerColor = (name) => {
    switch (name?.toLowerCase()) {
      case "zerodha":
        return "#FF6B35";
      case "upstox":
        return "#7B68EE";
      case "angel one":
      case "angel broking":
        return "#1976D2";
      case "iifl":
        return "#FFD700";
      case "dhan":
        return "#FF9800";
      case "fyers":
        return "#4CAF50";
      default:
        return theme.palette.primary.main;
    }
  };

  // Compact variant for lists
  if (variant === "compact") {
    return (
      <Card
        sx={{
          mb: 1,
          transition: "all 0.2s ease",
          "&:hover": {
            transform: "translateX(2px)",
            boxShadow: theme.shadows[2],
          },
        }}
        elevation={0}
      >
        <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Avatar
              sx={{
                width: 36,
                height: 36,
                bgcolor: getBrokerColor(account.broker_name),
                color: "white",
                fontSize: "0.875rem",
                fontWeight: 600,
              }}
            >
              {getBrokerIcon()}
            </Avatar>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" fontWeight={600} noWrap>
                {account.broker_name || "Unknown Broker"}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatCurrency(account.balance)}
              </Typography>
            </Box>

            <Chip
              size="small"
              label={account.is_active ? "Active" : "Inactive"}
              color={account.is_active ? "success" : "default"}
              sx={{ fontWeight: 500 }}
            />
          </Box>
        </CardContent>
      </Card>
    );
  }

  // Default variant
  return (
    <Card
      sx={{
        transition: "all 0.2s ease",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: theme.shadows[4],
        },
      }}
      elevation={1}
    >
      <CardContent sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 2,
          }}
        >
          {/* Broker Info */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, flex: 1 }}>
            <Avatar
              sx={{
                width: 48,
                height: 48,
                bgcolor: getBrokerColor(account.broker_name),
                color: "white",
                fontSize: "1.25rem",
                fontWeight: 700,
              }}
            >
              {getBrokerIcon()}
            </Avatar>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                {account.broker_name || "Unknown Broker"}
              </Typography>

              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <AccountBalanceIcon
                  sx={{ fontSize: 16, color: "text.secondary" }}
                />
                <Typography variant="body2" color="text.secondary">
                  Balance: <strong>{formatCurrency(account.balance)}</strong>
                </Typography>
              </Box>

              {account.created_at && (
                <Typography variant="caption" color="text.secondary">
                  Connected: {new Date(account.created_at).toLocaleDateString()}
                </Typography>
              )}
            </Box>
          </Box>

          {/* Status & Actions */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              icon={account.is_active ? <CheckIcon /> : <XIcon />}
              label={account.is_active ? "Active" : "Inactive"}
              color={account.is_active ? "success" : "error"}
              size="small"
              sx={{ fontWeight: 600 }}
            />

            {showActions && (
              <Tooltip title="More options">
                <IconButton
                  size="small"
                  onClick={handleMenuOpen}
                  sx={{
                    color: "text.secondary",
                    "&:hover": { color: "primary.main" },
                  }}
                >
                  <SettingsIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>

        {/* Additional Stats for detailed variant */}
        {variant === "detailed" && (
          <Box
            sx={{
              pt: 2,
              borderTop: `1px solid ${theme.palette.divider}`,
              display: "flex",
              gap: 3,
            }}
          >
            <Box>
              <Typography variant="caption" color="text.secondary">
                Last Updated
              </Typography>
              <Typography variant="body2" fontWeight={500}>
                {account.updated_at
                  ? new Date(account.updated_at).toLocaleString()
                  : "Never"}
              </Typography>
            </Box>

            <Box>
              <Typography variant="caption" color="text.secondary">
                Status
              </Typography>
              <Typography
                variant="body2"
                fontWeight={500}
                color={account.is_active ? "success.main" : "error.main"}
              >
                {account.is_active ? "Connected" : "Disconnected"}
              </Typography>
            </Box>
          </Box>
        )}
      </CardContent>

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleMenuClose}
        PaperProps={{
          sx: {
            minWidth: 160,
            "& .MuiMenuItem-root": {
              borderRadius: 1,
              mx: 1,
              my: 0.5,
            },
          },
        }}
      >
        <MenuItem onClick={() => handleMenuAction("view")}>
          <ListItemIcon>
            <ViewIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Details</ListItemText>
        </MenuItem>

        <MenuItem onClick={() => handleMenuAction("edit")}>
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit Account</ListItemText>
        </MenuItem>

        <MenuItem onClick={() => handleMenuAction("toggle")}>
          <ListItemIcon>
            {account.is_active ? (
              <XIcon fontSize="small" />
            ) : (
              <CheckIcon fontSize="small" />
            )}
          </ListItemIcon>
          <ListItemText>
            {account.is_active ? "Deactivate" : "Activate"}
          </ListItemText>
        </MenuItem>

        <MenuItem
          onClick={() => handleMenuAction("delete")}
          sx={{ color: "error.main" }}
        >
          <ListItemIcon>
            <DeleteIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>Delete Account</ListItemText>
        </MenuItem>
      </Menu>
    </Card>
  );
};

export default BrokerAccountCard;
