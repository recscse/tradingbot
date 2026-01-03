import React, { useState, useEffect } from "react";
import {
  Modal,
  Button,
  CircularProgress,
  Fade,
  Backdrop,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import brokerAPI from "../../services/brokerAPI";
import { useMarket } from "../../context/MarketProvider";

const BASE_URL = process.env.REACT_APP_API_URL;
const brokers = ["Zerodha", "Upstox", "Dhan", "Angel One", "Fyers"];
const fields = {
  Dhan: ["client_id", "access_token"],
  Zerodha: ["api_key", "api_secret", "request_token"],
  Upstox: ["api_key", "api_secret"],
  "Angel One": ["api_key", "api_secret"],
  Fyers: ["client_id", "secret_key"],
};

const BrokerConfigModal = ({
  open,
  onClose,
  refreshBrokers,
  existingBrokers,
}) => {
  // const theme = useTheme(); // Unused
  // const isDark = theme.palette.mode === "dark"; // Unused
  const [broker, setBroker] = useState({ broker_name: "", credentials: {} });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Get resetTokenExpired from context
  const { resetTokenExpired } = useMarket();

  useEffect(() => {
    setError(""); // Clear errors when modal opens
    if (!open) {
      setBroker({ broker_name: "", credentials: {} }); // Reset form on close
    }
  }, [open]);

  const handleChange = (field, value) => {
    setBroker((prev) => ({
      ...prev,
      credentials: { ...prev.credentials, [field]: value.trim() },
    }));
  };

  const isDuplicate = () => {
    return existingBrokers.some((existing) => {
      if (existing.broker_name !== broker.broker_name) return false;
      const requiredFields = fields[broker.broker_name] || [];
      const existingCredentials = existing.config || existing.credentials || {};
      return requiredFields.every(
        (field) =>
          existingCredentials[field]?.trim() ===
          broker.credentials[field]?.trim()
      );
    });
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError("");

    if (!broker.broker_name) {
      setError("Please select a broker.");
      setLoading(false);
      return;
    }

    const requiredFields = fields[broker.broker_name] || [];
    const missingFields = requiredFields.filter(
      (field) => !broker.credentials[field]
    );

    if (missingFields.length > 0) {
      setError(`Missing required fields: ${missingFields.join(", ")}`);
      setLoading(false);
      return;
    }

    if (isDuplicate()) {
      setError("This broker account already exists.");
      setLoading(false);
      return;
    }

    //  Special handling for Upstox
    if (broker.broker_name === "Upstox") {
      try {
        const response = await brokerAPI.initUpstoxAuth({
          api_key: broker.credentials.api_key,
          api_secret: broker.credentials.api_secret,
          redirect_uri: `${BASE_URL}/api/broker/upstox/callback`,
        });

        const authUrl = response?.auth_url;
        if (authUrl) {
          if (resetTokenExpired) resetTokenExpired();
          window.open(authUrl, "_blank");
          onClose();
          return;
        }
        setError("Failed to retrieve auth URL.");
      } catch (error) {
        console.error(error);
        setError(error.response?.data?.detail || "Upstox auth failed");
      } finally {
        setLoading(false);
      }
      return;
    }

    if (broker.broker_name === "Fyers") {
      try {
        const response = await brokerAPI.initFyersAuth({
          broker: "Fyers",
          config: {
            client_id: broker.credentials.client_id,
            secret_key: broker.credentials.secret_key,
            redirect_uri: `${BASE_URL}/api/broker/fyers/callback`,
          },
        });

        const authUrl = response?.auth_url;
        if (authUrl) {
          if (resetTokenExpired) resetTokenExpired();
          window.open(authUrl, "_blank");
          onClose();
          return;
        }
        setError("Failed to retrieve Fyers auth URL.");
      } catch (error) {
        console.error(error);
        const err = error.response?.data;
        setError(
          Array.isArray(err?.detail)
            ? err.detail
            : err?.detail || "Fyers auth failed"
        );
      } finally {
        setLoading(false);
      }
      return;
    }

    if (broker.broker_name === "Angel One") {
      try {
        const response = await brokerAPI.initAngelAuth({
          broker: "Angel One",
          config: {
            api_key: broker.credentials.api_key,
            api_secret: broker.credentials.api_secret,
            redirect_uri: `${BASE_URL}/api/broker/angel/callback`,
          },
        });

        const authUrl = response?.auth_url;
        if (authUrl) {
          if (resetTokenExpired) resetTokenExpired();
          window.open(authUrl, "_blank");
          onClose();
          return;
        }
        setError("Failed to retrieve Angel One auth URL.");
      } catch (error) {
        console.error(error);
        setError(error.response?.data?.detail || "Angel One auth failed");
      } finally {
        setLoading(false);
      }
      return;
    }

    try {
      await brokerAPI.addBroker(broker);
      if (resetTokenExpired) resetTokenExpired();
      refreshBrokers();
      onClose();
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to add broker");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      closeAfterTransition
      BackdropComponent={Backdrop}
      BackdropProps={{
        timeout: 500,
        className: "!tw-bg-slate-900/80 !tw-backdrop-blur-sm",
      }}
    >
      <Fade in={open}>
        <div className="tw-absolute tw-top-1/2 tw-left-1/2 tw-transform tw--translate-x-1/2 tw--translate-y-1/2 tw-w-full tw-max-w-md tw-p-4 tw-outline-none">
          <div className="tw-bg-slate-800 tw-border tw-border-slate-700 tw-rounded-2xl tw-shadow-2xl tw-overflow-hidden">
            {/* Header */}
            <div className="tw-flex tw-justify-between tw-items-center tw-p-5 tw-border-b tw-border-slate-700 tw-bg-slate-800/50">
              <h2 className="tw-text-xl tw-font-bold tw-text-slate-100">
                Connect Broker
              </h2>
              <button
                onClick={onClose}
                className="tw-text-slate-400 hover:tw-text-white tw-transition-colors tw-rounded-full tw-p-1 hover:tw-bg-slate-700"
              >
                <Close />
              </button>
            </div>

            {/* Content */}
            <div className="tw-p-6 tw-space-y-5">
              <div className="tw-space-y-2">
                <label className="tw-text-sm tw-font-medium tw-text-slate-300">
                  Select Broker
                </label>
                <div className="tw-relative">
                  <select
                    value={broker.broker_name}
                    onChange={(e) =>
                      setBroker({
                        broker_name: e.target.value,
                        credentials: {},
                      })
                    }
                    className="tw-w-full tw-bg-slate-900 tw-border tw-border-slate-700 tw-rounded-lg tw-px-4 tw-py-3 tw-text-slate-200 focus:tw-outline-none focus:tw-ring-2 focus:tw-ring-blue-500/50 focus:tw-border-blue-500 tw-transition-all tw-appearance-none tw-cursor-pointer"
                  >
                    <option value="" disabled>
                      Choose a provider
                    </option>
                    {brokers.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                  <div className="tw-absolute tw-inset-y-0 tw-right-0 tw-flex tw-items-center tw-px-2 tw-pointer-events-none">
                    <svg
                      className="tw-w-4 tw-h-4 tw-text-slate-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M19 9l-7 7-7-7"
                      ></path>
                    </svg>
                  </div>
                </div>
              </div>

              {broker.broker_name && (
                <div className="tw-space-y-4 tw-animate-in tw-fade-in tw-slide-in-from-top-2 tw-duration-300">
                  {fields[broker.broker_name]?.map((field) => (
                    <div key={field} className="tw-space-y-2">
                      <label className="tw-text-sm tw-font-medium tw-text-slate-300 tw-capitalize">
                        {field.replace(/_/g, " ")}
                      </label>
                      <input
                        type="text"
                        onChange={(e) => handleChange(field, e.target.value)}
                        className="tw-w-full tw-bg-slate-900 tw-border tw-border-slate-700 tw-rounded-lg tw-px-4 tw-py-3 tw-text-slate-200 focus:tw-outline-none focus:tw-ring-2 focus:tw-ring-blue-500/50 focus:tw-border-blue-500 tw-transition-all placeholder:tw-text-slate-600"
                        placeholder={`Enter ${field.replace(/_/g, " ")}`}
                      />
                    </div>
                  ))}
                </div>
              )}

              {error && (
                <div className="tw-bg-red-500/10 tw-border tw-border-red-500/20 tw-text-red-400 tw-text-sm tw-p-3 tw-rounded-lg tw-flex tw-items-center tw-gap-2">
                  <span className="tw-w-1.5 tw-h-1.5 tw-rounded-full tw-bg-red-500" />
                  {error}
                </div>
              )}

              <Button
                variant="contained"
                fullWidth
                onClick={handleSubmit}
                disabled={loading}
                className="!tw-bg-blue-600 hover:!tw-bg-blue-700 !tw-text-white !tw-py-3 !tw-rounded-lg !tw-font-bold !tw-shadow-lg !tw-shadow-blue-900/20 disabled:!tw-opacity-50 disabled:!tw-cursor-not-allowed !tw-mt-2 !tw-normal-case"
              >
                {loading ? (
                  <CircularProgress size={24} className="!tw-text-white/80" />
                ) : (
                  "Connect Account"
                )}
              </Button>
            </div>
          </div>
        </div>
      </Fade>
    </Modal>
  );
};

export default BrokerConfigModal;
