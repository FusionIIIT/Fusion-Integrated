import {
  Badge,
  Box,
  Button,
  Group,
  Loader,
  Modal,
  Paper,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import React, { useEffect, useState } from "react";
import { leaveApi } from "../api";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";
import type { LeaveRequest } from "../types";

export const SubstituteRequestsPage: React.FC = () => {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<"accept" | "decline" | null>(null);
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const data = await leaveApi.getSubstituteRequests();
      setRequests(data);
    } catch {
      notifications.show({ title: "Error", message: "Failed to load substitute requests.", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const handleRespond = async () => {
    if (!selectedReq || !actionType) return;
    setSubmitting(true);
    try {
      const accepted = actionType === "accept";
      await leaveApi.respondSubstitute(selectedReq.id, accepted, remarks);
      notifications.show({
        title: accepted ? "Accepted" : "Declined",
        message: `You have ${accepted ? "accepted" : "declined"} substitute responsibility.`,
        color: accepted ? "teal" : "gray",
      });
      setSelectedReq(null);
      setActionType(null);
      setRemarks("");
      loadRequests();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Action failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box p="md" maw={1000} mx="auto">
      <Title order={2} mb="xs">
        Substitute Responsibilities Inbox
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        Colleagues have nominated you to take over official duties during their leave absence (BR-EL-014, BR-EL-015).
        Approval routing will only proceed after your consent.
      </Text>

      <Paper withBorder shadow="xs" radius="md" p="md">
        {loading ? (
          <Group justify="center" p="xl">
            <Loader size="md" />
          </Group>
        ) : requests.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            No pending substitute requests.
          </Text>
        ) : (
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Application ID</Table.Th>
                <Table.Th>Applicant ID</Table.Th>
                <Table.Th>Leave Period</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Substitute Status</Table.Th>
                <Table.Th>Workflow Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.map((req) => (
                <Table.Tr key={req.id}>
                  <Table.Td>#{req.id}</Table.Td>
                  <Table.Td>User #{req.user_id}</Table.Td>
                  <Table.Td>
                    {req.start_date} to {req.end_date} ({req.computed_days} d)
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline">{req.category}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={
                        req.substitute_status === "ACCEPTED"
                          ? "teal"
                          : req.substitute_status === "DECLINED"
                          ? "red"
                          : "blue"
                      }
                    >
                      {req.substitute_status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <LeaveStatusBadge status={req.status} />
                  </Table.Td>
                  <Table.Td>
                    {req.substitute_status === "PENDING" ? (
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="teal"
                          onClick={() => {
                            setSelectedReq(req);
                            setActionType("accept");
                          }}
                        >
                          Accept
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => {
                            setSelectedReq(req);
                            setActionType("decline");
                          }}
                        >
                          Decline
                        </Button>
                      </Group>
                    ) : (
                      <Text size="xs" c="dimmed">
                        Responded
                      </Text>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>

      {/* Response Modal */}
      <Modal
        opened={Boolean(selectedReq && actionType)}
        onClose={() => {
          setSelectedReq(null);
          setActionType(null);
        }}
        title={actionType === "accept" ? "Accept Substitute Responsibility" : "Decline Substitute Nomination"}
      >
        <Stack gap="md">
          <Text size="sm">
            {actionType === "accept"
              ? `Confirm acceptance of substitute responsibility for Leave Application #${selectedReq?.id} (User #${selectedReq?.user_id}) from ${selectedReq?.start_date} to ${selectedReq?.end_date}.`
              : `Confirm declining substitute responsibility for Leave Application #${selectedReq?.id}. The applicant will be notified to nominate a replacement or withdraw.`}
          </Text>
          <Textarea
            label="Remarks (Optional)"
            placeholder="Add any remarks or handover notes..."
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setSelectedReq(null);
                setActionType(null);
              }}
            >
              Cancel
            </Button>
            <Button
              color={actionType === "accept" ? "teal" : "red"}
              loading={submitting}
              onClick={handleRespond}
            >
              {actionType === "accept" ? "Accept Responsibility" : "Decline Nomination"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Box>
  );
};

export default SubstituteRequestsPage;
