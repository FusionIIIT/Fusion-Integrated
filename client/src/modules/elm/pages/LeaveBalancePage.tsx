import { useQuery } from "@tanstack/react-query";
import { Alert, Card, Container, Loader, Stack, Table, Text, Title } from "@mantine/core";
import { errorMessage, http } from "../../../lib/http";

interface LeaveBalanceItem {
  id: number;
  leave_type_code: string;
  leave_type_name: string;
  year: number;
  total_allocated: string;
  used_days: string;
  remaining_days: string;
}

export default function LeaveBalancePage() {
  const balancesQuery = useQuery({
    queryKey: ["elm", "balances"],
    queryFn: async () => (await http.get<LeaveBalanceItem[]>("/elm/balances")).data,
  });

  const rows = balancesQuery.data ?? [];

  return (
    <Container size="lg" py="lg">
      <Stack gap="md">
        <Title order={2}>Leave Balance</Title>
        {balancesQuery.isPending && <Loader size="sm" />}
        {balancesQuery.isError && <Alert color="red">{errorMessage(balancesQuery.error)}</Alert>}
        <Card withBorder>
          {rows.length === 0 ? (
            <Text c="dimmed" size="sm">No leave balances available.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Code</Table.Th>
                  <Table.Th>Leave Type</Table.Th>
                  <Table.Th>Year</Table.Th>
                  <Table.Th>Allocated</Table.Th>
                  <Table.Th>Used</Table.Th>
                  <Table.Th>Remaining</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((b) => (
                  <Table.Tr key={b.id}>
                    <Table.Td>{b.leave_type_code}</Table.Td>
                    <Table.Td>{b.leave_type_name}</Table.Td>
                    <Table.Td>{b.year}</Table.Td>
                    <Table.Td>{b.total_allocated}</Table.Td>
                    <Table.Td>{b.used_days}</Table.Td>
                    <Table.Td>{b.remaining_days}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
