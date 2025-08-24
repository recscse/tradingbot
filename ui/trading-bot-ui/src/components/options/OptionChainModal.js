// components/options/OptionChainModal.js - Professional Bloomberg-style Option Chain Modal
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  ToggleButtonGroup,
  ToggleButton,
  useTheme,
  useMediaQuery,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Close as CloseIcon,
  ShowChart as ShowChartIcon,
  Timeline as TimelineIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import useOptionChain from '../../hooks/useOptionChain';

const OptionChainModal = ({ 
  open, 
  onClose, 
  symbol, 
  stockData 
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  // Use option chain hook - only use valid instrument_key, fallback to symbol
  const isValidInstrumentKey = stockData?.instrument_key && stockData.instrument_key.includes('|') && !stockData.instrument_key.endsWith('_KEY');
  const instrumentKeyOrSymbol = open ? (isValidInstrumentKey ? stockData.instrument_key : symbol) : null;
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
    refresh,
    wsConnected,
    expiryDates,
    spotPrice
  } = useOptionChain(instrumentKeyOrSymbol);
  
  // State
  const [activeTab, setActiveTab] = useState(0);

  // Bloomberg-inspired colors
  const colors = {
    call: {
      bg: '#e8f5e8',
      text: '#2e7d32',
      profit: '#1b5e20'
    },
    put: {
      bg: '#fde7e7',
      text: '#d32f2f',
      profit: '#c62828'
    },
    atm: {
      bg: '#fff3e0',
      border: '#ff9800',
      text: '#e65100',
      highlight: '#ffecb3'
    },
    itm: {
      bg: '#f3e5f5',
      text: '#7b1fa2'
    },
    otm: {
      bg: '#e1f5fe',
      text: '#0277bd'
    }
  };

  // Get option metrics for display
  const optionMetrics = getOptionMetrics();

  // Calculate strike color based on spot price
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

  // Format currency
  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '–';
    return `₹${Number(value).toFixed(2)}`;
  };

  // Render option chain table
  const renderOptionChainTable = () => {
    if (!optionChainData) return null;

    const strikes = optionChainData.strike_prices || [];
    const options = optionChainData.options || {};
    const currentSpotPrice = spotPrice;

    return (
      <TableContainer 
        component={Paper} 
        sx={{ 
          maxHeight: isMobile ? '60vh' : '70vh',
          backgroundColor: '#fafafa'
        }}
      >
        <Table 
          stickyHeader 
          size={isMobile ? 'small' : 'medium'}
          sx={{ minWidth: isMobile ? 300 : 800 }}
        >
          <TableHead>
            <TableRow>
              <TableCell 
                align="center" 
                colSpan={5}
                sx={{ 
                  backgroundColor: colors.call.bg,
                  fontWeight: 'bold',
                  fontSize: '0.875rem'
                }}
              >
                CALLS
              </TableCell>
              <TableCell 
                align="center"
                sx={{ 
                  backgroundColor: colors.atm.bg,
                  fontWeight: 'bold',
                  minWidth: 80
                }}
              >
                STRIKE
              </TableCell>
              <TableCell 
                align="center" 
                colSpan={5}
                sx={{ 
                  backgroundColor: colors.put.bg,
                  fontWeight: 'bold',
                  fontSize: '0.875rem'
                }}
              >
                PUTS
              </TableCell>
            </TableRow>
            <TableRow>
              {/* Call headers */}
              <TableCell align="right" sx={{ fontSize: '0.75rem' }}>LTP</TableCell>
              <TableCell align="right" sx={{ fontSize: '0.75rem' }}>CHG</TableCell>
              <TableCell align="right" sx={{ fontSize: '0.75rem' }}>IV</TableCell>
              <TableCell align="right" sx={{ fontSize: '0.75rem' }}>VOL</TableCell>
              <TableCell align="right" sx={{ fontSize: '0.75rem' }}>OI</TableCell>
              
              {/* Strike */}
              <TableCell align="center" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>STRIKE</TableCell>
              
              {/* Put headers */}
              <TableCell align="left" sx={{ fontSize: '0.75rem' }}>OI</TableCell>
              <TableCell align="left" sx={{ fontSize: '0.75rem' }}>VOL</TableCell>
              <TableCell align="left" sx={{ fontSize: '0.75rem' }}>IV</TableCell>
              <TableCell align="left" sx={{ fontSize: '0.75rem' }}>CHG</TableCell>
              <TableCell align="left" sx={{ fontSize: '0.75rem' }}>LTP</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {strikes.map((strike) => {
              const strikeOptions = options[strike] || {};
              const callOption = strikeOptions.CE;
              const putOption = strikeOptions.PE;
              
              const callLiveData = callOption ? getLivePriceData(callOption.instrument_key) : null;
              const putLiveData = putOption ? getLivePriceData(putOption.instrument_key) : null;
              
              const callLTP = callLiveData?.ltp || (callOption?.market_data?.ltp);
              const putLTP = putLiveData?.ltp || (putOption?.market_data?.ltp);
              
              const callChange = callLiveData?.change || (callOption?.market_data?.change) || 0;
              const putChange = putLiveData?.change || (putOption?.market_data?.change) || 0;
              
              const callChangePercent = callLiveData?.change_percent || (callOption?.market_data?.change_percent) || 0;
              const putChangePercent = putLiveData?.change_percent || (putOption?.market_data?.change_percent) || 0;
              
              const callVolume = callLiveData?.volume || (callOption?.market_data?.volume) || 0;
              const putVolume = putLiveData?.volume || (putOption?.market_data?.volume) || 0;
              
              const callOI = callLiveData?.oi || (callOption?.market_data?.oi) || 0;
              const putOI = putLiveData?.oi || (putOption?.market_data?.oi) || 0;
              
              const callIV = callOption?.option_greeks?.iv || 0;
              const putIV = putOption?.option_greeks?.iv || 0;
              
              const strikeColor = getStrikeColor(strike, currentSpotPrice, strikes);
              
              const isATM = strikeColor === colors.atm;
              
              return (
                <TableRow 
                  key={strike}
                  sx={{
                    backgroundColor: isATM ? colors.atm.highlight : strikeColor.bg,
                    borderTop: isATM ? `3px solid ${colors.atm.border}` : 'none',
                    borderBottom: isATM ? `3px solid ${colors.atm.border}` : 'none',
                    borderLeft: isATM ? `2px solid ${colors.atm.border}` : 'none',
                    borderRight: isATM ? `2px solid ${colors.atm.border}` : 'none',
                    '&:hover': {
                      backgroundColor: isATM ? colors.atm.highlight : theme.palette.action.hover
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
                    <Typography variant="body2" fontWeight="medium">
                      {formatCurrency(callLTP)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography 
                      variant="body2" 
                      color={callChange >= 0 ? 'success.main' : 'error.main'}
                      sx={{ fontSize: '0.75rem' }}
                    >
                      {callChange !== 0 ? `${callChange >= 0 ? '+' : ''}${callChange.toFixed(2)}` : '–'}
                    </Typography>
                    <Typography 
                      variant="caption" 
                      color={callChangePercent >= 0 ? 'success.main' : 'error.main'}
                      sx={{ fontSize: '0.6rem', display: 'block' }}
                    >
                      {callChangePercent !== 0 ? `(${callChangePercent >= 0 ? '+' : ''}${callChangePercent.toFixed(1)}%)` : ''}
                    </Typography>
                  </TableCell>
                  <TableCell align="right" sx={{ fontSize: '0.75rem' }}>
                    {callIV > 0 ? `${callIV.toFixed(1)}%` : '–'}
                  </TableCell>
                  <TableCell align="right" sx={{ fontSize: '0.75rem' }}>
                    {callVolume > 0 ? (callVolume > 1000 ? `${(callVolume/1000).toFixed(1)}K` : callVolume.toString()) : '–'}
                  </TableCell>
                  <TableCell align="right" sx={{ fontSize: '0.75rem' }}>
                    {callOI > 0 ? (callOI > 1000 ? `${(callOI/1000).toFixed(1)}K` : callOI.toString()) : '–'}
                  </TableCell>
                  
                  {/* Strike price */}
                  <TableCell 
                    align="center"
                    sx={{ 
                      fontWeight: isATM ? 'bolder' : 'bold',
                      borderLeft: `2px solid ${strikeColor.border || 'transparent'}`,
                      borderRight: `2px solid ${strikeColor.border || 'transparent'}`,
                      fontSize: isATM ? '1rem' : '0.875rem',
                      backgroundColor: isATM ? colors.atm.highlight : 'inherit',
                      color: isATM ? colors.atm.text : 'inherit'
                    }}
                  >
                    {strike}{isATM && ' (ATM)'}
                  </TableCell>
                  
                  {/* Put data */}
                  <TableCell align="left" sx={{ fontSize: '0.75rem' }}>
                    {putOI > 0 ? (putOI > 1000 ? `${(putOI/1000).toFixed(1)}K` : putOI.toString()) : '–'}
                  </TableCell>
                  <TableCell align="left" sx={{ fontSize: '0.75rem' }}>
                    {putVolume > 0 ? (putVolume > 1000 ? `${(putVolume/1000).toFixed(1)}K` : putVolume.toString()) : '–'}
                  </TableCell>
                  <TableCell align="left" sx={{ fontSize: '0.75rem' }}>
                    {putIV > 0 ? `${putIV.toFixed(1)}%` : '–'}
                  </TableCell>
                  <TableCell align="left">
                    <Typography 
                      variant="body2" 
                      color={putChange >= 0 ? 'success.main' : 'error.main'}
                      sx={{ fontSize: '0.75rem' }}
                    >
                      {putChange !== 0 ? `${putChange >= 0 ? '+' : ''}${putChange.toFixed(2)}` : '–'}
                    </Typography>
                    <Typography 
                      variant="caption" 
                      color={putChangePercent >= 0 ? 'success.main' : 'error.main'}
                      sx={{ fontSize: '0.6rem', display: 'block' }}
                    >
                      {putChangePercent !== 0 ? `(${putChangePercent >= 0 ? '+' : ''}${putChangePercent.toFixed(1)}%)` : ''}
                    </Typography>
                  </TableCell>
                  <TableCell align="left">
                    <Typography variant="body2" fontWeight="medium">
                      {formatCurrency(putLTP)}
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

  // Render futures table
  const renderFuturesTable = () => {
    if (!futuresData.length) {
      return (
        <Alert severity="info">
          No futures data available for {symbol}
        </Alert>
      );
    }

    return (
      <TableContainer component={Paper}>
        <Table size={isMobile ? 'small' : 'medium'}>
          <TableHead>
            <TableRow>
              <TableCell>Contract</TableCell>
              <TableCell align="right">LTP</TableCell>
              <TableCell align="right">Change</TableCell>
              <TableCell align="right">Volume</TableCell>
              <TableCell>Expiry</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {futuresData.map((future, index) => {
              const ltp = getLivePrice(future.instrument_key);
              
              return (
                <TableRow key={index}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {future.trading_symbol}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Lot: {future.lot_size}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {formatCurrency(ltp)}
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.secondary">
                      –
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.secondary">
                      –
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {new Date(future.expiry).toLocaleDateString()}
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

  if (!open) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xl"
      fullWidth
      fullScreen={isMobile}
      PaperProps={{
        sx: {
          height: isMobile ? '100%' : '90vh',
          backgroundColor: '#f5f5f5'
        }
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#1a1a1a',
          color: 'white',
          py: 1
        }}
      >
        <Box>
          <Typography variant="h6" component="div">
            {symbol} Option Chain
            {wsConnected && (
              <Chip 
                label="LIVE" 
                size="small" 
                sx={{ 
                  ml: 1,
                  backgroundColor: '#00ff00',
                  color: 'black',
                  fontWeight: 'bold',
                  fontSize: '0.6rem'
                }} 
              />
            )}
          </Typography>
          {spotPrice && (
            <Typography variant="body2" color="rgba(255,255,255,0.7)">
              Spot: {formatCurrency(spotPrice)}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh Data">
            <IconButton 
              onClick={refresh} 
              sx={{ color: 'white' }}
              disabled={loading}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <IconButton onClick={onClose} sx={{ color: 'white' }}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        {/* Header Stats */}
        {optionChainData && (
          <Box sx={{ p: 2, backgroundColor: 'white' }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={2.4}>
                <Card>
                  <CardContent sx={{ py: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Spot Price
                    </Typography>
                    <Typography variant="h6">
                      {formatCurrency(spotPrice)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={2.4}>
                <Card>
                  <CardContent sx={{ py: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Total Strikes
                    </Typography>
                    <Typography variant="h6">
                      {optionChainData.total_strikes}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={2.4}>
                <Card>
                  <CardContent sx={{ py: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Expiries
                    </Typography>
                    <Typography variant="h6">
                      {optionChainData.total_expiries}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={2.4}>
                <Card>
                  <CardContent sx={{ py: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Futures
                    </Typography>
                    <Typography variant="h6">
                      {futuresData.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={2.4}>
                <Card>
                  <CardContent sx={{ py: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      PCR
                    </Typography>
                    <Typography variant="h6" color={optionMetrics?.putCallRatio > 1 ? 'error.main' : 'success.main'}>
                      {optionMetrics?.putCallRatio?.toFixed(2) || '–'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Expiry Selection */}
        {expiryDates?.length > 0 && (
          <Box sx={{ p: 2, backgroundColor: 'white', borderBottom: '1px solid #e0e0e0' }}>
            <Typography variant="subtitle2" gutterBottom>
              Select Expiry:
            </Typography>
            <ToggleButtonGroup
              value={selectedExpiry}
              exclusive
              onChange={(e, value) => value && setSelectedExpiry(value)}
              size="small"
            >
              {expiryDates.slice(0, 6).map((expiry) => (
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

        {/* Tabs */}
        <Box sx={{ backgroundColor: 'white' }}>
          <Tabs 
            value={activeTab} 
            onChange={(e, value) => setActiveTab(value)}
            variant={isMobile ? 'fullWidth' : 'standard'}
          >
            <Tab 
              label="Option Chain" 
              icon={<ShowChartIcon />} 
              iconPosition="start"
            />
            <Tab 
              label="Futures" 
              icon={<TimelineIcon />} 
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Content */}
        <Box sx={{ p: 2 }}>
          {loading ? (
            <Box display="flex" justifyContent="center" p={4}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : (
            <>
              {activeTab === 0 && renderOptionChainTable()}
              {activeTab === 1 && renderFuturesTable()}
            </>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ backgroundColor: 'white', borderTop: '1px solid #e0e0e0' }}>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default OptionChainModal;