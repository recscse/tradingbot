// src/components/profile/EnhancedBrokerManagement.jsx
import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Grid,
  Tabs,
  Tab,
  Alert,
  Snackbar,
  useTheme,
  alpha,
  Paper,
  Divider,
} from "@mui/material";
import {
  Business as BusinessIcon,
  AccountBalance as FundsIcon,
  Assessment as StatsIcon,
} from "@mui/icons-material";
import BrokerManagement from "./BrokerManagement";
import BrokerProfileCard from "./BrokerProfileCard";
import CombinedFundsSummary from "./CombinedFundsSummary";
import { brokerService } from "../../services/brokerService";
import brokerProfileService from "../../services/brokerProfileService";

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`broker-tabpanel-${index}`}
      aria-labelledby={`broker-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const EnhancedBrokerManagement = () => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [brokers, setBrokers] = useState([]);
  const [supportedBrokers, setSupportedBrokers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  const showSnackbar = useCallback((message, severity = "success") => {
    setSnackbar({ open: true, message, severity });
  }, []);

  const fetchBrokers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await brokerService.getBrokers();
      if (response.data) {
        setBrokers(response.data.brokers || []);
      }
    } catch (error) {
      console.error("Failed to fetch brokers:", error);
      setError("Failed to load broker configurations");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSupportedBrokers = useCallback(async () => {
    try {
      const response = await brokerProfileService.getSupportedBrokers();
      setSupportedBrokers(response);
    } catch (error) {
      console.error("Failed to fetch supported brokers:", error);
    }
  }, []);

  useEffect(() => {
    fetchBrokers();
    fetchSupportedBrokers();
  }, [fetchBrokers, fetchSupportedBrokers]);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const getActiveBrokers = () => {
    return brokers.filter(broker => broker.is_active);
  };

  const getSupportedActiveBrokers = () => {
    const activeBrokers = getActiveBrokers();
    if (!supportedBrokers) return [];
    
    return activeBrokers.filter(broker => 
      supportedBrokers.supported_brokers[broker.broker_name.toLowerCase()]?.profile_supported
    );
  };

  const tabs = [
    { 
      label: "Broker Setup", 
      icon: <BusinessIcon />,
      description: "Configure and manage broker accounts"
    },
    { 
      label: "Profiles & Funds", 
      icon: <FundsIcon />,
      description: "View broker profiles and fund details"
    },
    { 
      label: "Summary", 
      icon: <StatsIcon />,
      description: "Combined funds summary across all brokers"
    }
  ];

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight={600} gutterBottom>
          🏦 Broker Management
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Manage your broker accounts, view profiles, and monitor funds across all platforms
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Tabs */}
      <Paper elevation={1} sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{
            '& .MuiTab-root': {
              minHeight: 72,
              textTransform: 'none',
            }
          }}
        >
          {tabs.map((tab, index) => (
            <Tab
              key={index}
              icon={tab.icon}
              label={
                <Box textAlign="center">
                  <Typography variant="subtitle2" fontWeight={600}>
                    {tab.label}
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    {tab.description}
                  </Typography>
                </Box>
              }
              iconPosition="top"
            />
          ))}
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <TabPanel value={activeTab} index={0}>
        {/* Existing Broker Management */}
        <BrokerManagement />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        {/* Broker Profiles & Funds */}
        <Box>
          {loading ? (
            <Typography>Loading broker profiles...</Typography>
          ) : getSupportedActiveBrokers().length === 0 ? (
            <Alert severity="info">
              <Typography variant="body2">
                No active brokers found with profile support. Please configure your brokers in the "Broker Setup" tab first.
              </Typography>
            </Alert>
          ) : (
            <Grid container spacing={3}>
              {getSupportedActiveBrokers().map((broker) => (
                <Grid item xs={12} lg={6} key={broker.id}>
                  <BrokerProfileCard
                    brokerName={broker.broker_name}
                    onError={(message) => showSnackbar(message, "error")}
                  />
                </Grid>
              ))}
            </Grid>
          )}

          {supportedBrokers && (
            <Box sx={{ mt: 4 }}>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                📋 Supported Brokers
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(supportedBrokers.supported_brokers).map(([brokerName, brokerInfo]) => (
                  <Grid item xs={12} sm={6} md={4} key={brokerName}>
                    <Paper
                      elevation={1}
                      sx={{
                        p: 2,
                        border: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
                        borderRadius: 2
                      }}
                    >
                      <Box display="flex" alignItems="center" mb={1}>
                        <Typography 
                          variant="subtitle2" 
                          fontWeight={600}
                          sx={{ textTransform: 'capitalize' }}
                        >
                          {brokerInfo.name}
                        </Typography>
                        {brokerInfo.profile_supported && (
                          <Typography variant="caption" color="success.main" sx={{ ml: 1 }}>
                            ✅
                          </Typography>
                        )}
                      </Box>
                      <Typography variant="caption" color="textSecondary">
                        Status: {brokerInfo.status || "Available"}
                      </Typography>
                      <Box mt={1}>
                        {brokerInfo.features.map((feature, index) => (
                          <Typography key={index} variant="caption" display="block" color="textSecondary">
                            • {feature}
                          </Typography>
                        ))}
                      </Box>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}
        </Box>
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        {/* Combined Summary */}
        <Box>
          {loading ? (
            <Typography>Loading funds summary...</Typography>
          ) : getActiveBrokers().length === 0 ? (
            <Alert severity="info">
              <Typography variant="body2">
                No active brokers found. Please configure your brokers first to view the combined funds summary.
              </Typography>
            </Alert>
          ) : (
            <CombinedFundsSummary
              onError={(message) => showSnackbar(message, "error")}
            />
          )}
        </Box>
      </TabPanel>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default EnhancedBrokerManagement;