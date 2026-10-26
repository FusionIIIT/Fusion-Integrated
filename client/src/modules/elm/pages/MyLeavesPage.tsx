import { Badge, Button, Card, Container, Group, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBan, FaPlus, FaUndo } from "react-icons/fa";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { errorMessage } from "../../../lib/http";
import { useCancelLeave, useMyLeaveApplications, useWithdrawLeave } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

function statusColor(status: string) {
  switch (status) {
    case "approved":
      return "green";
    case "rejected":
      return "red";
    case "withdrawn":
    case "cancelled":
      return "gray";
    case "recommended":
      return "teal";
    case "not_recommended":
      return "orange";
    case "submitted":
    default:
      return "blue";
  }
}

export default function MyLeavesPage() {
  const { data: applications, error } = useMyLeaveApplications();
  const withdraw = useWithdrawLeave();
  const cancel = useCancelLeave();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleWithdraw(app: LeaveApplication) {
    withdraw.mutate(app.id, {
      onSuccess: () => {
        notifications.show({
          color: "blue",
          title: "Application Withdrawn",
          message: `Leave #${app.id} (${app.category}) has been withdrawn and balance restored.`,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Withdrawal Failed",
          message: errorMessage(err),
        });
      },
    });
  }

  function handleCancel(app: LeaveApplication) {
    cancel.mutate(app.id, {
      onSuccess: () => {
        notifications.show({
          color: "gray",
          title: "Leave Cancelled",
          message: `Leave #${app.id} has been cancelled and balance restored.`,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Cancellation Failed",
          message: errorMessage(err),
        });
      },
    });
  }

  return (
    <Container size="xl">
      <Group justify="space-between" align="flex-end" mb="md">
        <PageHeader
          title="My Leaves"
          subtitle="Track your leave applications, status transitions, and responsibility coverage (CW-EL-01/02)"
        />
        <Button
          component={Link}
          to="/elm/apply"
          leftSection={<FaPlus />}
          color="blue"
        >
          Apply for Leave
        </Button>
      </Group>

      <Card withBorder radius="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Interval</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Substitute</Table.Th>
              <Table.Th>Station Leave</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(applications ?? []).map((app) => {
              const canWithdraw = ["submitted", "recommended", "not_recommended"].includes(app.status);
              const canCancel = app.status === "approved" && new Date(app.leave_start) > new Date();

              return (
                <Table.Tr key={app.id}>
                  <Table.Td fw={700}>#{app.id}</Table.Td>
                  <Table.Td>
                    <Badge variant="outline">{app.category}</Badge>
                    {app.is_half_day && (
                      <Badge size="xs" color="indigo" ml={4}>
                        Half ({app.half_day})
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">
                      {app.leave_start} to {app.leave_end}
                    </Text>
                  </Table.Td>
                  <Table.Td fw={600}>{app.computed_days}d</Table.Td>
                  <Table.Td>
                    {app.substitute_user_id ? (
                      <Badge
                        size="xs"
                        color={
                          app.substitute_status === "accepted"
                            ? "green"
                            : app.substitute_status === "declined"
                            ? "red"
                            : "yellow"
                        }
                      >
                        u{app.substitute_user_id} ({app.substitute_status})
                      </Badge>
                    ) : (
                      <Text size="xs" c="dimmed">None</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {app.station_leave_required ? (
                      <Badge color="orange" size="xs">
                        {app.station_leave_city || "Yes"}
                      </Badge>
                    ) : (
                      <Text size="xs" c="dimmed">No</Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Badge color={statusColor(app.status)} variant="filled">
                      {app.status.replace("_", " ").toUpperCase()}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {canWithdraw && (
                        <Button
                          size="xs"
                          variant="light"
                          color="red"
                          leftSection={<FaUndo />}
                          loading={withdraw.isPending}
                          onClick={() => handleWithdraw(app)}
                        >
                          Withdraw
                        </Button>
                      )}
                      {canCancel && (
                        <Button
                          size="xs"
                          variant="outline"
                          color="red"
                          leftSection={<FaBan />}
                          loading={cancel.isPending}
                          onClick={() => handleCancel(app)}
                        >
                          Cancel
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
