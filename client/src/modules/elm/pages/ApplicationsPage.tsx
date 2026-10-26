import { Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarCheck, FaPlus } from "react-icons/fa";
import { Link } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLeaveApplications, useWithdrawLeaveApplication } from "../api";
import type { LeaveApplication } from "../types";

export default function ApplicationsPage() {
  const { data, isPending, error } = useLeaveApplications();
  const withdraw = useWithdrawLeaveApplication();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const applications = (data ?? []) as LeaveApplication[];

  function handleWithdraw(app: LeaveApplication) {
    withdraw.mutate(app.id, {
      onSuccess: () => {
        notifications.show({
          color: "gray",
          title: "Withdrawn",
          message: "Your leave application has been withdrawn.",
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Could not withdraw",
          message: errorMessage(err),
        });
      },
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave Applications"
        subtitle="Track your submitted leave requests and their current status"
        action={
          <Button
            component={Link}
            to="/elm/apply"
            leftSection={<FaPlus size={14} />}
          >
            Apply for Leave
          </Button>
        }
      />
      <Card padding="lg" withBorder>
        <DataTable<LeaveApplication>
          rows={applications}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            {
              key: "type",
              header: "Leave Type",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.leave_type_name || `Type #${r.leave_type}`}</Text>
                  {r.leave_type_code && (
                    <Text size="xs" c="dimmed">
                      {r.leave_type_code}
                    </Text>
                  )}
                </Stack>
              ),
            },
            {
              key: "start_date",
              header: "From",
              render: (r) => r.start_date,
            },
            {
              key: "end_date",
              header: "To",
              render: (r) => r.end_date,
            },
            {
              key: "reason",
              header: "Reason",
              render: (r) => r.reason || "—",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Applied On",
              render: (r) =>
                r.created_at ? new Date(r.created_at).toLocaleDateString() : "—",
            },
            {
              key: "actions",
              header: "",
              align: "right",
              render: (r) => (
                <Group justify="flex-end">
                  {r.status === "pending" && (
                    <Button
                      size="xs"
                      variant="subtle"
                      color="red"
                      loading={withdraw.isPending}
                      onClick={() => handleWithdraw(r)}
                    >
                      Withdraw
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaCalendarCheck,
            title: "No leave applications found",
            description: "Applications you submit will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
