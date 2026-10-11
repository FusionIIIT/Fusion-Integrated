import { Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useApplications, useLeaveAction } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function SanctionPage() {
  const { data, isPending, error } = useApplications();
  const action = useLeaveAction();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const rows = (data?.results ?? []).filter((r) =>
    ["awaiting_final_sanction", "awaiting_director_self_sanction"].includes(r.status));

  function run(id: number, approve: boolean) {
    action.mutate({ id, path: "sanction", body: { approve } }, {
      onSuccess: () => notifications.show({ color: "green", message: "Decision recorded" }),
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Sanction queue" subtitle="Final sanctioning authority, including Director self-sanction" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={rows} loading={isPending} rowKey={(r) => r.id}
          columns={[
            { key: "user_id", header: "Employee", render: (r) => String(r.user_id) },
            { key: "category", header: "Category", render: (r) => r.category },
            { key: "rec", header: "Unit Head", render: (r) => r.unit_head_recommendation || "—" },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "",
              render: (r) => (
                <Group gap="xs">
                  <Button size="xs" onClick={() => run(r.id, true)}>Approve</Button>
                  <Button size="xs" color="red" variant="light" onClick={() => run(r.id, false)}>Reject</Button>
                </Group>
              ),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
