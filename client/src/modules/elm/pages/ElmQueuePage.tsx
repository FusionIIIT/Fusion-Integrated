import { useCallback, useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { getRequests, requestAction } from "../api";
import type { LeaveRequest } from "../api";

export default function ElmQueuePage() {
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const refresh = useCallback(async () => {
    try { setRows(await getRequests(true)); }
    catch (error) { notifications.show({ color: "red", title: "Could not load approval queue", message: errorMessage(error) }); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  async function act(row: LeaveRequest, action: string) {
    setBusy(row.id);
    try { await requestAction(row.id, action, notes[row.id] ?? ""); await refresh(); }
    catch (error) { notifications.show({ color: "red", title: "Workflow action failed", message: errorMessage(error) }); }
    finally { setBusy(null); }
  }

  return <Container size="xl">
    <PageHeader title="Approval Queue" subtitle="Only requests assigned to your account are shown" />
    <Card padding="lg">
      {rows.length ? <Table.ScrollContainer minWidth={820}><Table striped highlightOnHover>
        <Table.Thead><Table.Tr><Table.Th>Request</Table.Th><Table.Th>Employee</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Stage</Table.Th><Table.Th>Decision note</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{rows.map((row) => <Table.Tr key={row.id}>
          <Table.Td>{row.category} <Text size="xs" c="dimmed">{row.reason}</Text></Table.Td>
          <Table.Td>#{row.employee_user_id}</Table.Td><Table.Td>{row.starts_on} – {row.ends_on}<Text size="xs">{row.chargeable_days} days</Text></Table.Td>
          <Table.Td><Badge variant="light">{row.assigned_stage.replaceAll("_", " ")}</Badge></Table.Td>
          <Table.Td><TextInput aria-label="Decision note" value={notes[row.id] ?? ""} onChange={(e) => setNotes({ ...notes, [row.id]: e.currentTarget.value })} /></Table.Td>
          <Table.Td><Group gap="xs" wrap="wrap">{row.assigned_stage === "substitute" ? <><Button size="xs" loading={busy === row.id} onClick={() => void act(row, "accept_substitute")}>Accept</Button><Button size="xs" color="red" variant="light" onClick={() => void act(row, "decline_substitute")}>Decline</Button></> : row.assigned_stage === "unit_head" && !["CL", "RH"].includes(row.category) ? <><Button size="xs" loading={busy === row.id} onClick={() => void act(row, "recommended")}>Recommend</Button><Button size="xs" color="orange" variant="light" onClick={() => void act(row, "not_recommended")}>Not recommended</Button></> : row.assigned_stage === "establishment" ? <Button size="xs" loading={busy === row.id} onClick={() => void act(row, "verify")}>Verify and route</Button> : <><Button size="xs" loading={busy === row.id} onClick={() => void act(row, "approve")}>Approve</Button><Button size="xs" color="red" variant="light" onClick={() => void act(row, "reject")}>Reject</Button></>}</Group></Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer> : <Alert color="gray">No requests are assigned to you.</Alert>}
    </Card>
  </Container>;
}
