import { Badge, Container, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { useLeaveBalances } from "../api/hooks";
import { LeaveBalance } from "../api/types";

export default function BalancesPage() {
  const { data: balances = [], isLoading } = useLeaveBalances();

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        <div>
          <Title order={2}>Leave Balances</Title>
          <Text c="dimmed" size="sm">Your current allocated, consumed, and remaining leave quotas</Text>
        </div>

        <Paper withBorder p="md" radius="sm">
          {isLoading ? (
            <Text>Loading balances...</Text>
          ) : balances.length === 0 ? (
            <Text c="dimmed">No leave balances found for current year.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Leave Type</Table.Th>
                  <Table.Th>Year</Table.Th>
                  <Table.Th>Allocated Days</Table.Th>
                  <Table.Th>Used Days</Table.Th>
                  <Table.Th>Remaining Balance</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {balances.map((b: LeaveBalance) => (
                  <Table.Tr key={b.id}>
                    <Table.Td><Badge variant="light">{b.leave_type}</Badge></Table.Td>
                    <Table.Td>{b.year}</Table.Td>
                    <Table.Td>{b.allocated}</Table.Td>
                    <Table.Td>{b.used}</Table.Td>
                    <Table.Td>
                      <Badge color={parseFloat(b.balance) > 0 ? "teal" : "red"}>
                        {b.balance}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Paper>
      </Stack>
    </Container>
  );
}
