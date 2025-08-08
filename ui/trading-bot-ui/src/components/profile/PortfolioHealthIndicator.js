// src/components/profile/PortfolioHealthIndicator.jsx
import React from "react";
import {
  Box,
  Typography,
  Paper,
  Stack,
  Avatar,
  LinearProgress,
  Chip,
  Grid,
  useTheme,
  alpha,
} from "@mui/material";
import {
  Security as SecurityIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
} from "@mui/icons-material";

const PortfolioHealthIndicator = ({ portfolioData, tradingStats }) => {
  const theme = useTheme();

  // Calculate portfolio health metrics
  const calculateHealthScore = () => {
    let score = 0;
    let factors = [];

    // Diversification score (30%)
    const brokerCount = portfolioData?.brokerAccounts?.length || 0;
    const diversificationScore = Math.min(brokerCount * 20, 30);
    score += diversificationScore;
    factors.push({
      name: "Diversification",
      score: diversificationScore,
      max: 30,
      status: diversificationScore >= 20 ? "good" : diversificationScore >= 10 ? "warning" : "poor"
    });

    // Performance consistency (25%)
    const winRate = tradingStats?.win_rate || 0;
    const consistencyScore = Math.min(winRate * 0.25, 25);
    score += consistencyScore;
    factors.push({
      name: "Performance",
      score: consistencyScore,
      max: 25,
      status: consistencyScore >= 15 ? "good" : consistencyScore >= 10 ? "warning" : "poor"
    });

    // Risk management (25%)
    const avgTradeSize = tradingStats?.avg_trade_value || 0;
    const totalPortfolio = tradingStats?.total_portfolio_value || 1;
    const riskRatio = avgTradeSize / totalPortfolio;
    const riskScore = riskRatio < 0.05 ? 25 : riskRatio < 0.1 ? 20 : riskRatio < 0.2 ? 15 : 10;
    score += riskScore;
    factors.push({
      name: "Risk Management",
      score: riskScore,
      max: 25,
      status: riskScore >= 20 ? "good" : riskScore >= 15 ? "warning" : "poor"
    });

    // Activity level (20%)
    const totalTrades = tradingStats?.total_trades || 0;
    const activityScore = Math.min(totalTrades * 0.2, 20);
    score += activityScore;
    factors.push({
      name: "Activity",
      score: activityScore,
      max: 20,
      status: activityScore >= 15 ? "good" : activityScore >= 10 ? "warning" : "poor"
    });

    return { score: Math.round(score), factors };
  };

  const { score, factors } = calculateHealthScore();

  const getHealthStatus = (score) => {
    if (score >= 80) return { status: "excellent", color: "success", icon: CheckIcon };
    if (score >= 60) return { status: "good", color: "primary", icon: CheckIcon };
    if (score >= 40) return { status: "average", color: "warning", icon: WarningIcon };
    return { status: "needs improvement", color: "error", icon: ErrorIcon };
  };

  const healthStatus = getHealthStatus(score);

  const getFactorColor = (status) => {
    switch (status) {
      case "good": return "success";
      case "warning": return "warning";
      case "poor": return "error";
      default: return "primary";
    }
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 4,
        bgcolor: alpha(theme.palette.background.paper, 0.8),
        backdropFilter: "blur(10px)",
        border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        borderRadius: 3,
        position: "relative",
        overflow: "hidden",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: `linear-gradient(90deg, ${theme.palette[healthStatus.color].main}, ${theme.palette[healthStatus.color].light})`,
        }
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={3}>
        <Stack direction="row" alignItems="center" spacing={2}>
          <Avatar
            sx={{
              bgcolor: alpha(theme.palette[healthStatus.color].main, 0.1),
              color: `${healthStatus.color}.main`,
              width: 56,
              height: 56,
            }}
          >
            <SecurityIcon sx={{ fontSize: 28 }} />
          </Avatar>
          <Box>
            <Typography variant="h6" fontWeight={700}>
              Portfolio Health Score
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Overall assessment of your trading portfolio
            </Typography>
          </Box>
        </Stack>

        <Stack alignItems="center" spacing={1}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="h3" fontWeight={800} color={`${healthStatus.color}.main`}>
              {score}
            </Typography>
            <Typography variant="h6" color="text.secondary">
              /100
            </Typography>
          </Stack>
          <Chip
            icon={<healthStatus.icon sx={{ fontSize: 16 }} />}
            label={healthStatus.status.toUpperCase()}
            color={healthStatus.color}
            variant="outlined"
            sx={{ fontWeight: 600, textTransform: "capitalize" }}
          />
        </Stack>
      </Stack>

      {/* Health Score Progress */}
      <Box mb={4}>
        <LinearProgress
          variant="determinate"
          value={score}
          sx={{
            height: 12,
            borderRadius: 6,
            bgcolor: alpha(theme.palette[healthStatus.color].main, 0.1),
            "& .MuiLinearProgress-bar": {
              borderRadius: 6,
              background: `linear-gradient(90deg, ${theme.palette[healthStatus.color].main}, ${theme.palette[healthStatus.color].light})`,
            }
          }}
        />
        <Stack direction="row" justifyContent="space-between" mt={1}>
          <Typography variant="caption" color="text.secondary">
            Poor (0-39)
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Average (40-59)
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Good (60-79)
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Excellent (80-100)
          </Typography>
        </Stack>
      </Box>

      {/* Health Factors Breakdown */}
      <Typography variant="h6" fontWeight={700} mb={3}>
        Health Factors
      </Typography>

      <Grid container spacing={3}>
        {factors.map((factor, index) => (
          <Grid item xs={6} sm={3} key={index}>
            <Box>
              <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
                <Typography variant="body2" fontWeight={600}>
                  {factor.name}
                </Typography>
                <Chip
                  size="small"
                  label={`${factor.score}/${factor.max}`}
                  color={getFactorColor(factor.status)}
                  variant="outlined"
                  sx={{ fontSize: "0.7rem", height: 20 }}
                />
              </Stack>
              
              <LinearProgress
                variant="determinate"
                value={(factor.score / factor.max) * 100}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  bgcolor: alpha(theme.palette[getFactorColor(factor.status)].main, 0.1),
                  "& .MuiLinearProgress-bar": {
                    borderRadius: 3,
                    bgcolor: `${getFactorColor(factor.status)}.main`,
                  }
                }}
              />
            </Box>
          </Grid>
        ))}
      </Grid>

      {/* Recommendations */}
      <Box mt={4} pt={3} borderTop={`1px solid ${alpha(theme.palette.divider, 0.1)}`}>
        <Typography variant="body2" fontWeight={600} mb={2}>
          💡 Recommendations
        </Typography>
        
        <Stack spacing={1}>
          {score < 80 && (
            <>
              {factors.find(f => f.name === "Diversification" && f.score < 20) && (
                <Typography variant="body2" color="text.secondary">
                  • Consider connecting more brokers to improve diversification
                </Typography>
              )}
              {factors.find(f => f.name === "Performance" && f.score < 15) && (
                <Typography variant="body2" color="text.secondary">
                  • Review your trading strategy to improve win rate
                </Typography>
              )}
              {factors.find(f => f.name === "Risk Management" && f.score < 20) && (
                <Typography variant="body2" color="text.secondary">
                  • Consider reducing position sizes to manage risk better
                </Typography>
              )}
              {factors.find(f => f.name === "Activity" && f.score < 15) && (
                <Typography variant="body2" color="text.secondary">
                  • Increase trading activity with proper risk management
                </Typography>
              )}
            </>
          )}
          {score >= 80 && (
            <Typography variant="body2" color="success.main">
              ✅ Excellent portfolio health! Keep up the great work!
            </Typography>
          )}
        </Stack>
      </Box>
    </Paper>
  );
};

export default PortfolioHealthIndicator;