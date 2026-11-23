import { Button, Container, Group, TextInput } from "@mantine/core";
import { useState } from "react";
import { FaHistory } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAudit, useExport } from "../api/hooks";
import type { AuditEntry } from "../api/types";
import { day, words } from "../components/format";
import { usePmsCan } from "../components/access";

// UC-PMS-028: the audit trail within scope; viewing and exporting are themselves audited.
export default function AuditPage() {
  const can = usePmsCan();
  const [action, setAction] = useState("");
  const audit = useAudit(action ? { action } : undefined);
  const download = useExport();
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Audit Log" subtitle="Who did what, when, and to which application"
        action={can("pms.audit_log.export") ? (
          <Button variant="light" loading={download.isPending}
            onClick={() => download.mutate({ path: "audit/export", name: "pms-audit.csv" })}>
            Export CSV
          </Button>) : null} />
      <Group mb="sm">
        <TextInput label="Action starts with" value={action} w={280}
          onChange={(e) => setAction(e.currentTarget.value)} />
      </Group>
      {download.error != null && <ErrorState error={download.error} />}
      {audit.error ? <ErrorState error={audit.error} /> : (
        <DataTable<AuditEntry>
          rows={audit.data?.results ?? []} loading={audit.isPending} rowKey={(r) => r.id}
          empty={{ icon: FaHistory, title: "No audit entries" }}
          columns={[
            { key: "at", header: "When", render: (r) => `${day(r.at)} ${r.at.slice(11, 16)}` },
            { key: "actor_role", header: "Role", render: (r) => r.actor_role || "System" },
            { key: "action", header: "Action", render: (r) => words(r.action.replace(".", " ")) },
            { key: "application_reference", header: "Application" },
            { key: "change", header: "Change", render: (r) => r.to_state
              ? `${words(r.from_state)} → ${words(r.to_state)}` : "—" },
          ]}
        />
      )}
    </Container>
  );
}
