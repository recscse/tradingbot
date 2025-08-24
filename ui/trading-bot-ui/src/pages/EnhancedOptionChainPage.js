// src/pages/EnhancedOptionChainPage.jsx - Complete Option Chain Page with Upstox Integration
import React, { useState /* , useEffect */ } from 'react'; // useEffect reserved for data fetching
import {
  Box,
  Typography,
  Container,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton,
  useTheme,
  useMediaQuery,
  AppBar,
  Toolbar,
  Stack,
  /* Divider */ // Reserved for section separators
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  ShowChart as OptionsIcon,
  Timeline as FuturesIcon,
  /* TrendingUp as TrendingUpIcon, */ // Reserved for trend indicators
  /* TrendingDown as TrendingDownIcon, */ // Reserved for trend indicators
  /* Assessment as AssessmentIcon, */ // Reserved for analytics features
  /* Fullscreen as FullscreenIcon, */ // Reserved for fullscreen mode
  /* Download as DownloadIcon */ // Reserved for export functionality
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import useOptionChain from '../hooks/useOptionChain';
import '../styles/OptionChainOverrides.css';

const EnhancedOptionChainPage = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  // const isTablet = useMediaQuery(theme.breakpoints.down('md')); // Reserved for tablet responsive features

  // Option chain hook
  const {
    optionChainData,
    futuresData,
    loading,
    error,
    selectedExpiry,
    setSelectedExpiry,
    getLivePrice,
    getLivePriceData,
    getOptionMetrics,
    getATMStrikes,
    refresh,
    wsConnected,
    expiryDates,
    spotPrice
  } = useOptionChain(symbol);

  // UI State
  const [activeTab, setActiveTab] = useState(0);
  const [showOnlyATM, setShowOnlyATM] = useState(false);
  const [atmRange, setATMRange] = useState(5);

  // Get option metrics
  const optionMetrics = getOptionMetrics();
  const atmStrikes = getATMStrikes(atmRange);

  // ULTRA HIGH CONTRAST - MAXIMUM VISIBILITY (Based on dashboard pattern)
  const colors = {
    call: {
      bg: theme.palette.mode === 'dark' ? '#000000' : '#e8f8e8',
      text: '#ffffff',
      profit: '#00ff00',
      border: '#00ff00',
      headerText: '#ffffff'
    },
    put: {
      bg: theme.palette.mode === 'dark' ? '#000000' : '#f8e8e8',
      text: '#ffffff',
      profit: '#ff4444',
      border: '#ff4444',  
      headerText: '#ffffff'
    },
    atm: {
      bg: theme.palette.mode === 'dark' ? '#000000' : '#fff0cc',
      border: '#ffaa00',
      text: '#ffffff',
      headerText: '#ffffff'
    },
    itm: {
      bg: theme.palette.mode === 'dark' ? '#000000' : '#f0e8f0',
      text: '#ffffff'
    },
    otm: {
      bg: theme.palette.mode === 'dark' ? '#000000' : '#e8f0f8',
      text: '#ffffff'
    },
    header: theme.palette.mode === 'dark' ? '#000000' : '#ffffff',
    neutral: '#ffffff',
    positive: '#00ff00',
    negative: '#ff4444',
    primaryText: '#ffffff',
    secondaryText: '#ffffff',
    strongText: '#ffffff'
  };

  // Calculate strike color
  const getStrikeColor = (strike, currentSpotPrice, allStrikes) => {
    if (!currentSpotPrice) return colors.otm;
    
    // Find the exact ATM strike (closest to spot price)
    const atmStrike = allStrikes?.reduce((prev, curr) => 
      Math.abs(curr - currentSpotPrice) < Math.abs(prev - currentSpotPrice) ? curr : prev
    );
    
    if (strike === atmStrike) return colors.atm; // Exact ATM strike
    if (strike < currentSpotPrice) return colors.itm; // In the money for calls
    return colors.otm; // Out of the money
  };

  // Format functions
  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '–';
    return `₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined) return '–';
    return `${Number(value).toFixed(2)}%`;
  };

  const formatVolume = (volume) => {
    if (!volume || volume === 0) return '0';
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  // Render option chain table
  const renderOptionChainTable = () => {
    if (!optionChainData) return null;

    const strikes = showOnlyATM ? atmStrikes : (optionChainData.strike_prices || []);
    const options = optionChainData.options || {};

    return (
      <div className="option-chain-container">
        <TableContainer 
          component={Paper} 
          className="option-chain-table-container"
          sx={{ 
            maxHeight: '70vh',
            backgroundColor: colors.header,
            color: colors.primaryText,
            '& .MuiPaper-root': {
              backgroundColor: colors.header,
              color: colors.primaryText
            }
          }}
        >
        <Table 
          stickyHeader 
          size={isMobile ? 'small' : 'medium'}
          className="option-chain-table"
        >
          <TableHead>
            <TableRow>
              <TableCell 
                align="center" 
                colSpan={5}
                className="option-chain-header-call"
              >
                CALLS
              </TableCell>
              <TableCell 
                align="center"
                className="option-chain-header-strike"
              >
                STRIKE
              </TableCell>
              <TableCell 
                align="center" 
                colSpan={5}
                className="option-chain-header-put"
              >
                PUTS
              </TableCell>
            </TableRow>
            <TableRow sx={{ backgroundColor: colors.header, borderBottom: '3px solid #666' }}>
              {/* Call headers */}
              <TableCell align="right" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.call.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>LTP</TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.call.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>CHG</TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.call.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>%CHG</TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.call.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>VOL</TableCell>
              <TableCell align="right" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.call.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>OI</TableCell>
              
              {/* Strike */}
              <TableCell align="center" sx={{ 
                fontWeight: '900', 
                fontSize: '1.2rem', 
                color: colors.strongText,
                py: 2,
                borderBottom: `4px solid ${colors.atm.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>PRICE</TableCell>
              
              {/* Put headers */}
              <TableCell align="left" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.put.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>OI</TableCell>
              <TableCell align="left" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.put.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>VOL</TableCell>
              <TableCell align="left" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.put.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>%CHG</TableCell>
              <TableCell align="left" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.put.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>CHG</TableCell>
              <TableCell align="left" sx={{ 
                fontWeight: '900', 
                color: colors.strongText, 
                fontSize: '1.1rem',
                py: 2,
                borderBottom: `3px solid ${colors.put.border}`,
                textShadow: theme.palette.mode === 'dark' ? '2px 2px 4px rgba(0,0,0,0.8)' : '1px 1px 2px rgba(255,255,255,0.8)'
              }}>LTP</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {strikes.map((strike, index) => {
              const strikeOptions = options[strike] || {};
              const callOption = strikeOptions.CE;
              const putOption = strikeOptions.PE;
              
              // Get live price from WebSocket or fallback to backend market data
              const callLTP = callOption ? (
                getLivePrice(callOption.instrument_key) || 
                callOption.market_data?.ltp || 
                0
              ) : null;
              
              const putLTP = putOption ? (
                getLivePrice(putOption.instrument_key) || 
                putOption.market_data?.ltp || 
                0
              ) : null;
              
              // Get price data from WebSocket or fallback to backend market data
              const callData = callOption ? (
                getLivePriceData(callOption.instrument_key) || 
                callOption.market_data || 
                {}
              ) : null;
              
              const putData = putOption ? (
                getLivePriceData(putOption.instrument_key) || 
                putOption.market_data || 
                {}
              ) : null;
              
              const strikeColor = getStrikeColor(strike, spotPrice, strikes);
              const isATM = strikeColor === colors.atm;
              
              return (
                <TableRow 
                  key={strike}
                  sx={{
                    backgroundColor: isATM 
                      ? colors.atm.bg 
                      : index % 2 === 0 
                        ? strikeColor.bg 
                        : theme.palette.mode === 'dark' 
                          ? 'rgba(255, 255, 255, 0.02)' 
                          : 'rgba(0, 0, 0, 0.02)',
                    borderLeft: isATM ? `3px solid ${colors.atm.border}` : `2px solid ${strikeColor.border || 'transparent'}`,
                    borderRight: isATM ? `3px solid ${colors.atm.border}` : `2px solid ${strikeColor.border || 'transparent'}`,
                    borderTop: isATM ? `3px solid ${colors.atm.border}` : 'none',
                    borderBottom: isATM ? `3px solid ${colors.atm.border}` : `1px solid ${theme.palette.mode === 'dark' 
                      ? 'rgba(255, 255, 255, 0.1)' 
                      : 'rgba(0, 0, 0, 0.1)'}`,
                    '&:hover': {
                      backgroundColor: isATM 
                        ? colors.atm.bg 
                        : theme.palette.mode === 'dark' 
                          ? 'rgba(255, 255, 255, 0.12)' 
                          : 'rgba(0, 0, 0, 0.06)',
                      transform: 'scale(1.002)',
                      transition: 'all 0.15s ease',
                      boxShadow: theme.palette.mode === 'dark' 
                        ? '0 4px 12px rgba(255, 255, 255, 0.15)' 
                        : '0 4px 12px rgba(0, 0, 0, 0.15)',
                      zIndex: 1
                    },
                    ...(isATM && {
                      fontWeight: 'bold',
                      '& .MuiTableCell-root': {
                        color: colors.atm.text,
                        fontWeight: 'bold'
                      }
                    })
                  }}
                >
                  {/* Call data */}
                  <TableCell align="right">
                    <span className="option-chain-cell-ltp">
                      {callLTP !== null ? formatCurrency(callLTP) : '–'}
                    </span>
                  </TableCell>
                  <TableCell align="right">
                    <span className={callData?.change && callData?.change !== 0 ? 
                      (callData.change >= 0 ? 'option-chain-cell-change-positive' : 'option-chain-cell-change-negative') 
                      : 'option-chain-cell-neutral'}>
                      {callData?.change !== undefined ? 
                        `${callData.change >= 0 ? '+' : ''}${callData.change.toFixed(2)}` : '0.00'}
                    </span>
                  </TableCell>
                  <TableCell align="right">
                    <span className={callData?.change_percent && callData?.change_percent !== 0 ? 
                      (callData.change_percent >= 0 ? 'option-chain-cell-change-positive' : 'option-chain-cell-change-negative') 
                      : 'option-chain-cell-neutral'}>
                      {callData?.change_percent !== undefined ? 
                        formatPercent(callData.change_percent) : '0.00%'}
                    </span>
                  </TableCell>
                  <TableCell align="right">
                    <span className="option-chain-cell-neutral">
                      {callData?.volume !== undefined ? formatVolume(callData.volume) : '0'}
                    </span>
                  </TableCell>
                  <TableCell align="right">
                    <span className="option-chain-cell-neutral">–</span>
                  </TableCell>
                  
                  {/* Strike price */}
                  <TableCell 
                    align="center"
                    sx={{ 
                      fontWeight: 'bold',
                      fontSize: '1.1rem',
                      backgroundColor: strikeColor.bg,
                      borderLeft: `3px solid ${strikeColor.border || 'transparent'}`,
                      borderRight: `3px solid ${strikeColor.border || 'transparent'}`,
                      color: strikeColor.text,
                      minWidth: 100,
                      position: 'sticky',
                      left: '50%',
                      zIndex: 1
                    }}
                  >
                    <Typography variant="body1" sx={{ fontWeight: 'bold', fontSize: '1rem' }}>
                      {strike.toLocaleString('en-IN')}{isATM && ' (ATM)'}
                    </Typography>
                  </TableCell>
                  
                  {/* Put data */}
                  <TableCell align="left">
                    <span className="option-chain-cell-neutral">–</span>
                  </TableCell>
                  <TableCell align="left">
                    <span className="option-chain-cell-neutral">
                      {putData?.volume !== undefined ? formatVolume(putData.volume) : '0'}
                    </span>
                  </TableCell>
                  <TableCell align="left">
                    <span className={putData?.change_percent && putData?.change_percent !== 0 ? 
                      (putData.change_percent >= 0 ? 'option-chain-cell-change-positive' : 'option-chain-cell-change-negative') 
                      : 'option-chain-cell-neutral'}>
                      {putData?.change_percent !== undefined ? 
                        formatPercent(putData.change_percent) : '0.00%'}
                    </span>
                  </TableCell>
                  <TableCell align="left">
                    <span className={putData?.change && putData?.change !== 0 ? 
                      (putData.change >= 0 ? 'option-chain-cell-change-positive' : 'option-chain-cell-change-negative') 
                      : 'option-chain-cell-neutral'}>
                      {putData?.change !== undefined ? 
                        `${putData.change >= 0 ? '+' : ''}${putData.change.toFixed(2)}` : '0.00'}
                    </span>
                  </TableCell>
                  <TableCell align="left">
                    <span className="option-chain-cell-ltp">
                      {putLTP !== null ? formatCurrency(putLTP) : '–'}
                    </span>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      </div>
    );
  };

  // Render futures table
  const renderFuturesTable = () => {
    if (!futuresData.length) {
      return (
        <Alert severity="info" sx={{ m: 2 }}>
          No futures data available for {symbol}
        </Alert>
      );
    }

    return (
      <TableContainer component={Paper} sx={{ m: 2 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold' }}>Contract</TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>LTP</TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>Change</TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>%Change</TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>Volume</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Expiry</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {futuresData.map((future, index) => {
              const ltp = getLivePrice(future.instrument_key);
              const priceData = getLivePriceData(future.instrument_key);
              
              return (
                <TableRow key={index} sx={{ '&:hover': { backgroundColor: theme.palette.action.hover } }}>
                  <TableCell>
                    <Box>
                      <Typography variant="body1" fontWeight="bold">
                        {future.trading_symbol}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Lot: {future.lot_size}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body1" fontWeight="bold">
                      {formatCurrency(ltp)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography 
                      variant="body2" 
                      color={priceData?.change >= 0 ? 'success.main' : 'error.main'}
                    >
                      {priceData?.change ? `${priceData.change >= 0 ? '+' : ''}${priceData.change.toFixed(2)}` : '–'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography 
                      variant="body2" 
                      color={priceData?.change_percent >= 0 ? 'success.main' : 'error.main'}
                    >
                      {priceData?.change_percent ? formatPercent(priceData.change_percent) : '–'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {priceData?.volume ? formatVolume(priceData.volume) : '–'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {new Date(future.expiry).toLocaleDateString('en-IN')}
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  if (loading && !optionChainData) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Box display="flex" justifyContent="center" alignItems="center" height="50vh">
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ ml: 2 }}>
            Loading option chain for {symbol}...
          </Typography>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button variant="contained" onClick={() => navigate(-1)}>
          Go Back
        </Button>
      </Container>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, backgroundColor: theme.palette.background.default, minHeight: '100vh' }}>
      {/* Header */}
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar>
          <IconButton onClick={() => navigate(-1)} sx={{ mr: 2 }}>
            <ArrowBackIcon />
          </IconButton>
          
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h5" component="div" sx={{ fontWeight: 'bold' }}>
              {symbol} Option Chain
              {wsConnected && (
                <Chip 
                  label="LIVE" 
                  size="small" 
                  color="success"
                  sx={{ 
                    ml: 1,
                    fontWeight: 'bold'
                  }} 
                />
              )}
            </Typography>
            {spotPrice && (
              <Typography variant="subtitle1" color="text.secondary">
                Spot: {formatCurrency(spotPrice)}
              </Typography>
            )}
          </Box>

          <Stack direction="row" spacing={1}>
            <Tooltip title="Refresh Data">
              <IconButton onClick={refresh} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 2 }}>
        {/* Summary Cards */}
        {optionChainData && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} sm={4} md={2}>
              <Card>
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" color="text.secondary">Spot Price</Typography>
                  <Typography variant="h6" color="primary">{formatCurrency(spotPrice)}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={4} md={2}>
              <Card>
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" color="text.secondary">Strikes</Typography>
                  <Typography variant="h6">{optionChainData.total_strikes}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={4} md={2}>
              <Card>
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" color="text.secondary">Expiries</Typography>
                  <Typography variant="h6">{optionChainData.total_expiries}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={4} md={2}>
              <Card>
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" color="text.secondary">Futures</Typography>
                  <Typography variant="h6">{futuresData.length}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={4} md={2}>
              <Card>
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" color="text.secondary">PCR</Typography>
                  <Typography 
                    variant="h6" 
                    color={optionMetrics?.putCallRatio > 1 ? 'error.main' : 'success.main'}
                  >
                    {optionMetrics?.putCallRatio?.toFixed(2) || '–'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={4} md={2}>
              <Card>
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" color="text.secondary">Max Pain</Typography>
                  <Typography variant="h6" color="warning.main">
                    {optionMetrics?.maxPainStrike || '–'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Controls */}
        <Box sx={{ mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            {/* Expiry Selection */}
            <Grid item xs={12} md={8}>
              {expiryDates?.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Select Expiry:
                  </Typography>
                  <ToggleButtonGroup
                    value={selectedExpiry}
                    exclusive
                    onChange={(e, value) => value && setSelectedExpiry(value)}
                    size="small"
                  >
                    {expiryDates.slice(0, 8).map((expiry) => (
                      <ToggleButton key={expiry} value={expiry}>
                        {new Date(expiry).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short'
                        })}
                      </ToggleButton>
                    ))}
                  </ToggleButtonGroup>
                </Box>
              )}
            </Grid>

            {/* View Controls */}
            <Grid item xs={12} md={4}>
              <Stack direction="row" spacing={1} justifyContent="flex-end">
                <Button
                  variant={showOnlyATM ? "contained" : "outlined"}
                  size="small"
                  onClick={() => setShowOnlyATM(!showOnlyATM)}
                >
                  ATM Only
                </Button>
                <ToggleButtonGroup
                  value={atmRange}
                  exclusive
                  onChange={(e, value) => value && setATMRange(value)}
                  size="small"
                >
                  <ToggleButton value={3}>±3</ToggleButton>
                  <ToggleButton value={5}>±5</ToggleButton>
                  <ToggleButton value={10}>±10</ToggleButton>
                </ToggleButtonGroup>
              </Stack>
            </Grid>
          </Grid>
        </Box>

        {/* Tabs */}
        <Box sx={{ mb: 2 }}>
          <Tabs 
            value={activeTab} 
            onChange={(e, value) => setActiveTab(value)}
            variant={isMobile ? 'fullWidth' : 'standard'}
          >
            <Tab 
              label="Option Chain" 
              icon={<OptionsIcon />} 
              iconPosition="start"
            />
            <Tab 
              label="Futures" 
              icon={<FuturesIcon />} 
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Content */}
        <Box>
          {activeTab === 0 && renderOptionChainTable()}
          {activeTab === 1 && renderFuturesTable()}
        </Box>
      </Container>
    </Box>
  );
};

export default EnhancedOptionChainPage;