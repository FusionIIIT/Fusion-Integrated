import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";
import { FaBan, FaCalendarPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCancelLeave, useMyLeaves } from "../api";
import type { LeaveRequest } from "../types";

function statusBadge(status: string) {
  switch (status) {
    case "approved":
      return <Badge color="teal" variant="filled">Approved</Badge>;
    case "rejected":
      return <Badge color="red" variant="filled">Rejected</Badge>;
    case "cancelled":
      return <Badge color="gray" variant="filled">Cancelled</Badge>;
    case "pending_current_authority":
      return <Badge color="yellow" variant="filled">Pending Authority</Badge>;
    default:
      return <Badge color="gray">{status}</Badge>;
  }
}

export default function MyLeavesPage() {
  const { data, isPending, error } = useMyLeaves();
  const cancelMutation = useCancelLeave();

  const [activeRequest, setActiveRequest] = useState<LeaveRequest | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleOpenCancel = (req: LeaveRequest) => {
    setActiveRequest(req);
    setCancelReason("");
  };

  const handleConfirmCancel = () => {
    if (!activeRequest) return;

    cancelMutation.mutate(
      {
        id: activeRequest.id,
        reason: cancelReason.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Leave Request Cancelled",
            message: `Leave request #${activeRequest.id} has been withdrawn successfully.`,
          });
          setActiveRequest(null);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Cancellation Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  const rows = data || [];

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="Track submitted leave requests, statuses, and decision outcomes"
        action={
          <Button
            component={Link}
            to="/leave/apply"
            leftSection={<FaCalendarPlus />}
            color="blue"
          >
            Apply for Leave
          </Button>
        }
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<LeaveRequest>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            title: "No leave requests submitted yet",
            description: "Use the button above to submit a new leave application.",
          }}
          columns={[
            {
              key: "leave_type",
              header: "Type",
              render: (r) => (
                <Text fw={600} style={{ textTransform: "capitalize" }}>
                  {r.leave_type} Leave
                </Text>
              ),
            },
            {
              key: "duration",
              header: "Duration",
              render: (r) => (
                <Stack gap={2}>
                  <Text size="sm" fw={500}>
                    {r.duration_days} day(s)
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.start_date} to {r.end_date}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "justification",
              header: "Justification",
              render: (r) => (
                <Text size="sm" lineClamp={2}>
                  {r.justification}
                </Text>
              ),
            },
            {
              key: "authority",
              header: "Routing Tier",
              render: (r) => (
                <Group gap="xs">
                  <Badge variant="outline" color="indigo">
                    {r.current_authority_role || "Designated Authority"}
                  </Badge>
                  {r.forward_count > 0 && (
                    <Badge variant="light" color="violet" size="xs">
                      Forwarded ({r.forward_count}x)
                    </Badge>
                  )}
                </Group>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => statusBadge(r.status),
            },
            {
              key: "decision",
              header: "Remarks / Status Info",
              render: (r) => {
                if (r.status === "cancelled") {
                  return (
                    <Stack gap={2}>
                      <Text size="xs" fw={500} c="dimmed">
                        WITHDRAWN BY APPLICANT
                      </Text>
                      {r.cancellation_reason && (
                        <Text size="xs" c="dimmed" fs="italic">
                          "{r.cancellation_reason}"
                        </Text>
                      )}
                    </Stack>
                  );
                }

                const latestDecision = r.decisions?.[r.decisions.length - 1];
                if (!latestDecision) {
                  return <Text size="xs" c="dimmed">Awaiting evaluation</Text>;
                }
                return (
                  <Stack gap={2}>
                    <Text size="xs" fw={500}>
                      {latestDecision.outcome.toUpperCase()}
                    </Text>
                    {latestDecision.remarks && (
                      <Text size="xs" c="dimmed" fs="italic">
                        "{latestDecision.remarks}"
                      </Text>
                    )}
                  </Stack>
                );
              },
            },
            {
              key: "actions",
              header: "Action",
              render: (r) => {
                if (r.status !== "pending_current_authority") {
                  return null;
                }
                return (
                  <Button
                    size="xs"
                    color="red"
                    variant="subtle"
                    leftSection={<FaBan />}
                    onClick={() => handleOpenCancel(r)}
                  >
                    Withdraw
                  </Button>
                );
              },
            },
          ]}
        />
      </Card>

      <Modal
        opened={Boolean(activeRequest)}
        onClose={() => setActiveRequest(null)}
        title={
          <Text fw={600}>
            Withdraw Leave Request #{activeRequest?.id}
          </Text>
        }
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to withdraw this application for{" "}
            <b>{activeRequest?.duration_days} day(s)</b> of{" "}
            <b>{activeRequest?.leave_type} leave</b>?
          </Text>

          <Textarea
            label="Reason for withdrawal (optional)"
            placeholder="e.g., travel plans cancelled, personal conflict resolved..."
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            minRows={3}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setActiveRequest(null)}>
              Keep Application
            </Button>
            <Button
              color="red"
              loading={cancelMutation.isPending}
              onClick={handleConfirmCancel}
            >
              Confirm Withdrawal
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
