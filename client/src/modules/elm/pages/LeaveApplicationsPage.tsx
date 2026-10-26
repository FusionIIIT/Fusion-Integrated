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
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { errorMessage, http } from "../../../lib/http";
import type { LeaveApplication } from "../types";

export const LeaveApplicationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);
  const [detailOpened, setDetailOpened] = useState(false);
  const [cancelOpened, setCancelOpened] = useState(false);
  const [extendOpened, setExtendOpened] = useState(false);
  const [resumeOpened, setResumeOpened] = useState(false);

  const [actionReason, setActionReason] = useState("");
  const [extendedEndDate, setExtendedEndDate] = useState("");
  const [actualResumeDate, setActualResumeDate] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchApplications = async () => {
    try {
      const res = await http.get<LeaveApplication[]>("/elm/applications");
      setApplications(res.data);
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
    void fetchApplications();
  }, []);

  const handleWithdraw = async (appId: number) => {
    if (!window.confirm("Are you sure you want to withdraw this pending leave request?")) return;
    try {
      await http.post(`/elm/applications/${appId}/withdraw`);
      notifications.show({
        title: "Withdrawn",
        message: "Leave application has been withdrawn.",
        color: "blue",
      });
      void fetchApplications();
    } catch (err) {
      notifications.show({
        title: "Withdrawal Failed",
        message: errorMessage(err),
        color: "red",
      });
    }
  };

  const handleCancelSubmit = async () => {
    if (!selectedApp) return;
    setSubmitting(true);
    try {
      await http.post(`/elm/applications/${selectedApp.id}/cancel`, {
        reason: actionReason,
      });
      notifications.show({
        title: "Cancellation Requested",
        message: "Cancellation request submitted for review.",
        color: "blue",
      });
      setCancelOpened(false);
      void fetchApplications();
    } catch (err) {
      notifications.show({
        title: "Cancellation Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleExtendSubmit = async () => {
    if (!selectedApp || !extendedEndDate) return;
    setSubmitting(true);
    try {
      await http.post(`/elm/applications/${selectedApp.id}/extend`, {
        extended_end_date: extendedEndDate,
        reason: actionReason,
      });
      notifications.show({
        title: "Extension Requested",
        message: "Leave extension submitted for approval.",
        color: "green",
      });
      setExtendOpened(false);
      void fetchApplications();
    } catch (err) {
      notifications.show({
        title: "Extension Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleResumeSubmit = async () => {
    if (!selectedApp || !actualResumeDate) return;
    setSubmitting(true);
    try {
      await http.post(`/elm/applications/${selectedApp.id}/resume`, {
        actual_resumption_date: actualResumeDate,
        resumption_reason: actionReason,
      });
      notifications.show({
        title: "Resumption Submitted",
        message: "Duty resumption submitted for review.",
        color: "green",
      });
      setResumeOpened(false);
      void fetchApplications();
    } catch (err) {
      notifications.show({
        title: "Resumption Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const isWithdrawable = (status: string) =>
    [
      "awaiting_substitute",
      "applicant_action_required",
      "awaiting_unit_head",
      "awaiting_establishment",
      "awaiting_final_sanction",
      "awaiting_director_self_sanction",
      "awaiting_ext_substitute",
      "ext_applicant_action_required",
      "awaiting_ext_unit_head",
      "ext_pending_establishment",
      "ext_pending_final",
    ].includes(status);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "teal";
      case "rejected":
        return "red";
      case "withdrawn":
        return "gray";
      case "cancelled":
        return "dark";
      default:
        return "blue";
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <Group justify="space-between">
          <div>
            <Title order={2}>My Leave Applications</Title>
            <Text c="dimmed" size="sm">
              Track and manage all your submitted, ongoing, and completed leaves.
            </Text>
          </div>
          <Group>
            <Button variant="light" onClick={() => navigate("/elm/balances")}>
              View Balances
            </Button>
            <Button onClick={() => navigate("/elm/apply")}>Apply for Leave</Button>
          </Group>
        </Group>

        <Card withBorder shadow="xs" radius="md">
          {loading ? (
            <Text p="md">Loading applications...</Text>
          ) : applications.length === 0 ? (
            <Text p="xl" ta="center" c="dimmed">
              No leave applications found. Click "Apply for Leave" to create one.
            </Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>App ID</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Start Date</Table.Th>
                  <Table.Th>End Date</Table.Th>
                  <Table.Th>Chargeable Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {applications.map((app) => (
                  <Table.Tr key={app.id}>
                    <Table.Td fw={600}>#{app.id}</Table.Td>
                    <Table.Td>
                      <Badge variant="light">{app.leave_category}</Badge>{" "}
                      {app.half_day && <Badge size="xs" color="gray">0.5 Day</Badge>}
                    </Table.Td>
                    <Table.Td>{app.start_date}</Table.Td>
                    <Table.Td>{app.end_date}</Table.Td>
                    <Table.Td>{app.chargeable_days}</Table.Td>
                    <Table.Td>
                      <Badge color={getStatusColor(app.status)} size="sm">
                        {app.status_display}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          variant="subtle"
                          onClick={() => {
                            setSelectedApp(app);
                            setDetailOpened(true);
                          }}
                        >
                          Details
                        </Button>

                        {isWithdrawable(app.status) && (
                          <Button
                            size="xs"
                            color="orange"
                            variant="light"
                            onClick={() => handleWithdraw(app.id)}
                          >
                            Withdraw
                          </Button>
                        )}

                        {app.status === "approved" && (
                          <>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              onClick={() => {
                                setSelectedApp(app);
                                setActionReason("");
                                setCancelOpened(true);
                              }}
                            >
                              Cancel
                            </Button>
                            {["EL", "COL", "VL"].includes(app.leave_category) && (
                              <>
                                <Button
                                  size="xs"
                                  color="indigo"
                                  variant="light"
                                  onClick={() => {
                                    setSelectedApp(app);
                                    setExtendedEndDate("");
                                    setActionReason("");
                                    setExtendOpened(true);
                                  }}
                                >
                                  Extend
                                </Button>
                                <Button
                                  size="xs"
                                  color="teal"
                                  variant="light"
                                  onClick={() => {
                                    setSelectedApp(app);
                                    setActualResumeDate(app.end_date);
                                    setActionReason("");
                                    setResumeOpened(true);
                                  }}
                                >
                                  Resume
                                </Button>
                              </>
                            )}
                          </>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>

      {/* Details Modal */}
      <Modal
        opened={detailOpened}
        onClose={() => setDetailOpened(false)}
        title={`Leave Application #${selectedApp?.id} Summary`}
        size="lg"
      >
        {selectedApp && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text fw={600}>
                {selectedApp.leave_category_display} ({selectedApp.leave_category})
              </Text>
              <Badge color={getStatusColor(selectedApp.status)}>
                {selectedApp.status_display}
              </Badge>
            </Group>
            <Text size="sm">
              <b>Period:</b> {selectedApp.start_date} to {selectedApp.end_date} (
              {selectedApp.chargeable_days} chargeable days)
            </Text>
            {selectedApp.half_day && (
              <Text size="sm">
                <b>Half Day:</b> Yes ({selectedApp.half_day_type})
              </Text>
            )}
            <Text size="sm">
              <b>Reason:</b> {selectedApp.reason}
            </Text>

            {selectedApp.station_leave && (
              <Card withBorder p="xs" bg="gray.0">
                <Text fw={600} size="xs" c="dimmed">
                  STATION LEAVE DETAILS
                </Text>
                <Text size="xs">
                  Dates: {selectedApp.station_start_date} to {selectedApp.station_end_date}
                </Text>
                <Text size="xs">Address: {selectedApp.station_address}</Text>
                {selectedApp.station_emergency_contact && (
                  <Text size="xs">Emergency Contact: {selectedApp.station_emergency_contact}</Text>
                )}
              </Card>
            )}

            {selectedApp.substitute_required && (
              <Card withBorder p="xs" bg="gray.0">
                <Text fw={600} size="xs" c="dimmed">
                  SUBSTITUTE RESPONSIBILITY
                </Text>
                <Text size="xs">
                  Substitute User ID: {selectedApp.substitute_id} | Status:{" "}
                  {selectedApp.substitute_status}
                </Text>
                {selectedApp.substitute_remarks && (
                  <Text size="xs">Remarks: {selectedApp.substitute_remarks}</Text>
                )}
              </Card>
            )}

            {selectedApp.unit_head_acted_at && (
              <Card withBorder p="xs" bg="gray.0">
                <Text fw={600} size="xs" c="dimmed">
                  UNIT HEAD REVIEW
                </Text>
                <Text size="xs">
                  Recommendation: {selectedApp.unit_head_recommendation || "N/A"}
                </Text>
                {selectedApp.unit_head_remarks && (
                  <Text size="xs">Remarks: {selectedApp.unit_head_remarks}</Text>
                )}
              </Card>
            )}

            {selectedApp.sanction_acted_at && (
              <Card withBorder p="xs" bg="gray.0">
                <Text fw={600} size="xs" c="dimmed">
                  SANCTION DECISION ({selectedApp.sanction_role})
                </Text>
                <Text size="xs">Decision: {selectedApp.sanction_decision}</Text>
                {selectedApp.sanction_remarks && (
                  <Text size="xs">Remarks: {selectedApp.sanction_remarks}</Text>
                )}
              </Card>
            )}
          </Stack>
        )}
      </Modal>

      {/* Cancel Modal */}
      <Modal
        opened={cancelOpened}
        onClose={() => setCancelOpened(false)}
        title="Request Leave Cancellation"
      >
        <Stack gap="md">
          <Text size="sm">
            Cancel approved leave #{selectedApp?.id} ({selectedApp?.start_date} to{" "}
            {selectedApp?.end_date})?
          </Text>
          <Textarea
            label="Cancellation Reason"
            placeholder="State why this leave is being cancelled"
            value={actionReason}
            onChange={(e) => setActionReason(e.target.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelOpened(false)}>
              Back
            </Button>
            <Button color="red" loading={submitting} onClick={handleCancelSubmit}>
              Submit Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Extend Modal */}
      <Modal
        opened={extendOpened}
        onClose={() => setExtendOpened(false)}
        title="Request Leave Extension"
      >
        <Stack gap="md">
          <Text size="sm">
            Extend ongoing leave #{selectedApp?.id} currently ending on {selectedApp?.end_date}.
          </Text>
          <TextInput
            label="New Extended End Date"
            type="date"
            value={extendedEndDate}
            onChange={(e) => setExtendedEndDate(e.target.value)}
            required
          />
          <Textarea
            label="Extension Reason"
            placeholder="State reason for additional leave days"
            value={actionReason}
            onChange={(e) => setActionReason(e.target.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setExtendOpened(false)}>
              Cancel
            </Button>
            <Button color="indigo" loading={submitting} onClick={handleExtendSubmit}>
              Submit Extension
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resume Modal */}
      <Modal
        opened={resumeOpened}
        onClose={() => setResumeOpened(false)}
        title="Submit Duty Resumption"
      >
        <Stack gap="md">
          <Text size="sm">
            Declare your actual resumption date for Leave #{selectedApp?.id} (approved end date:{" "}
            {selectedApp?.end_date}).
          </Text>
          <TextInput
            label="Actual Resumption Date"
            type="date"
            value={actualResumeDate}
            onChange={(e) => setActualResumeDate(e.target.value)}
            required
          />
          <Textarea
            label="Remarks / Notes (optional)"
            placeholder="Add handover or resumption notes"
            value={actionReason}
            onChange={(e) => setActionReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumeOpened(false)}>
              Cancel
            </Button>
            <Button color="teal" loading={submitting} onClick={handleResumeSubmit}>
              Submit Resumption
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};

export default LeaveApplicationsPage;
