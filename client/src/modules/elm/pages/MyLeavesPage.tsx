import { useEffect, useState } from "react";
import {
  Badge, Button, Card, Container, Grid, Group, Stack, Table, Text, Title, Modal, Textarea
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function MyLeavesPage() {
  const [data, setData] = useState<{ balances: any[]; applications: any[] }>({ balances: [], applications: [] });
  const [loading, setLoading] = useState(true);
  const [cancelModal, setCancelModal] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  const fetchData = async () => {
    try {
      const res = await fetch("/api/v1/elm/my-leaves");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleWithdraw = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/elm/applications/${id}/withdraw`, { method: "POST" });
      if (res.ok) {
        notifications.show({ title: "Success", message: "Application withdrawn immediately." });
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCancelRequest = async () => {
    if (!cancelModal) return;
    try {
      const res = await fetch(`/api/v1/elm/applications/${cancelModal}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ remarks: cancelReason }),
      });
      if (res.ok) {
        notifications.show({ title: "Success", message: "Cancellation requested." });
        setCancelModal(null);
        setCancelReason("");
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="View your leave balances and track leave application status"
      />

      <Stack gap="lg">
        <Title order={3}>Leave Balances</Title>
        <Grid>
          {data.balances.map((b) => (
            <Grid.Col key={b.id} span={{ base: 12, sm: 4, md: 2 }}>
              <Card shadow="sm" padding="md" withBorder>
                <Text size="xs" c="dimmed" fw={700}>{b.leave_category}</Text>
                <Title order={2}>{b.available_days}</Title>
                <Text size="xs" c="dimmed">Allocated: {b.allocated_days} | Availed: {b.availed_days}</Text>
              </Card>
            </Grid.Col>
          ))}
        </Grid>

        <Title order={3} mt="md">Leave Applications</Title>
        <Card shadow="sm" padding="md" withBorder>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Station Leave</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.applications.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td fw={600}>{app.leave_category}</Table.Td>
                  <Table.Td>{app.start_date} to {app.end_date}</Table.Td>
                  <Table.Td>{app.calculated_days}</Table.Td>
                  <Table.Td>
                    <Badge color={app.status === "approved" ? "green" : app.status === "rejected" ? "red" : "blue"}>
                      {app.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{app.is_station_leave ? "Yes (" + app.station_destination + ")" : "No"}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {["pending_substitute", "pending_unit_head", "pending_higher_sanction"].includes(app.status) && (
                        <Button size="xs" color="red" variant="subtle" onClick={() => handleWithdraw(app.id)}>
                          Withdraw
                        </Button>
                      )}
                      {app.status === "approved" && (
                        <Button size="xs" color="orange" variant="subtle" onClick={() => setCancelModal(app.id)}>
                          Cancel
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {data.applications.length === 0 && !loading && (
                <Table.Tr>
                  <Table.Td colSpan={6}>
                    <Text ta="center" c="dimmed" py="md">No leave applications recorded.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>

      <Modal opened={cancelModal !== null} onClose={() => setCancelModal(null)} title="Request Leave Cancellation">
        <Stack>
          <Text size="sm">Pre-start cancellation requests will be routed to the sanctioning hierarchy.</Text>
          <Textarea
            label="Reason for Cancellation"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModal(null)}>Back</Button>
            <Button color="orange" onClick={handleCancelRequest}>Submit Cancellation Request</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
