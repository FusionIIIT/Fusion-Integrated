import { useState } from "react";
import { Alert, Card, Container, Stack, Text } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePmsApplication } from "../api/hooks";
import { PmsActionForm } from "../components/PmsActionForm";
import { PmsApplicationSelect } from "../components/PmsApplicationSelect";

export default function MaintenancePage() {
  const { can } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = usePmsApplication(selected ? Number(selected) : undefined);

  return (
    <Container size="xl">
      <PageHeader title="Post-grant maintenance" subtitle="Track configured renewal cycles, decision requests, and recorded maintenance actions." />
      <Card padding="lg"><PmsApplicationSelect value={selected} onChange={setSelected} /></Card>
      {detail.error && <Card mt="md"><ErrorState error={detail.error} /></Card>}
      {detail.isPending && selected && <Text c="dimmed" mt="md">Loading application…</Text>}
      {detail.data && (
        <Stack mt="md" gap="md">
          <Card padding="md">
            <PageHeader title={`${detail.data.application_no} · ${detail.data.title}`}
              subtitle={`Application status: ${detail.data.status.replace(/_/g, " ")}`} />
            {!detail.data.maintenance_records.length ? (
              <Alert color="blue" variant="light">
                No maintenance cycle is recorded. PMS creates cycles only when an applicable jurisdiction schedule is configured.
              </Alert>
            ) : detail.data.maintenance_records.map((cycle) => (
              <Card key={cycle.id} withBorder padding="sm" mb="sm">
                <PageHeader title={`Cycle ${cycle.cycle_number} · due ${cycle.fee_due_date}`}
                  subtitle={`Fee amount: ${cycle.fee_amount} · Decision: ${cycle.director_decision || "pending"}`}
                  action={<StatusBadge status={cycle.maintenance_status} />} />
                <Stack gap="sm">
                  {can("pms.maintenance.manage") && !cycle.decision_requested
                    && ["scheduled", "renewed"].includes(cycle.maintenance_status) && (
                      <PmsActionForm
                        title="Request renewal decision"
                        path={() => `/maintenance/${cycle.id}/request-renewal/`}
                        fields={[]}
                        submitLabel="Request Director decision"
                      />
                    )}
                  {can("pms.maintenance.decide")
                    && cycle.maintenance_status === "decision_requested" && (
                      <PmsActionForm
                        title="Director renewal decision"
                        path={() => `/maintenance/${cycle.id}/decide-renewal/`}
                        fields={[{ name: "decision", label: "Decision", type: "select", required: true, options: [
                          { value: "Renew", label: "Renew" },
                          { value: "Do Not Renew", label: "Do Not Renew" },
                        ] }]}
                        submitLabel="Record decision"
                      />
                    )}
                  {can("pms.maintenance.manage")
                    && cycle.maintenance_status === "renewal_approved" && (
                      <PmsActionForm
                        title="Record completed maintenance action"
                        path={() => `/maintenance/${cycle.id}/record-action/`}
                        fields={[{ name: "transaction_reference", label: "External transaction reference", required: true }]}
                        submitLabel="Record action"
                        successMessage="PMS recorded the action; the next cycle is created only if configured."
                      />
                    )}
                </Stack>
              </Card>
            ))}
          </Card>
        </Stack>
      )}
    </Container>
  );
}
