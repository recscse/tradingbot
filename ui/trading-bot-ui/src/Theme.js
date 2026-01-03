import { createTheme } from "@mui/material/styles";

// Premium Slate Design System
const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#3b82f6", // Blue 500 - Modern & Vibrant
      light: "#60a5fa",
      dark: "#2563eb",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#8b5cf6", // Violet 500 - Premium accent
      light: "#a78bfa",
      dark: "#7c3aed",
      contrastText: "#ffffff",
    },
    success: {
      main: "#10b981", // Emerald 500 - Clean success
      light: "#34d399",
      dark: "#059669",
    },
    warning: {
      main: "#f59e0b", // Amber 500 - Warm warning
      light: "#fbbf24",
      dark: "#d97706",
    },
    error: {
      main: "#ef4444", // Red 500 - Clear error
      light: "#f87171",
      dark: "#dc2626",
    },
    background: {
      default: "#0f172a", // Slate 900 - Deep, rich background
      paper: "#1e293b",   // Slate 800 - Subtle surface
    },
    text: {
      primary: "#f1f5f9", // Slate 100 - High contrast text
      secondary: "#94a3b8", // Slate 400 - Muted text
      disabled: "#64748b", // Slate 500
    },
    divider: "#334155", // Slate 700 - Subtle dividers
    action: {
      hover: "rgba(59, 130, 246, 0.08)", // Blue tint hover
      selected: "rgba(59, 130, 246, 0.16)",
    },
  },
  typography: {
    fontFamily: '"Inter", "SF Pro Display", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 700 },
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: { fontWeight: 600, textTransform: "none" },
    body1: { fontSize: "1rem", lineHeight: 1.5 },
    body2: { fontSize: "0.875rem", lineHeight: 1.43 },
  },
  shape: {
    borderRadius: 12, // Modern rounded corners
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
          borderRadius: "10px",
          boxShadow: "none",
          "&:hover": {
            boxShadow: "0 4px 12px rgba(59, 130, 246, 0.2)", // Soft glow
          },
        },
        containedPrimary: {
          background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
        },
        containedSecondary: {
          background: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: "#1e293b", // Slate 800
          borderRadius: 16,
          border: "1px solid #334155", // Slate 700 border
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
        elevation1: {
          boxShadow: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        },
        elevation2: {
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "rgba(15, 23, 42, 0.8)", // Glassmorphic Slate 900
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid #334155",
          boxShadow: "none",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          borderRadius: 8,
        },
        colorPrimary: {
          backgroundColor: "rgba(59, 130, 246, 0.15)",
          color: "#60a5fa", // Lighter blue for text
          border: "1px solid rgba(59, 130, 246, 0.3)",
        },
        colorSuccess: {
          backgroundColor: "rgba(16, 185, 129, 0.15)",
          color: "#34d399",
          border: "1px solid rgba(16, 185, 129, 0.3)",
        },
        colorError: {
          backgroundColor: "rgba(239, 68, 68, 0.15)",
          color: "#f87171",
          border: "1px solid rgba(239, 68, 68, 0.3)",
        },
        colorWarning: {
          backgroundColor: "rgba(245, 158, 11, 0.15)",
          color: "#fbbf24",
          border: "1px solid rgba(245, 158, 11, 0.3)",
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: "1px solid #334155",
          padding: "16px",
        },
        head: {
          fontWeight: 600,
          color: "#94a3b8", // Slate 400
          backgroundColor: "#1e293b", // Slate 800
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          "& .MuiOutlinedInput-root": {
            borderRadius: 10,
            backgroundColor: "rgba(30, 41, 59, 0.5)", // Semi-transparent input
            "& fieldset": { borderColor: "#334155" },
            "&:hover fieldset": { borderColor: "#475569" },
            "&.Mui-focused fieldset": { borderColor: "#3b82f6" },
          },
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          backgroundColor: "#1e293b",
          border: "1px solid #334155",
          borderRadius: 12,
          boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.15)",
        },
      },
    },
  },
});

export default theme;