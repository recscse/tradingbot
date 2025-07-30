import React, { useEffect } from "react";
import { Box } from "@mui/material";
import { useNavigate } from "react-router-dom";
import Navbar from "./Navbar";
import { isAuthenticated } from "../../services/authService";

const Layout = ({ children }) => {
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login");
    }
  }, [navigate]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        width: "100vw", // 🎯 FULL VIEWPORT WIDTH
        margin: 0, // 🎯 REMOVE ANY MARGIN
        padding: 0, // 🎯 REMOVE ANY PADDING
        boxSizing: "border-box", // 🎯 INCLUDE BORDERS IN WIDTH
        overflow: "hidden", // Prevent horizontal scroll
      }}
    >
      {/* Navbar */}
      <Navbar />

      {/* Main Content - NO CONTAINER WRAPPER */}
      <Box
        component="main"
        sx={{
          flex: 1,
          width: "100%", // 🎯 FULL WIDTH
          margin: 0, // 🎯 NO MARGIN
          padding: 0, // 🎯 NO PADDING - Let children handle their own padding
          boxSizing: "border-box",
          overflow: "auto", // Allow content scrolling
          // 🎯 REMOVED mt: 10 - Navbar already handles spacing with its own height
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default Layout;
