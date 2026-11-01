import { useState } from "react";
import { Button, Container, Select, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAppointments, useDoctors, usePhcPost } from "../api";

export default function AppointmentsPage() {
  const appointments = useAppointments(); const doctors = useDoctors();
  const { can } = useAuth();
  const [doctor, setDoctor] = useState<string | null>(null);
  const [startsAt, setStartsAt] = useState(""); const [reason, setReason] = useState("");
  const book = usePhcPost("/phc/appointments");
  if (appointments.error) return <Container><ErrorState error={appointments.error} /></Container>;
  const submit = async () => {
    try { await book.mutateAsync({ doctor_id: Number(doctor), starts_at: new Date(startsAt).toISOString(), reason });
      notifications.show({ message: "Appointment requested", color: "green" }); }
    catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); }
  };
  return <Container size="lg"><PageHeader title="Appointments" subtitle="Book and manage Health Center visits" />
    <Stack maw={520} mb="lg"><Select label="Doctor" data={(doctors.data?.results ?? []).map((d) =>
      ({ value: String(d.id), label: `Doctor #${d.user_id}${d.specialty ? ` · ${d.specialty}` : ""}` }))}
      value={doctor} onChange={setDoctor} searchable />
      <TextInput type="datetime-local" label="Date and time" value={startsAt}
        onChange={(e) => setStartsAt(e.currentTarget.value)} />
      <TextInput label="Reason for visit" value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
      <Button disabled={!doctor || !startsAt} loading={book.isPending} onClick={submit}>Request appointment</Button>
    </Stack>
    {appointments.isPending ? <Text c="dimmed">Loading appointments…</Text> :
      (appointments.data?.results ?? []).length === 0 ? <Text c="dimmed">No appointments found.</Text> :
        <Table.ScrollContainer minWidth={650}><Table striped><Table.Thead><Table.Tr>
          <Table.Th>Date</Table.Th><Table.Th>Doctor</Table.Th><Table.Th>Status</Table.Th><Table.Th>Reason</Table.Th><Table.Th /></Table.Tr></Table.Thead>
          <Table.Tbody>{appointments.data?.results.map((a) => <Table.Tr key={a.id}>
            <Table.Td>{new Date(a.starts_at).toLocaleString()}</Table.Td><Table.Td>#{a.doctor}</Table.Td>
            <Table.Td>{a.status}</Table.Td><Table.Td>{a.reason || "—"}</Table.Td>
            <Table.Td><Stack gap={4}>
              {(a.status === "pending" || a.status === "confirmed") &&
                (can("phc.appointment.book") || can("phc.appointment.manage")) && <Button size="xs" variant="light"
                  onClick={async () => { try { await http.post(`/phc/appointments/${a.id}/transition`, { status: "cancelled" }); notifications.show({ message: "Appointment cancelled" }); await appointments.refetch(); } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } }}>Cancel</Button>}
              {can("phc.appointment.manage") && a.status === "pending" && <>
                <Button size="xs" onClick={async () => { try { await http.post(`/phc/appointments/${a.id}/transition`, { status: "confirmed" }); await appointments.refetch(); } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } }}>Confirm</Button>
                <Button size="xs" color="red" variant="light" onClick={async () => { try { await http.post(`/phc/appointments/${a.id}/transition`, { status: "rejected" }); await appointments.refetch(); } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } }}>Reject</Button>
              </>}
              {can("phc.appointment.manage") && a.status === "confirmed" && <>
                <Button size="xs" onClick={async () => { try { await http.post(`/phc/appointments/${a.id}/transition`, { status: "completed" }); await appointments.refetch(); } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } }}>Complete</Button>
                <Button size="xs" variant="light" onClick={async () => { try { await http.post(`/phc/appointments/${a.id}/transition`, { status: "no_show" }); await appointments.refetch(); } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } }}>No-show</Button>
              </>}
            </Stack></Table.Td>
          </Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
  </Container>;
}
