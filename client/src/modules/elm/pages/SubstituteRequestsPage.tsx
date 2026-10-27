import { useEffect, useState } from "react";
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
  Textarea,
  Loader,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { elmApi } from "../api/elmApi";
import type { LeaveRequest } from "../types";

export default function SubstituteRequestsPage() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeRequest, setActiveRequest] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<"accept" | "decline">("accept");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await elmApi.getSubstituteQueue();
      setRequests(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load substitute requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleAction = async () => {
    if (!activeRequest) return;
    setSubmitting(true);
    try {
      await elmApi.respondSubstitute(activeRequest.id, actionType, remarks);
      notifications.show({
        title: "Success",
        message: `Substitute responsibility ${actionType}ed.`,
        color: actionType === "accept" ? "green" : "red",
      });
      setActiveRequest(null);
      setRemarks("");
      fetchQueue();
    } catch (err: unknown) {
      notifications.show({
        title: "Error",
        message: err instanceof Error ? err.message : "Failed to process substitute action.",
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Container size="xl" py="lg">
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      </Container>
    );
  }

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Substitute Requests"
        subtitle="Review and respond to colleagues who have nominated you as responsibility holder."
      />

      {error && (
        <Alert color="red" mb="md" title="Notice">
          {error}
        </Alert>
      )}

      <Card withBorder radius="md">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application ID</Table.Th>
              <Table.Th>Applicant (User ID)</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Leave Period</Table.Th>
              <Table.Th>Duration</Table.Th>
              <Table.Th>Purpose</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text c="dimmed" ta="center" py="md">
                    No pending substitute requests assigned to you.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              requests.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>#{r.id}</Table.Td>
                  <Table.Td>
                    <Badge variant="light">User #{r.user_id}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline">{r.category}</Badge>
                  </Table.Td>
                  <Table.Td>
                    {r.start_date} to {r.end_date}
                  </Table.Td>
                  <Table.Td>{r.duration_days} days</Table.Td>
                  <Table.Td style={{ maxWidth: 300 }}>
                    <Text size="sm" lineClamp={2}>
                      {r.purpose}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="green"
                        leftSection={<FaCheck size={12} />}
                        onClick={() => {
                          setActiveRequest(r);
                          setActionType("accept");
                        }}
                      >
                        Accept
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        leftSection={<FaTimes size={12} />}
                        onClick={() => {
                          setActiveRequest(r);
                          setActionType("decline");
                        }}
                      >
                        Decline
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Confirmation Modal */}
      <Modal
        opened={Boolean(activeRequest)}
        onClose={() => setActiveRequest(null)}
        title={`${actionType === "accept" ? "Accept" : "Decline"} Substitute Responsibility`}
      >
        <Stack gap="sm">
          <Text size="sm">
            Are you sure you want to <strong>{actionType}</strong> substitute responsibility for
            Leave Application #{activeRequest?.id} (
            {activeRequest?.start_date} to {activeRequest?.end_date})?
          </Text>
          <Textarea
            label="Remarks (optional)"
            placeholder="Any notes or handover comments"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setActiveRequest(null)}>
              Cancel
            </Button>
            <Button
              color={actionType === "accept" ? "green" : "red"}
              loading={submitting}
              onClick={handleAction}
            >
              Confirm {actionType === "accept" ? "Acceptance" : "Decline"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
