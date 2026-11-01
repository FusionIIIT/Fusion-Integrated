import { useEffect, useState } from "react";
import { Alert, Button, Container, Group, Table, Text } from "@mantine/core";
import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { bookingAction, listBookings, type Booking } from "../api";

export default function OperationsPage() {
  const { can } = useAuth();
  const [rows, setRows] = useState<Booking[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  async function refresh() {
    try { setRows(await listBookings()); setError(""); }
    catch (e) { setError(errorMessage(e)); }
  }
  useEffect(() => { void refresh(); }, []);
  async function act(id: number, action: string, payload: Record<string, unknown>) {
    setBusy(id); setError("");
    try { await bookingAction(id, action, payload); await refresh(); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(null); }
  }
  return <Container size="xl"><PageHeader title="VH Operations"
    subtitle="Review requests, record decisions, and manage approved stays." />
    {error && <Alert color="red" mb="md">{error}</Alert>}
    {!rows.length && !error ? <Text c="dimmed">No booking requests.</Text> :
      <Table.ScrollContainer minWidth={850}><Table><Table.Thead><Table.Tr>
        <Table.Th>Reference</Table.Th><Table.Th>Visitor</Table.Th><Table.Th>Source</Table.Th>
        <Table.Th>Dates</Table.Th><Table.Th>Status</Table.Th><Table.Th>Actions</Table.Th>
      </Table.Tr></Table.Thead><Table.Tbody>{rows.map((r) => <Table.Tr key={r.id}>
        <Table.Td>{r.booking_number}</Table.Td><Table.Td>{r.visitor_name}</Table.Td>
        <Table.Td>{r.source}</Table.Td><Table.Td>{r.arrival_date} – {r.departure_date}</Table.Td>
        <Table.Td>{r.status.replaceAll("_", " ")}</Table.Td><Table.Td><Group gap="xs">
          {can("visitor_hostel.booking.review") && r.status === "pending" && <>
            <Button size="xs" loading={busy === r.id} onClick={() => void act(r.id, "review", { outcome: "forward" })}>Forward</Button>
            <Button size="xs" color="red" variant="light" loading={busy === r.id}
              onClick={() => void act(r.id, "review", { outcome: "reject" })}>Reject</Button></>}
          {can("visitor_hostel.booking.decide") && r.status === "forwarded" && <>
            <Button size="xs" loading={busy === r.id} onClick={() => void act(r.id, "decision", { decision: "approve" })}>Approve</Button>
            <Button size="xs" color="red" variant="light" loading={busy === r.id}
              onClick={() => void act(r.id, "decision", { decision: "reject" })}>Reject</Button></>}
        </Group></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
  </Container>;
}
