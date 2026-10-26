import { Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaHistory } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { useLeaveTypes, useMyApplications, useWithdraw, useCancelLeave } from "../../../modules/elm/api";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { ErrorState } from "../../../ui/components/ErrorState";
import { DataTable } from "../../../ui/components/DataTable";
import type { LeaveApplication } from "../../../modules/elm/api";

export default function MyLeavePage() {
  const { data: leaveTypes } = useLeaveTypes();
  const { data: applications, isPending, error } = useMyApplications();
  const withdraw = useWithdraw();
  const cancelLeave = useCancelLeave();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const typeName = (id: number) => leaveTypes?.find(t => t.id === id)?.name ?? "leave";

  function handleWithdraw(app: LeaveApplication) {
    withdraw.mutate(
      { id: app.id },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Withdrawn",
          message: `Your ${typeName(app.leave_type)} application has been withdrawn.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not withdraw", message: errorMessage(e),
        }),
      },
    );
  }

  function handleCancel(app: LeaveApplication) {
    cancelLeave.mutate(
      { id: app.id },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Cancelled",
          message: `Your ${typeName(app.leave_type)} application has been cancelled.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not cancel", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leave Applications" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={applications ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "leave_type", header: "Leave type",
              render: (r) => typeName(r.leave_type),
            },
            { key: "start_date", header: "From", render: (r) => r.start_date },
            { key: "end_date", header: "To", render: (r) => r.end_date },
            { key: "days", header: "Days", render: (r) => r.days },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status.toLowerCase()} /> },
            { key: "remarks", header: "Remarks", render: (r) => r.remarks },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {r.status.toLowerCase() === "submitted" && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      loading={withdraw.isPending}
                      onClick={() => handleWithdraw(r)}
                    >
                      Withdraw
                    </Button>
                  )}
                  {r.status.toLowerCase() === "approved" && new Date(r.start_date) > new Date() && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      loading={cancelLeave.isPending}
                      onClick={() => handleCancel(r)}
                    >
                      Cancel
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaHistory,
            title: "No leave applications yet",
            description: "Applications you submit will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
