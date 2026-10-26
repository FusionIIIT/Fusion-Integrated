import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Timeline,
} from "@mantine/core";
import { FaEye, FaTimes, FaUndo } from "react-icons/fa";
import { Link } from "react-router-dom";
import { Column, DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useCancellationRequestMutation,
  useMyApplications,
  useResumptionSubmitMutation,
  useWithdrawMutation,
} from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function MyApplicationsPage() {
  const { data: applications = [], isLoading, refetch } = useMyApplications();
  const withdrawMutation = useWithdrawMutation();
  const cancelMutation = useCancellationRequestMutation();
  const resumeMutation = useResumptionSubmitMutation();

  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);
  const [cancelModalApp, setCancelModalApp] = useState<LeaveApplication | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  const [resumeModalApp, setResumeModalApp] = useState<LeaveApplication | null>(null);
  const [actualResumeDate, setActualResumeDate] = useState("");
  const [resumeDiffReason, setResumeDiffReason] = useState("");

  const handleWithdraw = async (appId: number) => {
    if (!window.confirm("Are you sure you want to withdraw this application?")) return;
    await withdrawMutation.mutateAsync(appId);
    refetch();
  };

  const handleCancelSubmit = async () => {
    if (!cancelModalApp || !cancelReason.trim()) return;
    await cancelMutation.mutateAsync({
      applicationId: cancelModalApp.id,
      reason: cancelReason,
    });
    setCancelModalApp(null);
    setCancelReason("");
    refetch();
  };

  const handleResumeSubmit = async () => {
    if (!resumeModalApp || !actualResumeDate) return;
    await resumeMutation.mutateAsync({
      applicationId: resumeModalApp.id,
      actual_resumption_date: actualResumeDate,
      reason_for_difference: resumeDiffReason,
    });
    setResumeModalApp(null);
    setActualResumeDate("");
    setResumeDiffReason("");
    refetch();
  };

  const columns: Column<LeaveApplication>[] = [
    {
      key: "id",
      header: "ID",
      render: (r) => <Text fw={500}>#{r.id}</Text>,
    },
    {
      key: "type",
      header: "Category",
      render: (r) => (
        <Group gap="xs">
          <Badge variant="outline">{r.leave_type_code}</Badge>
          <Text size="sm">{r.leave_type_name}</Text>
        </Group>
      ),
    },
    {
      key: "dates",
      header: "Period",
      render: (r) => (
        <Text size="sm">
          {r.start_date} to {r.end_date}
          {r.is_half_day && <Badge size="xs" ml={4}>Half-Day ({r.half_day_period})</Badge>}
        </Text>
      ),
    },
    {
      key: "days",
      header: "Days",
      render: (r) => <Text fw={600}>{r.days}d</Text>,
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (r) => {
        const isPending = [
          "AWAITING_SUBSTITUTE",
          "APPLICANT_ACTION_REQUIRED",
          "AWAITING_UNIT_HEAD",
          "AWAITING_ESTABLISHMENT",
          "AWAITING_SANCTION",
          "AWAITING_DIRECTOR_SELF_SANCTION",
        ].includes(r.status);

        const isApproved = r.status === "APPROVED";
        const today = new Date().toISOString().split("T")[0];
        const canCancelPreStart = isApproved && r.start_date > today;
        const canResume = isApproved && ["EL", "COL", "VL"].includes(r.leave_type_code);

        return (
          <Group gap="xs" justify="flex-end">
            <ActionIcon
              variant="subtle"
              color="gray"
              title="View Details & Audit Trail"
              onClick={() => setSelectedApp(r)}
            >
              <FaEye size={14} />
            </ActionIcon>

            {isPending && (
              <Button
                size="xs"
                variant="subtle"
                color="red"
                leftSection={<FaTimes size={12} />}
                onClick={() => handleWithdraw(r.id)}
                loading={withdrawMutation.isPending}
              >
                Withdraw
              </Button>
            )}

            {canCancelPreStart && (
              <Button
                size="xs"
                variant="subtle"
                color="orange"
                onClick={() => setCancelModalApp(r)}
              >
                Cancel
              </Button>
            )}

            {canResume && (
              <Button
                size="xs"
                variant="subtle"
                color="teal"
                leftSection={<FaUndo size={12} />}
                onClick={() => setResumeModalApp(r)}
              >
                Resume Duty
              </Button>
            )}
          </Group>
        );
      },
    },
  ];

  return (
    <div>
      <PageHeader
        title="My Leave Applications"
        subtitle="Track submitted leave requests, approvals, withdrawal, and duty resumption"
        action={
          <Button component={Link} to="/leave/apply">
            Apply for Leave
          </Button>
        }
      />

      <DataTable
        rows={applications}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No leave applications found",
          description: "You have not submitted any leave requests yet.",
        }}
      />

      {/* Details & Audit Trail Modal */}
      <Modal
        opened={Boolean(selectedApp)}
        onClose={() => setSelectedApp(null)}
        title={<Text fw={600}>Leave Application #{selectedApp?.id} Details</Text>}
        size="lg"
      >
        {selectedApp && (
          <Stack gap="md">
            <Card withBorder padding="sm">
              <Grid>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Category</Text>
                  <Text fw={500}>{selectedApp.leave_type_code} — {selectedApp.leave_type_name}</Text>
                </Grid.Col>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Chargeable Days</Text>
                  <Text fw={500}>{selectedApp.days} days</Text>
                </Grid.Col>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Leave Interval</Text>
                  <Text fw={500}>{selectedApp.start_date} to {selectedApp.end_date}</Text>
                </Grid.Col>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Current Status</Text>
                  <StatusBadge status={selectedApp.status.toLowerCase()} />
                </Grid.Col>
                <Grid.Col span={12}>
                  <Text size="xs" c="dimmed">Purpose / Reason</Text>
                  <Text size="sm">{selectedApp.reason}</Text>
                </Grid.Col>
                {selectedApp.is_station_leave && (
                  <Grid.Col span={12}>
                    <Text size="xs" c="dimmed">Station Leave</Text>
                    <Text size="sm">
                      Destination: {selectedApp.station_destination} ({selectedApp.station_start_date} to {selectedApp.station_end_date})
                    </Text>
                  </Grid.Col>
                )}
                {selectedApp.substitute_id && (
                  <Grid.Col span={12}>
                    <Text size="xs" c="dimmed">Substitute Responsibility</Text>
                    <Text size="sm">
                      Substitute Employee #{selectedApp.substitute_id} — Status: {selectedApp.substitute_status}
                    </Text>
                  </Grid.Col>
                )}
              </Grid>
            </Card>

            <Text fw={600} size="sm">Audit Trail & Workflow History</Text>
            {selectedApp.audit_trail?.length ? (
              <Timeline active={selectedApp.audit_trail.length - 1} bulletSize={20} lineWidth={2}>
                {selectedApp.audit_trail.map((item) => (
                  <Timeline.Item key={item.id} title={item.action}>
                    <Text size="xs" c="dimmed">{item.created_at}</Text>
                    <Text size="sm">Transition: {item.from_status} → {item.to_status}</Text>
                    {item.remarks && <Text size="xs" c="dimmed">Remarks: {item.remarks}</Text>}
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <Text size="sm" c="dimmed">No history recorded.</Text>
            )}
          </Stack>
        )}
      </Modal>

      {/* Pre-start Cancellation Modal */}
      <Modal
        opened={Boolean(cancelModalApp)}
        onClose={() => setCancelModalApp(null)}
        title="Request Cancellation of Approved Leave"
      >
        <Stack gap="md">
          <Text size="sm">
            Per BR-EL-023, cancellation must be approved through the hierarchy before your leave balance is restored.
          </Text>
          <TextInput
            label="Reason for Cancellation"
            placeholder="Why do you wish to cancel this approved leave?"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalApp(null)}>Cancel</Button>
            <Button color="orange" onClick={handleCancelSubmit} loading={cancelMutation.isPending}>
              Submit Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resumption of Duty Modal */}
      <Modal
        opened={Boolean(resumeModalApp)}
        onClose={() => setResumeModalApp(null)}
        title="Submit Resumption of Duty"
      >
        <Stack gap="md">
          <Text size="sm">
            Per BR-EL-027 and BR-EL-028, returning early restores unused leave days to your balance, while returning late adjusts additional days after review.
          </Text>
          <TextInput
            label="Actual Resumption Date"
            type="date"
            value={actualResumeDate}
            onChange={(e) => setActualResumeDate(e.currentTarget.value)}
            required
          />
          <TextInput
            label="Reason for Date Difference (if early/late)"
            placeholder="Explain why return date differed from approved end date..."
            value={resumeDiffReason}
            onChange={(e) => setResumeDiffReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumeModalApp(null)}>Cancel</Button>
            <Button color="teal" onClick={handleResumeSubmit} loading={resumeMutation.isPending}>
              Submit Resumption
            </Button>
          </Group>
        </Stack>
      </Modal>
    </div>
  );
}
