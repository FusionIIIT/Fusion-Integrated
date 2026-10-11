// Leave Balance Dashboard
import { Table, Paper, Stack, Title, Button, LoadingOverlay, Text } from '@mantine/core';
import { useLeaveBalances } from '../api/hooks';
import { useNavigate } from 'react-router-dom';

export default function LeaveBalanceDashboard() {
  const { data, isLoading, error } = useLeaveBalances();
  const navigate = useNavigate();

  if (isLoading) return (
    <Paper p="md">
      <LoadingOverlay visible={true} overlayProps={{ opacity: 0.1 }}>
        <Title order={3}>Leave Balance</Title>
        <Text>Loading balances...</Text>
      </LoadingOverlay>
    </Paper>
  );

  if (error) return (
    <Paper p="md">
      <Title order={3}>Leave Balance</Title>
      <Text color="red">{error.message}</Text>
    </Paper>
  );

  return (
    <Paper p="md">
      <Title order={3}>Leave Balance</Title>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Employee</Table.Th>
            <Table.Th>Annual Balance</Table.Th>
            <Table.Th>Used</Table.Th>
            <Table.Th>Remaining</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.map((balance: Record<string, any>) => (
            <Table.Tr key={balance.id}>
              <Table.Td>{balance.employee.name}</Table.Td>
              <Table.Td>{balance.annual_balance}</Table.Td>
              <Table.Td>{balance.used}</Table.Td>
              <Table.Td>{balance.remaining}</Table.Td>
              <Table.Td>
                <Stack>
                  <Button
                    variant="default"
                    onClick={() => navigate(`/elm/balances/${balance.id}`)}
                  >
                    View
                  </Button>
                </Stack>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Paper>
  );
}
