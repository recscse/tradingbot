import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMarket } from "../context/MarketProvider";
import brokerAPI from "../services/brokerAPI";
import {
  Button,
  CircularProgress,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import {
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  Security as SecurityIcon,
  AccessTime as AccessTimeIcon,
  Error as ErrorIcon,
  ArrowBack as ArrowBackIcon,
} from "@mui/icons-material";
import { motion, AnimatePresence } from "framer-motion";
import BrokerConfigModal from "../components/settings/BrokerConfigModal";

const BrokerConfigPage = () => {
  // const theme = useTheme(); // Unused
  // const isMobile = useMediaQuery(theme.breakpoints.down("sm")); // Unused
  const [brokers, setBrokers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState("");
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedBrokerId, setSelectedBrokerId] = useState(null);

  const navigate = useNavigate();
  const marketContext = useMarket();
  const resetTokenExpired = marketContext?.resetTokenExpired;

  useEffect(() => {
    fetchBrokers();
  }, []);

  const navigateToDashboard = () => {
    sessionStorage.setItem("returningFromConfig", "true");
    navigate("/");
  };

  const fetchBrokers = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await brokerAPI.getBrokers();
      setBrokers(data.brokers || []);
    } catch (error) {
      console.error("❌ Failed to load brokers:", error);
      setError("Failed to load brokers. Please try again.");
    } finally {
      setLoading(false);
    }
  };

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

  const refreshToken = async (brokerId) => {
    setLoading(true);
    try {
      const res = await brokerAPI.refreshBrokerToken(brokerId);
      if (res.auth_url) {
        if (resetTokenExpired && typeof resetTokenExpired === "function") {
          resetTokenExpired();
        }
        window.open(res.auth_url, "_blank");
      }
    } catch (error) {
      console.error("❌ Failed to refresh token:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleMenuOpen = (event, brokerId) => {
    setAnchorEl(event.currentTarget);
    setSelectedBrokerId(brokerId);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedBrokerId(null);
  };

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { type: "spring", stiffness: 300, damping: 24 },
    },
  };

  return (
    <div className="tw-min-h-screen tw-bg-slate-900 tw-text-slate-100 tw-p-4 md:tw-p-8 tw-pb-24 md:tw-pb-8">
      {/* Header Section */}
      <div className="tw-max-w-7xl tw-mx-auto tw-mb-8 tw-flex tw-flex-col md:tw-flex-row tw-justify-between tw-items-start md:tw-items-center tw-gap-4">
        <div>
          <h1 className="tw-text-2xl md:tw-text-3xl tw-font-bold tw-bg-gradient-to-r tw-from-blue-400 tw-to-violet-400 tw-bg-clip-text tw-text-transparent tw-flex tw-items-center tw-gap-2">
            <SecurityIcon className="tw-text-blue-400" /> Broker Configuration
          </h1>
          <p className="tw-text-slate-400 tw-mt-1 tw-text-sm md:tw-text-base">
            Manage your trading accounts and API connections
          </p>
        </div>
        <div className="tw-flex tw-gap-3 tw-w-full md:tw-w-auto">
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={navigateToDashboard}
            className="!tw-border-slate-600 !tw-text-slate-300 hover:!tw-bg-slate-800 tw-flex-1 md:tw-flex-none"
          >
            Back
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setModalOpen(true)}
            className="!tw-bg-gradient-to-r !tw-from-blue-600 !tw-to-blue-500 hover:!tw-from-blue-700 hover:!tw-to-blue-600 !tw-shadow-lg !tw-shadow-blue-900/20 tw-flex-1 md:tw-flex-none"
          >
            Add Broker
          </Button>
        </div>
      </div>

      {/* Content Section */}
      <div className="tw-max-w-7xl tw-mx-auto">
        {loading ? (
          <div className="tw-flex tw-flex-col tw-items-center tw-justify-center tw-h-64">
            <CircularProgress size={40} className="!tw-text-blue-500" />
            <p className="tw-mt-4 tw-text-slate-400 tw-animate-pulse">
              Loading configurations...
            </p>
          </div>
        ) : error ? (
          <div className="tw-bg-red-500/10 tw-border tw-border-red-500/20 tw-rounded-xl tw-p-6 tw-text-center">
            <ErrorIcon className="tw-text-red-500 tw-text-4xl tw-mb-2" />
            <p className="tw-text-red-400 tw-font-medium">{error}</p>
            <Button
              variant="text"
              onClick={fetchBrokers}
              className="tw-mt-2 !tw-text-red-400 hover:!tw-bg-red-500/10"
            >
              Try Again
            </Button>
          </div>
        ) : brokers.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="tw-bg-slate-800/50 tw-border tw-border-slate-700 tw-rounded-2xl tw-p-12 tw-text-center tw-max-w-lg tw-mx-auto tw-mt-12"
          >
            <div className="tw-w-20 tw-h-20 tw-bg-slate-700/50 tw-rounded-full tw-flex tw-items-center tw-justify-center tw-mx-auto tw-mb-6">
              <SecurityIcon className="tw-text-slate-500 tw-text-4xl" />
            </div>
            <h3 className="tw-text-xl tw-font-bold tw-text-slate-200 tw-mb-2">
              No Brokers Configured
            </h3>
            <p className="tw-text-slate-400 tw-mb-8">
              Connect your trading account to start using the automated features.
            </p>
            <Button
              variant="contained"
              size="large"
              startIcon={<AddIcon />}
              onClick={() => setModalOpen(true)}
              className="!tw-bg-blue-600 hover:!tw-bg-blue-700 !tw-rounded-xl !tw-py-3 !tw-px-8"
            >
              Add Your First Broker
            </Button>
          </motion.div>
        ) : (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="tw-grid tw-grid-cols-1 md:tw-grid-cols-2 lg:tw-grid-cols-3 tw-gap-4 md:tw-gap-6"
          >
            <AnimatePresence>
              {brokers.map((broker) => (
                <motion.div
                  key={broker.id}
                  variants={itemVariants}
                  layout
                  className="tw-bg-slate-800 tw-border tw-border-slate-700/50 tw-rounded-xl tw-overflow-hidden hover:tw-border-blue-500/30 hover:tw-shadow-xl hover:tw-shadow-blue-900/10 tw-transition-all tw-duration-300 group"
                >
                  {/* Card Header */}
                  <div className="tw-p-5 tw-border-b tw-border-slate-700/50 tw-flex tw-justify-between tw-items-start tw-bg-slate-800/50">
                    <div className="tw-flex tw-items-center tw-gap-3">
                      <div className="tw-w-10 tw-h-10 tw-rounded-lg tw-bg-gradient-to-br tw-from-slate-700 tw-to-slate-600 tw-flex tw-items-center tw-justify-center tw-text-lg tw-font-bold tw-text-white tw-shadow-inner">
                        {broker.broker_name?.[0] || "?"}
                      </div>
                      <div>
                        <h3 className="tw-font-bold tw-text-lg tw-text-slate-100 tw-leading-tight">
                          {broker.broker_name || "Unknown Broker"}
                        </h3>
                        <div className="tw-flex tw-items-center tw-gap-1.5 tw-mt-1">
                          <span
                            className={`tw-w-2 tw-h-2 tw-rounded-full ${
                              broker.is_active
                                ? "tw-bg-emerald-500 tw-shadow-[0_0_8px_rgba(16,185,129,0.4)]"
                                : "tw-bg-red-500"
                            }`}
                          />
                          <span
                            className={`tw-text-xs tw-font-medium ${
                              broker.is_active
                                ? "tw-text-emerald-400"
                                : "tw-text-red-400"
                            }`}
                          >
                            {broker.is_active ? "Active" : "Inactive"}
                          </span>
                        </div>
                      </div>
                    </div>
                    <IconButton
                      onClick={(e) => handleMenuOpen(e, broker.id)}
                      className="!tw-text-slate-400 hover:!tw-text-white hover:!tw-bg-slate-700"
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </div>

                  {/* Card Body */}
                  <div className="tw-p-5 tw-space-y-4">
                    <div className="tw-bg-slate-900/50 tw-rounded-lg tw-p-3 tw-border tw-border-slate-700/30">
                      <p className="tw-text-xs tw-text-slate-500 tw-uppercase tw-font-semibold tw-mb-1">
                        Client ID
                      </p>
                      <p className="tw-font-mono tw-text-slate-200 tw-text-sm tw-truncate">
                        {broker.client_id || "N/A"}
                      </p>
                    </div>

                    <div className="tw-flex tw-items-center tw-justify-between tw-text-sm">
                      <div className="tw-flex tw-items-center tw-gap-2 tw-text-slate-400">
                        <AccessTimeIcon fontSize="small" />
                        <span>Token Expiry</span>
                      </div>
                      <span className="tw-text-slate-300 tw-font-medium tw-text-xs tw-bg-slate-700/50 tw-px-2 tw-py-1 tw-rounded">
                        {broker.access_token_expiry
                          ? new Date(broker.access_token_expiry).toLocaleDateString()
                          : "N/A"}
                      </span>
                    </div>
                  </div>

                  {/* Card Footer - Actions */}
                  <div className="tw-p-3 tw-bg-slate-900/30 tw-border-t tw-border-slate-700/50 tw-flex tw-gap-2">
                    <Button
                      fullWidth
                      variant="outlined"
                      size="small"
                      startIcon={<RefreshIcon />}
                      onClick={() => refreshToken(broker.id)}
                      disabled={!broker.access_token}
                      className="!tw-border-slate-700 !tw-text-slate-300 hover:!tw-bg-slate-800 hover:!tw-border-slate-600 hover:!tw-text-white"
                    >
                      Refresh
                    </Button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          className: "!tw-bg-slate-800 !tw-border !tw-border-slate-700 !tw-text-slate-200 !tw-rounded-xl !tw-shadow-xl",
        }}
      >
        <MenuItem onClick={handleMenuClose} className="hover:!tw-bg-slate-700/50">
          <ListItemIcon>
            <EditIcon fontSize="small" className="tw-text-blue-400" />
          </ListItemIcon>
          <ListItemText>Edit Configuration</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleMenuClose();
            deleteBroker(selectedBrokerId);
          }}
          className="hover:!tw-bg-red-500/10 !tw-text-red-400"
        >
          <ListItemIcon>
            <DeleteIcon fontSize="small" className="tw-text-red-400" />
          </ListItemIcon>
          <ListItemText>Remove Broker</ListItemText>
        </MenuItem>
      </Menu>

      {/* Broker Config Modal */}
      <BrokerConfigModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        refreshBrokers={fetchBrokers}
        existingBrokers={brokers}
        resetTokenExpired={resetTokenExpired}
      />
    </div>
  );
};

export default BrokerConfigPage;
