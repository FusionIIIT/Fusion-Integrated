import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Stack, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaSearch, FaUserInjured } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreatePrescription, useCreateVisit, usePatientSearch,
} from "../api/hooks";
import type { Patient, Visit } from "../api/types";

export default function PatientRecordsPage() {
  const { can } = useAuth();
  const canManage = can("phc.records.manage");
  const [query, setQuery] = useState("");
  const [visiting, setVisiting] = useState<Patient | null>(null);
  const [activeVisit, setActiveVisit] = useState<{
    visit: Visit; patient: Patient;
  } | null>(null);
  const search = usePatientSearch(query);

  if (search.error) {
    return <Container size="xl"><ErrorState error={search.error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Patient Records"
        subtitle="Find a patient, record a consultation, then add a prescription"
      />

      {!canManage && (
        <Text c="red" size="sm" mb="md">
          You do not have permission to record patient visits.
        </Text>
      )}

      <Card padding="lg" mb="md">
        <TextInput
          label="Search patients" placeholder="At least two characters of the name"
          leftSection={<FaSearch size={12} />} value={query}
          onChange={(e) => setQuery(e.currentTarget.value)} w={360}
        />
      </Card>

      <Card padding="lg" mb="md">
        <DataTable<Patient>
          rows={search.data?.results ?? []}
          loading={query.trim().length >= 2 && search.isPending}
          rowKey={(r) => r.user_id}
          minWidth={680}
          columns={[
            { key: "display_name", header: "Patient",
              render: (r) => <Text fw={600}>{r.display_name}</Text> },
            { key: "kind", header: "Kind",
              render: (r) => (
                <Badge variant="light" size="sm">{r.kind || "—"}</Badge>
              ) },
            { key: "user_id", header: "User id", align: "right" },
            {
              key: "actions", header: "", align: "right",
              render: (r) => canManage && (
                <Button size="xs" variant="light" onClick={() => setVisiting(r)}>
                  Record visit
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaUserInjured,
            title: query.trim().length < 2
              ? "Search for a patient" : "No patients match",
            description: query.trim().length < 2
              ? "Enter at least two characters of the patient's name."
              : "Try a different spelling or check the name in the IAM directory.",
          }}
        />
      </Card>

      <VisitModal patient={visiting} onClose={() => setVisiting(null)}
        onVisited={(visit, patient) => setActiveVisit({ visit, patient })} />

      {activeVisit ? (
        <PrescriptionForm
          visit={activeVisit.visit} patient={activeVisit.patient}
          onDone={() => setActiveVisit(null)}
        />
      ) : (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <FaUserInjured size={24} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No visit in progress</Text>
            <Text size="sm" c="dimmed">
              Record a visit for a patient before adding a prescription.
            </Text>
          </Stack>
        </Card>
      )}
    </Container>
  );
}

function VisitModal({ patient, onClose, onVisited }: {
  patient: Patient | null;
  onClose: () => void;
  onVisited: (visit: Visit, patient: Patient) => void;
}) {
  const create = useCreateVisit();
  const [notes, setNotes] = useState("");

  return (
    <FormModal
      opened={patient != null} onClose={onClose}
      title={`Record a visit for ${patient?.display_name ?? ""}`}
      subtitle="The visit is timestamped and attributed to you"
      onSubmit={() => patient && create.mutate(
        { patient_id: patient.user_id, notes },
        {
          onSuccess: (visit) => {
            onVisited(visit, patient);
            setNotes("");
            onClose();
          },
        },
      )}
      submitLabel="Start visit" submitting={create.isPending}
      error={create.error}
    >
      <Textarea
        label="Consultation notes" autosize minRows={4} value={notes}
        onChange={(e) => setNotes(e.currentTarget.value)}
        placeholder="Symptoms, observations, advice"
        maxLength={4000}
      />
    </FormModal>
  );
}

function PrescriptionForm({ visit, patient, onDone }: {
  visit: Visit;
  patient: Patient;
  onDone: () => void;
}) {
  const create = useCreatePrescription();
  const [medicine, setMedicine] = useState("");
  const [dosage, setDosage] = useState("");

  return (
    <Card padding="lg">
      <Group justify="space-between" mb="sm">
        <div>
          <Text fw={600}>Visit #{visit.id} · {patient.display_name}</Text>
          <Text size="xs" c="dimmed">
            {new Date(visit.visit_date).toLocaleString()}
          </Text>
        </div>
        <Button size="xs" variant="subtle" onClick={onDone}>Done</Button>
      </Group>
      {create.error && <ErrorState error={create.error} />}
      <Stack gap="md">
        <Group grow align="flex-end">
          <TextInput
            label="Medicine" required value={medicine}
            onChange={(e) => setMedicine(e.currentTarget.value)} maxLength={200}
          />
          <TextInput
            label="Dosage" value={dosage}
            onChange={(e) => setDosage(e.currentTarget.value)} maxLength={120}
          />
        </Group>
        <Group justify="flex-end">
          <Button
            onClick={() => create.mutate(
              {
                visit_id: visit.id, patient_id: patient.user_id,
                medicine: medicine.trim(), dosage,
              },
              {
                onSuccess: () => {
                  notifications.show({
                    color: "green", title: "Prescription added",
                    message: `${medicine.trim()} is on the patient's record.`,
                  });
                  setMedicine("");
                  setDosage("");
                },
              },
            )}
            loading={create.isPending} disabled={!medicine.trim()}
          >
            Add prescription
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}
