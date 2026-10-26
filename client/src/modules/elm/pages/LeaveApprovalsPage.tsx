import { Badge, Button, Card, Container, Group, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovalQueue, useReviewLeave } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function LeaveApprovalsPage() {
  const { data: queue, isPending, error } = useApprovalQueue();
  const reviewMutation = useReviewLeave();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleAction(id: number, action: "APPROVED" | "REJECTED") {
    const verb = action === "APPROVED" ? "approve" : "reject";
    if (!window.confirm(`Are you sure you want to ${verb} this leave application?`)) return;

    reviewMutation.mutate(
      { id, action },
      {
        onSuccess: () => {
          notifications.show({
            color: action === "APPROVED" ? "green" : "red",
            title: action === "APPROVED" ? "Approved" : "Rejected",
            message: `Leave application #${id} has been ${action.toLowerCase()}.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Review Action Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Approval Queue"
        subtitle="Review and process pending leave applications from employees and students"
      />

      <Card padding="lg" withBorder>
        {isPending ? (
          <Text c="dimmed">Loading approval queue...</Text>
        ) : !queue?.length ? (
          <Text c="dimmed">No pending leave applications to review.</Text>
        ) : (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Applicant</Table.Th>
                <Table.Th>Leave Type</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Substitute</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {queue.map((app: LeaveApplication) => (
                <Table.Tr key={app.id}>
                  <Table.Td>#{app.id}</Table.Td>
                  <Table.Td fw={500}>{app.applicant_name}</Table.Td>
                  <Table.Td><Badge color="blue" variant="light">{app.leave_type}</Badge></Table.Td>
                  <Table.Td>{app.start_date} to {app.end_date}</Table.Td>
                  <Table.Td>{app.reason}</Table.Td>
                  <Table.Td>{app.substitute_name ?? "-"}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="green"
                        leftSection={<FaCheck />}
                        loading={reviewMutation.isPending}
                        onClick={() => handleAction(app.id, "APPROVED")}
                      >
                        Approve
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="outline"
                        leftSection={<FaTimes />}
                        loading={reviewMutation.isPending}
                        onClick={() => handleAction(app.id, "REJECTED")}
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
      </Card>
    </Container>
  );
}

