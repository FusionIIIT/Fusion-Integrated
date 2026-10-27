import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  ThemeIcon,
  Title,
  Loader,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";
import {
  FaCalendarAlt,
  FaPlus,
  FaUndo,
  FaBan,
  FaPrint,
} from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { elmApi } from "../api/elmApi";
import type { LeaveBalance, LeaveRequest } from "../types";

export default function MyLeavesPage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [withdrawTarget, setWithdrawTarget] = useState<LeaveRequest | null>(null);
  const [withdrawRemarks, setWithdrawRemarks] = useState("");
  const [cancelTarget, setCancelTarget] = useState<LeaveRequest | null>(null);
  const [cancelRemarks, setCancelRemarks] = useState("");
  const [detailTarget, setDetailTarget] = useState<LeaveRequest | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [balData, leaveData] = await Promise.all([
        elmApi.getBalances(),
        elmApi.getLeaves(),
      ]);
      setBalances(balData);
      setLeaves(leaveData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load leave records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleWithdraw = async () => {
    if (!withdrawTarget) return;
    setActionLoading(true);
    try {
      await elmApi.withdrawLeave(withdrawTarget.id, withdrawRemarks);
      notifications.show({
        title: "Success",
        message: "Leave application withdrawn successfully.",
        color: "green",
      });
      setWithdrawTarget(null);
      setWithdrawRemarks("");
      fetchData();
    } catch (err: unknown) {
      notifications.show({
        title: "Error",
        message: err instanceof Error ? err.message : "Failed to withdraw leave.",
        color: "red",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelRequest = async () => {
    if (!cancelTarget) return;
    setActionLoading(true);
    try {
      await elmApi.requestCancellation(cancelTarget.id, cancelRemarks);
      notifications.show({
        title: "Success",
        message: "Leave cancellation request submitted.",
        color: "green",
      });
      setCancelTarget(null);
      setCancelRemarks("");
      fetchData();
    } catch (err: unknown) {
      notifications.show({
        title: "Error",
        message: err instanceof Error ? err.message : "Failed to submit cancellation request.",
        color: "red",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "green";
      case "rejected":
      case "cancelled":
        return "red";
      case "withdrawn":
        return "gray";
      case "cancellation_pending":
        return "orange";
      default:
        return "blue";
    }
  };

  const isPending = (status: string) =>
    ["pending_substitute", "pending_unit_head", "pending_estt", "pending_sanction"].includes(
      status
    );

  const canCancel = (leave: LeaveRequest) => {
    if (leave.current_status !== "approved") return false;
    const start = new Date(leave.start_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return start > today;
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
        title="Employee Leave Management"
        subtitle="Manage your leave entitlements, applications, and approvals."
        action={
          <Button component={Link} to="/elm/apply" leftSection={<FaPlus />}>
            Apply for Leave
          </Button>
        }
      />

      {error && (
        <Alert color="red" mb="md" title="Notice">
          {error}
        </Alert>
      )}

      {/* Leave Balances Grid */}
      <Title order={4} mb="sm">
        Leave Balances
      </Title>
      <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 6 }} mb="xl">
        {balances.map((b) => (
          <Card key={b.id} withBorder padding="md" radius="md">
            <Group justify="space-between" mb="xs">
              <Text fw={700} size="md" c="blue">
                {b.category}
              </Text>
              <ThemeIcon variant="light" size="sm" color="blue">
                <FaCalendarAlt size={12} />
              </ThemeIcon>
            </Group>
            <Text size="xl" fw={800}>
              {b.available_balance}{" "}
              <Text span size="xs" c="dimmed">
                days avail
              </Text>
            </Text>
            <Group justify="space-between" mt="xs">
              <Text size="xs" c="dimmed">
                Credited: {b.credited + b.carried_forward}
              </Text>
              <Text size="xs" c="dimmed">
                Used: {b.consumed}
              </Text>
            </Group>
            {b.pending > 0 && (
              <Text size="xs" c="orange" mt={4}>
                Pending: {b.pending}d
              </Text>
            )}
          </Card>
        ))}
      </SimpleGrid>

      {/* Applications Table */}
      <Title order={4} mb="sm">
        My Leave Applications
      </Title>
      <Card withBorder radius="md">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Station Leave</Table.Th>
              <Table.Th>Substitute</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {leaves.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8}>
                  <Text c="dimmed" ta="center" py="md">
                    No leave applications found. Click &quot;Apply for Leave&quot; to submit a new request.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              leaves.map((l) => (
                <Table.Tr key={l.id}>
                  <Table.Td>#{l.id}</Table.Td>
                  <Table.Td>
                    <Badge variant="outline">{l.category}</Badge>
                    {l.half_day !== "none" && (
                      <Text size="xs" c="dimmed">
                        {l.half_day === "first_half" ? "1st Half" : "2nd Half"}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">
                      {l.start_date} to {l.end_date}
                    </Text>
                  </Table.Td>
                  <Table.Td fw={600}>{l.duration_days}d</Table.Td>
                  <Table.Td>
                    {l.is_station_leave ? (
                      <Badge color="cyan" size="sm">
                        Station Leave
                      </Badge>
                    ) : (
                      <Text size="xs" c="dimmed">
                        No
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {l.substitute_user_id ? (
                      <Badge
                        size="sm"
                        color={
                          l.substitute_status === "accepted"
                            ? "green"
                            : l.substitute_status === "declined"
                            ? "red"
                            : "orange"
                        }
                      >
                        {l.substitute_status}
                      </Badge>
                    ) : (
                      <Text size="xs" c="dimmed">
                        —
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Badge color={statusColor(l.current_status)}>
                      {l.current_status.replace("_", " ").toUpperCase()}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="subtle"
                        onClick={() => setDetailTarget(l)}
                      >
                        Details
                      </Button>
                      {isPending(l.current_status) && (
                        <Button
                          size="xs"
                          variant="light"
                          color="red"
                          leftSection={<FaUndo size={10} />}
                          onClick={() => setWithdrawTarget(l)}
                        >
                          Withdraw
                        </Button>
                      )}
                      {canCancel(l) && (
                        <Button
                          size="xs"
                          variant="light"
                          color="orange"
                          leftSection={<FaBan size={10} />}
                          onClick={() => setCancelTarget(l)}
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

      {/* Details & Print Modal */}
      <Modal
        opened={Boolean(detailTarget)}
        onClose={() => setDetailTarget(null)}
        title={`Leave Application #${detailTarget?.id} Details`}
        size="lg"
      >
        {detailTarget && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text fw={700}>Category:</Text>
              <Badge>{detailTarget.category}</Badge>
            </Group>
            <Group justify="space-between">
              <Text fw={700}>Requested Period:</Text>
              <Text>
                {detailTarget.start_date} to {detailTarget.end_date} (
                {detailTarget.duration_days} days)
              </Text>
            </Group>
            <Group justify="space-between">
              <Text fw={700}>Current Status:</Text>
              <Badge color={statusColor(detailTarget.current_status)}>
                {detailTarget.current_status}
              </Badge>
            </Group>
            <Text fw={700}>Purpose / Reason:</Text>
            <Card withBorder bg="gray.0" padding="xs">
              <Text size="sm">{detailTarget.purpose}</Text>
            </Card>

            {detailTarget.is_station_leave && (
              <>
                <Text fw={700} mt="xs">
                  Station Leave Details:
                </Text>
                <Card withBorder bg="gray.0" padding="xs">
                  <Text size="sm">
                    <strong>Address:</strong> {detailTarget.station_address || "—"}
                  </Text>
                  <Text size="sm">
                    <strong>Contact:</strong> {detailTarget.station_contact || "—"}
                  </Text>
                </Card>
              </>
            )}

            {detailTarget.unit_head_remarks && (
              <>
                <Text fw={700} mt="xs">
                  Unit Head Remarks:
                </Text>
                <Card withBorder bg="gray.0" padding="xs">
                  <Text size="sm">{detailTarget.unit_head_remarks}</Text>
                </Card>
              </>
            )}

            {detailTarget.actions && detailTarget.actions.length > 0 && (
              <>
                <Text fw={700} mt="xs">
                  Workflow History:
                </Text>
                <Stack gap="xs">
                  {detailTarget.actions.map((act) => (
                    <Card key={act.id} withBorder padding="xs">
                      <Group justify="space-between">
                        <Badge size="xs" variant="outline">
                          {act.action}
                        </Badge>
                        <Text size="xs" c="dimmed">
                          {new Date(act.created_at).toLocaleString()}
                        </Text>
                      </Group>
                      {act.remarks && (
                        <Text size="xs" mt={4}>
                          {act.remarks}
                        </Text>
                      )}
                    </Card>
                  ))}
                </Stack>
              </>
            )}

            <Group justify="flex-end" mt="md">
              <Button
                variant="default"
                leftSection={<FaPrint />}
                onClick={() => window.print()}
              >
                Print Application
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* Withdraw Modal */}
      <Modal
        opened={Boolean(withdrawTarget)}
        onClose={() => setWithdrawTarget(null)}
        title="Immediate Withdrawal of Pending Request"
      >
        <Stack gap="sm">
          <Text size="sm">
            Are you sure you want to withdraw Leave Application #{withdrawTarget?.id}?
            Withdrawal is immediate, frees pending balances, and halts all approval routing.
          </Text>
          <Textarea
            label="Withdrawal Reason / Remarks (optional)"
            placeholder="e.g. Schedule changed"
            value={withdrawRemarks}
            onChange={(e) => setWithdrawRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setWithdrawTarget(null)}>
              Cancel
            </Button>
            <Button
              color="red"
              loading={actionLoading}
              onClick={handleWithdraw}
            >
              Confirm Withdrawal
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Cancellation Modal */}
      <Modal
        opened={Boolean(cancelTarget)}
        onClose={() => setCancelTarget(null)}
        title="Request Cancellation of Approved Leave"
      >
        <Stack gap="sm">
          <Text size="sm">
            Requesting cancellation for Leave Application #{cancelTarget?.id} will submit a
            cancellation request through the approval hierarchy before the leave start date.
          </Text>
          <Textarea
            label="Reason for Cancellation"
            placeholder="State why the approved leave needs to be cancelled"
            required
            value={cancelRemarks}
            onChange={(e) => setCancelRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCancelTarget(null)}>
              Back
            </Button>
            <Button
              color="orange"
              loading={actionLoading}
              onClick={handleCancelRequest}
            >
              Submit Cancellation Request
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
