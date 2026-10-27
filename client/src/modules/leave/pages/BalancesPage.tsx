import React, { useState, useEffect } from 'react';
import { Card, Table, Text, Group, Button } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { LeaveBalance, LeaveLedgerEntry } from '../api/types/client';

const BalancesPage: React.FC = () => {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [ledgerEntries, setLedgerEntries] = useState<LeaveLedgerEntry[]>([]);

  const fetchBalances = async () => {
    // Assuming there's an API endpoint to get leave balances
    const response = await fetch('/api/leave/balances');
    const data: LeaveBalance[] = await response.json();
    setBalances(data);
  };

  const fetchLedgerEntries = async () => {
    // Assuming there's an API endpoint to get leave ledger entries
    const response = await fetch('/api/leave/ledger-entries');
    const data: LeaveLedgerEntry[] = await response.json();
    setLedgerEntries(data);
  };

  useEffect(() => {
    fetchBalances();
    fetchLedgerEntries();
  }, []);

  return (
    <div>
      <Card shadow="sm" p="lg">
        <Text size="xl" weight={500}>
          Annual Leave Balances
        </Text>
        <Group mt="md">
          {balances.map((balance) => (
            <Card key={balance.type} shadow="xs" p="sm" style={{ width: '120px' }}>
              <Text size="lg">{balance.type}</Text>
              <Text size="xl" weight={700}>
                {balance.remainingDays}
              </Text>
            </Card>
          ))}
        </Group>
      </Card>

      <Table mt="md">
        <thead>
          <tr>
            <th>Type</th>
            <th>Date</th>
            <th>Reason</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {ledgerEntries.map((entry) => (
            <tr key={entry.id}>
              <td>{entry.type}</td>
              <td>{entry.date.toDateString()}</td>
              <td>{entry.reason}</td>
              <td>{entry.status}</td>
            </tr>
          ))}
        </tbody>
      </Table>

      <Button mt="md" color="blue">
        View All Leave Requests
      </Button>
    </div>
  );
};

export default BalancesPage;