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
} from "@mantine/core";
import { fetchMyApplications, cancelLeave } from "../api";
import type { LeaveApplication } from "../types";
import { errorMessage } from "../../../lib/http";

export default function MyApplicationsPage() {
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);

  function loadData() {
    setLoading(true);
    fetchMyApplications()
      .then(setApplications)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleCancel(id: number) {
    if (!window.confirm("Are you sure you want to cancel this leave application?")) return;
    setActionLoading(id);
    setError(null);
    try {
      await cancelLeave(id);
      loadData();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setActionLoading(null);
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
        <Title order={2}>My Leave Applications</Title>
        <Text c="dimmed">History and track status of all your leave applications</Text>
      </div>

      {error && (
        <Alert color="red" title="Notice" withCloseButton onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card withBorder shadow="sm" radius="md" p="md">
        {applications.length === 0 ? (
          <Text c="dimmed" p="md">
            You have not submitted any leave applications yet.
          </Text>
        ) : (
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Interval</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Station Leave</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {applications.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td>#{app.id}</Table.Td>
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
                    <Badge
                      color={
                        app.status === "APPROVED"
                          ? "green"
                          : app.status === "REJECTED" || app.status === "CANCELLED"
                          ? "red"
                          : "yellow"
                      }
                    >
                      {app.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => setSelectedApp(app)}
                      >
                        Details
                      </Button>
                      {(app.status === "SUBMITTED" || app.status === "RECOMMENDED") && (
                        <Button
                          size="xs"
                          color="red"
                          variant="subtle"
                          loading={actionLoading === app.id}
                          onClick={() => handleCancel(app.id)}
                        >
                          Cancel
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal
        opened={!!selectedApp}
        onClose={() => setSelectedApp(null)}
        title={<Text fw={600}>Leave Application #{selectedApp?.id} Details</Text>}
        size="lg"
      >
        {selectedApp && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text size="sm" fw={500}>
                Leave Type: {selectedApp.leave_type}
              </Text>
              <Badge color="blue">{selectedApp.status}</Badge>
            </Group>
            <Text size="sm">
              <strong>Duration:</strong> {selectedApp.start_date} ({selectedApp.start_half}) to{" "}
              {selectedApp.end_date} ({selectedApp.end_half}) — {selectedApp.days_requested} day(s)
            </Text>
            <Text size="sm">
              <strong>Reason:</strong> {selectedApp.reason}
            </Text>
            {selectedApp.station_leave && (
              <Card withBorder bg="gray.0" p="xs">
                <Text size="xs" fw={600} mb="xs">
                  Station Leave Information:
                </Text>
                <Text size="xs">Address: {selectedApp.station_address}</Text>
                <Text size="xs">Contact: {selectedApp.station_contact}</Text>
                <Text size="xs">Emergency Contact: {selectedApp.emergency_contact}</Text>
              </Card>
            )}
            {selectedApp.remarks && (
              <Text size="sm" c="dimmed">
                <strong>Remarks:</strong> {selectedApp.remarks}
              </Text>
            )}
            {selectedApp.actions && selectedApp.actions.length > 0 && (
              <div>
                <Text size="sm" fw={600} mt="md" mb="xs">
                  Audit History:
                </Text>
                <Stack gap="xs">
                  {selectedApp.actions.map((act) => (
                    <Card key={act.id} withBorder p="xs">
                      <Group justify="space-between">
                        <Text size="xs" fw={600}>
                          {act.action} by User {act.actor_user_id}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {new Date(act.created_at).toLocaleString()}
                        </Text>
                      </Group>
                      {act.comments && (
                        <Text size="xs" c="dimmed" mt={4}>
                          "{act.comments}"
                        </Text>
                      )}
                    </Card>
                  ))}
                </Stack>
              </div>
            )}
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
