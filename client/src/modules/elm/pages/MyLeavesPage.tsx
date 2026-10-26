import { Badge, Button, Container, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCancelLeave, useMyLeaves, useWithdrawLeave } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function MyLeavesPage() {
  const { data: leaves = [], isLoading } = useMyLeaves();
  const withdrawMutation = useWithdrawLeave();
  const cancelMutation = useCancelLeave();

  const handleWithdraw = (id: number) => {
    withdrawMutation.mutate(id, {
      onSuccess: () => {
        notifications.show({
          title: "Success",
          message: "Leave application withdrawn successfully.",
          color: "green",
        });
      },
      onError: (err: any) => {
        notifications.show({
          title: "Error",
          message: err?.response?.data?.error || "Failed to withdraw leave application.",
          color: "red",
        });
      },
    });
  };

  const handleCancelRequest = (id: number) => {
    cancelMutation.mutate(
      { id, reason: "Requested cancellation before leave start." },
      {
        onSuccess: () => {
          notifications.show({
            title: "Success",
            message: "Leave cancellation requested successfully.",
            color: "green",
          });
        },
        onError: (err: any) => {
          notifications.show({
            title: "Error",
            message: err?.response?.data?.error || "Failed to request leave cancellation.",
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        <Group justify="space-between">
          <div>
            <Title order={2}>My Leave Applications</Title>
            <Text c="dimmed" size="sm">Track the status of your submitted leave applications</Text>
          </div>
        </Group>

        <Paper withBorder p="md" radius="sm">
          {isLoading ? (
            <Text>Loading applications...</Text>
          ) : leaves.length === 0 ? (
            <Text c="dimmed">No leave applications found.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {leaves.map((app: LeaveApplication) => (
                  <Table.Tr key={app.id}>
                    <Table.Td>
                      <Badge variant="light">{app.leave_type}</Badge>
                      {app.half_day && <Text size="xs" c="dimmed">Half day ({app.half_day_type})</Text>}
                    </Table.Td>
                    <Table.Td>{app.start_date} to {app.end_date}</Table.Td>
                    <Table.Td>{app.calculated_days}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={
                          app.status === "approved"
                            ? "green"
                            : app.status === "rejected"
                            ? "red"
                            : app.status === "withdrawn"
                            ? "gray"
                            : app.status === "cancellation_requested"
                            ? "orange"
                            : app.status === "cancelled"
                            ? "dark"
                            : "blue"
                        }
                      >
                        {app.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{app.reason || "-"}</Table.Td>
                    <Table.Td>
                      {["submitted", "pending_substitute", "pending_unit_head", "pending_sanction"].includes(app.status) && (
                        <Button
                          size="xs"
                          variant="outline"
                          color="red"
                          onClick={() => handleWithdraw(app.id)}
                          loading={withdrawMutation.isPending}
                        >
                          Withdraw
                        </Button>
                      )}
                      {app.status === "approved" && (
                        <Button
                          size="xs"
                          variant="outline"
                          color="orange"
                          onClick={() => handleCancelRequest(app.id)}
                          loading={cancelMutation.isPending}
                        >
                          Cancel Leave
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Paper>
      </Stack>
    </Container>
  );
}
