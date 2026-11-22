import { Button, Group, NumberInput, Select, Stack, TextInput, Textarea, Title } from "@mantine/core";
import { useState } from "react";

import { useCreateBooking } from "../api/hooks";

export default function BookingPage() {
  const create = useCreateBooking();
  const [form, setForm] = useState({
    visitor_name: "",
    visitor_phone: "",
    visitor_email: "",
    visitor_organization: "",
    visitor_address: "",
    purpose: "",
    category: "A",
    occupancy: "single",
    arrival_date: "",
    departure_date: "",
    rooms_required: 1,
    occupants: 1,
    billing_responsibility: "institute",
    billing_reference: "",
  });
  const set = (key: string, value: unknown) =>
    setForm((current) => ({ ...current, [key]: value }));

  return (
    <Stack>
      <Title order={2}>Submit a visitor booking</Title>
      <TextInput label="Visitor name" required value={form.visitor_name}
        onChange={(event) => set("visitor_name", event.currentTarget.value)} />
      <TextInput label="Phone" value={form.visitor_phone}
        onChange={(event) => set("visitor_phone", event.currentTarget.value)} />
      <TextInput label="Email" value={form.visitor_email}
        onChange={(event) => set("visitor_email", event.currentTarget.value)} />
      <TextInput label="Organization" value={form.visitor_organization}
        onChange={(event) => set("visitor_organization", event.currentTarget.value)} />
      <TextInput label="Address" value={form.visitor_address}
        onChange={(event) => set("visitor_address", event.currentTarget.value)} />
      <Textarea label="Purpose" required value={form.purpose}
        onChange={(event) => set("purpose", event.currentTarget.value)} />
      <Group grow>
        <Select label="Category" data={["A", "B", "C", "D"]}
          value={form.category} onChange={(value) => set("category", value ?? "A")} />
        <Select label="Occupancy" data={["single", "double", "suite"]}
          value={form.occupancy} onChange={(value) => set("occupancy", value ?? "single")} />
        <TextInput label="Arrival date" type="date" required value={form.arrival_date}
          onChange={(event) => set("arrival_date", event.currentTarget.value)} />
        <TextInput label="Departure date" type="date" required value={form.departure_date}
          onChange={(event) => set("departure_date", event.currentTarget.value)} />
      </Group>
      <Group grow>
        <NumberInput label="Rooms required" min={1} max={50} value={form.rooms_required}
          onChange={(value) => set("rooms_required", value)} />
        <NumberInput label="Occupants" min={1} max={200} value={form.occupants}
          onChange={(value) => set("occupants", value)} />
        <Select label="Billing responsibility"
          data={["visitor", "indenter", "institute", "project"]}
          value={form.billing_responsibility}
          onChange={(value) => set("billing_responsibility", value ?? "institute")} />
      </Group>
      <TextInput label="Billing reference" value={form.billing_reference}
        onChange={(event) => set("billing_reference", event.currentTarget.value)} />
      <Button onClick={() => create.mutate(form)}
        loading={create.isPending} disabled={!form.visitor_name || !form.purpose
          || !form.arrival_date || !form.departure_date}>
        Submit booking
      </Button>
    </Stack>
  );
}
