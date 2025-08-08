import React, { useState } from "react";
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Box, 
  Button, 
  IconButton,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  useTheme,
  useMediaQuery,
  Container,
  Divider
} from "@mui/material";
import { 
  Menu as MenuIcon, 
  Close as CloseIcon,
  TrendingUp,
  Assessment,
  AccountBalance,
  Login as LoginIcon
} from "@mui/icons-material";

const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const navigationItems = [
    { label: "Features", href: "#features", icon: <TrendingUp /> },
    { label: "Resources", href: "#resources", icon: <Assessment /> },
    { label: "Pricing", href: "#pricing", icon: <AccountBalance /> },
  ];

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen);
  };

  const handleMobileNavClick = (href) => {
    setMobileMenuOpen(false);
    // Handle navigation
    if (href.startsWith('#')) {
      const element = document.querySelector(href);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          bgcolor: "transparent",
          backdropFilter: "blur(20px)",
          borderBottom: `1px solid ${theme.palette.divider}`,
          zIndex: theme.zIndex.appBar,
        }}
      >
        <Container maxWidth="xl">
          <Toolbar 
            sx={{ 
              justifyContent: "space-between",
              py: { xs: 1, sm: 1.5 },
              px: { xs: 0, sm: 2 }
            }}
          >
            {/* Logo Section */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box
                sx={{
                  width: { xs: 32, sm: 40 },
                  height: { xs: 32, sm: 40 },
                  borderRadius: "50%",
                  background: `conic-gradient(from 180deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main}, ${theme.palette.primary.main})`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: `0 4px 16px ${theme.palette.primary.main}30`,
                  position: "relative",
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    inset: 2,
                    borderRadius: "50%",
                    background: theme.palette.background.paper,
                  },
                }}
              >
                <AccountBalance
                  sx={{
                    color: theme.palette.primary.main,
                    fontSize: { xs: 16, sm: 20 },
                    zIndex: 1,
                  }}
                />
              </Box>
              
              <Typography 
                variant="h6" 
                fontWeight={900}
                sx={{
                  fontSize: { xs: '1.1rem', sm: '1.3rem', md: '1.4rem' },
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '-0.02em',
                  display: { xs: 'none', sm: 'block' }
                }}
              >
                GrowthQuantix
              </Typography>
            </Box>

            {/* Desktop Navigation */}
            {!isMobile && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {navigationItems.map((item) => (
                  <Button
                    key={item.label}
                    color="inherit"
                    onClick={() => handleMobileNavClick(item.href)}
                    startIcon={item.icon}
                    className="touch-button"
                    sx={{
                      textTransform: 'none',
                      fontWeight: 600,
                      fontSize: '0.95rem',
                      px: 2,
                      py: 1,
                      borderRadius: 2,
                      '&:hover': {
                        bgcolor: 'action.hover',
                        transform: 'translateY(-1px)',
                      },
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {item.label}
                  </Button>
                ))}
                
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<LoginIcon />}
                  className="touch-button"
                  sx={{
                    textTransform: 'none',
                    fontWeight: 600,
                    fontSize: '0.95rem',
                    px: 3,
                    py: 1,
                    borderRadius: 2,
                    ml: 2,
                    boxShadow: `0 4px 12px ${theme.palette.primary.main}30`,
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: `0 6px 20px ${theme.palette.primary.main}40`,
                    },
                    transition: 'all 0.2s ease'
                  }}
                >
                  Login
                </Button>
              </Box>
            )}

            {/* Mobile Menu Button */}
            {isMobile && (
              <IconButton
                edge="end"
                color="inherit"
                aria-label="menu"
                onClick={toggleMobileMenu}
                className="touch-button"
                sx={{
                  width: 44,
                  height: 44,
                  bgcolor: 'action.hover',
                  '&:hover': {
                    bgcolor: 'action.selected',
                    transform: 'scale(1.05)',
                  },
                  transition: 'all 0.2s ease'
                }}
              >
                {mobileMenuOpen ? <CloseIcon /> : <MenuIcon />}
              </IconButton>
            )}
          </Toolbar>
        </Container>
      </AppBar>

      {/* Mobile Drawer */}
      <Drawer
        anchor="right"
        open={mobileMenuOpen}
        onClose={toggleMobileMenu}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: 320 },
            bgcolor: 'background.paper',
            backgroundImage: 'none'
          },
        }}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
      >
        <Box
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          {/* Drawer Header */}
          <Box
            sx={{
              p: 3,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: `1px solid ${theme.palette.divider}`,
              background: `linear-gradient(135deg, ${theme.palette.primary.main}10, ${theme.palette.secondary.main}05)`
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: `conic-gradient(from 180deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main}, ${theme.palette.primary.main})`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: `0 4px 16px ${theme.palette.primary.main}30`,
                  position: "relative",
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    inset: 2,
                    borderRadius: "50%",
                    background: theme.palette.background.paper,
                  },
                }}
              >
                <AccountBalance
                  sx={{
                    color: theme.palette.primary.main,
                    fontSize: 20,
                    zIndex: 1,
                  }}
                />
              </Box>
              
              <Typography 
                variant="h6" 
                fontWeight={900}
                sx={{
                  fontSize: '1.25rem',
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '-0.02em'
                }}
              >
                GrowthQuantix
              </Typography>
            </Box>
            
            <IconButton
              onClick={toggleMobileMenu}
              className="touch-button"
              sx={{
                bgcolor: 'action.hover',
                '&:hover': { bgcolor: 'action.selected' }
              }}
            >
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Mobile Navigation Items */}
          <Box sx={{ flex: 1, overflow: 'auto' }}>
            <List sx={{ p: 2 }}>
              {navigationItems.map((item) => (
                <ListItemButton
                  key={item.label}
                  onClick={() => handleMobileNavClick(item.href)}
                  className="touch-button"
                  sx={{
                    borderRadius: 3,
                    mb: 1,
                    py: 2,
                    px: 3,
                    '&:hover': {
                      bgcolor: 'action.hover',
                      transform: 'translateX(8px)',
                    },
                    transition: 'all 0.3s ease'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    <Box sx={{ color: 'primary.main' }}>
                      {item.icon}
                    </Box>
                    <ListItemText
                      primary={item.label}
                      primaryTypographyProps={{
                        fontWeight: 600,
                        fontSize: '1.1rem'
                      }}
                    />
                  </Box>
                </ListItemButton>
              ))}
            </List>

            <Divider sx={{ mx: 2, my: 2 }} />

            {/* Mobile Login Button */}
            <Box sx={{ p: 2 }}>
              <Button
                variant="contained"
                color="primary"
                fullWidth
                startIcon={<LoginIcon />}
                className="touch-button"
                sx={{
                  textTransform: 'none',
                  fontWeight: 600,
                  fontSize: '1.1rem',
                  py: 1.5,
                  borderRadius: 3,
                  boxShadow: `0 4px 12px ${theme.palette.primary.main}30`,
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: `0 6px 20px ${theme.palette.primary.main}40`,
                  },
                  transition: 'all 0.2s ease'
                }}
              >
                Get Started
              </Button>
            </Box>
          </Box>

          {/* Footer */}
          <Box 
            sx={{ 
              p: 3, 
              borderTop: `1px solid ${theme.palette.divider}`,
              textAlign: 'center'
            }}
          >
            <Typography variant="body2" color="text.secondary">
              AI-Powered Trading Platform
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              © 2024 GrowthQuantix. All rights reserved.
            </Typography>
          </Box>
        </Box>
      </Drawer>
    </>
  );
};

export default Header;
