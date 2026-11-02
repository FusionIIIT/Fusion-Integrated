import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Text, Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateFeedback, useFeedback, useFeedbackAction } from "../api/hooks";
import type { Feedback } from "../api/types";

function FeedbackCard({ row, canReview, role, onAction, busy }: {
  row: Feedback; canReview: boolean; role: string;
  onAction: (payload: Record<string, string>) => void; busy: boolean;
}) {
  const [category, setCategory] = useState(row.category);
  const [disposition, setDisposition] = useState("");
  const initialReview = role === "dept_admin" && row.status === "new";
  const terminalReview = canReview && row.status === "under_review";

  return (
    <Card withBorder padding="md">
      <Stack gap="xs">
        <Group justify="space-between">
          <Text fw={600}>Feedback #{row.id}</Text>
          <Badge color={row.status === "new" ? "orange"
            : row.status === "under_review" ? "blue" : "green"}>
            {row.status.replaceAll("_", " ")}
          </Badge>
        </Group>
        <Text style={{ whiteSpace: "pre-wrap" }}>{row.body}</Text>
        {row.category && <Text size="sm" c="dimmed">Category: {row.category}</Text>}

        {initialReview && (
          <>
            <TextInput label="Category" value={category}
              onChange={(e) => setCategory(e.currentTarget.value)} />
            <Select label="Optional initial disposition" clearable
              data={[{ value: "resolved", label: "Resolved" },
                { value: "closed", label: "Closed" }]}
              value={disposition || null} onChange={(value) => setDisposition(value ?? "")} />
            <Button size="xs" w="fit-content" loading={busy}
              disabled={!category.trim()}
              onClick={() => onAction({ category, disposition })}>
              Record initial review
            </Button>
          </>
        )}

        {terminalReview && (
          <>
            <Select label="Disposition"
              data={[{ value: "resolved", label: "Resolved" },
                { value: "closed", label: "Closed" }]}
              value={disposition || null} onChange={(value) => setDisposition(value ?? "")} />
            <Button size="xs" w="fit-content" loading={busy}
              disabled={!disposition}
              onClick={() => onAction({ disposition })}>
              Save disposition
            </Button>
          </>
        )}
      </Stack>
    </Card>
  );
}

export default function FeedbackPage() {
  const { can, session } = useAuth();
  const query = useFeedback();
  const create = useCreateFeedback();
  const action = useFeedbackAction();
  const [body, setBody] = useState("");
  const role = (session?.active_role ?? "").toLowerCase().replaceAll(" ", "_");
  const canSubmit = can("department.feedback.create");
  const canReview = can("department.feedback.review");

  if (query.error) return <Container size="md"><ErrorState error={query.error} /></Container>;

  function submit() {
    create.mutate({ body: body.trim() }, {
      onSuccess: () => {
        setBody("");
        notifications.show({ title: "Feedback submitted", message: "Your submission is confidential." });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not submit feedback", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="md">
      <PageHeader title="Department feedback"
        subtitle="Only you and authorized feedback handlers can see your submission." />

      {canSubmit && (
        <Card withBorder padding="lg" mb="lg">
          <Stack>
            <Text fw={700}>Submit confidential feedback</Text>
            <Textarea label="Your message" minRows={4} maxLength={5000}
              value={body} onChange={(e) => setBody(e.currentTarget.value)} />
            <Button w="fit-content" onClick={submit} loading={create.isPending}
              disabled={!body.trim()}>Submit feedback</Button>
          </Stack>
        </Card>
      )}

      <Stack gap="sm">
        <Text fw={700}>Feedback records</Text>
        {query.isPending && <Text c="dimmed">Loading feedback…</Text>}
        {!query.isPending && (query.data ?? []).length === 0 && (
          <Card withBorder><Text c="dimmed">No feedback to show.</Text></Card>
        )}
        {(query.data ?? []).map((row) => (
          <FeedbackCard key={row.id} row={row} canReview={canReview}
            role={role} busy={action.isPending}
            onAction={(payload) => action.mutate({ id: row.id, payload }, {
              onError: (e) => notifications.show({
                color: "red", title: "Could not update feedback", message: errorMessage(e),
              }),
            })} />
        ))}
      </Stack>
    </Container>
  );
}
