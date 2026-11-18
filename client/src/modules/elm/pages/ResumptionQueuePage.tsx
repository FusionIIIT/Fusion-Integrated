import { useState } from "react";
import { Button, Card, Container, Group, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useResumptionQueue, useVerifyResumption } from "../api";
export default function ResumptionQueuePage() {
  const query = useResumptionQueue(); const verify = useVerifyResumption(); const [notes, setNotes] = useState<Record<number, string>>({});
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  return <Container size="lg"><PageHeader title="Resumption Review" subtitle="Review actual return dates for EL, COL and VL and synchronize the approved leave period and balance when required." />
    {query.isPending ? <Text c="dimmed">Loading resumptions…</Text> : (query.data ?? []).length === 0 ? <Card withBorder><Text c="dimmed">No resumptions are awaiting your review.</Text></Card> :
      <Stack>{(query.data ?? []).map((row) => <Card withBorder key={row.id}><Stack gap="sm"><Title order={4}>Leave request #{row.id} · {row.category}</Title>
        <Text size="sm">Employee ID {row.user_id} · Approved period {row.start_date} – {row.end_date}</Text>
        <Text>Actual resumption date: {row.actual_return_date ?? "Not supplied"} · Outcome: {row.resumption_kind ?? "—"}</Text>
        {row.resumption_note && <Text size="sm">Employee details: {row.resumption_note}</Text>}
        <Textarea label="Review note" value={notes[row.id] ?? ""} onChange={(e) => setNotes((old) => ({ ...old, [row.id]: e.currentTarget.value }))} />
        <Group justify="flex-end"><Button loading={verify.isPending} onClick={() => verify.mutate({ id: row.id, note: notes[row.id] ?? "" }, { onSuccess: () => notifications.show({ color: "green", title: "Resumption reviewed", message: `Request #${row.id} synchronized.` }), onError: (e) => notifications.show({ color: "red", title: "Review failed", message: errorMessage(e) }) })}>Verify and synchronize</Button></Group>
      </Stack></Card>)}</Stack>}
  </Container>;
}
