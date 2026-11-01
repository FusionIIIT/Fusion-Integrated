import { Card, Container, Group, Table, Text, Title } from "@mantine/core";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances } from "../api";
export default function LeaveBalancesPage() {
  const query = useLeaveBalances();
  if (query.error) return <Container size="md"><ErrorState error={query.error} /></Container>;
  return <Container size="md"><PageHeader title="Leave Balances" subtitle="Current-year entitlements and debits from the append-only leave ledger." />
    <Card withBorder><Group justify="space-between" mb="md"><Title order={3}>Balance by category</Title><Text c="dimmed">{query.data?.[0]?.year ?? new Date().getFullYear()}</Text></Group>
      {query.isPending ? <Text c="dimmed">Loading balances…</Text> : <Table><Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Available balance</Table.Th></Table.Tr></Table.Thead><Table.Tbody>
        {(query.data ?? []).map((row) => <Table.Tr key={row.category}><Table.Td>{row.category}</Table.Td><Table.Td>{row.balance}</Table.Td></Table.Tr>)}
      </Table.Tbody></Table>}
    </Card>
  </Container>;
}
