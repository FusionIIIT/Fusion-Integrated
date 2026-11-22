import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Table, Text, TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecideLeaveRequest, useLeaveRequests, useSubmitLeaveRequest } from "../api/hooks";
import type { LeaveRequest, LeaveType } from "../api/types";

const LEAVE_TYPES: { value: LeaveType; label: string }[] = [
  { value: "casual", label: "Casual" },
  { value: "restricted", label: "Restricted" },
  { value: "medical", label: "Medical" },
  { value: "earned", label: "Earned" },
  { value: "vacation", label: "Vacation" },
  { value: "sabbatical", label: "Sabbatical" },
];

export default function LeavesPage() {
  const { can, session } = useAuth();
  const { data, isPending, error } = useLeaveRequests();
  const submit = useSubmitLeaveRequest();
  const [leaveType, setLeaveType] = useState<LeaveType | null>(null);
  const [duration, setDuration] = useState("");
  const [justification, setJustification] = useState("");
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function createRequest() {
    if (!leaveType || !duration || !justification.trim()) return;
    submit.mutate({ leave_type: leaveType, duration_days: duration, justification }, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Leave request submitted", message: "Your request was routed for approval." });
        setLeaveType(null);
        setDuration("");
        setJustification("");
      },
      onError: (cause) => notifications.show({
        color: "red", title: "Could not submit leave request", message: errorMessage(cause),
      }),
    });
  }

  return <Container size="xl">
    <PageHeader title={can("hr.leave.approve") ? "Leave Approvals" : "Leave Requests"}
      subtitle="Submit and track requests for the six supported leave types" />
    {can("hr.leave.create") && <Card withBorder mb="md"><Stack>
      <Text fw={700}>Apply for leave</Text>
      <Group grow>
        <Select label="Leave type" value={leaveType} onChange={(value) => setLeaveType(value as LeaveType | null)}
          data={LEAVE_TYPES} />
        <TextInput label="Duration in days" type="number" min="0.01" step="0.01"
          value={duration} onChange={(event) => setDuration(event.currentTarget.value)} />
      </Group>
      <Textarea label="Justification" required maxLength={1000} value={justification}
        onChange={(event) => setJustification(event.currentTarget.value)} />
      <Group justify="flex-end"><Button loading={submit.isPending}
        disabled={!leaveType || !duration || !justification.trim()} onClick={createRequest}>
        Submit request
      </Button></Group>
    </Stack></Card>}
    <Card withBorder>
      {isPending ? <Text>Loading leave requests…</Text> : data?.results.length ? (
        <Table.ScrollContainer minWidth={850}><Table striped>
          <Table.Thead><Table.Tr>
            <Table.Th>Request</Table.Th><Table.Th>Employee</Table.Th><Table.Th>Duration</Table.Th>
            <Table.Th>Justification</Table.Th><Table.Th>Status</Table.Th><Table.Th>Decision</Table.Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody>{data.results.map((request) => (
            <Table.Tr key={request.id}>
              <Table.Td>#{request.id} · {request.leave_type_display}</Table.Td>
              <Table.Td>{request.employee_user_id}</Table.Td>
              <Table.Td>{request.duration_days} days</Table.Td>
              <Table.Td>{request.justification}</Table.Td>
              <Table.Td><Badge>{request.status.replaceAll("_", " ")}</Badge></Table.Td>
              <Table.Td><LeaveDecision request={request} actorId={session?.user.id} /></Table.Td>
            </Table.Tr>
          ))}</Table.Tbody>
        </Table></Table.ScrollContainer>
      ) : <Text c="dimmed">No leave requests are available.</Text>}
    </Card>
  </Container>;
}

function LeaveDecision({ request, actorId }: { request: LeaveRequest; actorId?: number }) {
  const { can } = useAuth();
  const decide = useDecideLeaveRequest(request.id);
  const [note, setNote] = useState("");
  const canDecide = can("hr.leave.approve") && request.current_authority_user_id === actorId
    && request.employee_user_id !== actorId
    && ["pending_authority", "pending_next_authority"].includes(request.status);
  if (!canDecide) return <Text size="sm" c="dimmed">—</Text>;
  const act = (action: "approve" | "reject" | "forward") => decide.mutate({ action, note }, {
    onSuccess: () => notifications.show({
      color: "green", title: `Request ${{
        approve: "approved", reject: "rejected", forward: "forwarded",
      }[action]}`, message: "The leave workflow was updated.",
    }),
    onError: (cause) => notifications.show({
      color: "red", title: "Decision failed", message: errorMessage(cause),
    }),
  });
  return <Stack gap="xs">
    <TextInput aria-label="Decision note" value={note} onChange={(event) => setNote(event.currentTarget.value)} />
    <Group gap="xs">{(["approve", "reject", "forward"] as const).map((action) => (
      <Button key={action} size="xs" loading={decide.isPending}
        color={action === "reject" ? "red" : undefined} onClick={() => act(action)}>
        {action}
      </Button>
    ))}</Group>
  </Stack>;
}
