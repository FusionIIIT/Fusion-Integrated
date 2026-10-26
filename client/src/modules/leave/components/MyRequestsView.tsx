import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { FaCalendarPlus, FaEye, FaPlus, FaSignOutAlt, FaTimes, FaUndo } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import {
  useApplications,
  useCancelApplication,
  useExtendApplication,
  useResumptionSubmit,
  useWithdrawApplication,
} from "../api/hooks";
import type { LeaveApplication } from "../api/types";
import { ApplicationDetailModal } from "./ApplicationDetailModal";

const STATUS_COLORS: Record<string, string> = {
  APPROVED: "teal",
  REJECTED: "red",
  CANCELLED: "gray",
  WITHDRAWN: "gray",
  AWAITING_SUBSTITUTE: "orange",
  SUBSTITUTE_DECLINED: "red",
  AWAITING_UNIT_HEAD: "blue",
  AWAITING_ESTABLISHMENT: "violet",
  AWAITING_SANCTION: "grape",
  AWAITING_CANCELLATION: "yellow",
};

export function MyRequestsView() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);

  // Action Modals State
  const [cancelModalId, setCancelModalId] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  const [extendModalApp, setExtendModalApp] = useState<LeaveApplication | null>(null);
  const [extendEndDate, setExtendEndDate] = useState("");
  const [extendReason, setExtendReason] = useState("");

  const [resumeModalApp, setResumeModalApp] = useState<LeaveApplication | null>(null);
  const [actualResumeDate, setActualResumeDate] = useState("");
  const [resumeRemarks, setResumeRemarks] = useState("");

  const filterParams = statusFilter !== "ALL" ? { status: statusFilter } : undefined;
  const { data: applications, isPending } = useApplications(filterParams);

  const withdrawMutation = useWithdrawApplication();
  const cancelMutation = useCancelApplication();
  const extendMutation = useExtendApplication();
  const resumeMutation = useResumptionSubmit();

  const handleWithdraw = async (id: number) => {
    if (!window.confirm("Are you sure you want to withdraw this application?")) return;
    try {
      await withdrawMutation.mutateAsync(id);
      notifications.show({ title: "Application Withdrawn", message: "Application has been withdrawn.", color: "blue" });
    } catch (e) {
      notifications.show({ title: "Withdraw Failed", message: errorMessage(e), color: "red" });
    }
  };

  const handleCancelSubmit = async () => {
    if (!cancelModalId || !cancelReason.trim()) return;
    try {
      await cancelMutation.mutateAsync({ id: cancelModalId, reason: cancelReason });
      notifications.show({ title: "Cancellation Requested", message: "Cancellation request submitted for review.", color: "green" });
      setCancelModalId(null);
      setCancelReason("");
    } catch (e) {
      notifications.show({ title: "Cancellation Failed", message: errorMessage(e), color: "red" });
    }
  };

  const handleExtendSubmit = async () => {
    if (!extendModalApp || !extendEndDate || !extendReason.trim()) return;
    try {
      await extendMutation.mutateAsync({
        id: extendModalApp.id,
        new_end_date: extendEndDate,
        reason: extendReason,
      });
      notifications.show({ title: "Extension Requested", message: "Extension application submitted.", color: "green" });
      setExtendModalApp(null);
      setExtendEndDate("");
      setExtendReason("");
    } catch (e) {
      notifications.show({ title: "Extension Failed", message: errorMessage(e), color: "red" });
    }
  };

  const handleResumeSubmit = async () => {
    if (!resumeModalApp || !actualResumeDate) return;
    try {
      await resumeMutation.mutateAsync({
        id: resumeModalApp.id,
        actual_resumption_date: actualResumeDate,
        remarks: resumeRemarks,
      });
      notifications.show({ title: "Resumption Submitted", message: "Resumption of duty submitted for review.", color: "green" });
      setResumeModalApp(null);
      setActualResumeDate("");
      setResumeRemarks("");
    } catch (e) {
      notifications.show({ title: "Resumption Failed", message: errorMessage(e), color: "red" });
    }
  };

  const today = new Date().toISOString().slice(0, 10);

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center">
        <Select
          label="Filter by Status"
          value={statusFilter}
          onChange={(v) => setStatusFilter(v || "ALL")}
          data={[
            { value: "ALL", label: "All Requests" },
            { value: "AWAITING_UNIT_HEAD", label: "Awaiting Unit Head" },
            { value: "AWAITING_SANCTION", label: "Awaiting Sanction" },
            { value: "APPROVED", label: "Approved" },
            { value: "REJECTED", label: "Rejected" },
            { value: "CANCELLED", label: "Cancelled" },
          ]}
        />
        <Button leftSection={<FaPlus />} onClick={() => navigate("/leave/apply")}>
          Apply Leave
        </Button>
      </Group>

      <Card withBorder padding="md" radius="md">
        {isPending ? (
          <Center py="xl"><Loader size="md" /></Center>
        ) : !applications || applications.length === 0 ? (
          <Center py="xl"><Text c="dimmed">No leave requests found.</Text></Center>
        ) : (
          <Table.ScrollContainer minWidth={800}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Period</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Substitute</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {applications.map((app) => {
                  const isPendingState = [
                    "AWAITING_SUBSTITUTE",
                    "SUBSTITUTE_DECLINED",
                    "AWAITING_UNIT_HEAD",
                    "AWAITING_ESTABLISHMENT",
                    "AWAITING_SANCTION",
                  ].includes(app.status);

                  const isApproved = app.status === "APPROVED";
                  const canCancel = isApproved && app.start_date > today;
                  const canExtend = isApproved && ["EL", "COL", "VL"].includes(app.leave_type) && app.start_date <= today && today <= app.end_date;
                  const canResume = isApproved && ["EL", "COL", "VL"].includes(app.leave_type) && app.resumption_status === "NONE";

                  return (
                    <Table.Tr key={app.id}>
                      <Table.Td>#{app.id}</Table.Td>
                      <Table.Td><Badge variant="outline">{app.leave_type}</Badge></Table.Td>
                      <Table.Td>{app.start_date} → {app.end_date}</Table.Td>
                      <Table.Td>{app.days_count} ({app.half_day_type})</Table.Td>
                      <Table.Td>
                        <Badge color={STATUS_COLORS[app.status] ?? "gray"}>{app.status}</Badge>
                      </Table.Td>
                      <Table.Td>
                        {app.substitute_user_id ? `User #${app.substitute_user_id} (${app.substitute_status})` : "None"}
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Tooltip label="View Audit History">
                            <ActionIcon variant="subtle" color="blue" onClick={() => setSelectedAppId(app.id)}>
                              <FaEye />
                            </ActionIcon>
                          </Tooltip>

                          {isPendingState && (
                            <Tooltip label="Withdraw Request">
                              <ActionIcon variant="subtle" color="red" onClick={() => handleWithdraw(app.id)}>
                                <FaUndo />
                              </ActionIcon>
                            </Tooltip>
                          )}

                          {canCancel && (
                            <Tooltip label="Cancel Approved Leave">
                              <ActionIcon variant="subtle" color="orange" onClick={() => setCancelModalId(app.id)}>
                                <FaTimes />
                              </ActionIcon>
                            </Tooltip>
                          )}

                          {canExtend && (
                            <Tooltip label="Extend Ongoing Leave">
                              <ActionIcon variant="subtle" color="teal" onClick={() => setExtendModalApp(app)}>
                                <FaCalendarPlus />
                              </ActionIcon>
                            </Tooltip>
                          )}

                          {canResume && (
                            <Tooltip label="Submit Resumption of Duty">
                              <ActionIcon variant="subtle" color="grape" onClick={() => setResumeModalApp(app)}>
                                <FaSignOutAlt />
                              </ActionIcon>
                            </Tooltip>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>

      <ApplicationDetailModal applicationId={selectedAppId} onClose={() => setSelectedAppId(null)} />

      {/* Cancellation Modal */}
      <Modal opened={!!cancelModalId} onClose={() => setCancelModalId(null)} title="Request Leave Cancellation" centered>
        <Stack gap="md">
          <Text size="sm">
            You are requesting cancellation for approved Leave #{cancelModalId}. Reason is required.
          </Text>
          <Textarea
            label="Reason for Cancellation"
            required
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalId(null)}>Close</Button>
            <Button color="red" onClick={handleCancelSubmit} loading={cancelMutation.isPending}>
              Submit Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Extension Modal */}
      <Modal opened={!!extendModalApp} onClose={() => setExtendModalApp(null)} title="Extend Ongoing Leave" centered>
        <Stack gap="md">
          <Text size="sm">
            Extend Leave #{extendModalApp?.id} ({extendModalApp?.leave_type}) current end date: {extendModalApp?.end_date}
          </Text>
          <TextInput
            label="New End Date"
            type="date"
            required
            value={extendEndDate}
            onChange={(e) => setExtendEndDate(e.target.value)}
          />
          <Textarea
            label="Reason for Extension"
            required
            value={extendReason}
            onChange={(e) => setExtendReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setExtendModalApp(null)}>Close</Button>
            <Button color="teal" onClick={handleExtendSubmit} loading={extendMutation.isPending}>
              Request Extension
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resumption Modal */}
      <Modal opened={!!resumeModalApp} onClose={() => setResumeModalApp(null)} title="Submit Resumption of Duty" centered>
        <Stack gap="md">
          <Text size="sm">
            Formal return from Leave #{resumeModalApp?.id} ({resumeModalApp?.leave_type}).
            Approved period was {resumeModalApp?.start_date} to {resumeModalApp?.end_date}.
          </Text>
          <TextInput
            label="Actual Resumption Date"
            type="date"
            required
            value={actualResumeDate}
            onChange={(e) => setActualResumeDate(e.target.value)}
          />
          <Textarea
            label="Remarks (optional)"
            value={resumeRemarks}
            onChange={(e) => setResumeRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumeModalApp(null)}>Close</Button>
            <Button color="grape" onClick={handleResumeSubmit} loading={resumeMutation.isPending}>
              Submit Resumption
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
