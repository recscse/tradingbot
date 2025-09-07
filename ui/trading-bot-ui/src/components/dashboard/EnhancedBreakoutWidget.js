// components/dashboard/EnhancedBreakoutWidget.js
import React, { useState, useEffect, useMemo } from "react";
import {
  Paper,
  Box,
  Grid2,
  Chip,
  Tooltip,
  Typography,
  Divider,
  LinearProgress,
  Badge,
  IconButton,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  ShowChart,
  Refresh,
} from "@mui/icons-material";
import { bloombergColors } from "../../themes/bloombergColors";
import { withErrorBoundary } from "../common/ErrorBoundary";

const EnhancedBreakoutWidget = ({
  data,
  isLoading,
  compact = false,
  onRefresh,
  realTimeEnabled = true,
}) => {
  // State for filters and display options
  const [selectedType, setSelectedType] = useState("all");
  const [selectedStrength, setSelectedStrength] = useState("all");
  const [showMetrics, setShowMetrics] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Update timestamp when data changes
  useEffect(() => {
    if (data && !isLoading) {
      setLastUpdate(new Date());
    }
  }, [data, isLoading]);

  // Auto-refresh timer
  useEffect(() => {
    if (autoRefresh && onRefresh) {
      const interval = setInterval(() => {
        onRefresh();
      }, 10000); // Refresh every 10 seconds

      return () => clearInterval(interval);
    }
  }, [autoRefresh, onRefresh]);

  // Enhanced breakout types with icons and colors
  const breakoutTypeConfig = {
    volume_breakout: { icon: "📊", color: "#00D4AA", label: "Volume" },
    volume_surge: { icon: "🚀", color: "#00D4AA", label: "Volume Surge" },
    momentum_breakout: { icon: "⚡", color: "#FFB020", label: "Momentum" },
    strong_momentum: { icon: "💥", color: "#FF6B3D", label: "Strong Momentum" },
    resistance_breakout: { icon: "📈", color: "#00D4AA", label: "Resistance" },
    support_breakdown: { icon: "📉", color: "#FF4081", label: "Support" },
    gap_up: { icon: "⬆️", color: "#4CAF50", label: "Gap Up" },
    gap_down: { icon: "⬇️", color: "#F44336", label: "Gap Down" },
    volatility_expansion: { icon: "🌊", color: "#9C27B0", label: "Volatility" },
    high_breakout: { icon: "🔺", color: "#2196F3", label: "High Break" },
    low_breakdown: { icon: "🔻", color: "#FF9800", label: "Low Break" },
  };

  // Process and filter breakout data
  const processedData = useMemo(() => {
    if (!data) return { breakouts: [], metrics: {}, summary: {} };

    // Handle both legacy and enhanced data formats
    const breakouts = data.breakouts || [];
    const recentBreakouts = data.recent_breakouts || [];
    const topBreakouts = data.top_breakouts || [];
    const breakoutsByType = data.breakouts_by_type || {};
    const metrics = data.engine_metrics || data.scanner_stats || {};

    // Combine all breakout data
    const allBreakouts = [...breakouts, ...recentBreakouts, ...topBreakouts];

    // Add breakouts from breakouts_by_type
    Object.entries(breakoutsByType).forEach(([type, typeBreakouts]) => {
      if (Array.isArray(typeBreakouts)) {
        allBreakouts.push(...typeBreakouts);
      }
    });

    // Remove duplicates based on instrument_key and timestamp
    const uniqueBreakouts = allBreakouts.reduce((acc, current) => {
      const key = `${current.instrument_key}_${current.timestamp}`;
      if (
        !acc.some((item) => `${item.instrument_key}_${item.timestamp}` === key)
      ) {
        acc.push(current);
      }
      return acc;
    }, []);

    // Apply filters
    const filteredBreakouts = uniqueBreakouts.filter((breakout) => {
      // Type filter
      if (selectedType !== "all") {
        if (
          selectedType === "bullish" &&
          ![
            "volume_breakout",
            "momentum_breakout",
            "resistance_breakout",
            "gap_up",
          ].includes(breakout.breakout_type)
        ) {
          return false;
        }
        if (
          selectedType === "bearish" &&
          !["support_breakdown", "gap_down", "low_breakdown"].includes(
            breakout.breakout_type
          )
        ) {
          return false;
        }
        if (
          selectedType !== "bullish" &&
          selectedType !== "bearish" &&
          breakout.breakout_type !== selectedType
        ) {
          return false;
        }
      }

      // Strength filter
      if (selectedStrength !== "all") {
        const strength = breakout.strength || 0;
        switch (selectedStrength) {
          case "weak":
            return strength < 4;
          case "moderate":
            return strength >= 4 && strength < 7;
          case "strong":
            return strength >= 7;
          default:
            return true;
        }
      }

      return true;
    });

    // Sort by timestamp (most recent first)
    filteredBreakouts.sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );

    return {
      breakouts: filteredBreakouts.slice(0, compact ? 10 : 25),
      metrics,
      summary: data.summary || {},
      totalBreakouts: data.total_breakouts_today || uniqueBreakouts.length,
    };
  }, [data, selectedType, selectedStrength, compact]);

  // Get strength color
  const getStrengthColor = (strength) => {
    if (strength >= 8) return "#4CAF50"; // Green for strong
    if (strength >= 6) return "#FF9800"; // Orange for moderate
    if (strength >= 4) return "#FFC107"; // Yellow for weak-moderate
    return "#757575"; // Grey for weak
  };

  // Get time ago string
  const getTimeAgo = (timestamp) => {
    if (!timestamp) return "Unknown";

    const now = new Date();
    const past = new Date(timestamp);
    const diffInSeconds = Math.floor((now - past) / 1000);

    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400)
      return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return past.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <Paper
        sx={{ backgroundColor: bloombergColors.cardBg, p: 2, height: "100%" }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
          <Typography
            variant="h6"
            sx={{ color: bloombergColors.primary, mb: 2 }}
          >
            Enhanced Breakout Scanner
          </Typography>
          <Box
            sx={{
              flexGrow: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Box sx={{ textAlign: "center" }}>
              <LinearProgress sx={{ mb: 2, width: 200 }} />
              <Typography sx={{ color: bloombergColors.textSecondary }}>
                Loading enhanced breakout data...
              </Typography>
            </Box>
          </Box>
        </Box>
      </Paper>
    );
  }

  const { breakouts, metrics, totalBreakouts } = processedData;

  return (
    <Paper
      sx={{ backgroundColor: bloombergColors.cardBg, p: 2, height: "100%" }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
        {/* Header with controls */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography variant="h6" sx={{ color: bloombergColors.primary }}>
              Enhanced Breakout Scanner
            </Typography>
            {realTimeEnabled && (
              <Chip
                label="LIVE"
                size="small"
                sx={{
                  backgroundColor: "#4CAF50",
                  color: "white",
                  animation: "pulse 2s infinite",
                }}
              />
            )}
            <Badge badgeContent={totalBreakouts} color="primary" max={999}>
              <TrendingUp sx={{ color: bloombergColors.primary }} />
            </Badge>
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={showMetrics}
                  onChange={(e) => setShowMetrics(e.target.checked)}
                  size="small"
                />
              }
              label="Metrics"
              sx={{ color: bloombergColors.textSecondary, fontSize: "0.75rem" }}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  size="small"
                />
              }
              label="Auto"
              sx={{ color: bloombergColors.textSecondary, fontSize: "0.75rem" }}
            />
            <IconButton
              size="small"
              onClick={onRefresh}
              sx={{ color: bloombergColors.primary }}
            >
              <Refresh />
            </IconButton>
          </Box>
        </Box>

        {/* Filters */}
        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel sx={{ color: bloombergColors.textSecondary }}>
              Type
            </InputLabel>
            <Select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              sx={{ color: bloombergColors.text }}
            >
              <MenuItem value="all">All Types</MenuItem>
              <MenuItem value="bullish">🔥 Bullish</MenuItem>
              <MenuItem value="bearish">🔻 Bearish</MenuItem>
              <MenuItem value="volume_breakout">📊 Volume</MenuItem>
              <MenuItem value="momentum_breakout">⚡ Momentum</MenuItem>
              <MenuItem value="resistance_breakout">📈 Resistance</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel sx={{ color: bloombergColors.textSecondary }}>
              Strength
            </InputLabel>
            <Select
              value={selectedStrength}
              onChange={(e) => setSelectedStrength(e.target.value)}
              sx={{ color: bloombergColors.text }}
            >
              <MenuItem value="all">All Strength</MenuItem>
              <MenuItem value="strong">💪 Strong (7+)</MenuItem>
              <MenuItem value="moderate">📊 Moderate (4-7)</MenuItem>
              <MenuItem value="weak">📉 Weak (&lt;4)</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Performance Metrics (collapsible) */}
        {showMetrics && metrics && (
          <Paper
            sx={{
              p: 1,
              mb: 2,
              backgroundColor: bloombergColors.surfaceVariant,
            }}
          >
            <Grid2 container spacing={1}>
              <Grid2 xs={6}>
                <Box sx={{ textAlign: "center" }}>
                  <Typography
                    variant="caption"
                    sx={{ color: bloombergColors.textSecondary }}
                  >
                    Instruments
                  </Typography>
                  <Typography
                    variant="h6"
                    sx={{ color: bloombergColors.primary }}
                  >
                    {metrics.instruments_tracked || 0}
                  </Typography>
                </Box>
              </Grid2>
              <Grid2 xs={6}>
                <Box sx={{ textAlign: "center" }}>
                  <Typography
                    variant="caption"
                    sx={{ color: bloombergColors.textSecondary }}
                  >
                    Latency
                  </Typography>
                  <Typography
                    variant="h6"
                    sx={{ color: bloombergColors.success }}
                  >
                    {metrics.avg_processing_time_ms?.toFixed(1) || 0}ms
                  </Typography>
                </Box>
              </Grid2>
              <Grid2 xs={6}>
                <Box sx={{ textAlign: "center" }}>
                  <Typography
                    variant="caption"
                    sx={{ color: bloombergColors.textSecondary }}
                  >
                    Memory
                  </Typography>
                  <Typography
                    variant="h6"
                    sx={{ color: bloombergColors.warning }}
                  >
                    {metrics.memory_usage_mb?.toFixed(1) || 0}MB
                  </Typography>
                </Box>
              </Grid2>
              <Grid2 xs={6}>
                <Box sx={{ textAlign: "center" }}>
                  <Typography
                    variant="caption"
                    sx={{ color: bloombergColors.textSecondary }}
                  >
                    Accuracy
                  </Typography>
                  <Typography
                    variant="h6"
                    sx={{ color: bloombergColors.primary }}
                  >
                    {metrics.detection_accuracy?.toFixed(0) || 0}%
                  </Typography>
                </Box>
              </Grid2>
            </Grid2>
          </Paper>
        )}

        {/* Breakout List */}
        <Box sx={{ flexGrow: 1, overflow: "auto" }}>
          {breakouts.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                flexDirection: "column",
              }}
            >
              <ShowChart
                sx={{
                  color: bloombergColors.textSecondary,
                  fontSize: 48,
                  mb: 1,
                }}
              />
              <Typography
                sx={{
                  color: bloombergColors.textSecondary,
                  textAlign: "center",
                }}
              >
                No breakouts detected
                <br />
                <small>Waiting for market signals...</small>
              </Typography>
            </Box>
          ) : (
            <Box sx={{ space: 1 }}>
              {breakouts.map((breakout, index) => {
                const config = breakoutTypeConfig[breakout.breakout_type] || {
                  icon: "📊",
                  color: bloombergColors.primary,
                  label: breakout.breakout_type,
                };

                const strengthColor = getStrengthColor(breakout.strength);
                const isPositive = breakout.percentage_move > 0;

                return (
                  <Paper
                    key={`${breakout.instrument_key}_${breakout.timestamp}_${index}`}
                    sx={{
                      p: 1.5,
                      mb: 1,
                      backgroundColor: bloombergColors.surface,
                      border: `1px solid ${config.color}20`,
                      "&:hover": {
                        backgroundColor: bloombergColors.surfaceVariant,
                        border: `1px solid ${config.color}40`,
                      },
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                      }}
                    >
                      <Box sx={{ flex: 1 }}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                            mb: 0.5,
                          }}
                        >
                          <Typography sx={{ fontSize: "1.2em" }}>
                            {config.icon}
                          </Typography>
                          <Typography
                            variant="body2"
                            fontWeight="bold"
                            sx={{ color: bloombergColors.text }}
                          >
                            {breakout.symbol}
                          </Typography>
                          <Chip
                            label={config.label}
                            size="small"
                            sx={{
                              backgroundColor: `${config.color}20`,
                              color: config.color,
                              fontSize: "0.7rem",
                              height: 20,
                            }}
                          />
                        </Box>

                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 2,
                            mb: 0.5,
                          }}
                        >
                          <Typography
                            variant="h6"
                            sx={{ color: bloombergColors.primary }}
                          >
                            ₹{breakout.current_price?.toFixed(2)}
                          </Typography>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 0.5,
                            }}
                          >
                            {isPositive ? <TrendingUp /> : <TrendingDown />}
                            <Typography
                              variant="body2"
                              sx={{
                                color: isPositive
                                  ? bloombergColors.success
                                  : bloombergColors.error,
                                fontWeight: "bold",
                              }}
                            >
                              {isPositive ? "+" : ""}
                              {breakout.percentage_move?.toFixed(2)}%
                            </Typography>
                          </Box>
                        </Box>

                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                            flexWrap: "wrap",
                          }}
                        >
                          {breakout.volume && (
                            <Typography
                              variant="caption"
                              sx={{ color: bloombergColors.textSecondary }}
                            >
                              Vol: {(breakout.volume / 1000).toFixed(0)}K
                            </Typography>
                          )}
                          {breakout.volume_ratio &&
                            breakout.volume_ratio > 1 && (
                              <Chip
                                label={`${breakout.volume_ratio.toFixed(
                                  1
                                )}x Vol`}
                                size="small"
                                sx={{
                                  backgroundColor:
                                    bloombergColors.warning + "20",
                                  color: bloombergColors.warning,
                                  fontSize: "0.6rem",
                                  height: 16,
                                }}
                              />
                            )}
                          {breakout.confirmation_signals &&
                            breakout.confirmation_signals.length > 0 && (
                              <Tooltip
                                title={breakout.confirmation_signals.join(", ")}
                              >
                                <Chip
                                  label="Confirmed"
                                  size="small"
                                  sx={{
                                    backgroundColor:
                                      bloombergColors.success + "20",
                                    color: bloombergColors.success,
                                    fontSize: "0.6rem",
                                    height: 16,
                                  }}
                                />
                              </Tooltip>
                            )}
                        </Box>
                      </Box>

                      <Box sx={{ textAlign: "right" }}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 0.5,
                            mb: 0.5,
                          }}
                        >
                          <Typography
                            variant="caption"
                            sx={{ color: bloombergColors.textSecondary }}
                          >
                            Strength
                          </Typography>
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: "50%",
                              backgroundColor: strengthColor,
                            }}
                          />
                          <Typography
                            variant="caption"
                            sx={{ color: strengthColor, fontWeight: "bold" }}
                          >
                            {breakout.strength?.toFixed(1)}
                          </Typography>
                        </Box>

                        {breakout.confidence && (
                          <Typography
                            variant="caption"
                            sx={{
                              color: bloombergColors.textSecondary,
                              display: "block",
                            }}
                          >
                            Confidence: {breakout.confidence.toFixed(0)}%
                          </Typography>
                        )}

                        <Typography
                          variant="caption"
                          sx={{
                            color: bloombergColors.textSecondary,
                            display: "block",
                          }}
                        >
                          {getTimeAgo(breakout.timestamp)}
                        </Typography>
                      </Box>
                    </Box>
                  </Paper>
                );
              })}
            </Box>
          )}
        </Box>

        {/* Footer with last update time */}
        <Divider sx={{ my: 1 }} />
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography
            variant="caption"
            sx={{ color: bloombergColors.textSecondary }}
          >
            {breakouts.length} of {totalBreakouts} breakouts
          </Typography>
          <Typography
            variant="caption"
            sx={{ color: bloombergColors.textSecondary }}
          >
            Updated: {lastUpdate.toLocaleTimeString()}
          </Typography>
        </Box>
      </Box>

      {/* CSS for pulse animation */}
      <style jsx>{`
        @keyframes pulse {
          0% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
          100% {
            opacity: 1;
          }
        }
      `}</style>
    </Paper>
  );
};

export default withErrorBoundary(EnhancedBreakoutWidget, {
  fallbackComponent: ({ error }) => (
    <Paper
      sx={{ backgroundColor: bloombergColors.cardBg, p: 2, height: "100%" }}
    >
      <Box sx={{ textAlign: "center", color: bloombergColors.error }}>
        <Typography variant="h6">Enhanced Breakout Widget Error</Typography>
        <Typography variant="body2">{error?.message}</Typography>
      </Box>
    </Paper>
  ),
});
