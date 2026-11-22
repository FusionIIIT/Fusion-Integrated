import { Button, Container, Group } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import {
  useClaimDecision, useClaims, useForwardClaim, useProcessStipend,
} from "../api/hooks";
import type { Claim } from "../api/types";

export default function ClaimQueuePage() {
  const { data, error, isPending } = useClaims();
  const { session } = useAuth();
  const forward = useForwardClaim();
  const decide = useClaimDecision();
  const stipend = useProcessStipend();
  const role = session?.active_role ?? null;

  const done = (msg: string) => ({ onSuccess: () => notifyDone(msg), onError: notifyError });

  const action = (c: Claim) => {
    if (role === "Department Administrator" && c.status === "awaiting_department_review")
      return <Button size="xs" onClick={() => forward.mutate(c.id, done("Forwarded to the HoD."))}>Review and forward</Button>;
    if (role === "Head of Department" && c.status === "awaiting_hod_decision")
      return (
        <Group gap="xs">
          <Button size="xs" onClick={() => decide.mutate({ id: c.id, outcome: "approve" }, done("Claim approved."))}>Approve</Button>
          <Button size="xs" color="red" variant="light" onClick={() => decide.mutate({ id: c.id, outcome: "reject" }, done("Claim rejected."))}>Reject</Button>
        </Group>
      );
    if (role === "Academic Administrator" && c.status === "approved_awaiting_stipend")
      return <Button size="xs" onClick={() => stipend.mutate(c.id, done("Stipend processed."))}>Process stipend</Button>;
    return null;
  };

  const columns = [
    { key: "id", header: "#", render: (r: Claim) => r.id },
    { key: "stage", header: "Stage", render: (r: Claim) => <StatusBadge status={r.status} /> },
    { key: "act", header: "Action", align: "right" as const, render: action },
  ];

  return (
    <Container size="lg" py="md">
      <PageHeader title="Claim queue" subtitle="Claims waiting on your role." />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={620}
          rowKey={(r) => r.id} empty={{ title: "No claims are waiting on your role." }} />
      )}
    </Container>
  );
}
