// components/common/ErrorBoundary.jsx
import React from "react";
import { Paper, Box, Button, Typography } from "@mui/material";
import { bloombergColors } from "../../themes/bloombergColors";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    
    // Update state with error details
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Optional: Log to error reporting service
    if (typeof this.props.onError === 'function') {
      this.props.onError(error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      retryCount: this.state.retryCount + 1
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Render fallback UI
      return (
        <Paper
          elevation={0}
          sx={{
            backgroundColor: bloombergColors.cardBg,
            border: `1px solid ${bloombergColors.negative}`,
            borderRadius: 1,
            p: 3,
            height: this.props.height || "auto",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "200px",
          }}
        >
          <Box sx={{ textAlign: "center", maxWidth: "400px" }}>
            {/* Error Icon */}
            <Box sx={{ fontSize: "3rem", mb: 2 }}>⚠️</Box>
            
            {/* Error Title */}
            <Typography
              variant="h6"
              sx={{
                color: bloombergColors.negative,
                fontWeight: "bold",
                mb: 1,
              }}
            >
              Component Error
            </Typography>
            
            {/* Error Message */}
            <Typography
              variant="body2"
              sx={{
                color: bloombergColors.textSecondary,
                mb: 2,
                lineHeight: 1.5,
              }}
            >
              {this.props.fallbackMessage || 
                "Something went wrong while loading this component. The error has been logged."}
            </Typography>

            {/* Error Details (Development only) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <Box
                sx={{
                  mt: 2,
                  p: 2,
                  backgroundColor: bloombergColors.background,
                  border: `1px solid ${bloombergColors.border}`,
                  borderRadius: 1,
                  textAlign: "left",
                  fontSize: "0.7rem",
                  fontFamily: "monospace",
                  color: bloombergColors.negative,
                  overflow: "auto",
                  maxHeight: "150px",
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: "bold", display: "block", mb: 1 }}>
                  Error Details (Development Mode):
                </Typography>
                <div>{this.state.error.toString()}</div>
                {this.state.errorInfo.componentStack && (
                  <div style={{ marginTop: "8px", fontSize: "0.65rem", opacity: 0.8 }}>
                    {this.state.errorInfo.componentStack}
                  </div>
                )}
              </Box>
            )}

            {/* Action Buttons */}
            <Box sx={{ display: "flex", gap: 2, mt: 3, justifyContent: "center" }}>
              <Button
                size="small"
                variant="outlined"
                onClick={this.handleRetry}
                disabled={this.state.retryCount >= 3}
                sx={{
                  borderColor: bloombergColors.border,
                  color: bloombergColors.textPrimary,
                  fontSize: "0.8rem",
                  "&:hover": {
                    borderColor: bloombergColors.accent,
                    backgroundColor: `${bloombergColors.accent}10`,
                  },
                }}
              >
                {this.state.retryCount >= 3 ? "Max Retries" : `Retry (${this.state.retryCount}/3)`}
              </Button>
              
              <Button
                size="small"
                variant="contained"
                onClick={this.handleReload}
                sx={{
                  backgroundColor: bloombergColors.accent,
                  color: bloombergColors.background,
                  fontSize: "0.8rem",
                  "&:hover": {
                    backgroundColor: bloombergColors.positive,
                  },
                }}
              >
                Reload Page
              </Button>
            </Box>

            {/* Component Info */}
            {this.props.componentName && (
              <Typography
                variant="caption"
                sx={{
                  color: bloombergColors.textSecondary,
                  mt: 2,
                  display: "block",
                  opacity: 0.7,
                }}
              >
                Component: {this.props.componentName}
              </Typography>
            )}
          </Box>
        </Paper>
      );
    }

    // Render children normally if no error
    return this.props.children;
  }
}

// HOC to wrap components with error boundary
export const withErrorBoundary = (WrappedComponent, errorBoundaryProps = {}) => {
  const WithErrorBoundaryComponent = (props) => (
    <ErrorBoundary 
      componentName={WrappedComponent.displayName || WrappedComponent.name}
      {...errorBoundaryProps}
    >
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );
  
  WithErrorBoundaryComponent.displayName = `withErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name})`;
  
  return WithErrorBoundaryComponent;
};

// Hook for functional components to handle errors
export const useErrorHandler = () => {
  const [error, setError] = React.useState(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const handleError = React.useCallback((error) => {
    console.error("Error caught by useErrorHandler:", error);
    setError(error);
  }, []);

  // Throw error to be caught by ErrorBoundary
  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return { handleError, resetError, hasError: !!error };
};

export default ErrorBoundary;