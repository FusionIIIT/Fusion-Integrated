import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Title,
  Paper,
  Table,
  Badge,
  Button,
  Group,
  Stack,
  SimpleGrid,
  Text,
  Modal,
  Textarea,
  Alert,
} from "@mantine/core";
import { leaveApi, type LeaveApplication, type LeaveBalance } from "../api";

export default function MyLeavesPage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [cancelModalOpen, setCancelModalOpen] = useState<boolean>(false);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState<string>("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setPageError(null);
    try {
      const [balData, appData] = await Promise.all([
        leaveApi.getBalances(),
        leaveApi.getApplications(),
      ]);
      setBalances(balData);
      setApplications(appData);
    } catch (err) {
      console.error("Failed to load leave records", err);
      setPageError("Unable to load leave records. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleWithdraw = async (id: number) => {
    if (!confirm("Are you sure you want to withdraw this pending leave request?")) return;
    setPageError(null);
    try {
      await leaveApi.withdrawApplication(id);
      loadData();
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || "Failed to withdraw application.";
      setPageError(msg);
    }
  };

  const handleCancelSubmit = async () => {
    if (!selectedAppId || !cancelReason.trim()) return;
    try {
      await leaveApi.cancelApplication(selectedAppId, cancelReason);
      setCancelModalOpen(false);
      setCancelReason("");
      setSelectedAppId(null);
      loadData();
    } catch (err: any) {
      setActionError("Failed to cancel approved leave. Leave may have already commenced.");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "green";
      case "rejected":
        return "red";
      case "withdrawn":
      case "cancelled":
        return "gray";
      case "substitute_pending":
      case "unit_head_pending":
      case "sanctioning_pending":
        return "yellow";
      default:
        return "blue";
    }
  };

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <Title order={2}>My Leaves & Balances</Title>
        <Button component={Link} to="/leave/apply">
          + Apply for Leave
        </Button>
      </Group>

      {pageError && (
        <Alert color="red" withCloseButton onClose={() => setPageError(null)}>
          {pageError}
        </Alert>
      )}

      {/* Balance Cards */}
      <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }}>
        {balances.map((b) => (
          <Paper key={b.category} withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" fw={700}>
              {b.category}
            </Text>
            <Text size="xl" fw={800} mt="xs">
              {b.available_balance}
            </Text>
            <Text size="xs" c="dimmed">
              Credited: {b.credited} | Availed: {b.availed}
            </Text>
          </Paper>
        ))}
      </SimpleGrid>

      {/* Applications Table */}
      <Paper withBorder radius="md" p="md">
        <Title order={4} mb="md">
          Leave History
        </Title>
        {applications.length === 0 && !loading ? (
          <Text c="dimmed">No leave applications found.</Text>
        ) : (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {applications.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td>#{app.id}</Table.Td>
                  <Table.Td>
                    <Badge variant="outline">{app.category}</Badge>
                  </Table.Td>
                  <Table.Td>
                    {app.start_date} to {app.end_date}
                    {app.half_day_slot !== "none" && ` (${app.half_day_slot})`}
                  </Table.Td>
                  <Table.Td>{app.calculated_days}</Table.Td>
                  <Table.Td>{app.reason || "—"}</Table.Td>
                  <Table.Td>
                    <Badge color={getStatusColor(app.status)}>
                      {app.status.replace(/_/g, " ")}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {["submitted", "substitute_pending", "unit_head_pending", "sanctioning_pending"].includes(
                        app.status
                      ) && (
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => handleWithdraw(app.id)}
                        >
                          Withdraw
                        </Button>
                      )}
                      {app.status === "approved" && (
                        <Button
                          size="xs"
                          color="orange"
                          variant="light"
                          onClick={() => {
                            setSelectedAppId(app.id);
                            setCancelModalOpen(true);
                          }}
                        >
                          Cancel Leave
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Paper>

      <Modal
        opened={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Cancel Approved Leave"
      >
        <Stack gap="md">
          {actionError && <Alert color="red">{actionError}</Alert>}
          <Text size="sm">
            Please provide a reason for cancelling this approved leave. If cancellation is approved before commencement, your deducted leave balance will be restored.
          </Text>
          <Textarea
            label="Cancellation Reason"
            required
            rows={3}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalOpen(false)}>
              Close
            </Button>
            <Button color="red" onClick={handleCancelSubmit}>
              Confirm Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
