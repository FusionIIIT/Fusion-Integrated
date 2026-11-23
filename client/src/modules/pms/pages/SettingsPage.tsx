import {
  Alert, Button, Checkbox, Container, Group, List, MultiSelect, NumberInput, Stack, Textarea,
  TextInput, Title,
} from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePolicy, usePublishPolicy, useSetup } from "../api/hooks";
import type { Policy, PolicyPayload } from "../api/types";
import { words } from "../components/format";
import { PersonPicker } from "../components/PersonPicker";

const CANDIDATES = ["submitted", "under_review", "needs_revision", "rejected", "approved",
  "attorney_assigned", "pending_review"];

const linesOf = (text: string) => text.split("\n").map((l) => l.trim()).filter(Boolean);

function domainsText(p: PolicyPayload) {
  return p.domains.map((d) => [d.code, d.label, d.ipc_classes.join(" ")].join(" | ")).join("\n");
}

function rulesText(p: PolicyPayload) {
  return Object.entries(p.maintenance_rules).map(([k, v]) => `${k}: ${v.join(", ")}`).join("\n");
}

// UC-PMS-025, Step 2.8: settings are published as a new version, never edited in place.
type Publish = ReturnType<typeof usePublishPolicy>;

function Editor({ policy, publish }: { policy: Policy; publish: Publish }) {
  const p = policy.payload;
  const [threshold, setThreshold] = useState(p.cost_threshold ?? "");
  const [appealDays, setAppealDays] = useState<number>(p.appeal_period_days);
  const [alerts, setAlerts] = useState(p.alert_offsets_days.join(", "));
  const [withdrawal, setWithdrawal] = useState<string[]>(p.withdrawal_statuses);
  const [consent, setConsent] = useState(p.withdrawal_consent_required);
  const [holidays, setHolidays] = useState(p.holidays.join("\n"));
  const [domains, setDomains] = useState(domainsText(p));
  const [rules, setRules] = useState(rulesText(p));
  const [contact, setContact] = useState<number | null>(p.pcc_contact_user_id);
  const [autoRoute, setAutoRoute] = useState(p.auto_routing_enabled);
  const [committee, setCommittee] = useState(p.licensing_route?.committee_name ?? "");

  const payload = (): Record<string, unknown> => ({
    ...p,
    cost_threshold: threshold === "" ? null : threshold,
    appeal_period_days: appealDays,
    alert_offsets_days: alerts.split(",").map((a) => Number(a.trim())).filter(Boolean),
    withdrawal_statuses: withdrawal,
    withdrawal_consent_required: consent,
    holidays: linesOf(holidays),
    domains: linesOf(domains).map((l) => {
      const [code = "", label = "", ipc = ""] = l.split("|").map((x) => x.trim());
      return { code, label, ipc_classes: ipc.split(/\s+/).filter(Boolean) };
    }),
    maintenance_rules: Object.fromEntries(linesOf(rules).map((l) => {
      const [j = "", months = ""] = l.split(":");
      return [j.trim(), months.split(",").map((m) => Number(m.trim())).filter(Boolean)];
    })),
    pcc_contact_user_id: contact,
    auto_routing_enabled: autoRoute,
    licensing_route: committee.trim() ? { kind: "committee", committee_name: committee.trim() }
      : p.licensing_route,
  });

  return (
    <Stack gap="sm" maw={720}>
      {publish.error != null && <ErrorState error={publish.error} />}
      <TextInput label="Budget threshold (Rs)" value={threshold}
        description="Budgets above this are escalated to the higher authority."
        onChange={(e) => setThreshold(e.currentTarget.value)} />
      <NumberInput label="Appeal period (days)" value={appealDays} min={1} max={365}
        onChange={(v) => setAppealDays(Number(v) || 0)} />
      <TextInput label="Alert days before a deadline (comma separated)" value={alerts}
        onChange={(e) => setAlerts(e.currentTarget.value)} />
      <MultiSelect label="Statuses that allow withdrawal" value={withdrawal}
        onChange={setWithdrawal} data={CANDIDATES.map((c) => ({ value: c, label: words(c) }))} />
      <Checkbox label="Co-inventors must consent to a withdrawal" checked={consent}
        onChange={(e) => setConsent(e.currentTarget.checked)} />
      <Textarea label="Technical areas (one per line: code | label | IPC classes)"
        autosize minRows={3} value={domains} onChange={(e) => setDomains(e.currentTarget.value)} />
      <Textarea label="Holidays (one YYYY-MM-DD per line)" autosize minRows={2} value={holidays}
        onChange={(e) => setHolidays(e.currentTarget.value)} />
      <Textarea label="Maintenance schedule (one per line: IN: 12, 24)" autosize minRows={2}
        value={rules} onChange={(e) => setRules(e.currentTarget.value)} />
      <PersonPicker label="PCC_ADMIN contact for notices" value={contact}
        onChange={(id) => setContact(id)} />
      <Checkbox label="Assign Directors automatically" checked={autoRoute}
        onChange={(e) => setAutoRoute(e.currentTarget.checked)} />
      <TextInput label="Licensing committee" value={committee}
        onChange={(e) => setCommittee(e.currentTarget.value)} />
      <Group>
        <Button loading={publish.isPending} onClick={() => publish.mutate({
          based_on_version: policy.version, payload: payload() })}>
          Publish version {policy.version + 1}
        </Button>
      </Group>
    </Stack>
  );
}

export default function SettingsPage() {
  const policy = usePolicy();
  const setup = useSetup();
  // Held here: a publish reloads the editor under the new version's key.
  const publish = usePublishPolicy();
  const published = publish.isSuccess ? publish.data?.version : undefined;
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Settings" subtitle="Patent Management configuration, versioned" />
      <Stack gap="lg">
        {setup.data && setup.data.gaps.length > 0 && (
          <Alert color="yellow" title="Still to configure">
            <List size="sm">{setup.data.gaps.map((g) => <List.Item key={g}>{g}</List.Item>)}</List>
          </Alert>
        )}
        {published != null && published === policy.data?.version && (
          <Alert color="green" title="Published">Version {published} is in effect.</Alert>
        )}
        <Title order={4}>Current version {policy.data?.version ?? ""}</Title>
        {policy.error ? <ErrorState error={policy.error} />
          : policy.isPending ? null : <Editor key={policy.data.version} policy={policy.data}
            publish={publish} />}
      </Stack>
    </Container>
  );
}
