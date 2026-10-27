import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaCheck, FaTimes, FaUndo } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLeaveRequests, useTransitionLeave } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function MyLeavesPage() {
  const { data: requests, isLoading, error } = useLeaveRequests();
  const transitionMutation = useTransitionLeave();

  const [cancelModalReq, setCancelModalReq] = useState<LeaveRequest | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleWithdraw = (req: LeaveRequest) => {
    transitionMutation.mutate(
      { id: req.id, to_status: "withdrawn", reason: "Applicant withdrew request" },
      {
        onSuccess: () => {
          notifications.show({
            title: "Request Withdrawn",
            message: `Leave #${req.id} was withdrawn successfully. Pending quota restored.`,
            color: "blue",
          });
        },
      }
    );
  };

  const handleCancel = () => {
    if (!cancelModalReq) return;
    transitionMutation.mutate(
      {
        id: cancelModalReq.id,
        to_status: "cancelled",
        reason: cancelReason || "Applicant requested cancellation before start date",
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Leave Cancelled",
            message: `Approved leave #${cancelModalReq.id} was cancelled. Quota restored.`,
            color: "orange",
          });
          setCancelModalReq(null);
          setCancelReason("");
        },
      }
    );
  };

  const rows = (requests || []).map((r) => {
    const isPending = [
      "draft",
      "awaiting_substitute",
      "unit_head_queue",
      "establishment",
      "final_decision",
    ].includes(r.status);
    const isApproved = r.status === "approved";

    return (
      <Table.Tr key={r.id}>
        <Table.Td fw={500}>#{r.id}</Table.Td>
        <Table.Td>
          <Badge variant="outline">{r.category}</Badge>
        </Table.Td>
        <Table.Td>
          {r.start_date} → {r.end_date}
          {r.half_day && (
            <Text size="xs" c="dimmed">
              ({r.half_day_period === "FN" ? "Forenoon" : "Afternoon"})
            </Text>
          )}
        </Table.Td>
        <Table.Td>{r.days_count} d</Table.Td>
        <Table.Td>
          <StatusBadge status={r.status} />
        </Table.Td>
        <Table.Td>
          {r.substitute_user_id ? (
            <Badge
              size="xs"
              color={
                r.substitute_status === "accepted"
                  ? "green"
                  : r.substitute_status === "declined"
                  ? "red"
                  : "yellow"
              }
            >
              u{r.substitute_user_id}: {r.substitute_status}
            </Badge>
          ) : (
            <Text size="xs" c="dimmed">
              None
            </Text>
          )}
        </Table.Td>
        <Table.Td>
          <Group gap="xs">
            {isPending && (
              <Button
                variant="light"
                color="red"
                size="xs"
                leftSection={<FaUndo />}
                onClick={() => handleWithdraw(r)}
                loading={transitionMutation.isPending}
              >
                Withdraw
              </Button>
            )}
            {isApproved && (
              <Button
                variant="subtle"
                color="orange"
                size="xs"
                leftSection={<FaTimes />}
                onClick={() => setCancelModalReq(r)}
              >
                Cancel
              </Button>
            )}
          </Group>
        </Table.Td>
      </Table.Tr>
    );
  });

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="My Leave Requests"
        description="Comprehensive history of all submitted leave applications, status progressions, and audit trails."
      />

      <Card withBorder radius="md" p="md" mt="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Substitute</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text ta="center" c="dimmed" py="md">
                    No leave requests found.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              rows
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal
        opened={Boolean(cancelModalReq)}
        onClose={() => setCancelModalReq(null)}
        title="Cancel Approved Leave"
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to cancel approved leave #{cancelModalReq?.id}?
            The deducted balance will be credited back to your account (BR-EL-023).
          </Text>
          <TextInput
            label="Cancellation Reason"
            placeholder="e.g., Event rescheduled"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCancelModalReq(null)}>
              Keep Leave
            </Button>
            <Button
              color="red"
              onClick={handleCancel}
              loading={transitionMutation.isPending}
            >
              Confirm Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
