import {
  Badge, Button, Card, Group, Stack, Text, Timeline,
} from "@mantine/core";

import type { LeaveAuditEvent, LeaveCase, LeaveRequest } from "../types";

const statusColor: Record<string, string> = {
  approved: "green",
  rejected: "red",
  withdrawn: "gray",
  cancelled: "gray",
  completed: "teal",
  pending_unit_head: "yellow",
  pending_sanction: "orange",
  awaiting_substitute: "blue",
};

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function LeaveHistory({
  requests, userId, canWithdraw, onWithdraw, onCase, onReplaceSubstitute,
  onWithdrawCase, onReplaceCaseSubstitute,
}: {
  requests: LeaveRequest[];
  userId?: number;
  canWithdraw: boolean;
  onWithdraw: (request: LeaveRequest) => void;
  onCase: (request: LeaveRequest, kind: "cancellation" | "extension" | "resumption") => void;
  onReplaceSubstitute: (request: LeaveRequest) => void;
  onWithdrawCase: (item: LeaveCase) => void;
  onReplaceCaseSubstitute: (item: LeaveCase) => void;
}) {
  if (!requests.length) {
    return <Text c="dimmed">No leave requests yet.</Text>;
  }
  return (
    <Stack>
      {requests.map((request) => {
        const pending = [
          "awaiting_substitute", "pending_unit_head", "pending_sanction",
        ].includes(request.status);
        const own = request.applicant_user_id === userId;
        const ongoing = request.status === "approved"
          && request.start_date <= new Date().toISOString().slice(0, 10)
          && request.end_date >= new Date().toISOString().slice(0, 10);
        return (
          <Card key={request.id} withBorder radius="md" padding="md">
            <Group justify="space-between" align="flex-start">
              <div>
                <Text fw={600}>{request.category} · {request.start_date} – {request.end_date}</Text>
                <Text size="sm" c="dimmed" mt={4}>{request.purpose}</Text>
                {request.station_leave && (
                  <Text size="sm" mt={4}>Station Leave: {request.station_destination}</Text>
                )}
              </div>
              <Badge color={statusColor[request.status] ?? "gray"}>
                {label(request.status)}
              </Badge>
            </Group>
            <Group mt="sm" gap="xs">
              {own && pending && canWithdraw && (
                <Button size="xs" variant="light" color="red"
                  onClick={() => onWithdraw(request)}>Withdraw</Button>
              )}
              {own && request.workflow_stage === "applicant_action_required" && (
                <Button size="xs" variant="light"
                  onClick={() => onReplaceSubstitute(request)}>
                  Nominate another substitute
                </Button>
              )}
              {own && (
                <Button size="xs" variant="subtle" onClick={() => window.print()}>
                  Print
                </Button>
              )}
              {own && request.status === "approved"
                && request.start_date > new Date().toISOString().slice(0, 10) && (
                  <Button size="xs" variant="light"
                    onClick={() => onCase(request, "cancellation")}>
                    Request cancellation
                  </Button>
                )}
              {own && ongoing && ["EL", "COL", "VL"].includes(request.category) && (
                <>
                  <Button size="xs" variant="light"
                    onClick={() => onCase(request, "extension")}>Request extension</Button>
                  <Button size="xs" variant="light"
                    onClick={() => onCase(request, "resumption")}>Submit resumption</Button>
                </>
              )}
            </Group>
            {request.cases?.map((item) => (
              <Group key={item.id} mt="xs" justify="space-between">
                <Text size="xs" c="dimmed">
                  {label(item.case_type)} · {label(item.status)}{item.reason && ` · ${item.reason}`}
                </Text>
                {own && item.status === "applicant_action_required" && (
                  <Button size="xs" variant="light"
                    onClick={() => onReplaceCaseSubstitute(item)}>
                    Replace substitute
                  </Button>
                )}
                {own && canWithdraw && [
                  "awaiting_substitute", "pending_unit_head", "pending_sanction",
                ].includes(item.status) && (
                  <Button size="xs" variant="subtle" color="red"
                    onClick={() => onWithdrawCase(item)}>
                    Withdraw action
                  </Button>
                )}
              </Group>
            ))}
            {request.history?.length ? (
              <Timeline mt="md" bulletSize={8} lineWidth={1}>
                {request.history.map((event: LeaveAuditEvent) => (
                  <Timeline.Item key={event.id} title={label(event.action)}>
                    <Text size="xs" c="dimmed">
                      {new Date(event.created_at).toLocaleString()}
                      {event.note ? ` · ${event.note}` : ""}
                    </Text>
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : null}
          </Card>
        );
      })}
    </Stack>
  );
}