import { useCallback, useEffect, useState } from "react";
import { Button, Container, NumberInput, Select, Stack, Switch, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDoctors, usePhcPost } from "../api";

interface Schedule { id: number; doctor: number; weekday: number; starts_at: string; ends_at: string;
  slot_minutes: number; effective_from: string; effective_until: string | null }
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function SchedulesPage() {
  const doctors = useDoctors(); const add = usePhcPost<Schedule>("/phc/schedules");
  const { can } = useAuth();
  const [doctor, setDoctor] = useState<string | null>(null); const [weekday, setWeekday] = useState("0");
  const [starts, setStarts] = useState("09:00"); const [ends, setEnds] = useState("17:00");
  const [slot, setSlot] = useState<number | "">(15); const [from, setFrom] = useState("");
  const [rows, setRows] = useState<Schedule[]>([]); const [error, setError] = useState<unknown>(null);
  const [newDoctorId, setNewDoctorId] = useState<number | "">(""); const [specialty, setSpecialty] = useState("");
  const load = useCallback(async () => { try { const { data } = await http.get<Schedule[]>("/phc/schedules"); setRows(data); setError(null); }
    catch (e) { setError(e); } }, []);
  useEffect(() => { void load(); }, [load]);
  if (doctors.error) return <Container><ErrorState error={doctors.error} /></Container>;
  const save = async () => { try { await add.mutateAsync({ doctor: Number(doctor), weekday: Number(weekday),
      starts_at: starts, ends_at: ends, slot_minutes: slot, effective_from: from, effective_until: null });
    notifications.show({ message: "Doctor schedule added", color: "green" }); await load(); }
    catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } };
  const createDoctor = async () => { try { await http.post("/phc/doctors/manage", { user_id: newDoctorId, specialty });
      notifications.show({ message: "Doctor added", color: "green" }); setNewDoctorId(""); setSpecialty(""); await doctors.refetch(); }
    catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } };
  return <Container size="lg"><PageHeader title="Doctor Schedules" subtitle="Manage recurring appointment availability" />
    {error !== null && <ErrorState error={error} />}
    <Stack maw={520} mb="lg"><Text fw={600}>Doctor directory</Text>
      {can("phc.doctor.register") && <>
        <NumberInput label="Institute user ID" min={1} value={newDoctorId}
          onChange={(v) => setNewDoctorId(typeof v === "number" ? v : "")} />
        <TextInput label="Specialty" value={specialty} onChange={(e) => setSpecialty(e.currentTarget.value)} />
        <Button disabled={!newDoctorId} onClick={createDoctor}>Add doctor</Button>
      </>}
      {(doctors.data?.results ?? []).map((d) => <Switch key={d.id} label={`Doctor #${d.user_id}${d.specialty ? ` · ${d.specialty}` : ""}`}
        checked={d.is_available} disabled={!can("phc.appointment.manage")}
        onChange={async (e) => { const isAvailable = e.currentTarget.checked; try { await http.patch(`/phc/doctors/${d.id}`, { is_available: isAvailable }); await doctors.refetch(); }
          catch (err) { notifications.show({ message: errorMessage(err), color: "red" }); } }} />)}
    </Stack>
    <Stack maw={520} mb="lg"><Select label="Doctor" data={(doctors.data?.results ?? []).map((d) =>
      ({ value: String(d.id), label: `Doctor #${d.user_id}${d.specialty ? ` · ${d.specialty}` : ""}` }))}
      value={doctor} onChange={setDoctor} searchable />
      <Select label="Weekday" data={DAYS.map((d, i) => ({ value: String(i), label: d }))}
        value={weekday} onChange={(v) => setWeekday(v ?? "0")} />
      <TextInput label="Starts at" type="time" value={starts} onChange={(e) => setStarts(e.currentTarget.value)} />
      <TextInput label="Ends at" type="time" value={ends} onChange={(e) => setEnds(e.currentTarget.value)} />
      <NumberInput label="Slot length (minutes)" min={5} value={slot} onChange={(v) => setSlot(typeof v === "number" ? v : "")} />
      <TextInput label="Effective from" type="date" value={from} onChange={(e) => setFrom(e.currentTarget.value)} />
      <Button disabled={!doctor || !from || !slot} loading={add.isPending} onClick={save}>Add schedule</Button>
    </Stack>
    {rows.length === 0 ? <Text c="dimmed">No schedules added.</Text> : <Table.ScrollContainer minWidth={640}><Table striped>
      <Table.Thead><Table.Tr><Table.Th>Doctor</Table.Th><Table.Th>Day</Table.Th><Table.Th>Hours</Table.Th><Table.Th>Slot</Table.Th><Table.Th>From</Table.Th></Table.Tr></Table.Thead>
      <Table.Tbody>{rows.map((r) => <Table.Tr key={r.id}><Table.Td>#{r.doctor}</Table.Td><Table.Td>{DAYS[r.weekday]}</Table.Td>
        <Table.Td>{r.starts_at}–{r.ends_at}</Table.Td><Table.Td>{r.slot_minutes} min</Table.Td><Table.Td>{r.effective_from}</Table.Td></Table.Tr>)}</Table.Tbody>
    </Table></Table.ScrollContainer>}
  </Container>;
}
