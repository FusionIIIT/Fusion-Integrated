import { Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { downloadApplication, useApplications, useLeaveAction } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function MyLeavePage() {
  const { data, isPending, error } = useApplications();
  const action = useLeaveAction();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function run(id: number, path: string, body?: Record<string, unknown>) {
    action.mutate({ id, path, body }, {
      onSuccess: () => notifications.show({ color: "green", message: "Updated" }),
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leave" subtitle="Applications you submitted, and where they stand" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={(data?.results ?? []) as LeaveApplication[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            { key: "category", header: "Category", render: (r) => r.category },
            { key: "period", header: "Period",
              render: (r) => `${r.start_on} – ${r.end_on}` },
            { key: "days", header: "Days", render: (r) => r.chargeable_days },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "",
              render: (r) => (
                <Group gap="xs">
                  <Button size="xs" variant="light"
                    onClick={() => downloadApplication(r.id)}>Print</Button>
                  {["draft", "awaiting_substitute", "awaiting_unit_head",
                    "awaiting_establishment", "awaiting_final_sanction",
                    "awaiting_director_self_sanction"].includes(r.status) && (
                    <Button size="xs" color="gray" variant="light"
                      onClick={() => run(r.id, "withdraw")}>Withdraw</Button>
                  )}
                  {r.status === "approved" && (
                    <Button size="xs" variant="light"
                      onClick={() => run(r.id, "cancel", { reason: "Cancellation requested" })}>
                      Cancel
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
