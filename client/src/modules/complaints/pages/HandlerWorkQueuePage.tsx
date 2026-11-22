import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useComplaintAttachments, useHandlerAction, useHandlerQueue } from "../api/hooks";
import type { Complaint } from "../api/types";

export default function HandlerWorkQueuePage() {
  const queue = useHandlerQueue();
  const progress = useHandlerAction("progress");
  const resolve = useHandlerAction("resolve");
  const reject = useHandlerAction("reject");
  const escalate = useHandlerAction("escalate");
  const [notes, setNotes] = useState<Record<string, string>>({});
  if (queue.error) return <Container size="lg"><ErrorState error={queue.error} /></Container>;
  const noteFor = (reference: string) => notes[reference] ?? "";
  const update = (reference: string, value: string) => setNotes((old) => ({ ...old, [reference]: value }));
  function act(mutation: typeof progress, row: Complaint, success: string) {
    mutation.mutate({ reference: row.reference, text: noteFor(row.reference) }, {
      onSuccess: () => { update(row.reference, ""); notifications.show({ color: "green", title: success, message: "The complaint history was updated." }); },
      onError: (e) => notifications.show({ color: "red", title: "Could not update complaint", message: errorMessage(e) }),
    });
  }
  return <Container size="lg">
    <PageHeader title="Handler Work Queue" subtitle="Record progress, outcomes, and manual escalations for complaints assigned to you." />
    <Stack>
      {(queue.data?.results ?? []).map((row) => <Card withBorder key={row.reference}>
        <Stack>
          <Group justify="space-between"><Text fw={600}>{row.category}</Text><Text size="sm">{row.status} · {row.priority} priority</Text></Group>
          <Text size="xs" c="dimmed">{row.reference} · SLA due {row.sla_due_at ? new Date(row.sla_due_at).toLocaleString() : "not set"}</Text>
          <Text>{row.description}</Text>
          <ComplaintFiles reference={row.reference} />
          {row.history.map((event, index) => <Text key={`${event.event}-${index}`} size="sm" c="dimmed">{new Date(event.occurred_at).toLocaleString()} · {event.event.replaceAll("_", " ")}{event.details ? ` — ${event.details}` : ""}</Text>)}
          <Textarea label="Progress, resolution, rejection, or escalation note" value={noteFor(row.reference)} onChange={(event) => update(row.reference, event.currentTarget.value)} />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => act(progress, row, "Progress recorded")} loading={progress.isPending} disabled={!noteFor(row.reference).trim()}>Add progress</Button>
            <Button color="red" variant="light" onClick={() => act(reject, row, "Complaint rejected")} loading={reject.isPending} disabled={!noteFor(row.reference).trim()}>Reject</Button>
            <Button variant="light" onClick={() => act(escalate, row, "Complaint escalated")} loading={escalate.isPending} disabled={!noteFor(row.reference).trim()}>Escalate</Button>
            <Button onClick={() => act(resolve, row, "Complaint resolved")} loading={resolve.isPending} disabled={!noteFor(row.reference).trim()}>Resolve</Button>
          </Group>
        </Stack>
      </Card>)}
      {queue.isLoading && <Text c="dimmed">Loading assigned complaints…</Text>}
      {!queue.isLoading && !queue.data?.results.length && <Alert color="gray">No active complaints are assigned to you.</Alert>}
    </Stack>
  </Container>;
}

function ComplaintFiles({ reference }: { reference: string }) {
  const query = useComplaintAttachments(reference);
  if (!query.data?.results.length) return null;
  return <Stack gap={4}><Text size="sm" fw={500}>Attachments</Text>{query.data.results.map((file) => <a key={file.id} href={`/api/v1/complaints/attachments/${file.id}/download`} target="_blank" rel="noreferrer">{file.original_name}</a>)}</Stack>;
}
