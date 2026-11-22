// Effective-dated PSM policy viewer and version publisher (BR-PSM-028, Step 2.8).
import { useState } from "react";
import { Badge, Button, Card, Container, NumberInput, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePsmPolicies, usePublishPolicy } from "../api/hooks";
import type { PsmPolicy } from "../api/types";

export default function PolicyPage() {
  const { can } = useAuth();
  const { data, isPending, error } = usePsmPolicies();
  const publish = usePublishPolicy();

  const [creating, setCreating] = useState(false);
  const [directLimit, setDirectLimit] = useState("50000.00");
  const [finalThreshold, setFinalThreshold] = useState("100000.00");
  const [slaRem, setSlaRem] = useState<number | string>(24);
  const [slaEsc, setSlaEsc] = useState<number | string>(48);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="PSM Policy"
        subtitle="Effective-dated procurement thresholds and SLA configuration"
        action={can("psm.policy.create") ? <Button onClick={() => setCreating(true)}>Publish new version</Button> : undefined}
      />

      <Card padding="lg">
        <DataTable<PsmPolicy>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No PSM policy versions published yet." }}
          columns={[
            { key: "version", header: "Version", render: (r) => `v${r.version}` },
            { key: "direct", header: "Direct Limit", render: (r) => `₹${r.direct_limit}` },
            { key: "final", header: "Final Approval >", render: (r) => `₹${r.final_approval_threshold}` },
            { key: "sla", header: "SLA (Rem / Esc)", render: (r) => `${r.sla_reminder_hours}h / ${r.sla_escalation_hours}h` },
            { key: "active", header: "Status", render: (r) => <Badge color={r.is_active ? "green" : "gray"}>{r.is_active ? "Active" : "Superseded"}</Badge> },
          ]}
        />
      </Card>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Publish New Policy Version"
        submitLabel="Publish policy"
        submitting={publish.isPending}
        onSubmit={() =>
          publish.mutate(
            {
              direct_limit: directLimit,
              final_approval_threshold: finalThreshold,
              sla_reminder_hours: Number(slaRem),
              sla_escalation_hours: Number(slaEsc),
            },
            {
              onSuccess: () => {
                setCreating(false);
                notifications.show({ color: "green", title: "Published", message: "New active PSM policy version created." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <TextInput label="Direct procurement limit" value={directLimit} onChange={(e) => setDirectLimit(e.currentTarget.value)} required />
          <TextInput label="Final approval threshold" value={finalThreshold} onChange={(e) => setFinalThreshold(e.currentTarget.value)} required />
          <NumberInput label="SLA reminder hours" min={1} value={slaRem} onChange={setSlaRem} required />
          <NumberInput label="SLA escalation hours" min={2} value={slaEsc} onChange={setSlaEsc} required />
        </Stack>
      </FormModal>
    </Container>
  );
}
