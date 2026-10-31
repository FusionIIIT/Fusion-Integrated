import {
  Alert, Badge, Card, Container, Table,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveHistory } from "../api/hooks";

export default function HistoryPage() {
  const historyQuery = useLeaveHistory();

  if (historyQuery.error) {
    return <Container size="lg"><ErrorState error={historyQuery.error} /></Container>;
  }

  const history = historyQuery.data ?? [];

  return (
    <Container size="lg">
      <PageHeader title="Leave History" subtitle="Requests and recorded balance snapshots" />
      {history.length === 0 ? (
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
                  <Table.Th>Submitted</Table.Th>
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
                    <Table.Td>
                      {entry.status ? (
                        <Badge
                          color={
                            entry.status === "approved" ? "green"
                              : entry.status === "rejected" ? "red"
                              : entry.status === "withdrawn" ? "orange" : "blue"
                          }
                        >
                          {entry.status}
                        </Badge>
                      ) : "—"}
                    </Table.Td>
                    <Table.Td>
                      {entry.type === "balance"
                        ? "Year " + (entry.year ?? "—")
                        : entry.requested_start
                          ? entry.requested_start + " – " + (entry.requested_end ?? "")
                          : "—"}
                    </Table.Td>
                    <Table.Td>
                      {entry.submitted_at
                        ? new Date(entry.submitted_at).toLocaleDateString()
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
    </Container>
  );
}
