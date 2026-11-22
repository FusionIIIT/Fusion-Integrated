import { Alert, Badge, Button, Group, Loader, Stack, Table, Text, Title } from "@mantine/core";

import { useArchives, useRequestPurge } from "../api/hooks";
import type { HistoricalArchive } from "../api/types";

export default function ArchivePage() {
  const { data: archives, isLoading, isError } = useArchives();
  const purgeMutation = useRequestPurge();

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Historical Archive Records</Title>
          <Text c="dimmed">Search and view institutional archives and retention schedules.</Text>
        </div>
      </Group>

      {isLoading && (
        <Stack align="center" justify="center" p="xl" data-testid="loading-spinner">
          <Loader size="lg" />
          <Text c="dimmed">Loading archive records...</Text>
        </Stack>
      )}

      {isError && (
        <Alert color="red" title="Error loading archives" data-testid="error-message">
          Failed to retrieve archive records from the server.
        </Alert>
      )}

      {!isLoading && !isError && archives?.length === 0 && (
        <Alert color="blue" title="No archives found" data-testid="empty-message">
          No historical archives currently recorded.
        </Alert>
      )}

      {!isLoading && !isError && archives && archives.length > 0 && (
        <Table withTableBorder striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Entity Type</Table.Th>
              <Table.Th>Identifier</Table.Th>
              <Table.Th>Backup Ref</Table.Th>
              <Table.Th>Purge Eligible At</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {archives.map((a: HistoricalArchive) => (
              <Table.Tr key={a.id}>
                <Table.Td>{a.id}</Table.Td>
                <Table.Td>{a.entity_type}</Table.Td>
                <Table.Td fw={500}>{a.record_identifier}</Table.Td>
                <Table.Td>{a.backup_reference}</Table.Td>
                <Table.Td>{new Date(a.purge_eligible_at).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <Badge color={a.status === "ARCHIVED" ? "blue" : a.status === "PURGED" ? "red" : "green"}>
                    {a.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {a.status === "ARCHIVED" && (
                    <Button
                      size="xs"
                      color="red"
                      variant="light"
                      onClick={() => purgeMutation.mutate({ archive_id: a.id, reason: "Retention expired purge request" })}
                    >
                      Request Purge
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}
