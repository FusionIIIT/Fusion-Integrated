import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import dayjs from "dayjs";
import { useState } from "react";
import {
  FaCheckCircle,
  FaExclamationCircle,
  FaEye,
  FaRedo,
  FaShieldAlt,
  FaTimesCircle,
} from "react-icons/fa";

import { useComplaints, useReopenReview, useVerifyCloseComplaint } from "../api/hooks";
import { ComplaintDetailModal } from "../components/ComplaintDetailModal";
import { PriorityBadge } from "../components/PriorityBadge";
import { StatusBadge } from "../components/StatusBadge";

export function SupervisorPage() {
  const [detailId, setDetailId] = useState<number | null>(null);

  // Review modal state
  const [reviewTarget, setReviewTarget] = useState<any | null>(null);
  const [reviewApproved, setReviewApproved] = useState<boolean>(true);
  const [reviewRemarks, setReviewRemarks] = useState("");

  // Verification modal state
  const [verifyTargetId, setVerifyTargetId] = useState<number | null>(null);
  const [verifyRemarks, setVerifyRemarks] = useState("");

  // Queries
  const { data: allComplaints, isLoading } = useComplaints();

  // Filter into the 3 supervisory buckets
  const escalatedComplaints = allComplaints?.filter((c) => c.is_escalated) || [];
  const pendingReopenings =
    allComplaints?.filter((c) => c.reopening_status === "pending") || [];
  const supervisorVerifications =
    allComplaints?.filter(
      (c) => c.status === "resolved" && c.verification_required === "supervisor"
    ) || [];

  const reopenReviewMutation = useReopenReview(reviewTarget?.id || 0);
  const verifyCloseMutation = useVerifyCloseComplaint(verifyTargetId || 0);

  const handleOpenReview = (c: any, approved: boolean) => {
    setReviewTarget(c);
    setReviewApproved(approved);
    setReviewRemarks("");
  };

  const handleExecuteReview = async () => {
    if (!reviewTarget) return;
    try {
      await reopenReviewMutation.mutateAsync({
        approved: reviewApproved,
        review_remarks: reviewRemarks.trim(),
      });
      setReviewTarget(null);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to submit reopening review.");
    }
  };

  const handleExecuteVerification = async () => {
    if (!verifyTargetId) return;
    try {
      await verifyCloseMutation.mutateAsync({
        remarks: verifyRemarks.trim(),
      });
      setVerifyTargetId(null);
      setVerifyRemarks("");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to verify closure.");
    }
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <div>
          <Title order={2}>Supervisor Oversight</Title>
          <Text c="dimmed" size="sm">
            Monitor escalated complaints, review reopening requests, and verify resolutions.
          </Text>
        </div>

        <Tabs defaultValue="escalated">
          <Tabs.List>
            <Tabs.Tab
              value="escalated"
              leftSection={<FaExclamationCircle color="#e03131" />}
              rightSection={
                <Badge size="xs" color="red">
                  {escalatedComplaints.length}
                </Badge>
              }
            >
              Escalated Complaints
            </Tabs.Tab>
            <Tabs.Tab
              value="reopenings"
              leftSection={<FaRedo color="#f08c00" />}
              rightSection={
                <Badge size="xs" color="orange">
                  {pendingReopenings.length}
                </Badge>
              }
            >
              Pending Reopenings
            </Tabs.Tab>
            <Tabs.Tab
              value="verifications"
              leftSection={<FaShieldAlt color="#2b8a3e" />}
              rightSection={
                <Badge size="xs" color="teal">
                  {supervisorVerifications.length}
                </Badge>
              }
            >
              Closure Verification Queue
            </Tabs.Tab>
          </Tabs.List>

          {/* TAB 1: Escalated Complaints */}
          <Tabs.Panel value="escalated" pt="md">
            <Card withBorder radius="md" p={0}>
              {isLoading ? (
                <Stack align="center" py="xl">
                  <Loader size="md" />
                </Stack>
              ) : escalatedComplaints.length === 0 ? (
                <Stack align="center" py="xl">
                  <Text c="dimmed">No escalated complaints at this time.</Text>
                </Stack>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Location</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Priority</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Worker</Table.Th>
                      <Table.Th>Deadline</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {escalatedComplaints.map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td fw={500}>{c.complaint_id}</Table.Td>
                        <Table.Td>{c.location}</Table.Td>
                        <Table.Td>{c.category_name}</Table.Td>
                        <Table.Td>
                          <PriorityBadge priority={c.priority} />
                        </Table.Td>
                        <Table.Td>
                          <StatusBadge status={c.status} isEscalated={c.is_escalated} />
                        </Table.Td>
                        <Table.Td>{c.assigned_worker_name || "Unassigned"}</Table.Td>
                        <Table.Td c="red">
                          {c.sla_deadline ? dayjs(c.sla_deadline).format("DD MMM, hh:mm A") : "—"}
                        </Table.Td>
                        <Table.Td>
                          <ActionIcon
                            variant="subtle"
                            color="blue"
                            title="Inspect Complaint"
                            onClick={() => setDetailId(c.id)}
                          >
                            <FaEye />
                          </ActionIcon>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          {/* TAB 2: Pending Reopening Requests */}
          <Tabs.Panel value="reopenings" pt="md">
            <Card withBorder radius="md" p={0}>
              {isLoading ? (
                <Stack align="center" py="xl">
                  <Loader size="md" />
                </Stack>
              ) : pendingReopenings.length === 0 ? (
                <Stack align="center" py="xl">
                  <Text c="dimmed">No pending reopening requests awaiting review.</Text>
                </Stack>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Location</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {pendingReopenings.map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td fw={500}>{c.complaint_id}</Table.Td>
                        <Table.Td>{c.location}</Table.Td>
                        <Table.Td>{c.category_name}</Table.Td>
                        <Table.Td>
                          <Badge color="orange">Pending Reopening</Badge>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <ActionIcon
                              variant="subtle"
                              color="blue"
                              onClick={() => setDetailId(c.id)}
                            >
                              <FaEye />
                            </ActionIcon>
                            <Button
                              size="xs"
                              color="teal"
                              variant="light"
                              leftSection={<FaCheckCircle />}
                              onClick={() => handleOpenReview(c, true)}
                            >
                              Approve
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              leftSection={<FaTimesCircle />}
                              onClick={() => handleOpenReview(c, false)}
                            >
                              Deny
                            </Button>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          {/* TAB 3: Closure Verification */}
          <Tabs.Panel value="verifications" pt="md">
            <Card withBorder radius="md" p={0}>
              {isLoading ? (
                <Stack align="center" py="xl">
                  <Loader size="md" />
                </Stack>
              ) : supervisorVerifications.length === 0 ? (
                <Stack align="center" py="xl">
                  <Text c="dimmed">No resolved complaints awaiting supervisor verification.</Text>
                </Stack>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Location</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Resolved At</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {supervisorVerifications.map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td fw={500}>{c.complaint_id}</Table.Td>
                        <Table.Td>{c.location}</Table.Td>
                        <Table.Td>{c.category_name}</Table.Td>
                        <Table.Td>
                          {c.resolved_at ? dayjs(c.resolved_at).format("DD MMM, hh:mm A") : "—"}
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <ActionIcon
                              variant="subtle"
                              color="blue"
                              onClick={() => setDetailId(c.id)}
                            >
                              <FaEye />
                            </ActionIcon>
                            <Button
                              size="xs"
                              color="teal"
                              leftSection={<FaCheckCircle />}
                              onClick={() => setVerifyTargetId(c.id)}
                            >
                              Verify & Close
                            </Button>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>
        </Tabs>

        {/* Modal: Reopening Review */}
        <Modal
          opened={Boolean(reviewTarget)}
          onClose={() => setReviewTarget(null)}
          title={`${reviewApproved ? "Approve" : "Deny"} Reopening Request (${reviewTarget?.complaint_id})`}
        >
          <Stack gap="md">
            <Alert color={reviewApproved ? "teal" : "red"}>
              {reviewApproved
                ? "Approving this request transitions the complaint back to 'In Progress' for further operational resolution."
                : "Denying this request permanently keeps the complaint in 'Closed' status."}
            </Alert>
            <Textarea
              label="Review Remarks"
              placeholder="Provide comments on the review decision..."
              value={reviewRemarks}
              onChange={(e) => setReviewRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setReviewTarget(null)}>
                Cancel
              </Button>
              <Button
                color={reviewApproved ? "teal" : "red"}
                loading={reopenReviewMutation.isPending}
                onClick={handleExecuteReview}
              >
                Confirm {reviewApproved ? "Approval" : "Denial"}
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Verify Close */}
        <Modal
          opened={Boolean(verifyTargetId)}
          onClose={() => setVerifyTargetId(null)}
          title="Supervisor Verification & Closure"
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Confirm that the reported resolution satisfies institutional quality requirements and
              formally close the complaint.
            </Text>
            <Textarea
              label="Verification Remarks (Optional)"
              placeholder="e.g. Work inspected on site; satisfactory."
              value={verifyRemarks}
              onChange={(e) => setVerifyRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setVerifyTargetId(null)}>
                Cancel
              </Button>
              <Button
                color="teal"
                loading={verifyCloseMutation.isPending}
                onClick={handleExecuteVerification}
              >
                Verify & Close
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

export default SupervisorPage;

