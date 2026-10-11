import React from 'react';
import { Card, Grid } from '@mui/material';

const LeaveBalancesPage: React.FC = () => {
  // Example data for leave balances
  const leaveBalances = [
    { name: 'Casual Leave (CL)', days: 8 },
    { name: 'Restricted Holiday (RH)', days: 2 },
    { name: 'Special Casual Leave (SCL)', days: 15 },
    { name: 'Earned Leave (EL)', days: 30 },
    { name: 'Commuted Leave / Medical (COL)', days: 20 },
    { name: 'Vacation Leave (VL)', days: 60 },
  ];

  return (
    <Grid container spacing={4}>
      {leaveBalances.map((balance, index) => (
        <Grid item xs={12} sm={6} md={4} key={index}>
          <Card sx={{ padding: 2 }}>
            <h3>{balance.name}</h3>
            <p>Days Remaining: {balance.days}</p>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default LeaveBalancesPage;