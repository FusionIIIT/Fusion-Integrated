import { useEffect, useState, type FormEvent } from "react";
import { Alert, Badge, Button, Card, Container, Group, Loader, Select, Stack, Table, Text, Textarea, TextInput, Title } from "@mantine/core";
import { http, errorMessage } from "../../../lib/http";

type LeaveRequest = { id: number; category: string; status: string; start_date: string; end_date: string; chargeable_days: string; purpose: string };
type Props = { tasks?: boolean; policy?: boolean };

export function ElmPage({ tasks = false, policy = false }: Props) {
  const [items, setItems] = useState<LeaveRequest[]>([]);
  const [category, setCategory] = useState<string | null>("CL");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [purpose, setPurpose] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [balances, setBalances] = useState<Record<string, string> | null>(null);

  async function load() {
    setLoading(true); setError("");
    try {
      if (tasks) {
        const response = await http.get<{ id: number; request_id: number; task_type: string }[]>("/elm/tasks/me");
        setItems(response.data.map((t) => ({ id: t.request_id, category: "—", status: t.task_type, start_date: "—", end_date: "—", chargeable_days: "—", purpose: `Task #${t.id}` })));
      } else {
        const response = await http.get<LeaveRequest[]>("/elm/requests"); setItems(response.data);
        const balanceResponse = await http.get<{ balances: Record<string, string> }>("/elm/balances/me");
        setBalances(balanceResponse.data.balances);
      }
    } catch (e) { setError(errorMessage(e)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [tasks]);

  async function submit(event: FormEvent) {
    event.preventDefault(); if (!category || !start || !end || !purpose.trim()) return;
    setSaving(true); setError("");
    try {
      await http.post("/elm/requests", { category, start_date: start, end_date: end, purpose, half_day: "none" });
      setPurpose(""); await load();
    } catch (e) { setError(errorMessage(e)); }
    finally { setSaving(false); }
  }

  return <Container size="lg" py="xl"><Stack gap="lg">
    <div><Title order={2}>{policy ? "Leave Policy" : tasks ? "Leave Tasks" : "Employee Leave Management"}</Title>
      <Text c="dimmed" mt="xs">Submit and track leave requests. Your institution's published policy and calendar govern eligibility and balance checks.</Text></div>
    {error && <Alert color="red" title="Unable to complete request">{error}</Alert>}
    {policy ? <Alert title="Policy administration" color="yellow">Policy and calendar editing endpoints are available to authorized administrators. Role-to-designation grants must be configured by the platform administrator before this page is enabled.</Alert> : null}
    {!tasks && !policy && balances && <Card withBorder radius="md" p="lg"><Stack gap="xs"><Title order={4}>My leave balances</Title><Group gap="xs">{Object.entries(balances).map(([name, amount]) => <Badge key={name} size="lg" variant="light">{name}: {amount} days</Badge>)}</Group></Stack></Card>}
    {!tasks && !policy && <Card withBorder radius="md" p="lg"><form onSubmit={submit}><Stack>
      <Title order={4}>New leave request</Title>
      <Select label="Leave category" data={["CL", "RH", "SCL", "EL", "COL", "VL"]} value={category} onChange={setCategory} required />
      <Group grow><TextInput type="date" label="Start date" value={start} onChange={(e) => setStart(e.currentTarget.value)} required />
        <TextInput type="date" label="End date" value={end} onChange={(e) => setEnd(e.currentTarget.value)} required /></Group>
      <Textarea label="Purpose / reason" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} minRows={3} required />
      <Group justify="flex-end"><Button type="submit" loading={saving}>Submit request</Button></Group>
    </Stack></form></Card>}
    <Card withBorder radius="md" p="lg"><Group justify="space-between"><Title order={4}>{tasks ? "Assigned tasks" : "Requests"}</Title><Button variant="subtle" onClick={() => void load()}>Refresh</Button></Group>
      {loading ? <Loader mt="md" /> : items.length === 0 ? <Text c="dimmed" mt="md">No records found.</Text> : <Table.ScrollContainer minWidth={650} mt="md"><Table striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>ID</Table.Th><Table.Th>Category</Table.Th><Table.Th>Period</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Purpose / task</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => <Table.Tr key={`${item.id}-${item.status}`}><Table.Td>{item.id}</Table.Td><Table.Td>{item.category}</Table.Td><Table.Td>{item.start_date} – {item.end_date}</Table.Td><Table.Td>{item.chargeable_days}</Table.Td><Table.Td><Badge variant="light">{item.status.replaceAll("_", " ")}</Badge></Table.Td><Table.Td>{item.purpose}</Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
    </Card>
  </Stack></Container>;
}
