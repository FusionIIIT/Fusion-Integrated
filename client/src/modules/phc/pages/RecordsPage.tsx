import { useState } from "react";
import {
  Button, Card, Checkbox, Container, Group, NumberInput, Select, Stack, Text, TextInput,
  Textarea,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDownloadRecords, usePatientSearch, useRecordVisit, useVisits,
} from "../api/hooks";
import type { Prescription } from "../api/types";
import { ListStates } from "../components/ListStates";

const BLANK: Prescription = { medicine: "", dosage: "", duration_days: null, instructions: "" };

function RecordVisitModal({ onClose }: { onClose: () => void }) {
  const record = useRecordVisit();
  const [query, setQuery] = useState("");
  const patients = usePatientSearch(query);
  const [patient, setPatient] = useState<string | null>(null);
  const [visitDate, setVisitDate] = useState(new Date().toISOString().slice(0, 10));
  const [complaint, setComplaint] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [lines, setLines] = useState<Prescription[]>([BLANK]);
  const setLine = (i: number, patch: Partial<Prescription>) =>
    setLines(lines.map((l, j) => (j === i ? { ...l, ...patch } : l)));

  return (
    <FormModal
      opened onClose={onClose} title="Record a patient visit" submitLabel="Save visit"
      submitting={record.isPending} error={record.error}
      disabled={!patient || !complaint.trim() || lines.some((l) => !l.medicine || !l.dosage)}
      disabledReason="Choose the patient, enter the complaint and every prescribed medicine."
      onSubmit={() => record.mutate({
        patient_user_id: Number(patient), visit_date: visitDate, complaint, diagnosis,
        prescriptions: lines,
      }, { onSuccess: onClose })}
    >
      <Stack>
        <TextInput label="Search patient by name" value={query}
          onChange={(e) => setQuery(e.currentTarget.value)} />
        <Select label="Patient" required value={patient} onChange={setPatient}
          data={(patients.data ?? []).map((p) => ({
            value: String(p.user_id), label: `${p.display_name} (${p.kind})`,
          }))}
          nothingFoundMessage={query.length < 2 ? "Type two letters" : "No patient found"} />
        <TextInput label="Visit date" type="date" required value={visitDate}
          onChange={(e) => setVisitDate(e.currentTarget.value)} />
        <Textarea label="Complaint" required value={complaint}
          onChange={(e) => setComplaint(e.currentTarget.value)} />
        <Textarea label="Diagnosis" value={diagnosis}
          onChange={(e) => setDiagnosis(e.currentTarget.value)} />
        {lines.map((line, i) => (
          <Group key={i} grow align="flex-end">
            <TextInput label={`Medicine ${i + 1}`} required value={line.medicine}
              onChange={(e) => setLine(i, { medicine: e.currentTarget.value })} />
            <TextInput label="Dosage" required value={line.dosage}
              onChange={(e) => setLine(i, { dosage: e.currentTarget.value })} />
            <NumberInput label="Days" min={1} value={line.duration_days ?? ""}
              onChange={(v) => setLine(i, { duration_days: v === "" ? null : Number(v) })} />
            <TextInput label="Instructions" value={line.instructions}
              onChange={(e) => setLine(i, { instructions: e.currentTarget.value })} />
          </Group>
        ))}
        <Button variant="light" onClick={() => setLines([...lines, BLANK])}>Add medicine</Button>
      </Stack>
    </FormModal>
  );
}

export default function RecordsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useVisits();
  const download = useDownloadRecords();
  const [selected, setSelected] = useState<number[]>([]);
  const [recording, setRecording] = useState(false);
  const rows = data?.results ?? [];
  const toggle = (id: number) =>
    setSelected(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);

  return (
    <Container size="lg">
      <PageHeader
        title="Medical records"
        subtitle={can("phc.record.create")
          ? "Visits and prescriptions recorded at the PHC"
          : "Your visits and prescriptions, read-only"}
        action={(
          <Group>
            <Button variant="default" disabled={selected.length === 0}
              loading={download.isPending} onClick={() => download.mutate(selected)}>
              Download PDF
            </Button>
            {can("phc.record.create") && (
              <Button onClick={() => setRecording(true)}>Record visit</Button>
            )}
          </Group>
        )}
      />
      {download.error != null && <Text c="red" mb="sm">{errorMessage(download.error)}</Text>}
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No medical records yet" />
      <Stack>
        {rows.map((v) => (
          <Card key={v.id} withBorder padding="lg">
            <Group justify="space-between">
              <Checkbox label={`Visit on ${v.visit_date}`} checked={selected.includes(v.id)}
                onChange={() => toggle(v.id)} />
              {can("phc.record.create") && (
                <Text size="sm" c="dimmed">Patient #{v.patient_user_id}</Text>
              )}
            </Group>
            <Text mt="xs"><b>Complaint:</b> {v.complaint}</Text>
            <Text><b>Diagnosis:</b> {v.diagnosis || "Not recorded"}</Text>
            {v.prescriptions.map((p) => (
              <Text key={p.id} size="sm">
                {p.medicine} — {p.dosage}{p.duration_days ? `, ${p.duration_days} days` : ""}
                {p.instructions ? ` (${p.instructions})` : ""}
              </Text>
            ))}
          </Card>
        ))}
      </Stack>
      {recording && <RecordVisitModal onClose={() => setRecording(false)} />}
    </Container>
  );
}
