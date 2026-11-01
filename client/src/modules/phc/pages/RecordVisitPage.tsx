import { useState } from "react";
import {
  Box,
  Button,
  Group,
  NumberInput,
  Stack,
  Text,
  Title,
  TextInput,
  Card,
  Divider,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePatientVisits, useRecordVisit } from "../api/hooks";
import { errorMessage } from "../../../lib/http";

export default function RecordVisitPage() {
  const [patientId, setPatientId] = useState<number | null>(null);
  const [visitDate, setVisitDate] = useState("");
  const [complaint, setComplaint] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [prescriptions, setPrescriptions] = useState<
    { medicine: string; dosage: number; duration_days: number }[]
  >([]);

  const addMedicine = () => {
    setPrescriptions([...prescriptions, { medicine: "", dosage: 0, duration_days: 0 }]);
  };

  const updatePrescription = (index: number, field: keyof typeof prescriptions[0], value: string | number) => {
    const newPrescriptions = [...prescriptions];
    if (field === "medicine") {
      newPrescriptions[index].medicine = value as string;
    } else {
      newPrescriptions[index][field] = value as number;
    }
    setPrescriptions(newPrescriptions);
  };

  const removeMedicine = (index: number) => {
    setPrescriptions(prescriptions.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!patientId || !visitDate || !complaint || !diagnosis) {
      notifications.show({ color: "red", title: "Missing fields", message: "Please fill in all required fields." });
      return;
    }
    if (prescriptions.some(p => !p.medicine)) {
      notifications.show({ color: "red", title: "Invalid prescription", message: "Medicine name cannot be empty." });
      return;
    }

    const body = {
      patient_id: patientId,
      visit_date: visitDate,
      complaint,
      diagnosis,
      prescriptions: prescriptions.map(p => ({
        medicine: p.medicine,
        dosage: p.dosage,
        duration_days: p.duration_days,
      })),
    };

    try {
      await useRecordVisit.mutateAsync(body);
      notifications.show({ color: "green", title: "Success", message: "Visit recorded successfully." });
      // Optional: reset form or fetch updated list
    } catch (e) {
      notifications.show({ color: "red", title: "Error", message: errorMessage(e) });
    }
  };

  const { data: previousVisits } = usePatientVisits(patientId);

  return (
    <Box p="md">
      <PageHeader title="Record Visit" subtitle="PHC Staff Interface" />

      <Stack gap="lg">
        <Card shadow="sm" p="md">
          <Group justify="space-between" mb="md">
            <Title order={3}>New Visit</Title>
            <Button onClick={addMedicine} variant="default">+ Add medicine</Button>
          </Group>

          <Grid cols={2} gap="md">
            <TextInput
              label="Patient ID"
              placeholder="Enter patient ID"
              value={patientId?.toString() || ""}
              onChange={(e) => setPatientId(Number(e.target.value))}
            />
            <TextInput
              type="date"
              label="Visit Date"
              value={visitDate}
              onChange={(e) => setVisitDate(e.target.value)}
            />
            <Textarea
              label="Complaint"
              placeholder="Describe the patient's complaint..."
              value={complaint}
              onChange={(e) => setComplaint(e.target.value)}
              rows={3}
            />
            <Textarea
              label="Diagnosis"
              placeholder="Enter diagnosis..."
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              rows={3}
            />
          </Grid>

          <Divider my="md" />

          <Title order={4}>Prescriptions</Title>
          {prescriptions.map((p, index) => (
            <Group key={index} justify="space-between" mb="sm">
              <TextInput
                placeholder="Medicine name"
                value={p.medicine}
                onChange={(e) => updatePrescription(index, "medicine", e.target.value)}
                style={{ flex: 2 }}
              />
              <NumberInput
                label="Dosage"
                value={p.dosage}
                onChange={(val) => updatePrescription(index, "dosage", Number(val))}
                style={{ width: 100 }}
              />
              <NumberInput
                label="Duration (days)"
                value={p.duration_days}
                onChange={(val) => updatePrescription(index, "duration_days", Number(val))}
                style={{ width: 120 }}
              />
              <Button variant="light" color="red" onClick={() => removeMedicine(index)}>Remove</Button>
            </Group>
          ))}

          <Button fullWidth onClick={handleSubmit}>Save Visit</Button>
        </Card>

        {patientId && previousVisits?.results.length > 0 && (
          <Card shadow="sm" p="md">
            <Title order={3}>Previous Visits for Patient {patientId}</Title>
            <Stack gap="sm">
              {previousVisits.results.map((visit) => (
                <Card key={visit.id} variant="outline" p="sm">
                  <Group justify="space-between">
                    <Text fw={500}>Date: {new Date(visit.visit_date).toLocaleDateString()}</Text>
                    <Text c="dimmed">ID: {visit.id}</Text>
                  </Group>
                  <Text size="sm" c="dimmed">{visit.complaint}</Text>
                  <Text size="sm">{visit.diagnosis}</Text>
                </Card>
              ))}
            </Stack>
          </Card>
        )}
      </Stack>
    </Box>
  );
}
