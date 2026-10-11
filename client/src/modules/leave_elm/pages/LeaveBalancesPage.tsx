import React from 'react';
import { Card, Grid } from '@mui/material';
import { useTheme } from '@mui/material/styles';

interface LeaveBalancesPageProps {
  // No props needed for this simple component
}

const LeaveBalancesPage: React.FC<LeaveBalancesPageProps> = () => {
  const theme = useTheme();

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6} lg={4}>
        <Card sx={{ height: '100%', bgcolor: theme.palette.secondary.light }}>
          <CardHeader title="Casual Leave (CL)" />
          <CardContent>
            {/* Replace with actual leave balance logic */}
            <p>Balance: 8</p>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6} lg={4}>
        <Card sx={{ height: '100%', bgcolor: theme.palette.secondary.light }}>
          <CardHeader title="Restricted Holiday (RH)" />
          <CardContent>
            {/* Replace with actual leave balance logic */}
            <p>Balance: 2</p>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6} lg={4}>
        <Card sx={{ height: '100%', bgcolor: theme.palette.secondary.light }}>
          <CardHeader title="Special Casual Leave (SCL)" />
          <CardContent>
            {/* Replace with actual leave balance logic */}
            <p>Balance: 15</p>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6} lg={4}>
        <Card sx={{ height: '100%', bgcolor: theme.palette.secondary.light }}>
          <CardHeader title="Earned Leave (EL)" />
          <CardContent>
            {/* Replace with actual leave balance logic */}
            <p>Balance: 30</p>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6} lg={4}>
        <Card sx={{ height: '100%', bgcolor: theme.palette.secondary.light }}>
          <CardHeader title="Commuted Leave / Medical (COL)" />
          <CardContent>
            {/* Replace with actual leave balance logic */}
            <p>Balance: 20</p>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6} lg={4}>
        <Card sx={{ height: '100%', bgcolor: theme.palette.secondary.light }}>
          <CardHeader title="Vacation Leave (VL)" />
          <CardContent>
            {/* Replace with actual leave balance logic */}
            <p>Balance: 60</p>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default LeaveBalancesPage;