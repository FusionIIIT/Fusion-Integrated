import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Modal,
  Progress,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import {
  FaCheckCircle,
  FaDatabase,
  FaExclamationCircle,
  FaFileContract,
  FaHdd,
  FaPlus,
  FaShieldAlt,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAuditLogs,
  useComplianceReport,
  useSpecialArchives,
  useSubmitSpecialArchival,
} from "../api";
import type { SpecialArchivalRecord } from "../api";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 MB";
  const mb = bytes / (1024 * 1024);
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`;
  }
  return `${mb.toFixed(1)} MB`;
}

export default function AuditReportsPage() {
  const { data: compliance } = useComplianceReport();
  const { data: auditData, isLoading: auditLoading } = useAuditLogs();
  const { data: specialArchivesData, isLoading: specialLoading } = useSpecialArchives();
  const submitSpecialArchival = useSubmitSpecialArchival();

  // Special Archival Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [reqName, setReqName] = useState("");
  const [reqDesignation, setReqDesignation] = useState("");
  const [datasetTitle, setDatasetTitle] = useState("");
  const [mediaType, setMediaType] = useState("LTO-8 Tape");
  const [mediaSerial, setMediaSerial] = useState("");
  const [vaultLocation, setVaultLocation] = useState("Air-gapped Vault B, Section 12");
  const [notes, setNotes] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; error?: boolean } | null>(null);

  const auditLogs = auditData?.results || [];
  const specialArchives: SpecialArchivalRecord[] = specialArchivesData?.results || [];

  const handleCreateSpecialArchive = async () => {
    setFeedbackMsg(null);
    if (!reqName.trim() || !datasetTitle.trim() || !mediaSerial.trim()) {
      setFeedbackMsg({ text: "Please fill in all required fields.", error: true });
      return;
    }

    try {
      await submitSpecialArchival.mutateAsync({
        requester_name: reqName.trim(),
        requester_designation: reqDesignation.trim() || "Authority / Dean",
        dataset_title: datasetTitle.trim(),
        offline_media_type: mediaType,
        media_serial_number: mediaSerial.trim(),
        storage_vault_location: vaultLocation.trim(),
        notes: notes.trim(),
      });
      setModalOpen(false);
      setReqName("");
      setDatasetTitle("");
      setMediaSerial("");
      setNotes("");
      setFeedbackMsg({ text: "Special offline archival recorded and audited successfully." });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record special archival";
      setFeedbackMsg({ text: msg, error: true });
    }
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Audit Trail & Retention Reports"
        subtitle="Operational compliance analytics, immutable security audit logs, and offline special archival records"
      />

      <Stack gap="lg" mt="md">
        {feedbackMsg && (
          <Alert
            color={feedbackMsg.error ? "red" : "green"}
            icon={feedbackMsg.error ? <FaExclamationCircle /> : <FaCheckCircle />}
            withCloseButton
            onClose={() => setFeedbackMsg(null)}
          >
            {feedbackMsg.text}
          </Alert>
        )}

        {/* High-Level Compliance Metrics */}
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Card padding="md" withBorder radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Retention Compliance
                </Text>
                <FaShieldAlt color="#2b8a3e" />
              </Group>
              <Title order={2} mt="xs" c="green.7">
                {compliance?.archives.compliance_rate_percent ?? 100}%
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                {compliance?.archives.compliant_count ?? 0} of {compliance?.archives.total ?? 0}{" "}
                archives protected
              </Text>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Card padding="md" withBorder radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Backup Health
                </Text>
                <FaHdd color="#1c7ed6" />
              </Group>
              <Title order={2} mt="xs">
                {compliance?.backups.successful ?? 0} / {compliance?.backups.total ?? 0}
              </Title>
              <Text size="xs" c={compliance?.backups.consecutive_failures ? "red" : "dimmed"} mt={4}>
                {compliance?.backups.consecutive_failures ?? 0} consecutive failures
              </Text>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Card padding="md" withBorder radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Restorations
                </Text>
                <FaDatabase color="#f59f00" />
              </Group>
              <Title order={2} mt="xs">
                {compliance?.restorations.completed ?? 0}
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                {compliance?.restorations.pending ?? 0} sensitive approvals pending
              </Text>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Card padding="md" withBorder radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Storage Allocation
                </Text>
                <FaFileContract color="#7048e8" />
              </Group>
              <Title order={2} mt="xs">
                {formatBytes(compliance?.storage.total_used_bytes ?? 0)}
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                of {formatBytes(compliance?.storage.total_allocated_bytes ?? 0)} quota
              </Text>
            </Card>
          </Grid.Col>
        </Grid>

        <Tabs defaultValue="compliance">
          <Tabs.List>
            <Tabs.Tab value="compliance" leftSection={<FaFileContract />}>
              Compliance Summary
            </Tabs.Tab>
            <Tabs.Tab value="audit" leftSection={<FaShieldAlt />}>
              Audit Trail ({auditLogs.length})
            </Tabs.Tab>
            <Tabs.Tab value="special" leftSection={<FaHdd />}>
              Special Offline Archival ({specialArchives.length})
            </Tabs.Tab>
          </Tabs.List>

          {/* Compliance Tab */}
          <Tabs.Panel value="compliance" pt="md">
            <Stack gap="md">
              <Card padding="lg" withBorder radius="md">
                <Title order={4} mb="sm">
                  Institutional Storage Quota Overview
                </Title>
                <Progress
                  value={compliance?.storage.utilization_percent ?? 0}
                  size="xl"
                  radius="xl"
                  color="blue"
                  my="sm"
                />
                <Group justify="space-between" mt="xs">
                  <div>
                    <Text size="xs" c="dimmed">
                      Used Bytes
                    </Text>
                    <Text fw={600}>{formatBytes(compliance?.storage.total_used_bytes ?? 0)}</Text>
                  </div>
                  <div>
                    <Text size="xs" c="dimmed">
                      Remaining Capacity
                    </Text>
                    <Text fw={600}>{formatBytes(compliance?.storage.total_remaining_bytes ?? 0)}</Text>
                  </div>
                  <div>
                    <Text size="xs" c="dimmed">
                      Total Allocation
                    </Text>
                    <Text fw={600}>{formatBytes(compliance?.storage.total_allocated_bytes ?? 0)}</Text>
                  </div>
                  <div>
                    <Text size="xs" c="dimmed">
                      Utilization
                    </Text>
                    <Badge color="blue">{compliance?.storage.utilization_percent ?? 0}%</Badge>
                  </div>
                </Group>
              </Card>

              <Card padding="lg" withBorder radius="md">
                <Title order={4} mb="sm">
                  Archive Classification Distribution
                </Title>
                <Grid>
                  {Object.entries(compliance?.archives.by_classification || {}).map(
                    ([classification, count]) => (
                      <Grid.Col key={classification} span={{ base: 6, sm: 3 }}>
                        <Card withBorder padding="sm">
                          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                            {classification}
                          </Text>
                          <Title order={3} mt="xs">
                            {count}
                          </Title>
                        </Card>
                      </Grid.Col>
                    ),
                  )}
                </Grid>
              </Card>
            </Stack>
          </Tabs.Panel>

          {/* Audit Trail Tab */}
          <Tabs.Panel value="audit" pt="md">
            <Card padding="lg" withBorder radius="md">
              <Title order={4} mb="md">
                Security & Operational Audit Log
              </Title>

              {auditLoading ? (
                <Text c="dimmed">Loading audit events...</Text>
              ) : auditLogs.length === 0 ? (
                <Text c="dimmed">No audit events recorded yet.</Text>
              ) : (
                <Table highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Timestamp</Table.Th>
                      <Table.Th>Actor</Table.Th>
                      <Table.Th>Action</Table.Th>
                      <Table.Th>Target</Table.Th>
                      <Table.Th>Outcome</Table.Th>
                      <Table.Th>Audit Details</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {auditLogs.map((log) => (
                      <Table.Tr key={log.id}>
                        <Table.Td>
                          <Text size="xs">{new Date(log.created_at).toLocaleString()}</Text>
                        </Table.Td>
                        <Table.Td>
                          User {log.actor_user_id} ({log.actor_role})
                        </Table.Td>
                        <Table.Td>
                          <Badge variant="outline" color="dark">
                            {log.action}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          {log.target_type} #{log.target_id}
                        </Table.Td>
                        <Table.Td>
                          <Badge color={log.outcome === "success" ? "green" : "red"}>
                            {log.outcome}
                          </Badge>
                        </Table.Td>
                        <Table.Td style={{ maxWidth: 300 }}>
                          <Text size="xs" ff="monospace" lineClamp={2}>
                            {JSON.stringify(log.details)}
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          {/* Special Offline Archival Tab */}
          <Tabs.Panel value="special" pt="md">
            <Card padding="lg" withBorder radius="md">
              <Group justify="space-between" mb="md">
                <div>
                  <Title order={4}>Offline Special Archival Repository</Title>
                  <Text size="sm" c="dimmed">
                    Air-gapped and physical media archive records for sensitive research data
                  </Text>
                </div>
                <Button leftSection={<FaPlus />} onClick={() => setModalOpen(true)}>
                  Record Special Archival
                </Button>
              </Group>

              {specialLoading ? (
                <Text c="dimmed">Loading special archives...</Text>
              ) : specialArchives.length === 0 ? (
                <Text c="dimmed">No offline special archives recorded.</Text>
              ) : (
                <Table highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Dataset Title</Table.Th>
                      <Table.Th>Media Type & Serial</Table.Th>
                      <Table.Th>Storage Location</Table.Th>
                      <Table.Th>Requested By</Table.Th>
                      <Table.Th>Completed Date</Table.Th>
                      <Table.Th>Checksum</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {specialArchives.map((sa) => (
                      <Table.Tr key={sa.id}>
                        <Table.Td fw={600}>#{sa.id}</Table.Td>
                        <Table.Td>
                          <Text fw={500}>{sa.dataset_title}</Text>
                          <Badge color="red" size="xs">
                            {sa.classification}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{sa.offline_media_type}</Text>
                          <Text size="xs" c="dimmed">
                            S/N: {sa.media_serial_number}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{sa.storage_vault_location}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">
                            {sa.requester_name} ({sa.requester_designation})
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{new Date(sa.completed_at).toLocaleDateString()}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" ff="monospace">
                            {sa.checksum ? `${sa.checksum.slice(0, 12)}...` : "-"}
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Stack>

      {/* Special Archival Record Modal */}
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Record Offline Special Archival (Super Admin)"
        size="lg"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Record physical deposition of Sensitive Research Data to air-gapped or offline media.
            An immutable audit log will be created upon submission.
          </Text>

          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="Authorizing Requester Name"
                placeholder="e.g. Prof. R. Sharma"
                value={reqName}
                onChange={(e) => setReqName(e.currentTarget.value)}
                required
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Requester Designation / Title"
                placeholder="e.g. Dean of Research & Development"
                value={reqDesignation}
                onChange={(e) => setReqDesignation(e.currentTarget.value)}
                required
              />
            </Grid.Col>
          </Grid>

          <TextInput
            label="Sensitive Research Dataset Title"
            placeholder="e.g. Quantum Key Distribution Experiments 2026"
            value={datasetTitle}
            onChange={(e) => setDatasetTitle(e.currentTarget.value)}
            required
          />

          <Grid>
            <Grid.Col span={6}>
              <Select
                label="Offline Media Type"
                value={mediaType}
                onChange={(val) => setMediaType(val || "LTO-8 Tape")}
                data={[
                  { value: "LTO-8 Tape", label: "LTO-8 Magnetic Tape" },
                  { value: "Optical M-DISC", label: "Archival Optical M-DISC" },
                  { value: "Air-gapped HSM", label: "Air-gapped Hardware Security Module" },
                ]}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Physical Media Serial Number"
                placeholder="e.g. TAPE-QC-2026-009A"
                value={mediaSerial}
                onChange={(e) => setMediaSerial(e.currentTarget.value)}
                required
              />
            </Grid.Col>
          </Grid>

          <TextInput
            label="Storage Vault Location"
            placeholder="e.g. Sub-Basement Vault Room 04"
            value={vaultLocation}
            onChange={(e) => setVaultLocation(e.currentTarget.value)}
            required
          />

          <Textarea
            label="Chain of Custody / Notes"
            placeholder="Verification details, custody sign-offs..."
            minRows={2}
            value={notes}
            onChange={(e) => setNotes(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={submitSpecialArchival.isPending}
              onClick={handleCreateSpecialArchive}
            >
              Record Special Archival
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
