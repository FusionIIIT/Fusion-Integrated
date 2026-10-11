import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaHistory, FaUserCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { CpiBadge } from "../../placement/components/CpiBadge";
import { HistoryDrawer } from "../../placement/components/HistoryDrawer";
import { useLeaveRequests, useTransition } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function LeaveRequestsPage() {
  const { data, isPending, error } = useLeaveRequests();
  const transition = useTransition();
  const [historyFor, setHistoryFor] = useState<number | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function approve(request: LeaveRequest) {
    transition.mutate(
      { id: request.id, to_status: "approved", reason: "Approved by the employee" },
      {
        onSuccess: () => notifications.show({
          color: "green", title: "Approved",
          message: `Your leave application for ${request.leave_type} from ${request.start_date} to ${request.end_date} has been approved.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not approve", message: errorMessage(e),
        }),
      },
    );
  }

  function cancel(request: LeaveRequest) {
    transition.mutate(
      { id: request.id, to_status: "cancelled", reason: "Cancelled by the employee" },
      {
        onSuccess: () => notifications.show({
          color: "red", title: "Cancelled",
          message: `Your leave application for ${request.leave_type} from ${request.start_date} to ${request.end_date} has been cancelled.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not cancel", message: errorMessage(e),
        }),
      },
    );
  }

  function withdraw(request: LeaveRequest) {
    transition.mutate(
      { id: request.id, to_status: "withdrawn", reason: "Withdrawn by the employee" },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Withdrawn",
          message: `Your leave application for ${request.leave_type} from ${request.start_date} to ${request.end_date} has been withdrawn.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not withdraw", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Requests"
        subtitle="All leave requests you have submitted, and where they stand"
      />
      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={(data?.results ?? []) as LeaveRequest[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "leave_type", header: "Leave Type",
              render: (r) => (
                <Text fw={600}>{r.leave_type}</Text>
              ),
            },
            { key: "start_date", header: "Start Date",
              render: (r) => r.start_date
                ? new Date(r.start_date).toLocaleDateString() : "—" },
            { key: "end_date", header: "End Date",
              render: (r) => r.end_date
                ? new Date(r.end_date).toLocaleDateString() : "—" },
            { key: "reason", header: "Reason",
              render: (r) => (
                <Text size="sm" c="dimmed">{r.reason}</Text>
              ),
            },
            {
              key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {/* "Why is my application at this status?" answered without
                      a support request. */}
                  <ActionIcon
                    variant="subtle" color="gray" aria-label="History"
                    onClick={() => setHistoryFor(r.id)}
                  >
                    <FaHistory size={12} />
                  </ActionIcon>
                  {r.allowed_transitions?.includes("approved") && (
                    <Button
                      size="xs" variant="subtle" color="green"
                      loading={transition.isPending}
                      onClick={() => approve(r)}
                    >
                      Approve
                    </Button>
                  )}
                  {r.allowed_transitions?.includes("cancelled") && (
                    <Button
                      size="xs" variant="subtle" color="red"
                      loading={transition.isPending}
                      onClick={() => cancel(r)}
                    >
                      Cancel
                    </Button>
                  )}
                  {r.allowed_transitions?.includes("withdrawn") && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      loading={transition.isPending}
                      onClick={() => withdraw(r)}
                    >
                      Withdraw
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaUserCheck,
            title: "You have not submitted any leave requests yet",
            description: "Leave requests you submit will be tracked here.",
          }}
        />
      </Card>

      <HistoryDrawer
        applicationId={historyFor} onClose={() => setHistoryFor(null)}
      />
    </Container>
  );
}
