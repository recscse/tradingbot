// components/common/StocksListOptimized.jsx - ULTRA-OPTIMIZED FOR REAL-TIME PERFORMANCE
import React, { memo, useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Skeleton,
  useTheme,
} from "@mui/material";
import { useSymbolPrice } from '../../store/marketStore';

// 🚀 ULTRA-OPTIMIZED: Individual stock row with React.memo and Zustand subscription
const StockRow = memo(({ symbol, showVolume = true, showSector = false, compact = false }) => {
  const theme = useTheme();
  
  // 🚀 GRANULAR SUBSCRIPTION: Only this row re-renders when this symbol updates
  const stock = useSymbolPrice(symbol);
  
  
  // Skip rendering if no data
  if (!stock) {
    return (
      <TableRow>
        <TableCell colSpan={showVolume ? 6 : 5}>
          <Skeleton variant="rectangular" height={compact ? 30 : 40} />
        </TableCell>
      </TableRow>
    );
  }
  
  const isPositive = stock.change >= 0;
  const changeColor = isPositive 
    ? theme.palette.success.main 
    : theme.palette.error.main;
  
  return (
    <TableRow
      sx={{
        height: compact ? 35 : 45,
        '&:hover': {
          backgroundColor: theme.palette.action.hover,
        },
        transition: 'background-color 0.1s ease',
      }}
    >
      {/* Symbol */}
      <TableCell sx={{ py: compact ? 0.5 : 1 }}>
        <Box>
          <Typography variant={compact ? "body2" : "body1"} fontWeight="bold">
            {stock.symbol}
          </Typography>
          {showSector && (
            <Typography variant="caption" color="text.secondary">
              {stock.sector}
            </Typography>
          )}
        </Box>
      </TableCell>
      
      {/* LTP */}
      <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
        <Typography 
          variant={compact ? "body2" : "body1"} 
          fontWeight="bold"
          color={changeColor}
        >
          ₹{stock.ltp.toFixed(2)}
        </Typography>
      </TableCell>
      
      {/* Change */}
      <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
        <Typography 
          variant={compact ? "body2" : "body1"}
          color={changeColor}
          fontWeight="medium"
        >
          {isPositive ? '+' : ''}₹{stock.change.toFixed(2)}
        </Typography>
      </TableCell>
      
      {/* Change % */}
      <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
        <Chip
          label={`${isPositive ? '+' : ''}${stock.change_percent.toFixed(2)}%`}
          size={compact ? "small" : "medium"}
          sx={{
            backgroundColor: isPositive 
              ? theme.palette.success.light 
              : theme.palette.error.light,
            color: isPositive 
              ? theme.palette.success.contrastText 
              : theme.palette.error.contrastText,
            fontWeight: 'bold',
            minWidth: compact ? 60 : 80,
          }}
        />
      </TableCell>
      
      {/* Volume */}
      {showVolume && (
        <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
          <Typography variant={compact ? "caption" : "body2"} color="text.secondary">
            {stock.volume > 1000000 
              ? `${(stock.volume / 1000000).toFixed(1)}M`
              : stock.volume > 1000
              ? `${(stock.volume / 1000).toFixed(1)}K`
              : stock.volume.toString()}
          </Typography>
        </TableCell>
      )}
      
      {/* High/Low */}
      <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
        <Box>
          <Typography variant="caption" color="text.secondary">
            H: ₹{stock.high?.toFixed(2) || '--'}
          </Typography>
          <br />
          <Typography variant="caption" color="text.secondary">
            L: ₹{stock.low?.toFixed(2) || '--'}
          </Typography>
        </Box>
      </TableCell>
    </TableRow>
  );
});

StockRow.displayName = 'StockRow';

// 🚀 OPTIMIZED: Loading skeleton row
const SkeletonRow = memo(({ showVolume = true, compact = false }) => (
  <TableRow sx={{ height: compact ? 35 : 45 }}>
    <TableCell><Skeleton width={80} height={compact ? 20 : 24} /></TableCell>
    <TableCell align="right"><Skeleton width={60} height={compact ? 20 : 24} /></TableCell>
    <TableCell align="right"><Skeleton width={60} height={compact ? 20 : 24} /></TableCell>
    <TableCell align="right"><Skeleton width={80} height={compact ? 20 : 24} /></TableCell>
    {showVolume && <TableCell align="right"><Skeleton width={50} height={compact ? 20 : 24} /></TableCell>}
    <TableCell align="right"><Skeleton width={70} height={compact ? 20 : 24} /></TableCell>
  </TableRow>
));

SkeletonRow.displayName = 'SkeletonRow';

// 🚀 MAIN COMPONENT: Optimized stocks list
const StocksListOptimized = memo(({
  title,
  symbols = [], // Array of symbol strings to display
  isLoading = false,
  titleIcon = "📊",
  emptyMessage = "No data available",
  maxItems = 20,
  showVolume = true,
  showSector = false,
  compact = false,
  containerHeight = "70vh",
}) => {
  const theme = useTheme();
  
  // 🚀 OPTIMIZED: Memoized symbols list (prevents unnecessary re-renders)
  const displaySymbols = useMemo(() => 
    symbols.slice(0, maxItems), 
    [symbols, maxItems]
  );
  
  // 🚀 OPTIMIZED: Memoized table header
  const tableHeader = useMemo(() => (
    <TableHead>
      <TableRow>
        <TableCell>
          <Typography variant="subtitle2" fontWeight="bold">
            Symbol
          </Typography>
        </TableCell>
        <TableCell align="right">
          <Typography variant="subtitle2" fontWeight="bold">
            LTP
          </Typography>
        </TableCell>
        <TableCell align="right">
          <Typography variant="subtitle2" fontWeight="bold">
            Change
          </Typography>
        </TableCell>
        <TableCell align="right">
          <Typography variant="subtitle2" fontWeight="bold">
            Change %
          </Typography>
        </TableCell>
        {showVolume && (
          <TableCell align="right">
            <Typography variant="subtitle2" fontWeight="bold">
              Volume
            </Typography>
          </TableCell>
        )}
        <TableCell align="right">
          <Typography variant="subtitle2" fontWeight="bold">
            H/L
          </Typography>
        </TableCell>
      </TableRow>
    </TableHead>
  ), [showVolume]);
  
  return (
    <Card
      elevation={3}
      sx={{
        height: containerHeight,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <CardContent sx={{ pb: 1, flexShrink: 0 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <Typography variant="h6" component="span">
            {titleIcon}
          </Typography>
          <Typography variant="h6" fontWeight="bold" color="primary">
            {title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            ({displaySymbols.length} items)
          </Typography>
        </Box>
      </CardContent>
      
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <TableContainer 
          component={Paper} 
          sx={{ 
            height: '100%',
            '& .MuiTableContainer-root': {
              borderRadius: 0,
            }
          }}
        >
          <Table 
            stickyHeader 
            size={compact ? "small" : "medium"}
            sx={{
              '& .MuiTableCell-head': {
                backgroundColor: theme.palette.grey[100],
                fontWeight: 'bold',
              },
            }}
          >
            {tableHeader}
            <TableBody>
              {isLoading ? (
                // Loading state
                Array.from({ length: Math.min(maxItems, 10) }).map((_, index) => (
                  <SkeletonRow 
                    key={`skeleton-${index}`}
                    showVolume={showVolume}
                    compact={compact}
                  />
                ))
              ) : displaySymbols.length > 0 ? (
                // 🚀 OPTIMIZED: Each row is independently subscribed and memoized
                displaySymbols.map((symbol) => (
                  <StockRow
                    key={symbol}
                    symbol={symbol}
                    showVolume={showVolume}
                    showSector={showSector}
                    compact={compact}
                  />
                ))
              ) : (
                // Empty state
                <TableRow>
                  <TableCell 
                    colSpan={showVolume ? 6 : 5} 
                    align="center"
                    sx={{ py: 4 }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {emptyMessage}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Card>
  );
});

StocksListOptimized.displayName = 'StocksListOptimized';

export default StocksListOptimized;