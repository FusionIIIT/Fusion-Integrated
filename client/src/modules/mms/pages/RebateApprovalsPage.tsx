import { Alert, Button, Card, Container, Group, Stack, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecideRebate, useRebates } from "../api/hooks";

export default function RebateApprovalsPage() {
  const { data: rebates, isLoading, error } = useRebates();
  const decide = useDecideRebate();

  const handleDecide = (id: number, approve: boolean) => {
    decide.mutate(
      { id, data: { approve } },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: approve ? "Approved" : "Rejected",
            message: `Rebate #${id} marked as ${approve ? "Approved" : "Rejected"}.`,
          });
        },
        onError: (err) => notifications.show({ color: "red", title: "Action Failed", message: errorMessage(err) }),
      }
    );
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  const pending = rebates?.filter((r) => r.status === "pending") || [];

  return (
    <Container size="lg">
      <PageHeader title="Rebate Approvals" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Review mess rebate requests submitted by students (min 3 days duration).
        </Text>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Pending Rebates ({pending.length})</Text>
          {isLoading ? (
            <Text c="dimmed">Loading...</Text>
          ) : pending.length === 0 ? (
            <Alert color="gray">No pending rebate requests to review.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Student</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Requested Dates</Table.Th>
                  <Table.Th>Explanation</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pending.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>{r.student_user_id || r.user_id}</Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                    <Table.Td>{r.explanation || "—"}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" color="green" onClick={() => handleDecide(r.id, true)} loading={decide.isPending}>Approve</Button>
                        <Button size="xs" color="red" variant="outline" onClick={() => handleDecide(r.id, false)} loading={decide.isPending}>Reject</Button>
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
