import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { FaCheck, FaExclamationTriangle, FaShieldAlt } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { ArchivalRequest, ArchiveClassification } from "../api";
import { useArchives, useClassifyArchive } from "../api";
import { BadmsStatusBadge } from "../components/BadmsStatusBadge";

export default function ClassificationPage() {
  const { data: hodApprovedData, isLoading } = useArchives({ status: "hod_approved" });
  const classifyMutation = useClassifyArchive();

  const [classifyTarget, setClassifyTarget] = useState<ArchivalRequest | null>(null);
  const [classification, setClassification] = useState<ArchiveClassification>("routine");
  const [comments, setComments] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleClassifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!classifyTarget) return;

    setErrorMsg("");
    setSuccessMsg("");
    try {
      await classifyMutation.mutateAsync({
        id: classifyTarget.id,
        payload: { classification, comments: comments.trim() },
      });
      setSuccessMsg(
        `Archive #${classifyTarget.id} authoritatively classified as ${classification.toUpperCase()}. ${
          classification === "sensitive" ? "Routed to IT Security for encryption." : "Policy applied."
        }`,
      );
      setClassifyTarget(null);
      setComments("");
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.detail ||
          err?.response?.data?.error?.message ||
          "Failed to classify archive.",
      );
    }
  };

  const pendingClassification = hodApprovedData?.results || [];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Authoritative Archive Classification"
        subtitle="Assign institutional classification (Critical, Sensitive, Routine, Archival) to HoD-approved requests"
      />

      <Alert icon={<FaShieldAlt size={14} />} color="blue">
        Classification Policy: Only System Administration assigns the authoritative
        classification. Files classified as <strong>Sensitive</strong> are automatically routed
        to IT Security for AES-256 encryption. Non-sensitive files receive automated policy application.
      </Alert>

      {successMsg && (
        <Alert icon={<FaCheck size={14} />} color="green" withCloseButton onClose={() => setSuccessMsg("")}>
          {successMsg}
        </Alert>
      )}

      {errorMsg && (
        <Alert icon={<FaExclamationTriangle size={14} />} color="red" withCloseButton onClose={() => setErrorMsg("")}>
          {errorMsg}
        </Alert>
      )}

      {/* Awaiting Classification Table */}
      <Card withBorder padding="md" radius="md">
        <Text fw={600} size="md" mb="md">
          HoD-Approved Requests Awaiting Classification ({pendingClassification.length})
        </Text>
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>File Name</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>HoD Approved Date</Table.Th>
                <Table.Th>Initial Class.</Table.Th>
                <Table.Th>Size</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {isLoading ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    Loading pending classifications...
                  </Table.Td>
                </Table.Tr>
              ) : pendingClassification.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    No HoD-approved archives awaiting classification.
                  </Table.Td>
                </Table.Tr>
              ) : (
                pendingClassification.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td>#{req.id}</Table.Td>
                    <Table.Td fw={500}>{req.file_name}</Table.Td>
                    <Table.Td>{req.department}</Table.Td>
                    <Table.Td>
                      {req.hod_decided_at
                        ? new Date(req.hod_decided_at).toLocaleDateString()
                        : "Approved"}
                    </Table.Td>
                    <Table.Td>
                      <BadmsStatusBadge value={req.initial_classification} variant="outline" />
                    </Table.Td>
                    <Table.Td>{(req.file_size_bytes / 1024).toFixed(1)} KB</Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        color="blue"
                        onClick={() => {
                          setClassifyTarget(req);
                          setClassification(req.initial_classification || "routine");
                          setComments("");
                        }}
                      >
                        Assign Classification
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {/* Classification Modal */}
      <Modal
        opened={Boolean(classifyTarget)}
        onClose={() => setClassifyTarget(null)}
        title={`Assign Classification for #${classifyTarget?.id}: ${classifyTarget?.file_name}`}
      >
        <form onSubmit={handleClassifySubmit}>
          <Stack gap="md">
            <Text size="sm">
              Originating Department: <strong>{classifyTarget?.department}</strong> | Initial:{" "}
              <strong>{classifyTarget?.initial_classification?.toUpperCase()}</strong>
            </Text>

            <Select
              label="Authoritative Classification"
              data={[
                { value: "routine", label: "Routine - Standard institutional retention" },
                {
                  value: "sensitive",
                  label: "Sensitive - Requires AES-256 encryption via IT Security",
                },
                { value: "critical", label: "Critical - Essential operations" },
                { value: "archival", label: "Archival - Permanent historical records" },
              ]}
              required
              value={classification}
              onChange={(val) => setClassification((val as ArchiveClassification) || "routine")}
            />

            {classification === "sensitive" && (
              <Alert icon={<FaShieldAlt size={14} />} color="orange">
                Notice: Assigning <strong>Sensitive</strong> will immediately route this archive
                to IT Security to configure AES-256 encryption.
              </Alert>
            )}

            <TextInput
              label="Classification Notes / Rationale"
              placeholder="e.g. Approved routine departmental thesis archive"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
            />

            <Group justify="flex-end">
              <Button variant="default" onClick={() => setClassifyTarget(null)}>
                Cancel
              </Button>
              <Button type="submit" color="blue" loading={classifyMutation.isPending}>
                Apply Authoritative Classification
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
}
