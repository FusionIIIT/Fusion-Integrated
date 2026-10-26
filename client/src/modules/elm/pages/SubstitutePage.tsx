import { Badge, Button, Container, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useSubstituteAction, useSubstituteRequests } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function SubstitutePage() {
  const { data: requests = [], isLoading } = useSubstituteRequests();
  const actionMutation = useSubstituteAction();

  const handleAction = (id: number, action: "accept" | "decline") => {
    actionMutation.mutate(
      { id, action },
      {
        onSuccess: () => {
          notifications.show({
            title: "Success",
            message: `Substitute request ${action}ed successfully.`,
            color: "green",
          });
        },
        onError: () => {
          notifications.show({
            title: "Error",
            message: `Failed to ${action} substitute request.`,
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
          <Title order={2}>Substitute Requests</Title>
          <Text c="dimmed" size="sm">Requests where you have been nominated as a substitute for an employee on leave</Text>
        </div>

        <Paper withBorder p="md" radius="sm">
          {isLoading ? (
            <Text>Loading substitute requests...</Text>
          ) : requests.length === 0 ? (
            <Text c="dimmed">No pending substitute requests found.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Applicant ID</Table.Th>
                  <Table.Th>Leave Type</Table.Th>
                  <Table.Th>Period</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {requests.map((app: LeaveApplication) => (
                  <Table.Tr key={app.id}>
                    <Table.Td>User #{app.applicant_id}</Table.Td>
                    <Table.Td><Badge variant="light">{app.leave_type}</Badge></Table.Td>
                    <Table.Td>{app.start_date} to {app.end_date}</Table.Td>
                    <Table.Td>{app.reason || "-"}</Table.Td>
                    <Table.Td><Badge color="orange">{app.substitute_status}</Badge></Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => handleAction(app.id, "accept")}
                          loading={actionMutation.isPending}
                        >
                          Accept
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="outline"
                          onClick={() => handleAction(app.id, "decline")}
                          loading={actionMutation.isPending}
                        >
                          Decline
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
