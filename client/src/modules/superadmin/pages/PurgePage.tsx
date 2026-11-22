import { Alert, Badge, Button, Group, Loader, Stack, Table, Text, Title } from "@mantine/core";

import { useAuthorizePurge, usePurgeRequests } from "../api/hooks";
import type { PurgeRequest } from "../api/types";

export default function PurgePage() {
  const { data: requests, isLoading, isError } = usePurgeRequests();
  const authorizeMutation = useAuthorizePurge();

  return (
    <Stack gap="lg" p="md">
      <div>
        <Title order={2}>Purge Authorizations</Title>
        <Text c="dimmed">Dual-authorization control for permanent deletion of institutional data (BW-SA-01 / BW-SA-02).</Text>
      </div>

      {isLoading && (
        <Stack align="center" justify="center" p="xl" data-testid="loading-spinner">
          <Loader size="lg" />
          <Text c="dimmed">Loading purge authorization requests...</Text>
        </Stack>
      )}

      {isError && (
        <Alert color="red" title="Error loading requests" data-testid="error-message">
          Failed to retrieve purge requests from the server.
        </Alert>
      )}

      {!isLoading && !isError && requests?.length === 0 && (
        <Alert color="blue" title="No pending requests" data-testid="empty-message">
          No purge authorization requests currently pending.
        </Alert>
      )}

      {!isLoading && !isError && requests && requests.length > 0 && (
        <Table withTableBorder striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Request ID</Table.Th>
              <Table.Th>Archive ID</Table.Th>
              <Table.Th>Requester User ID</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Dual-Auth Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.map((r: PurgeRequest) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.id}</Table.Td>
                <Table.Td>{r.archive_record}</Table.Td>
                <Table.Td>{r.requested_by_user_id}</Table.Td>
                <Table.Td>{r.request_reason}</Table.Td>
                <Table.Td>
                  <Badge color={r.status === "PENDING" ? "orange" : r.status === "COMPLETED" ? "red" : "gray"}>
                    {r.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {r.status === "PENDING" && (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="red"
                        onClick={() => authorizeMutation.mutate({ requestId: r.id, action: "APPROVE" })}
                      >
                        Authorize Purge
                      </Button>
                      <Button
                        size="xs"
                        variant="default"
                        onClick={() => authorizeMutation.mutate({ requestId: r.id, action: "REJECT", reason: "Rejected by IT Head" })}
                      >
                        Reject
                      </Button>
                    </Group>
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
