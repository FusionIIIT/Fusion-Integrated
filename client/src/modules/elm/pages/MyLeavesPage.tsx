import { Badge, Button, Card, Container, Group, Modal, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBan, FaPlus, FaUndo } from "react-icons/fa";
import { Link } from "react-router-dom";
import { useState } from "react";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { errorMessage } from "../../../lib/http";
import {
  useCancelLeave,
  useExtendLeave,
  useMyLeaveApplications,
  useRecordResumption,
  useWithdrawLeave,
} from "../api/hooks";
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
  const extend = useExtendLeave();
  const resumption = useRecordResumption();
  const [dialog, setDialog] = useState<{
    kind: "extend" | "resume";
    app: LeaveApplication;
  } | null>(null);
  const [dateValue, setDateValue] = useState("");
  const [purpose, setPurpose] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleWithdraw(app: LeaveApplication) {
    if (!window.confirm(`Withdraw leave #${app.id} and restore its balance?`)) return;
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
    if (!window.confirm(`Cancel approved leave #${app.id} and restore its balance?`)) return;
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

  function openDialog(kind: "extend" | "resume", app: LeaveApplication) {
    setDialog({ kind, app });
    setDateValue(kind === "extend" ? app.leave_end : new Date().toISOString().slice(0, 10));
    setPurpose("");
  }

  function closeDialog() {
    setDialog(null);
    setDateValue("");
    setPurpose("");
  }

  function submitDialog() {
    if (!dialog || !dateValue) return;
    if (dialog.kind === "extend") {
      extend.mutate(
        { applicationId: dialog.app.id, extendedEndDate: dateValue, purpose },
        {
          onSuccess: () => {
            closeDialog();
            notifications.show({ color: "blue", title: "Extension Submitted", message: "The extension is now in the approval workflow." });
          },
          onError: (err) => notifications.show({ color: "red", title: "Extension Failed", message: errorMessage(err) }),
        }
      );
    } else {
      resumption.mutate(
        { applicationId: dialog.app.id, actualResumptionDate: dateValue },
        {
          onSuccess: () => {
            closeDialog();
            notifications.show({ color: "green", title: "Resumption Recorded", message: "Your leave balance has been adjusted." });
          },
          onError: (err) => notifications.show({ color: "red", title: "Resumption Failed", message: errorMessage(err) }),
        }
      );
    }
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
              const canExtend = app.status === "approved" && ["EL", "COL", "VL"].includes(app.category) && !app.is_resumption && new Date(app.leave_end).getTime() >= Date.now();
              const canResume = app.status === "approved" && !app.is_resumption && new Date(app.leave_start).getTime() <= Date.now();

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
                      {canExtend && (
                        <Button size="xs" variant="light" onClick={() => openDialog("extend", app)}>
                          Extend
                        </Button>
                      )}
                      {canResume && (
                        <Button size="xs" variant="light" color="teal" onClick={() => openDialog("resume", app)}>
                          Resume
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

      <Modal
        opened={dialog !== null}
        onClose={closeDialog}
        title={dialog?.kind === "extend" ? "Request Leave Extension" : "Record Resumption"}
      >
        <TextInput
          type="date"
          label={dialog?.kind === "extend" ? "New end date" : "Actual resumption date"}
          value={dateValue}
          onChange={(event) => setDateValue(event.currentTarget.value)}
          required
        />
        {dialog?.kind === "extend" && (
          <TextInput
            mt="md"
            label="Purpose"
            value={purpose}
            onChange={(event) => setPurpose(event.currentTarget.value)}
            required
          />
        )}
        <Group justify="flex-end" mt="lg">
          <Button variant="default" onClick={closeDialog}>Close</Button>
          <Button
            onClick={submitDialog}
            loading={extend.isPending || resumption.isPending}
            disabled={!dateValue || (dialog?.kind === "extend" && !purpose.trim())}
          >
            Submit
          </Button>
        </Group>
      </Modal>
    </Container>
  );
}
