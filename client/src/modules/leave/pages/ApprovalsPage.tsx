import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaShare, FaTimes, FaUserCheck } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useLeaveRequests,
  useSubstituteAction,
  useTransitionLeave,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function ApprovalsPage() {
  const { data: requests, isLoading, error } = useLeaveRequests();
  const transitionMutation = useTransitionLeave();
  const substituteMutation = useSubstituteAction();

  const [rejectModalReq, setRejectModalReq] = useState<LeaveRequest | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [remarks, setRemarks] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  // Pending actionable items
  const actionable = (requests || []).filter(
    (r) =>
      r.status === "awaiting_substitute" ||
      r.status === "unit_head_queue" ||
      r.status === "establishment" ||
      r.status === "final_decision"
  );

  const handleApprove = (req: LeaveRequest) => {
    // For CL/RH in unit_head_queue: Unit head can directly approve
    // For higher leaves: moves to establishment or final decision
    const nextStatus =
      req.status === "unit_head_queue" && (req.category === "CL" || req.category === "RH")
        ? "approved"
        : req.status === "unit_head_queue"
        ? "establishment"
        : req.status === "establishment"
        ? "final_decision"
        : "approved";

    transitionMutation.mutate(
      { id: req.id, to_status: nextStatus as any, reason: "Approved by reviewing authority" },
      {
        onSuccess: () => {
          notifications.show({
            title: "Leave Processed",
            message: `Request #${req.id} moved to '${nextStatus}'.`,
            color: "green",
          });
        },
      }
    );
  };

  const handleRejectSubmit = () => {
    if (!rejectModalReq) return;
    if (!rejectReason.trim()) {
      notifications.show({
        title: "Rejection Reason Mandatory",
        message: "Institute rules require a stated reason for rejection (BR-EL-016..019).",
        color: "red",
      });
      return;
    }

    transitionMutation.mutate(
      {
        id: rejectModalReq.id,
        to_status: "rejected",
        reason: rejectReason.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Request Rejected",
            message: `Leave #${rejectModalReq.id} was rejected.`,
            color: "red",
          });
          setRejectModalReq(null);
          setRejectReason("");
        },
      }
    );
  };

  const handleSubstituteConsent = (req: LeaveRequest, accept: boolean) => {
    substituteMutation.mutate(
      { id: req.id, accept, remarks },
      {
        onSuccess: () => {
          notifications.show({
            title: accept ? "Consent Granted" : "Consent Declined",
            message: accept
              ? `Accepted substitute responsibility for #${req.id}. Request forwarded to Unit Head.`
              : `Declined substitute assignment for #${req.id}.`,
            color: accept ? "green" : "red",
          });
          setRemarks("");
        },
      }
    );
  };

  const rows = actionable.map((r) => (
    <Table.Tr key={r.id}>
      <Table.Td fw={500}>#{r.id}</Table.Td>
      <Table.Td>User {r.user_id}</Table.Td>
      <Table.Td>
        <Badge variant="outline">{r.category}</Badge>
      </Table.Td>
      <Table.Td>
        {r.start_date} → {r.end_date} ({r.days_count} d)
      </Table.Td>
      <Table.Td>{r.purpose || "No remarks stated"}</Table.Td>
      <Table.Td>
        <StatusBadge status={r.status} />
      </Table.Td>
      <Table.Td>
        <Group gap="xs">
          {r.status === "awaiting_substitute" ? (
            <>
              <Button
                size="xs"
                color="green"
                leftSection={<FaUserCheck />}
                onClick={() => handleSubstituteConsent(r, true)}
                loading={substituteMutation.isPending}
              >
                Accept
              </Button>
              <Button
                size="xs"
                color="red"
                variant="light"
                leftSection={<FaTimes />}
                onClick={() => handleSubstituteConsent(r, false)}
                loading={substituteMutation.isPending}
              >
                Decline
              </Button>
            </>
          ) : (
            <>
              <Button
                size="xs"
                color="green"
                leftSection={<FaCheck />}
                onClick={() => handleApprove(r)}
                loading={transitionMutation.isPending}
              >
                {r.status === "final_decision" ||
                (r.status === "unit_head_queue" &&
                  (r.category === "CL" || r.category === "RH"))
                  ? "Approve"
                  : "Recommend"}
              </Button>
              <Button
                size="xs"
                color="red"
                variant="light"
                leftSection={<FaTimes />}
                onClick={() => setRejectModalReq(r)}
              >
                Reject
              </Button>
            </>
          )}
        </Group>
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Approval Queue"
        description="Review pending leave applications, act as nominated substitute, or endorse recommendations."
      />

      <Card withBorder radius="md" p="md" mt="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Applicant</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Purpose</Table.Th>
              <Table.Th>Workflow State</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text ta="center" c="dimmed" py="md">
                    No applications currently require your review.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              rows
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal
        opened={Boolean(rejectModalReq)}
        onClose={() => setRejectModalReq(null)}
        title={`Reject Leave Request #${rejectModalReq?.id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            Please record the administrative justification for rejecting this leave
            request (mandatory per institute compliance):
          </Text>
          <Textarea
            label="Rejection Reason"
            placeholder="e.g., Critical administrative deadlines / inadequate documentation"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            rows={3}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRejectModalReq(null)}>
              Dismiss
            </Button>
            <Button
              color="red"
              onClick={handleRejectSubmit}
              loading={transitionMutation.isPending}
            >
              Confirm Rejection
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
