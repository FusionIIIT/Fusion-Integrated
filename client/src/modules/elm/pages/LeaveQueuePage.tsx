import { useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecideLeave, useLeaveQueue } from "../api";

export default function LeaveQueuePage() {
  const query = useLeaveQueue(); const decide = useDecideLeave(); const [notes, setNotes] = useState<Record<number, string>>({});
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  function submit(id: number, decision: string) {
    decide.mutate({ id, decision, note: notes[id] ?? "" }, {
      onSuccess: () => notifications.show({ color: "green", title: "Decision recorded", message: `Request #${id} updated.` }),
      onError: (e) => notifications.show({ color: "red", title: "Could not record decision", message: errorMessage(e) }),
    });
  }
  return <Container size="lg"><PageHeader title="Leave Review Queue" subtitle="Review requests assigned to your active designation." />
    {query.isPending ? <Text c="dimmed">Loading queue…</Text> : (query.data ?? []).length === 0 ? <Card withBorder><Text c="dimmed">There are no requests assigned to your designation.</Text></Card> :
      <Stack>{(query.data ?? []).map((row) => <Card withBorder key={row.id}><Stack gap="sm">
        <Group justify="space-between"><Title order={4}>#{row.id} · {row.category}</Title><Badge>{row.status.replaceAll("_", " ")}</Badge></Group>
        <Text size="sm">Employee ID: {row.user_id} · {row.start_date} – {row.end_date} · {row.days} day(s)</Text>
        {row.purpose && <Text>{row.purpose}</Text>}
        <Text size="sm" c="dimmed">Assigned to: {row.current_role || "—"}{row.substitute_status === "accepted" ? " · substitute accepted" : ""}</Text>
        <Textarea label="Decision note" value={notes[row.id] ?? ""} onChange={(e) => setNotes((old) => ({ ...old, [row.id]: e.currentTarget.value }))} />
        <Group justify="flex-end" gap="xs">
          {row.status === "awaiting_unit_head" && !["CL", "RH"].includes(row.category) && <Button variant="light" onClick={() => submit(row.id, "recommend")} loading={decide.isPending}>Recommend</Button>}
          {row.status === "awaiting_establishment" && <Button variant="light" onClick={() => submit(row.id, "forward")} loading={decide.isPending}>Forward</Button>}
          {row.status !== "awaiting_director" && <Button color="red" variant="light" onClick={() => submit(row.id, row.status === "awaiting_unit_head" && !["CL", "RH"].includes(row.category) ? "not_recommended" : "reject")} loading={decide.isPending}>{row.status === "awaiting_unit_head" && !["CL", "RH"].includes(row.category) ? "Not recommended" : "Reject"}</Button>}
          {row.status !== "awaiting_establishment" && !(row.status === "awaiting_unit_head" && !["CL", "RH"].includes(row.category)) && <Button onClick={() => submit(row.id, "approve")} loading={decide.isPending}>{row.status === "awaiting_director" ? "Self-sanction" : row.status === "cancellation_pending" ? "Approve cancellation" : "Approve / Sanction"}</Button>}
        </Group>
      </Stack></Card>)}</Stack>}
  </Container>;
}
