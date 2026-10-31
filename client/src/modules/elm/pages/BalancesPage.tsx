import { useState } from "react";
import {
  Alert, Badge, Card, Container, Table, Tabs, Text,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances, useLeaveHistory } from "../api/hooks";

export default function BalancesPage() {
  const [tab, setTab] = useState<string | null>("balances");
  const balancesQuery = useLeaveBalances();
  const historyQuery = useLeaveHistory();

  if (balancesQuery.error) {
    return <Container size="lg"><ErrorState error={balancesQuery.error} /></Container>;
  }

  const balances = balancesQuery.data?.balances ?? [];
  const history = historyQuery.data ?? [];

  return (
    <Container size="lg">
      <PageHeader title="Leave Balances and History" />
      <Tabs value={tab} onChange={setTab}>
        <Tabs.List>
          <Tabs.Tab value="balances">Balances</Tabs.Tab>
          <Tabs.Tab value="history">History</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="balances" pt="md">
          {balances.length === 0 ? (
            <Alert color="gray">No leave balances are available for your account.</Alert>
          ) : (
            <Card withBorder>
              <Table.ScrollContainer minWidth={640}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Entitlement</Table.Th>
                      <Table.Th>Used</Table.Th>
                      <Table.Th>Carry forward</Table.Th>
                      <Table.Th>Available</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {balances.map((balance) => (
                      <Table.Tr key={balance.leave_category_code}>
                        <Table.Td>{balance.category_label}</Table.Td>
                        <Table.Td>{balance.entitlement_per_year}</Table.Td>
                        <Table.Td>{balance.used_per_year}</Table.Td>
                        <Table.Td>{balance.carried_forward_from_previous}</Table.Td>
                        <Table.Td>
                          <Badge color={balance.available_days > 0 ? "green" : "gray"}>
                            {balance.available_days}
                          </Badge>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            </Card>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="history" pt="md">
          {historyQuery.error ? (
            <ErrorState error={historyQuery.error} />
          ) : history.length === 0 ? (
            <Alert color="gray">No leave history is available.</Alert>
          ) : (
            <Card withBorder>
              <Table.ScrollContainer minWidth={720}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Type</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Period</Table.Th>
                      <Table.Th>Decision</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {history.map((entry, index) => (
                      <Table.Tr key={entry.pk ?? "balance-" + index}>
                        <Table.Td>
                          {entry.type === "balance" ? "Balance snapshot" : "Application"}
                        </Table.Td>
                        <Table.Td>{entry.leave_category_code}</Table.Td>
                        <Table.Td>{entry.status ?? "—"}</Table.Td>
                        <Table.Td>
                          {entry.type === "balance"
                            ? "Year " + (entry.year ?? "—")
                            : entry.requested_start
                              ? entry.requested_start + " – " + (entry.requested_end ?? "")
                              : "—"}
                        </Table.Td>
                        <Table.Td>
                          {entry.type === "balance"
                            ? "—"
                            : entry.final_decision ? entry.status : "Pending"}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            </Card>
          )}
        </Tabs.Panel>
      </Tabs>
      <Text size="xs" c="dimmed" mt="sm">
        Balance totals reflect posted leave-account transactions.
      </Text>
    </Container>
  );
}
