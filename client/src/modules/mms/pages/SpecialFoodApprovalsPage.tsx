import { Alert, Button, Card, Container, Group, Stack, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useDecideSpecialFoodRequest,
  useFulfillSpecialFoodRequest,
  useSpecialFoodRequests,
} from "../api/hooks";

export default function SpecialFoodApprovalsPage() {
  const { data: requests, isLoading, error } = useSpecialFoodRequests();
  const decide = useDecideSpecialFoodRequest();
  const fulfill = useFulfillSpecialFoodRequest();

  const handleDecide = (id: number, approve: boolean) => {
    decide.mutate(
      { id, data: { approve } },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: approve ? "Approved" : "Rejected",
            message: `Special food #${id} decided.`,
          });
        },
        onError: (err) => notifications.show({ color: "red", title: "Action Failed", message: errorMessage(err) }),
      }
    );
  };

  const handleFulfill = (id: number, status: "served" | "cancelled") => {
    fulfill.mutate(
      { id, data: { status } },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: `Marked as ${status}`,
            message: `Special food #${id} fulfillment recorded as ${status}.`,
          });
        },
        onError: (err) => notifications.show({ color: "red", title: "Action Failed", message: errorMessage(err) }),
      }
    );
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  const pending = requests?.filter((r) => r.status === "requested") || [];
  const approved = requests?.filter((r) => r.status === "approved") || [];

  return (
    <Container size="lg">
      <PageHeader title="Special Food Approvals & Fulfillment" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Pending Special Food Requests ({pending.length})</Text>
          {isLoading ? (
            <Text c="dimmed">Loading...</Text>
          ) : pending.length === 0 ? (
            <Alert color="gray">No pending special food requests requiring decision.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Student</Table.Th>
                  <Table.Th>Date</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Decision Due</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pending.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>{r.student_user_id || r.user_id}</Table.Td>
                    <Table.Td>{r.requested_date}</Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>{r.decision_due_at ? new Date(r.decision_due_at).toLocaleString() : "—"}</Table.Td>
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

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Approved Requests Pending Fulfillment ({approved.length})</Text>
          {approved.length === 0 ? (
            <Alert color="gray">No approved requests awaiting meal fulfillment.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Student</Table.Th>
                  <Table.Th>Date</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {approved.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>{r.student_user_id || r.user_id}</Table.Td>
                    <Table.Td>{r.requested_date}</Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" color="blue" onClick={() => handleFulfill(r.id, "served")} loading={fulfill.isPending}>Record Served</Button>
                        <Button size="xs" color="gray" variant="outline" onClick={() => handleFulfill(r.id, "cancelled")} loading={fulfill.isPending}>Mark Cancelled</Button>
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
