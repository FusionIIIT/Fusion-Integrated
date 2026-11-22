import { useState } from "react";
import { Alert, Button, Checkbox, Container, FileInput, Group, NumberInput, Stack, Table, Text, Textarea, TextInput, Title } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage, http } from "../../lib/http";
import { useAuth } from "../../auth/AuthProvider";

type Visit = { id: number; visitor_name: string; host_user_id: number; status: string;
  purpose: string; starts_at: string; ends_at: string; requested_zones: string[] };

function useVisits(inbox = false, admin = false) {
  const suffix = admin ? "/admin-review" : inbox ? "/inbox" : "";
  return useQuery({ queryKey: ["vms", suffix || "visits"],
    queryFn: async () => (await http.get<Visit[]>(`/vms/visits${suffix}`)).data });
}

function VisitTable({ rows, actions = false }: { rows: Visit[]; actions?: boolean }) {
  const client = useQueryClient();
  const [reason, setReason] = useState("");
  const decision = useMutation({
    mutationFn: async ({ id, move }: { id: number; move: string }) =>
      (await http.post(`/vms/visits/${id}/${move}`, { reason })).data,
    onSuccess: () => { setReason(""); void client.invalidateQueries({ queryKey: ["vms"] }); },
  });
  return <Stack>
    {decision.isError && <Alert color="red" title="Could not update visit">{errorMessage(decision.error)}</Alert>}
    {actions && <Textarea label="Decision note" value={reason} onChange={(e) => setReason(e.currentTarget.value)} maxLength={500} />}
    <Table striped highlightOnHover withTableBorder><Table.Thead><Table.Tr>
      <Table.Th>Visitor</Table.Th><Table.Th>Purpose</Table.Th><Table.Th>Window</Table.Th><Table.Th>Status</Table.Th>{actions && <Table.Th>Decision</Table.Th>}
    </Table.Tr></Table.Thead><Table.Tbody>{rows.map((v) => <Table.Tr key={v.id}>
      <Table.Td>{v.visitor_name}</Table.Td><Table.Td>{v.purpose}</Table.Td>
      <Table.Td>{new Date(v.starts_at).toLocaleString()} – {new Date(v.ends_at).toLocaleString()}</Table.Td>
      <Table.Td>{v.status.replaceAll("_", " ")}</Table.Td>
      {actions && <Table.Td><Group><Button size="xs" onClick={() => decision.mutate({ id: v.id, move: "approve" })} loading={decision.isPending}>Approve</Button>
        <Button size="xs" color="red" variant="light" onClick={() => decision.mutate({ id: v.id, move: "reject" })} loading={decision.isPending}>Reject</Button></Group></Table.Td>}
    </Table.Tr>)}</Table.Tbody></Table>
  </Stack>;
}

export function VmsVisitsPage() {
  const q = useVisits();
  return <Container size="xl" py="md"><Stack><Title order={2}>Visitor requests</Title>
    {q.isError && <Alert color="red">Could not load visitor requests.</Alert>}
    {q.isPending ? <Text>Loading visits…</Text> : <VisitTable rows={q.data ?? []} />}
  </Stack></Container>;
}

export function VmsHomePage() {
  const { can } = useAuth();
  return can("vms.visit_request.approve") ? <HostInboxPage /> : <VmsVisitsPage />;
}

export function HostInboxPage({ admin = false }: { admin?: boolean }) {
  const { session } = useAuth();
  const q = useVisits(true, admin);
  const role = session?.active_role?.trim().toLocaleLowerCase() ?? "";
  const canDecide = admin
    ? ["admin", "super admin", "super_admin"].includes(role)
    : ["host", "faculty", "staff", "vms demo host"].includes(role);
  return <Container size="xl" py="md"><Stack><Title order={2}>{admin ? "Urgent and contingency review" : "Requests awaiting your decision"}</Title>
    {q.isError && <Alert color="red">Could not load the host inbox.</Alert>}
    {!canDecide && <Alert color="yellow" title="Switch role to decide requests">
      {admin
        ? "Select Admin to review urgent or contingency requests."
        : "Select VMS Demo Host to approve or reject regular visit requests."}
    </Alert>}
    {q.isPending ? <Text>Loading requests…</Text> : <VisitTable rows={q.data ?? []} actions={canDecide} />}
  </Stack></Container>;
}

type EventRow = { id: number; name: string; starts_at: string; ends_at: string; zones: string[];
  status: string; fast_lane_enabled: boolean; overflow_limit: number | null;
  rate_limit_per_minute: number | null; guest_count: number; on_site_count: number;
  total_entries: number; entries_last_minute: number };

export function EventAdminPage() {
  const { session } = useAuth();
  const client = useQueryClient();
  const activeRole = session?.active_role?.trim().toLocaleLowerCase().replaceAll("_", " ") ?? "";
  const canManageEvents = ["admin", "super admin"].includes(activeRole);
  const [name, setName] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [zones, setZones] = useState("");
  const [guestFiles, setGuestFiles] = useState<Record<number, File | null>>({});
  const [importKeys, setImportKeys] = useState<Record<number, string>>({});
  const [controlDrafts, setControlDrafts] = useState<Record<number, {
    overflow: number | null; rate: number | null }>>({});
  const events = useQuery({ queryKey: ["vms", "events"], enabled: canManageEvents,
    queryFn: async () => (await http.get<EventRow[]>("/vms/admin/events")).data });
  const refresh = () => client.invalidateQueries({ queryKey: ["vms", "events"] });
  const create = useMutation({ mutationFn: async () => (await http.post("/vms/admin/events", {
    name, starts_at: new Date(startsAt).toISOString(), ends_at: new Date(endsAt).toISOString(),
    zones: zones.split(",").map((z) => z.trim()).filter(Boolean), fast_lane_enabled: false,
  })).data, onSuccess: () => { setName(""); void refresh(); } });
  const act = useMutation({ mutationFn: async ({ id, action }: { id: number; action: string }) =>
    (await http.post(`/vms/admin/events/${id}/${action}`)).data, onSuccess: () => void refresh() });
  const controls = useMutation({ mutationFn: async ({ event, fastLane, overflow, rate }:
    { event: EventRow; fastLane: boolean; overflow: number | null; rate: number | null }) =>
    (await http.patch(`/vms/admin/events/${event.id}/controls`, {
      fast_lane_enabled: fastLane, overflow_limit: overflow, rate_limit_per_minute: rate,
    })).data, onSuccess: () => void refresh() });
  const importGuests = useMutation({ mutationFn: async ({ id, file, key }: { id: number; file: File; key: string }) => {
    const form = new FormData(); form.set("file", file);
    return (await http.post(`/vms/admin/events/${id}/guests`, form,
      { headers: { "Idempotency-Key": key } })).data;
  }, onSuccess: () => void refresh() });
  return <Container size="xl" py="md"><Stack>
    <Title order={2}>Special events</Title>
    {!canManageEvents && <Alert color="yellow" title="Admin role required">
      Switch to Admin to load and manage special events.
    </Alert>}
    {canManageEvents && events.isError && <Alert color="red" title="Could not load events">{errorMessage(events.error)}</Alert>}
    {(create.isError || act.isError || controls.isError || importGuests.isError) &&
      <Alert color="red" title="Event action failed">{errorMessage(
        create.error ?? act.error ?? controls.error ?? importGuests.error)}</Alert>}
    {canManageEvents && <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }}><Stack>
      <Title order={4}>Create event</Title>
      <TextInput label="Event name" value={name} onChange={(e) => setName(e.currentTarget.value)} required maxLength={180} />
      <TextInput label="Starts" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.currentTarget.value)} required />
      <TextInput label="Ends" type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.currentTarget.value)} required />
      <TextInput label="Allowed zones, comma separated" value={zones} onChange={(e) => setZones(e.currentTarget.value)} />
      <Button type="submit" loading={create.isPending}>Create draft event</Button>
    </Stack></form>}
    {canManageEvents && (events.isPending ? <Text>Loading events…</Text> : <Table striped withTableBorder><Table.Thead><Table.Tr>
      <Table.Th>Event</Table.Th><Table.Th>Window</Table.Th><Table.Th>State</Table.Th><Table.Th>Attendance</Table.Th><Table.Th>Controls and guests</Table.Th>
    </Table.Tr></Table.Thead><Table.Tbody>{(events.data ?? []).map((event) => {
      const draft = controlDrafts[event.id];
      return <Table.Tr key={event.id}>
      <Table.Td>{event.name}<Text size="xs" c="dimmed">Zones: {event.zones.join(", ") || "none"}</Text></Table.Td>
      <Table.Td>{new Date(event.starts_at).toLocaleString()} – {new Date(event.ends_at).toLocaleString()}</Table.Td>
      <Table.Td>{event.status}</Table.Td><Table.Td>{event.on_site_count} on site / {event.guest_count} assigned
        <Text size="xs" c="dimmed">{event.entries_last_minute} entries/minute · {event.total_entries} total</Text>
      </Table.Td>
      <Table.Td><Stack gap="xs">
        {event.status === "draft" && <Button size="xs" onClick={() => act.mutate({ id: event.id, action: "activate" })}>Activate</Button>}
        {event.status === "active" && <Button size="xs" color="orange" onClick={() => act.mutate({ id: event.id, action: "complete" })}>Complete</Button>}
        <Checkbox label="Fast lane" checked={event.fast_lane_enabled}
          onChange={(e) => controls.mutate({ event, fastLane: e.currentTarget.checked,
            overflow: draft ? draft.overflow : event.overflow_limit,
            rate: draft ? draft.rate : event.rate_limit_per_minute })} />
        <NumberInput label="Overflow cap" min={1}
          value={draft ? draft.overflow ?? "" : event.overflow_limit ?? ""}
          onChange={(value) => setControlDrafts({ ...controlDrafts, [event.id]: {
            overflow: value === "" ? null : Number(value),
            rate: controlDrafts[event.id]?.rate ?? event.rate_limit_per_minute,
          } })} />
        <NumberInput label="Rate per minute" min={1}
          value={draft ? draft.rate ?? "" : event.rate_limit_per_minute ?? ""}
          onChange={(value) => setControlDrafts({ ...controlDrafts, [event.id]: {
            overflow: controlDrafts[event.id]?.overflow ?? event.overflow_limit,
            rate: value === "" ? null : Number(value),
          } })} />
        <Button size="xs" variant="light" onClick={() => controls.mutate({ event,
          fastLane: event.fast_lane_enabled,
          overflow: draft ? draft.overflow : event.overflow_limit,
          rate: draft ? draft.rate : event.rate_limit_per_minute })}>Save controls</Button>
        <FileInput label="Approved visit CSV (visit_id column)" accept=".csv,text/csv"
          value={guestFiles[event.id] ?? null} onChange={(file) => {
            setGuestFiles({ ...guestFiles, [event.id]: file });
            setImportKeys({ ...importKeys, [event.id]: crypto.randomUUID() });
          }} />
        <Text size="xs" c="dimmed">Each row must reference an already host-approved visit with an active pass and a clean ID scan.</Text>
        <Button size="xs" variant="light" disabled={!guestFiles[event.id]}
          onClick={() => { const file = guestFiles[event.id]; if (file) importGuests.mutate({
            id: event.id, file, key: importKeys[event.id] ?? crypto.randomUUID() }); }}>Import approved visits</Button>
      </Stack></Table.Td>
    </Table.Tr>;
    })}</Table.Tbody></Table>)}
    {importGuests.data && <Alert color="blue">Latest import outcome: {JSON.stringify(importGuests.data.results)}</Alert>}
  </Stack></Container>;
}

export function EventOperationsPage() {
  const { session } = useAuth();
  const [eventId, setEventId] = useState<number | null>(null);
  const activeRole = session?.active_role?.trim().toLocaleLowerCase().replaceAll("_", " ") ?? "";
  const canViewEvents = ["admin", "super admin", "security", "security personnel"].includes(activeRole);
  const events = useQuery({ queryKey: ["vms", "events"], enabled: canViewEvents,
    queryFn: async () => (await http.get<EventRow[]>("/vms/admin/events")).data });
  const guests = useQuery({ queryKey: ["vms", "event-guests", eventId], enabled: eventId !== null,
    queryFn: async () => (await http.get<{ visit_id: number; status: string; reason: string; batch_id: number }[]>(
      `/vms/admin/events/${eventId}/guests`)).data });
  return <Container size="xl" py="md"><Stack>
    <Title order={2}>Event operations</Title>
    {!canViewEvents && <Alert color="yellow" title="Admin or Security role required">
      Switch to Admin or Security to view event operations.
    </Alert>}
    {canViewEvents && events.isError && <Alert color="red" title="Could not load event operations">{errorMessage(events.error)}</Alert>}
    {canViewEvents && (events.isPending ? <Text>Loading events…</Text> : <Table withTableBorder striped><Table.Thead><Table.Tr>
      <Table.Th>Event</Table.Th><Table.Th>State</Table.Th><Table.Th>Entry controls</Table.Th><Table.Th>Attendance</Table.Th><Table.Th>Guest results</Table.Th>
    </Table.Tr></Table.Thead><Table.Tbody>{(events.data ?? []).map((event) => <Table.Tr key={event.id}>
      <Table.Td>{event.name}</Table.Td><Table.Td>{event.status}</Table.Td>
      <Table.Td>{event.fast_lane_enabled ? "Fast lane enabled" : "Standard lane"}
        {event.overflow_limit ? ` · occupancy cap ${event.overflow_limit}` : ""}
        {event.rate_limit_per_minute ? ` · ${event.rate_limit_per_minute} entries/minute` : ""}</Table.Td>
      <Table.Td>{event.on_site_count} on site / {event.guest_count} assigned
        <Text size="xs" c="dimmed">{event.entries_last_minute} entries/minute · {event.total_entries} total</Text>
      </Table.Td>
      <Table.Td><Button size="xs" variant="light" onClick={() => setEventId(event.id)}>View list outcome</Button></Table.Td>
    </Table.Tr>)}</Table.Tbody></Table>)}
    {eventId !== null && <Stack><Title order={4}>Guest-list outcome for event {eventId}</Title>
      {guests.isError && <Alert color="red">Could not load this event guest list.</Alert>}
      {guests.isPending ? <Text>Loading list…</Text> : <Table withTableBorder><Table.Thead><Table.Tr>
        <Table.Th>Visit reference</Table.Th><Table.Th>Batch</Table.Th><Table.Th>Outcome</Table.Th><Table.Th>Reason</Table.Th>
      </Table.Tr></Table.Thead><Table.Tbody>{(guests.data ?? []).map((guest, index) => <Table.Tr key={`${guest.batch_id}-${guest.visit_id}-${index}`}>
        <Table.Td>{guest.visit_id}</Table.Td><Table.Td>{guest.batch_id}</Table.Td>
        <Table.Td>{guest.status}</Table.Td><Table.Td>{guest.reason || "—"}</Table.Td>
      </Table.Tr>)}</Table.Tbody></Table>}
    </Stack>}
  </Stack></Container>;
}
