import { Badge, Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useLeaveAction, useLeaveCaseAction, useLeaveInbox,
} from "../hooks/useLeaveManagement";
import type { LeaveCase, LeaveRequest } from "../types";

function RequestActions({
  request, onAction, loading,
}: {
  request: LeaveRequest;
  onAction: (action: string) => void;
  loading: boolean;
}) {
  if (request.status === "awaiting_substitute") {
    return <Group>
      <Button size="xs" loading={loading} onClick={() => onAction("accept")}>Accept coverage</Button>
      <Button size="xs" color="red" variant="light" loading={loading}
        onClick={() => onAction("decline")}>Decline</Button>
    </Group>;
  }
  if (request.workflow_stage === "unit_head") {
    const casual = ["CL", "RH"].includes(request.category);
    return <Group>
      <Button size="xs" loading={loading}
        onClick={() => onAction(casual ? "approve" : "recommend")}>
        {casual ? "Approve" : "Recommend"}
      </Button>
      <Button size="xs" color="red" variant="light" loading={loading}
        onClick={() => onAction(casual ? "reject" : "not_recommended")}>
        {casual ? "Reject" : "Not recommended"}
      </Button>
    </Group>;
  }
  return <Group>
    {request.workflow_stage === "establishment" ? (
      <Button size="xs" loading={loading} onClick={() => onAction("forward")}>
        Verify and forward
      </Button>
    ) : (
      <>
        <Button size="xs" loading={loading} onClick={() => onAction("approve")}>Sanction</Button>
        <Button size="xs" color="red" variant="light" loading={loading}
          onClick={() => onAction("reject")}>Reject</Button>
      </>
    )}
  </Group>;
}

function CaseActions({
  item, onAction, loading,
}: {
  item: LeaveCase;
  onAction: (action: string) => void;
  loading: boolean;
}) {
  if (item.status === "awaiting_substitute") {
    return <Group>
      <Button size="xs" loading={loading} onClick={() => onAction("accept")}>
        Accept coverage
      </Button>
      <Button size="xs" color="red" variant="light" loading={loading}
        onClick={() => onAction("decline")}>Decline</Button>
    </Group>;
  }
  if (item.workflow_stage === "unit_head"
      && !["CL", "RH"].includes(item.leave_category)) {
    return <Group>
      <Button size="xs" loading={loading} onClick={() => onAction("recommend")}>
        Recommend
      </Button>
      <Button size="xs" color="red" variant="light" loading={loading}
        onClick={() => onAction("not_recommended")}>Not recommended</Button>
    </Group>;
  }
  return <Group>
    <Button size="xs" loading={loading} onClick={() => onAction("approve")}>Approve</Button>
    <Button size="xs" color="red" variant="light" loading={loading}
      onClick={() => onAction("reject")}>Reject</Button>
  </Group>;
}

export default function LeaveInboxPage() {
  const inbox = useLeaveInbox();
  const leaveAction = useLeaveAction();
  const caseAction = useLeaveCaseAction();
  const loading = leaveAction.isPending || caseAction.isPending;
  const handleError = (error: unknown) => notifications.show({
    color: "red", title: "Could not update leave request", message: errorMessage(error),
  });
  if (inbox.error) {
    return <Container size="xl"><ErrorState error={inbox.error} /></Container>;
  }
  return (
    <Container size="xl">
      <PageHeader title="Review Queue" subtitle="Requests assigned to your ELM roles" />
      {inbox.isPending ? <Text c="dimmed">Loading assigned work…</Text> : (
        <Stack>
          {inbox.data?.requests.map((request) => (
            <Card key={`request-${request.id}`} withBorder>
              <Group justify="space-between" align="flex-start">
                <div>
                  <Text fw={600}>
                    {request.category} · {request.start_date} – {request.end_date}
                    {" · "}Employee #{request.applicant_user_id}
                  </Text>
                  <Text size="sm" c="dimmed">{request.purpose}</Text>
                  {request.workflow_stage && (
                    <Badge mt="xs" variant="light">{request.workflow_stage.replaceAll("_", " ")}</Badge>
                  )}
                </div>
                <RequestActions
                  request={request} loading={loading}
                  onAction={(action) => leaveAction.mutate(
                    { id: request.id, action }, {
                      onSuccess: () => notifications.show({
                        color: "green", title: "Leave task updated",
                        message: "The latest request state is now recorded.",
                      }),
                      onError: handleError,
                    })}
                />
              </Group>
            </Card>
          ))}
          {inbox.data?.cases.map((item) => (
            <Card key={`case-${item.id}`} withBorder>
              <Group justify="space-between" align="flex-start">
                <div>
                  <Text fw={600}>
                    {item.case_type} · {item.leave_category} · Employee #{item.applicant_user_id}
                  </Text>
                  <Text size="sm" c="dimmed">{item.reason}</Text>
                  <Text size="xs" c="dimmed">
                    {item.requested_start && `${item.requested_start} – ${item.requested_end}`}
                    {item.actual_resumption_date && `Resumption ${item.actual_resumption_date}`}
                  </Text>
                </div>
                <CaseActions
                  item={item} loading={loading}
                  onAction={(action) => caseAction.mutate(
                    { id: item.id, action }, {
                      onSuccess: () => notifications.show({
                        color: "green", title: "Leave action updated",
                        message: "The employee will see the updated decision in leave history.",
                      }),
                      onError: handleError,
                    })}
                />
              </Group>
            </Card>
          ))}
          {!inbox.data?.requests.length && !inbox.data?.cases.length && (
            <Text c="dimmed">There are no tasks assigned to you.</Text>
          )}
        </Stack>
      )}
    </Container>
  );
}
