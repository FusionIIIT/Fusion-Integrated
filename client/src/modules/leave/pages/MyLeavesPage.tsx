import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  Menu,
  Modal,
  Paper,
  Progress,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { leaveApi } from "../api";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";
import { PrintModal } from "../components/PrintModal";
import type { LeaveBalance, LeaveRequest } from "../types";

export const MyLeavesPage: React.FC = () => {
  const navigate = useNavigate();
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [selectedLeave, setSelectedLeave] = useState<LeaveRequest | null>(null);
  const [printOpened, setPrintOpened] = useState(false);
  const [withdrawOpened, setWithdrawOpened] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [cancelOpened, setCancelOpened] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [extendOpened, setExtendOpened] = useState(false);
  const [extendedDate, setExtendedDate] = useState("");
  const [extendReason, setExtendReason] = useState("");
  const [resumeOpened, setResumeOpened] = useState(false);
  const [resumeDate, setResumeDate] = useState("");
  const [resumeRemarks, setResumeRemarks] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [bals, reqs] = await Promise.all([
        leaveApi.getMyBalances(),
        leaveApi.getMyLeaves(),
      ]);
      setBalances(bals);
      setLeaves(reqs);
    } catch {
      notifications.show({
        title: "Error",
        message: "Failed to load leave records.",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleWithdraw = async () => {
    if (!selectedLeave) return;
    setActionLoading(true);
    try {
      await leaveApi.withdrawLeave(selectedLeave.id, withdrawReason);
      notifications.show({ title: "Withdrawn", message: "Leave request withdrawn.", color: "gray" });
      setWithdrawOpened(false);
      setWithdrawReason("");
      loadData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Withdrawal failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!selectedLeave) return;
    setActionLoading(true);
    try {
      await leaveApi.cancelLeave(selectedLeave.id, cancelReason);
      notifications.show({ title: "Cancellation Requested", message: "Submitted for hierarchy review.", color: "orange" });
      setCancelOpened(false);
      setCancelReason("");
      loadData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Cancellation failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleExtend = async () => {
    if (!selectedLeave) return;
    setActionLoading(true);
    try {
      await leaveApi.extendLeave(selectedLeave.id, extendedDate, extendReason);
      notifications.show({ title: "Extension Requested", message: "Extension application submitted.", color: "teal" });
      setExtendOpened(false);
      setExtendedDate("");
      setExtendReason("");
      loadData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Extension failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    if (!selectedLeave) return;
    setActionLoading(true);
    try {
      await leaveApi.resumeLeave(selectedLeave.id, resumeDate, resumeRemarks);
      notifications.show({ title: "Resumption Submitted", message: "Submitted for authority review.", color: "teal" });
      setResumeOpened(false);
      setResumeDate("");
      setResumeRemarks("");
      loadData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Resumption failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setActionLoading(false);
    }
  };

  const isPending = (status: string) =>
    ["DRAFT", "PENDING_SUBSTITUTE", "SUBSTITUTE_DECLINED", "PENDING_UNIT_HEAD", "PENDING_SANCTION"].includes(status);

  return (
    <Box p="md" maw={1200} mx="auto">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>My Leaves & Balances</Title>
          <Text c="dimmed" size="sm">
            View your current leave account balances, track pending applications, and manage leave lifecycles.
          </Text>
        </div>
        <Button onClick={() => navigate("/leave/apply")} color="teal">
          + Apply for Leave
        </Button>
      </Group>

      {/* Balance Cards */}
      <Text fw={600} mb="xs">
        Current Year Leave Balances
      </Text>
      <Grid mb="xl">
        {balances.map((b) => {
          const credited = Number(b.credited) || 1;
          const availed = Number(b.availed) || 0;
          const remaining = Number(b.balance);
          const percent = Math.min(100, Math.round((availed / credited) * 100));

          return (
            <Grid.Col key={b.category} span={{ base: 12, sm: 6, md: 4 }}>
              <Card withBorder shadow="xs" radius="md" p="md">
                <Group justify="space-between" mb="xs">
                  <Text fw={700} size="md">
                    {b.category}
                  </Text>
                  <Badge variant="filled" color={remaining > 0 ? "teal" : "gray"}>
                    {remaining} Left
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed" mb="xs">
                  Availed: {availed} / {credited} credited
                </Text>
                <Progress value={percent} color="teal" size="sm" radius="xl" />
              </Card>
            </Grid.Col>
          );
        })}
      </Grid>

      {/* Applications Table */}
      <Paper withBorder shadow="xs" radius="md" p="md">
        <Title order={4} mb="md">
          Leave History & Applications
        </Title>
        {loading ? (
          <Group justify="center" p="xl">
            <Loader size="md" />
          </Group>
        ) : leaves.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            No leave applications recorded yet. Click &quot;Apply for Leave&quot; to submit one.
          </Text>
        ) : (
          <Table.ScrollContainer minWidth={800}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {leaves.map((leave) => (
                  <Table.Tr key={leave.id}>
                    <Table.Td>#{leave.id}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline">{leave.category}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {leave.start_date} to {leave.end_date}
                      </Text>
                      {leave.half_day !== "NONE" && (
                        <Text size="xs" c="dimmed">
                          {leave.half_day}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>{leave.computed_days}</Table.Td>
                    <Table.Td>
                      <LeaveStatusBadge status={leave.status} />
                    </Table.Td>
                    <Table.Td maw={200}>
                      <Text truncate size="sm">
                        {leave.reason}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          variant="light"
                          onClick={() => {
                            setSelectedLeave(leave);
                            setPrintOpened(true);
                          }}
                        >
                          View / Print
                        </Button>

                        {isPending(leave.status) && (
                          <Button
                            size="xs"
                            color="red"
                            variant="subtle"
                            onClick={() => {
                              setSelectedLeave(leave);
                              setWithdrawOpened(true);
                            }}
                          >
                            Withdraw
                          </Button>
                        )}

                        {leave.status === "APPROVED" && (
                          <Menu shadow="md" width={180}>
                            <Menu.Target>
                              <Button size="xs" variant="default">
                                Options ▾
                              </Button>
                            </Menu.Target>
                            <Menu.Dropdown>
                              <Menu.Item
                                onClick={() => {
                                  setSelectedLeave(leave);
                                  setCancelOpened(true);
                                }}
                              >
                                Request Cancellation
                              </Menu.Item>
                              {["EL", "COL", "VL"].includes(leave.category) && (
                                <>
                                  <Menu.Item
                                    onClick={() => {
                                      setSelectedLeave(leave);
                                      setExtendOpened(true);
                                    }}
                                  >
                                    Request Extension
                                  </Menu.Item>
                                  <Menu.Item
                                    onClick={() => {
                                      setSelectedLeave(leave);
                                      setResumeOpened(true);
                                    }}
                                  >
                                    Submit Resumption
                                  </Menu.Item>
                                </>
                              )}
                            </Menu.Dropdown>
                          </Menu>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Paper>

      {/* Print / Detail Modal */}
      <PrintModal
        opened={printOpened}
        onClose={() => setPrintOpened(false)}
        leave={selectedLeave}
      />

      {/* Withdraw Modal */}
      <Modal
        opened={withdrawOpened}
        onClose={() => setWithdrawOpened(false)}
        title="Withdraw Pending Leave Application"
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to withdraw Leave Application #{selectedLeave?.id}? This will immediately
            terminate all remaining approval processing (BR-EL-022).
          </Text>
          <Textarea
            label="Withdrawal Reason"
            placeholder="Optional reason..."
            value={withdrawReason}
            onChange={(e) => setWithdrawReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setWithdrawOpened(false)}>
              Back
            </Button>
            <Button color="red" loading={actionLoading} onClick={handleWithdraw}>
              Confirm Withdrawal
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Cancellation Modal */}
      <Modal
        opened={cancelOpened}
        onClose={() => setCancelOpened(false)}
        title="Request Cancellation of Approved Leave"
      >
        <Stack gap="md">
          <Text size="sm">
            Pre-start cancellation request for Leave #{selectedLeave?.id}. If approved, leave balance
            will be automatically restored (BR-EL-023).
          </Text>
          <Textarea
            label="Cancellation Justification"
            required
            placeholder="Reason why the approved leave is no longer needed..."
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelOpened(false)}>
              Back
            </Button>
            <Button color="orange" loading={actionLoading} onClick={handleCancel}>
              Submit Cancellation Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Extension Modal */}
      <Modal
        opened={extendOpened}
        onClose={() => setExtendOpened(false)}
        title="Request Extension of Ongoing Leave"
      >
        <Stack gap="md">
          <Text size="sm">
            Extending ongoing {selectedLeave?.category} leave #{selectedLeave?.id} (currently ends on{" "}
            {selectedLeave?.end_date}). Approval will post only the incremental period (BR-EL-025).
          </Text>
          <TextInput
            label="New Extended End Date"
            type="date"
            required
            value={extendedDate}
            onChange={(e) => setExtendedDate(e.target.value)}
          />
          <Textarea
            label="Reason for Extension"
            required
            placeholder="Justify additional leave time required..."
            value={extendReason}
            onChange={(e) => setExtendReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setExtendOpened(false)}>
              Back
            </Button>
            <Button color="teal" loading={actionLoading} onClick={handleExtend}>
              Submit Extension Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resumption Modal */}
      <Modal
        opened={resumeOpened}
        onClose={() => setResumeOpened(false)}
        title="Submit Resumption of Duty"
      >
        <Stack gap="md">
          <Text size="sm">
            Submit your actual return to duty for Leave #{selectedLeave?.id} (Approved end date was{" "}
            {selectedLeave?.end_date}). The Sanctioning Authority will review and adjust leave balance
            if early or late (BR-EL-027, BR-EL-028).
          </Text>
          <TextInput
            label="Actual Resumption Date"
            type="date"
            required
            value={resumeDate}
            onChange={(e) => setResumeDate(e.target.value)}
          />
          <Textarea
            label="Resumption Remarks / Joining Details"
            placeholder="Optional details or medical fitness notes..."
            value={resumeRemarks}
            onChange={(e) => setResumeRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumeOpened(false)}>
              Back
            </Button>
            <Button color="teal" loading={actionLoading} onClick={handleResume}>
              Submit Resumption
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Box>
  );
};

export default MyLeavesPage;
