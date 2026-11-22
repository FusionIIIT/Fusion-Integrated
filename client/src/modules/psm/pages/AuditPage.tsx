// Internal and statutory audit trail viewer (PSM-UC-014, BR-PSM-021).
import { useState } from "react";
import { Badge, Card, Container, Select, Stack } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { AuditLog } from "../api/types";

export default function AuditPage() {
  const [targetType, setTargetType] = useState<string | null>(null);
  const { data, isPending, error } = useAuditLogs(targetType ?? undefined);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Audit Trail" subtitle="Internal and statutory audit record of all PSM actions" />
      <Stack gap="md">
        <Select
          label="Filter by entity"
          clearable
          data={["indent", "vendor", "tender", "purchase_order", "grn", "discrepancy", "invoice", "stock_transfer", "policy"]}
          value={targetType}
          onChange={setTargetType}
          maw={280}
        />
        <Card padding="lg">
          <DataTable<AuditLog>
            rows={data?.results ?? []}
            loading={isPending}
            rowKey={(r) => r.id}
            empty={{ title: "No audit records found." }}
            columns={[
              { key: "action", header: "Action", render: (r) => <Badge variant="light">{r.action}</Badge> },
              { key: "target", header: "Target", render: (r) => `${r.target_type}#${r.target_id}` },
              { key: "transition", header: "State Change", render: (r) => (r.from_state || r.to_state ? `${r.from_state || "—"} → ${r.to_state || "—"}` : "—") },
              { key: "actor", header: "Actor Role", render: (r) => `${r.actor_role || "system"} (#${r.actor_user_id ?? "—"})` },
              { key: "at", header: "Timestamp", render: (r) => r.created_at },
            ]}
          />
        </Card>
      </Stack>
    </Container>
  );
}
