import React from 'react';
import { Box, Container, Typography } from '@mui/material';
import SystemHealthDashboard from '../components/dashboard/SystemHealthDashboard';

const SystemHealthPage = () => {
  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight="bold" color="primary">
          System Health & Status
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Real-time monitoring of system infrastructure, business logic, and operational status.
        </Typography>
      </Box>
      <SystemHealthDashboard />
    </Container>
  );
};

export default SystemHealthPage;
