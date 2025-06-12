// src/components/profile/ProfileTabs.jsx
import React from "react";
import {
  Box,
  Tabs,
  Tab,
  Typography,
  FormControl,
  Select,
  MenuItem,
  Avatar,
  useTheme,
  alpha,
  useMediaQuery,
  Badge,
  Tooltip,
  Paper,
  Stack,
  Chip,
  IconButton,
  Skeleton,
  Fade,
} from "@mui/material";
import {
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
  Business as BrokerIcon,
  ExpandMore as ExpandMoreIcon,
  KeyboardArrowRight as ArrowIcon,
  Dashboard as DashboardIcon,
  Assessment as AnalyticsIcon,
  AccountCircle as ProfileIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from "@mui/icons-material";

const ProfileTabs = ({
  activeTab,
  onTabChange,
  tabData = {},
  loading = false,
  notificationCounts = {},
  securityAlerts = 0,
  brokerCount = 0,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const isSmallMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const [expandedDescription, setExpandedDescription] = useState(false);

  // Enhanced tabs configuration with dynamic data
  const tabs = [
    {
      id: "overview",
      label: "Overview",
      icon: DashboardIcon,
      description: "Account summary, performance metrics, and quick insights",
      color: "primary",
      badge: null,
      disabled: false,
    },
    {
      id: "performance",
      label: "Performance",
      icon: AnalyticsIcon,
      description: "Trading analytics, P&L reports, and performance metrics",
      color: "success",
      badge: null,
      disabled: false,
    },
    {
      id: "brokers",
      label: "Brokers",
      icon: BrokerIcon,
      description: `Manage ${
        brokerCount || 0
      } broker connections and trading accounts`,
      color: "info",
      badge: brokerCount > 0 ? brokerCount : null,
      disabled: false,
    },
    {
      id: "settings",
      label: "Profile",
      icon: ProfileIcon,
      description: "Personal information, preferences, and account settings",
      color: "secondary",
      badge: null,
      disabled: false,
    },
    {
      id: "security",
      label: "Security",
      icon: SecurityIcon,
      description: "Password, two-factor authentication, and security settings",
      color: "error",
      badge: securityAlerts > 0 ? securityAlerts : null,
      disabled: false,
      urgent: securityAlerts > 0,
    },
    {
      id: "notifications",
      label: "Notifications",
      icon: NotificationsIcon,
      description: "Alert preferences, notification history, and settings",
      color: "warning",
      badge: notificationCounts?.unread || null,
      disabled: false,
    },
  ];

  // Safe tab data access
  const getTabBadgeCount = (tabId) => {
    switch (tabId) {
      case "notifications":
        return notificationCounts?.unread || 0;
      case "security":
        return securityAlerts || 0;
      case "brokers":
        return brokerCount || 0;
      default:
        return tabData?.[tabId]?.badge || 0;
    }
  };

  // Update tab descriptions and badges dynamically
  const getUpdatedTab = (tab) => ({
    ...tab,
    badge: getTabBadgeCount(tab.id),
    description:
      tab.id === "brokers"
        ? `Manage ${brokerCount || 0} broker connection${
            brokerCount !== 1 ? "s" : ""
          } and trading accounts`
        : tab.description,
  });

  const updatedTabs = tabs.map(getUpdatedTab);
  const activeTabIndex = updatedTabs.findIndex((tab) => tab.id === activeTab);
  const activeTabData = updatedTabs.find((tab) => tab.id === activeTab);

  const handleTabChange = (event, newValue) => {
    if (loading) return;
    const selectedTab = updatedTabs[newValue];
    if (selectedTab && !selectedTab.disabled) {
      onTabChange(selectedTab.id);
    }
  };

  const handleMobileTabChange = (event) => {
    if (loading) return;
    const selectedTabId = event.target.value;
    const selectedTab = updatedTabs.find((tab) => tab.id === selectedTabId);
    if (selectedTab && !selectedTab.disabled) {
      onTabChange(selectedTabId);
    }
  };

  // Enhanced Tab Label Component with better accessibility
  const TabLabel = ({
    tab,
    isActive = false,
    showDescription = false,
    compact = false,
  }) => {
    const updatedTab = getUpdatedTab(tab);

    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: compact ? 1 : 1.5,
          py: compact ? 0.25 : 0.5,
          opacity: updatedTab.disabled ? 0.5 : 1,
          filter: updatedTab.disabled ? "grayscale(1)" : "none",
        }}
      >
        <Avatar
          sx={{
            width: compact ? 28 : { xs: 32, sm: 36 },
            height: compact ? 28 : { xs: 32, sm: 36 },
            bgcolor: isActive
              ? `${updatedTab.color}.main`
              : alpha(
                  theme.palette[updatedTab.color].main,
                  updatedTab.urgent ? 0.15 : 0.1
                ),
            color: isActive
              ? "white"
              : updatedTab.urgent
              ? `${updatedTab.color}.main`
              : `${updatedTab.color}.main`,
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            boxShadow: isActive
              ? `0 4px 12px ${alpha(theme.palette[updatedTab.color].main, 0.4)}`
              : updatedTab.urgent
              ? `0 2px 8px ${alpha(theme.palette[updatedTab.color].main, 0.2)}`
              : "none",
            border:
              updatedTab.urgent && !isActive
                ? `2px solid ${alpha(
                    theme.palette[updatedTab.color].main,
                    0.3
                  )}`
                : "none",
          }}
        >
          <updatedTab.icon
            sx={{ fontSize: compact ? 14 : { xs: 16, sm: 18 } }}
          />
        </Avatar>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography
              variant={compact ? "body2" : "body1"}
              sx={{
                fontWeight: isActive ? 700 : 600,
                fontSize: compact ? "0.8rem" : { xs: "0.875rem", sm: "1rem" },
                color: isActive
                  ? "text.primary"
                  : updatedTab.disabled
                  ? "text.disabled"
                  : "text.secondary",
                lineHeight: 1.2,
              }}
            >
              {updatedTab.label}
            </Typography>

            {updatedTab.badge && updatedTab.badge > 0 && (
              <Badge
                badgeContent={updatedTab.badge > 99 ? "99+" : updatedTab.badge}
                color={updatedTab.urgent ? "error" : "primary"}
                sx={{
                  "& .MuiBadge-badge": {
                    fontSize: compact ? "0.5rem" : "0.6rem",
                    height: compact ? 16 : 18,
                    minWidth: compact ? 16 : 18,
                    fontWeight: 600,
                    animation: updatedTab.urgent ? "pulse 2s infinite" : "none",
                    "@keyframes pulse": {
                      "0%": { transform: "scale(1)" },
                      "50%": { transform: "scale(1.1)" },
                      "100%": { transform: "scale(1)" },
                    },
                  },
                }}
              />
            )}

            {updatedTab.urgent && (
              <Tooltip title="Requires attention">
                <WarningIcon
                  sx={{
                    fontSize: 16,
                    color: "error.main",
                    animation: "pulse 2s infinite",
                  }}
                />
              </Tooltip>
            )}
          </Stack>

          {showDescription && (
            <Typography
              variant="caption"
              color={updatedTab.disabled ? "text.disabled" : "text.secondary"}
              sx={{
                fontSize: compact ? "0.7rem" : "0.75rem",
                lineHeight: 1.2,
                display: "block",
                mt: 0.25,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: compact ? "nowrap" : "normal",
              }}
            >
              {updatedTab.description}
            </Typography>
          )}
        </Box>

        {showDescription && !compact && (
          <ArrowIcon
            sx={{
              color: "text.disabled",
              fontSize: 18,
              opacity: isActive ? 1 : 0.5,
              transform: isActive ? "rotate(90deg)" : "rotate(0deg)",
              transition: "all 0.3s ease",
            }}
          />
        )}
      </Box>
    );
  };

  // Mobile Dropdown Selector with enhanced design
  const MobileTabSelector = () => (
    <Paper
      elevation={0}
      sx={{
        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        borderRadius: 3,
        overflow: "hidden",
        background: `linear-gradient(135deg, 
          ${alpha(theme.palette.background.paper, 0.9)} 0%, 
          ${alpha(theme.palette.primary.main, 0.02)} 100%
        )`,
        backdropFilter: "blur(20px)",
      }}
    >
      <FormControl fullWidth disabled={loading}>
        <Select
          value={loading ? "" : activeTab}
          onChange={handleMobileTabChange}
          displayEmpty
          IconComponent={ExpandMoreIcon}
          sx={{
            "& .MuiSelect-select": {
              py: 2,
              px: 3,
              display: "flex",
              alignItems: "center",
            },
            "& .MuiOutlinedInput-notchedOutline": {
              border: "none",
            },
            "&:hover": {
              bgcolor: alpha(theme.palette.primary.main, 0.04),
            },
            "& .MuiSelect-icon": {
              transition: "transform 0.3s ease",
            },
            "&.Mui-focused .MuiSelect-icon": {
              transform: "rotate(180deg)",
            },
          }}
          renderValue={(selected) => {
            if (loading) {
              return (
                <Stack direction="row" alignItems="center" spacing={2}>
                  <Skeleton variant="circular" width={36} height={36} />
                  <Stack>
                    <Skeleton variant="text" width={120} height={20} />
                    <Skeleton variant="text" width={200} height={16} />
                  </Stack>
                </Stack>
              );
            }

            const selectedTab = updatedTabs.find((tab) => tab.id === selected);
            return selectedTab ? (
              <TabLabel
                tab={selectedTab}
                isActive={true}
                showDescription={!isSmallMobile}
              />
            ) : null;
          }}
        >
          {updatedTabs.map((tab) => (
            <MenuItem
              key={tab.id}
              value={tab.id}
              disabled={tab.disabled}
              sx={{
                py: 2,
                px: 3,
                borderRadius: 2,
                mx: 1,
                my: 0.5,
                transition: "all 0.2s ease",
                "&:hover": {
                  bgcolor: alpha(theme.palette[tab.color].main, 0.08),
                },
                "&.Mui-selected": {
                  bgcolor: alpha(theme.palette[tab.color].main, 0.12),
                  "&:hover": {
                    bgcolor: alpha(theme.palette[tab.color].main, 0.16),
                  },
                },
                "&.Mui-disabled": {
                  opacity: 0.5,
                },
              }}
            >
              <TabLabel
                tab={tab}
                isActive={tab.id === activeTab}
                showDescription={!isSmallMobile}
                compact={isSmallMobile}
              />
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Paper>
  );

  // Desktop Tabs with enhanced animations
  const DesktopTabs = () => (
    <Box
      sx={{
        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        mb: 2,
        position: "relative",
        "&::before": {
          content: '""',
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 1,
          background: `linear-gradient(90deg, 
            transparent 0%, 
            ${alpha(theme.palette.divider, 0.3)} 50%, 
            transparent 100%
          )`,
        },
      }}
    >
      {loading ? (
        <Stack direction="row" spacing={2} sx={{ p: 2 }}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Stack key={i} alignItems="center" spacing={1} sx={{ flex: 1 }}>
              <Skeleton variant="circular" width={36} height={36} />
              <Skeleton variant="text" width={60} height={20} />
            </Stack>
          ))}
        </Stack>
      ) : (
        <Tabs
          value={activeTabIndex >= 0 ? activeTabIndex : 0}
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{
            "& .MuiTabs-indicator": {
              height: 3,
              borderRadius: "3px 3px 0 0",
              background: activeTabData
                ? `linear-gradient(135deg, ${
                    theme.palette[activeTabData.color].main
                  } 0%, ${theme.palette[activeTabData.color].light} 100%)`
                : `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
              boxShadow: activeTabData
                ? `0 2px 8px ${alpha(
                    theme.palette[activeTabData.color].main,
                    0.3
                  )}`
                : `0 2px 8px ${alpha(theme.palette.primary.main, 0.3)}`,
              transition: "all 0.3s ease",
            },
            "& .MuiTab-root": {
              minHeight: 80,
              textTransform: "none",
              fontWeight: 500,
              fontSize: "0.875rem",
              color: "text.secondary",
              transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              borderRadius: "12px 12px 0 0",
              position: "relative",
              "&:hover": {
                color: "text.primary",
                transform: "translateY(-2px)",
                bgcolor: alpha(theme.palette.primary.main, 0.04),
                "&::before": {
                  opacity: 1,
                },
              },
              "&.Mui-selected": {
                color: "primary.main",
                fontWeight: 700,
                bgcolor: alpha(theme.palette.primary.main, 0.08),
              },
              "&.Mui-disabled": {
                opacity: 0.3,
                cursor: "not-allowed",
              },
              "&::before": {
                content: '""',
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 2,
                background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                opacity: 0,
                transition: "opacity 0.3s ease",
              },
            },
          }}
        >
          {updatedTabs.map((tab, index) => (
            <Tab
              key={tab.id}
              disabled={tab.disabled}
              label={
                <Tooltip
                  title={tab.disabled ? "Coming soon" : tab.description}
                  arrow
                  placement="top"
                  enterDelay={500}
                >
                  <Box sx={{ position: "relative" }}>
                    {tab.badge && tab.badge > 0 ? (
                      <Badge
                        badgeContent={tab.badge > 99 ? "99+" : tab.badge}
                        color={tab.urgent ? "error" : "primary"}
                        sx={{
                          "& .MuiBadge-badge": {
                            top: -8,
                            right: -12,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            animation: tab.urgent
                              ? "pulse 2s infinite"
                              : "none",
                          },
                        }}
                      >
                        <TabLabel
                          tab={tab}
                          isActive={activeTabIndex === index}
                        />
                      </Badge>
                    ) : (
                      <TabLabel tab={tab} isActive={activeTabIndex === index} />
                    )}
                  </Box>
                </Tooltip>
              }
              sx={{
                "&:hover .MuiAvatar-root": {
                  transform: tab.disabled ? "none" : "scale(1.1)",
                  boxShadow: tab.disabled
                    ? "none"
                    : `0 4px 12px ${alpha(theme.palette[tab.color].main, 0.3)}`,
                },
              }}
            />
          ))}
        </Tabs>
      )}
    </Box>
  );

  // Enhanced Active Tab Description Card
  const ActiveTabCard = () => {
    if (!activeTabData || loading) {
      return (
        <Skeleton
          variant="rectangular"
          height={100}
          sx={{ borderRadius: 3, mt: 3 }}
        />
      );
    }

    return (
      <Fade in={true} timeout={300}>
        <Paper
          elevation={0}
          sx={{
            mt: 3,
            p: { xs: 2.5, sm: 3 },
            borderRadius: 3,
            background: `linear-gradient(135deg, 
              ${alpha(theme.palette[activeTabData.color].main, 0.02)} 0%, 
              ${alpha(theme.palette[activeTabData.color].main, 0.08)} 100%
            )`,
            border: `1px solid ${alpha(
              theme.palette[activeTabData.color].main,
              activeTabData.urgent ? 0.25 : 0.15
            )}`,
            position: "relative",
            overflow: "hidden",
            transition: "all 0.3s ease",
            "&::before": {
              content: '""',
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 3,
              background: `linear-gradient(90deg, ${
                theme.palette[activeTabData.color].main
              }, ${theme.palette[activeTabData.color].light})`,
            },
            "&:hover": {
              transform: "translateY(-2px)",
              boxShadow: `0 8px 24px ${alpha(
                theme.palette[activeTabData.color].main,
                0.15
              )}`,
            },
          }}
        >
          <Stack direction="row" alignItems="flex-start" spacing={2}>
            <Avatar
              sx={{
                bgcolor: alpha(theme.palette[activeTabData.color].main, 0.15),
                color: `${activeTabData.color}.main`,
                width: { xs: 40, sm: 48 },
                height: { xs: 40, sm: 48 },
                flexShrink: 0,
              }}
            >
              <activeTabData.icon sx={{ fontSize: { xs: 20, sm: 24 } }} />
            </Avatar>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                alignItems={{ xs: "flex-start", sm: "center" }}
                justifyContent="space-between"
                spacing={1}
              >
                <Box>
                  <Stack
                    direction="row"
                    alignItems="center"
                    spacing={1}
                    flexWrap="wrap"
                  >
                    <Typography
                      variant="h6"
                      fontWeight={700}
                      sx={{
                        color: `${activeTabData.color}.main`,
                        fontSize: { xs: "1rem", sm: "1.25rem" },
                      }}
                    >
                      {activeTabData.label}
                    </Typography>

                    {activeTabData.badge && activeTabData.badge > 0 && (
                      <Chip
                        label={
                          activeTabData.id === "notifications"
                            ? `${activeTabData.badge} unread`
                            : activeTabData.id === "security"
                            ? `${activeTabData.badge} alert${
                                activeTabData.badge !== 1 ? "s" : ""
                              }`
                            : activeTabData.id === "brokers"
                            ? `${activeTabData.badge} connected`
                            : `${activeTabData.badge} item${
                                activeTabData.badge !== 1 ? "s" : ""
                              }`
                        }
                        size="small"
                        color={
                          activeTabData.urgent ? "error" : activeTabData.color
                        }
                        sx={{
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          height: 22,
                        }}
                      />
                    )}

                    {activeTabData.urgent && (
                      <Chip
                        label="Needs Attention"
                        size="small"
                        color="error"
                        icon={<WarningIcon sx={{ fontSize: 14 }} />}
                        sx={{
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          height: 22,
                          animation: "pulse 2s infinite",
                        }}
                      />
                    )}
                  </Stack>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      mt: 0.5,
                      fontSize: { xs: "0.8rem", sm: "0.875rem" },
                      opacity: 0.8,
                      lineHeight: 1.4,
                    }}
                  >
                    {activeTabData.description}
                  </Typography>
                </Box>

                {/* Additional actions could go here */}
                <Stack direction="row" spacing={1}>
                  {activeTabData.urgent && (
                    <Tooltip title="This section requires your attention">
                      <IconButton
                        size="small"
                        sx={{
                          color: "error.main",
                          bgcolor: alpha(theme.palette.error.main, 0.1),
                          "&:hover": {
                            bgcolor: alpha(theme.palette.error.main, 0.2),
                          },
                        }}
                      >
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </Stack>
              </Stack>
            </Box>
          </Stack>
        </Paper>
      </Fade>
    );
  };

  return (
    <Box sx={{ width: "100%" }}>
      {/* Render appropriate tab interface */}
      {isMobile ? <MobileTabSelector /> : <DesktopTabs />}

      {/* Active Tab Description Card */}
      <ActiveTabCard />

      {/* Global style for animations */}
      <style jsx global>{`
        @keyframes pulse {
          0% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.1);
          }
          100% {
            transform: scale(1);
          }
        }
      `}</style>
    </Box>
  );
};

export default ProfileTabs;
