// components/common/StocksListZeroDelay.js
/**
 * 🚀 ZERO-DELAY Stocks List Component
 * 
 * Ultra-fast stocks list that receives raw market data directly from Upstox
 * without any processing delays. Perfect for real-time trading applications.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Box,
    Typography,
    Chip,
    LinearProgress,
    Tooltip,
    Alert,
    IconButton,
    CircularProgress
} from '@mui/material';
import {
    TrendingUp,
    TrendingDown,
    SignalWifi4Bar,
    SignalWifi0Bar,
    Speed,
    Refresh
} from '@mui/icons-material';
import { green, red, orange, grey } from '@mui/material/colors';
import { useZeroDelayMarketData } from '../../hooks/useZeroDelayMarketData';

const StocksListZeroDelay = ({ 
    stocks = [], 
    maxRows = 100, 
    showLatency = true,
    showPerformanceStats = true,
    onStockClick = null,
    enableAdvancedMetrics = false 
}) => {
    const [processedStocks, setProcessedStocks] = useState([]);
    const [priceChanges, setPriceChanges] = useState({}); // Track price changes for animations
    const [updateCount, setUpdateCount] = useState(0);
    
    // 🚀 Connect to ZERO-DELAY streaming
    const {
        marketData,
        connectionStatus,
        streamingStats,
        latency,
        error,
        isConnected,
        totalInstruments,
        lastUpdate,
        requestStats,
        ping
    } = useZeroDelayMarketData({
        enableStats: showPerformanceStats,
        onDataReceived: useCallback((data) => {
            setUpdateCount(prev => prev + 1);
        }, [])
    });

    // Process and merge stock data with real-time prices
    const processStocksWithPrices = useCallback(() => {
        if (!stocks.length || !marketData || Object.keys(marketData).length === 0) {
            return stocks.map(stock => ({ ...stock, _source: 'static' }));
        }

        const processed = stocks.map(stock => {
            // Try different key formats to match market data
            const possibleKeys = [
                stock.instrument_key,
                stock.instrument_token,
                `NSE_EQ|${stock.symbol}`,
                `NSE_FO|${stock.symbol}`,
                stock.symbol
            ].filter(Boolean);

            let liveData = null;
            let matchedKey = null;

            for (const key of possibleKeys) {
                if (marketData[key]) {
                    liveData = marketData[key];
                    matchedKey = key;
                    break;
                }
            }

            if (liveData) {
                // Track price changes for visual effects
                const currentPrice = parseFloat(liveData.lp || liveData.last_price || 0);
                const previousPrice = processedStocks.find(p => p.symbol === stock.symbol)?.current_price || currentPrice;
                
                if (currentPrice !== previousPrice) {
                    setPriceChanges(prev => ({
                        ...prev,
                        [stock.symbol]: {
                            direction: currentPrice > previousPrice ? 'up' : 'down',
                            timestamp: Date.now()
                        }
                    }));
                }

                return {
                    ...stock,
                    // Price data
                    current_price: currentPrice,
                    last_price: currentPrice,
                    open_price: parseFloat(liveData.op || liveData.open || stock.open_price || 0),
                    high_price: parseFloat(liveData.h || liveData.high || stock.high_price || 0),
                    low_price: parseFloat(liveData.l || liveData.low || stock.low_price || 0),
                    
                    // Change calculations
                    price_change: currentPrice - parseFloat(liveData.op || liveData.open || currentPrice),
                    price_change_percent: liveData.op ? ((currentPrice - parseFloat(liveData.op)) / parseFloat(liveData.op) * 100) : 0,
                    
                    // Volume data
                    volume: parseInt(liveData.v || liveData.volume || 0),
                    
                    // Additional fields
                    instrument_token: liveData.instrument_token || stock.instrument_token,
                    last_trade_time: liveData.ltt || liveData.last_trade_time,
                    
                    // Metadata
                    _matched_key: matchedKey,
                    _live_data_available: true,
                    _source: 'zero_delay',
                    _last_update: marketData._lastUpdate
                };
            }

            return {
                ...stock,
                _live_data_available: false,
                _source: 'static'
            };
        });

        return processed.slice(0, maxRows);
    }, [stocks, marketData, processedStocks, maxRows]);

    // Update processed stocks when market data changes
    useEffect(() => {
        const processed = processStocksWithPrices();
        setProcessedStocks(processed);
    }, [processStocksWithPrices]);

    // Price change indicator component
    const PriceChangeIndicator = ({ stock }) => {
        const change = priceChanges[stock.symbol];
        const isRecent = change && (Date.now() - change.timestamp < 2000); // 2 second highlight
        
        if (!isRecent) return null;
        
        return (
            <Box 
                component="span" 
                sx={{ 
                    animation: 'pulse 1s ease-in-out',
                    '@keyframes pulse': {
                        '0%': { opacity: 1 },
                        '50%': { opacity: 0.5 },
                        '100%': { opacity: 1 }
                    }
                }}
            >
                {change.direction === 'up' ? (
                    <TrendingUp sx={{ color: green[500], fontSize: 16 }} />
                ) : (
                    <TrendingDown sx={{ color: red[500], fontSize: 16 }} />
                )}
            </Box>
        );
    };

    // Format price with proper decimals
    const formatPrice = (price) => {
        return typeof price === 'number' ? price.toFixed(2) : '0.00';
    };

    // Format percentage with color
    const formatPercentage = (percent) => {
        if (typeof percent !== 'number') return '0.00%';
        
        const value = percent.toFixed(2);
        const color = percent >= 0 ? green[600] : red[600];
        
        return (
            <Typography component="span" sx={{ color, fontWeight: 600 }}>
                {percent >= 0 ? '+' : ''}{value}%
            </Typography>
        );
    };

    // Connection status indicator
    const ConnectionStatusIndicator = () => (
        <Box display="flex" alignItems="center" gap={1}>
            <Tooltip title={`Connection: ${connectionStatus} | Latency: ${latency}ms`}>
                <Box display="flex" alignItems="center">
                    {isConnected ? (
                        <SignalWifi4Bar sx={{ color: green[500], fontSize: 20 }} />
                    ) : (
                        <SignalWifi0Bar sx={{ color: red[500], fontSize: 20 }} />
                    )}
                    
                    {showLatency && latency !== null && (
                        <Typography variant="caption" sx={{ ml: 0.5, color: grey[600] }}>
                            {latency}ms
                        </Typography>
                    )}
                </Box>
            </Tooltip>
            
            <Tooltip title="Refresh stats">
                <IconButton size="small" onClick={requestStats}>
                    <Refresh fontSize="small" />
                </IconButton>
            </Tooltip>
            
            <Tooltip title="Test connection latency">
                <IconButton size="small" onClick={ping}>
                    <Speed fontSize="small" />
                </IconButton>
            </Tooltip>
        </Box>
    );

    // Performance stats display
    const PerformanceStats = () => {
        if (!showPerformanceStats || !streamingStats.streaming_active) return null;
        
        return (
            <Box display="flex" gap={2} alignItems="center" mb={2}>
                <Chip 
                    label={`🚀 ZERO-DELAY Active`} 
                    color="success" 
                    size="small" 
                    icon={<Speed />}
                />
                <Chip 
                    label={`${totalInstruments} instruments`} 
                    variant="outlined" 
                    size="small" 
                />
                <Chip 
                    label={`${streamingStats.total_broadcasts || 0} updates`} 
                    variant="outlined" 
                    size="small" 
                />
                <Chip 
                    label={`Avg: ${streamingStats.average_latency_ms || 0}ms`} 
                    variant="outlined" 
                    size="small" 
                    color={streamingStats.average_latency_ms > 10 ? "warning" : "success"}
                />
            </Box>
        );
    };

    if (error) {
        return (
            <Alert severity="error" sx={{ mb: 2 }}>
                ZERO-DELAY streaming error: {error}
            </Alert>
        );
    }

    return (
        <Box>
            {/* Header with connection status and performance */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box>
                    <Typography variant="h6" component="h2">
                        🚀 Ultra-Fast Market Data
                        {isConnected && (
                            <Typography component="span" sx={{ color: green[600], ml: 1, fontSize: '0.8em' }}>
                                LIVE
                            </Typography>
                        )}
                    </Typography>
                    {lastUpdate && (
                        <Typography variant="caption" color="textSecondary">
                            Last update: {new Date(lastUpdate).toLocaleTimeString()} 
                            {updateCount > 0 && ` (${updateCount} updates)`}
                        </Typography>
                    )}
                </Box>
                <ConnectionStatusIndicator />
            </Box>

            <PerformanceStats />

            {/* Loading indicator for initial connection */}
            {connectionStatus === 'connecting' && (
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                    <CircularProgress size={20} />
                    <Typography>Connecting to ZERO-DELAY streaming...</Typography>
                </Box>
            )}

            {/* Stocks table */}
            <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
                <Table stickyHeader size="small" aria-label="stocks table">
                    <TableHead>
                        <TableRow>
                            <TableCell>Symbol</TableCell>
                            <TableCell align="right">Price</TableCell>
                            <TableCell align="right">Change</TableCell>
                            <TableCell align="right">Change %</TableCell>
                            <TableCell align="right">Volume</TableCell>
                            <TableCell align="center">Status</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {processedStocks.map((stock, index) => (
                            <TableRow 
                                key={stock.symbol || index}
                                hover
                                onClick={onStockClick ? () => onStockClick(stock) : undefined}
                                sx={{ 
                                    cursor: onStockClick ? 'pointer' : 'default',
                                    '&:hover': onStockClick ? { backgroundColor: 'rgba(0,0,0,0.04)' } : {}
                                }}
                            >
                                <TableCell component="th" scope="row">
                                    <Box display="flex" alignItems="center" gap={1}>
                                        <Typography variant="body2" fontWeight={600}>
                                            {stock.symbol}
                                        </Typography>
                                        <PriceChangeIndicator stock={stock} />
                                    </Box>
                                    {stock.name && (
                                        <Typography variant="caption" color="textSecondary" display="block">
                                            {stock.name.slice(0, 30)}...
                                        </Typography>
                                    )}
                                </TableCell>
                                
                                <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                        ₹{formatPrice(stock.current_price)}
                                    </Typography>
                                </TableCell>
                                
                                <TableCell align="right">
                                    <Typography 
                                        variant="body2" 
                                        sx={{ 
                                            color: stock.price_change >= 0 ? green[600] : red[600],
                                            fontWeight: 600 
                                        }}
                                    >
                                        {stock.price_change >= 0 ? '+' : ''}
                                        ₹{formatPrice(Math.abs(stock.price_change))}
                                    </Typography>
                                </TableCell>
                                
                                <TableCell align="right">
                                    {formatPercentage(stock.price_change_percent)}
                                </TableCell>
                                
                                <TableCell align="right">
                                    <Typography variant="body2">
                                        {stock.volume?.toLocaleString() || '-'}
                                    </Typography>
                                </TableCell>
                                
                                <TableCell align="center">
                                    {stock._live_data_available ? (
                                        <Tooltip title={`Live data via ${stock._source} | Key: ${stock._matched_key}`}>
                                            <Chip 
                                                label="LIVE" 
                                                color="success" 
                                                size="small" 
                                                sx={{ fontSize: '0.7rem' }}
                                            />
                                        </Tooltip>
                                    ) : (
                                        <Tooltip title="No live data available">
                                            <Chip 
                                                label="STATIC" 
                                                color="default" 
                                                size="small" 
                                                sx={{ fontSize: '0.7rem' }}
                                            />
                                        </Tooltip>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
                
                {processedStocks.length === 0 && (
                    <Box p={4} textAlign="center">
                        <Typography color="textSecondary">
                            No stock data available
                        </Typography>
                    </Box>
                )}
            </TableContainer>
        </Box>
    );
};

export default StocksListZeroDelay;