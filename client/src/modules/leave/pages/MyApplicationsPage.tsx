import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Timeline,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaBan,
  FaCalendarAlt,
  FaCalendarCheck,
  FaCalendarPlus,
  FaHistory,
  FaUndo,
  FaUserEdit,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCancelLeaveApplication,
  useLeaveBalances,
  useLeaveApplications,
  useNominateReplacementSubstitute,
  useSubmitResumption,
  useWithdrawLeaveApplication,
} from "../api/hooks";
import type { LeaveApplication } from "../api/types";

function getStatusBadgeColor(status: string): string {
  switch (status) {
    case "APPROVED":
      return "green";
    case "REJECTED":
      return "red";
    case "WITHDRAWN":
      return "gray";
    case "CANCELLED":
      return "dark";
    case "AWAITING_SUBSTITUTE":
      return "orange";
    case "SUBSTITUTE_DECLINED":
      return "pink";
    case "AWAITING_UNIT_HEAD":
      return "blue";
    case "AWAITING_SANCTION":
      return "cyan";
    case "AWAITING_DIRECTOR":
      return "grape";
    case "CANCELLATION_REQUESTED":
      return "yellow";
    default:
      return "blue";
  }
}

export default function MyApplicationsPage() {
  const { data: balances } = useLeaveBalances();
  const { data: applications, isPending, error } = useLeaveApplications();

  const withdrawMutation = useWithdrawLeaveApplication();
  const cancelMutation = useCancelLeaveApplication();
  const replaceSubMutation = useNominateReplacementSubstitute();
  const resumptionMutation = useSubmitResumption();

  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);
  const [modalMode, setModalMode] = useState<
    "history" | "withdraw" | "cancel" | "replacement" | "resumption" | null
  >(null);
  const [remarks, setRemarks] = useState("");
  const [newSubstituteId, setNewSubstituteId] = useState("");
  const [resumptionDate, setResumptionDate] = useState("");

  if (error) {
    return (
      <Container size="xl" py="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleActionSubmit() {
    if (!selectedApp) return;

    if (modalMode === "withdraw") {
      withdrawMutation.mutate(
        { id: selectedApp.id, remarks },
        {
          onSuccess: () => {
            notifications.show({
              color: "gray",
              title: "Application Withdrawn",
              message: `Leave application #${selectedApp.id} was withdrawn immediately.`,
            });
            setModalMode(null);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Withdrawal Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    } else if (modalMode === "cancel") {
      cancelMutation.mutate(
        { id: selectedApp.id, reason: remarks },
        {
          onSuccess: () => {
            notifications.show({
              color: "yellow",
              title: "Cancellation Requested",
              message: `Cancellation requested for leave #${selectedApp.id}.`,
            });
            setModalMode(null);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Cancellation Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    } else if (modalMode === "replacement") {
      replaceSubMutation.mutate(
        { id: selectedApp.id, substitute_id: newSubstituteId, remarks },
        {
          onSuccess: () => {
            notifications.show({
              color: "blue",
              title: "Substitute Nominated",
              message: `Replacement substitute nominated for leave #${selectedApp.id}.`,
            });
            setModalMode(null);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Nomination Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    } else if (modalMode === "resumption") {
      resumptionMutation.mutate(
        { id: selectedApp.id, resumption_date: resumptionDate, remarks },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Resumption Submitted",
              message: `Duty resumption submitted for review.`,
            });
            setModalMode(null);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Resumption Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    }
  }

  const isPendingState = (s: string) =>
    [
      "DRAFT",
      "AWAITING_SUBSTITUTE",
      "SUBSTITUTE_DECLINED",
      "AWAITING_UNIT_HEAD",
      "AWAITING_ESTABLISHMENT",
      "AWAITING_SANCTION",
      "AWAITING_DIRECTOR",
    ].includes(s);

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" align="center" mb="md">
        <PageHeader
          title="My Applications & Balances"
          subtitle="Track your leave entitlement, active workflow states, and history"
        />
        <Button
          component={Link}
          to="/leave/apply"
          leftSection={<FaCalendarPlus />}
          size="md"
        >
          Apply for Leave
        </Button>
      </Group>

      <Stack gap="lg">
        {balances && balances.length > 0 && (
          <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }}>
            {balances.map((b) => (
              <Card key={b.id} withBorder padding="md" radius="md">
                <Text size="xs" fw={700} c="dimmed" tt="uppercase">
                  {b.leave_type_code}
                </Text>
                <Text size="xl" fw={700} c="blue" mt="xs">
                  {b.available}
                </Text>
                <Text size="xs" c="dimmed">
                  Consumed: {b.consumed} / {b.credited}
                </Text>
              </Card>
            ))}
          </SimpleGrid>
        )}

        <Card withBorder padding="lg" radius="md">
          <DataTable<LeaveApplication>
            rows={(applications ?? []) as LeaveApplication[]}
            loading={isPending}
            rowKey={(r) => r.id}
            minWidth={850}
            empty={{
              title: "No leave applications found",
              description: "You have not submitted any leave applications yet.",
            }}
            columns={[
              {
                key: "category",
                header: "Category",
                render: (r) => (
                  <Stack gap={0}>
                    <Text fw={600}>{r.leave_type_name}</Text>
                    <Group gap="xs">
                      <Badge size="xs" variant="outline">
                        {r.leave_type_code}
                      </Badge>
                      {r.is_half_day && (
                        <Badge size="xs" color="indigo" variant="light">
                          Half-Day ({r.half_day_period})
                        </Badge>
                      )}
                      {r.station_leave_required && (
                        <Badge size="xs" color="teal" variant="light">
                          Station Leave
                        </Badge>
                      )}
                    </Group>
                  </Stack>
                ),
              },
              {
                key: "dates",
                header: "Leave Period",
                render: (r) => (
                  <Stack gap={0}>
                    <Text size="sm">
                      {r.start_date} to {r.end_date}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {r.leave_days} {Number(r.leave_days) === 1 ? "day" : "days"}
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "substitute",
                header: "Substitute",
                render: (r) =>
                  r.substitute_id ? (
                    <Stack gap={0}>
                      <Text size="sm">{r.substitute_id}</Text>
                      <Badge size="xs" color={r.substitute_status === "ACCEPTED" ? "green" : r.substitute_status === "DECLINED" ? "red" : "orange"} variant="dot">
                        {r.substitute_status}
                      </Badge>
                    </Stack>
                  ) : (
                    <Text size="xs" c="dimmed">None</Text>
                  ),
              },
              {
                key: "status",
                header: "Status",
                render: (r) => (
                  <Badge color={getStatusBadgeColor(r.status)} variant="filled">
                    {r.status.replace(/_/g, " ")}
                  </Badge>
                ),
              },
              {
                key: "actions",
                header: "Actions",
                render: (r) => (
                  <Group gap="xs">
                    <Tooltip label="View Audit History">
                      <ActionIcon
                        variant="subtle"
                        color="blue"
                        onClick={() => {
                          setSelectedApp(r);
                          setModalMode("history");
                        }}
                      >
                        <FaHistory />
                      </ActionIcon>
                    </Tooltip>

                    {isPendingState(r.status) && (
                      <Tooltip label="Withdraw Application">
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          onClick={() => {
                            setSelectedApp(r);
                            setRemarks("");
                            setModalMode("withdraw");
                          }}
                        >
                          <FaUndo />
                        </ActionIcon>
                      </Tooltip>
                    )}

                    {r.status === "SUBSTITUTE_DECLINED" && (
                      <Tooltip label="Nominate Replacement Substitute">
                        <ActionIcon
                          variant="subtle"
                          color="orange"
                          onClick={() => {
                            setSelectedApp(r);
                            setNewSubstituteId("");
                            setRemarks("");
                            setModalMode("replacement");
                          }}
                        >
                          <FaUserEdit />
                        </ActionIcon>
                      </Tooltip>
                    )}

                    {r.status === "APPROVED" && (
                      <>
                        <Tooltip label="Request Cancellation">
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            onClick={() => {
                              setSelectedApp(r);
                              setRemarks("");
                              setModalMode("cancel");
                            }}
                          >
                            <FaBan />
                          </ActionIcon>
                        </Tooltip>

                        {["EL", "COL", "VL"].includes(r.leave_type_code) &&
                          r.resumption_status === "NOT_SUBMITTED" && (
                            <Tooltip label="Submit Resumption of Duty">
                              <ActionIcon
                                variant="subtle"
                                color="green"
                                onClick={() => {
                                  setSelectedApp(r);
                                  setResumptionDate("");
                                  setRemarks("");
                                  setModalMode("resumption");
                                }}
                              >
                                <FaCalendarCheck />
                              </ActionIcon>
                            </Tooltip>
                          )}
                      </>
                    )}
                  </Group>
                ),
              },
            ]}
          />
        </Card>
      </Stack>

      <Modal
        opened={Boolean(modalMode)}
        onClose={() => setModalMode(null)}
        title={
          modalMode === "history"
            ? `Audit Trail for Application #${selectedApp?.id}`
            : modalMode === "withdraw"
            ? "Withdraw Leave Application"
            : modalMode === "cancel"
            ? "Request Pre-Start Leave Cancellation"
            : modalMode === "replacement"
            ? "Nominate Replacement Substitute"
            : "Submit Resumption of Duty"
        }
        size={modalMode === "history" ? "lg" : "md"}
      >
        {selectedApp && modalMode === "history" && (
          <Stack gap="md">
            <Card withBorder padding="sm">
              <Text size="sm">
                <strong>{selectedApp.leave_type_name}</strong> ({selectedApp.start_date} to {selectedApp.end_date})
              </Text>
              <Text size="xs" c="dimmed" mt="4px">
                Purpose: {selectedApp.reason}
              </Text>
            </Card>

            <Timeline active={(selectedApp.history?.length ?? 1) - 1} bulletSize={24} lineWidth={2}>
              {(selectedApp.history ?? []).map((h) => (
                <Timeline.Item
                  key={h.id}
                  title={h.action.replace(/_/g, " ")}
                  bullet={<FaCalendarAlt size={12} />}
                >
                  <Text size="xs" c="dimmed">
                    By <strong>{h.actor_id}</strong> on {new Date(h.created_at).toLocaleString()}
                  </Text>
                  <Text size="xs" mt="2px">
                    State: <code>{h.from_state}</code> → <code>{h.to_state}</code>
                  </Text>
                  {h.remarks && (
                    <Text size="xs" c="dimmed" mt="2px" fs="italic">
                      "{h.remarks}"
                    </Text>
                  )}
                </Timeline.Item>
              ))}
            </Timeline>
          </Stack>
        )}

        {selectedApp && modalMode === "withdraw" && (
          <Stack gap="md">
            <Text size="sm">
              Are you sure you want to withdraw this application? Withdrawal becomes effective immediately and stops any further approval workflow.
            </Text>
            <Textarea
              label="Withdrawal Remarks (Optional)"
              placeholder="State reason for withdrawal..."
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setModalMode(null)}>
                Back
              </Button>
              <Button
                color="red"
                onClick={handleActionSubmit}
                loading={withdrawMutation.isPending}
              >
                Confirm Withdrawal
              </Button>
            </Group>
          </Stack>
        )}

        {selectedApp && modalMode === "cancel" && (
          <Stack gap="md">
            <Text size="sm">
              Request pre-start cancellation for approved leave (#{selectedApp.id}). Upon review and approval by the authority, deducted leave balance will be restored.
            </Text>
            <Textarea
              label="Reason for Cancellation"
              placeholder="State why the approved leave is no longer needed..."
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
              required
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setModalMode(null)}>
                Back
              </Button>
              <Button
                color="red"
                onClick={handleActionSubmit}
                loading={cancelMutation.isPending}
              >
                Submit Cancellation Request
              </Button>
            </Group>
          </Stack>
        )}

        {selectedApp && modalMode === "replacement" && (
          <Stack gap="md">
            <Text size="sm">
              The previously nominated substitute declined. Please nominate an eligible replacement colleague to proceed with your application.
            </Text>
            <TextInput
              label="New Substitute Username"
              placeholder="e.g. colleague_username"
              value={newSubstituteId}
              onChange={(e) => setNewSubstituteId(e.currentTarget.value)}
              required
            />
            <Textarea
              label="Remarks (Optional)"
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setModalMode(null)}>
                Cancel
              </Button>
              <Button
                onClick={handleActionSubmit}
                loading={replaceSubMutation.isPending}
              >
                Nominate Substitute
              </Button>
            </Group>
          </Stack>
        )}

        {selectedApp && modalMode === "resumption" && (
          <Stack gap="md">
            <Text size="sm">
              Declare your actual resumption date following {selectedApp.leave_type_code}. If resuming early or late, leave balance will be reconciled upon review.
            </Text>
            <TextInput
              label="Actual Resumption Date"
              type="date"
              value={resumptionDate}
              onChange={(e) => setResumptionDate(e.currentTarget.value)}
              required
            />
            <Textarea
              label="Resumption Remarks"
              placeholder="Additional details regarding duty resumption..."
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setModalMode(null)}>
                Cancel
              </Button>
              <Button
                color="green"
                onClick={handleActionSubmit}
                loading={resumptionMutation.isPending}
              >
                Submit Resumption
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
