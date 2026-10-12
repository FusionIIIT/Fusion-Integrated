import {
  Badge, Button, Card, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInbox } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useRequests, useReview, useRoute, useSanction, useSubstituteResponse,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { STATUS_COLOR } from "./MyLeavePage";

/** Requests waiting on the signed-in user, by role (EL-UC-002/003/004/005). */
export default function ApprovalsPage() {
  const { can, session } = useAuth();
  const { data, isPending, error } = useRequests();
  const substitute = useSubstituteResponse();
  const review = useReview();
  const route = useRoute();
  const sanction = useSanction();

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const me = session?.user.id;
  const onError = (e: unknown) =>
    notifications.show({ color: "red", title: "Action failed", message: errorMessage(e) });
  const busy = substitute.isPending || review.isPending || route.isPending || sanction.isPending;

  /** The buttons this user may press on this request right now; empty means nothing to do. */
  const actions = (r: LeaveRequest) => {
    if (r.status === "substitute_pending" && r.substitute_user_id === me && r.substitute_status === "pending") {
      return [
        { label: "Accept duty", go: () => substitute.mutate({ id: r.id, accept: true }, { onError }) },
        { label: "Decline", color: "red", go: () => substitute.mutate({ id: r.id, accept: false }, { onError }) },
      ];
    }
    if (r.status === "unit_review" && can("leave.request.review")) {
      const final = r.category === "CL" || r.category === "RH";
      return final
        ? [
          { label: "Approve", go: () => review.mutate({ id: r.id, outcome: "approve", note: "" }, { onError }) },
          { label: "Reject", color: "red", go: () => review.mutate({ id: r.id, outcome: "reject", note: "" }, { onError }) },
        ]
        : [
          { label: "Recommend", go: () => review.mutate({ id: r.id, outcome: "recommend", note: "" }, { onError }) },
          { label: "Not recommend", color: "red", go: () => review.mutate({ id: r.id, outcome: "not_recommend", note: "" }, { onError }) },
        ];
    }
    if (r.status === "routing" && can("leave.request.route")) {
      return [{ label: "Route to sanction", go: () => route.mutate({ id: r.id, note: "" }, { onError }) }];
    }
    if (r.status === "sanction" && can("leave.request.sanction")) {
      return [
        { label: "Sanction", go: () => sanction.mutate({ id: r.id, decision: "approve", note: "" }, { onError }) },
        { label: "Refuse", color: "red", go: () => sanction.mutate({ id: r.id, decision: "reject", note: "" }, { onError }) },
      ];
    }
    return [];
  };

  const waiting = (data?.results ?? []).filter((r) => r.user_id !== me && actions(r).length > 0);

  return (
    <Container size="md">
      <PageHeader title="Leave approvals"
        subtitle="Substitute requests, unit-head reviews, routing and sanction waiting on you" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && waiting.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <FaInbox size={24} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>Nothing waiting for you</Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {waiting.map((r) => (
          <Card key={r.id} withBorder padding="lg">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={4} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700}>Employee #{r.user_id} · {r.category}</Text>
                  <Badge color={STATUS_COLOR[r.status] ?? "gray"} variant="light">
                    {r.status.replace("_", " ")}
                  </Badge>
                  {r.recommendation && <Badge variant="outline" size="sm">{r.recommendation.replace("_", " ")}</Badge>}
                </Group>
                <Text size="sm">{r.start_date} → {r.end_date} · {r.days} day(s)</Text>
                <Text size="sm" c="dimmed">{r.purpose}</Text>
              </Stack>
              <Group gap="xs">
                {actions(r).map((a) => (
                  <Button key={a.label} size="xs" variant="light" color={a.color} loading={busy} onClick={a.go}>
                    {a.label}
                  </Button>
                ))}
              </Group>
            </Group>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
