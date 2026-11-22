import { useState } from "react";
import {
  Button, Card, Code, Container, Group, Select, SimpleGrid, Stack, Text, TextInput, Textarea,
  Title,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAddBudgetEntry, useAddYear, useBudget, usePolicies, usePublishPolicy, useYears,
} from "../api/hooks";
import { done, failed } from "../components/toast";

const TEMPLATE = JSON.stringify({
  approval_timeout_hours: 48,
  ta_high_value_threshold: "25000",
  budget_check_required: true,
  request_types: ["voucher", "purchase", "contingency"],
  required_documents: { expense: 1, ta: 1 },
  routes: [
    { kind: "expense", min_amount: "0", max_amount: "50000", levels: ["iaa_hod"],
      escalation_designation: "iaa_dean" },
    { kind: "expense", min_amount: "50000", levels: ["iaa_hod", "iaa_dean", "iaa_director"],
      escalation_designation: "" },
    { kind: "ta", min_amount: "0", levels: ["iaa_hod", "iaa_dean"],
      escalation_designation: "iaa_director" },
  ],
  anomaly_resolvers: {
    budget: ["iaa_finance_staff", "iaa_dean"],
    policy: ["iaa_finance_staff", "iaa_auditor"],
    financial: ["iaa_auditor", "iaa_director"],
  },
}, null, 2);

function PolicyCard({ canEdit }: { canEdit: boolean }) {
  const { data, error } = usePolicies();
  const publish = usePublishPolicy();
  const [text, setText] = useState(TEMPLATE);
  const current = data?.[0];
  let parsed: Record<string, unknown> | null = null;
  try { parsed = JSON.parse(text) as Record<string, unknown>; } catch { parsed = null; }
  return (
    <Card padding="md">
      <Title order={5}>Policy</Title>
      {error && <ErrorState error={error} />}
      <Text size="sm" c="dimmed" mb="xs">
        {current ? `Version ${current.id} in effect since `
          + new Date(current.effective_from).toLocaleString()
          : "No policy published yet — nobody can submit until one is."}
      </Text>
      {current && <Code block mb="sm">{JSON.stringify(current, null, 2)}</Code>}
      {canEdit && (
        <Stack gap={6}>
          <Textarea label="New version (JSON). Publishing supersedes; nothing is edited."
            value={text} autosize minRows={10} ff="monospace"
            error={parsed ? undefined : "Not valid JSON"}
            onChange={(e) => setText(e.currentTarget.value)} />
          <Button disabled={!parsed} loading={publish.isPending}
            onClick={() => publish.mutateAsync(parsed ?? {})
              .then(() => done("Policy published.")).catch(failed)}>Publish</Button>
        </Stack>
      )}
    </Card>
  );
}

function YearsCard({ canEdit }: { canEdit: boolean }) {
  const { data } = useYears();
  const add = useAddYear();
  const [f, setF] = useState({ code: "", starts_on: "", ends_on: "" });
  return (
    <Card padding="md">
      <Title order={5}>Financial years</Title>
      {(data ?? []).map((y) => <Text key={y.id} size="sm">{y.code}: {y.starts_on} → {y.ends_on}
      </Text>)}
      {(data ?? []).length === 0 && <Text size="sm" c="dimmed">None yet.</Text>}
      {canEdit && (
        <Group align="end" mt="sm">
          <TextInput label="Code" placeholder="2026-27" value={f.code}
            onChange={(e) => setF({ ...f, code: e.currentTarget.value })} />
          <TextInput type="date" label="Starts" value={f.starts_on}
            onChange={(e) => setF({ ...f, starts_on: e.currentTarget.value })} />
          <TextInput type="date" label="Ends" value={f.ends_on}
            onChange={(e) => setF({ ...f, ends_on: e.currentTarget.value })} />
          <Button disabled={!f.code || !f.starts_on || !f.ends_on} loading={add.isPending}
            onClick={() => add.mutateAsync(f).then(() => done("Financial year added."))
              .catch(failed)}>Add</Button>
        </Group>
      )}
    </Card>
  );
}

function BudgetCard({ canEdit }: { canEdit: boolean }) {
  const { data } = useBudget();
  const { data: years } = useYears();
  const add = useAddBudgetEntry();
  const [f, setF] = useState({ year: "", department: "", kind: "allocation", amount: "",
                               note: "" });
  return (
    <Card padding="md">
      <Title order={5}>Departmental budget ledger</Title>
      <Text size="xs" c="dimmed">Append-only: correct with an adjustment, never an edit.</Text>
      {(data?.results ?? []).map((b) => (
        <Text key={b.id} size="sm">{b.financial_year} · {b.department} · {b.kind} · {b.amount}
          {b.note && ` · ${b.note}`}</Text>
      ))}
      {canEdit && (
        <SimpleGrid cols={{ base: 1, sm: 3 }} mt="sm">
          <Select label="Financial year" value={f.year}
            data={(years ?? []).map((y) => ({ value: String(y.id), label: y.code }))}
            onChange={(v) => setF({ ...f, year: v ?? "" })} />
          <TextInput label="Department" value={f.department}
            onChange={(e) => setF({ ...f, department: e.currentTarget.value })} />
          <Select label="Kind" value={f.kind} data={["allocation", "adjustment"]}
            onChange={(v) => setF({ ...f, kind: v ?? "allocation" })} />
          <TextInput label="Amount (₹, negative to reduce)" value={f.amount}
            onChange={(e) => setF({ ...f, amount: e.currentTarget.value })} />
          <TextInput label="Note" value={f.note}
            onChange={(e) => setF({ ...f, note: e.currentTarget.value })} />
          <Button mt="lg" disabled={!f.year || !f.department || !f.amount} loading={add.isPending}
            onClick={() => add.mutateAsync({ financial_year_id: Number(f.year),
                                             department: f.department, kind: f.kind,
                                             amount: f.amount, note: f.note })
              .then(() => done("Budget entry added.")).catch(failed)}>Add entry</Button>
        </SimpleGrid>
      )}
    </Card>
  );
}

export default function ConfigurationPage() {
  const { can } = useAuth();
  const canEdit = can("iaa.configuration.update");
  return (
    <Container size="lg">
      <PageHeader title="IAA configuration"
        subtitle="Policy, financial years and budget — no access to requests or decisions" />
      <Stack gap="md">
        <PolicyCard canEdit={canEdit} />
        <YearsCard canEdit={canEdit} />
        <BudgetCard canEdit={canEdit} />
      </Stack>
    </Container>
  );
}
