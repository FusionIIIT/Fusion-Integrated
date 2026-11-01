import { useState } from "react";
import { Alert, Button, Card, Container, Group, Select, Stack, TextInput } from "@mantine/core";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { createOfflineBooking } from "../api";

const initial = { visitor_name: "", visitor_email: "", visitor_phone: "", purpose: "",
  visitor_category: "A", arrival_date: "", departure_date: "", room_count: "1",
  occupant_count: "1", requested_occupancy: "single", requested_room_kind: "non_suite",
  billing_responsibility: "Visitor" };

export default function OfflineBookingPage() {
  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      const result = await createOfflineBooking({ ...form, room_count: Number(form.room_count),
        occupant_count: Number(form.occupant_count) });
      setMessage(`Offline request ${result.booking_number} recorded as pending.`);
      setForm(initial);
    } catch (e) { setError(errorMessage(e)); }
    finally { setSaving(false); }
  }
  const text = (key: keyof typeof initial, label: string, type = "text") =>
    <TextInput label={label} type={type} required={!key.includes("email")} value={form[key]}
      onChange={(e) => setForm({ ...form, [key]: e.currentTarget.value })} />;
  return <Container size="md"><PageHeader title="Record offline booking"
    subtitle="Record a telephone or walk-in request. It enters the same availability and approval flow." />
    {error && <Alert color="red" mb="md">{error}</Alert>}
    {message && <Alert color="green" mb="md">{message}</Alert>}
    <Card withBorder p="lg"><form onSubmit={submit}><Stack>
      {text("visitor_name", "Visitor name")}
      <Group grow>{text("visitor_email", "Visitor email", "email")}{text("visitor_phone", "Visitor phone")}</Group>
      {text("purpose", "Visit purpose")}
      <Group grow>
        <Select label="Category" data={["A", "B", "C", "D"]} value={form.visitor_category}
          onChange={(v) => setForm({ ...form, visitor_category: v ?? "A" })} />
        <Select label="Billing responsibility" data={["Visitor", "Indenter", "Institute", "Project"]}
          value={form.billing_responsibility}
          onChange={(v) => setForm({ ...form, billing_responsibility: v ?? "Visitor" })} />
      </Group>
      <Group grow>{text("arrival_date", "Arrival", "date")}{text("departure_date", "Departure", "date")}</Group>
      <Group grow>
        {text("room_count", "Rooms", "number")}{text("occupant_count", "Occupants", "number")}
        <Select label="Occupancy" data={["single", "double"]} value={form.requested_occupancy}
          onChange={(v) => setForm({ ...form, requested_occupancy: v ?? "single" })} />
        <Select label="Room type" data={[{ value: "suite", label: "Suite" },
          { value: "non_suite", label: "Non-suite" }]}
          value={form.requested_room_kind}
          onChange={(v) => setForm({ ...form, requested_room_kind: v ?? "non_suite" })} />
      </Group>
      <Button type="submit" loading={saving}>Record request</Button>
    </Stack></form></Card>
  </Container>;
}
