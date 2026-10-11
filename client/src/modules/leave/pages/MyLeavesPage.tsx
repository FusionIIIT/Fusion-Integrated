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
import { HistoryDrawer } from "../components/HistoryDrawer";
import { useMyApplications, useBalances, useHistory } from "../api/hooks";
import type { LeaveApplication, LeaveBalance } from "../api/types";

export default function MyLeavesPage() {
  const { data: applicationsData, isPending: appsPending, error: appsError } = useMyApplications();
  const { data: balancesData, isPending: balancesPending } = useBalances(new Date().getFullYear());
  const { data: historyData, isPending: historyPending } = useHistory();
  const [historyFor, setHistoryFor] = useState<number | null>(null);

  if (appsError) return <Container size="xl"><ErrorState error={appsError} /></Container>;

  function withdraw(app: LeaveApplication) {
    notifications.show({
      color: "gray", title: "Withdrawn",
      message: `Your application has been withdrawn.`,
    });
  }

  function cancel(app: LeaveApplication) {
    notifications.show({
      color: "blue", title: "Cancelled",
      message: `Your approved leave has been cancelled.`,
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="Track your leave balances and application history"
      />
      <Card padding="lg" mb="md">
        <Text fw={600} mb="xs">Leave Balance ({balancesData?.year})</Text>
        <Stack gap="sm">
          <Group justify="space-between">
            <Text>Earned Days: {balancesData?.earned_days ?? 0}</Text>
            <Text>Used Days: {balancesData?.used_days ?? 0}</Text>
          </Group>
          <Group justify="space-between">
            <Text>Remaining Days: {balancesData?.remaining_days ?? 0}</Text>
            <Text>Carry Forward: {balancesData?.carry_forward_days ?? 0}</Text>
          </Group>
        </Stack>
      </Card>

      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={(applicationsData?.results ?? []) as LeaveApplication[]}
          loading={appsPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "leave_type", header: "Type",
              render: (r) => r.leave_type.replace(/_/g, " "),
            },
            {
              key: "start_date", header: "Start Date",
              render: (r) => r.start_date ? new Date(r.start_date).toLocaleDateString() : "—",
            },
            {
              key: "end_date", header: "End Date",
              render: (r) => r.end_date ? new Date(r.end_date).toLocaleDateString() : "—",
            },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  <ActionIcon
                    variant="subtle" color="gray" aria-label="History"
                    onClick={() => setHistoryFor(r.id)}
                  >
                    <FaHistory size={12} />
                  </ActionIcon>
                  {r.status === "approved" && (
                    <Button
                      size="xs" variant="subtle" color="red"
                      onClick={() => cancel(r)}
                    >
                      Cancel
                    </Button>
                  )}
                  {r.status !== "approved" && r.status !== "cancelled" && (
                    <Button
                      size="xs" variant="subtle" color="gray"
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
            title: "No leave applications found",
            description: "Your leave applications will appear here.",
          }}
        />
      </Card>

      <HistoryDrawer
        applicationId={historyFor} onClose={() => setHistoryFor(null)}
      />
    </Container>
  );
}
