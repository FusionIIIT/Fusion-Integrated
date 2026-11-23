import { Card, Container, Loader, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { FileAuditLog } from "../api/types";

export default function GovernancePage() {
  const { data: logs, isPending, error } = useAuditLogs();

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="FTS Governance Audit Trail"
        subtitle="Immutable audit history for file lifecycle transitions, movements, and administrator oversight."
      />

      {isPending && <Loader size="md" />}
      {error && <ErrorState error={error} />}

      {logs && (
        <Card withBorder radius="md" p="md">
          {logs.length === 0 ? (
            <Text c="dimmed">No audit logs recorded yet.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Timestamp</Table.Th>
                  <Table.Th>Action</Table.Th>
                  <Table.Th>File ID</Table.Th>
                  <Table.Th>Actor</Table.Th>
                  <Table.Th>IP Address</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {logs.map((l: FileAuditLog) => (
                  <Table.Tr key={l.id}>
                    <Table.Td>{new Date(l.created_at).toLocaleString()}</Table.Td>
                    <Table.Td>
                      <Text fw={500}>{l.action}</Text>
                    </Table.Td>
                    <Table.Td>{l.file_id ?? "—"}</Table.Td>
                    <Table.Td>
                      {l.actor_designation} (#{l.actor_user_id})
                    </Table.Td>
                    <Table.Td>{l.ip_address || "127.0.0.1"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      )}
    </Container>
  );
}
