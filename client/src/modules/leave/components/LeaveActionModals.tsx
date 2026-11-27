import { useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Divider,
  Grid,
  Group,
  Modal,
  NumberInput,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import {
  useCancelRequest,
  useExtendRequest,
  useResumeLeave,
  useWithdrawRequest,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { LeaveStatusBadge } from "./LeaveStatusBadge";

export function LeaveDetailModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  if (!request) return null;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group justify="space-between" gap="sm">
          <Text fw={700}>Leave Application #{request.application_number}</Text>
          <LeaveStatusBadge status={request.status} />
        </Group>
      }
      size="lg"
      centered
    >
      <Stack gap="sm">
        <Grid>
          <Grid.Col span={6}>
            <Text size="xs" c="dimmed">Leave Type</Text>
            <Text fw={600}>{request.leave_type?.name} ({request.leave_type?.code})</Text>
          </Grid.Col>
          <Grid.Col span={6}>
            <Text size="xs" c="dimmed">Department</Text>
            <Text fw={600}>{request.department || "—"}</Text>
          </Grid.Col>
          <Grid.Col span={6}>
            <Text size="xs" c="dimmed">Leave Duration</Text>
            <Text fw={600}>
              {request.start_date} to {request.end_date} ({request.requested_days} days)
            </Text>
            {request.is_half_day && (
              <Badge size="xs" color="blue" variant="outline" mt={2}>
                Half Day ({request.half_day_period})
              </Badge>
            )}
          </Grid.Col>
          <Grid.Col span={6}>
            <Text size="xs" c="dimmed">Current Stage / Handler</Text>
            <Text fw={600}>{request.current_handler_role || "Complete"}</Text>
          </Grid.Col>
        </Grid>

        <Divider />

        <Box>
          <Text size="xs" c="dimmed">Reason for Leave</Text>
          <Text size="sm">{request.reason}</Text>
        </Box>

        {request.is_station_leave && (
          <Box p="xs" style={{ background: "var(--mantine-color-gray-0)", borderRadius: 6 }}>
            <Text size="xs" fw={700} c="dimmed">Station Leave Details</Text>
            <Text size="xs">Destination: {request.station_destination || "—"}</Text>
            <Text size="xs">
              Departure: {request.station_departure_date || "—"} | Arrival: {request.station_arrival_date || "—"}
            </Text>
          </Box>
        )}

        {(request.address_during_leave || request.contact_number) && (
          <Grid>
            {request.address_during_leave && (
              <Grid.Col span={6}>
                <Text size="xs" c="dimmed">Address During Leave</Text>
                <Text size="xs">{request.address_during_leave}</Text>
              </Grid.Col>
            )}
            {request.contact_number && (
              <Grid.Col span={6}>
                <Text size="xs" c="dimmed">Emergency Contact</Text>
                <Text size="xs">{request.contact_number}</Text>
              </Grid.Col>
            )}
          </Grid>
        )}

        {request.unit_head_recommendation && (
          <Box p="xs" style={{ background: "var(--mantine-color-blue-0)", borderRadius: 6 }}>
            <Text size="xs" fw={700} c="blue">Unit Head Review</Text>
            <Text size="xs">Recommendation: {request.unit_head_recommendation}</Text>
            {request.unit_head_remarks && <Text size="xs">Remarks: {request.unit_head_remarks}</Text>}
          </Box>
        )}

        {request.cancellation_reason && (
          <Box p="xs" style={{ background: "var(--mantine-color-yellow-0)", borderRadius: 6 }}>
            <Text size="xs" fw={700} c="yellow.9">Cancellation Details</Text>
            <Text size="xs">Reason: {request.cancellation_reason}</Text>
            {request.cancellation_requested_at && (
              <Text size="xs">Requested: {new Date(request.cancellation_requested_at).toLocaleString()}</Text>
            )}
          </Box>
        )}

        {request.extension_end_date && (
          <Box p="xs" style={{ background: "var(--mantine-color-grape-0)", borderRadius: 6 }}>
            <Text size="xs" fw={700} c="grape.9">Extension Details</Text>
            <Text size="xs">Extended End Date: {request.extension_end_date} (+{request.extension_days} days)</Text>
            <Text size="xs">Reason: {request.extension_reason || "—"}</Text>
          </Box>
        )}

        {request.is_offline_record && (
          <Box p="xs" style={{ background: "var(--mantine-color-teal-0)", borderRadius: 6 }}>
            <Text size="xs" fw={700} c="teal.9">Offline Sanction Record</Text>
            <Text size="xs">Reference: {request.offline_sanction_reference}</Text>
            <Text size="xs">Sanctioned By: {request.offline_sanctioned_by} on {request.offline_sanctioned_date}</Text>
          </Box>
        )}

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose}>Close</Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function WithdrawModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [remarks, setRemarks] = useState("");
  const withdraw = useWithdrawRequest();

  if (!request) return null;

  function handleSubmit() {
    if (!request) return;
    withdraw.mutate(
      { id: request.id, payload: { remarks } },
      {
        onSuccess: () => {
          notifications.show({
            color: "gray",
            title: "Application Withdrawn",
            message: `Leave application #${request.application_number} has been withdrawn.`,
          });
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Could not withdraw",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Withdraw Leave Application"
      subtitle={`Application #${request.application_number} (${request.start_date} to ${request.end_date})`}
      onSubmit={handleSubmit}
      submitLabel="Confirm Withdrawal"
      submitting={withdraw.isPending}
      danger
      error={withdraw.error}
    >
      <Stack gap="md">
        <Alert color="orange" icon={<FaInfoCircle />}>
          Withdrawing this application is immediate and terminates all active approval processing.
        </Alert>
        <Textarea
          label="Withdrawal Remarks (Optional)"
          placeholder="State why you are withdrawing this application..."
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export function CancelLeaveModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const cancel = useCancelRequest();

  if (!request) return null;

  function handleSubmit() {
    if (!request || !reason.trim()) return;
    cancel.mutate(
      { id: request.id, payload: { reason: reason.trim() } },
      {
        onSuccess: () => {
          notifications.show({
            color: "yellow",
            title: "Cancellation Requested",
            message: `Cancellation for application #${request.application_number} has been submitted for review.`,
          });
          setReason("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Cancellation Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Request Cancellation of Approved Leave"
      subtitle={`Application #${request.application_number} (${request.start_date} to ${request.end_date})`}
      onSubmit={handleSubmit}
      submitLabel="Submit Cancellation Request"
      submitting={cancel.isPending}
      disabled={!reason.trim()}
      disabledReason={!reason.trim() ? "A cancellation reason is required" : undefined}
      error={cancel.error}
    >
      <Stack gap="md">
        <Alert color="blue" icon={<FaInfoCircle />}>
          Approved leave can be cancelled before its start date. The cancellation request will be routed through the approval hierarchy.
        </Alert>
        <Textarea
          label="Reason for Cancellation"
          placeholder="Provide the reason for cancelling this approved leave..."
          required
          minRows={3}
          value={reason}
          onChange={(e) => setReason(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export function ExtendLeaveModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [extensionEndDate, setExtensionEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [substituteId, setSubstituteId] = useState<number | string>("");
  const extend = useExtendRequest();

  if (!request) return null;

  function handleSubmit() {
    if (!request || !extensionEndDate || !reason.trim()) return;
    extend.mutate(
      {
        id: request.id,
        payload: {
          extension_end_date: extensionEndDate,
          reason: reason.trim(),
          substitute_user_id: substituteId ? Number(substituteId) : undefined,
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Extension Requested",
            message: `Leave extension request submitted for approval.`,
          });
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Extension Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Request Leave Extension"
      subtitle={`Current leave period: ${request.start_date} to ${request.end_date}`}
      onSubmit={handleSubmit}
      submitLabel="Submit Extension Request"
      submitting={extend.isPending}
      disabled={!extensionEndDate || !reason.trim()}
      disabledReason={!extensionEndDate || !reason.trim() ? "New end date and reason are required" : undefined}
      error={extend.error}
    >
      <Stack gap="md">
        <TextInput
          type="date"
          label="New Extension End Date"
          min={request.end_date}
          required
          value={extensionEndDate}
          onChange={(e) => setExtensionEndDate(e.currentTarget.value)}
        />
        <Textarea
          label="Reason for Extension"
          required
          placeholder="Reason for extending ongoing leave..."
          value={reason}
          onChange={(e) => setReason(e.currentTarget.value)}
        />
        {request.leave_type?.requires_substitute && (
          <NumberInput
            label="Substitute Employee User ID (Optional)"
            placeholder="User ID of substitute for extended period"
            value={substituteId}
            onChange={(val) => setSubstituteId(val)}
          />
        )}
      </Stack>
    </FormModal>
  );
}

export function ResumeLeaveModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [actualDate, setActualDate] = useState(new Date().toISOString().split("T")[0]);
  const [remarks, setRemarks] = useState("");
  const resume = useResumeLeave();

  if (!request) return null;

  function handleSubmit() {
    if (!request || !actualDate) return;
    resume.mutate(
      {
        id: request.id,
        payload: {
          actual_resumption_date: actualDate,
          remarks,
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Duty Resumption Submitted",
            message: "Resumption report submitted for review by the sanctioning authority.",
          });
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Resumption Submission Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Submit Duty Resumption"
      subtitle={`Leave #${request.application_number} (Approved End: ${request.end_date})`}
      onSubmit={handleSubmit}
      submitLabel="Submit Resumption"
      submitting={resume.isPending}
      disabled={!actualDate}
      disabledReason={!actualDate ? "Actual resumption date is required" : undefined}
      error={resume.error}
    >
      <Stack gap="md">
        <TextInput
          type="date"
          label="Actual Duty Resumption Date"
          required
          value={actualDate}
          onChange={(e) => setActualDate(e.currentTarget.value)}
        />
        <Textarea
          label="Resumption Remarks (Optional)"
          placeholder="Note any early return or delay details..."
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
