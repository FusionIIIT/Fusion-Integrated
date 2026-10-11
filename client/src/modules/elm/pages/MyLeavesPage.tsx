import { useState } from "react";
import { ActionIcon, Button, Card, Container, Group, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaHistory } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { HistoryDrawer } from "../components/HistoryDrawer";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";
import { useMyApplications, useTransition } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function MyLeavesPage() {
  const { data, isPending, error } = useMyApplications();
  const transition = useTransition();
  const [historyFor, setHistoryFor] = useState<number | null>(null);

  if (error) {
    return <Container size="xl"><ErrorState error={error} /></Container>;
  }

  function move(application: LeaveApplication, toStatus: string) {
    transition.mutate(
      { id: application.id, to_status: toStatus },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Updated",
          message: `Your ${application.leave_type.code} request is now ${toStatus}.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not update", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="Everything you have submitted, and where it stands"
      />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={(data?.results ?? []) as LeaveApplication[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={860}
          empty={{
            title: "No leave requests yet",
            description: "Use Apply for Leave to submit your first request.",
          }}
          columns={[
            {
              key: "type", header: "Type",
              render: (r) => (
                <Text fw={600}>{r.leave_type.code} — {r.leave_type.name}</Text>
              ),
            },
            {
              key: "dates", header: "Dates",
              render: (r) => (
                <Text size="sm">
                  {r.start_date} → {r.end_date}
                  {r.is_half_day && ` (${r.half_day_part} half)`}
                </Text>
              ),
            },
            { key: "days", header: "Days", render: (r) => r.days },
            {
              key: "status", header: "Status",
              render: (r) => <LeaveStatusBadge status={r.status} />,
            },
            {
              key: "note", header: "Decision note",
              render: (r) => (
                <Text size="sm" c="dimmed">{r.decision_note || "—"}</Text>
              ),
            },
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
                  {r.allowed_transitions.includes("withdrawn") && (
                    <Button size="xs" variant="subtle" color="gray"
                            loading={transition.isPending}
                            onClick={() => move(r, "withdrawn")}>
                      Withdraw
                    </Button>
                  )}
                  {r.allowed_transitions.includes("cancelled") && (
                    <Button size="xs" variant="subtle" color="red"
                            loading={transition.isPending}
                            onClick={() => move(r, "cancelled")}>
                      Cancel
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>
      <HistoryDrawer applicationId={historyFor} onClose={() => setHistoryFor(null)} />
    </Container>
  );
}
