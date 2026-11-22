import {
  Container,
  Stack,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { useAuditObservations } from "../api/hooks";
import type { AuditObservation } from "../api/types";

export default function AuditObservationsPage() {
  const { data: observations, isPending, error } = useAuditObservations();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const columns: Column<AuditObservation>[] = [
    { key: "id", header: "ID", render: (o) => `#OBS-${o.id}` },
    { key: "title", header: "Title", render: (o) => o.title },
    { key: "department", header: "Department", render: (o) => o.department },
    { key: "description", header: "Description", render: (o) => o.description },
    { key: "status", header: "Status", render: (o) => <StatusBadge status={o.status} /> },
  ];

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Audit Observations"
          subtitle="Internal audit findings, department responses, and compliance verification."
        />

        <DataTable
          rows={observations || []}
          columns={columns}
          loading={isPending}
          rowKey={(o) => o.id}
          empty={{ title: "No audit observations found." }}
        />
      </Stack>
    </Container>
  );
}
