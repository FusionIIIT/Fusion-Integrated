import { Alert, Badge, Loader, Stack, Table, Text, Title } from "@mantine/core";

import { useAuditLogs } from "../api/hooks";
import type { AuditLogEntry } from "../api/types";

export default function AuditPage() {
  const { data: logs, isLoading, isError } = useAuditLogs();

  return (
    <Stack gap="lg" p="md">
      <div>
        <Title order={2}>Audit Logs</Title>
        <Text c="dimmed">Immutable compliance log of administrative actions, authentications, and security events.</Text>
      </div>

      {isLoading && (
        <Stack align="center" justify="center" p="xl" data-testid="loading-spinner">
          <Loader size="lg" />
          <Text c="dimmed">Loading audit events...</Text>
        </Stack>
      )}

      {isError && (
        <Alert color="red" title="Error loading logs" data-testid="error-message">
          Failed to retrieve audit records from the server.
        </Alert>
      )}

      {!isLoading && !isError && logs?.length === 0 && (
        <Alert color="blue" title="No audit logs" data-testid="empty-message">
          No audit records found.
        </Alert>
      )}

      {!isLoading && !isError && logs && logs.length > 0 && (
        <Table withTableBorder striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Timestamp</Table.Th>
              <Table.Th>Event Type</Table.Th>
              <Table.Th>Actor User ID</Table.Th>
              <Table.Th>Target Entity</Table.Th>
              <Table.Th>Target ID</Table.Th>
              <Table.Th>IP Address</Table.Th>
              <Table.Th>Integrity</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {logs.map((l: AuditLogEntry) => (
              <Table.Tr key={l.id}>
                <Table.Td>{new Date(l.created_at).toLocaleString()}</Table.Td>
                <Table.Td fw={500}>{l.event_type}</Table.Td>
                <Table.Td>{l.actor_user_id}</Table.Td>
                <Table.Td>{l.target_entity}</Table.Td>
                <Table.Td>{l.target_id}</Table.Td>
                <Table.Td>{l.ip_address || "internal"}</Table.Td>
                <Table.Td>
                  <Badge color="green" variant="light">Immutable</Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}
