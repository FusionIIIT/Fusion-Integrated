import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Text, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDecide, useQueue, useRespondSubstitute,
} from "../api/hooks";
import type { LeaveRequest, TaskWithRequest } from "../api/types";

function requestSummary(t: TaskWithRequest): string {
  const r = t.request as LeaveRequest;
  return `${r?.category ?? "?"} · ${r?.user_id} · ${r?.start_date ?? "?"} → ${r?.end_date ?? "?"} · ${r?.days ?? "?"} day(s)`;
}

export default function TasksPage() {
  const { data, isPending, error } = useQueue();
  const decide = useDecide();
  const respond = useRespondSubstitute();
  const [pending, setPending] = useState<
    { task: TaskWithRequest; action: "decide" | "respond" } | null>(null);
  const [outcome, setOutcome] = useState<string>("approve");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const tasks = data ?? [];

  function act() {
    if (!pending) return;
    const { task, action } = pending;
    if (action === "respond") {
      respond.mutate(
        { taskId: task.id, accept: outcome === "accept" },
        {
          onSuccess: () => {
            notifications.show({ color: "green", title: "Recorded", message: "Your response was recorded." });
            setPending(null);
          },
          onError: (e) => notifications.show({ color: "red", title: "Could not respond", message: errorMessage(e) }),
        },
      );
      return;
    }
    decide.mutate(
      { taskId: task.id, outcome },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Decided", message: "The request advanced." });
          setPending(null);
        },
        onError: (e) => notifications.show({ color: "red", title: "Could not decide", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Tasks"
        subtitle="What waits on you: reviews, routing and sanctioning decisions"
      />
      {isPending ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <Stack>
          {tasks.map((t) => (
            <Card key={t.id} withBorder radius="md" p="md">
              <Group justify="space-between">
                <Title order={5}>{t.task_class.replace(/_/g, " ")}</Title>
                <Badge variant="light">{t.assignee_role.replace(/_/g, " ")}</Badge>
              </Group>
              <Text size="sm" c="dimmed">{requestSummary(t)}</Text>
              {t.escalated_at && (
                <Badge color="red" variant="light">escalated</Badge>
              )}
              <Group mt="xs">
                {t.task_class === "substitute_response" ? (
                  <>
                    <Button size="xs" onClick={() => { setOutcome("accept"); setPending({ task: t, action: "respond" }); }}>
                      Accept
                    </Button>
                    <Button size="xs" variant="light" color="red" onClick={() => { setOutcome("decline"); setPending({ task: t, action: "respond" }); }}>
                      Decline
                    </Button>
                  </>
                ) : t.task_class === "unit_head_review" ? (
                  <Button size="xs" onClick={() => { setOutcome("approve"); setPending({ task: t, action: "decide" }); }}>
                    Review
                  </Button>
                ) : t.task_class === "establishment_routing" ? (
                  <Button size="xs" onClick={() => { setOutcome("forward"); setPending({ task: t, action: "decide" }); }}>
                    Route
                  </Button>
                ) : (
                  <Button size="xs" onClick={() => { setOutcome("approve"); setPending({ task: t, action: "decide" }); }}>
                    Decide
                  </Button>
                )}
              </Group>
            </Card>
          ))}
          {tasks.length === 0 && (
            <Text c="dimmed">Nothing waits on you right now.</Text>
          )}
        </Stack>
      )}

      <FormModal
        opened={pending !== null}
        onClose={() => setPending(null)}
        title={pending?.action === "respond"
          ? "Answer the assignment"
          : `Decision — ${pending?.task.task_class.replace(/_/g, " ")}`}
        onSubmit={act}
        submitLabel="Confirm"
        submitting={decide.isPending || respond.isPending}
      >
        <Stack>
          {pending?.task.task_class === "unit_head_review"
            && pending.action === "decide" ? (
            <Select
              label="Outcome"
              data={[
                { value: "approve", label: "Approve" },
                { value: "reject", label: "Reject" },
                { value: "recommended", label: "Recommend" },
                { value: "not_recommended", label: "Not recommended" },
              ]}
              value={outcome}
              onChange={(v) => setOutcome(v ?? "approve")}
            />
          ) : pending?.action === "decide" && outcome !== "forward" ? (
            <Select
              label="Outcome"
              data={[
                { value: "approve", label: "Approve" },
                { value: "reject", label: "Reject" },
              ]}
              value={outcome}
              onChange={(v) => setOutcome(v ?? "approve")}
            />
          ) : null}
          {pending?.action === "respond" && (
            <Text size="sm">
              {outcome === "accept"
                ? "Accept responsibility for this period."
                : "Decline — the applicant will nominate a replacement or withdraw."}
            </Text>
          )}
        </Stack>
      </FormModal>
    </Container>
  );
}
