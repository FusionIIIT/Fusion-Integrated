import { Alert, Badge, Container, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances } from "../api/hooks";

export default function BalancePage() {
  const query = useLeaveBalances();
  if (query.error) return <Container size="xl"><ErrorState error={query.error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title="Balances & History" subtitle="Your current leave account and posted entries" />
      {query.isPending ? <Text c="dimmed">Loading balances…</Text> : <>
        {query.data?.balances.length ? <Table.ScrollContainer minWidth={620} mb="xl">
          <Table striped><Table.Thead><Table.Tr><Table.Th>Category</Table.Th>
            <Table.Th>Year</Table.Th><Table.Th>Opening</Table.Th><Table.Th>Credits</Table.Th>
            <Table.Th>Used</Table.Th><Table.Th>Available</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{query.data.balances.map((row) => <Table.Tr key={row.id}>
              <Table.Td><Badge variant="light">{row.leave_type}</Badge></Table.Td>
              <Table.Td>{row.leave_year}</Table.Td><Table.Td>{row.opening_balance}</Table.Td>
              <Table.Td>{row.credited}</Table.Td><Table.Td>{row.used}</Table.Td>
              <Table.Td fw={700}>{row.available}</Table.Td>
            </Table.Tr>)}</Table.Tbody>
          </Table>
        </Table.ScrollContainer> : <Alert color="gray" mb="xl">No balances have been initialized for your account.</Alert>}
        <Table.ScrollContainer minWidth={560}>
          <Table><Table.Thead><Table.Tr><Table.Th>Posted</Table.Th><Table.Th>Entry</Table.Th>
            <Table.Th>Days</Table.Th><Table.Th>Description</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{query.data?.history.map((row) => <Table.Tr key={row.id}>
              <Table.Td>{new Date(row.created_at).toLocaleDateString()}</Table.Td>
              <Table.Td>{row.entry_type}</Table.Td><Table.Td>{row.days}</Table.Td>
              <Table.Td>{row.description}</Table.Td>
            </Table.Tr>)}</Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </>}
    </Container>
  );
}