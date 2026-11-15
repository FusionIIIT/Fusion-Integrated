import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import dayjs from "dayjs";
import { useState } from "react";
import {
  FaCheck,
  FaClock,
  FaExclamationTriangle,
  FaEye,
  FaSearch,
  FaTimes,
  FaUserCheck,
} from "react-icons/fa";

import {
  useAssignComplaint,
  useCategories,
  useComplaints,
  useManualEscalate,
  useRejectComplaint,
  useResolveComplaint,
  useTriggerSlaCheck,
  useUpdateProgress,
} from "../api/hooks";
import type { ComplaintPriority } from "../api/types";
import { ComplaintDetailModal } from "../components/ComplaintDetailModal";
import { PriorityBadge } from "../components/PriorityBadge";
import { StatusBadge } from "../components/StatusBadge";

export function ComplaintQueuePage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const [detailId, setDetailId] = useState<number | null>(null);

  // Operational Action Targets
  const [assignTarget, setAssignTarget] = useState<any | null>(null);
  const [workerName, setWorkerName] = useState("");
  const [workerId, setWorkerId] = useState("");
  const [assignPriority, setAssignPriority] = useState<ComplaintPriority>("medium");
  const [assignCategory, setAssignCategory] = useState<string | null>(null);
  const [assignRemarks, setAssignRemarks] = useState("");

  const [progressTargetId, setProgressTargetId] = useState<number | null>(null);
  const [progressNotes, setProgressNotes] = useState("");

  const [resolveTargetId, setResolveTargetId] = useState<number | null>(null);
  const [resolutionDetails, setResolutionDetails] = useState("");

  const [rejectTargetId, setRejectTargetId] = useState<number | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  const [escalateTargetId, setEscalateTargetId] = useState<number | null>(null);
  const [escalateRemarks, setEscalateRemarks] = useState("");

  const [slaResult, setSlaResult] = useState<string | null>(null);

  // Hooks
  const { data: complaints, isLoading } = useComplaints({
    search: search.trim() || undefined,
    status: statusFilter || undefined,
    priority: priorityFilter || undefined,
    category_id: categoryFilter || undefined,
  });
  const { data: categories } = useCategories();

  const assignMutation = useAssignComplaint(assignTarget?.id || 0);
  const progressMutation = useUpdateProgress(progressTargetId || 0);
  const resolveMutation = useResolveComplaint(resolveTargetId || 0);
  const rejectMutation = useRejectComplaint(rejectTargetId || 0);
  const escalateMutation = useManualEscalate(escalateTargetId || 0);
  const slaCheckMutation = useTriggerSlaCheck();

  const handleOpenAssign = (c: any) => {
    setAssignTarget(c);
    setWorkerName(c.assigned_worker_name || "");
    setAssignPriority(c.priority || "medium");
    setAssignCategory(String(c.category_id));
    setAssignRemarks("");
  };

  const handleExecuteAssign = async () => {
    if (!assignTarget) return;
    try {
      await assignMutation.mutateAsync({
        worker_id: workerId ? Number(workerId) : undefined,
        worker_name: workerName.trim(),
        priority: assignPriority,
        category_id: assignCategory ? Number(assignCategory) : undefined,
        remarks: assignRemarks.trim(),
      });
      setAssignTarget(null);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to assign complaint.");
    }
  };

  const handleExecuteProgress = async () => {
    if (!progressTargetId || !progressNotes.trim()) return;
    try {
      await progressMutation.mutateAsync({ progress_notes: progressNotes.trim() });
      setProgressTargetId(null);
      setProgressNotes("");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to update progress.");
    }
  };

  const handleExecuteResolve = async () => {
    if (!resolveTargetId || !resolutionDetails.trim()) return;
    try {
      await resolveMutation.mutateAsync({ resolution_details: resolutionDetails.trim() });
      setResolveTargetId(null);
      setResolutionDetails("");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to resolve complaint.");
    }
  };

  const handleExecuteReject = async () => {
    if (!rejectTargetId || !rejectionReason.trim()) return;
    try {
      await rejectMutation.mutateAsync({ rejection_reason: rejectionReason.trim() });
      setRejectTargetId(null);
      setRejectionReason("");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to reject complaint.");
    }
  };

  const handleExecuteEscalate = async () => {
    if (!escalateTargetId || !escalateRemarks.trim()) return;
    try {
      await escalateMutation.mutateAsync({ remarks: escalateRemarks.trim() });
      setEscalateTargetId(null);
      setEscalateRemarks("");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to escalate complaint.");
    }
  };

  const handleRunSlaCheck = async () => {
    try {
      const res = await slaCheckMutation.mutateAsync();
      setSlaResult(
        `Autonomous SLA Check Complete: ${res.escalated_count} complaints escalated, ${res.reminders_sent} reminders sent.`
      );
    } catch (err: any) {
      alert(err?.message || "Failed to run SLA check.");
    }
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Title order={2}>Complaint Queue</Title>
            <Text c="dimmed" size="sm">
              Operational triage, assignment, progress updates, and resolution processing.
            </Text>
          </div>
          <Button
            variant="light"
            color="orange"
            leftSection={<FaClock />}
            loading={slaCheckMutation.isPending}
            onClick={handleRunSlaCheck}
          >
            Run SLA Audit
          </Button>
        </Group>

        {slaResult && (
          <Alert color="blue" onClose={() => setSlaResult(null)} withCloseButton>
            {slaResult}
          </Alert>
        )}

        {/* Filters */}
        <Card withBorder p="sm" radius="md">
          <Group grow>
            <TextInput
              placeholder="Search ID, location, or description..."
              leftSection={<FaSearch />}
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
            />
            <Select
              placeholder="Status"
              clearable
              value={statusFilter}
              onChange={setStatusFilter}
              data={[
                { value: "submitted", label: "Submitted" },
                { value: "in_progress", label: "In Progress" },
                { value: "resolved", label: "Resolved" },
                { value: "closed", label: "Closed" },
                { value: "rejected", label: "Rejected" },
              ]}
            />
            <Select
              placeholder="Priority"
              clearable
              value={priorityFilter}
              onChange={setPriorityFilter}
              data={[
                { value: "high", label: "High" },
                { value: "medium", label: "Medium" },
                { value: "low", label: "Low" },
              ]}
            />
            <Select
              placeholder="Category"
              clearable
              value={categoryFilter}
              onChange={setCategoryFilter}
              data={categories?.map((cat) => ({ value: String(cat.id), label: cat.name })) || []}
            />
          </Group>
        </Card>

        {/* Complaints Table */}
        <Card withBorder radius="md" p={0}>
          {isLoading ? (
            <Stack align="center" py="xl">
              <Loader size="md" />
            </Stack>
          ) : !complaints || complaints.length === 0 ? (
            <Stack align="center" py="xl">
              <Text c="dimmed">No complaints matching the specified filters.</Text>
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
                {complaints.map((c) => (
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
                    <Table.Td>
                      {c.sla_deadline ? dayjs(c.sla_deadline).format("DD MMM, hh:mm A") : "—"}
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4}>
                        <ActionIcon
                          variant="subtle"
                          color="blue"
                          title="View Details"
                          onClick={() => setDetailId(c.id)}
                        >
                          <FaEye />
                        </ActionIcon>

                        {/* Handlers can assign submitted / in-progress complaints */}
                        {(c.status === "submitted" || c.status === "in_progress") && (
                          <ActionIcon
                            variant="subtle"
                            color="indigo"
                            title="Assign Worker / Setup"
                            onClick={() => handleOpenAssign(c)}
                          >
                            <FaUserCheck />
                          </ActionIcon>
                        )}

                        {/* Update progress */}
                        {(c.status === "submitted" || c.status === "in_progress") && (
                          <Button
                            size="compact-xs"
                            variant="light"
                            color="blue"
                            onClick={() => setProgressTargetId(c.id)}
                          >
                            Progress
                          </Button>
                        )}

                        {/* Resolve */}
                        {(c.status === "submitted" || c.status === "in_progress") && (
                          <ActionIcon
                            variant="subtle"
                            color="teal"
                            title="Resolve Complaint"
                            onClick={() => setResolveTargetId(c.id)}
                          >
                            <FaCheck />
                          </ActionIcon>
                        )}

                        {/* Reject */}
                        {(c.status === "submitted" || c.status === "in_progress") && (
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            title="Reject Complaint"
                            onClick={() => setRejectTargetId(c.id)}
                          >
                            <FaTimes />
                          </ActionIcon>
                        )}

                        {/* Manual Escalate */}
                        {!c.is_escalated &&
                          c.status !== "resolved" &&
                          c.status !== "closed" &&
                          c.status !== "rejected" && (
                            <ActionIcon
                              variant="subtle"
                              color="red"
                              title="Manual Escalation"
                              onClick={() => setEscalateTargetId(c.id)}
                            >
                              <FaExclamationTriangle />
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

        {/* Modal: Assign */}
        <Modal
          opened={Boolean(assignTarget)}
          onClose={() => setAssignTarget(null)}
          title={`Assign & Prioritize Complaint (${assignTarget?.complaint_id})`}
        >
          <Stack gap="md">
            <TextInput
              label="Assigned Worker Name"
              placeholder="e.g. Ramesh Kumar (Electrician)"
              value={workerName}
              onChange={(e) => setWorkerName(e.currentTarget.value)}
            />
            <TextInput
              label="Worker User ID (Optional)"
              placeholder="e.g. 104"
              value={workerId}
              onChange={(e) => setWorkerId(e.currentTarget.value)}
            />
            <Select
              label="Complaint Priority"
              value={assignPriority}
              onChange={(val) => setAssignPriority((val as ComplaintPriority) || "medium")}
              data={[
                { value: "low", label: "Low (72h SLA)" },
                { value: "medium", label: "Medium (48h SLA)" },
                { value: "high", label: "High (24h SLA)" },
              ]}
            />
            <Select
              label="Category"
              value={assignCategory}
              onChange={setAssignCategory}
              data={categories?.map((cat) => ({ value: String(cat.id), label: cat.name })) || []}
            />
            <Textarea
              label="Handling Remarks"
              placeholder="Add internal dispatch notes..."
              value={assignRemarks}
              onChange={(e) => setAssignRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setAssignTarget(null)}>
                Cancel
              </Button>
              <Button loading={assignMutation.isPending} onClick={handleExecuteAssign}>
                Save Assignment
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Progress */}
        <Modal
          opened={Boolean(progressTargetId)}
          onClose={() => setProgressTargetId(null)}
          title="Update Complaint Progress"
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Logging progress notes transitions newly submitted complaints to 'In Progress' and
              updates the audit trail.
            </Text>
            <Textarea
              label="Progress Notes"
              placeholder="e.g. Technician dispatched with replacement ballast..."
              required
              minRows={3}
              value={progressNotes}
              onChange={(e) => setProgressNotes(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setProgressTargetId(null)}>
                Cancel
              </Button>
              <Button loading={progressMutation.isPending} onClick={handleExecuteProgress}>
                Update Progress
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Resolve */}
        <Modal
          opened={Boolean(resolveTargetId)}
          onClose={() => setResolveTargetId(null)}
          title="Resolve Complaint"
        >
          <Stack gap="md">
            <Textarea
              label="Resolution Details"
              placeholder="Describe work performed and repairs made..."
              required
              minRows={3}
              value={resolutionDetails}
              onChange={(e) => setResolutionDetails(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setResolveTargetId(null)}>
                Cancel
              </Button>
              <Button color="teal" loading={resolveMutation.isPending} onClick={handleExecuteResolve}>
                Mark as Resolved
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Reject */}
        <Modal
          opened={Boolean(rejectTargetId)}
          onClose={() => setRejectTargetId(null)}
          title="Reject Complaint"
        >
          <Stack gap="md">
            <Alert color="red" title="Mandatory Rejection Reason">
              Institutional policy requires an explicit explanation for rejecting a complaint.
            </Alert>
            <Textarea
              label="Rejection Reason"
              placeholder="e.g. Duplicate submission or request outside hostel maintenance scope..."
              required
              minRows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setRejectTargetId(null)}>
                Cancel
              </Button>
              <Button color="red" loading={rejectMutation.isPending} onClick={handleExecuteReject}>
                Confirm Rejection
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Escalate */}
        <Modal
          opened={Boolean(escalateTargetId)}
          onClose={() => setEscalateTargetId(null)}
          title="Manual Complaint Escalation"
        >
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Manually escalate this unresolved complaint to the Complaint Supervisor for oversight.
            </Text>
            <Textarea
              label="Escalation Remarks"
              placeholder="Explain reasons for escalating..."
              required
              minRows={3}
              value={escalateRemarks}
              onChange={(e) => setEscalateRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEscalateTargetId(null)}>
                Cancel
              </Button>
              <Button
                color="red"
                loading={escalateMutation.isPending}
                onClick={handleExecuteEscalate}
              >
                Escalate Complaint
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

export default ComplaintQueuePage;

