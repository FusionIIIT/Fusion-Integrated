import { Alert, Container, Paper, Table } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances } from "../api/hooks";

export default function BalancesPage() {
  const query = useBalances();
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  const data = query.data;
  return <Container size="lg">
    <PageHeader title="Leave Balances and History" subtitle="Current-year balances and account transactions." />
    {!data?.balances.length ? <Alert color="gray">No balance information is available.</Alert> : <>
      <Paper withBorder p="md" mb="md"><Table>
        <Table.Thead><Table.Tr><Table.Th>Leave</Table.Th><Table.Th>Year</Table.Th>
          <Table.Th>Entitlement</Table.Th><Table.Th>Available</Table.Th>
          <Table.Th>Carry forward</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{data.balances.map((item) => <Table.Tr key={item.leave_type}>
          <Table.Td>{item.leave_type}</Table.Td><Table.Td>{item.year}</Table.Td>
          <Table.Td>{item.entitlement}</Table.Td><Table.Td>{item.available}</Table.Td>
          <Table.Td>{item.carry_forward ? "Yes" : "No"}</Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></Paper>
      <Paper withBorder p="md"><Table.ScrollContainer minWidth={680}><Table>
        <Table.Thead><Table.Tr><Table.Th>Date</Table.Th><Table.Th>Leave</Table.Th>
          <Table.Th>Change</Table.Th><Table.Th>Transaction</Table.Th><Table.Th>Note</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{data.history.map((row) => <Table.Tr key={row.id}>
          <Table.Td>{new Date(row.created_at).toLocaleDateString()}</Table.Td>
          <Table.Td>{row.leave_type} · {row.year}</Table.Td><Table.Td>{row.amount}</Table.Td>
          <Table.Td>{row.transaction_type.replaceAll("_", " ")}</Table.Td><Table.Td>{row.note}</Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer></Paper>
    </>}
  </Container>;
}
