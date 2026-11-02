import { Card, Title, Table, Button, Badge, Group, Tabs } from '@mantine/core';
import React from 'react';

const InChargeDashboardPage = () => (
  <Card shadow="sm" padding="lg">
    <Title order={2}>In-Charge Dashboard</Title>
    
    <Tabs defaultValue="Pending Approvals">
      <Tabs.List grow>
        <Tabs.Tab value="Pending Approvals">Pending Approvals</Tabs.Tab>
        <Tabs.Tab value="Replenishment Requests">Replenishment Requests</Tabs.Tab>
        <Tabs.Tab value="Management Reports">Management Reports</Tabs.Tab>
      </Tabs.List>
      
      {/* Pending Approvals */}
      <Tabs.Panel value="Pending Approvals" pt="xs">
        <Table>
          <thead>
            <tr>
              <th>Booking ID</th>
              <th>Guest Name</th>
              <th>Check-In Date</th>
              <th>Check-Out Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          {/* Fill this with actual data */}
        </Table>
      </Tabs.Panel>
      
      {/* Replenishment Requests */}
      <Tabs.Panel value="Replenishment Requests" pt="xs">
        {/* Content for replenishment requests goes here */}
      </Tabs.Panel>
      
      {/* Management Reports */}
      <Tabs.Panel value="Management Reports" pt="xs">
        {/* Content for management reports goes here */}
      </Tabs.Panel>
    </Tabs>
  </Card>
);

export default InChargeDashboardPage;
