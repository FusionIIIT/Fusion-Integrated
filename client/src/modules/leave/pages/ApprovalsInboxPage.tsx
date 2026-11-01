import {
  Badge,
  Box,
  Button,
  Group,
  Loader,
  Modal,
  Paper,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import React, { useEffect, useState } from "react";
import { leaveApi } from "../api";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";
import { PrintModal } from "../components/PrintModal";
import type { LeaveRequest } from "../types";

export const ApprovalsInboxPage: React.FC = () => {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string | null>("all");

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [reviewModalOpened, setReviewModalOpened] = useState(false);
  const [unitHeadDecision, setUnitHeadDecision] = useState<string>("RECOMMENDED");
  const [sanctionApprove, setSanctionApprove] = useState<boolean>(true);
  const [reviewRemarks, setReviewRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [printOpened, setPrintOpened] = useState(false);

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const data = await leaveApi.getApprovals();
      setRequests(data);
    } catch {
      notifications.show({ title: "Error", message: "Failed to load approval inbox.", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const filteredRequests = requests.filter((r) => {
    if (activeTab === "unit_head") return r.status === "PENDING_UNIT_HEAD";
    if (activeTab === "sanction") return r.status === "PENDING_SANCTION";
    if (activeTab === "cancellation") return r.status === "CANCEL_REQUESTED";
    if (activeTab === "resumption") return r.status === "RESUMED";
    return true;
  });

  const handleUnitHeadSubmit = async () => {
    if (!selectedReq) return;
    setSubmitting(true);
    try {
      await leaveApi.reviewUnitHead(selectedReq.id, unitHeadDecision, reviewRemarks);
      notifications.show({ title: "Reviewed", message: "Unit head review recorded successfully.", color: "teal" });
      setReviewModalOpened(false);
      setReviewRemarks("");
      loadApprovals();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Review failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSanctionSubmit = async (approved: boolean) => {
    if (!selectedReq) return;
    setSubmitting(true);
    try {
      await leaveApi.decideSanction(selectedReq.id, approved, reviewRemarks);
      notifications.show({
        title: approved ? "Approved" : "Rejected",
        message: `Sanctioning decision recorded: ${approved ? "APPROVED" : "REJECTED"}.`,
        color: approved ? "teal" : "red",
      });
      setReviewModalOpened(false);
      setReviewRemarks("");
      loadApprovals();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Decision failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleResumptionSubmit = async () => {
    if (!selectedReq) return;
    setSubmitting(true);
    try {
      await leaveApi.reviewResumption(selectedReq.id, reviewRemarks);
      notifications.show({ title: "Reviewed", message: "Resumption reviewed and balance synchronized.", color: "teal" });
      setReviewModalOpened(false);
      setReviewRemarks("");
      loadApprovals();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Resumption review failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box p="md" maw={1200} mx="auto">
      <Title order={2} mb="xs">
        Leave Approvals & Recommendations Inbox
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        Review, recommend, and sanction applications from employees in your department or authority scope
        (BR-EL-016 through BR-EL-020).
      </Text>

      <Tabs value={activeTab} onChange={setActiveTab} mb="md">
        <Tabs.List>
          <Tabs.Tab value="all">All Pending ({requests.length})</Tabs.Tab>
          <Tabs.Tab value="unit_head">
            Unit Head ({requests.filter((r) => r.status === "PENDING_UNIT_HEAD").length})
          </Tabs.Tab>
          <Tabs.Tab value="sanction">
            Higher Sanction ({requests.filter((r) => r.status === "PENDING_SANCTION").length})
          </Tabs.Tab>
          <Tabs.Tab value="cancellation">
            Cancellations ({requests.filter((r) => r.status === "CANCEL_REQUESTED").length})
          </Tabs.Tab>
          <Tabs.Tab value="resumption">
            Resumptions ({requests.filter((r) => r.status === "RESUMED").length})
          </Tabs.Tab>
        </Tabs.List>
      </Tabs>

      <Paper withBorder shadow="xs" radius="md" p="md">
        {loading ? (
          <Group justify="center" p="xl">
            <Loader size="md" />
          </Group>
        ) : filteredRequests.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            No pending applications in this category.
          </Text>
        ) : (
          <Table.ScrollContainer minWidth={900}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Applicant</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Workflow State</Table.Th>
                  <Table.Th>Station Leave</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filteredRequests.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td>#{req.id}</Table.Td>
                    <Table.Td>User #{req.user_id}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline">{req.category}</Badge>
                    </Table.Td>
                    <Table.Td>
                      {req.start_date} to {req.end_date}
                    </Table.Td>
                    <Table.Td>{req.computed_days}</Table.Td>
                    <Table.Td>
                      <LeaveStatusBadge status={req.status} />
                    </Table.Td>
                    <Table.Td>
                      {req.station_leave ? (
                        <Badge color="blue" size="xs">
                          Yes ({req.station_address || "Out of station"})
                        </Badge>
                      ) : (
                        <Text size="xs" c="dimmed">
                          No
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          variant="light"
                          onClick={() => {
                            setSelectedReq(req);
                            setPrintOpened(true);
                          }}
                        >
                          Details
                        </Button>
                        <Button
                          size="xs"
                          color="teal"
                          onClick={() => {
                            setSelectedReq(req);
                            if (req.category === "CL" || req.category === "RH") {
                              setUnitHeadDecision("APPROVE");
                            } else {
                              setUnitHeadDecision("RECOMMENDED");
                            }
                            setReviewModalOpened(true);
                          }}
                        >
                          Review / Action
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Paper>

      {/* Review Modal */}
      <Modal
        opened={reviewModalOpened}
        onClose={() => setReviewModalOpened(false)}
        size="md"
        title={`Review Application #${selectedReq?.id} (User #${selectedReq?.user_id})`}
      >
        <Stack gap="md">
          <Text size="sm">
            Category: <b>{selectedReq?.category}</b> | Period: {selectedReq?.start_date} to{" "}
            {selectedReq?.end_date} ({selectedReq?.computed_days} days)
          </Text>
          <Text size="sm" c="dimmed">
            Reason: &quot;{selectedReq?.reason}&quot;
          </Text>

          {selectedReq?.status === "PENDING_UNIT_HEAD" && (
            <>
              {selectedReq.category === "CL" || selectedReq.category === "RH" ? (
                <Select
                  label="Unit Head Final Decision (BR-EL-016)"
                  data={[
                    { value: "APPROVE", label: "Approve Leave (Final)" },
                    { value: "REJECT", label: "Reject Leave (Final)" },
                  ]}
                  value={unitHeadDecision}
                  onChange={(v) => setUnitHeadDecision(v || "APPROVE")}
                />
              ) : (
                <Select
                  label="Unit Head Recommendation (BR-EL-017)"
                  description="For SCL/EL/COL/VL, Unit Head records recommendation before forwarding to Sanctioning Authority."
                  data={[
                    { value: "RECOMMENDED", label: "Recommended" },
                    { value: "NOT_RECOMMENDED", label: "Not Recommended" },
                  ]}
                  value={unitHeadDecision}
                  onChange={(v) => setUnitHeadDecision(v || "RECOMMENDED")}
                />
              )}
              <Textarea
                label="Unit Head Remarks"
                placeholder="Optional remarks..."
                value={reviewRemarks}
                onChange={(e) => setReviewRemarks(e.target.value)}
              />
              <Group justify="flex-end">
                <Button variant="default" onClick={() => setReviewModalOpened(false)}>
                  Cancel
                </Button>
                <Button color="teal" loading={submitting} onClick={handleUnitHeadSubmit}>
                  Submit Review
                </Button>
              </Group>
            </>
          )}

          {selectedReq?.status === "PENDING_SANCTION" && (
            <>
              <Text size="sm">
                Unit Head Recommendation: <b>{selectedReq.unit_head_recommendation || "N/A"}</b> (
                {selectedReq.unit_head_remarks || "No remarks"})
              </Text>
              <Textarea
                label="Sanctioning Authority Remarks"
                placeholder="Remarks for approval/rejection..."
                value={reviewRemarks}
                onChange={(e) => setReviewRemarks(e.target.value)}
              />
              <Group justify="flex-end">
                <Button
                  color="red"
                  variant="light"
                  loading={submitting}
                  onClick={() => handleSanctionSubmit(false)}
                >
                  Reject Application
                </Button>
                <Button color="teal" loading={submitting} onClick={() => handleSanctionSubmit(true)}>
                  Approve Application
                </Button>
              </Group>
            </>
          )}

          {selectedReq?.status === "CANCEL_REQUESTED" && (
            <>
              <Text size="sm" c="orange">
                Applicant Cancellation Justification: &quot;{selectedReq.cancellation_reason}&quot;
              </Text>
              <Textarea
                label="Cancellation Decision Remarks"
                placeholder="Remarks..."
                value={reviewRemarks}
                onChange={(e) => setReviewRemarks(e.target.value)}
              />
              <Group justify="flex-end">
                <Button
                  color="gray"
                  variant="default"
                  loading={submitting}
                  onClick={() => handleSanctionSubmit(false)}
                >
                  Reject Cancellation (Keep Approved)
                </Button>
                <Button color="orange" loading={submitting} onClick={() => handleSanctionSubmit(true)}>
                  Approve Cancellation (Restore Balance)
                </Button>
              </Group>
            </>
          )}

          {selectedReq?.status === "RESUMED" && (
            <>
              <Text size="sm">
                Actual Resumption Date: <b>{selectedReq.resumption_date}</b> (Approved was{" "}
                {selectedReq.end_date})
              </Text>
              <Textarea
                label="Resumption Review Remarks"
                placeholder="Remarks..."
                value={reviewRemarks}
                onChange={(e) => setReviewRemarks(e.target.value)}
              />
              <Group justify="flex-end">
                <Button variant="default" onClick={() => setReviewModalOpened(false)}>
                  Cancel
                </Button>
                <Button color="teal" loading={submitting} onClick={handleResumptionSubmit}>
                  Confirm Resumption Review & Synchronize
                </Button>
              </Group>
            </>
          )}
        </Stack>
      </Modal>

      <PrintModal
        opened={printOpened}
        onClose={() => setPrintOpened(false)}
        leave={selectedReq}
      />
    </Box>
  );
};

export default ApprovalsInboxPage;
