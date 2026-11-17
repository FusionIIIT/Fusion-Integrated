import React, { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
  Alert,
} from "@mantine/core";
import { leaveApi, type LeaveRequest } from "../api/leaveApi";

export default function LeaveApprovalsPage() {
  const [approvals, setApprovals] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal decision state
  const [activeRequest, setActiveRequest] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<"recommend" | "approve" | "reject" | null>(null);
  const [remarks, setRemarks] = useState("");
  const [processing, setProcessing] = useState(false);

  const fetchApprovals = () => {
    leaveApi
      .getPendingApprovals()
      .then((data) => {
        setApprovals(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load pending requests");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const openDecisionModal = (req: LeaveRequest, action: "recommend" | "approve" | "reject") => {
    setActiveRequest(req);
    setActionType(action);
    setRemarks("");
  };

  const handleDecisionSubmit = async () => {
    if (!activeRequest || !actionType) return;
    setProcessing(true);
    try {
      if (actionType === "recommend") {
        await leaveApi.recommendRequest(activeRequest.id, remarks);
      } else {
        await leaveApi.approveOrRejectRequest(activeRequest.id, actionType, remarks);
      }
      setActiveRequest(null);
      setActionType(null);
      fetchApprovals();
    } catch (err: any) {
      setError(err.message || "Failed to process request");
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  return (
    <Container size="lg" py="xl">
      <Title order={2} mb="lg">
        Pending Leave Approvals & Recommendations
      </Title>

      {error && (
        <Alert color="red" mb="md" onClose={() => setError(null)} withCloseButton>
          {error}
        </Alert>
      )}

      <Card withBorder radius="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Request #</Table.Th>
              <Table.Th>Applicant</Table.Th>
              <Table.Th>Leave Type</Table.Th>
              <Table.Th>Duration</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Station Leave</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {approvals.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8} align="center">
                  <Text c="dimmed">No pending leave approvals found.</Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              approvals.map((req) => (
                <Table.Tr key={req.id}>
                  <Table.Td fw={500}>#{req.id}</Table.Td>
                  <Table.Td>User #{req.user_id}</Table.Td>
                  <Table.Td>{req.leave_type_code}</Table.Td>
                  <Table.Td>{req.duration_days} days</Table.Td>
                  <Table.Td>
                    {req.start_date} to {req.end_date}
                  </Table.Td>
                  <Table.Td>{req.is_station_leave ? "Yes" : "No"}</Table.Td>
                  <Table.Td>
                    <Badge color={req.status === "RECOMMENDED" ? "blue" : "yellow"}>
                      {req.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {req.status === "PENDING_APPROVAL" && (
                        <Button
                          size="xs"
                          variant="light"
                          color="blue"
                          onClick={() => openDecisionModal(req, "recommend")}
                        >
                          Recommend
                        </Button>
                      )}
                      <Button
                        size="xs"
                        variant="filled"
                        color="green"
                        onClick={() => openDecisionModal(req, "approve")}
                      >
                        Approve
                      </Button>
                      <Button
                        size="xs"
                        variant="outline"
                        color="red"
                        onClick={() => openDecisionModal(req, "reject")}
                      >
                        Reject
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal
        opened={!!activeRequest}
        onClose={() => setActiveRequest(null)}
        title={
          actionType === "recommend"
            ? `Recommend Leave Application #${activeRequest?.id}`
            : actionType === "approve"
            ? `Approve Leave Application #${activeRequest?.id}`
            : `Reject Leave Application #${activeRequest?.id}`
        }
      >
        <Stack gap="md">
          <div>
            <Text size="sm" fw={600}>
              Applicant Reason:
            </Text>
            <Text size="sm">{activeRequest?.reason}</Text>
          </div>
          {activeRequest?.is_station_leave && (
            <div>
              <Text size="sm" fw={600}>
                Station Leave Address:
              </Text>
              <Text size="sm">
                {activeRequest?.station_address} (Ph: {activeRequest?.emergency_contact_no})
              </Text>
            </div>
          )}
          <Textarea
            label={actionType === "reject" ? "Rejection Reason (Required)" : "Remarks (Optional)"}
            placeholder="Enter comments or justification..."
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
            required={actionType === "reject"}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActiveRequest(null)}>
              Cancel
            </Button>
            <Button
              color={actionType === "reject" ? "red" : actionType === "approve" ? "green" : "blue"}
              loading={processing}
              disabled={actionType === "reject" && !remarks.trim()}
              onClick={handleDecisionSubmit}
            >
              Confirm {actionType ? actionType.toUpperCase() : ""}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
