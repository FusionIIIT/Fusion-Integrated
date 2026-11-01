import { useState } from "react";
import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Grid,
  Group,
  Modal,
  NumberInput,
  Progress,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaCheck, FaExclamationTriangle, FaEye, FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { ArchivalRequest, ArchiveClassification } from "../api";
import { useArchives, useSubmitArchive, useUserQuota } from "../api";
import { BadmsStatusBadge } from "../components/BadmsStatusBadge";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

export default function ArchivesPage() {
  const { data: archivesData, isLoading: loadingArchives } = useArchives();
  const { data: quota } = useUserQuota();
  const submitMutation = useSubmitArchive();

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedArchive, setSelectedArchive] = useState<ArchivalRequest | null>(null);

  // Form State
  const [fileName, setFileName] = useState("");
  const [documentDate, setDocumentDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [fileType, setFileType] = useState("pdf");
  const [fileSizeBytes, setFileSizeBytes] = useState<number | string>(1048576);
  const [owners, setOwners] = useState("");
  const [reason, setReason] = useState("");
  const [initialClassification, setInitialClassification] =
    useState<ArchiveClassification>("routine");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!fileName.trim()) {
      setErrorMsg("File name is required.");
      return;
    }
    if (!reason.trim()) {
      setErrorMsg("Reason is required.");
      return;
    }

    try {
      await submitMutation.mutateAsync({
        file_name: fileName.trim(),
        document_date: documentDate || new Date().toISOString().slice(0, 10),
        file_type: fileType,
        file_size_bytes: Number(fileSizeBytes) || 0,
        owners: owners
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        reason: reason.trim(),
        initial_classification: initialClassification,
      });
      setModalOpen(false);
      // Reset form
      setFileName("");
      setReason("");
      setOwners("");
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.error?.message ||
        "Submission failed. Check quota and inputs.";
      setErrorMsg(msg);
    }
  };

  const usedPercent =
    quota && quota.allocated_bytes > 0
      ? Math.min(100, Math.round((quota.used_bytes / quota.allocated_bytes) * 100))
      : 0;

  return (
    <Stack gap="lg">
      <PageHeader
        title="Secure Archival Management"
        subtitle="Submit, track, and manage official digital archive requests"
        action={
          <Button
            leftSection={<FaPlus size={14} />}
            onClick={() => {
              setErrorMsg("");
              setModalOpen(true);
            }}
          >
            Submit Archival Request
          </Button>
        }
      />

      {/* Storage Quota Widget */}
      {quota && (
        <Card withBorder padding="md" radius="md">
          <Group justify="space-between" mb="xs">
            <Text fw={600} size="sm">
              Your Storage Quota Utilization ({quota.department || "General"})
            </Text>
            <Text size="xs" c="dimmed">
              {formatBytes(quota.used_bytes)} used of {formatBytes(quota.allocated_bytes)} (
              {usedPercent}%)
            </Text>
          </Group>
          <Progress
            value={usedPercent}
            color={usedPercent > 90 ? "red" : usedPercent > 70 ? "orange" : "blue"}
            size="lg"
            radius="xl"
          />
          <Group justify="flex-end" mt="xs">
            <Text size="xs" c="dimmed">
              Remaining: {formatBytes(quota.remaining_bytes)}
            </Text>
          </Group>
        </Card>
      )}

      {/* Requests Table */}
      <Card withBorder padding="md" radius="md">
        <Text fw={600} size="md" mb="md">
          Archival Requests ({archivesData?.count || 0})
        </Text>
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>File Name</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>Document Date</Table.Th>
                <Table.Th>Initial Class.</Table.Th>
                <Table.Th>Authoritative Class.</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Size</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {loadingArchives ? (
                <Table.Tr>
                  <Table.Td colSpan={9} style={{ textAlign: "center" }}>
                    Loading archival requests...
                  </Table.Td>
                </Table.Tr>
              ) : !archivesData?.results?.length ? (
                <Table.Tr>
                  <Table.Td colSpan={9} style={{ textAlign: "center" }}>
                    No archival requests found. Click "Submit Archival Request" to begin.
                  </Table.Td>
                </Table.Tr>
              ) : (
                archivesData.results.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td>#{req.id}</Table.Td>
                    <Table.Td fw={500}>{req.file_name}</Table.Td>
                    <Table.Td>{req.department}</Table.Td>
                    <Table.Td>{req.document_date}</Table.Td>
                    <Table.Td>
                      <BadmsStatusBadge value={req.initial_classification} variant="outline" />
                    </Table.Td>
                    <Table.Td>
                      {req.authoritative_classification ? (
                        <BadmsStatusBadge
                          value={req.authoritative_classification}
                          variant="filled"
                        />
                      ) : (
                        <Text size="xs" c="dimmed">
                          Pending
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <BadmsStatusBadge value={req.status} />
                    </Table.Td>
                    <Table.Td>{formatBytes(req.file_size_bytes)}</Table.Td>
                    <Table.Td>
                      <ActionIcon
                        variant="subtle"
                        color="blue"
                        title="View Details"
                        onClick={() => setSelectedArchive(req)}
                      >
                        <FaEye size={14} />
                      </ActionIcon>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {/* Submission Modal */}
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Submit New Archival Request"
        size="lg"
      >
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            {errorMsg && (
              <Alert icon={<FaExclamationTriangle size={14} />} title="Error" color="red">
                {errorMsg}
              </Alert>
            )}

            <TextInput
              label="File Name"
              placeholder="e.g. Thesis_2026_Final.pdf"
              required
              value={fileName}
              onChange={(e) => setFileName(e.target.value)}
            />

            <Grid>
              <Grid.Col span={6}>
                <TextInput
                  label="Document Date"
                  type="date"
                  required
                  value={documentDate}
                  onChange={(e) => setDocumentDate(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <Select
                  label="File Type"
                  data={[
                    { value: "pdf", label: "PDF Document (.pdf)" },
                    { value: "docx", label: "Word Document (.docx)" },
                    { value: "sql", label: "SQL Database Dump (.sql)" },
                    { value: "tar.gz", label: "Tarball (.tar.gz)" },
                    { value: "zip", label: "ZIP Archive (.zip)" },
                    { value: "csv", label: "CSV Dataset (.csv)" },
                  ]}
                  value={fileType}
                  onChange={(val) => setFileType(val || "pdf")}
                />
              </Grid.Col>
            </Grid>

            <Grid>
              <Grid.Col span={6}>
                <NumberInput
                  label="File Size (Bytes)"
                  min={1}
                  required
                  value={fileSizeBytes}
                  onChange={(val) => setFileSizeBytes(val)}
                  description={formatBytes(Number(fileSizeBytes) || 0)}
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <Select
                  label="Initial Classification"
                  data={[
                    { value: "routine", label: "Routine (Standard)" },
                    { value: "sensitive", label: "Sensitive" },
                    { value: "critical", label: "Critical" },
                    { value: "archival", label: "Archival" },
                  ]}
                  value={initialClassification}
                  onChange={(val) =>
                    setInitialClassification((val as ArchiveClassification) || "routine")
                  }
                  description="Defaults to Routine. Authoritative classification assigned by SysAdmin."
                />
              </Grid.Col>
            </Grid>

            <TextInput
              label="Owners"
              placeholder="e.g. u1001, u1002 (comma-separated usernames or IDs)"
              value={owners}
              onChange={(e) => setOwners(e.target.value)}
            />

            <Textarea
              label="Reason for Archival"
              placeholder="Describe the significance and retention requirement of this file..."
              required
              minRows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={submitMutation.isPending}>
                Submit for HoD Review
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Details Modal */}
      <Modal
        opened={Boolean(selectedArchive)}
        onClose={() => setSelectedArchive(null)}
        title={`Archival Request #${selectedArchive?.id}: ${selectedArchive?.file_name}`}
        size="lg"
      >
        {selectedArchive && (
          <Stack gap="md">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Status:
              </Text>
              <BadmsStatusBadge value={selectedArchive.status} />
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Department:
              </Text>
              <Text size="sm" fw={500}>
                {selectedArchive.department}
              </Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Document Date:
              </Text>
              <Text size="sm">{selectedArchive.document_date}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                File Size:
              </Text>
              <Text size="sm">{formatBytes(selectedArchive.file_size_bytes)}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Initial Classification:
              </Text>
              <BadmsStatusBadge value={selectedArchive.initial_classification} variant="outline" />
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Authoritative Classification:
              </Text>
              {selectedArchive.authoritative_classification ? (
                <BadmsStatusBadge
                  value={selectedArchive.authoritative_classification}
                  variant="filled"
                />
              ) : (
                <Text size="sm" c="dimmed">
                  Not yet classified by SysAdmin
                </Text>
              )}
            </Group>

            <Card withBorder padding="sm" radius="sm">
              <Text fw={600} size="sm" mb="xs">
                HoD Review Details
              </Text>
              {selectedArchive.hod_decided_at ? (
                <Stack gap={4}>
                  <Text size="xs">Decided by User #{selectedArchive.hod_user_id}</Text>
                  <Text size="xs">Date: {new Date(selectedArchive.hod_decided_at).toLocaleString()}</Text>
                  <Text size="xs">Comments: {selectedArchive.hod_comments || "None"}</Text>
                </Stack>
              ) : (
                <Text size="xs" c="dimmed">
                  Pending review by Head of Department
                </Text>
              )}
            </Card>

            <Card withBorder padding="sm" radius="sm">
              <Text fw={600} size="sm" mb="xs">
                SysAdmin Classification
              </Text>
              {selectedArchive.sysadmin_classified_at ? (
                <Stack gap={4}>
                  <Text size="xs">Classified by User #{selectedArchive.sysadmin_user_id}</Text>
                  <Text size="xs">Date: {new Date(selectedArchive.sysadmin_classified_at).toLocaleString()}</Text>
                  <Text size="xs">Comments: {selectedArchive.sysadmin_comments || "None"}</Text>
                </Stack>
              ) : (
                <Text size="xs" c="dimmed">
                  Awaiting HoD approval before classification
                </Text>
              )}
            </Card>

            <Card withBorder padding="sm" radius="sm">
              <Text fw={600} size="sm" mb="xs">
                Security & Encryption (AES-256)
              </Text>
              {selectedArchive.is_encrypted ? (
                <Stack gap={4}>
                  <Group gap="xs">
                    <FaCheck size={14} color="green" />
                    <Text size="xs" c="green" fw={500}>
                      Encrypted with {selectedArchive.encryption_algorithm}
                    </Text>
                  </Group>
                  <Text size="xs">Configured by Security User #{selectedArchive.security_user_id}</Text>
                  {selectedArchive.security_configured_at && (
                    <Text size="xs">
                      Date: {new Date(selectedArchive.security_configured_at).toLocaleString()}
                    </Text>
                  )}
                </Stack>
              ) : (
                <Text size="xs" c="dimmed">
                  Not encrypted (non-sensitive or awaiting security configuration)
                </Text>
              )}
            </Card>

            <Group justify="flex-end">
              <Button variant="default" onClick={() => setSelectedArchive(null)}>
                Close
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
