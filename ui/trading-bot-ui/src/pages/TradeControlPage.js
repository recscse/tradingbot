import React, { useState } from "react";
import {
  Container,
  Paper,
  Typography,
  Box,
  TextField,
  Button,
  Stack,
  Grid,
  Card,
  CardContent,
  Alert,
  Chip,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import {
  PlayArrow,
  Stop,
  TrendingUp,
  AccountBalance,
  ShowChart,
  Speed,
} from "@mui/icons-material";

const TradeControlForm = () => {
  const [stockSymbol, setStockSymbol] = useState("");
  const [tradeAmount, setTradeAmount] = useState("");
  // const [tradeType, setTradeType] = useState("buy"); // Trade type state - reserved for buy/sell selection
  const [isTrading, setIsTrading] = useState(false);

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  // const isTablet = useMediaQuery(theme.breakpoints.down("md")); // Tablet breakpoint - reserved for responsive features

  const handleStartTrade = () => {
    setIsTrading(true);
    console.log(
      "Starting trade for stock:",
      stockSymbol,
      "with amount:",
      tradeAmount
    );
    // Simulate trade start
    setTimeout(() => setIsTrading(false), 3000);
  };

  const handleStopTrade = () => {
    setIsTrading(false);
    console.log("Stopping trade for stock:", stockSymbol);
  };

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2, sm: 3 } }}>
      <Box component="form" noValidate>
        <Grid container spacing={2}>
          {/* Trade Form Section */}
          <Grid item xs={12} md={8}>
            <Card sx={{ borderRadius: 2, boxShadow: theme.shadows[4] }}>
              <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    fontSize: { xs: "1.1rem", sm: "1.25rem" },
                  }}
                >
                  <ShowChart color="primary" />
                  Trade Configuration
                </Typography>

                <Stack spacing={{ xs: 2, sm: 3 }}>
                  <TextField
                    label="Stock Symbol"
                    variant="outlined"
                    fullWidth
                    value={stockSymbol}
                    onChange={(e) =>
                      setStockSymbol(e.target.value.toUpperCase())
                    }
                    placeholder="e.g., AAPL, GOOGL, TSLA"
                    sx={{
                      "& .MuiInputBase-root": {
                        fontSize: { xs: "1rem", sm: "1.1rem" },
                      },
                    }}
                  />

                  <TextField
                    label="Trade Amount (₹)"
                    variant="outlined"
                    type="number"
                    fullWidth
                    value={tradeAmount}
                    onChange={(e) => setTradeAmount(e.target.value)}
                    placeholder="Enter amount to invest"
                    sx={{
                      "& .MuiInputBase-root": {
                        fontSize: { xs: "1rem", sm: "1.1rem" },
                      },
                    }}
                  />

                  {/* Action Buttons - Responsive Stack */}
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={{ xs: 1.5, sm: 2 }}
                    sx={{ pt: 1 }}
                  >
                    <Button
                      variant="contained"
                      color="success"
                      onClick={handleStartTrade}
                      disabled={!stockSymbol || !tradeAmount || isTrading}
                      startIcon={<PlayArrow />}
                      fullWidth={isMobile}
                      sx={{
                        minHeight: { xs: 48, sm: 52 },
                        fontSize: { xs: "0.9rem", sm: "1rem" },
                        fontWeight: 600,
                      }}
                    >
                      {isTrading ? "Starting..." : "Start Trade"}
                    </Button>

                    <Button
                      variant="outlined"
                      color="error"
                      onClick={handleStopTrade}
                      startIcon={<Stop />}
                      fullWidth={isMobile}
                      sx={{
                        minHeight: { xs: 48, sm: 52 },
                        fontSize: { xs: "0.9rem", sm: "1rem" },
                        fontWeight: 600,
                      }}
                    >
                      Stop Trade
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          {/* Status & Info Section */}
          <Grid item xs={12} md={4}>
            <Stack spacing={2}>
              {/* Trading Status */}
              <Card sx={{ borderRadius: 2, boxShadow: theme.shadows[4] }}>
                <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{
                      fontSize: { xs: "1.1rem", sm: "1.25rem" },
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                    }}
                  >
                    <Speed color="primary" />
                    Trading Status
                  </Typography>

                  <Box sx={{ textAlign: "center", py: 2 }}>
                    <Chip
                      label={isTrading ? "TRADING ACTIVE" : "TRADING IDLE"}
                      color={isTrading ? "success" : "default"}
                      variant={isTrading ? "filled" : "outlined"}
                      sx={{
                        fontSize: { xs: "0.8rem", sm: "0.9rem" },
                        fontWeight: 600,
                        px: 2,
                        py: 0.5,
                      }}
                    />
                  </Box>

                  {stockSymbol && (
                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        Selected Symbol:
                      </Typography>
                      <Typography
                        variant="h6"
                        color="primary.main"
                        sx={{ fontSize: { xs: "1.1rem", sm: "1.25rem" } }}
                      >
                        {stockSymbol}
                      </Typography>
                    </Box>
                  )}

                  {tradeAmount && (
                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        gutterBottom
                      >
                        Trade Amount:
                      </Typography>
                      <Typography
                        variant="h6"
                        color="success.main"
                        sx={{ fontSize: { xs: "1.1rem", sm: "1.25rem" } }}
                      >
                        ₹{Number(tradeAmount).toLocaleString()}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>

              {/* Quick Stats */}
              <Card sx={{ borderRadius: 2, boxShadow: theme.shadows[4] }}>
                <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{
                      fontSize: { xs: "1.1rem", sm: "1.25rem" },
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                    }}
                  >
                    <TrendingUp color="primary" />
                    Quick Stats
                  </Typography>

                  <Stack spacing={1.5}>
                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        Active Trades:
                      </Typography>
                      <Typography variant="body2" fontWeight={600}>
                        0
                      </Typography>
                    </Box>

                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        Portfolio Value:
                      </Typography>
                      <Typography
                        variant="body2"
                        fontWeight={600}
                        color="success.main"
                      >
                        ₹0.00
                      </Typography>
                    </Box>

                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        Today's P&L:
                      </Typography>
                      <Typography variant="body2" fontWeight={600}>
                        ₹0.00
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Stack>
          </Grid>
        </Grid>

        {/* Mobile-specific alerts and tips */}
        {isMobile && (
          <Alert
            severity="info"
            sx={{ mt: 3, fontSize: "0.875rem" }}
            icon={<AccountBalance />}
          >
            <Typography variant="body2">
              <strong>Mobile Trading Tip:</strong> Ensure stable internet
              connection for real-time trading operations.
            </Typography>
          </Alert>
        )}
      </Box>
    </Container>
  );
};

const TradeControlPage = () => {
  const theme = useTheme();
  // const isMobile = useMediaQuery(theme.breakpoints.down("sm")); // Reserved for responsive features

  return (
    <Container
      maxWidth="lg"
      sx={{
        py: { xs: 2, sm: 3, md: 4 },
        px: { xs: 1, sm: 2 },
      }}
    >
      <Paper
        sx={{
          borderRadius: { xs: 2, sm: 3 },
          overflow: "hidden",
          p: 0,
        }}
      >
        {/* Header Section */}
        <Box
          sx={{
            background: `linear-gradient(135deg, ${theme.palette.primary.main}20, ${theme.palette.secondary.main}10)`,
            p: { xs: 2, sm: 3 },
            borderBottom: `1px solid ${theme.palette.divider}`,
          }}
        >
          <Typography
            variant="h4"
            align="center"
            gutterBottom
            sx={{
              fontSize: { xs: "1.75rem", sm: "2rem", md: "2.5rem" },
              fontWeight: 700,
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              mb: 1,
            }}
          >
            Trade Control Center
          </Typography>

          <Typography
            variant="body1"
            align="center"
            color="text.secondary"
            sx={{
              fontSize: { xs: "0.875rem", sm: "1rem" },
              maxWidth: 600,
              mx: "auto",
            }}
          >
            Manage your automated trading operations with advanced controls and
            real-time monitoring
          </Typography>
        </Box>

        {/* Form Content */}
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <TradeControlForm />
        </Box>
      </Paper>
    </Container>
  );
};

export default TradeControlPage;
