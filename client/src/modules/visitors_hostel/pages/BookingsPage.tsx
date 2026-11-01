import { useEffect, useState } from "react";
import {
  Alert, Button, Card, Container, Group, Select, Stack, Table, Text, TextInput,
} from "@mantine/core";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { createBooking, listBookings, type Booking } from "../api";

const initial = {
  visitor_name: "", visitor_email: "", visitor_phone: "", purpose: "",
  visitor_category: "A", arrival_date: "", departure_date: "", room_count: "1",
  occupant_count: "1", requested_occupancy: "single", requested_room_kind: "non_suite",
  billing_responsibility: "Indenter",
};

export default function BookingsPage() {
  const [rows, setRows] = useState<Booking[]>([]);
  const [form, setForm] = useState(initial);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function refresh() {
    setLoading(true);
    try { setRows(await listBookings()); setError(""); }
    catch (e) { setError(errorMessage(e)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(""); setSuccess("");
    try {
      const booking = await createBooking({ ...form,
        room_count: Number(form.room_count), occupant_count: Number(form.occupant_count) });
      setSuccess(`Request ${booking.booking_number} submitted.`);
      setForm(initial); await refresh();
    } catch (e) { setError(errorMessage(e)); }
    finally { setSaving(false); }
  }

  return <Container size="xl">
    <PageHeader title="Visitors Hostel bookings"
      subtitle="Submit a booking request and review your booking history." />
    {error && <Alert color="red" mb="md">{error}</Alert>}
    {success && <Alert color="green" mb="md">{success}</Alert>}
    <Card withBorder mb="md" p="lg">
      <form onSubmit={submit}>
        <Stack>
          <Text fw={600}>New online booking request</Text>
          <TextInput label="Visitor name" required value={form.visitor_name}
            onChange={(e) => setForm({ ...form, visitor_name: e.currentTarget.value })} />
          <Group grow>
            <TextInput label="Visitor email" type="email" value={form.visitor_email}
              onChange={(e) => setForm({ ...form, visitor_email: e.currentTarget.value })} />
            <TextInput label="Visitor phone" required value={form.visitor_phone}
              onChange={(e) => setForm({ ...form, visitor_phone: e.currentTarget.value })} />
          </Group>
          <TextInput label="Visit purpose" required value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.currentTarget.value })} />
          <Group grow>
            <Select label="Visitor category" data={["A", "B", "C", "D"]}
              value={form.visitor_category}
              onChange={(v) => setForm({ ...form, visitor_category: v ?? "A" })} />
            <Select label="Billing responsibility"
              data={["Visitor", "Indenter", "Institute", "Project"]}
              value={form.billing_responsibility}
              onChange={(v) => setForm({ ...form, billing_responsibility: v ?? "Indenter" })} />
          </Group>
          <Group grow>
            <TextInput label="Arrival date" type="date" required value={form.arrival_date}
              onChange={(e) => setForm({ ...form, arrival_date: e.currentTarget.value })} />
            <TextInput label="Departure date" type="date" required value={form.departure_date}
              onChange={(e) => setForm({ ...form, departure_date: e.currentTarget.value })} />
          </Group>
          <Group grow>
            <TextInput label="Rooms" type="number" min={1} required value={form.room_count}
              onChange={(e) => setForm({ ...form, room_count: e.currentTarget.value })} />
            <TextInput label="Occupants" type="number" min={1} required value={form.occupant_count}
              onChange={(e) => setForm({ ...form, occupant_count: e.currentTarget.value })} />
            <Select label="Occupancy" data={["single", "double"]}
              value={form.requested_occupancy}
              onChange={(v) => setForm({ ...form, requested_occupancy: v ?? "single" })} />
            <Select label="Room type" data={[{ value: "suite", label: "Suite" },
              { value: "non_suite", label: "Non-suite" }]}
              value={form.requested_room_kind}
              onChange={(v) => setForm({ ...form, requested_room_kind: v ?? "non_suite" })} />
          </Group>
          <Button type="submit" loading={saving}>Submit request</Button>
        </Stack>
      </form>
    </Card>
    <Card withBorder p="lg">
      <Text fw={600} mb="sm">Booking history</Text>
      {loading ? <Text c="dimmed">Loading bookings…</Text> : rows.length === 0
        ? <Text c="dimmed">No bookings found.</Text>
        : <Table.ScrollContainer minWidth={700}><Table>
          <Table.Thead><Table.Tr><Table.Th>Reference</Table.Th><Table.Th>Visitor</Table.Th>
            <Table.Th>Source</Table.Th><Table.Th>Stay</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{rows.map((r) => <Table.Tr key={r.id}>
            <Table.Td>{r.booking_number}</Table.Td><Table.Td>{r.visitor_name}</Table.Td>
            <Table.Td>{r.source}</Table.Td>
            <Table.Td>{r.arrival_date} – {r.departure_date}</Table.Td>
            <Table.Td>{r.status.replaceAll("_", " ")}</Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table></Table.ScrollContainer>}
    </Card>
  </Container>;
}
