import {
  Alert, Button, Card, Checkbox, Container, Group, NumberInput, Select, Stack, Table, Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useState } from "react";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePolicy, useSavePolicy } from "../api/hooks";
import type { CategoryRule } from "../api/types";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** EL-UC-014: saving creates a revision that governs at once; there is no draft (BR-EL-030). */
export default function PolicyPage() {
  const { data, isPending, error } = usePolicy();
  const save = useSavePolicy();
  const [rules, setRules] = useState<CategoryRule[]>([]);
  const [weekend, setWeekend] = useState<number[]>([5, 6]);
  const [backdate, setBackdate] = useState(0);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!data) return;
    setRules(data.rules);
    setWeekend(data.weekend_days);
    setBackdate(data.max_backdate_days);
  }, [data]);

  if (error) return <Container><ErrorState error={error} /></Container>;
  const update = (i: number, patch: Partial<CategoryRule>) =>
    setRules(rules.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <Container size="lg">
      <PageHeader title="Leave Policy"
        subtitle={data?.revision_id ? `Revision ${data.revision_id} is in effect` : "Not configured"} />
      {!isPending && !data?.revision_id && (
        <Alert color="yellow" mb="md">No policy exists yet. Run <code>manage.py leave_seed</code> to
          load the baseline numbers, then revise them here.</Alert>)}
      <Card padding="lg">
        <Stack>
          <Table>
            <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Days per year</Table.Th>
              <Table.Th>Substitute</Table.Th><Table.Th>Evidence from (days)</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {rules.map((r, i) => (
                <Table.Tr key={r.category}>
                  <Table.Td><Text fw={600}>{r.category}</Text></Table.Td>
                  <Table.Td><NumberInput w={110} min={0} max={366} step={0.5} decimalScale={1}
                    value={Number(r.annual_entitlement)}
                    onChange={(v) => update(i, { annual_entitlement: String(v ?? 0) })} /></Table.Td>
                  <Table.Td><Select w={150} value={r.substitute}
                    onChange={(v) => update(i, { substitute: (v ?? "optional") as CategoryRule["substitute"] })}
                    data={[{ value: "optional", label: "Applicant decides" },
                      { value: "required", label: "Required" }, { value: "none", label: "Not taken" }]} /></Table.Td>
                  <Table.Td><NumberInput w={110} min={0.5} step={0.5} decimalScale={1}
                    placeholder="never" value={r.evidence_min_days == null ? "" : Number(r.evidence_min_days)}
                    onChange={(v) => update(i, { evidence_min_days: v === "" ? null : String(v) })} /></Table.Td>
                </Table.Tr>))}
            </Table.Tbody>
          </Table>
          <Checkbox.Group label="Weekend days (not counted for CL, SCL and RH)"
            value={weekend.map(String)} onChange={(v) => setWeekend(v.map(Number))}>
            <Group mt={6}>{DAYS.map((d, i) => <Checkbox key={d} value={String(i)} label={d} />)}</Group>
          </Checkbox.Group>
          <NumberInput label="How many days back an employee may apply" min={0} max={30} w={260}
            description="0 means past leave is recorded by the Leave Administrator instead"
            value={backdate} onChange={(v) => setBackdate(Number(v) || 0)} />
          <TextInput label="Office order or reason for this revision" value={note}
            onChange={(e) => setNote(e.currentTarget.value)} />
          {save.error != null && <ErrorState error={save.error} />}
          <Group justify="flex-end">
            <Button loading={save.isPending} disabled={!rules.length}
              onClick={() => save.mutate({ rules, weekend_days: weekend, max_backdate_days: backdate,
                note }, { onSuccess: () => notifications.show({ color: "green",
                title: "Policy saved", message: "The new revision applies from now." }) })}>
              Save as current policy</Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
