import React, { useState, useEffect } from "react";
import {
  Container,
  Card,
  Title,
  Text,
  Table,
  Badge,
  Button,
  Group,
  Modal,
  TextInput,
  Textarea,
  Loader,
  Center,
  Stack,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaClock, FaTimes, FaUndo, FaCheckCircle } from "react-icons/fa";

interface LeaveApp {
  id: number;
  applicant_username: string;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  days_count: string;
  status: string;
  reason: string;
  substitute_username: string | null;
  substitute_status: string;
  actual_resumption_date: string | null;
}

export default function LeaveHistoryPage() {
  const [leaves, setLeaves] = useState<LeaveApp[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Modal states
  const [cancelModalOpen, setCancelModalOpen] = useState<boolean>(false);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState<string>("");

  const [resumptionModalOpen, setResumptionModalOpen] = useState<boolean>(false);
  const [resumptionDate, setResumptionDate] = useState<string>("");
  const [resumptionRemarks, setResumptionRemarks] = useState<string>("");

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/leave/applications/?role=my_leaves");
      if (res.ok) {
        const data = await res.json();
        setLeaves(data.results || data);
      }
    } catch (err) {
      notifications.show({
        title: "Error",
        message: "Failed to load leave history.",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleWithdraw = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/leave/applications/${id}/withdraw/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ remarks: "Withdrawn by user." }),
      });
      if (res.ok) {
        notifications.show({
          title: "Application Withdrawn",
          message: `Application #${id} withdrawn successfully (BR-EL-022).`,
          color: "teal",
        });
        fetchHistory();
      } else {
        const err = await res.json();
        notifications.show({ title: "Error", message: err.error, color: "red" });
      }
    } catch {
      notifications.show({ title: "Error", message: "Failed to withdraw leave.", color: "red" });
    }
  };

  const submitCancel = async () => {
    if (!selectedAppId || !cancelReason) return;
    try {
      const res = await fetch(`/api/v1/leave/applications/${selectedAppId}/cancel/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: cancelReason }),
      });
      if (res.ok) {
        notifications.show({
          title: "Leave Cancelled",
          message: `Leave #${selectedAppId} cancelled before start date; balance restored (BR-EL-023).`,
          color: "teal",
        });
        setCancelModalOpen(false);
        setCancelReason("");
        fetchHistory();
      } else {
        const err = await res.json();
        notifications.show({ title: "Cancellation Rejected", message: err.error, color: "red" });
      }
    } catch {
      notifications.show({ title: "Error", message: "Failed to cancel leave.", color: "red" });
    }
  };

  const submitResumption = async () => {
    if (!selectedAppId || !resumptionDate) return;
    try {
      const res = await fetch(`/api/v1/leave/applications/${selectedAppId}/resumption/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actual_resumption_date: resumptionDate,
          remarks: resumptionRemarks,
        }),
      });
      if (res.ok) {
        notifications.show({
          title: "Resumption Recorded",
          message: `Resumption for #${selectedAppId} recorded (BR-EL-027, BR-EL-028).`,
          color: "teal",
        });
        setResumptionModalOpen(false);
        fetchHistory();
      } else {
        const err = await res.json();
        notifications.show({ title: "Error", message: err.error, color: "red" });
      }
    } catch {
      notifications.show({ title: "Error", message: "Failed to record resumption.", color: "red" });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return <Badge color="teal">Approved</Badge>;
      case "PENDING_UNIT_HEAD":
        return <Badge color="blue">Pending Unit Head</Badge>;
      case "PENDING_HIGHER_SANCTION":
        return <Badge color="violet">Pending Higher Sanction</Badge>;
      case "SUBSTITUTE_PENDING":
        return <Badge color="yellow">Awaiting Substitute</Badge>;
      case "REJECTED":
        return <Badge color="red">Rejected</Badge>;
      case "WITHDRAWN":
        return <Badge color="gray">Withdrawn</Badge>;
      case "CANCELLED":
        return <Badge color="pink">Cancelled</Badge>;
      default:
        return <Badge color="gray">{status}</Badge>;
    }
  };

  return (
    <Container size="xl" py="xl">
      <Card shadow="sm" padding="xl" radius="md" withBorder>
        <Group justify="space-between" mb="lg">
          <div>
            <Title order={2}>My Leave History</Title>
            <Text c="dimmed" size="sm">
              Track submitted leave applications, manage withdrawal, pre-start cancellations, and resumption.
            </Text>
          </div>
          <FaClock size={28} color="#228be6" />
        </Group>

        {loading ? (
          <Center py="xl">
            <Loader size="lg" />
          </Center>
        ) : leaves.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            No leave applications recorded yet.
          </Text>
        ) : (
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Interval</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Substitute</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {leaves.map((app) => {
                const canWithdraw = [
                  "SUBSTITUTE_PENDING",
                  "PENDING_UNIT_HEAD",
                  "PENDING_HIGHER_SANCTION",
                ].includes(app.status);
                const isApproved = app.status === "APPROVED";
                const isFuture = new Date(app.start_date) > new Date();

                return (
                  <Table.Tr key={app.id}>
                    <Table.Td>#{app.id}</Table.Td>
                    <Table.Td>
                      <Text fw={600}>{app.leave_type_code}</Text>
                      <Text size="xs" c="dimmed">{app.leave_type_name}</Text>
                    </Table.Td>
                    <Table.Td>
                      {app.start_date} to {app.end_date}
                    </Table.Td>
                    <Table.Td>{app.days_count}</Table.Td>
                    <Table.Td>
                      {app.substitute_username ? (
                        <div>
                          <Text size="sm">{app.substitute_username}</Text>
                          <Badge size="xs" variant="outline">
                            {app.substitute_status}
                          </Badge>
                        </div>
                      ) : (
                        "—"
                      )}
                    </Table.Td>
                    <Table.Td>{getStatusBadge(app.status)}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {canWithdraw && (
                          <Button
                            size="xs"
                            color="gray"
                            variant="light"
                            leftSection={<FaTimes size={10} />}
                            onClick={() => handleWithdraw(app.id)}
                          >
                            Withdraw
                          </Button>
                        )}
                        {isApproved && isFuture && (
                          <Button
                            size="xs"
                            color="pink"
                            variant="light"
                            leftSection={<FaUndo size={10} />}
                            onClick={() => {
                              setSelectedAppId(app.id);
                              setCancelModalOpen(true);
                            }}
                          >
                            Cancel
                          </Button>
                        )}
                        {isApproved && ["EL", "COL", "VL"].includes(app.leave_type_code) && (
                          <Button
                            size="xs"
                            color="cyan"
                            variant="light"
                            leftSection={<FaCheckCircle size={10} />}
                            onClick={() => {
                              setSelectedAppId(app.id);
                              setResumptionDate(app.end_date);
                              setResumptionModalOpen(true);
                            }}
                          >
                            Resumption
                          </Button>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      {/* Cancellation Modal */}
      <Modal
        opened={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Cancel Approved Leave (BR-EL-023)"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Approved leave can be cancelled prior to the start date. Approved days will be restored to your leave balance.
          </Text>
          <Textarea
            label="Reason for Cancellation"
            placeholder="Explain why this approved leave is no longer required..."
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalOpen(false)}>
              Back
            </Button>
            <Button color="pink" onClick={submitCancel}>
              Confirm Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resumption Modal */}
      <Modal
        opened={resumptionModalOpen}
        onClose={() => setResumptionModalOpen(false)}
        title="Duty Resumption Review (BR-EL-027, BR-EL-028)"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Submit duty resumption date for EL/COL/VL. If actual return is earlier or later, balance will be adjusted accordingly.
          </Text>
          <TextInput
            label="Actual Resumption Date"
            type="date"
            value={resumptionDate}
            onChange={(e) => setResumptionDate(e.target.value)}
            required
          />
          <Textarea
            label="Remarks"
            placeholder="Optional comments on return..."
            value={resumptionRemarks}
            onChange={(e) => setResumptionRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumptionModalOpen(false)}>
              Cancel
            </Button>
            <Button color="cyan" onClick={submitResumption}>
              Record Resumption
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}