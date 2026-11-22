import { Container } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useNotices } from "../api/hooks";
import type { Notice } from "../api/types";

const columns = [
  { key: "when", header: "When", render: (r: Notice) => new Date(r.created_at).toLocaleString() },
  { key: "subject", header: "Subject", render: (r: Notice) => r.subject },
  { key: "body", header: "Message", render: (r: Notice) => r.body },
];

export default function NotificationsPage() {
  const { data, error, isPending } = useNotices();
  return (
    <Container size="lg" py="md">
      <PageHeader title="OAP alerts" subtitle="Updates on your OAP requests." />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={640}
          rowKey={(r) => r.id} empty={{ title: "No alerts yet." }} />
      )}
    </Container>
  );
}
