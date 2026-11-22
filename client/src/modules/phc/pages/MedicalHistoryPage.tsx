import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Modal,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaDownload, FaFileMedical, FaPrescriptionBottleAlt } from "react-icons/fa";

import { http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyMedicalHistory, useMyPrescriptions } from "../api/hooks";

export default function MedicalHistoryPage() {
  const { data: visits, isPending: visitsPending, error: visitsError } = useMyMedicalHistory();
  const { data: prescriptions, isPending: presPending } = useMyPrescriptions();

  const [downloadModalOpen, setDownloadModalOpen] = useState(false);
  const [downloadData, setDownloadData] = useState<any>(null);
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await http.get("/phc/patient/download/");
      setDownloadData(res.data);
      setDownloadModalOpen(true);
      notifications.show({
        title: "Medical Records Ready",
        message: "Your clinical records have been compiled for download (UC-PHC-03).",
        color: "teal",
      });
    } catch {
      notifications.show({
        title: "Download Error",
        message: "Failed to download medical records.",
        color: "red",
      });
    } finally {
      setDownloading(false);
    }
  };

  if (visitsError) return <ErrorState error={visitsError} />;

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="My Health Records & Prescriptions"
        subtitle="Secure, read-only personal medical history and prescriptions (PHC-BR-02; AFR-PHC-009, 010)"
        action={
          <Button
            leftSection={<FaDownload />}
            variant="filled"
            color="teal"
            onClick={handleDownload}
            loading={downloading}
          >
            Download Records (PDF)
          </Button>
        }
      />

      <Tabs defaultValue="visits">
        <Tabs.List mb="md">
          <Tabs.Tab value="visits" leftSection={<FaFileMedical />}>
            Consultation Visits ({visits?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="prescriptions" leftSection={<FaPrescriptionBottleAlt />}>
            Digitized Prescriptions ({prescriptions?.length ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="visits">
          {visitsPending ? (
            <Text c="dimmed">Loading your visit records...</Text>
          ) : !visits || visits.length === 0 ? (
            <Card withBorder p="xl">
              <Text c="dimmed" ta="center">
                No past PHC consultation visit records found.
              </Text>
            </Card>
          ) : (
            <Stack gap="md">
              {visits.map((visit) => (
                <Card key={visit.id} withBorder shadow="xs" radius="md" p="md">
                  <Group justify="space-between" mb="xs">
                    <div>
                      <Text fw={600} size="md">
                        Consultation on {visit.visit_date}
                      </Text>
                      <Text size="xs" c="dimmed">
                        Attending Doctor: Dr. {visit.doctor_name}
                      </Text>
                    </div>
                    <Badge color="blue" variant="light">
                      Visit #{visit.id}
                    </Badge>
                  </Group>

                  <Divider my="xs" />

                  <SimpleGrid cols={{ base: 1, md: 2 }} mb="xs">
                    <div>
                      <Text size="xs" fw={700} c="dimmed">
                        Symptoms / Complaint:
                      </Text>
                      <Text size="sm">{visit.symptoms}</Text>
                    </div>
                    <div>
                      <Text size="xs" fw={700} c="dimmed">
                        Diagnosis:
                      </Text>
                      <Text size="sm" fw={500} c="blue.8">
                        {visit.diagnosis}
                      </Text>
                    </div>
                  </SimpleGrid>

                  {visit.notes && (
                    <Text size="xs" c="dimmed" mb="xs">
                      Clinical Advice: {visit.notes}
                    </Text>
                  )}

                  {visit.prescriptions && visit.prescriptions.length > 0 && (
                    <div>
                      <Text size="xs" fw={700} c="dimmed" mt="xs" mb={4}>
                        Attached Prescriptions:
                      </Text>
                      <Stack gap={4}>
                        {visit.prescriptions.map((p) => (
                          <Card key={p.id} withBorder p="xs" bg="gray.0">
                            <Group justify="space-between">
                              <Text size="xs" fw={600}>
                                Rx #{p.prescription_number} ({p.prescribed_date})
                              </Text>
                              {p.scanned_document_url && (
                                <Badge size="xs" color="teal" variant="outline">
                                  Scanned Copy Available
                                </Badge>
                              )}
                            </Group>
                            <Text size="xs" mt={2}>
                              {p.medicines_prescribed}
                            </Text>
                          </Card>
                        ))}
                      </Stack>
                    </div>
                  )}
                </Card>
              ))}
            </Stack>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="prescriptions">
          {presPending ? (
            <Text c="dimmed">Loading prescriptions...</Text>
          ) : !prescriptions || prescriptions.length === 0 ? (
            <Card withBorder p="xl">
              <Text c="dimmed" ta="center">
                No prescriptions recorded on file.
              </Text>
            </Card>
          ) : (
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Prescription #</Table.Th>
                  <Table.Th>Prescribed Date</Table.Th>
                  <Table.Th>Doctor</Table.Th>
                  <Table.Th>Medicines & Instructions</Table.Th>
                  <Table.Th>Document</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {prescriptions.map((p) => (
                  <Table.Tr key={p.id}>
                    <Table.Td fw={600}>{p.prescription_number}</Table.Td>
                    <Table.Td>{p.prescribed_date}</Table.Td>
                    <Table.Td>Dr. {p.doctor_name}</Table.Td>
                    <Table.Td>{p.medicines_prescribed}</Table.Td>
                    <Table.Td>
                      {p.scanned_document_url ? (
                        <Badge color="blue" variant="light">
                          Digitized Scanned
                        </Badge>
                      ) : (
                        <Text size="xs" c="dimmed">
                          Digital Entry
                        </Text>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Tabs.Panel>
      </Tabs>

      {/* PDF Download Preview Modal */}
      <Modal
        opened={downloadModalOpen}
        onClose={() => setDownloadModalOpen(false)}
        title="Official PHC Medical Records Summary"
        size="lg"
      >
        {downloadData && (
          <Stack>
            <Card withBorder p="md" bg="blue.0">
              <Text fw={700} size="md">
                Patient: {downloadData.patient_name} ({downloadData.patient_username})
              </Text>
              <Text size="xs" c="dimmed">
                Institute Primary Health Centre Official Health Record Export
              </Text>
              <Text size="xs" mt="xs">
                Total Consultations: {downloadData.total_visits} | Total Prescriptions: {downloadData.total_prescriptions}
              </Text>
            </Card>

            <Title order={5} mt="xs">
              Consultation Log
            </Title>
            <Table withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Date</Table.Th>
                  <Table.Th>Doctor</Table.Th>
                  <Table.Th>Diagnosis</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {downloadData.visits.map((v: any) => (
                  <Table.Tr key={v.id}>
                    <Table.Td>{v.visit_date}</Table.Td>
                    <Table.Td>Dr. {v.doctor_name}</Table.Td>
                    <Table.Td>{v.diagnosis}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setDownloadModalOpen(false)}>
                Close
              </Button>
              <Button
                color="teal"
                onClick={() => {
                  window.print();
                }}
              >
                Print / Save as PDF
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}

function SimpleGrid({ mb, children }: { cols?: any; mb?: string; children: React.ReactNode }) {
  return <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: mb }}>{children}</div>;
}
