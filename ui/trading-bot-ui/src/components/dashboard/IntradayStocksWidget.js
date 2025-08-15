// components/dashboard/IntradayStocksWidget.jsx
import React from "react";
import { bloombergColors } from "../../themes/bloombergColors";
import { Paper, Box, Chip } from "@mui/material";
import { withErrorBoundary } from "../common/ErrorBoundary";

const IntradayStocksWidget = ({ data, isLoading, compact = false }) => {
  if (isLoading) {
    return (
      <Paper
        sx={{ backgroundColor: bloombergColors.cardBg, p: 2, height: "100%" }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
          }}
        >
          <Box sx={{ color: bloombergColors.textSecondary }}>
            Loading intraday stocks...
          </Box>
        </Box>
      </Paper>
    );
  }

  // FIXED: Backend sends different data structure
  const {
    all_candidates = [],
    fno_candidates = [], 
    high_momentum = [],
    high_volume = [],
    summary = {},
  } = data;

  // FIXED: Categorize stocks by risk level based on change_percent and volatility
  const categorizeByRisk = (stocks) => {
    const low_risk = [];
    const medium_risk = [];
    const high_risk = [];
    
    stocks.forEach(stock => {
      const changePercent = Math.abs(stock.change_percent || 0);
      const volume_ratio = stock.volume_ratio || 1;
      const price = stock.last_price || stock.ltp || 0;
      
      // Risk calculation based on multiple factors
      let riskScore = 0;
      
      // Change percent risk (0-3 points)
      if (changePercent >= 5) riskScore += 3;
      else if (changePercent >= 2.5) riskScore += 2;
      else if (changePercent >= 1) riskScore += 1;
      
      // Volume risk (0-2 points)
      if (volume_ratio >= 3) riskScore += 2;
      else if (volume_ratio >= 1.5) riskScore += 1;
      
      // Price risk (0-1 point)
      if (price < 50) riskScore += 1;
      
      // Categorize based on total risk score
      if (riskScore >= 4) {
        high_risk.push({...stock, risk_score: riskScore});
      } else if (riskScore >= 2) {
        medium_risk.push({...stock, risk_score: riskScore});
      } else {
        low_risk.push({...stock, risk_score: riskScore});
      }
    });
    
    return { low_risk, medium_risk, high_risk };
  };

  // Use all_candidates as primary source, fallback to combined arrays
  const stocksToAnalyze = all_candidates.length > 0 
    ? all_candidates 
    : [...fno_candidates, ...high_momentum, ...high_volume];
  
  const { low_risk, medium_risk, high_risk } = categorizeByRisk(stocksToAnalyze);

  const getRiskColor = (risk) => {
    switch (risk) {
      case "low":
        return bloombergColors.positive;
      case "medium":
        return bloombergColors.warning;
      case "high":
        return bloombergColors.negative;
      default:
        return bloombergColors.textPrimary;
    }
  };

  const getRiskIcon = (risk) => {
    switch (risk) {
      case "low":
        return "🟢";
      case "medium":
        return "🟡";
      case "high":
        return "🔴";
      default:
        return "⚪";
    }
  };

  const renderIntradayStock = (stock, riskLevel) => (
    <Box
      key={stock.symbol}
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        py: 0.5,
        px: 1,
        mb: 0.5,
        backgroundColor: bloombergColors.background,
        border: `1px solid ${bloombergColors.border}`,
        borderRadius: 0.5,
        borderLeft: `3px solid ${getRiskColor(riskLevel)}`,
        position: "relative",
        "&:hover": {
          backgroundColor: `${getRiskColor(riskLevel)}15`,
          borderColor: getRiskColor(riskLevel),
        },
      }}
    >
      <Box>
        <Box
          sx={{
            fontWeight: "bold",
            fontSize: "0.9rem",
            display: "flex",
            alignItems: "center",
            gap: 0.5,
          }}
        >
          <span style={{ fontSize: "0.7rem" }}>{getRiskIcon(riskLevel)}</span>
          {stock.symbol}
        </Box>
        <Box sx={{ fontSize: "0.75rem", color: bloombergColors.textSecondary }}>
          ₹{stock.last_price?.toFixed(2)}
        </Box>
      </Box>

      <Box sx={{ textAlign: "right" }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            gap: 0.5,
          }}
        >
          <Chip
            label={riskLevel.toUpperCase()}
            size="small"
            sx={{
              backgroundColor: getRiskColor(riskLevel),
              color: bloombergColors.background,
              fontSize: "0.65rem",
              height: "18px",
              fontWeight: "bold",
            }}
          />
          <Box
            sx={{
              fontSize: "0.65rem",
              color: bloombergColors.textSecondary,
            }}
          >
            Score: {(stock.intraday_score || stock.risk_score || 0).toFixed(1)}
          </Box>
        </Box>
      </Box>
    </Box>
  );

  const totalStocks = low_risk.length + medium_risk.length + high_risk.length;

  return (
    <Paper
      elevation={0}
      sx={{
        backgroundColor: bloombergColors.cardBg,
        border: `1px solid ${bloombergColors.border}`,
        borderRadius: 1,
        p: 2,
        height: "100%",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          fontSize: "1rem",
          fontWeight: "bold",
          color: bloombergColors.accent,
          mb: 2,
          letterSpacing: "1px",
        }}
      >
        ⚡ INTRADAY STOCKS
      </Box>

      {/* Summary Stats */}
      {!compact && (
        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <Chip
            label={`Total: ${totalStocks}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.accent}20`,
              color: bloombergColors.accent,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`Low: ${low_risk.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.positive}20`,
              color: bloombergColors.positive,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`Med: ${medium_risk.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.warning}20`,
              color: bloombergColors.warning,
              fontSize: "0.7rem",
            }}
          />
          <Chip
            label={`High: ${high_risk.length}`}
            size="small"
            sx={{
              backgroundColor: `${bloombergColors.negative}20`,
              color: bloombergColors.negative,
              fontSize: "0.7rem",
            }}
          />
        </Box>
      )}

      <Box
        sx={{
          display: "flex",
          flexDirection: compact ? "column" : "row",
          height: compact ? "calc(100% - 50px)" : "calc(100% - 100px)",
          gap: 2,
        }}
      >
        {/* Low Risk */}
        <Box sx={{ flex: 1 }}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.positive,
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            🟢 LOW RISK ({low_risk.length})
          </Box>
          <Box sx={{ maxHeight: compact ? "80px" : "150px", overflow: "auto" }}>
            {low_risk
              .slice(0, compact ? 2 : 4)
              .map((stock) => renderIntradayStock(stock, "low"))}
          </Box>
        </Box>

        {/* Medium Risk */}
        <Box sx={{ flex: 1 }}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.warning,
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            🟡 MEDIUM RISK ({medium_risk.length})
          </Box>
          <Box sx={{ maxHeight: compact ? "80px" : "150px", overflow: "auto" }}>
            {medium_risk
              .slice(0, compact ? 2 : 4)
              .map((stock) => renderIntradayStock(stock, "medium"))}
          </Box>
        </Box>

        {/* High Risk */}
        <Box sx={{ flex: 1 }}>
          <Box
            sx={{
              fontSize: "0.85rem",
              fontWeight: "bold",
              color: bloombergColors.negative,
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            🔴 HIGH RISK ({high_risk.length})
          </Box>
          <Box sx={{ maxHeight: compact ? "80px" : "150px", overflow: "auto" }}>
            {high_risk
              .slice(0, compact ? 2 : 4)
              .map((stock) => renderIntradayStock(stock, "high"))}
          </Box>
        </Box>
      </Box>

      {/* Summary Section */}
      {!compact && summary && Object.keys(summary).length > 0 && (
        <Box
          sx={{
            mt: 2,
            pt: 2,
            borderTop: `1px solid ${bloombergColors.border}`,
            display: "flex",
            justifyContent: "space-around",
            fontSize: "0.75rem",
          }}
        >
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>Avg Score</Box>
            <Box sx={{ fontWeight: "bold", color: bloombergColors.accent }}>
              {summary.avg_score?.toFixed(1) || "N/A"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Risk Distribution
            </Box>
            <Box
              sx={{ fontWeight: "bold", color: bloombergColors.textPrimary }}
            >
              {low_risk.length > 0 &&
              medium_risk.length > 0 &&
              high_risk.length > 0
                ? "BALANCED"
                : low_risk.length > medium_risk.length + high_risk.length
                ? "LOW RISK"
                : high_risk.length > low_risk.length + medium_risk.length
                ? "HIGH RISK"
                : "MIXED"}
            </Box>
          </Box>
          <Box sx={{ textAlign: "center" }}>
            <Box sx={{ color: bloombergColors.textSecondary }}>
              Market Sentiment
            </Box>
            <Box
              sx={{
                fontWeight: "bold",
                color:
                  summary.sentiment === "bullish"
                    ? bloombergColors.positive
                    : summary.sentiment === "bearish"
                    ? bloombergColors.negative
                    : bloombergColors.textPrimary,
              }}
            >
              {summary.sentiment?.toUpperCase() || "NEUTRAL"}
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default withErrorBoundary(IntradayStocksWidget, {
  fallbackMessage: "Unable to load intraday stocks data. Trading analysis may be temporarily unavailable.",
  height: "100%"
});
