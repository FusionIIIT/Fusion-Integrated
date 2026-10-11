import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Alert, Button, Card, Group, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { http, errorMessage } from "../../../lib/http";

type LeaveRequest = {
  id: number;
  employee_name: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  status: string;
  reason: string;
};

export default function LeaveRequestsPage() {
  const [items, setItems] = useState<LeaveRequest[]>([]);
  const [start, setStart] = useState<Date | null>(null);
  const [end, setEnd] = useState<Date | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await http.get("/elm/leave-requests/");
      const payload = response.data;
      setItems(Array.isArray(payload) ? payload : (payload.results ?? []));
      setError("");
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!start || !end || end < start || !reason.trim()) {
      setError("Enter a valid date range and reason.");
      return;
    }
    setBusy(true);
    try {
      await http.post("/elm/leave-requests/", {
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
        reason: reason.trim(),
      });
      setReason("");
      setStart(null);
      setEnd(null);
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack gap="md">
      <Title order={2}>Employee Leave Management</Title>
      <Text c="dimmed" size="sm">Submit a leave request and review its current status.</Text>
      {error && <Alert color="red" title="Unable to complete request">{error}</Alert>}
      <Card withBorder>
        <form onSubmit={submit}>
          <Stack gap="sm">
            <Group grow>
              <DateInput label="Start date" value={start} onChange={setStart} required />
              <DateInput label="End date" value={end} onChange={setEnd} minDate={start ?? undefined} required />
            </Group>
            <Textarea label="Reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)}
              minRows={3} maxRows={6} required maxLength={2000} />
            <Group justify="flex-end">
              <Button type="submit" loading={busy}>Submit request</Button>
            </Group>
          </Stack>
        </form>
      </Card>
      <Title order={3}>My leave requests</Title>
      {items.length === 0 ? <Text c="dimmed">No leave requests found.</Text> : (
        <Table.ScrollContainer minWidth={600}>
          <Table striped highlightOnHover>
            <Table.Thead><Table.Tr>
              <Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Reason</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>{items.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>{item.start_date} – {item.end_date}</Table.Td>
                <Table.Td>{item.duration_days}</Table.Td>
                <Table.Td>{item.status}</Table.Td>
                <Table.Td>{item.reason}</Table.Td>
              </Table.Tr>
            ))}</Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}
