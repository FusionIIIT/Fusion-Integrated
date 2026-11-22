import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarPlus, FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useDecideRegistration,
  useOpenRegistrationWindow,
  useRegistrations,
  useRegistrationWindows,
} from "../api/hooks";

export default function RegistrationApprovalsPage() {
  const { data: registrations, isLoading, error } = useRegistrations();
  const { data: windows } = useRegistrationWindows();
  const decide = useDecideRegistration();
  const openWindow = useOpenRegistrationWindow();

  const [cycle, setCycle] = useState("");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");

  const handleOpenWindow = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cycle || !opensAt || !closesAt) return;
    openWindow.mutate(
      { cycle_or_period: cycle, opens_at: opensAt, closes_at: closesAt },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Window Opened", message: `Registration window opened for ${cycle}.` });
          setCycle("");
          setOpensAt("");
          setClosesAt("");
        },
        onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
      }
    );
  };

  const handleDecide = (id: number, approve: boolean) => {
    decide.mutate(
      { id, data: { approve } },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: approve ? "Approved" : "Rejected",
            message: `Registration #${id} marked as ${approve ? "Approved" : "Rejected"}.`,
          });
        },
        onError: (err) => notifications.show({ color: "red", title: "Action Failed", message: errorMessage(err) }),
      }
    );
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  const pending = registrations?.filter((r) => r.status === "pending") || [];

  return (
    <Container size="lg">
      <PageHeader title="Registration Approvals & Windows" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <form onSubmit={handleOpenWindow}>
            <Stack gap="sm">
              <Text fw={600}>Open Registration Window</Text>
              <TextInput label="Cycle / Period" placeholder="e.g. Autumn 2026-27" required value={cycle} onChange={(e) => setCycle(e.currentTarget.value)} />
              <Group grow>
                <TextInput label="Opens At" type="datetime-local" required value={opensAt} onChange={(e) => setOpensAt(e.currentTarget.value)} />
                <TextInput label="Closes At" type="datetime-local" required value={closesAt} onChange={(e) => setClosesAt(e.currentTarget.value)} />
              </Group>
              <Group justify="flex-end">
                <Button type="submit" loading={openWindow.isPending}>Open Registration Window</Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Pending Registrations ({pending.length})</Text>
          {isLoading ? (
            <Text c="dimmed">Loading...</Text>
          ) : pending.length === 0 ? (
            <Alert color="gray">No pending registration requests to review.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Student User ID</Table.Th>
                  <Table.Th>Submitted At</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pending.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>{r.student_user_id || r.user_id}</Table.Td>
                    <Table.Td>{new Date(r.submitted_at).toLocaleString()}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" color="green" onClick={() => handleDecide(r.id, true)} loading={decide.isPending}>Approve</Button>
                        <Button size="xs" color="red" variant="outline" onClick={() => handleDecide(r.id, false)} loading={decide.isPending}>Reject</Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
