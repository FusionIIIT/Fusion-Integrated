import { Badge, Button, Container, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useApprovalAction, useApprovals } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function ApprovalsPage() {
  const { data: queue = [], isLoading } = useApprovals();
  const actionMutation = useApprovalAction();

  const handleAction = (id: number, action: "approve" | "reject" | "recommend" | "not_recommend") => {
    actionMutation.mutate(
      { id, action },
      {
        onSuccess: () => {
          notifications.show({
            title: "Success",
            message: `Application action '${action}' recorded successfully.`,
            color: "green",
          });
        },
        onError: (err: any) => {
          notifications.show({
            title: "Action Failed",
            message: err?.response?.data?.error || "Failed to process approval action.",
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
          <Text c="dimmed" size="sm">Review, recommend, and approve pending employee leave applications</Text>
        </div>

        <Paper withBorder p="md" radius="sm">
          {isLoading ? (
            <Text>Loading approval queue...</Text>
          ) : queue.length === 0 ? (
            <Text c="dimmed">No leave applications currently pending your review.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Applicant</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {queue.map((app: LeaveApplication) => {
                  const isUnitHeadReview = app.status === "pending_unit_head";
                  const isHigherSanctionType = ["SCL", "EL", "COL", "VL"].includes(app.leave_type);

                  return (
                    <Table.Tr key={app.id}>
                      <Table.Td>User #{app.applicant_id}</Table.Td>
                      <Table.Td><Badge variant="light">{app.leave_type}</Badge></Table.Td>
                      <Table.Td>{app.start_date} to {app.end_date}</Table.Td>
                      <Table.Td>{app.calculated_days}</Table.Td>
                      <Table.Td><Badge color="blue">{app.status}</Badge></Table.Td>
                      <Table.Td>{app.reason || "-"}</Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          {isUnitHeadReview && isHigherSanctionType ? (
                            <>
                              <Button
                                size="xs"
                                color="yellow"
                                variant="filled"
                                onClick={() => handleAction(app.id, "recommend")}
                                loading={actionMutation.isPending}
                              >
                                Recommend
                              </Button>
                              <Button
                                size="xs"
                                color="orange"
                                variant="outline"
                                onClick={() => handleAction(app.id, "not_recommend")}
                                loading={actionMutation.isPending}
                              >
                                Not Recommend
                              </Button>
                            </>
                          ) : (
                            <>
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
                                color="red"
                                variant="subtle"
                                onClick={() => handleAction(app.id, "reject")}
                                loading={actionMutation.isPending}
                              >
                                Reject
                              </Button>
                            </>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          )}
        </Paper>
      </Stack>
    </Container>
  );
}
