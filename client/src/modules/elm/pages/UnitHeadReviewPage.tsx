import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Stack, Table, Text, Textarea
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveRequests, useTransitionLeave } from "../api/hooks";
import type { LeaveRequest, LeaveStatus } from "../api/types";

export default function UnitHeadReviewPage() {
  const { data: allRequests, isPending } = useLeaveRequests();
  const transitionMutation = useTransitionLeave();

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [targetStatus, setTargetStatus] = useState<LeaveStatus | null>(null);
  const [reason, setReason] = useState("");

  // Filter requests that require Unit Head review
  const pendingRequests = allRequests?.filter((r) =>
    r.status === "PENDING_UNIT_HEAD" || r.status === "CANCELLATION_PENDING_UNIT_HEAD"
  ) ?? [];

  const handleOpenAction = (req: LeaveRequest, status: LeaveStatus) => {
    setSelectedReq(req);
    setTargetStatus(status);
    setReason("");
  };

  const handleSubmitTransition = async () => {
    if (!selectedReq || !targetStatus) return;

    try {
      await transitionMutation.mutateAsync({
        id: selectedReq.id,
        target_status: targetStatus,
        reason,
      });
      notifications.show({
        title: "Action completed",
        message: `Leave Request #${selectedReq.id} updated to ${targetStatus}`,
        color: "teal",
      });
      setSelectedReq(null);
      setTargetStatus(null);
    } catch (err: any) {
      notifications.show({
        title: "Action failed",
        message: err.message || "Failed to update leave request",
        color: "red",
      });
    }
  };

  return (
    <Container size="lg">
      <PageHeader
        title="Unit Head Review"
        subtitle="Review, approve, or forward department leave applications (BR-EL-016, BR-EL-017, BR-EL-023)"
      />

      <Card padding="md" shadow="xs" radius="md">
        {isPending ? (
          <Text c="dimmed">Loading review requests...</Text>
        ) : pendingRequests.length === 0 ? (
          <Text c="dimmed">No pending requests requiring Unit Head review at this time.</Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Request #</Table.Th>
                <Table.Th>Applicant ID</Table.Th>
                <Table.Th>Leave Category</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Reason / Remarks</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pendingRequests.map((r) => {
                const isClRh = r.leave_type__code === "CL" || r.leave_type__code === "RH";
                const isCancellation = r.status === "CANCELLATION_PENDING_UNIT_HEAD";

                return (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>Employee #{r.employee_user_id}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline">{r.leave_type__code}</Badge>
                      {r.is_station_leave && <Badge color="orange" size="xs" ml="xs">Station</Badge>}
                    </Table.Td>
                    <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                    <Table.Td>
                      <Badge color={isCancellation ? "red" : "blue"}>{r.status}</Badge>
                    </Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {isCancellation ? (
                          <>
                            <Button
                              size="xs"
                              color="red"
                              onClick={() => handleOpenAction(r, "CANCELLED")}
                            >
                              Approve Cancellation
                            </Button>
                            <Button
                              size="xs"
                              variant="light"
                              color="gray"
                              onClick={() => handleOpenAction(r, "APPROVED")}
                            >
                              Reject Cancellation
                            </Button>
                          </>
                        ) : isClRh ? (
                          <>
                            <Button
                              size="xs"
                              color="teal"
                              onClick={() => handleOpenAction(r, "APPROVED")}
                            >
                              Approve
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              onClick={() => handleOpenAction(r, "REJECTED")}
                            >
                              Reject
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              size="xs"
                              color="blue"
                              onClick={() => handleOpenAction(r, "PENDING_ESTABLISHMENT")}
                            >
                              Recommend & Forward
                            </Button>
                            <Button
                              size="xs"
                              color="orange"
                              variant="light"
                              onClick={() => handleOpenAction(r, "PENDING_ESTABLISHMENT")}
                            >
                              Forward (Not Rec.)
                            </Button>
                          </>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal
        opened={!!selectedReq}
        onClose={() => setSelectedReq(null)}
        title={`Confirm Decision for Leave Request #${selectedReq?.id}`}
      >
        <Stack>
          <Text size="sm">
            Transitioning status to: <b>{targetStatus}</b>
          </Text>
          <Textarea
            label="Decision Remarks / Reason"
            placeholder="Enter reason or recommendation notes"
            required
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Cancel</Button>
            <Button
              color="teal"
              loading={transitionMutation.isPending}
              onClick={handleSubmitTransition}
            >
              Submit Decision
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
