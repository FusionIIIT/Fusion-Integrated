import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
  Timeline,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCalendarPlus,
  FaHistory,
  FaPlaneArrival,
  FaTimes,
  FaUndo,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useCancelRequest,
  useExtensionRequest,
  useLeaveHistory,
  useMyLeaves,
  useResumptionRequest,
  useWithdrawLeave,
} from "../api/hooks";
import type { LeaveRequest, LeaveStatus } from "../api/types";

function formatStatus(status: LeaveStatus) {
  return status.replace(/_/g, " ").toUpperCase();
}

export default function MyLeavesPage() {
  const { data, isPending, error } = useMyLeaves();
  const withdrawMutation = useWithdrawLeave();
  const cancelMutation = useCancelRequest();
  const extendMutation = useExtensionRequest();
  const resumeMutation = useResumptionRequest();

  // Modals state
  const [historyId, setHistoryId] = useState<number | null>(null);
  const { data: historyLogs } = useLeaveHistory(historyId || 0);

  const [cancelModalItem, setCancelModalItem] = useState<LeaveRequest | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  const [extendModalItem, setExtendModalItem] = useState<LeaveRequest | null>(null);
  const [newEndDate, setNewEndDate] = useState("");
  const [extendReason, setExtendReason] = useState("");

  const [resumeModalItem, setResumeModalItem] = useState<LeaveRequest | null>(null);
  const [resumptionDate, setResumptionDate] = useState("");
  const [resumeReason, setResumeReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleWithdraw(req: LeaveRequest) {
    withdrawMutation.mutate(
      { id: req.id, reason: "Withdrawn by employee" },
      {
        onSuccess: () => {
          notifications.show({
            color: "gray",
            title: "Withdrawn",
            message: `Leave application #${req.id} was withdrawn.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Withdrawal Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleConfirmCancel() {
    if (!cancelModalItem) return;
    cancelMutation.mutate(
      { id: cancelModalItem.id, reason: cancelReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Cancellation Requested",
            message: `Cancellation requested for leave #${cancelModalItem.id}.`,
          });
          setCancelModalItem(null);
          setCancelReason("");
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

  function handleConfirmExtend() {
    if (!extendModalItem || !newEndDate) return;
    extendMutation.mutate(
      { id: extendModalItem.id, new_end_date: newEndDate, reason: extendReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Extension Requested",
            message: `Extension requested until ${newEndDate}.`,
          });
          setExtendModalItem(null);
          setNewEndDate("");
          setExtendReason("");
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

  function handleConfirmResume() {
    if (!resumeModalItem || !resumptionDate) return;
    resumeMutation.mutate(
      { id: resumeModalItem.id, resumption_date: resumptionDate, reason: resumeReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Duty Resumption Submitted",
            message: `Duty resumption report recorded for ${resumptionDate}.`,
          });
          setResumeModalItem(null);
          setResumptionDate("");
          setResumeReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Resumption Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  const rows = (data?.results ?? []) as LeaveRequest[];

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="Track your leave applications, approval progress, and history"
        action={
          <Button component={Link} to="/elm/apply" leftSection={<FaCalendarPlus />}>
            Apply for Leave
          </Button>
        }
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<LeaveRequest>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            title: "No leave applications yet",
            description: "Click Apply for Leave to submit a new leave request",
          }}
          columns={[
            {
              key: "id",
              header: "ID",
              render: (r) => <Text fw={600}>#{r.id}</Text>,
            },
            {
              key: "category",
              header: "Category",
              render: (r) => (
                <Group gap="xs">
                  <Badge color="indigo" variant="light">
                    {r.category}
                  </Badge>
                  {r.half !== "full" && (
                    <Badge size="xs" color="gray">
                      {r.half === "first_half" ? "1st Half" : "2nd Half"}
                    </Badge>
                  )}
                </Group>
              ),
            },
            {
              key: "dates",
              header: "Duration",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm">
                    {r.start_date} to {r.end_date}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.days_counted} day(s) charged
                  </Text>
                </Stack>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },

            {
              key: "substitute",
              header: "Substitute",
              render: (r) =>
                r.substitute_id ? (
                  <Badge
                    size="xs"
                    color={
                      r.substitute_accepted === true
                        ? "green"
                        : r.substitute_accepted === false
                        ? "red"
                        : "yellow"
                    }
                  >
                    User #{r.substitute_id}{" "}
                    {r.substitute_accepted === true
                      ? "Accepted"
                      : r.substitute_accepted === false
                      ? "Declined"
                      : "Pending"}
                  </Badge>
                ) : (
                  <Text size="xs" c="dimmed">
                    None
                  </Text>
                ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group gap="xs">
                  <Tooltip label="View Audit History">
                    <ActionIcon
                      variant="light"
                      color="blue"
                      onClick={() => setHistoryId(r.id)}
                    >
                      <FaHistory />
                    </ActionIcon>
                  </Tooltip>

                  {/* Pre-approval withdraw */}
                  {["draft", "awaiting_substitute", "awaiting_unit_head", "awaiting_sanction"].includes(
                    r.status
                  ) && (
                    <Tooltip label="Withdraw application">
                      <ActionIcon
                        variant="light"
                        color="orange"
                        loading={withdrawMutation.isPending}
                        onClick={() => handleWithdraw(r)}
                      >
                        <FaUndo />
                      </ActionIcon>
                    </Tooltip>
                  )}

                  {/* Cancel approved leave before start */}
                  {r.status === "approved" && (
                    <Tooltip label="Request cancellation before leave starts">
                      <ActionIcon
                        variant="light"
                        color="red"
                        onClick={() => setCancelModalItem(r)}
                      >
                        <FaTimes />
                      </ActionIcon>
                    </Tooltip>
                  )}

                  {/* Extend ongoing leave */}
                  {["approved", "ongoing"].includes(r.status) &&
                    ["EL", "COL", "VL"].includes(r.category) && (
                      <Tooltip label="Request extension">
                        <ActionIcon
                          variant="light"
                          color="teal"
                          onClick={() => setExtendModalItem(r)}
                        >
                          <FaCalendarPlus />
                        </ActionIcon>
                      </Tooltip>
                    )}

                  {/* Duty resumption */}
                  {["approved", "ongoing", "extension_approved"].includes(r.status) &&
                    ["EL", "COL", "VL"].includes(r.category) && (
                      <Tooltip label="Submit Duty Resumption / Early Return">
                        <ActionIcon
                          variant="light"
                          color="cyan"
                          onClick={() => setResumeModalItem(r)}
                        >
                          <FaPlaneArrival />
                        </ActionIcon>
                      </Tooltip>
                    )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      {/* History Modal */}
      <Modal
        opened={Boolean(historyId)}
        onClose={() => setHistoryId(null)}
        title={<Text fw={600}>Audit Trail for Leave #{historyId}</Text>}
        size="lg"
      >
        <Timeline active={(historyLogs ?? []).length} bulletSize={20} lineWidth={2}>
          {(historyLogs ?? []).map((t) => (
            <Timeline.Item
              key={t.id}
              title={`${formatStatus(t.from_status)} → ${formatStatus(t.to_status)}`}
            >
              <Text size="xs" c="dimmed">
                Actor: {t.actor_role} (User #{t.actor_user_id || "System"}) at {new Date(t.at).toLocaleString()}
              </Text>
              {t.reason && (
                <Text size="sm" mt={4}>
                  Note: {t.reason}
                </Text>
              )}
              {t.recommendation && (
                <Badge size="xs" color="indigo" mt={4}>
                  Recommendation: {t.recommendation}
                </Badge>
              )}
            </Timeline.Item>
          ))}
        </Timeline>
      </Modal>

      {/* Cancel Modal */}
      <Modal
        opened={Boolean(cancelModalItem)}
        onClose={() => setCancelModalItem(null)}
        title={`Cancel Leave #${cancelModalItem?.id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            You are requesting cancellation of approved {cancelModalItem?.category} leave ({cancelModalItem?.start_date} to {cancelModalItem?.end_date}).
          </Text>
          <Textarea
            label="Reason for cancellation"
            placeholder="Why is this leave being cancelled?"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalItem(null)}>
              Dismiss
            </Button>
            <Button color="red" onClick={handleConfirmCancel} loading={cancelMutation.isPending}>
              Confirm Cancellation Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Extend Modal */}
      <Modal
        opened={Boolean(extendModalItem)}
        onClose={() => setExtendModalItem(null)}
        title={`Request Extension for Leave #${extendModalItem?.id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            Current end date: <strong>{extendModalItem?.end_date}</strong>. Select the new extended end date:
          </Text>
          <TextInput
            type="date"
            label="New End Date"
            value={newEndDate}
            onChange={(e) => setNewEndDate(e.currentTarget.value)}
            required
          />
          <Textarea
            label="Extension Reason"
            value={extendReason}
            onChange={(e) => setExtendReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setExtendModalItem(null)}>
              Dismiss
            </Button>
            <Button color="teal" onClick={handleConfirmExtend} loading={extendMutation.isPending}>
              Submit Extension
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resumption Modal */}
      <Modal
        opened={Boolean(resumeModalItem)}
        onClose={() => setResumeModalItem(null)}
        title={`Duty Resumption for Leave #${resumeModalItem?.id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            Scheduled leave: <strong>{resumeModalItem?.start_date}</strong> to <strong>{resumeModalItem?.end_date}</strong>.
            If resuming duty early, unused days will be automatically credited back to your balance upon approval.
          </Text>
          <TextInput
            type="date"
            label="Actual Duty Resumption Date"
            value={resumptionDate}
            onChange={(e) => setResumptionDate(e.currentTarget.value)}
            required
          />
          <Textarea
            label="Remarks"
            value={resumeReason}
            onChange={(e) => setResumeReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumeModalItem(null)}>
              Dismiss
            </Button>
            <Button color="cyan" onClick={handleConfirmResume} loading={resumeMutation.isPending}>
              Submit Resumption Report
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
