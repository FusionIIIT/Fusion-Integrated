import { useEffect, useState } from "react";
import {
  Card,
  Title,
  Text,
  Table,
  Badge,
  Button,
  Stack,
  Group,
  Loader,
  Center,
  Alert,
  Modal,
  Textarea,
} from "@mantine/core";
import { fetchPendingApprovals, reviewLeave, sanctionLeave } from "../api";
import type { LeaveApplication } from "../types";
import { errorMessage } from "../../../lib/http";

export default function ApprovalsPage() {
  const [pending, setPending] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeApp, setActiveApp] = useState<LeaveApplication | null>(null);
  const [actionType, setActionType] = useState<"RECOMMEND" | "NOT_RECOMMEND" | "APPROVE" | "REJECT" | null>(null);
  const [comments, setComments] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function loadPending() {
    setLoading(true);
    fetchPendingApprovals()
      .then(setPending)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadPending();
  }, []);

  function openActionModal(app: LeaveApplication, type: "RECOMMEND" | "NOT_RECOMMEND" | "APPROVE" | "REJECT") {
    setActiveApp(app);
    setActionType(type);
    setComments("");
  }

  async function handleConfirmAction() {
    if (!activeApp || !actionType) return;
    setSubmitting(true);
    setError(null);

    try {
      if (actionType === "RECOMMEND") {
        await reviewLeave(activeApp.id, true, comments);
      } else if (actionType === "NOT_RECOMMEND") {
        await reviewLeave(activeApp.id, false, comments);
      } else if (actionType === "APPROVE") {
        await sanctionLeave(activeApp.id, true, comments);
      } else if (actionType === "REJECT") {
        await sanctionLeave(activeApp.id, false, comments);
      }
      setActiveApp(null);
      setActionType(null);
      loadPending();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <Center h="50vh">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="lg" p="md">
      <div>
        <Title order={2}>Pending Leave Approvals</Title>
        <Text c="dimmed">Review, recommend, or sanction pending employee leave applications</Text>
      </div>

      {error && (
        <Alert color="red" title="Notice" withCloseButton onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card withBorder shadow="sm" radius="md" p="md">
        {pending.length === 0 ? (
          <Text c="dimmed" p="md">
            No pending leave applications requiring your action.
          </Text>
        ) : (
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Applicant ID</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Station Leave</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Decisions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pending.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td fw={500}>User #{app.user_id}</Table.Td>
                  <Table.Td fw={600}>{app.leave_type}</Table.Td>
                  <Table.Td>
                    {app.start_date} to {app.end_date}
                  </Table.Td>
                  <Table.Td>{app.days_requested}</Table.Td>
                  <Table.Td>
                    {app.station_leave ? (
                      <Badge color="orange" size="xs">
                        Yes
                      </Badge>
                    ) : (
                      "No"
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Badge color="yellow">{app.status}</Badge>
                  </Table.Td>
                  <Table.Td maw={200}>
                    <Text size="xs" truncate>
                      {app.reason}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {app.status === "SUBMITTED" && (
                        <>
                          <Button
                            size="xs"
                            color="blue"
                            onClick={() => openActionModal(app, "RECOMMEND")}
                          >
                            Recommend
                          </Button>
                          <Button
                            size="xs"
                            color="gray"
                            variant="subtle"
                            onClick={() => openActionModal(app, "NOT_RECOMMEND")}
                          >
                            Don't Recommend
                          </Button>
                        </>
                      )}
                      <Button
                        size="xs"
                        color="green"
                        onClick={() => openActionModal(app, "APPROVE")}
                      >
                        Approve
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="subtle"
                        onClick={() => openActionModal(app, "REJECT")}
                      >
                        Reject
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal
        opened={!!actionType}
        onClose={() => {
          setActionType(null);
          setActiveApp(null);
        }}
        title={
          <Text fw={600}>
            Confirm Action: {actionType} for Leave #{activeApp?.id}
          </Text>
        }
      >
        <Stack gap="md">
          <Text size="sm">
            Please provide any remarks or comments for this decision:
          </Text>
          <Textarea
            placeholder="Remarks / comments (optional)..."
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            minRows={3}
          />
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setActionType(null);
                setActiveApp(null);
              }}
            >
              Cancel
            </Button>
            <Button
              color={
                actionType === "APPROVE" || actionType === "RECOMMEND"
                  ? "green"
                  : "red"
              }
              loading={submitting}
              onClick={handleConfirmAction}
            >
              Confirm {actionType}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
