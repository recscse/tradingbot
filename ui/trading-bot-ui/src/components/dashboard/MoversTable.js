import React, { memo } from "react";
import { 
  Typography, 
  Box, 
  Grid,
  Card,
  CardContent,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  useTheme,
  useMediaQuery,
  Stack,
  Skeleton,
  Tooltip,
  IconButton
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  ShowChart,
  Refresh,
  Info
} from "@mui/icons-material";

const MoversTable = memo(({ stocks = [], isLoading = false, onRefresh, lastUpdated }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  // const isTablet = useMediaQuery(theme.breakpoints.down('md')); // Tablet breakpoint check - reserved for responsive features

  const filtered = stocks.filter((s) => s.open && s.livePrice);
  const movers = filtered.map((s) => ({
    ...s,
    changePercent: ((s.livePrice - s.open) / s.open) * 100,
    changeAmount: s.livePrice - s.open
  }));

  const gainers = movers
    .sort((a, b) => b.changePercent - a.changePercent)
    .slice(0, isMobile ? 5 : 10);
  const losers = movers
    .sort((a, b) => a.changePercent - b.changePercent)
    .slice(0, isMobile ? 5 : 10);

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const getChangeColor = (changePercent) => {
    if (changePercent > 0) return theme.palette.success.main;
    if (changePercent < 0) return theme.palette.error.main;
    return theme.palette.text.secondary;
  };

  const renderMoverCard = (stock, index, isGainer) => (
    <ListItem
      key={stock.symbol || index}
      sx={{
        borderRadius: 2,
        mb: 0.75,
        bgcolor: 'background.paper',
        border: `1px solid ${theme.palette.divider}`,
        minHeight: { xs: 56, sm: 64 }, // Compact but touch-friendly
        '&:hover': {
          bgcolor: 'action.hover',
          transform: 'translateY(-1px)',
          boxShadow: theme.shadows[2],
          borderColor: isGainer ? 'success.main' : 'error.main'
        },
        transition: 'all 0.2s ease',
        px: { xs: 1.25, sm: 1.5 },
        py: { xs: 0.75, sm: 1 },
        cursor: 'pointer'
      }}
    >
      <ListItemAvatar sx={{ minWidth: { xs: 32, sm: 40 } }}>
        <Avatar
          sx={{
            bgcolor: isGainer ? 'success.main' : 'error.main',
            width: { xs: 28, sm: 36 },
            height: { xs: 28, sm: 36 },
            fontSize: { xs: '0.75rem', sm: '0.875rem' }
          }}
        >
          {isGainer ? <TrendingUp fontSize="inherit" /> : <TrendingDown fontSize="inherit" />}
        </Avatar>
      </ListItemAvatar>
      
      <ListItemText
        sx={{ 
          m: 0,
          '& .MuiListItemText-primary': { mb: 0.25 },
          '& .MuiListItemText-secondary': { mb: 0 }
        }}
        primary={
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography 
              variant="body2" 
              fontWeight={700}
              sx={{ 
                fontSize: { xs: '0.8rem', sm: '0.875rem' },
                lineHeight: 1.2,
                color: 'primary.main'
              }}
              noWrap
            >
              {stock.symbol}
            </Typography>
            <Chip
              label={`${stock.changePercent >= 0 ? '+' : ''}${stock.changePercent.toFixed(1)}%`}
              size="small"
              sx={{
                bgcolor: getChangeColor(stock.changePercent),
                color: 'white',
                fontWeight: 700,
                fontSize: { xs: '0.65rem', sm: '0.7rem' },
                height: { xs: 20, sm: 24 },
                ml: 1,
                '& .MuiChip-label': {
                  px: { xs: 0.75, sm: 1 }
                }
              }}
            />
          </Box>
        }
        secondary={
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography 
              variant="body2" 
              color="text.primary"
              sx={{ 
                fontWeight: 600,
                fontSize: { xs: '0.75rem', sm: '0.8rem' },
                fontFamily: 'monospace'
              }}
            >
              {formatPrice(stock.livePrice)}
            </Typography>
            <Typography 
              variant="body2" 
              sx={{ 
                color: getChangeColor(stock.changePercent),
                fontWeight: 600,
                fontSize: { xs: '0.7rem', sm: '0.75rem' },
                fontFamily: 'monospace'
              }}
            >
              {stock.changeAmount >= 0 ? '+' : ''}{formatPrice(stock.changeAmount)}
            </Typography>
          </Box>
        }
      />
    </ListItem>
  );

  const renderList = (list, title, isGainer) => (
    <Card 
      sx={{ 
        height: '60vh', // Fixed height - compact for dashboard
        display: 'flex',
        flexDirection: 'column',
        borderLeft: `4px solid ${isGainer ? theme.palette.success.main : theme.palette.error.main}`,
        transition: 'all 0.3s ease',
        overflow: 'hidden',
        '&:hover': {
          boxShadow: theme.shadows[8],
          transform: 'translateY(-4px)'
        }
      }}
    >
      <CardContent sx={{ p: { xs: 1.5, sm: 2 }, pb: 0, flexShrink: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>        
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isGainer ? (
            <TrendingUp sx={{ color: 'success.main', fontSize: { xs: 18, sm: 20 } }} />
          ) : (
            <TrendingDown sx={{ color: 'error.main', fontSize: { xs: 18, sm: 20 } }} />
          )}
            <Typography 
              variant="h6" 
              color="primary"
              sx={{ 
                fontSize: { xs: '1rem', sm: '1.1rem' },
                fontWeight: 600
              }}
            >
              {title}
            </Typography>
          </Box>
          
          {onRefresh && (
            <Tooltip title="Refresh data" arrow>
              <IconButton 
                size="small" 
                onClick={onRefresh}
                sx={{ 
                  opacity: 0.7,
                  '&:hover': { opacity: 1 }
                }}
              >
                <Refresh fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </CardContent>
        
      {isLoading ? (
        <Box sx={{ flex: 1, p: { xs: 1.5, sm: 2 } }}>
          <Stack spacing={1}>
            {[...Array(5)].map((_, i) => (
              <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1 }}>
                <Skeleton variant="circular" width={40} height={40} />
                <Box sx={{ flex: 1 }}>
                  <Skeleton variant="text" width="40%" />
                  <Skeleton variant="text" width="60%" />
                </Box>
                <Skeleton variant="rectangular" width={70} height={24} sx={{ borderRadius: 3 }} />
              </Box>
            ))}
          </Stack>
        </Box>
      ) : list.length === 0 ? (
        <Box 
          sx={{ 
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center', 
            p: 4,
            color: 'text.secondary'
          }}
        >
          <Box>
            <ShowChart sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
            <Typography variant="body2">
              No data available
            </Typography>
          </Box>
        </Box>
      ) : (
        <Box 
          sx={{ 
            flex: 1,
            overflow: 'auto',
            px: { xs: 1.5, sm: 2 },
            pb: { xs: 1.5, sm: 2 },
            // Hide scrollbars
            '&::-webkit-scrollbar': {
              display: 'none',
            },
            '&': {
              msOverflowStyle: 'none',
              scrollbarWidth: 'none',
            },
          }}
        >
          <List sx={{ p: 0 }}>
            {list.map((stock, index) => renderMoverCard(stock, index, isGainer))}
          </List>
        </Box>
      )}
    </Card>
  );

  if (isLoading) {
    return (
      <Box sx={{ mt: { xs: 3, sm: 4 } }}>
        <Skeleton variant="text" width="40%" height={40} sx={{ mb: 2 }} />
        <Grid container spacing={{ xs: 2, sm: 3 }}>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                <Skeleton variant="text" width="60%" height={32} sx={{ mb: 2 }} />
                <Stack spacing={1}>
                  {[...Array(5)].map((_, i) => (
                    <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1 }}>
                      <Skeleton variant="circular" width={40} height={40} />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton variant="text" width="40%" />
                        <Skeleton variant="text" width="60%" />
                      </Box>
                      <Skeleton variant="rectangular" width={70} height={24} sx={{ borderRadius: 3 }} />
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                <Skeleton variant="text" width="60%" height={32} sx={{ mb: 2 }} />
                <Stack spacing={1}>
                  {[...Array(5)].map((_, i) => (
                    <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1 }}>
                      <Skeleton variant="circular" width={40} height={40} />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton variant="text" width="40%" />
                        <Skeleton variant="text" width="60%" />
                      </Box>
                      <Skeleton variant="rectangular" width={70} height={24} sx={{ borderRadius: 3 }} />
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  }
  
  if (!stocks || stocks.length === 0) {
    return (
      <Box sx={{ mt: { xs: 3, sm: 4 } }}>
        <Card>
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <ShowChart sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Market Data Loading
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Top movers will appear here once market data is available
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box sx={{ mt: { xs: 3, sm: 4 } }}>
      {/* Enhanced Header */}
      <Box sx={{ mb: 3, display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'center', sm: 'flex-start' }, gap: 2 }}>
        <Box sx={{ textAlign: { xs: 'center', sm: 'left' } }}>
          <Typography 
            variant="h5" 
            fontWeight={700}
            sx={{ 
              fontSize: { xs: '1.25rem', sm: '1.5rem' },
              mb: 1,
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}
          >
            Market Movers
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Top performing stocks in today's trading session
          </Typography>
        </Box>
        
        {lastUpdated && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, opacity: 0.7 }}>
            <Info sx={{ fontSize: 16 }} />
            <Typography variant="caption" color="text.secondary">
              Updated: {new Date(lastUpdated).toLocaleTimeString()}
            </Typography>
          </Box>
        )}
      </Box>

      {/* Responsive Layout for Gainers and Losers */}
      <Grid container spacing={{ xs: 2, sm: 3 }}>
        <Grid item xs={12} lg={6}>
          {renderList(gainers, isMobile ? "Top Gainers" : "📈 Top 10 Gainers", true)}
        </Grid>
        
        <Grid item xs={12} lg={6}>
          {renderList(losers, isMobile ? "Top Losers" : "📉 Top 10 Losers", false)}
        </Grid>
      </Grid>

      {/* Enhanced Mobile Summary Stats */}
      {isMobile && (gainers.length > 0 || losers.length > 0) && (
        <Card 
          sx={{ 
            mt: 3,
            background: `linear-gradient(135deg, ${theme.palette.background.paper}90, ${theme.palette.background.default}90)`,
            backdropFilter: 'blur(10px)'
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Typography variant="h6" gutterBottom sx={{ fontSize: '1.1rem' }}>
              Market Summary
            </Typography>
            
            <Stack direction="row" spacing={2} justifyContent="space-around">
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h6" color="success.main" fontWeight={700}>
                  {gainers.length}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Gainers
                </Typography>
              </Box>
              
              <Divider orientation="vertical" flexItem />
              
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h6" color="error.main" fontWeight={700}>
                  {losers.length}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Losers
                </Typography>
              </Box>
              
              <Divider orientation="vertical" flexItem />
              
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h6" color="primary.main" fontWeight={700}>
                  {gainers.length > 0 ? gainers[0].changePercent.toFixed(1) : '0'}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Top Gain
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Box>
  );
});

MoversTable.displayName = 'MoversTable';

export default MoversTable;
