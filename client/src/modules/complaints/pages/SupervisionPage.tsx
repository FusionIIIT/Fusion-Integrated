import { Alert, Button, Card, Container, Group, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useEscalatedQueue, usePendingClosures, useReopeningQueue, useReviewReopening, useVerifySupervisorClosure } from "../api/hooks";

export default function SupervisionPage() {
  const closures = usePendingClosures();
  const requests = useReopeningQueue();
  const escalated = useEscalatedQueue();
  const verify = useVerifySupervisorClosure();
  const decision = useReviewReopening();
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const error = closures.error ?? requests.error ?? escalated.error;
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  function decide(id: number, value: "approved" | "denied") {
    decision.mutate({ id, decision: value, reason: reasons[id] ?? "" }, { onSuccess: () => notifications.show({ color: "green", title: "Decision recorded", message: value === "approved" ? "The complaint has returned to active handling." : "The request was denied." }), onError: (e) => notifications.show({ color: "red", title: "Could not record decision", message: errorMessage(e) }) });
  }
  return <Container size="lg"><PageHeader title="Supervisor Queue" subtitle="Closure verification and complaint reopening requests." />
    <Text fw={600} mt="md">Escalated complaints</Text>
    <Stack mt="sm">{(escalated.data?.results ?? []).map((row) => <Card withBorder key={row.reference}><Group justify="space-between"><Text fw={500}>{row.category}</Text><Text size="sm">{row.status} · {row.priority} priority</Text></Group><Text size="xs" c="dimmed">{row.reference} · due {row.sla_due_at ? new Date(row.sla_due_at).toLocaleString() : "unknown"}</Text><Text mt="sm">{row.description}</Text>{row.history.filter((item) => item.event.includes("escalation")).map((item, index) => <Text key={index} size="sm" c="dimmed">{item.event.replaceAll("_", " ")} · {item.details}</Text>)}</Card>)}{!escalated.isLoading && !escalated.data?.results.length && <Alert color="gray">There are no escalated complaints.</Alert>}</Stack>
    <Text fw={600} mt="xl">Resolved complaints awaiting verification</Text>
    <Stack mt="sm">{(closures.data?.results ?? []).map((row) => <Card withBorder key={row.reference}><Group justify="space-between"><div><Text fw={500}>{row.category}</Text><Text size="xs" c="dimmed">{row.reference}</Text></div><Button onClick={() => verify.mutate(row.reference, { onSuccess: () => notifications.show({ color: "green", title: "Complaint closed", message: "Verification was recorded." }), onError: (e) => notifications.show({ color: "red", title: "Could not verify", message: errorMessage(e) }) })} loading={verify.isPending}>Verify and close</Button></Group><Text mt="sm">{row.description}</Text><Text size="sm" c="dimmed" mt="xs">Resolution: {row.resolution_details}</Text></Card>)}{!closures.isLoading && !closures.data?.results.length && <Alert color="gray">No resolved complaints are waiting for supervisor verification.</Alert>}</Stack>
    <Text fw={600} mt="xl">Reopening requests</Text>
    <Stack mt="sm">{(requests.data?.results ?? []).map((row) => <Card withBorder key={row.id}><Text size="xs" c="dimmed">Complaint #{row.complaint_id}</Text><Text mt="xs">{row.reason}</Text><Textarea mt="sm" label="Decision note (optional)" value={reasons[row.id] ?? ""} onChange={(e) => setReasons((old) => ({ ...old, [row.id]: e.currentTarget.value }))} /><Group justify="flex-end" mt="sm"><Button variant="default" color="red" onClick={() => decide(row.id, "denied")} loading={decision.isPending}>Deny</Button><Button onClick={() => decide(row.id, "approved")} loading={decision.isPending}>Approve</Button></Group></Card>)}{!requests.isLoading && !requests.data?.results.length && <Alert color="gray">No reopening requests are waiting for review.</Alert>}</Stack>
  </Container>;
}
