import {
  Container,
  Stack,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { useAnomalies } from "../api/hooks";
import type { Anomaly } from "../api/types";

export default function AnomaliesPage() {
  const { data: anomalies, isPending, error } = useAnomalies();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const columns: Column<Anomaly>[] = [
    { key: "id", header: "ID", render: (a) => `#AN-${a.id}` },
    { key: "category", header: "Category", render: (a) => a.category.replace(/_/g, " ").toUpperCase() },
    { key: "description", header: "Description", render: (a) => a.description },
    { key: "reference", header: "Reference", render: (a) => `${a.reference_type}:${a.reference_id}` },
    { key: "resolver_role", header: "Resolver Role", render: (a) => a.resolver_role },
    { key: "status", header: "Status", render: (a) => <StatusBadge status={a.status} /> },
  ];

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Material Anomalies"
          subtitle="Track flagged budget insufficiencies, policy violations, and financial discrepancies."
        />

        <DataTable
          rows={anomalies || []}
          columns={columns}
          loading={isPending}
          rowKey={(a) => a.id}
          empty={{ title: "No material anomalies recorded." }}
        />
      </Stack>
    </Container>
  );
}
