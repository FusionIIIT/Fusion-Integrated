import { useState } from "react";
import { Button, Card, Container, Group, NumberInput, SimpleGrid, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  CATEGORY_LABELS, useBalances, useCancel, useMyApplications, useReplaceSubstitute, useWithdraw,
  type LeaveApplication,
  type LeaveBalance,
} from "../api";

function ReplaceSubstitute({ id, substituteId, status }: { id: number; substituteId: number | null; status: string }) {
  const [subId, setSubId] = useState<string>("");
  const replace = useReplaceSubstitute();

  function handleSubmit() {
    if (!subId) return;
    replace.mutate({ id, substitute_id: Number(subId) }, {
      onSuccess: () => notifications.show({ color: "green", title: "Substitute nominated", message: "Your new substitute has been asked to confirm." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not nominate", message: errorMessage(e) }),
    });
  }

  return (
    <Group gap="xs">
      {status === "declined" ? (
        <>
          <NumberInput
            size="xs"
            placeholder="User ID"
            value={subId}
            onChange={(v) => setSubId(String(v))}
          />
          <Button size="xs" onClick={handleSubmit}>
            Nominate
          </Button>
        </>
      ) : (
        <Text size="sm">
          {substituteId ? `User ${substituteId} (${status.replace(/_/g, " ")})` : "-"}
        </Text>
      )}
    </Group>
  );
}

export default function MyLeavesPage() {
  const { data: applicationsData, isPending: appsPending, error: appsError } = useMyApplications();
  const { data: balancesData } = useBalances(new Date().getFullYear());
  const withdrawMutation = useWithdraw();
  const cancelMutation = useCancel();
  const today = new Date().toISOString().slice(0, 10);

  if (appsError) return <Container size="xl"><ErrorState error={appsError} /></Container>;

  function withdraw(app: LeaveApplication) {
    withdrawMutation.mutate({ id: app.id }, {
      onSuccess: () => notifications.show({ color: "gray", title: "Withdrawn", message: "Your application has been withdrawn." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not withdraw", message: errorMessage(e) }),
    });
  }

  function cancel(app: LeaveApplication) {
    cancelMutation.mutate({ id: app.id }, {
      onSuccess: () => notifications.show({ color: "blue", title: "Cancellation requested", message: "Your cancellation request has been sent for approval." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not cancel", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leaves" subtitle="Your leave balances and requests" />
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md" mb="md">
        {(balancesData ?? []).map((b: LeaveBalance) => (
          <Card padding="sm" key={b.category}>
            <Text fw={600} size="sm">{CATEGORY_LABELS[b.category]} ({b.year})</Text>
            <Group gap="xs" mt="xs">
              <Text size="sm">Available: {Number(b.available)}/Entitled: {Number(b.entitled)}</Text>
              <Text size="sm">Used: {Number(b.used)}</Text>
            </Group>
          </Card>
        ))}
      </SimpleGrid>

      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={applicationsData ?? []}
          loading={appsPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "category", header: "Type",
              render: (r) => `${CATEGORY_LABELS[r.category]} ${r.kind === "cancellation" ? "(cancellation)" : ""}`,
            },
            {
              key: "start_date", header: "Start Date",
              render: (r) => r.start_date ? new Date(r.start_date).toLocaleDateString() : "—",
            },
            {
              key: "end_date", header: "End Date",
              render: (r) => r.end_date ? new Date(r.end_date).toLocaleDateString() : "—",
            },
            {
              key: "days", header: "Days",
              render: (r) => Number(r.days),
            },
            {
              key: "stage", header: "Stage",
              render: (r) => r.stage.replace(/_/g, " "),
            },
            {
              key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "substitute", header: "Substitute",
              render: (r) => (
                <ReplaceSubstitute
                  id={r.id}
                  substituteId={r.substitute_id}
                  status={r.substitute_status}
                />
              ),
            },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {r.status === "pending" && r.kind === "leave" && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      onClick={() => withdraw(r)}
                    >
                      Withdraw
                    </Button>
                  )}
                  {r.status === "approved" && r.kind === "leave" && new Date(r.start_date) > new Date(today) && (
                    <Button
                      size="xs" variant="subtle" color="red"
                      onClick={() => cancel(r)}
                    >
                      Cancel leave
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            title: "No leave requests yet",
            description: "Requests you apply for appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
