import { useState } from "react";
import {
  Badge,
  Button,
  Divider,
  Grid,
  Group,
  Modal,
  Stack,
  Text,
  Textarea,
  Timeline,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  useRequestCancellation,
  useRespondSubstitute,
  useReviewUnitHead,
  useSanctionLeave,
  useWithdrawLeaveRequest,
} from "../api";
import type { LeaveRequest, LeaveStatus } from "../types";

interface Props {
  opened: boolean;
  onClose: () => void;
  request: LeaveRequest | null;
}

const STATUS_COLORS: Record<LeaveStatus, string> = {
  draft: "gray",
  submitted: "blue",
  pending_substitute: "yellow",
  substitute_declined: "red",
  pending_unit_head: "blue",
  pending_sanction: "indigo",
  awaiting_director_self_sanction: "violet",
  approved: "teal",
  rejected: "red",
  withdrawn: "gray",
  cancellation_pending_unit_head: "orange",
  cancellation_pending_sanction: "orange",
  cancelled: "dark",
};

export function LeaveRequestDetailModal({ opened, onClose, request }: Props) {
  const [remarks, setRemarks] = useState("");

  const withdrawMutation = useWithdrawLeaveRequest();
  const substituteMutation = useRespondSubstitute();
  const unitHeadMutation = useReviewUnitHead();
  const sanctionMutation = useSanctionLeave();
  const cancelMutation = useRequestCancellation();

  if (!request) return null;

  const isPending = [
    "pending_substitute",
    "substitute_declined",
    "pending_unit_head",
    "pending_sanction",
    "awaiting_director_self_sanction",
    "submitted",
  ].includes(request.status);

  const canWithdraw = isPending;
  const isPreStartApproved =
    request.status === "approved" && new Date(request.start_date) > new Date();

  const handleWithdraw = async () => {
    try {
      await withdrawMutation.mutateAsync({ id: request.id, remarks });
      notifications.show({ title: "Success", message: "Leave request withdrawn.", color: "blue" });
      onClose();
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.response?.data?.detail || "Withdrawal failed.", color: "red" });
    }
  };

  const handleSubstitute = async (action: "accept" | "decline") => {
    try {
      await substituteMutation.mutateAsync({ id: request.id, action, remarks });
      notifications.show({ title: "Success", message: `Substitute response recorded: ${action}.`, color: "teal" });
      onClose();
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.response?.data?.detail || "Action failed.", color: "red" });
    }
  };

  const handleUnitHead = async (decision: "approve" | "reject" | "recommended" | "not_recommended") => {
    try {
      await unitHeadMutation.mutateAsync({ id: request.id, decision, remarks });
      notifications.show({ title: "Success", message: `Unit Head review recorded: ${decision}.`, color: "teal" });
      onClose();
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.response?.data?.detail || "Action failed.", color: "red" });
    }
  };

  const handleSanction = async (decision: "approve" | "reject") => {
    try {
      await sanctionMutation.mutateAsync({ id: request.id, decision, remarks });
      notifications.show({ title: "Success", message: `Sanction decision recorded: ${decision}.`, color: "teal" });
      onClose();
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.response?.data?.detail || "Action failed.", color: "red" });
    }
  };

  const handleRequestCancel = async () => {
    if (!remarks.trim()) {
      notifications.show({ title: "Required", message: "Please provide a reason for cancellation.", color: "red" });
      return;
    }
    try {
      await cancelMutation.mutateAsync({ id: request.id, remarks });
      notifications.show({ title: "Success", message: "Cancellation request submitted.", color: "orange" });
      onClose();
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.response?.data?.detail || "Cancellation failed.", color: "red" });
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={<Text fw={700}>Leave Request #{request.id}</Text>} size="lg">
      <Stack gap="md">
        <Group justify="space-between">
          <div>
            <Text size="sm" c="dimmed">
              Category & Period
            </Text>
            <Text fw={600} size="md">
              {request.category.toUpperCase()} • {request.start_date} to {request.end_date}
            </Text>
            {request.half_day && (
              <Badge color="cyan" size="xs" mt={2}>
                Half Day ({request.half_day_type === "first_half" ? "First Half" : "Second Half"})
              </Badge>
            )}
          </div>
          <Badge color={STATUS_COLORS[request.status] || "gray"} size="lg" radius="sm">
            {request.status.replace(/_/g, " ").toUpperCase()}
          </Badge>
        </Group>

        <Grid gutter="xs">
          <Grid.Col span={6}>
            <Text size="xs" c="dimmed">
              Leave Days
            </Text>
            <Text fw={500}>{request.leave_days || `${request.estimated_calendar_interval} (est.)`}</Text>
          </Grid.Col>
          <Grid.Col span={6}>
            <Text size="xs" c="dimmed">
              Applicant User ID
            </Text>
            <Text fw={500}>#{request.user_id}</Text>
          </Grid.Col>
          <Grid.Col span={12}>
            <Text size="xs" c="dimmed">
              Reason / Purpose
            </Text>
            <Text size="sm">{request.reason}</Text>
          </Grid.Col>
        </Grid>

        {request.is_station_leave && (
          <Card withBorder padding="xs" bg="var(--mantine-color-gray-0)">
            <Text size="xs" fw={600}>
              Station Leave Details (BR-EL-013)
            </Text>
            <Text size="xs">Address: {request.station_address}</Text>
            {request.station_start_date && (
              <Text size="xs">
                Period: {request.station_start_date} to {request.station_end_date}
              </Text>
            )}
          </Card>
        )}

        {request.substitute_id && (
          <Group gap="xs">
            <Text size="xs" c="dimmed">
              Substitute:
            </Text>
            <Text size="xs" fw={500}>
              User #{request.substitute_id} ({request.substitute_status})
            </Text>
          </Group>
        )}

        {request.unit_head_remarks && (
          <div>
            <Text size="xs" c="dimmed">
              Unit Head Remarks
            </Text>
            <Text size="xs">{request.unit_head_remarks}</Text>
          </div>
        )}

        {request.sanctioning_remarks && (
          <div>
            <Text size="xs" c="dimmed">
              Sanctioning Remarks
            </Text>
            <Text size="xs">{request.sanctioning_remarks}</Text>
          </div>
        )}

        <Divider label="Action History Audit Trail" labelPosition="center" />
        {request.actions && request.actions.length > 0 ? (
          <Timeline active={request.actions.length - 1} bulletSize={18} lineWidth={2}>
            {request.actions.map((act) => (
              <Timeline.Item key={act.id} title={act.action.replace(/_/g, " ")}>
                <Text size="xs" c="dimmed">
                  {act.from_status} → {act.to_status} by User #{act.actor_id} on{" "}
                  {new Date(act.created_at).toLocaleString()}
                </Text>
                {act.remarks && <Text size="xs" mt={2}>"{act.remarks}"</Text>}
              </Timeline.Item>
            ))}
          </Timeline>
        ) : (
          <Text size="xs" c="dimmed">
            No action history logged yet.
          </Text>
        )}

        <Divider />
        <Textarea
          label="Action Remarks / Reason"
          placeholder="Enter remarks for review, decision, or withdrawal"
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          size="xs"
        />

        <Group justify="flex-end" gap="xs">
          {/* Substitute Actions */}
          {request.status === "pending_substitute" && (
            <>
              <Button color="red" variant="light" size="xs" onClick={() => handleSubstitute("decline")}>
                Decline Coverage
              </Button>
              <Button color="teal" size="xs" onClick={() => handleSubstitute("accept")}>
                Accept Coverage
              </Button>
            </>
          )}

          {/* Unit Head Review Actions */}
          {request.status === "pending_unit_head" && (
            <>
              {["cl", "rh"].includes(request.category) ? (
                <>
                  <Button color="red" variant="light" size="xs" onClick={() => handleUnitHead("reject")}>
                    Reject (Final)
                  </Button>
                  <Button color="teal" size="xs" onClick={() => handleUnitHead("approve")}>
                    Approve (Final)
                  </Button>
                </>
              ) : (
                <>
                  <Button color="orange" variant="light" size="xs" onClick={() => handleUnitHead("not_recommended")}>
                    Not Recommend
                  </Button>
                  <Button color="blue" size="xs" onClick={() => handleUnitHead("recommended")}>
                    Recommend to Sanction
                  </Button>
                </>
              )}
            </>
          )}

          {/* Sanctioning Decision Actions */}
          {(request.status === "pending_sanction" || request.status === "awaiting_director_self_sanction") && (
            <>
              <Button color="red" variant="light" size="xs" onClick={() => handleSanction("reject")}>
                Reject Sanction
              </Button>
              <Button color="teal" size="xs" onClick={() => handleSanction("approve")}>
                Grant Sanction
              </Button>
            </>
          )}

          {/* Pre-start Cancellation */}
          {isPreStartApproved && (
            <Button color="orange" variant="light" size="xs" onClick={handleRequestCancel}>
              Request Pre-Start Cancellation
            </Button>
          )}

          {/* In-Flight Withdrawal */}
          {canWithdraw && (
            <Button color="gray" variant="outline" size="xs" onClick={handleWithdraw}>
              Withdraw Request
            </Button>
          )}

          <Button variant="default" size="xs" onClick={onClose}>
            Close
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function Card(props: any) {
  const { children, ...rest } = props;
  return <div style={{ border: "1px solid #e0e0e0", borderRadius: "4px", padding: "8px" }} {...rest}>{children}</div>;
}
