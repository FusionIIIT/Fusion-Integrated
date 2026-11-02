import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Container,
  FileInput,
  Group,
  Loader,
  Modal,
  Rating,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import dayjs from "dayjs";
import { useState } from "react";
import { FaEye, FaPlus, FaRedo, FaRegCheckCircle, FaStar } from "react-icons/fa";

import {
  useCategories,
  useComplaints,
  useReopenRequest,
  useSubmitComplaint,
  useSubmitFeedback,
  useVerifyCloseComplaint,
} from "../api/hooks";
import type { ClosureVerification, ComplaintPriority, SubmitComplaintPayload } from "../api/types";
import { ComplaintDetailModal } from "../components/ComplaintDetailModal";
import { PriorityBadge } from "../components/PriorityBadge";
import { StatusBadge } from "../components/StatusBadge";

export function MyComplaintsPage() {
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const [detailId, setDetailId] = useState<number | null>(null);

  // Modals
  const [submitOpened, { open: openSubmit, close: closeSubmit }] = useDisclosure(false);
  const [reopenTargetId, setReopenTargetId] = useState<number | null>(null);
  const [reopenReason, setReopenReason] = useState("");
  const [feedbackTargetId, setFeedbackTargetId] = useState<number | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackComments, setFeedbackComments] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Submit form state
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<ComplaintPriority>("medium");
  const [verificationRequired, setVerificationRequired] = useState<ClosureVerification>("none");
  const [attachments, setAttachments] = useState<File[]>([]);

  // Queries & Mutations
  const { data: complaints, isLoading } = useComplaints({
    status: selectedStatus || undefined,
  });
  const { data: categories } = useCategories();
  const submitMutation = useSubmitComplaint();
  const verifyCloseMutation = useVerifyCloseComplaint();
  const reopenMutation = useReopenRequest(reopenTargetId || 0);
  const feedbackMutation = useSubmitFeedback(feedbackTargetId || 0);

  const handleCreateComplaint = async () => {
    if (!categoryId || !location.trim() || !description.trim()) {
      setErrorMsg("Please fill in category, location, and description.");
      return;
    }
    setErrorMsg("");
    try {
      const payload: SubmitComplaintPayload = {
        category_id: Number(categoryId),
        location: location.trim(),
        description: description.trim(),
        priority,
        verification_required: verificationRequired,
        attachments: attachments.length ? attachments : undefined,
      };
      await submitMutation.mutateAsync(payload);
      closeSubmit();
      setLocation("");
      setDescription("");
      setAttachments([]);
      setCategoryId(null);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || "Failed to submit complaint.");
    }
  };

  const handleVerifyClose = async (id: number) => {
    try {
      await verifyCloseMutation.mutateAsync({ id, remarks: "Verified and closed by user" });
      setDetailId(null);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to verify closure.");
    }
  };

  const handleRequestReopening = async () => {
    if (!reopenTargetId || !reopenReason.trim()) return;
    try {
      await reopenMutation.mutateAsync({ reopening_reason: reopenReason.trim() });
      setReopenTargetId(null);
      setReopenReason("");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to request reopening.");
    }
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackTargetId) return;
    try {
      await feedbackMutation.mutateAsync({
        rating: feedbackRating,
        comments: feedbackComments.trim(),
      });
      setFeedbackTargetId(null);
      setFeedbackComments("");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to submit feedback.");
    }
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Title order={2}>My Complaints</Title>
            <Text c="dimmed" size="sm">
              Lodge institutional complaints, track status history, and verify resolutions.
            </Text>
          </div>
          <Button leftSection={<FaPlus />} onClick={openSubmit}>
            Lodge Complaint
          </Button>
        </Group>

        <Group>
          <Select
            placeholder="Filter by Status"
            clearable
            value={selectedStatus}
            onChange={setSelectedStatus}
            data={[
              { value: "submitted", label: "Submitted" },
              { value: "in_progress", label: "In Progress" },
              { value: "resolved", label: "Resolved" },
              { value: "closed", label: "Closed" },
              { value: "rejected", label: "Rejected" },
            ]}
          />
        </Group>

        <Card withBorder radius="md" p={0}>
          {isLoading ? (
            <Stack align="center" py="xl">
              <Loader size="md" />
            </Stack>
          ) : !complaints || complaints.length === 0 ? (
            <Stack align="center" py="xl">
              <Text c="dimmed">No complaints found. Click 'Lodge Complaint' to register one.</Text>
            </Stack>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Location</Table.Th>
                  <Table.Th>Priority</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>SLA Deadline</Table.Th>
                  <Table.Th>Submitted</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {complaints.map((c) => (
                  <Table.Tr key={c.id}>
                    <Table.Td fw={500}>{c.complaint_id}</Table.Td>
                    <Table.Td>{c.category_name}</Table.Td>
                    <Table.Td>{c.location}</Table.Td>
                    <Table.Td>
                      <PriorityBadge priority={c.priority} />
                    </Table.Td>
                    <Table.Td>
                      <StatusBadge status={c.status} isEscalated={c.is_escalated} />
                    </Table.Td>
                    <Table.Td>
                      {c.sla_deadline ? dayjs(c.sla_deadline).format("DD MMM, hh:mm A") : "—"}
                    </Table.Td>
                    <Table.Td>{dayjs(c.created_at).format("DD MMM YYYY")}</Table.Td>
                    <Table.Td>
                      <Group gap={6}>
                        <ActionIcon
                          variant="subtle"
                          color="blue"
                          title="View Details"
                          onClick={() => setDetailId(c.id)}
                        >
                          <FaEye />
                        </ActionIcon>

                        {c.status === "resolved" && c.verification_required === "user" && (
                          <Button
                            size="xs"
                            color="teal"
                            variant="light"
                            leftSection={<FaRegCheckCircle />}
                            onClick={() => handleVerifyClose(c.id)}
                          >
                            Verify & Close
                          </Button>
                        )}

                        {c.status === "closed" && c.reopening_status === "none" && (
                          <Button
                            size="xs"
                            color="orange"
                            variant="light"
                            leftSection={<FaRedo />}
                            onClick={() => setReopenTargetId(c.id)}
                          >
                            Reopen
                          </Button>
                        )}

                        {(c.status === "resolved" || c.status === "closed") && (
                          <ActionIcon
                            variant="subtle"
                            color="yellow"
                            title="Provide Feedback"
                            onClick={() => setFeedbackTargetId(c.id)}
                          >
                            <FaStar />
                          </ActionIcon>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>

        {/* Modal: Submit Complaint */}
        <Modal opened={submitOpened} onClose={closeSubmit} title="Lodge New Complaint" size="lg">
          <Stack gap="md">
            {errorMsg && (
              <Alert color="red" onClose={() => setErrorMsg("")} withCloseButton>
                {errorMsg}
              </Alert>
            )}

            <Select
              label="Complaint Category"
              placeholder="Select category (e.g. Electrical, Plumbing)"
              required
              value={categoryId}
              onChange={setCategoryId}
              data={categories?.map((cat) => ({ value: String(cat.id), label: cat.name })) || []}
            />

            <TextInput
              label="Location"
              placeholder="e.g. Hall 3, Room B-204"
              required
              value={location}
              onChange={(e) => setLocation(e.currentTarget.value)}
            />

            <Textarea
              label="Description"
              placeholder="Describe the problem in detail..."
              required
              minRows={3}
              value={description}
              onChange={(e) => setDescription(e.currentTarget.value)}
            />

            <Group grow>
              <Select
                label="Priority"
                value={priority}
                onChange={(val) => setPriority((val as ComplaintPriority) || "medium")}
                data={[
                  { value: "low", label: "Low (72h SLA)" },
                  { value: "medium", label: "Medium (48h SLA)" },
                  { value: "high", label: "High (24h SLA)" },
                ]}
              />

              <Select
                label="Closure Verification"
                value={verificationRequired}
                onChange={(val) => setVerificationRequired((val as ClosureVerification) || "none")}
                data={[
                  { value: "none", label: "Direct closure upon resolution" },
                  { value: "user", label: "User verification required" },
                  { value: "supervisor", label: "Supervisor verification required" },
                ]}
              />
            </Group>

            <FileInput
              label="Supporting Evidence / Attachment"
              placeholder="Attach photo or document"
              multiple
              value={attachments}
              onChange={setAttachments}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={closeSubmit}>
                Cancel
              </Button>
              <Button loading={submitMutation.isPending} onClick={handleCreateComplaint}>
                Submit Complaint
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Request Reopening */}
        <Modal
          opened={Boolean(reopenTargetId)}
          onClose={() => setReopenTargetId(null)}
          title="Request Complaint Reopening"
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              If the resolution was unsatisfactory or the issue recurred, provide detailed reasons
              for the Complaint Supervisor to review.
            </Text>
            <Textarea
              label="Reason for Reopening"
              placeholder="Explain why this complaint should be reopened..."
              required
              minRows={3}
              value={reopenReason}
              onChange={(e) => setReopenReason(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setReopenTargetId(null)}>
                Cancel
              </Button>
              <Button
                color="orange"
                loading={reopenMutation.isPending}
                onClick={handleRequestReopening}
              >
                Submit Reopening Request
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Feedback */}
        <Modal
          opened={Boolean(feedbackTargetId)}
          onClose={() => setFeedbackTargetId(null)}
          title="Submit Resolution Feedback"
        >
          <Stack gap="md">
            <div>
              <Text size="sm" fw={500} mb={4}>
                Satisfaction Rating
              </Text>
              <Rating value={feedbackRating} onChange={setFeedbackRating} size="lg" />
            </div>
            <Textarea
              label="Comments (Optional)"
              placeholder="Share your experience or remarks..."
              value={feedbackComments}
              onChange={(e) => setFeedbackComments(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setFeedbackTargetId(null)}>
                Cancel
              </Button>
              <Button loading={feedbackMutation.isPending} onClick={handleSubmitFeedback}>
                Submit Feedback
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Detail Modal */}
        <ComplaintDetailModal
          complaintId={detailId}
          opened={Boolean(detailId)}
          onClose={() => setDetailId(null)}
        />
      </Stack>
    </Container>
  );
}

export default MyComplaintsPage;

