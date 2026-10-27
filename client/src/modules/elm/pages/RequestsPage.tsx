import { useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarCheck, FaInfoCircle } from "react-icons/fa";

import { errorMessage, errorStatus } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveRequest, useLeaveRequests, useSubmitLeaveRequest,
  useWithdrawLeaveRequest } from "../api/hooks";
import type { LeaveCategory, LeaveRequestStatus } from "../api/types";

const CATEGORIES: { value: LeaveCategory; label: string }[] = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
];

const PENDING = new Set<LeaveRequestStatus>([
  "PENDING_SUBSTITUTE",
  "APPLICANT_ACTION_REQUIRED",
  "PENDING_UNIT_HEAD",
  "PENDING_ESTABLISHMENT",
  "PENDING_FINAL_DECISION",
  "PENDING_DIRECTOR_SANCTION",
]);

function dateLabel(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString();
}

function statusColor(status: LeaveRequestStatus) {
  if (status === "APPROVED") return "green";
  if (status === "REJECTED" || status === "CANCELLED") return "red";
  if (PENDING.has(status)) return "blue";
  return "gray";
}

export default function RequestsPage() {
  const [leaveType, setLeaveType] = useState<LeaveCategory | null>("EL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [purpose, setPurpose] = useState("");
  const [halfDay, setHalfDay] = useState<string | null>(null);
  const [substituteId, setSubstituteId] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number>();
  const [formError, setFormError] = useState("");

  const requests = useLeaveRequests({
    ...(statusFilter ? { status: statusFilter } : {}),
  });
  const detail = useLeaveRequest(selectedId);
  const submit = useSubmitLeaveRequest();
  const withdraw = useWithdrawLeaveRequest();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    if (!leaveType || !startDate || !endDate || !purpose.trim()) {
      setFormError("Select a leave category and dates, and enter a purpose.");
      return;
    }
    if (startDate > endDate) {
      setFormError("End date must be on or after the start date.");
      return;
    }
    if (leaveType === "CL" && (!halfDay || startDate !== endDate)) {
      setFormError("CL is currently supported only as a first-half or second-half single-day request.");
      return;
    }

    submit.mutate(
      {
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        purpose: purpose.trim(),
        ...(leaveType === "CL" ? { half_day: halfDay as "FIRST" | "SECOND" } : {}),
        ...(substituteId ? { substitute_user_id: Number(substituteId) } : {}),
      },
      {
        onSuccess: (created) => {
          setPurpose("");
          setSelectedId(created.id);
          notifications.show({
            color: "green",
            title: "Request submitted",
            message: `Request ${created.id} is ${created.status.replaceAll("_", " ").toLowerCase()}.`,
          });
        },
        onError: (error) => setFormError(errorMessage(error)),
      },
    );
  }

  function onWithdraw(id: number) {
    withdraw.mutate(id, {
      onSuccess: () => notifications.show({
        color: "orange",
        title: "Request withdrawn",
        message: "The pending request workflow has ended.",
      }),
      onError: (error) => notifications.show({
        color: "red",
        title: "Could not withdraw request",
        message: errorMessage(error),
      }),
    });
  }

  return (
    <Container size="lg">
      <PageHeader
        title="My Leave Requests"
        subtitle="Submit a request and review its recorded workflow history."
      />

      <Alert mb="md" color="blue" variant="light" icon={<FaInfoCircle />}>
        EL and COL use inclusive calendar-day counting. VL also needs a published
        vacation period. CL is supported here only for a single half day. RH,
        SCL, and full-day CL are refused until their counting rules are configured.
      </Alert>

      <Card withBorder mb="lg">
        <Group mb="md" gap="xs">
          <FaCalendarCheck />
          <Title order={4}>New leave request</Title>
        </Group>
        <form onSubmit={onSubmit}>
          <Stack>
            <Select
              label="Leave category"
              data={CATEGORIES}
              value={leaveType}
              onChange={(value) => {
                setLeaveType(value as LeaveCategory | null);
                setHalfDay(null);
              }}
              required
            />
            <Group grow align="flex-start">
              <TextInput
                type="date"
                label="Start date"
                value={startDate}
                onChange={(event) => setStartDate(event.currentTarget.value)}
                required
              />
              <TextInput
                type="date"
                label="End date"
                value={endDate}
                onChange={(event) => setEndDate(event.currentTarget.value)}
                required
              />
            </Group>
            {leaveType === "CL" && (
              <Select
                label="CL half"
                placeholder="Choose a half"
                data={[
                  { value: "FIRST", label: "First half" },
                  { value: "SECOND", label: "Second half" },
                ]}
                value={halfDay}
                onChange={setHalfDay}
                required
              />
            )}
            <TextInput
              label="Substitute employee ID, when the route requires one"
              inputMode="numeric"
              value={substituteId}
              onChange={(event) => setSubstituteId(event.currentTarget.value)}
            />
            <Textarea
              label="Purpose or reason"
              value={purpose}
              onChange={(event) => setPurpose(event.currentTarget.value)}
              required
              minRows={2}
            />
            {formError && (
              <Alert color="red" title={errorStatus(submit.error) === 503
                ? "Request cannot be routed right now"
                : "Request was not submitted"}>
                {formError}
              </Alert>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={submit.isPending}>
                Submit request
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>

      <Group justify="space-between" mb="sm">
        <Title order={4}>Request history</Title>
        <Select
          placeholder="All statuses"
          clearable
          value={statusFilter}
          onChange={setStatusFilter}
          data={[
            "PENDING_SUBSTITUTE",
            "APPLICANT_ACTION_REQUIRED",
            "PENDING_UNIT_HEAD",
            "PENDING_ESTABLISHMENT",
            "PENDING_FINAL_DECISION",
            "PENDING_DIRECTOR_SANCTION",
            "APPROVED",
            "REJECTED",
            "WITHDRAWN",
            "CANCELLED",
          ].map((value) => ({ value, label: value.replaceAll("_", " ") }))}
        />
      </Group>

      {requests.error && <ErrorState error={requests.error} />}
      {requests.isLoading && <Text c="dimmed">Loading request history…</Text>}
      {!requests.error && !requests.isLoading && requests.data?.results.length === 0 && (
        <Text c="dimmed" mb="md">No leave requests are recorded yet.</Text>
      )}
      {!!requests.data?.results.length && (
        <Table.ScrollContainer minWidth={620}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Request</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.data.results.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>ELM-{row.id}</Table.Td>
                  <Table.Td>{row.leave_type}</Table.Td>
                  <Table.Td>{dateLabel(row.start_date)} – {dateLabel(row.end_date)}</Table.Td>
                  <Table.Td>
                    <Badge color={statusColor(row.status)} variant="light">
                      {row.status.replaceAll("_", " ")}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Button variant="subtle" size="xs" onClick={() => setSelectedId(row.id)}>
                      Details
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      {selectedId != null && (
        <Card withBorder mt="lg">
          <Group justify="space-between" mb="sm">
            <Title order={4}>Request ELM-{selectedId}</Title>
            <Button variant="subtle" size="xs" onClick={() => setSelectedId(undefined)}>
              Close
            </Button>
          </Group>
          {detail.error && <ErrorState error={detail.error} />}
          {detail.data && (
            <Stack>
              <Text>{detail.data.leave_type}: {dateLabel(detail.data.start_date)} – {dateLabel(detail.data.end_date)}</Text>
              <Text>Purpose: {detail.data.purpose}</Text>
              <Text>Chargeable quantity: {detail.data.chargeable_days ?? "Not calculated"}</Text>
              <Badge color={statusColor(detail.data.status)} variant="light" w="fit-content">
                {detail.data.status.replaceAll("_", " ")}
              </Badge>
              {PENDING.has(detail.data.status) && (
                <Button
                  color="red"
                  variant="light"
                  loading={withdraw.isPending}
                  onClick={() => onWithdraw(detail.data!.id)}
                  w="fit-content"
                >
                  Withdraw pending request
                </Button>
              )}
              <Title order={5} mt="sm">Recorded workflow history</Title>
              {detail.data.workflow_actions.length === 0 ? (
                <Text c="dimmed" size="sm">No workflow actions are recorded.</Text>
              ) : (
                <Table.ScrollContainer minWidth={520}>
                  <Table>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Action</Table.Th>
                        <Table.Th>Role</Table.Th>
                        <Table.Th>Recorded</Table.Th>
                        <Table.Th>Reason</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {detail.data.workflow_actions.map((action, index) => (
                        <Table.Tr key={`${action.at}-${index}`}>
                          <Table.Td>{action.action.replaceAll("_", " ")}</Table.Td>
                          <Table.Td>{action.actor_role || "—"}</Table.Td>
                          <Table.Td>{new Date(action.at).toLocaleString()}</Table.Td>
                          <Table.Td>{action.reason || "—"}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              )}
            </Stack>
          )}
        </Card>
      )}
    </Container>
  );
}
