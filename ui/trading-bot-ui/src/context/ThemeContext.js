import { createContext, useContext, useMemo, useState } from "react";
import { createTheme, ThemeProvider } from "@mui/material/styles";

const ThemeModeContext = createContext();

const getDesignTokens = (mode) => ({
  palette: {
    mode,
    ...(mode === "dark"
      ? {
          // Dark Mode (Premium Slate)
          primary: { main: "#3b82f6", light: "#60a5fa", dark: "#2563eb", contrastText: "#ffffff" },
          secondary: { main: "#8b5cf6", light: "#a78bfa", dark: "#7c3aed", contrastText: "#ffffff" },
          background: { default: "#0f172a", paper: "#1e293b" }, // Slate 900 / 800
          text: { primary: "#f1f5f9", secondary: "#94a3b8", disabled: "#64748b" },
          divider: "#334155",
          success: { main: "#10b981", light: "#34d399", dark: "#059669" },
          warning: { main: "#f59e0b", light: "#fbbf24", dark: "#d97706" },
          error: { main: "#ef4444", light: "#f87171", dark: "#dc2626" },
          action: { hover: "rgba(59, 130, 246, 0.08)", selected: "rgba(59, 130, 246, 0.16)" },
        }
      : {
          // Light Mode (Clean Zinc)
          primary: { main: "#2563eb", light: "#60a5fa", dark: "#1d4ed8", contrastText: "#ffffff" },
          secondary: { main: "#7c3aed", light: "#a78bfa", dark: "#6d28d9", contrastText: "#ffffff" },
          background: { default: "#f8fafc", paper: "#ffffff" }, // Slate 50 / White
          text: { primary: "#0f172a", secondary: "#64748b", disabled: "#94a3b8" },
          divider: "#e2e8f0",
          success: { main: "#059669", light: "#34d399", dark: "#047857" },
          warning: { main: "#d97706", light: "#fbbf24", dark: "#b45309" },
          error: { main: "#dc2626", light: "#f87171", dark: "#b91c1c" },
          action: { hover: "rgba(37, 99, 235, 0.04)", selected: "rgba(37, 99, 235, 0.08)" },
        }),
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
    borderRadius: 12,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
          borderRadius: "10px",
          boxShadow: "none",
          "&:hover": { boxShadow: "0 4px 12px rgba(59, 130, 246, 0.2)" },
        },
        containedPrimary: {
          background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          borderRadius: 16,
          boxShadow: mode === "dark" 
            ? "0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1)"
            : "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)",
          border: mode === "dark" ? "1px solid #334155" : "1px solid #e2e8f0",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: "none" },
        elevation1: { boxShadow: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)" },
        elevation2: { boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)" },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: mode === "dark" ? "rgba(15, 23, 42, 0.85)" : "rgba(255, 255, 255, 0.85)",
          backdropFilter: "blur(12px)",
          borderBottom: mode === "dark" ? "1px solid #334155" : "1px solid #e2e8f0",
          boxShadow: "none",
          color: mode === "dark" ? "#f1f5f9" : "#0f172a",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, borderRadius: 8 },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          "& .MuiOutlinedInput-root": {
            borderRadius: 10,
            backgroundColor: mode === "dark" ? "rgba(30, 41, 59, 0.5)" : "rgba(241, 245, 249, 0.5)",
            "& fieldset": { borderColor: mode === "dark" ? "#334155" : "#e2e8f0" },
            "&:hover fieldset": { borderColor: mode === "dark" ? "#475569" : "#cbd5e1" },
            "&.Mui-focused fieldset": { borderColor: "#3b82f6" },
          },
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          borderRadius: 12,
          border: mode === "dark" ? "1px solid #334155" : "1px solid #e2e8f0",
          boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        },
      },
    },
  },
});

export const CustomThemeProvider = ({ children }) => {
  // Use local storage to persist theme
  const [mode, setMode] = useState(() => {
    const savedMode = localStorage.getItem("themeMode");
    return savedMode || "dark";
  });

  const toggleTheme = () => {
    setMode((prev) => {
      const newMode = prev === "light" ? "dark" : "light";
      localStorage.setItem("themeMode", newMode);
      return newMode;
    });
  };

  // Update theme when mode changes
  const theme = useMemo(() => createTheme(getDesignTokens(mode)), [mode]);

  return (
    <ThemeModeContext.Provider value={{ mode, toggleTheme }}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </ThemeModeContext.Provider>
  );
};

export const useThemeMode = () => useContext(ThemeModeContext);