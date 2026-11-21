import React, { useState } from 'react';
import { Paper, Title, TextInput, Select, Button, Stack, Group, Table, Text } from '@mantine/core';
import { useStudentBills, useSubmitRebate, useSubmitRegistration } from '../api/queries';

export default function StudentDashboardPage() {
  const { data: bills } = useStudentBills();
  const rebateMutation = useSubmitRebate();
  const registerMutation = useSubmitRegistration();

  const [reason, setReason] = useState('medical');
  const [explanation, setExplanation] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const handleRebate = () => {
    rebateMutation.mutate({
      reason,
      explanation,
      start_date: startDate,
      end_date: endDate,
    });
  };

  return (
    <Stack gap="lg" p="md">
      <Title order={2}>MMS Student Portal</Title>

      <Paper p="md" withBorder radius="md">
        <Title order={4} mb="xs">Quick Registration</Title>
        <Group>
          <Button onClick={() => registerMutation.mutate({ window_id: 1 })} loading={registerMutation.isPending}>
            Apply for Active Cycle (Window #1)
          </Button>
        </Group>
      </Paper>

      <Paper p="md" withBorder radius="md">
        <Title order={4} mb="xs">Apply for Rebate</Title>
        <Stack gap="sm">
          <Select
            label="Reason"
            data={['medical', 'institute_leave', 'family_function', 'other']}
            value={reason}
            onChange={(val) => setReason(val || 'medical')}
          />
          {reason === 'other' && (
            <TextInput
              label="Explanation"
              placeholder="Reason details"
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
            />
          )}
          <Group grow>
            <TextInput label="Start Date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            <TextInput label="End Date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </Group>
          <Button onClick={handleRebate} loading={rebateMutation.isPending}>
            Submit Rebate Request
          </Button>
        </Stack>
      </Paper>

      <Paper p="md" withBorder radius="md">
        <Title order={4} mb="xs">My Monthly Bills</Title>
        <Table striped withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Month/Year</Table.Th>
              <Table.Th>Base Charge</Table.Th>
              <Table.Th>Deductions</Table.Th>
              <Table.Th>Total</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {bills && bills.length > 0 ? (
              bills.map((b: any) => (
                <Table.Tr key={b.id}>
                  <Table.Td>{b.month}/{b.year}</Table.Td>
                  <Table.Td>₹{b.base_charge}</Table.Td>
                  <Table.Td>-₹{b.rebate_deduction}</Table.Td>
                  <Table.Td>₹{b.total_amount}</Table.Td>
                  <Table.Td>{b.status}</Table.Td>
                </Table.Tr>
              ))
            ) : (
              <Table.Tr>
                <Table.Td colSpan={5}><Text ta="center">No published bills found.</Text></Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}