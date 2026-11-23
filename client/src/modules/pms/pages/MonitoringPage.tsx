import { Container, Stack, Title } from "@mantine/core";
import { FaCheckCircle } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useDeadlines, useEscalations, useHandleEscalation } from "../api/hooks";
import type { Deadline, Escalation } from "../api/types";
import { ActionBar, action, str } from "../components/ActionBar";
import { day, words } from "../components/format";

// UC-PMS-016, 027: every tracked deadline and every open escalation.
export default function MonitoringPage() {
  const deadlines = useDeadlines();
  const escalations = useEscalations();
  const handle = useHandleEscalation();
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Deadlines & Escalations"
        subtitle="Reviews, revisions, office actions and maintenance, soonest first" />
      <Stack gap="xl">
        <div>
          <Title order={4} mb="sm">Escalations</Title>
          {escalations.error ? <ErrorState error={escalations.error} /> : (
            <DataTable<Escalation>
              rows={(escalations.data ?? []).filter((e) => e.status !== "resolved")}
              loading={escalations.isPending} rowKey={(r) => r.id}
              empty={{ icon: FaCheckCircle, title: "No open escalations" }}
              columns={[
                { key: "kind", header: "Escalation", render: (r) => words(r.kind) },
                { key: "application_reference", header: "Application" },
                { key: "deadline", header: "Deadline", render: (r) => day(r.deadline) },
                { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
                { key: "act", header: "", align: "right", render: (r) => (
                  <ActionBar actions={[action({ key: `handle-${r.id}`, label: "Handle",
                    title: words(r.kind), fields: [
                      { name: "action", label: "What was done", type: "select", required: true,
                        options: [{ value: "route", label: "Routed to the deciding authority" },
                          { value: "resolve", label: "Resolved" }] },
                      { name: "note", label: "Note", type: "textarea", required: true },
                    ], submitLabel: "Record" }, handle, (v) => ({ id: r.id,
                    action: str(v.action), note: str(v.note) }))]} />) },
              ]}
            />
          )}
        </div>
        <div>
          <Title order={4} mb="sm">Deadlines</Title>
          {deadlines.error ? <ErrorState error={deadlines.error} /> : (
            <DataTable<Deadline>
              rows={deadlines.data ?? []} loading={deadlines.isPending}
              rowKey={(r) => `${r.kind}-${r.subject_id}`}
              empty={{ icon: FaCheckCircle, title: "No tracked deadlines" }}
              columns={[
                { key: "kind", header: "Deadline", render: (r) => words(r.kind) },
                { key: "reference", header: "Application" },
                { key: "due_on", header: "Due", render: (r) => day(r.due_on) },
                { key: "responsible", header: "Responsible" },
                { key: "missed", header: "", render: (r) => r.missed
                  ? <StatusBadge status="rejected" /> : null },
              ]}
            />
          )}
        </div>
      </Stack>
    </Container>
  );
}
