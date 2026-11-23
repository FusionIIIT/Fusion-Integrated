import { Button, Container, Group } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useLeaveDecision, useLeaves } from "../api/hooks";
import type { Leave } from "../api/types";

export default function LeaveDecisionsPage() {
  const { data, error, isPending } = useLeaves();
  const decide = useLeaveDecision();

  const act = (id: number, outcome: "approve" | "reject") =>
    decide.mutate({ id, outcome }, {
      onSuccess: () => notifyDone(`Leave application ${outcome === "approve" ? "approved" : "rejected"}.`),
      onError: notifyError,
    });

  const columns = [
    { key: "id", header: "#", render: (r: Leave) => r.id },
    { key: "to", header: "Period", render: (r: Leave) => `${r.from_date} to ${r.to_date}` },
    { key: "reason", header: "Reason", render: (r: Leave) => r.reason },
    { key: "status", header: "Status", render: (r: Leave) => <StatusBadge status={r.status} /> },
    {
      key: "act", header: "Decision", align: "right" as const,
      render: (r: Leave) => r.status !== "submitted" ? null : (
        <Group gap="xs" justify="flex-end">
          <Button size="xs" onClick={() => act(r.id, "approve")}>Approve</Button>
          <Button size="xs" variant="light" color="red" onClick={() => act(r.id, "reject")}>Reject</Button>
        </Group>
      ),
    },
  ];

  return (
    <Container size="lg" py="md">
      <PageHeader title="Leave decisions" subtitle="Leave applications routed to you as Head of Department." />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={820}
          rowKey={(r) => r.id} empty={{ title: "No leave applications are waiting." }} />
      )}
    </Container>
  );
}
