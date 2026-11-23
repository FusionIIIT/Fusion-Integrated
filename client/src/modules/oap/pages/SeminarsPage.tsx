import { Button, Container } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useRequestSeminar, useSeminarRequests } from "../api/hooks";
import type { SeminarRequest } from "../api/types";

const columns = [
  { key: "id", header: "#", render: (r: SeminarRequest) => r.id },
  { key: "status", header: "Status", render: (r: SeminarRequest) => <StatusBadge status={r.status} /> },
  { key: "at", header: "Requested", render: (r: SeminarRequest) => new Date(r.created_at).toLocaleDateString() },
];

export default function SeminarsPage() {
  const { data, error, isPending } = useSeminarRequests();
  const request = useRequestSeminar();

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Graduate seminars"
        subtitle="Ask the Department Administrator to schedule your seminar."
        action={
          <Button loading={request.isPending} onClick={() => request.mutate(undefined, {
            onSuccess: () => notifyDone("Seminar scheduling requested."), onError: notifyError,
          })}>Request scheduling</Button>
        }
      />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={520}
          rowKey={(r) => r.id} empty={{ title: "No seminar requests yet." }} />
      )}
    </Container>
  );
}
