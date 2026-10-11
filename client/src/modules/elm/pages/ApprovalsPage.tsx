import { Badge, Button, Container, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useApprovals, useApprovalAction } from "../api/hooks";
import { LeaveApplication } from "../api/types";

export default function ApprovalsPage() {
  const { data: queue = [], isLoading } = useApprovals();
  const actionMutation = useApprovalAction();

  const handleAction = (id: number, action: "approve" | "reject" | "recommend") => {
    actionMutation.mutate(
      { id, action },
      {
        onSuccess: () => {
          notifications.show({
            title: "Success",
            message: `Application ${action}ed successfully.`,
            color: "green",
          });
        },
        onError: () => {
          notifications.show({
            title: "Error",
            message: `Failed to ${action} application.`,
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        <div>
          <Title order={2}>Leave Approval Queue</Title>
          <Text c="dimmed" size="sm">Review pending leave applications requiring approval or recommendation</Text>
        </div>

        <Paper withBorder p="md" radius="sm">
          {isLoading ? (
            <Text>Loading approval queue...</Text>
          ) : queue.length === 0 ? (
            <Text c="dimmed">No pending applications awaiting approval.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Applicant ID</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {queue.map((app: LeaveApplication) => (
                  <Table.Tr key={app.id}>
                    <Table.Td>User #{app.applicant_id}</Table.Td>
                    <Table.Td><Badge variant="light">{app.leave_type}</Badge></Table.Td>
                    <Table.Td>{app.start_date} to {app.end_date}</Table.Td>
                    <Table.Td>{app.calculated_days}</Table.Td>
                    <Table.Td><Badge color="blue">{app.status}</Badge></Table.Td>
                    <Table.Td>{app.reason || "-"}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => handleAction(app.id, "approve")}
                          loading={actionMutation.isPending}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="yellow"
                          variant="outline"
                          onClick={() => handleAction(app.id, "recommend")}
                          loading={actionMutation.isPending}
                        >
                          Recommend
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="subtle"
                          onClick={() => handleAction(app.id, "reject")}
                          loading={actionMutation.isPending}
                        >
                          Reject
                        </Button>
                      </Group>
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
