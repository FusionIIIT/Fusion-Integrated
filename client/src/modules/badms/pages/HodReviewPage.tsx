import { useState } from "react";
import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
} from "@mantine/core";
import { FaCheck, FaExclamationTriangle, FaEye, FaInfoCircle, FaTimes } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { ArchivalRequest } from "../api";
import { useArchives, useHodReview } from "../api";
import { BadmsStatusBadge } from "../components/BadmsStatusBadge";

export default function HodReviewPage() {
  const { data: archivesData, isLoading } = useArchives({ status: "submitted" });
  const reviewMutation = useHodReview();

  const [selectedArchive, setSelectedArchive] = useState<ArchivalRequest | null>(null);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<ArchivalRequest | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleApprove = async (req: ArchivalRequest) => {
    setErrorMsg("");
    setSuccessMsg("");
    try {
      await reviewMutation.mutateAsync({
        id: req.id,
        payload: { decision: "approve", comments: "Approved by Head of Department." },
      });
      setSuccessMsg(`Archival request #${req.id} (${req.file_name}) approved successfully.`);
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.detail ||
          err?.response?.data?.error?.message ||
          "Failed to approve request.",
      );
    }
  };

  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectTarget) return;
    if (!rejectionReason.trim()) {
      setErrorMsg("Rejection reason is required.");
      return;
    }

    setErrorMsg("");
    setSuccessMsg("");
    try {
      await reviewMutation.mutateAsync({
        id: rejectTarget.id,
        payload: { decision: "reject", comments: rejectionReason.trim() },
      });
      setSuccessMsg(
        `Archival request #${rejectTarget.id} (${rejectTarget.file_name}) rejected. Quota has been released.`,
      );
      setRejectModalOpen(false);
      setRejectTarget(null);
      setRejectionReason("");
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.detail ||
          err?.response?.data?.error?.message ||
          "Failed to reject request.",
      );
    }
  };

  const pendingRequests = archivesData?.results || [];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Department Archival Review (HoD)"
        subtitle="Review, approve, or reject archival submissions originating within your department"
      />

      <Alert icon={<FaInfoCircle size={14} />} color="blue">
        Department Scoping Active: As Head of Department, you only see and action requests
        originating from your department. Cross-department review is strictly restricted.
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

      <Card withBorder padding="md" radius="md">
        <Text fw={600} size="md" mb="md">
          Pending Submissions ({pendingRequests.length})
        </Text>
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>File Name</Table.Th>
                <Table.Th>Requester ID</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Initial Class.</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {isLoading ? (
                <Table.Tr>
                  <Table.Td colSpan={8} style={{ textAlign: "center" }}>
                    Loading pending submissions...
                  </Table.Td>
                </Table.Tr>
              ) : pendingRequests.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={8} style={{ textAlign: "center" }}>
                    No pending archival requests requiring your department review.
                  </Table.Td>
                </Table.Tr>
              ) : (
                pendingRequests.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td>#{req.id}</Table.Td>
                    <Table.Td fw={500}>{req.file_name}</Table.Td>
                    <Table.Td>User #{req.user_id}</Table.Td>
                    <Table.Td>{req.department}</Table.Td>
                    <Table.Td>{req.document_date}</Table.Td>
                    <Table.Td>
                      <BadmsStatusBadge value={req.initial_classification} variant="outline" />
                    </Table.Td>
                    <Table.Td style={{ maxWidth: 220 }}>
                      <Text size="xs" lineClamp={2}>
                        {req.reason}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          leftSection={<FaCheck size={14} />}
                          loading={reviewMutation.isPending}
                          onClick={() => handleApprove(req)}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          leftSection={<FaTimes size={14} />}
                          onClick={() => {
                            setRejectTarget(req);
                            setRejectionReason("");
                            setRejectModalOpen(true);
                          }}
                        >
                          Reject
                        </Button>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          title="View"
                          onClick={() => setSelectedArchive(req)}
                        >
                          <FaEye size={14} />
                        </ActionIcon>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {/* Rejection Modal */}
      <Modal
        opened={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title={`Reject Archival Request #${rejectTarget?.id}`}
      >
        <form onSubmit={handleRejectSubmit}>
          <Stack gap="md">
            <Text size="sm">
              Rejecting request for <strong>{rejectTarget?.file_name}</strong> will return the
              allocated storage quota back to the student.
            </Text>
            <Textarea
              label="Rejection Reason"
              placeholder="Explain why this request is being rejected..."
              required
              minRows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setRejectModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" color="red" loading={reviewMutation.isPending}>
                Confirm Rejection
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Details Modal */}
      <Modal
        opened={Boolean(selectedArchive)}
        onClose={() => setSelectedArchive(null)}
        title={`Request #${selectedArchive?.id}: ${selectedArchive?.file_name}`}
      >
        {selectedArchive && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Department:
              </Text>
              <Text size="sm">{selectedArchive.department}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Owners:
              </Text>
              <Text size="sm">{selectedArchive.owners?.join(", ") || `User #${selectedArchive.user_id}`}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                File Size:
              </Text>
              <Text size="sm">{(selectedArchive.file_size_bytes / 1024).toFixed(1)} KB</Text>
            </Group>
            <Text size="sm" fw={500} mt="xs">
              Reason for Archival:
            </Text>
            <Text size="xs">{selectedArchive.reason}</Text>
            <Group justify="flex-end" mt="md">
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
