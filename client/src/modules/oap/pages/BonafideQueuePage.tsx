import { Button, Container, Group } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useBonafideDecision, useBonafides, useVerifyBonafide } from "../api/hooks";
import type { Bonafide } from "../api/types";

export default function BonafideQueuePage() {
  const { data, error, isPending } = useBonafides();
  const verify = useVerifyBonafide();
  const decide = useBonafideDecision();

  const columns = [
    { key: "id", header: "#", render: (r: Bonafide) => r.id },
    { key: "status", header: "Status", render: (r: Bonafide) => <StatusBadge status={r.status} /> },
    {
      key: "verified", header: "Verified",
      render: (r: Bonafide) => (r.verified_at ? "Yes" : "No"),
    },
    {
      key: "act", header: "Actions", align: "right" as const,
      render: (r: Bonafide) => r.status !== "submitted" ? null : (
        <Group gap="xs" justify="flex-end">
          {!r.verified_at && (
            <Button size="xs" variant="light" loading={verify.isPending}
              onClick={() => verify.mutate(r.id, { onSuccess: () => notifyDone("Request verified."), onError: notifyError })}>
              Verify
            </Button>
          )}
          {r.verified_at && (
            <>
              <Button size="xs" onClick={() => decide.mutate({ id: r.id, outcome: "approve" }, { onError: notifyError })}>Approve</Button>
              <Button size="xs" color="red" variant="light"
                onClick={() => decide.mutate({ id: r.id, outcome: "reject" }, { onError: notifyError })}>Reject</Button>
            </>
          )}
        </Group>
      ),
    },
  ];

  return (
    <Container size="lg" py="md">
      <PageHeader title="Bonafide queue" subtitle="Verify and decide bonafide requests." />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={640}
          rowKey={(r) => r.id} empty={{ title: "No bonafide requests are waiting." }} />
      )}
    </Container>
  );
}
