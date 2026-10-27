import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Stack, Table, Text, Textarea
} from "@mantine/core";
import { notifications } from "@mantine/notifications";


import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useLeaveRequests, useTransitionLeave } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function MyRequestsPage() {
  const { data: requests, isPending, error, refetch } = useLeaveRequests();
  const transitionMutation = useTransitionLeave();
  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<"withdraw" | "cancel" | null>(null);
  const [reason, setReason] = useState("");

  const handleAction = async () => {
    if (!selectedReq || !actionType) return;
    const targetStatus = actionType === "withdraw" ? "WITHDRAWN" : "CANCELLATION_PENDING_UNIT_HEAD";
    try {
      await transitionMutation.mutateAsync({
        id: selectedReq.id,
        target_status: targetStatus,
        reason,
      });
      notifications.show({
        title: "Success",
        message: actionType === "withdraw" ? "Request withdrawn." : "Cancellation submitted.",
        color: "teal",
      });
      setSelectedReq(null);
      setActionType(null);
      setReason("");
      refetch();
    } catch (err: any) {
      notifications.show({
        title: "Action failed",
        message: err.message || "Failed to update leave status",
        color: "red",
      });
    }
  };

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave Requests"
        subtitle="Track submitted leave applications, withdrawal, and status"
      />

      <Card padding="lg" shadow="xs" radius="md">
        <Table highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Half Day</Table.Th>
              <Table.Th>Station Leave</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isPending ? (
              <Table.Tr><Table.Td colSpan={7}>Loading requests...</Table.Td></Table.Tr>
            ) : !requests || requests.length === 0 ? (
              <Table.Tr><Table.Td colSpan={7}>No leave requests submitted yet.</Table.Td></Table.Tr>
            ) : (
              requests.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>#{r.id}</Table.Td>
                  <Table.Td><strong>{r.leave_type__code}</strong></Table.Td>
                  <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                  <Table.Td>{r.half_day_type}</Table.Td>
                  <Table.Td>{r.is_station_leave ? "Yes" : "No"}</Table.Td>
                  <Table.Td>
                    <Badge color={r.status === "APPROVED" ? "teal" : r.status === "REJECTED" ? "red" : "blue"}>
                      {r.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {["DRAFT", "PENDING_UNIT_HEAD", "AWAITING_SUBSTITUTE_RESPONSE", "PENDING_ESTABLISHMENT", "PENDING_FINAL_SANCTION"].includes(r.status) && (
                        <Button
                          size="xs"
                          variant="light"
                          color="orange"
                          onClick={() => { setSelectedReq(r); setActionType("withdraw"); }}
                        >
                          Withdraw
                        </Button>
                      )}
                      {r.status === "APPROVED" && (
                        <Button
                          size="xs"
                          variant="light"
                          color="red"
                          onClick={() => { setSelectedReq(r); setActionType("cancel"); }}
                        >
                          Cancel
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal
        opened={!!selectedReq}
        onClose={() => { setSelectedReq(null); setActionType(null); }}
        title={actionType === "withdraw" ? "Withdraw Pending Leave" : "Request Cancellation of Approved Leave"}
      >
        <Stack>
          <Text size="sm">
            {actionType === "withdraw"
              ? "Withdrawing will immediately cancel the pending review and restore any reserved quota."
              : "Submitting cancellation requires Unit Head review before the leave is marked Cancelled."}
          </Text>
          <Textarea
            label="Reason"
            placeholder="Explain why you are modifying this request"
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Close</Button>
            <Button
              color={actionType === "withdraw" ? "orange" : "red"}
              loading={transitionMutation.isPending}
              onClick={handleAction}
            >
              Confirm
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
