import { Alert, Button, Card, Container, Group, Stack, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecideDeregistration, useDeregistrations } from "../api/hooks";

export default function DeregistrationApprovalsPage() {
  const { data: deregistrations, isLoading, error } = useDeregistrations();
  const decide = useDecideDeregistration();

  const handleDecide = (id: number, approve: boolean) => {
    decide.mutate(
      { id, data: { approve } },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: approve ? "Approved" : "Rejected",
            message: `Deregistration #${id} marked as ${approve ? "Approved" : "Rejected"}.`,
          });
        },
        onError: (err) => notifications.show({ color: "red", title: "Action Failed", message: errorMessage(err) }),
      }
    );
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  const pending = deregistrations?.filter((d) => d.status === "pending") || [];

  return (
    <Container size="lg">
      <PageHeader title="Deregistration Approvals" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Review student deregistration requests. Approved deregistrations take effect on the next calendar day.
        </Text>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Pending Requests ({pending.length})</Text>
          {isLoading ? (
            <Text c="dimmed">Loading...</Text>
          ) : pending.length === 0 ? (
            <Alert color="gray">No pending deregistration requests to review.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Student User ID</Table.Th>
                  <Table.Th>Submitted At</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pending.map((d) => (
                  <Table.Tr key={d.id}>
                    <Table.Td>#{d.id}</Table.Td>
                    <Table.Td>{d.student_user_id || d.user_id}</Table.Td>
                    <Table.Td>{new Date(d.submitted_at).toLocaleString()}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" color="green" onClick={() => handleDecide(d.id, true)} loading={decide.isPending}>Approve</Button>
                        <Button size="xs" color="red" variant="outline" onClick={() => handleDecide(d.id, false)} loading={decide.isPending}>Reject</Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
