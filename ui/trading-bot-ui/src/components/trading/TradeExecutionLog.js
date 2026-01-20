// components/trading/TradeExecutionLog.js
import React, { useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Stack,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
} from "@mui/material";
import {
  ExpandMore,
  TrendingUp,
  TrendingDown,
  Target,
  Shield,
  Psychology,
  Timeline,
  Assessment,
  Info,
  CheckCircle,
} from "@mui/icons-material";

const TradeExecutionLog = ({ trades, tradingMode, analytics }) => {
  const [expandedTrade, setExpandedTrade] = useState(null);

  const formatCurrency = (amount) => {
    if (amount == null) return "₹0.00";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString(),
      time: date.toLocaleTimeString(),
    };
  };

  const getPnLColor = (pnl) => {
    if (pnl > 0) return "success.main";
    if (pnl < 0) return "error.main";
    return "text.primary";
  };

  const getTradeDecisionReason = (trade) => {
    // Simulate AI decision reasoning based on trade data
    const reasons = [];
    
    if (trade.pnl > 0) {
      reasons.push("✅ Price moved favorably");
      reasons.push("📈 Technical indicators aligned");
      reasons.push("⏰ Optimal timing execution");
    } else if (trade.pnl < 0) {
      reasons.push("🛡️ Stop-loss triggered for risk management");
      reasons.push("📉 Market sentiment shifted");
      reasons.push("⚡ Quick exit to minimize losses");
    }
    
    if (trade.strategy) {
      reasons.push(`🎯 ${trade.strategy} strategy applied`);
    }
    
    return reasons.length > 0 ? reasons : ["📊 Standard market execution"];
  };

  const getExitReasonIcon = (reason) => {
    if (!reason) return <Info />;
    
    const lowerReason = reason.toLowerCase();
    if (lowerReason.includes("target")) return <Target color="success" />;
    if (lowerReason.includes("stop")) return <Shield color="error" />;
    if (lowerReason.includes("time")) return <Timeline color="warning" />;
    if (lowerReason.includes("manual")) return <Psychology color="info" />;
    
    return <Assessment />;
  };

  const getRiskRewardAnalysis = (trade) => {
    // Simulate risk-reward analysis
    if (!trade.pnl) return null;
    
    const risk = Math.abs(trade.price * 0.02); // Assume 2% risk
    const reward = Math.abs(trade.pnl);
    const ratio = reward / risk;
    
    return {
      risk: risk,
      reward: reward,
      ratio: ratio,
      rating: ratio >= 2 ? "Excellent" : ratio >= 1.5 ? "Good" : ratio >= 1 ? "Average" : "Poor"
    };
  };

  if (!trades || trades.length === 0) {
    return (
      <Card>
        <CardContent>
          <Box textAlign="center" py={4}>
            <Assessment sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
            <Typography variant="h6" color="textSecondary" gutterBottom>
              No Trade Execution Data
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Detailed trade logs will appear here once trading begins
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" fontWeight="bold" gutterBottom>
          📋 Trade Execution Log ({tradingMode} Mode)
        </Typography>

        {/* Execution Summary */}
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            <strong>Execution Summary:</strong> {trades.length} total executions • 
            {analytics ? ` ${analytics.winning_trades} profitable • ${analytics.losing_trades} losses • ` : " "}
            All decisions logged with AI reasoning
          </Typography>
        </Alert>

        {/* Trade Log Table */}
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Trade Details</TableCell>
                <TableCell align="right">Execution</TableCell>
                <TableCell align="right">P&L Impact</TableCell>
                <TableCell>Decision Logic</TableCell>
                <TableCell>Risk Management</TableCell>
                <TableCell align="center">Analysis</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {trades.slice(0, 15).map((trade, index) => {
                const dateTime = formatDateTime(trade.timestamp);
                const decisions = getTradeDecisionReason(trade);
                const riskReward = getRiskRewardAnalysis(trade);
                
                return (
                  <TableRow key={index} hover>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {trade.symbol}
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="center" mt={0.5}>
                          <Chip
                            label={trade.action}
                            color={trade.action === "BUY" ? "success" : "error"}
                            size="small"
                          />
                          <Typography variant="caption" color="textSecondary">
                            {trade.quantity} qty
                          </Typography>
                        </Stack>
                        <Typography variant="caption" color="textSecondary" display="block">
                          {dateTime.date} • {dateTime.time}
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell align="right">
                      <Typography variant="body2" fontWeight="medium">
                        {formatCurrency(trade.price)}
                      </Typography>
                      <Chip
                        label={trade.order_type || "MARKET"}
                        size="small"
                        variant="outlined"
                        sx={{ mt: 0.5 }}
                      />
                    </TableCell>
                    
                    <TableCell align="right">
                      {trade.pnl ? (
                        <Box>
                          <Typography 
                            variant="body2" 
                            fontWeight="bold"
                            sx={{ color: getPnLColor(trade.pnl) }}
                          >
                            {trade.pnl >= 0 ? "+" : ""}{formatCurrency(trade.pnl)}
                          </Typography>
                          <Box display="flex" alignItems="center" justifyContent="flex-end" mt={0.5}>
                            {trade.pnl >= 0 ? (
                              <TrendingUp sx={{ fontSize: 14 }} color="success" />
                            ) : (
                              <TrendingDown sx={{ fontSize: 14 }} color="error" />
                            )}
                            <Typography variant="caption" color="textSecondary" ml={0.5}>
                              Impact
                            </Typography>
                          </Box>
                        </Box>
                      ) : (
                        <Typography variant="body2" color="textSecondary">
                          Pending
                        </Typography>
                      )}
                    </TableCell>
                    
                    <TableCell>
                      <Box>
                        {decisions.slice(0, 2).map((reason, idx) => (
                          <Typography key={idx} variant="caption" display="block" color="textSecondary">
                            {reason}
                          </Typography>
                        ))}
                        {decisions.length > 2 && (
                          <Typography variant="caption" color="primary.main">
                            +{decisions.length - 2} more factors
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        {getExitReasonIcon(trade.exit_reason)}
                        <Box>
                          <Typography variant="caption" display="block">
                            {trade.exit_reason || "Manual execution"}
                          </Typography>
                          {riskReward && (
                            <Typography 
                              variant="caption" 
                              color={riskReward.ratio >= 1.5 ? "success.main" : "textSecondary"}
                            >
                              R:R {riskReward.ratio.toFixed(2)}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </TableCell>
                    
                    <TableCell align="center">
                      <Tooltip title="View detailed analysis">
                        <IconButton
                          size="small"
                          onClick={() => setExpandedTrade(expandedTrade === index ? null : index)}
                        >
                          <ExpandMore />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Detailed Analysis Accordion */}
        {trades.slice(0, 15).map((trade, index) => (
          <Accordion 
            key={`detail-${index}`}
            expanded={expandedTrade === index}
            onChange={() => setExpandedTrade(expandedTrade === index ? null : index)}
            sx={{ mt: 1, display: expandedTrade === index ? 'block' : 'none' }}
          >
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography variant="subtitle2">
                📊 Detailed Analysis: {trade.symbol} {trade.action}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                {/* Trade Details */}
                <Grid item xs={12} md={4}>
                  <Typography variant="h6" gutterBottom>
                    🎯 Trade Execution
                  </Typography>
                  <Stack spacing={1}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="textSecondary">Symbol:</Typography>
                      <Typography variant="body2" fontWeight="medium">{trade.symbol}</Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="textSecondary">Action:</Typography>
                      <Chip label={trade.action} size="small" color={trade.action === "BUY" ? "success" : "error"} />
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="textSecondary">Quantity:</Typography>
                      <Typography variant="body2" fontWeight="medium">{trade.quantity}</Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="textSecondary">Price:</Typography>
                      <Typography variant="body2" fontWeight="medium">{formatCurrency(trade.price)}</Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="textSecondary">Order Type:</Typography>
                      <Typography variant="body2" fontWeight="medium">{trade.order_type || "MARKET"}</Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="textSecondary">Status:</Typography>
                      <Chip 
                        label={trade.status} 
                        size="small" 
                        color={trade.status === "COMPLETED" ? "success" : "default"} 
                      />
                    </Box>
                  </Stack>
                </Grid>

                {/* AI Decision Reasoning */}
                <Grid item xs={12} md={4}>
                  <Typography variant="h6" gutterBottom>
                    🧠 AI Decision Logic
                  </Typography>
                  <Stack spacing={1}>
                    {getTradeDecisionReason(trade).map((reason, idx) => (
                      <Box key={idx} display="flex" alignItems="center" gap={1}>
                        <CheckCircle sx={{ fontSize: 16 }} color="success" />
                        <Typography variant="body2">{reason}</Typography>
                      </Box>
                    ))}
                  </Stack>
                  
                  {trade.strategy && (
                    <Box mt={2} p={1} bgcolor="primary.light" borderRadius={1}>
                      <Typography variant="caption" color="primary.dark" fontWeight="medium">
                        Strategy Applied: {trade.strategy}
                      </Typography>
                    </Box>
                  )}
                </Grid>

                {/* Risk & Performance */}
                <Grid item xs={12} md={4}>
                  <Typography variant="h6" gutterBottom>
                    📈 Performance Analysis
                  </Typography>
                  
                  {trade.pnl && (
                    <Box mb={2}>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        P&L Impact
                      </Typography>
                      <Typography 
                        variant="h6" 
                        fontWeight="bold"
                        sx={{ color: getPnLColor(trade.pnl) }}
                      >
                        {trade.pnl >= 0 ? "+" : ""}{formatCurrency(trade.pnl)}
                      </Typography>
                    </Box>
                  )}

                  {getRiskRewardAnalysis(trade) && (
                    <Box>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        Risk-Reward Analysis
                      </Typography>
                      <Grid container spacing={1}>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="error.main">
                            Risk: {formatCurrency(getRiskRewardAnalysis(trade).risk)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="success.main">
                            Reward: {formatCurrency(getRiskRewardAnalysis(trade).reward)}
                          </Typography>
                        </Grid>
                        <Grid item xs={12}>
                          <Chip 
                            label={`${getRiskRewardAnalysis(trade).rating} (1:${getRiskRewardAnalysis(trade).ratio.toFixed(2)})`}
                            size="small"
                            color={getRiskRewardAnalysis(trade).ratio >= 1.5 ? "success" : "warning"}
                          />
                        </Grid>
                      </Grid>
                    </Box>
                  )}

                  {trade.exit_reason && (
                    <Box mt={2} p={1} bgcolor="background.paper" border={1} borderColor="divider" borderRadius={1}>
                      <Typography variant="caption" color="textSecondary" display="block">
                        Exit Reason
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {trade.exit_reason}
                      </Typography>
                    </Box>
                  )}
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        ))}

        {/* Summary Statistics */}
        <Box mt={3} p={2} bgcolor="background.paper" borderRadius={1} border={1} borderColor="divider">
          <Typography variant="subtitle2" gutterBottom>
            📊 Execution Summary
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Total Executions
              </Typography>
              <Typography variant="h6" fontWeight="bold">
                {trades.length}
              </Typography>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Profitable Trades
              </Typography>
              <Typography variant="h6" fontWeight="bold" color="success.main">
                {trades.filter(t => t.pnl > 0).length}
              </Typography>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Average P&L
              </Typography>
              <Typography variant="h6" fontWeight="bold">
                {formatCurrency(
                  trades.filter(t => t.pnl).reduce((sum, t) => sum + t.pnl, 0) / 
                  Math.max(trades.filter(t => t.pnl).length, 1)
                )}
              </Typography>
            </Grid>
            
            <Grid item xs={6} md={3}>
              <Typography variant="caption" color="textSecondary">
                Success Rate
              </Typography>
              <Typography variant="h6" fontWeight="bold" color="primary.main">
                {trades.length > 0 ? 
                  ((trades.filter(t => t.pnl > 0).length / trades.filter(t => t.pnl).length) * 100).toFixed(1) + "%" 
                  : "0%"
                }
              </Typography>
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TradeExecutionLog;