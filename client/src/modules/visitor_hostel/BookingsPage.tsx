import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Badge, Button, Card, Container, Group, Modal, MultiSelect, NumberInput, Select,
  Stack, Text, TextInput, Textarea, Title } from "@mantine/core";
import { useAuth } from "../../auth/AuthProvider";
import { http, errorMessage } from "../../lib/http";

interface Booking {
  id: number; visitor_name: string; status: string;
  check_in_date: string; check_out_date: string; number_of_rooms: number;
  cancellation_requested_at: string | null;
  bill: { total_amount: string; is_settled_offline: boolean } | null;
}
interface Page { results: Booking[]; next: string | null; previous: string | null }
const root = "/visitor-hostel/bookings/";

export default function BookingsPage() {
  const { can, session } = useAuth();
  const qc = useQueryClient();
  const [cursor, setCursor] = useState("");
  const [creating, setCreating] = useState(false);
  const [action, setAction] = useState<{ booking: Booking; command: string } | null>(null);
  const [note, setNote] = useState("");
  const [roomIds, setRoomIds] = useState<string[]>([]);
  const query = useQuery({
    queryKey: ["hostel", session?.user.id, session?.active_role, cursor],
    queryFn: async () => (await http.get<Page>(root, { params: cursor ? { cursor } : {} })).data,
  });
  const rooms = useQuery({
    queryKey: ["hostel-rooms", action?.booking.id],
    enabled: action?.command === "allot",
    queryFn: async () => (await http.get<{ results: { id: number; room_number: string }[] }>(
      "/visitor-hostel/rooms/", { params: { booking: action?.booking.id, limit: 100 } })).data,
  });
  const mutation = useMutation({
    mutationFn: async ({ url, body }: { url: string; body: Record<string, unknown> }) =>
      (await http.post(url, body)).data,
    onSuccess: () => { setCreating(false); setAction(null); qc.invalidateQueries({ queryKey: ["hostel"] }); },
  });
  const caretaker = can("visitor_hostel.booking.manage");
  const approver = can("visitor_hostel.booking.approve");
  function open(booking: Booking, command: string) {
    mutation.reset(); setNote(""); setRoomIds([]); setAction({ booking, command });
  }
  function execute(event: FormEvent) {
    event.preventDefault();
    if (!action) return;
    const command = action.command;
    let body: Record<string, unknown> = {};
    let route = command;
    if (command === "forward" || command === "reject") {
      route = "route"; body = { action: command, reason: note };
    } else if (command === "approve" || command === "decline") {
      route = "decision"; body = { decision: command === "approve" ? "approve" : "reject", reason: note };
    } else if (command === "cancel") body = { reason: note };
    else if (command === "allot") body = { room_ids: roomIds.map(Number) };
    mutation.mutate({ url: `${root}${action.booking.id}/${route}/`, body });
  }
  function paginate(url: string | null) {
    setCursor(url ? new URL(url, window.location.origin).searchParams.get("cursor") ?? "" : "");
  }
  return <Container size="lg"><Stack>
    <Group justify="space-between"><Title order={1}>Hostel bookings</Title>
      <Button onClick={() => { mutation.reset(); setCreating(true); }}>New booking</Button></Group>
    <Text c="dimmed">Request a visitor stay and track its approval, room allotment and billing.</Text>
    {query.isPending && <Text>Loading bookings…</Text>}
    {query.error && <Alert color="red" title="Unable to load bookings">{errorMessage(query.error)}</Alert>}
    {query.data?.results.length === 0 && <Text>No bookings to display.</Text>}
    {query.data?.results.map((booking) => <Card key={booking.id} withBorder>
      <Group justify="space-between"><Title order={2} size="h4">#{booking.id} · {booking.visitor_name}</Title>
        <Badge>{booking.status.replaceAll("_", " ")}</Badge></Group>
      <Text>{booking.check_in_date} to {booking.check_out_date} · {booking.number_of_rooms} room(s)</Text>
      {booking.bill && <Text>Bill: ₹{booking.bill.total_amount} · {booking.bill.is_settled_offline ? "Settled" : "Unsettled"}</Text>}
      {booking.cancellation_requested_at && booking.status !== "cancelled" && <Text c="orange">Cancellation awaiting caretaker review</Text>}
      <Group mt="sm">
        {caretaker && booking.status === "pending" && <><Button onClick={() => open(booking, "forward")}>Forward</Button><Button color="red" onClick={() => open(booking, "reject")}>Reject</Button></>}
        {approver && booking.status === "forwarded" && <><Button onClick={() => open(booking, "approve")}>Approve</Button><Button color="red" onClick={() => open(booking, "decline")}>Reject</Button></>}
        {caretaker && booking.status === "approved" && <Button onClick={() => open(booking, "allot")}>Allot rooms</Button>}
        {caretaker && booking.status === "confirmed" && <Button onClick={() => open(booking, "check-in")}>Check in</Button>}
        {caretaker && booking.status === "checked_in" && <Button onClick={() => open(booking, "check-out")}>Check out and bill</Button>}
        {["pending", "forwarded", "approved", "confirmed"].includes(booking.status) && !booking.cancellation_requested_at && <Button variant="light" onClick={() => open(booking, "cancel")}>Request cancellation</Button>}
        {caretaker && booking.cancellation_requested_at && booking.status !== "cancelled" && <Button color="red" onClick={() => open(booking, "cancel/confirm")}>Confirm cancellation</Button>}
      </Group>
    </Card>)}
    <Group><Button variant="light" disabled={!query.data?.previous} onClick={() => paginate(query.data?.previous ?? null)}>Previous</Button>
      <Button variant="light" disabled={!query.data?.next} onClick={() => paginate(query.data?.next ?? null)}>Next</Button></Group>
    <Modal opened={creating} onClose={() => { if (!mutation.isPending) setCreating(false); }} title="New visitor booking">
      <BookingForm busy={mutation.isPending} onSubmit={(body) => mutation.mutate({ url: root, body })} />
      {mutation.error && <Alert color="red">{errorMessage(mutation.error)}</Alert>}
    </Modal>
    <Modal opened={action !== null} onClose={() => { if (!mutation.isPending) setAction(null); }} title={`Confirm ${action?.command.replaceAll("/", " ") ?? "action"}`}>
      <form onSubmit={execute}><Stack>
        <Text>Booking #{action?.booking.id} · {action?.booking.visitor_name}</Text>
        {["reject", "decline", "cancel"].includes(action?.command ?? "") && <Textarea label="Reason" required value={note} onChange={(e) => setNote(e.currentTarget.value)} />}
        {action?.command === "allot" && <Stack><MultiSelect label="Available rooms" required searchable
          data={rooms.data?.results.map((room) => ({ value: String(room.id), label: room.room_number })) ?? []}
          value={roomIds} onChange={setRoomIds} disabled={rooms.isPending} />
          {rooms.error && <Alert color="red">{errorMessage(rooms.error)}</Alert>}</Stack>}
        {mutation.error && <Alert color="red">{errorMessage(mutation.error)}</Alert>}
        <Button type="submit" loading={mutation.isPending}>Confirm</Button>
      </Stack></form>
    </Modal>
  </Stack></Container>;
}

function BookingForm({ busy, onSubmit }: { busy: boolean; onSubmit: (body: Record<string, unknown>) => void }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    onSubmit({ ...data, number_of_rooms: Number(data.number_of_rooms), number_of_occupants: Number(data.number_of_occupants) });
  }
  return <form onSubmit={submit}><Stack>
    <TextInput name="visitor_name" label="Visitor name" required maxLength={100} />
    <TextInput name="visitor_email" type="email" label="Visitor email" />
    <TextInput name="visitor_phone" label="Visitor phone" maxLength={20} />
    <Textarea name="purpose" label="Purpose of visit" required />
    <Select name="visitor_category" label="Category" data={["A", "B", "C", "D"]} defaultValue="A" allowDeselect={false} required />
    <TextInput name="check_in_date" type="date" label="Arrival date" required />
    <TextInput name="check_out_date" type="date" label="Departure date" required />
    <TextInput name="check_in_time" type="time" label="Arrival time" defaultValue="14:00" required />
    <TextInput name="check_out_time" type="time" label="Departure time" defaultValue="11:00" required />
    <Select name="room_type" label="Room type" data={[{ value: "suite", label: "Suite" }, { value: "non_suite", label: "Non-suite" }]} defaultValue="non_suite" allowDeselect={false} />
    <Select name="occupancy" label="Occupancy" data={["single", "double"]} defaultValue="single" allowDeselect={false} />
    <NumberInput name="number_of_rooms" label="Rooms" min={1} max={100} defaultValue={1} required allowDecimal={false} />
    <NumberInput name="number_of_occupants" label="Occupants" min={1} defaultValue={1} required allowDecimal={false} />
    <Select name="billing_responsibility" label="Billing responsibility" data={["Visitor", "Indenter", "Institute", "Project"]} defaultValue="Visitor" allowDeselect={false} />
    <Button type="submit" loading={busy}>Submit request</Button>
  </Stack></form>;
}
