import { useState } from "react";
import { Button, Card, Container, Group, TextInput } from "@mantine/core";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePmsAudit } from "../api/hooks";
import type { PmsAuditEntry } from "../api/types";

export default function AuditPage() {
  const [applicationInput, setApplicationInput] = useState("");
  const [applicationId, setApplicationId] = useState<number>();
  const query = usePmsAudit(applicationId);
  const columns: Column<PmsAuditEntry>[] = [
    { key: "timestamp", header: "Time" },
    { key: "application_id", header: "Application" },
    { key: "actor_user_id", header: "Actor" },
    { key: "action_type", header: "Action" },
    { key: "from_state", header: "From" },
    { key: "to_state", header: "To" },
  ];
  if (query.error) return <Container size="xl"><ErrorState error={query.error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title="Audit trail" subtitle="Review PMS audit records within the scope granted to your current role." />
      <Card padding="lg">
        <Group mb="md" align="flex-end">
          <TextInput label="Application ID" type="number" value={applicationInput}
            onChange={(event) => setApplicationInput(event.currentTarget.value)} />
          <Button variant="default" onClick={() => setApplicationId(
            applicationInput.trim() ? Number(applicationInput) : undefined,
          )}>Apply filter</Button>
        </Group>
        <DataTable rows={query.data ?? []} columns={columns} rowKey={(row) => row.id}
          loading={query.isPending} minWidth={900}
          empty={{ title: "No audit records", description: "No records match this filter within your authorized scope." }} />
      </Card>
    </Container>
  );
}
