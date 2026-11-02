import { useState } from "react";
import { Button, Group, NumberInput, Paper, Select, Stack, Textarea, TextInput, Title, Text, Alert } from "@mantine/core";
import { DatePickerInput } from "@mantine/dates";

export default function NewRequestPage() {
  const [form, setForm] = useState({
    title: "", description: "", location: "",
    category: "repair", priority: "medium",
    estimated_cost: 0, required_by: null as Date | null,
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setError("");
    const payload = {
      ...form,
      required_by: form.required_by ? form.required_by.toISOString().split("T")[0] : null,
    };
    const resp = await fetch("/api/v1/iwd/requests/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      setSubmitted(true);
    } else {
      const data = await resp.json();
      setError(JSON.stringify(data));
    }
  };

  if (submitted) {
    return (
      <Stack p="md">
        <Alert color="green" title="Request Submitted">
          Your work request has been created successfully. The IWD team will review it shortly.
        </Alert>
        <Button variant="outline" onClick={() => { setSubmitted(false); setForm({ title:"", description:"", location:"", category:"repair", priority:"medium", estimated_cost:0, required_by:null }); }}>
          Submit Another
        </Button>
      </Stack>
    );
  }

  return (
    <Stack gap="md" p="md">
      <Title order={2}>Submit New Work Request</Title>
      <Paper shadow="xs" p="md" withBorder>
        <Stack gap="sm">
          <TextInput label="Title" required placeholder="e.g. Repair broken window in Room 204" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <Textarea label="Description" required rows={4} placeholder="Describe the issue in detail..." value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <TextInput label="Location" required placeholder="e.g. Block A, Room 204" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          <Group grow>
            <Select label="Category" data={["civil","electrical","plumbing","carpentry","housekeeping","repair","new_construction","other"]} value={form.category} onChange={(v) => setForm({ ...form, category: v ?? "repair" })} />
            <Select label="Priority" data={["low","medium","high","urgent"]} value={form.priority} onChange={(v) => setForm({ ...form, priority: v ?? "medium" })} />
          </Group>
          <NumberInput label="Estimated Cost (Rs.)" min={0} value={form.estimated_cost} onChange={(v) => setForm({ ...form, estimated_cost: Number(v) })} />
          {error && <Text c="red" size="sm">{error}</Text>}
          <Group justify="flex-end">
            <Button onClick={handleSubmit}>Submit Request</Button>
          </Group>
        </Stack>
      </Paper>
    </Stack>
  );
}

