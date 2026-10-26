import {
  ActionIcon, Button, Card, Container, Group, NumberInput, Select, Stack, Table, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useState } from "react";
import { FaTrash } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHierarchy, useSaveSla, useSla } from "../api/hooks";
import type { SlaRule } from "../api/types";
import { STEP_LABELS } from "../components/fields";

/** EL-UC-018: reminder and escalation thresholds; only a still-pending task is ever touched. */
export default function SlaPage() {
  const { data, error } = useSla();
  const hierarchy = useHierarchy();
  const save = useSaveSla();
  const [rules, setRules] = useState<SlaRule[]>([]);
  const [note, setNote] = useState("");
  useEffect(() => { if (data) setRules(data.rules); }, [data]);
  if (error) return <Container><ErrorState error={error} /></Container>;

  const authorities = [...new Set([...(hierarchy.data?.choices.authority ?? []),
    ...(hierarchy.data?.choices.unit_head ?? [])])].sort();
  const used = new Set(rules.map((r) => r.step));
  const free = Object.keys(STEP_LABELS).filter((s) => !used.has(s));
  const set = (i: number, p: Partial<SlaRule>) => setRules(rules.map((r, j) => j === i ? { ...r, ...p } : r));

  return (
    <Container size="lg">
      <PageHeader title="Response Deadlines"
        subtitle="When a waiting task is reminded, and when it is escalated" />
      <Card padding="lg">
        <Table>
          <Table.Thead><Table.Tr><Table.Th>Step</Table.Th><Table.Th>Remind after (h)</Table.Th>
            <Table.Th>Escalate after (h)</Table.Th><Table.Th>Escalation</Table.Th>
            <Table.Th>To</Table.Th><Table.Th /></Table.Tr></Table.Thead>
          <Table.Tbody>
            {rules.map((r, i) => (
              <Table.Tr key={r.step}>
                <Table.Td>{STEP_LABELS[r.step] ?? r.step}</Table.Td>
                <Table.Td><NumberInput w={90} min={1} value={r.reminder_hours}
                  onChange={(v) => set(i, { reminder_hours: Number(v) || 1 })} /></Table.Td>
                <Table.Td><NumberInput w={90} min={2} value={r.escalation_hours}
                  onChange={(v) => set(i, { escalation_hours: Number(v) || 2 })} /></Table.Td>
                <Table.Td><Select w={150} value={r.action}
                  onChange={(v) => set(i, { action: (v ?? "notify") as SlaRule["action"] })}
                  data={[{ value: "notify", label: "Notify" },
                    { value: "reassign", label: "Reassign the task" }]} /></Table.Td>
                <Table.Td><Select searchable clearable w={190} data={authorities}
                  value={r.escalate_to || null} onChange={(v) => set(i, { escalate_to: v ?? "" })} /></Table.Td>
                <Table.Td><ActionIcon variant="subtle" color="red" aria-label="Remove"
                  onClick={() => setRules(rules.filter((_, j) => j !== i))}><FaTrash size={11} /></ActionIcon></Table.Td>
              </Table.Tr>))}
          </Table.Tbody>
        </Table>
        {!rules.length && <Text c="dimmed" size="sm" mt="sm">No deadlines: nothing is reminded or escalated.</Text>}
        <Stack mt="md">
          {!!free.length && <Group>
            <Select placeholder="Add a step" data={free.map((s) => ({ value: s, label: STEP_LABELS[s] ?? s }))}
              value={null} onChange={(v) => v && setRules([...rules, { step: v, reminder_hours: 24,
                escalation_hours: 72, action: "notify", escalate_to: "" }])} />
          </Group>}
          <TextInput label="Reason for this revision" value={note}
            onChange={(e) => setNote(e.currentTarget.value)} />
          {save.error != null && <ErrorState error={save.error} />}
          <Group justify="flex-end">
            <Button loading={save.isPending} onClick={() => save.mutate({ rules, note }, {
              onSuccess: () => notifications.show({ color: "green", title: "Saved",
                message: "The next threshold run uses these." }) })}>Save deadlines</Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
