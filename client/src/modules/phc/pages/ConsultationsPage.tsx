import { useCallback, useEffect, useState } from "react";
import { Button, Card, Container, NumberInput, Stack, Table, Text, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAppointments } from "../api";

interface Consultation { id: number; appointment_id: number; patient_user_id: number; symptoms: string;
  diagnosis: string; treatment: string; created_at: string;
  prescriptions: { id: number; items: { medicine_name: string; dosage: string;
    frequency: string; duration: string; instructions: string }[] }[] }
interface MedicineItem { medicine_name: string; dosage: string; frequency: string; duration: string }

export default function ConsultationsPage() {
  const appts = useAppointments();
  const [appointmentId, setAppointmentId] = useState<number | "">("");
  const [symptoms, setSymptoms] = useState(""); const [diagnosis, setDiagnosis] = useState("");
  const [observations, setObservations] = useState(""); const [treatment, setTreatment] = useState("");
  const [medicines, setMedicines] = useState<MedicineItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [records, setRecords] = useState<Consultation[]>([]); const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => { try { const { data } = await http.get<{ results: Consultation[] }>("/phc/consultations"); setRecords(data.results); }
    catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } finally { setLoading(false); } }, []);
  useEffect(() => { void reload(); }, [reload]);
  if (appts.error) return <Container><ErrorState error={appts.error} /></Container>;
  const save = async () => {
    setSaving(true);
    try {
      await http.post(`/phc/appointments/${appointmentId}/consultation`, {
        symptoms, diagnosis, observations, treatment,
        medicines,
      });
      notifications.show({ message: "Consultation recorded", color: "green" });
      setSymptoms(""); setDiagnosis(""); setObservations(""); setTreatment("");
      setMedicines([]);
      await reload(); await appts.refetch();
    } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); }
    finally { setSaving(false); }
  };
  const eligible = (appts.data?.results ?? []).filter((a) => a.status === "confirmed");
  return <Container size="lg"><PageHeader title="Consultations" subtitle="Record and review authorized clinical notes" />
    <Card withBorder mb="lg"><Stack><Text fw={600}>Record a consultation</Text>
      <NumberInput label="Appointment ID" value={appointmentId} onChange={(v) => setAppointmentId(typeof v === "number" ? v : "")}
        description={eligible.length ? `Confirmed appointments: ${eligible.map((a) => a.id).join(", ")}` : "No confirmed appointments available"} min={1} />
      <Textarea label="Symptoms" value={symptoms} onChange={(e) => setSymptoms(e.currentTarget.value)} required />
      <Textarea label="Clinical observations" value={observations} onChange={(e) => setObservations(e.currentTarget.value)} />
      <Textarea label="Diagnosis" value={diagnosis} onChange={(e) => setDiagnosis(e.currentTarget.value)} required />
      <Textarea label="Treatment recommendations" value={treatment} onChange={(e) => setTreatment(e.currentTarget.value)} />
      <Text fw={500}>Prescription (optional)</Text>
      {medicines.map((item, index) => <Card withBorder key={index}><Stack>
        <TextInput label="Medicine" value={item.medicine_name} onChange={(e) => setMedicines((old) => old.map((x, i) => i === index ? { ...x, medicine_name: e.currentTarget.value } : x))} />
        <TextInput label="Dosage" value={item.dosage} onChange={(e) => setMedicines((old) => old.map((x, i) => i === index ? { ...x, dosage: e.currentTarget.value } : x))} />
        <TextInput label="Frequency" value={item.frequency} onChange={(e) => setMedicines((old) => old.map((x, i) => i === index ? { ...x, frequency: e.currentTarget.value } : x))} />
        <TextInput label="Duration" value={item.duration} onChange={(e) => setMedicines((old) => old.map((x, i) => i === index ? { ...x, duration: e.currentTarget.value } : x))} />
        <Button color="red" variant="light" onClick={() => setMedicines((old) => old.filter((_, i) => i !== index))}>Remove medicine</Button>
      </Stack></Card>)}
      <Button variant="light" onClick={() => setMedicines((old) => [...old, { medicine_name: "", dosage: "", frequency: "", duration: "" }])}>Add medicine</Button>
      <Button disabled={!appointmentId || !symptoms || !diagnosis || medicines.some((m) => !m.medicine_name || !m.dosage || !m.frequency || !m.duration)}
        loading={saving} onClick={save}>Finalize consultation</Button>
    </Stack></Card>
    {loading ? <Text c="dimmed">Loading consultation history…</Text> : records.length === 0 ?
      <Text c="dimmed">No consultation history available.</Text> : <Stack>{records.map((r) => <Card withBorder key={r.id}>
        <Text fw={600}>Appointment #{r.appointment_id} · Patient #{r.patient_user_id}</Text>
        <Text size="sm" c="dimmed">{new Date(r.created_at).toLocaleString()}</Text>
        <Text mt="sm"><b>Symptoms:</b> {r.symptoms}</Text><Text><b>Diagnosis:</b> {r.diagnosis}</Text>
        {r.treatment && <Text><b>Treatment:</b> {r.treatment}</Text>}
        {r.prescriptions.flatMap((p) => p.items).length > 0 && <Table mt="sm"><Table.Thead><Table.Tr>
          <Table.Th>Medicine</Table.Th><Table.Th>Dosage</Table.Th><Table.Th>Frequency</Table.Th><Table.Th>Duration</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{r.prescriptions.flatMap((p) => p.items).map((item, i) => <Table.Tr key={`${r.id}-${i}`}>
            <Table.Td>{item.medicine_name}</Table.Td><Table.Td>{item.dosage}</Table.Td><Table.Td>{item.frequency}</Table.Td><Table.Td>{item.duration}</Table.Td>
          </Table.Tr>)}</Table.Tbody></Table>}
      </Card>)}</Stack>}
  </Container>;
}
