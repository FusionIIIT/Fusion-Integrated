import { Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useApplications, useLeaveAction } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function QueuePage() {
  const { data, isPending, error } = useApplications();
  const action = useLeaveAction();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function run(id: number, path: string, body: Record<string, unknown>) {
    action.mutate({ id, path, body }, {
      onSuccess: () => notifications.show({ color: "green", message: "Recorded" }),
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  const rows = (data?.results ?? []).filter((r) =>
    ["awaiting_unit_head", "awaiting_establishment", "awaiting_resumption_verification",
     "cancellation_pending"].includes(r.status));

  return (
    <Container size="xl">
      <PageHeader title="Review queue" subtitle="Unit Head recommendation and Establishment routing" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={rows} loading={isPending} rowKey={(r) => r.id} minWidth={900}
          columns={[
            { key: "user_id", header: "Employee", render: (r) => String(r.user_id) },
            { key: "category", header: "Category", render: (r) => r.category },
            { key: "period", header: "Period", render: (r) => `${r.start_on} – ${r.end_on}` },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "",
              render: (r) => (
                <Group gap="xs">
                  {r.status === "awaiting_unit_head" && ["CL", "RH"].includes(r.category) && (
                    <>
                      <Button size="xs" onClick={() => run(r.id, "unit-head", { action: "approve" })}>Approve</Button>
                      <Button size="xs" color="red" variant="light"
                        onClick={() => run(r.id, "unit-head", { action: "reject" })}>Reject</Button>
                    </>
                  )}
                  {r.status === "awaiting_unit_head" && !["CL", "RH"].includes(r.category) && (
                    <>
                      <Button size="xs" onClick={() => run(r.id, "unit-head", { action: "recommend" })}>Recommend</Button>
                      <Button size="xs" variant="light"
                        onClick={() => run(r.id, "unit-head", { action: "not_recommend" })}>Not recommended</Button>
                    </>
                  )}
                  {r.status === "awaiting_establishment" && (
                    <Button size="xs" onClick={() => run(r.id, "establishment", {})}>Route</Button>
                  )}
                  {r.status === "awaiting_resumption_verification" && (
                    <Button size="xs" onClick={() => run(r.id, "resume/verify", { verified: true })}>Verify return</Button>
                  )}
                  {r.status === "cancellation_pending" && (
                    <>
                      <Button size="xs" onClick={() => run(r.id, "cancel/decide", { approve: true })}>Approve cancel</Button>
                      <Button size="xs" variant="light"
                        onClick={() => run(r.id, "cancel/decide", { approve: false })}>Keep leave</Button>
                    </>
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
