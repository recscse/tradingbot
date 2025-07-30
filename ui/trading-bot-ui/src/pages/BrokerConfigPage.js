import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMarket } from "../context/MarketProvider";
import brokerAPI from "../services/brokerAPI";
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Tooltip,
  IconButton,
} from "@mui/material";
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import BrokerConfigModal from "../components/settings/BrokerConfigModal";

const BrokerConfigPage = () => {
  const [brokers, setBrokers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();
  const marketContext = useMarket();

  // Add safety check for resetTokenExpired function
  const resetTokenExpired = marketContext?.resetTokenExpired;

  // Set the flag when we're in the config page
  useEffect(() => {
    console.log("🔧 Config page mounted");
    // We do NOT call resetTokenExpired here - only when a successful operation happens
  }, []);

  // Handle navigation back to dashboard
  const navigateToDashboard = () => {
    console.log("🏠 Navigating back to dashboard");
    sessionStorage.setItem("returningFromConfig", "true");
    navigate("/");
  };

  // ✅ Fetch Brokers from API
  const fetchBrokers = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await brokerAPI.getBrokers();
      console.log("📌 Broker API Response:", data);
      setBrokers(data.brokers || []);
    } catch (error) {
      console.error("❌ Failed to load brokers:", error);
      setError("Failed to load brokers. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBrokers();
  }, []);

  // ✅ Delete Broker Function
  const deleteBroker = async (brokerId) => {
    if (!window.confirm("Are you sure you want to remove this broker?")) return;

    setLoading(true);
    try {
      await brokerAPI.deleteBroker(brokerId);
      fetchBrokers();
    } catch (error) {
      console.error("❌ Failed to delete broker:", error);
    } finally {
      setLoading(false);
    }
  };

  // ✅ Handle Refresh Token Action
  const refreshToken = async (brokerId) => {
    setLoading(true);
    try {
      const res = await brokerAPI.refreshBrokerToken(brokerId);
      if (res.auth_url) {
        // Only reset token expired when successful AND function exists
        if (resetTokenExpired && typeof resetTokenExpired === "function") {
          resetTokenExpired();
          console.log(
            "✅ Token refreshed successfully, token expired state reset"
          );
        } else {
          console.warn("⚠️ resetTokenExpired function not available");
        }
        window.open(res.auth_url, "_blank");
      } else {
        console.warn("No auth URL returned.");
      }
    } catch (error) {
      console.error("❌ Failed to refresh token:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={3}>
      {/* ✅ Header with "Add Broker" Button */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
      >
        <Box display="flex" alignItems="center">
          <Typography variant="h5">Broker Configurations</Typography>
          <Button
            variant="outlined"
            onClick={navigateToDashboard}
            sx={{ ml: 2 }}
          >
            Back to Dashboard
          </Button>
        </Box>
        <Button variant="contained" onClick={() => setModalOpen(true)}>
          Add Broker
        </Button>
      </Box>

      {/* ✅ Loading Indicator */}
      {loading ? (
        <CircularProgress sx={{ display: "block", margin: "20px auto" }} />
      ) : error ? (
        <Typography color="error" sx={{ textAlign: "center", p: 2 }}>
          {error}
        </Typography>
      ) : brokers.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <strong>Broker</strong>
                </TableCell>
                <TableCell>
                  <strong>Client ID</strong>
                </TableCell>
                <TableCell>
                  <strong>API Key</strong>
                </TableCell>
                <TableCell>
                  <strong>Status</strong>
                </TableCell>
                <TableCell>
                  <strong>Expiry</strong>
                </TableCell>
                <TableCell align="right">
                  <strong>Actions</strong>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {brokers.map((broker) => (
                <TableRow key={broker.id}>
                  <TableCell>{broker.broker_name || "N/A"}</TableCell>
                  <TableCell>{broker.client_id || "N/A"}</TableCell>
                  <TableCell>{broker.api_key ? "****" : "N/A"}</TableCell>
                  <TableCell>
                    <Chip
                      label={broker.is_active ? "Active" : "Inactive"}
                      color={broker.is_active ? "success" : "error"}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {broker.access_token_expiry
                      ? new Date(broker.access_token_expiry).toLocaleString()
                      : "N/A"}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit Broker">
                      <IconButton edge="end" color="primary">
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Refresh Token">
                      <IconButton
                        edge="end"
                        color="warning"
                        onClick={() => refreshToken(broker.id)}
                        disabled={!broker.access_token}
                      >
                        <RefreshIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Broker">
                      <IconButton
                        edge="end"
                        color="error"
                        onClick={() => deleteBroker(broker.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography color="text.secondary" align="center">
          No brokers added. Click "Add Broker" to start.
        </Typography>
      )}

      {/* ✅ Add Broker Popup Modal */}
      <BrokerConfigModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        refreshBrokers={fetchBrokers}
        existingBrokers={brokers}
        resetTokenExpired={resetTokenExpired}
      />
    </Box>
  );
};

export default BrokerConfigPage;
