import { useState } from "react";
import {
  Alert, Badge, Button, Container, Group, Stack, Table, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAcknowledgeTaskNotice, useLeaveAction, useLeaveTasks, useTaskNotices,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function TasksPage() {
  const tasks = useLeaveTasks();
  const notices = useTaskNotices();
  const acknowledge = useAcknowledgeTaskNotice();
  const action = useLeaveAction();
  const [comments, setComments] = useState<Record<number, string>>({});
  if (tasks.error) return <Container size="xl"><ErrorState error={tasks.error} /></Container>;

  function act(row: LeaveRequest, actionName: string) {
    action.mutate({ id: row.id, action: actionName, comment: comments[row.id] ?? "" }, {
      onSuccess: () => setComments((all) => ({ ...all, [row.id]: "" })),
      onError: (error) => notifications.show({ color: "red", message: errorMessage(error) }),
    });
  }

  function controls(row: LeaveRequest) {
    const buttons: [string, string][] = row.status === "substitute_pending"
      ? [["accept_substitute", "Accept"], ["decline_substitute", "Decline"]]
      : row.status === "unit_head_pending"
        ? row.leave_type === "CL" || row.leave_type === "RH"
          ? [["approve", "Approve"], ["reject", "Reject"]]
          : row.requires_higher_sanction
            ? [
              ["recommend", "Recommend"],
              ...(row.establishment_required ? [["route_establishment", "Route"] as [string, string]] : []),
              ["reject", "Reject"],
            ]
            : [["approve", "Approve"], ["reject", "Reject"]]
        : row.status === "establishment_pending"
          ? [["route_final", "Route to authority"], ["return_to_unit_head", "Return"], ["reject", "Reject"]]
          : row.status === "final_pending"
            ? [["approve", "Sanction"], ["reject", "Reject"]]
            : row.status === "cancellation_unit_head_pending"
              ? row.leave_type === "CL" || row.leave_type === "RH"
                ? [["approve_cancellation", "Approve cancellation"], ["reject_cancellation", "Reject"]]
                : row.requires_higher_sanction
                  ? [
                    ["recommend_cancellation", "Recommend"],
                    ...(row.establishment_required
                      ? [["route_cancellation_establishment", "Route"] as [string, string]]
                      : []),
                    ["reject_cancellation", "Reject"],
                  ]
                  : [["approve_cancellation", "Approve cancellation"], ["reject_cancellation", "Reject"]]
              : row.status === "cancellation_establishment_pending"
                ? [["route_cancellation_final", "Route to authority"],
                  ["return_cancellation_to_unit_head", "Return"], ["reject_cancellation", "Reject"]]
                : row.status === "cancellation_final_pending"
                  ? [["approve_cancellation", "Approve cancellation"], ["reject_cancellation", "Reject"]]
            : row.status === "resumption_pending" ? [["review", "Review resumption"]] : [];
    return <Group gap={4} wrap="wrap">{buttons.map(([name, text]) =>
      <Button key={name} size="xs" variant={name === "reject" ? "light" : "filled"}
        color={name === "reject" ? "red" : undefined} loading={action.isPending}
        onClick={() => act(row, name)}>{text}</Button>)}</Group>;
  }

  return (
    <Container size="xl">
      <PageHeader title="Approval Queue" subtitle="Requests assigned to your role" />
      <Stack gap="md">
        {notices.data?.filter((notice) => !notice.read_at).map((notice) => (
          <Alert key={notice.id} title={notice.event === "decision" ? "Leave request update" :
            notice.event === "escalated" ? "Task escalated" :
              notice.event === "reminder" ? "Pending task reminder" : "New task assigned"}
            color={notice.event === "decision" ? "green" :
              notice.event === "escalated" ? "orange" : "blue"}>
            <Group justify="space-between" align="center">
              <Text size="sm">{notice.message}</Text>
              <Button size="xs" variant="subtle" loading={acknowledge.isPending}
                onClick={() => acknowledge.mutate(notice.id, {
                  onError: (error) => notifications.show({
                    color: "red", message: errorMessage(error),
                  }),
                })}>Mark read</Button>
            </Group>
          </Alert>
        ))}
        {tasks.isPending ? <Text c="dimmed">Loading assigned tasks…</Text> : tasks.data?.length ?
        <Table.ScrollContainer minWidth={980}><Table striped highlightOnHover>
          <Table.Thead><Table.Tr><Table.Th>Employee</Table.Th><Table.Th>Request</Table.Th>
            <Table.Th>Period</Table.Th><Table.Th>Stage</Table.Th><Table.Th>Decision note</Table.Th>
            <Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{tasks.data.map((row) => <Table.Tr key={row.id}>
            <Table.Td>{row.employee_name}<Text size="xs" c="dimmed">#{row.employee_id}</Text></Table.Td>
            <Table.Td>{row.leave_type} · {row.request_kind}<Text size="xs" c="dimmed">{row.charged_days} days</Text></Table.Td>
            <Table.Td>{row.start_date} – {row.end_date}</Table.Td>
            <Table.Td><Badge variant="light">{row.assigned_role || row.status}</Badge></Table.Td>
            <Table.Td><TextInput aria-label="Decision note" placeholder="Required for routing or rejection"
              value={comments[row.id] ?? ""} onChange={(event) => setComments((all) =>
                ({ ...all, [row.id]: event.currentTarget.value }))} /></Table.Td>
            <Table.Td>{controls(row)}</Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table></Table.ScrollContainer> : <Alert color="gray">No tasks are assigned to your role.</Alert>}
      </Stack>
    </Container>
  );
}