import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Skeleton
} from '@mui/material';
import { styled } from '@mui/material/styles';

/**
 * Template for React components following trading application standards.
 *
 * Features:
 * - Material-UI v6 integration
 * - Proper error handling and loading states
 * - Performance optimization with useMemo/useCallback
 * - TypeScript-ready structure
 * - Responsive design
 * - Accessibility compliance
 */

// Styled components for consistent theming
const StyledCard = styled(Card)(({ theme }) => ({
  margin: theme.spacing(2),
  transition: 'box-shadow 0.3s ease-in-out',
  '&:hover': {
    boxShadow: theme.shadows[4],
  },
}));

const LoadingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: 200,
  padding: theme.spacing(2),
}));

const DataContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(1),
  },
}));

/**
 * Template Component following trading application standards.
 *
 * @param {Object} props - Component props
 * @param {string} props.title - Component title
 * @param {Array} props.data - Data to display
 * @param {Function} props.onDataChange - Callback for data changes
 * @param {boolean} props.loading - Loading state
 * @param {string} props.error - Error message
 */
const TemplateComponent = ({
  title = 'Default Title',
  data = [],
  onDataChange = () => {},
  loading = false,
  error = null,
  className = '',
  ...props
}) => {
  // State management
  const [localData, setLocalData] = useState(data);
  const [isProcessing, setIsProcessing] = useState(false);

  // Effect for data synchronization
  useEffect(() => {
    setLocalData(data);
  }, [data]);

  // Memoized calculations for performance
  const processedData = useMemo(() => {
    if (!localData.length) return [];

    return localData.map((item, index) => ({
      ...item,
      id: item.id || index,
      displayValue: typeof item.value === 'number'
        ? item.value.toFixed(2)
        : item.value
    }));
  }, [localData]);

  // Callback handlers with useCallback for performance
  const handleDataUpdate = useCallback(async (newData) => {
    setIsProcessing(true);

    try {
      setLocalData(newData);
      await onDataChange(newData);
    } catch (err) {
      console.error('Error updating data:', err);
    } finally {
      setIsProcessing(false);
    }
  }, [onDataChange]);

  const handleItemClick = useCallback((item) => {
    console.log('Item clicked:', item);
    // Handle item interaction
  }, []);

  // Loading state
  if (loading) {
    return (
      <StyledCard className={className}>
        <CardContent>
          <LoadingContainer>
            <CircularProgress size={40} />
            <Typography variant="body2" sx={{ ml: 2 }}>
              Loading {title.toLowerCase()}...
            </Typography>
          </LoadingContainer>
        </CardContent>
      </StyledCard>
    );
  }

  // Error state
  if (error) {
    return (
      <StyledCard className={className}>
        <CardContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        </CardContent>
      </StyledCard>
    );
  }

  // Main render
  return (
    <StyledCard className={className} {...props}>
      <CardContent>
        {/* Header */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Typography variant="h6" component="h2">
            {title}
          </Typography>
          {isProcessing && (
            <CircularProgress size={20} />
          )}
        </Box>

        {/* Data container */}
        <DataContainer>
          {processedData.length === 0 ? (
            <Typography
              variant="body2"
              color="textSecondary"
              align="center"
              sx={{ py: 4 }}
            >
              No data available
            </Typography>
          ) : (
            processedData.map((item) => (
              <Box
                key={item.id}
                onClick={() => handleItemClick(item)}
                sx={{
                  p: 1,
                  mb: 1,
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                  cursor: 'pointer',
                  '&:hover': {
                    backgroundColor: 'action.hover',
                  },
                }}
              >
                <Typography variant="body1">
                  {item.displayValue}
                </Typography>
              </Box>
            ))
          )}
        </DataContainer>
      </CardContent>
    </StyledCard>
  );
};

// Loading skeleton component for better UX
export const TemplateComponentSkeleton = () => (
  <StyledCard>
    <CardContent>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Skeleton variant="text" width={200} height={32} />
        <Skeleton variant="circular" width={20} height={20} />
      </Box>
      <DataContainer>
        {[...Array(5)].map((_, index) => (
          <Skeleton
            key={index}
            variant="rectangular"
            height={48}
            sx={{ mb: 1, borderRadius: 1 }}
          />
        ))}
      </DataContainer>
    </CardContent>
  </StyledCard>
);

export default TemplateComponent;