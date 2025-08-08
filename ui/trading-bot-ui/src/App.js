import React, { useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import Layout from "./components/common/Layout";
import LandingPage from "./pages/LandingPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import TradeControlPage from "./pages/TradeControlPage";
import ConfigPage from "./pages/BrokerConfigPage";
import { isAuthenticated } from "./services/authService";
import { CustomThemeProvider } from "./context/ThemeContext";
import { NotificationProvider } from "./context/NotificationContext";
import { CssBaseline } from "@mui/material";
import PrivateRoute from "./routes/PrivateRoute";
import StockAnalysisPage from "./pages/StockAnalysisPage";
import ProfilePage from "./pages/ProfilePage";
import BacktestingPage from "./pages/BacktestingPage";
import PaperTradingPage from "./pages/PaperTradingPage";
import { MarketProvider } from "./context/MarketProvider";
import EnhancedOptionChainPage from "./pages/EnhancedOptionChainPage";
import AboutPage from "./pages/AboutPage";
import ContactPage from "./pages/ContactPage";
import PrivacyPolicyPage from "./pages/PrivacyPolicyPage";
import TermsPage from "./pages/TermsPage";
import SecurityPage from "./pages/SecurityPage";
import TermsModal from "./components/TermsModal";
import { UnifiedMarketProvider } from "./hooks/useUnifiedMarketData";

// 🎯 PROTECTED LAYOUT WRAPPER - This ensures all providers are available
const ProtectedLayout = ({ children }) => (
  <PrivateRoute>
    <MarketProvider>
      <UnifiedMarketProvider>
        <Layout>{children}</Layout>
      </UnifiedMarketProvider>
    </MarketProvider>
  </PrivateRoute>
);

const App = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(isAuthenticated());

  useEffect(() => {
    const checkAuth = () => setIsLoggedIn(isAuthenticated());
    window.addEventListener("storage", checkAuth);
    return () => window.removeEventListener("storage", checkAuth);
  }, []);

  return (
    <CustomThemeProvider>
      <CssBaseline />
      <NotificationProvider>
        <Router>
          <TermsModal />
          <Routes>
            {/* ===== PUBLIC ROUTES ===== */}
            <Route
              path="/"
              element={
                isLoggedIn ? (
                  <Navigate to="/dashboard" replace />
                ) : (
                  <LandingPage />
                )
              }
            />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/privacy" element={<PrivacyPolicyPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/security" element={<SecurityPage />} />

            {/* ===== PROTECTED ROUTES ===== */}
            <Route
              path="/dashboard"
              element={
                <ProtectedLayout>
                  <DashboardPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/option-chain/:symbol"
              element={
                <ProtectedLayout>
                  <EnhancedOptionChainPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/trade-control"
              element={
                <ProtectedLayout>
                  <TradeControlPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/config"
              element={
                <ProtectedLayout>
                  <ConfigPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/backtesting"
              element={
                <ProtectedLayout>
                  <BacktestingPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/papertrading"
              element={
                <ProtectedLayout>
                  <PaperTradingPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/analysis"
              element={
                <ProtectedLayout>
                  <StockAnalysisPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedLayout>
                  <ProfilePage />
                </ProtectedLayout>
              }
            />

            {/* ===== CATCH ALL ROUTE ===== */}
            <Route
              path="*"
              element={
                <Navigate to={isLoggedIn ? "/dashboard" : "/"} replace />
              }
            />
          </Routes>
        </Router>
      </NotificationProvider>
    </CustomThemeProvider>
  );
};

export default App;
