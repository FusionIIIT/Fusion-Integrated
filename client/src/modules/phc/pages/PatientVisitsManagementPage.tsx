import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaFilePrescription, FaPlus, FaSearch } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreatePatientVisit,
  useCreatePrescription,
  useDoctors,
  useStaffPatientVisits,
} from "../api/hooks";
import type { PatientVisit } from "../api/types";

export default function PatientVisitsManagementPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const { data: visits, isPending, error } = useStaffPatientVisits(searchQuery);
  const { data: doctors } = useDoctors();

  const [visitModalOpen, setVisitModalOpen] = useState(false);
  const [prescriptionModalOpen, setPrescriptionModalOpen] = useState(false);
  const [selectedVisit, setSelectedVisit] = useState<PatientVisit | null>(null);

  // Visit form
  const [patientUserId, setPatientUserId] = useState<number | string>(1001);
  const [doctorId, setDoctorId] = useState<string | null>(null);
  const [symptoms, setSymptoms] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [notes, setNotes] = useState("");

  // Prescription form
  const [prescriptionNumber, setPrescriptionNumber] = useState("");
  const [medicinesPrescribed, setMedicinesPrescribed] = useState("");
  const [scannedDocUrl, setScannedDocUrl] = useState("");
  const [prescriptionNotes, setPrescriptionNotes] = useState("");

  const createVisitMutation = useCreatePatientVisit();
  const createPrescriptionMutation = useCreatePrescription();

  const handleCreateVisit = async () => {
    if (!patientUserId || !symptoms || !diagnosis) {
      notifications.show({ title: "Incomplete Form", message: "Patient ID, symptoms and diagnosis are required.", color: "orange" });
      return;
    }

    try {
      await createVisitMutation.mutateAsync({
        patient_user_id: Number(patientUserId),
        doctor_id: doctorId ? Number(doctorId) : null,
        symptoms,
        diagnosis,
        notes,
      });
      notifications.show({
        title: "Visit Created",
        message: "Patient consultation record created and audited (AFR-PHC-007, BR-PHC-09).",
        color: "teal",
      });
      setVisitModalOpen(false);
      setSymptoms("");
      setDiagnosis("");
      setNotes("");
    } catch {
      notifications.show({ title: "Error", message: "Failed to record consultation.", color: "red" });
    }
  };

  const handleCreatePrescription = async () => {
    if (!selectedVisit || !prescriptionNumber || !medicinesPrescribed) {
      notifications.show({ title: "Incomplete Form", message: "Prescription number and medicines are required.", color: "orange" });
      return;
    }

    try {
      await createPrescriptionMutation.mutateAsync({
        visit_id: selectedVisit.id,
        prescription_number: prescriptionNumber,
        medicines_prescribed: medicinesPrescribed,
        scanned_document_url: scannedDocUrl,
        notes: prescriptionNotes,
      });
      notifications.show({
        title: "Prescription Digitized",
        message: `Prescription ${prescriptionNumber} linked to Visit #${selectedVisit.id} (AFR-PHC-008).`,
        color: "teal",
      });
      setPrescriptionModalOpen(false);
      setPrescriptionNumber("");
      setMedicinesPrescribed("");
      setScannedDocUrl("");
      setPrescriptionNotes("");
    } catch {
      notifications.show({ title: "Error", message: "Failed to digitize prescription.", color: "red" });
    }
  };

  if (error) return <ErrorState error={error} />;

  const doctorOptions = (doctors || []).map((d) => ({
    value: String(d.id),
    label: `Dr. ${d.name} (${d.specialization})`,
  }));

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Patient Consultations & Prescriptions"
        subtitle="Search patient profiles, record clinical visits, and digitize prescriptions (AFR-PHC-006, 007, 008)"
        action={
          <Button leftSection={<FaPlus />} color="blue" onClick={() => setVisitModalOpen(true)}>
            Record Patient Visit
          </Button>
        }
      />

      <Card withBorder p="md" mb="md">
        <TextInput
          placeholder="Search visits by symptoms, diagnosis, doctor, or prescription number (AFR-PHC-006)..."
          leftSection={<FaSearch />}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.currentTarget.value)}
        />
      </Card>

      {isPending ? (
        <Text c="dimmed">Loading patient records...</Text>
      ) : !visits || visits.length === 0 ? (
        <Card withBorder p="xl">
          <Text c="dimmed" ta="center">
            No patient records match the search query.
          </Text>
        </Card>
      ) : (
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Visit #</Table.Th>
              <Table.Th>Patient User ID</Table.Th>
              <Table.Th>Date</Table.Th>
              <Table.Th>Attending Doctor</Table.Th>
              <Table.Th>Symptoms</Table.Th>
              <Table.Th>Diagnosis</Table.Th>
              <Table.Th>Prescriptions</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {visits.map((v) => (
              <Table.Tr key={v.id}>
                <Table.Td fw={600}>#{v.id}</Table.Td>
                <Table.Td>
                  <Badge color="gray" variant="light">
                    User {v.patient_user_id}
                  </Badge>
                </Table.Td>
                <Table.Td>{v.visit_date}</Table.Td>
                <Table.Td>Dr. {v.doctor_name}</Table.Td>
                <Table.Td>{v.symptoms}</Table.Td>
                <Table.Td fw={500} c="blue.8">
                  {v.diagnosis}
                </Table.Td>
                <Table.Td>
                  {v.prescriptions?.length > 0 ? (
                    <Badge color="teal" variant="filled">
                      {v.prescriptions.length} Rx Digitized
                    </Badge>
                  ) : (
                    <Badge color="gray" variant="outline">
                      None
                    </Badge>
                  )}
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    leftSection={<FaFilePrescription />}
                    variant="light"
                    color="teal"
                    onClick={() => {
                      setSelectedVisit(v);
                      setPrescriptionNumber(`RX-${v.id}-${Date.now().toString().slice(-4)}`);
                      setPrescriptionModalOpen(true);
                    }}
                  >
                    Add Rx
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* Record Visit Modal */}
      <Modal opened={visitModalOpen} onClose={() => setVisitModalOpen(false)} title="Record New Patient Consultation Visit" size="lg">
        <Stack>
          <NumberInput
            label="Patient User ID"
            placeholder="IAM User ID (e.g. 1001)"
            value={patientUserId}
            onChange={setPatientUserId}
            required
          />
          <Select
            label="Attending Doctor"
            placeholder="Select doctor"
            data={doctorOptions}
            value={doctorId}
            onChange={setDoctorId}
            clearable
          />
          <Textarea
            label="Symptoms / Complaint"
            placeholder="Describe clinical symptoms reported by patient"
            value={symptoms}
            onChange={(e) => setSymptoms(e.currentTarget.value)}
            required
            rows={2}
          />
          <Textarea
            label="Diagnosis"
            placeholder="Clinical diagnosis"
            value={diagnosis}
            onChange={(e) => setDiagnosis(e.currentTarget.value)}
            required
            rows={2}
          />
          <Textarea
            label="Clinical Advice / Notes (optional)"
            placeholder="Dietary or follow-up instructions"
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
            rows={2}
          />
          <Button fullWidth onClick={handleCreateVisit} loading={createVisitMutation.isPending}>
            Save Consultation Record
          </Button>
        </Stack>
      </Modal>

      {/* Digitize Prescription Modal */}
      <Modal
        opened={prescriptionModalOpen}
        onClose={() => setPrescriptionModalOpen(false)}
        title={`Digitize Prescription for Visit #${selectedVisit?.id} (Patient ${selectedVisit?.patient_user_id})`}
        size="lg"
      >
        <Stack>
          <TextInput
            label="Prescription Identifier"
            value={prescriptionNumber}
            onChange={(e) => setPrescriptionNumber(e.currentTarget.value)}
            required
          />
          <Textarea
            label="Medicines Prescribed & Dosages"
            placeholder="e.g. Paracetamol 500mg 1-0-1 (3 days), Cetirizine 10mg 0-0-1 (5 days)"
            value={medicinesPrescribed}
            onChange={(e) => setMedicinesPrescribed(e.currentTarget.value)}
            required
            rows={3}
          />
          <TextInput
            label="Scanned Physical Prescription Document URL (optional)"
            placeholder="https://drive.google.com/... or /docs/prescription.pdf"
            value={scannedDocUrl}
            onChange={(e) => setScannedDocUrl(e.currentTarget.value)}
          />
          <Textarea
            label="Pharmacy Notes"
            placeholder="Additional instructions for patient"
            value={prescriptionNotes}
            onChange={(e) => setPrescriptionNotes(e.currentTarget.value)}
            rows={2}
          />
          <Button fullWidth color="teal" onClick={handleCreatePrescription} loading={createPrescriptionMutation.isPending}>
            Save & Link Digitized Prescription
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
