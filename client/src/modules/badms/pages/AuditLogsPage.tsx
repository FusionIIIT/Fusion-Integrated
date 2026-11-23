import { Badge, Card, Container } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { AuditEvent } from "../api/types";

export default function AuditLogsPage() {
  const { data, isPending, error } = useAuditLogs();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="BADMS Audit Logs"
        subtitle="Append-only immutable audit trail of backup, archival, restoration, and quota actions"
      />
      <Card padding="lg">
        <DataTable<AuditEvent>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{ title: "No audit logs", description: "No security or administrative audit records found." }}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            {
              key: "event_type",
              header: "Event",
              render: (r) => <Badge variant="light">{r.event_type}</Badge>,
            },
            {
              key: "actor_user_id",
              header: "User ID",
              render: (r) => (r.actor_user_id ? String(r.actor_user_id) : "System"),
            },
            {
              key: "department",
              header: "Department",
              render: (r) => r.department || "—",
            },
            {
              key: "target",
              header: "Target",
              render: (r) => `${r.target_model} #${r.target_id ?? "—"}`,
            },
            {
              key: "ip_address",
              header: "IP Address",
              render: (r) => r.ip_address || "—",
            },
            {
              key: "timestamp",
              header: "Timestamp",
              render: (r) => new Date(r.timestamp).toLocaleString(),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
