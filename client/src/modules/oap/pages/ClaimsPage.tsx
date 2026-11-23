import { Button, Container } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useClaims, useSubmitClaim } from "../api/hooks";
import type { Claim } from "../api/types";

const columns = [
  { key: "id", header: "#", render: (r: Claim) => r.id },
  { key: "verified", header: "Verifications", render: (r: Claim) => r.verifications.map((v) => v.role).join(", ") || "none yet" },
  { key: "status", header: "Stage", render: (r: Claim) => <StatusBadge status={r.status} /> },
];

export default function ClaimsPage() {
  const { data, error, isPending } = useClaims();
  const submit = useSubmitClaim();

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Assistantship claims"
        subtitle="Submit a claim and follow it through supervisor verification."
        action={
          <Button loading={submit.isPending} onClick={() => submit.mutate(undefined, {
            onSuccess: () => notifyDone("Claim submitted to both supervisors."), onError: notifyError,
          })}>Submit claim</Button>
        }
      />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={620}
          rowKey={(r) => r.id} empty={{ title: "No assistantship claims yet." }} />
      )}
    </Container>
  );
}
