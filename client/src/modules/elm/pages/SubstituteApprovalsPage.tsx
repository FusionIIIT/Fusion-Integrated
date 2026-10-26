import React, { useEffect, useState } from "react";
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
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage, http } from "../../../lib/http";
import type { LeaveApplication } from "../types";

export const SubstituteApprovalsPage: React.FC = () => {
  const [requests, setRequests] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);
  const [actionType, setActionType] = useState<"accepted" | "declined">("accepted");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [opened, setOpened] = useState(false);

  const fetchRequests = async () => {
    try {
      const res = await http.get<LeaveApplication[]>("/elm/substitute/pending");
      setRequests(res.data);
    } catch (err) {
      notifications.show({
        title: "Error",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchRequests();
  }, []);

  const handleAction = async () => {
    if (!selectedApp) return;
    setSubmitting(true);
    try {
      await http.post(`/elm/applications/${selectedApp.id}/substitute-respond`, {
        decision: actionType,
        remarks: remarks.trim(),
      });
      notifications.show({
        title: "Action Recorded",
        message: `Responsibility ${actionType} successfully.`,
        color: actionType === "accepted" ? "green" : "orange",
      });
      setOpened(false);
      void fetchRequests();
    } catch (err) {
      notifications.show({
        title: "Action Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>Substitute Responsibility Requests</Title>
          <Text c="dimmed" size="sm">
            Requests where colleagues have nominated you as their responsibility substitute.
          </Text>
        </div>

        <Card withBorder shadow="xs" radius="md">
          {loading ? (
            <Text p="md">Loading substitute requests...</Text>
          ) : requests.length === 0 ? (
            <Text p="xl" ta="center" c="dimmed">
              No pending substitute responsibility requests.
            </Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Applicant ID</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Period</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {requests.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>User #{r.user_id}</Table.Td>
                    <Table.Td>
                      <Badge variant="light">{r.leave_category}</Badge>
                    </Table.Td>
                    <Table.Td>
                      {r.start_date} to {r.end_date}
                    </Table.Td>
                    <Table.Td>{r.chargeable_days}</Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => {
                            setSelectedApp(r);
                            setActionType("accepted");
                            setRemarks("");
                            setOpened(true);
                          }}
                        >
                          Accept
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => {
                            setSelectedApp(r);
                            setActionType("declined");
                            setRemarks("");
                            setOpened(true);
                          }}
                        >
                          Decline
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={`${actionType === "accepted" ? "Accept" : "Decline"} Responsibility`}
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to {actionType} substitute responsibility for Leave Application #
            {selectedApp?.id} ({selectedApp?.start_date} to {selectedApp?.end_date})?
          </Text>
          <Textarea
            label="Remarks (optional)"
            placeholder="Add comments or handover notes"
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setOpened(false)}>
              Cancel
            </Button>
            <Button
              color={actionType === "accepted" ? "green" : "red"}
              loading={submitting}
              onClick={handleAction}
            >
              Confirm {actionType === "accepted" ? "Accept" : "Decline"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};

export default SubstituteApprovalsPage;
