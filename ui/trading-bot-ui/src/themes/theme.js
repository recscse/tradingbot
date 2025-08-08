import { createTheme } from "@mui/material/styles";

// UNIFIED THEME SYSTEM - Using Landing Page Colors Across Application
// Primary: #3f8fff (Modern Blue) | Secondary: #19de9b (Modern Green)
// Background: #030712 (Deep Dark) | Paper: #111827 (Dark Gray)

const getThemeConfig = (mode) => ({
  palette: {
    mode,
    // UNIFIED PRIMARY COLORS from Landing Page
    primary: {
      main: "#3f8fff", // Modern blue from landing
      light: "#75b8ff", 
      dark: "#0062cc",
      contrastText: "#ffffff",
    },
    // UNIFIED SECONDARY COLORS from Landing Page  
    secondary: {
      main: "#19de9b", // Modern green from landing
      light: "#6effce",
      dark: "#00ac6c",
      contrastText: "#ffffff",
    },
    // FINANCIAL TRADING COLORS (Accessible & Modern)
    success: {
      main: "#00C851", // Softer green for gains
      light: "#4CAF50",
      dark: "#2E7D32",
      contrastText: "#ffffff",
    },
    error: {
      main: "#FF4444", // Softer red for losses  
      light: "#EF5350",
      dark: "#C62828",
      contrastText: "#ffffff",
    },
    warning: {
      main: "#FFB300", // Amber for neutral/warning
      light: "#FFC107",
      dark: "#F57C00",
      contrastText: "#000000",
    },
    info: {
      main: "#2196F3", // Info blue
      light: "#42A5F5",
      dark: "#1976D2",
      contrastText: "#ffffff",
    },
    // UNIFIED BACKGROUND SYSTEM
    background: {
      default: mode === "light" ? "#f8f9fa" : "#030712", // Landing page dark
      paper: mode === "light" ? "#ffffff" : "#111827", // Landing page paper
    },
    // UNIFIED TEXT SYSTEM
    text: {
      primary: mode === "light" ? "#000000" : "#ffffff",
      secondary: mode === "light" ? "rgba(0, 0, 0, 0.7)" : "rgba(255, 255, 255, 0.7)",
    },
    // TRADING-SPECIFIC COLORS
    trading: {
      bullish: "#00C851", // Green for bullish/gains
      bearish: "#FF4444", // Red for bearish/losses
      neutral: "#FFB300", // Amber for neutral
      volume: "#9E9E9E", // Gray for volume data
      border: mode === "light" ? "#E0E0E0" : "#333333",
    },
  },
  // STANDARDIZED BREAKPOINTS (Material-UI defaults + consistent usage)
  breakpoints: {
    values: {
      xs: 0,      // phones (320px+)
      sm: 600,    // tablets 
      md: 900,    // small laptops
      lg: 1200,   // desktop
      xl: 1536,   // large screens
    },
  },
  
  // UNIFIED SHAPE SYSTEM (from landing page)
  shape: {
    borderRadius: 12, // Consistent rounded corners
  },
  // UNIFIED TYPOGRAPHY SYSTEM (from landing page)
  typography: {
    fontFamily: "'Inter', 'Roboto', 'Helvetica', 'Arial', sans-serif", // Landing page font
    h1: {
      fontSize: "clamp(2rem, 5vw, 3.5rem)",
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: "clamp(1.75rem, 4vw, 2.8rem)", // Matching landing page
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h3: {
      fontSize: "clamp(1.5rem, 3.5vw, 2.2rem)", // Matching landing page
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h4: {
      fontSize: "clamp(1.25rem, 3vw, 1.75rem)",
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: "clamp(1.1rem, 2.5vw, 1.5rem)",
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h6: {
      fontSize: "clamp(1rem, 2vw, 1.25rem)",
      fontWeight: 600,
      lineHeight: 1.4,
    },
    body1: {
      fontSize: "clamp(0.875rem, 2vw, 1rem)",
      lineHeight: 1.5,
    },
    body2: {
      fontSize: "clamp(0.75rem, 1.8vw, 0.875rem)",
      lineHeight: 1.5,
    },
    caption: {
      fontSize: "clamp(0.625rem, 1.5vw, 0.75rem)",
      lineHeight: 1.4,
    },
    button: {
      textTransform: "none", // Landing page style
      fontWeight: 600,
    },
  },
  // Enhanced spacing system
  spacing: 8, // Base spacing unit (8px)
  // Component overrides for responsive design
  components: {
    // UNIFIED BUTTON SYSTEM (from landing page)
    MuiButton: {
      styleOverrides: {
        root: {
          minHeight: 44, // Touch-friendly minimum
          borderRadius: 8, // Landing page style
          textTransform: 'none', // Landing page style
          fontWeight: 600,
          fontSize: "clamp(0.875rem, 2vw, 1rem)",
          padding: "10px 20px", // Landing page padding
          transition: "all 0.3s ease", // Landing page transition
          '&:hover': {
            transform: 'translateY(-2px)', // Landing page hover effect
            boxShadow: '0 7px 14px rgba(0, 0, 0, 0.25)',
          },
        },
        containedPrimary: {
          background: 'linear-gradient(45deg, #3f8fff 30%, #75b8ff 90%)', // Landing page gradient
        },
        containedSecondary: {
          background: 'linear-gradient(45deg, #19de9b 30%, #6effce 90%)', // Landing page gradient
        },
        sizeSmall: {
          minHeight: 36,
          fontSize: "clamp(0.75rem, 1.8vw, 0.875rem)",
        },
        sizeLarge: {
          minHeight: 52,
          fontSize: "clamp(1rem, 2.2vw, 1.125rem)",
        },
      },
    },
    // UNIFIED CARD SYSTEM (from landing page)
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16, // Landing page style
          backdropFilter: 'blur(10px)', // Landing page effect
          backgroundColor: mode === "light" 
            ? "#ffffff" 
            : "rgba(17, 24, 39, 0.7)", // Landing page semi-transparent
          boxShadow: mode === "light" 
            ? "0 2px 8px rgba(0, 0, 0, 0.1)"
            : "0 10px 20px rgba(0, 0, 0, 0.2)", // Landing page shadow
          transition: 'transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out', // Landing page transition
          '&:hover': {
            transform: 'translateY(-5px)', // Landing page hover effect
            boxShadow: mode === "light" 
              ? "0 4px 12px rgba(0, 0, 0, 0.15)"
              : "0 15px 30px rgba(0, 0, 0, 0.3)",
          },
        },
      },
    },
    // UNIFIED CONTAINER SYSTEM (from landing page)
    MuiContainer: {
      styleOverrides: {
        root: {
          paddingLeft: "24px", // Landing page padding
          paddingRight: "24px",
          "@media (min-width:600px)": {
            paddingLeft: "32px",
            paddingRight: "32px",
          },
        },
      },
    },
    // UNIFIED DIALOG SYSTEM
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 16, // Landing page style
          margin: 16,
          width: "calc(100% - 32px)",
          maxWidth: "none",
          backdropFilter: 'blur(10px)', // Landing page effect
          "@media (min-width: 600px)": {
            margin: 32,
            width: "calc(100% - 64px)",
            maxWidth: 600,
          },
          "@media (min-width: 900px)": {
            maxWidth: 800,
          },
        },
      },
    },
    // TextField responsive design
    MuiTextField: {
      styleOverrides: {
        root: {
          "& .MuiInputBase-root": {
            minHeight: 44, // Touch-friendly
            fontSize: "clamp(0.875rem, 2vw, 1rem)",
          },
        },
      },
    },
    // ENHANCED TABLE SYSTEM for Trading Data
    MuiTable: {
      styleOverrides: {
        root: {
          minWidth: 320, // Mobile-first approach
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          fontSize: "clamp(0.75rem, 1.8vw, 0.875rem)",
          padding: "12px 8px",
          borderBottom: `1px solid ${mode === "light" ? "#E0E0E0" : "#333333"}`,
          "@media (max-width: 600px)": {
            padding: "8px 4px",
            fontSize: "0.75rem",
          },
        },
        head: {
          fontWeight: 700, // Bold headers for financial data
          fontSize: "clamp(0.75rem, 1.8vw, 0.875rem)",
          backgroundColor: mode === "light" ? "#f5f5f5" : "rgba(17, 24, 39, 0.5)",
        },
      },
    },
    MuiTableContainer: {
      styleOverrides: {
        root: {
          borderRadius: 12, // Consistent with card styling
          '&::-webkit-scrollbar': {
            width: 6,
            height: 6,
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: mode === "light" ? "#f5f5f5" : "#1a1a1a",
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: "#3f8fff", // Primary color
            borderRadius: 3,
          },
        },
      },
    },
    // Toolbar responsive design  
    MuiToolbar: {
      styleOverrides: {
        root: {
          minHeight: "56px !important",
          "@media (min-width: 600px)": {
            minHeight: "64px !important",
          },
          "@media (min-width: 900px)": {
            minHeight: "72px !important",
          },
        },
      },
    },
    // IconButton responsive sizing
    MuiIconButton: {
      styleOverrides: {
        root: {
          width: 44,
          height: 44,
          "@media (max-width: 600px)": {
            width: 40,
            height: 40,
          },
        },
        sizeSmall: {
          width: 36,
          height: 36,
          "@media (max-width: 600px)": {
            width: 32,
            height: 32,
          },
        },
      },
    },
  },
});

// CREATE UNIFIED THEMES
export const lightTheme = createTheme(getThemeConfig("light"));
export const darkTheme = createTheme(getThemeConfig("dark"));

// EXPORT TRADING-SPECIFIC COLOR PALETTE for Components
export const tradingColors = {
  bullish: "#00C851", // Green for gains
  bearish: "#FF4444", // Red for losses  
  neutral: "#FFB300", // Amber for neutral
  volume: "#9E9E9E", // Gray for volume
  primary: "#3f8fff", // Unified primary blue
  secondary: "#19de9b", // Unified secondary green
};

// EXPORT RESPONSIVE BREAKPOINT HELPERS
export const breakpoints = {
  xs: 0,
  sm: 600,
  md: 900, 
  lg: 1200,
  xl: 1536,
};

// EXPORT SPACING HELPERS
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};
