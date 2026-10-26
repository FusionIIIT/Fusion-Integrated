import { Badge, Card, Container, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveAccounts } from "../hooks/useLeaveManagement";

export default function LeaveAccountsPage() {
  const accounts = useLeaveAccounts();
  if (accounts.error) {
    return <Container size="xl"><ErrorState error={accounts.error} /></Container>;
  }
  return (
    <Container size="xl">
      <PageHeader title="Leave Accounts" subtitle="Balances and account ledger summaries" />
      <Card withBorder>
        {accounts.isPending ? <Text c="dimmed">Loading accounts…</Text> : (
          <Table.ScrollContainer minWidth={680}>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Employee</Table.Th><Table.Th>Year</Table.Th>
                  <Table.Th>Category</Table.Th><Table.Th>Opening</Table.Th>
                  <Table.Th>Credited</Table.Th><Table.Th>Used</Table.Th>
                  <Table.Th>Balance</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(accounts.data ?? []).map((account) => (
                  <Table.Tr key={`${account.user_id}-${account.category}-${account.year}`}>
                    <Table.Td>#{account.user_id}</Table.Td>
                    <Table.Td>{account.year}</Table.Td>
                    <Table.Td><Badge variant="light">{account.category}</Badge></Table.Td>
                    <Table.Td>{account.opening_balance}</Table.Td>
                    <Table.Td>{account.credited}</Table.Td>
                    <Table.Td>{account.used}</Table.Td>
                    <Table.Td fw={700}>{account.balance}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>
    </Container>
  );
}
