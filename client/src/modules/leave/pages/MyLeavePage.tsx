import { useEffect, useState, type FormEvent } from "react";
import { Alert, Button, Card, Group, NumberFormatter, Select, Stack, Table, Text, Textarea, Title } from "@mantine/core";

import { http } from "../../../lib/http";
import type { MyLeave } from "../api";

export default function MyLeavePage() {
  const [data, setData] = useState<MyLeave | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function refresh() {
    try { setData((await http.get<MyLeave>("/leave/mine")).data); }
    catch { setError("Could not load your leave information."); }
  }

  useEffect(() => { void refresh(); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await http.post("/leave/requests/create", {
        leave_type: Number(form.get("leave_type")), start_date: form.get("start_date"),
        end_date: form.get("end_date"), reason: form.get("reason"),
      });
      (event.target as HTMLFormElement).reset();
      await refresh();
    } catch { setError("The leave request could not be submitted. Check the dates and available balance."); }
    finally { setSaving(false); }
  }

  async function cancel(id: number) {
    try { await http.post(`/leave/requests/${id}/cancel`, {}); await refresh(); }
    catch { setError("Only your pending requests can be cancelled."); }
  }

  if (!data) return <Stack p="lg">{error ? <Alert color="red">{error}</Alert> : <Text>Loading leave information…</Text>}</Stack>;

  return <Stack p="lg" maw={1000}>
    <Title order={2}>My Leave</Title>
    {error && <Alert color="red" onClose={() => setError("")} withCloseButton>{error}</Alert>}
    <Title order={4}>Balances</Title>
    <Group align="stretch">{data.balances.map((balance) => <Card key={balance.id} withBorder>
      <Text fw={600}>{balance.leave_type_name}</Text>
      <Text size="sm">Available: <NumberFormatter value={balance.available_days} decimalScale={1} /> days</Text>
    </Card>)}</Group>
    <Card withBorder>
      <form onSubmit={submit}><Stack>
        <Title order={4}>Request leave</Title>
        <Select name="leave_type" label="Leave type" required data={data.leave_types.map((type) => ({ value: String(type.id), label: type.name }))} />
        <Group grow><input name="start_date" type="date" required aria-label="Start date" /><input name="end_date" type="date" required aria-label="End date" /></Group>
        <Textarea name="reason" label="Reason" required minLength={3} maxLength={1000} />
        <Button type="submit" loading={saving} w="fit-content">Submit request</Button>
      </Stack></form>
    </Card>
    <Title order={4}>Your requests</Title>
    <Table striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>Type</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th /></Table.Tr></Table.Thead>
      <Table.Tbody>{data.requests.map((row) => <Table.Tr key={row.id}><Table.Td>{row.leave_type_name}</Table.Td><Table.Td>{row.start_date} – {row.end_date}</Table.Td><Table.Td>{row.days}</Table.Td><Table.Td>{row.status}</Table.Td><Table.Td>{row.status === "pending" && <Button size="xs" variant="subtle" color="red" onClick={() => void cancel(row.id)}>Cancel</Button>}</Table.Td></Table.Tr>)}</Table.Tbody>
    </Table>
  </Stack>;
}
