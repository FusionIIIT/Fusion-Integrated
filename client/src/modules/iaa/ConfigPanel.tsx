import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Checkbox, Group, Modal, NumberInput, Paper, Select, Stack,
  Table, Text, TextInput, Title } from "@mantine/core";
import { errorMessage } from "../../lib/http";
import { authorities, get, label, post, roles, type Row } from "./api";

type Field = { key: string; type?: "number" | "money" | "bool" | "date" | "role" | "kind";
  optional?: boolean };
const schemas: Record<string, Field[]> = {
  roles: [{ key: "user_id", type: "number" }, { key: "role", type: "role" },
    { key: "department", optional: true }, { key: "active", type: "bool" }],
  years: [{ key: "name" }, { key: "starts_on", type: "date" }, { key: "ends_on", type: "date" },
    { key: "active", type: "bool" }],
  departments: [{ key: "code" }, { key: "finance_user_id", type: "number" }],
  budgets: [{ key: "department" }, { key: "year", type: "number" },
    { key: "allocated", type: "money" }],
  policies: [{ key: "name" }, { key: "ta_approval_threshold", type: "money" },
    { key: "ta_max_daily_amount", type: "money", optional: true },
    { key: "documents_required", type: "bool" }, { key: "budget_required", type: "bool" },
    { key: "anomaly_resolver_id", type: "number" }, { key: "anomaly_resolver_role", type: "role" },
    { key: "anomaly_escalation_id", type: "number", optional: true },
    { key: "anomaly_escalation_role", type: "role", optional: true }, { key: "active", type: "bool" }],
  routes: [{ key: "name" }, { key: "department", optional: true },
    { key: "request_type", optional: true }, { key: "kind", type: "kind" },
    { key: "minimum", type: "money" }, { key: "maximum", type: "money", optional: true },
    { key: "priority", type: "number" }, { key: "active", type: "bool" }],
};
export default function ConfigPanel({ role }: { role: string }) {
  const qc = useQueryClient();
  const [resource, setResource] = useState("roles");
  const [form, setForm] = useState<Record<string, unknown> | null>(null);
  const [steps, setSteps] = useState<{ user_id: number | string; role: string; timeout_hours: number }[]>([]);
  const [recoveryId, setRecoveryId] = useState<number | string>("");
  const query = useQuery({ queryKey: ["iaa", role, "config", resource],
    queryFn: () => get<{ results: Row[] }>(`config/${resource}`, role) });
  const save = useMutation({ mutationFn: (data: Record<string, unknown>) =>
    post(`config/${resource}`, role, data),
    onSuccess: () => { setForm(null); qc.invalidateQueries({ queryKey: ["iaa"] }); } });
  const recover = useMutation({ mutationFn: () => post(`recovery/${recoveryId}`, role, {}),
    onSuccess: () => setRecoveryId("") });
  function edit(row?: Row) {
    save.reset();
    setForm(row ? { ...row } : Object.fromEntries((schemas[resource] ?? []).map(f =>
      [f.key, f.type === "bool" ? true : f.key === "priority" ? 100 : ""])));
    setSteps((row?.steps as typeof steps | undefined) ?? []);
  }
  function submit(e: React.FormEvent) {
    e.preventDefault(); if (!form) return;
    const payload = { ...form };
    for (const field of (schemas[resource] ?? [])) {
      const value = payload[field.key];
      if (field.type === "number" || field.type === "money") {
        payload[field.key] = value === "" || value == null ? null
          : field.type === "money" ? String(value) : Number(value);
      }
    }
    if (resource === "routes") payload.steps = steps.map(s => ({ ...s, user_id: Number(s.user_id) }));
    save.mutate(payload);
  }
  return <Stack>
    <Text c="dimmed">Configure roles first, then years, departments, policy, budgets, and approval routes.
      Administrative access does not expose financial request content.</Text>
    <Group><Select label="Configuration" data={Object.keys(schemas).map(value => ({ value, label: label(value) }))}
      value={resource} onChange={v => { setResource(v ?? "roles"); setForm(null); }} />
      <Button mt="xl" onClick={() => edit()}>Add configuration</Button></Group>
    {query.isPending && <Text>Loading configuration…</Text>}
    {query.error && <Alert color="red">{errorMessage(query.error)}</Alert>}
    {!query.isPending && !query.error && !query.data?.results.length && <Paper p="lg" withBorder>
      <Text>No {resource} configured yet.</Text></Paper>}
    {!!query.data?.results.length && <Table.ScrollContainer minWidth={600}><Table>
      <Table.Thead><Table.Tr>{["ID", "Configuration", "Scope", ""].map(h => <Table.Th key={h}>{h}</Table.Th>)}</Table.Tr></Table.Thead>
      <Table.Tbody>{query.data.results.map(row => <Table.Tr key={row.id}>
        <Table.Td>{row.id}</Table.Td><Table.Td>{String(row.name ?? row.role ?? row.code ?? `Budget ${row.id}`)}</Table.Td>
        <Table.Td>{String(row.department ?? "Institute")}{row.user_id ? ` · User ${row.user_id}` : ""}</Table.Td>
        <Table.Td><Button variant="light" size="xs" onClick={() => edit(row)}>Edit</Button></Table.Td>
      </Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
    <Paper p="md" withBorder><Title order={4}>Recover Finance routing</Title>
      <Text size="sm">For submitted records flagged because a Finance assignee was unavailable.</Text>
      <Group mt="sm"><NumberInput label="Record ID" min={1} value={recoveryId} onChange={setRecoveryId} />
        <Button mt="xl" disabled={!recoveryId} loading={recover.isPending} onClick={() => recover.mutate()}>Recover routing</Button></Group>
      {recover.error && <Alert color="red">{errorMessage(recover.error)}</Alert>}
      {recover.isSuccess && <Alert color="green">Routing recovered.</Alert>}
    </Paper>
    <Modal opened={form !== null} onClose={() => setForm(null)} title={`${label(resource)} configuration`} size="lg">
      <form onSubmit={submit}><Stack>{(schemas[resource] ?? []).map(field => {
        const value = form?.[field.key]; const update = (v: unknown) => setForm(f => ({ ...f, [field.key]: v }));
        const title = label(field.key) + (field.optional ? " (optional)" : "");
        if (field.type === "bool") return <Checkbox key={field.key} label={title} checked={!!value} onChange={e => update(e.currentTarget.checked)} />;
        if (field.type === "role" || field.type === "kind") return <Select key={field.key} label={title}
          data={field.type === "role" ? roles : ["expense", "ta"]} clearable={field.optional}
          required={!field.optional} value={String(value ?? "") || null} onChange={v => update(v ?? "")} />;
        if (field.type === "number") return <NumberInput key={field.key} label={title} min={field.key === "priority" ? 0 : 1}
          allowDecimal={false} required={!field.optional} value={value as number | string ?? ""} onChange={update} />;
        return <TextInput key={field.key} label={title} type={field.type === "date" ? "date" : "text"}
          inputMode={field.type === "money" ? "decimal" : undefined} required={!field.optional}
          value={String(value ?? "")} onChange={e => update(e.currentTarget.value)} />;
      })}
        {resource === "routes" && <Stack><Title order={5}>Approval levels in order</Title>
          {steps.map((step, index) => <Paper p="sm" withBorder key={index}><Group>
            <NumberInput label={`Level ${index + 1} user ID`} min={1} required allowDecimal={false} value={step.user_id}
              onChange={v => setSteps(all => all.map((s, i) => i === index ? { ...s, user_id: v } : s))} />
            <Select label="Authority role" data={authorities} required value={step.role}
              onChange={v => setSteps(all => all.map((s, i) => i === index ? { ...s, role: v ?? "HoD" } : s))} />
            <NumberInput label="Timeout (hours)" min={1} max={8760} value={step.timeout_hours}
              onChange={v => setSteps(all => all.map((s, i) => i === index ? { ...s, timeout_hours: Number(v) } : s))} />
            <Button color="red" variant="subtle" onClick={() => setSteps(s => s.filter((_, i) => i !== index))}>Remove level</Button>
          </Group></Paper>)}
          <Button variant="light" onClick={() => setSteps(s => [...s, { user_id: "", role: "HoD", timeout_hours: 24 }])}>Add approval level</Button>
        </Stack>}
        {save.error && <Alert color="red">{errorMessage(save.error)}</Alert>}
        <Button type="submit" loading={save.isPending}>Save configuration</Button>
      </Stack></form>
    </Modal>
  </Stack>;
}
