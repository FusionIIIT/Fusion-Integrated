import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useFeedback, useMoveFeedback, useSubmitFeedback } from "../api/hooks";
import type { Feedback, FeedbackStatus } from "../api/types";

const STATUS: Record<FeedbackStatus, { label: string; color: string }> = {
  new: { label: "New", color: "blue" },
  under_review: { label: "Under review", color: "yellow" },
  resolved: { label: "Resolved", color: "green" },
  closed: { label: "Closed", color: "gray" },
};

type Action = { feedback: Feedback; to: "under_review" | "resolved" | "closed" };

export default function FeedbackPage() {
  const { data, isPending, error } = useFeedback();
  const { can } = useAuth();
  const move = useMoveFeedback();
  const [writing, setWriting] = useState(false);
  const [action, setAction] = useState<Action | null>(null);
  const [text, setText] = useState("");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const canReview = can("dept.feedback.review");
  const canResolve = can("dept.feedback.resolve");
  const rows = data ?? [];
  const reviewing = action?.to === "under_review";

  const begin = (feedback: Feedback, to: Action["to"]) => {
    setAction({ feedback, to });
    setText(to === "under_review" ? feedback.category : "");
  };

  return (
    <Container size="md">
      <PageHeader
        title="Feedback"
        subtitle="Confidential — visible only to you and the people handling it"
        action={can("dept.feedback.create") && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setWriting(true)}>
            Give feedback
          </Button>
        )}
      />

      {isPending && <Text c="dimmed">Loading…</Text>}
      {!isPending && rows.length === 0 && (
        <Card padding="xl"><Text ta="center" fw={600}>No feedback to show</Text></Card>
      )}

      <Stack gap="md">
        {rows.map((f) => {
          const open = f.status === "new" || f.status === "under_review";
          return (
            <Card key={f.id} padding="lg" withBorder>
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Stack gap={4} style={{ flex: 1 }}>
                  <Group gap="xs">
                    <Text fw={700}>{f.subject}</Text>
                    <Badge variant="light" color={STATUS[f.status].color} size="sm">
                      {STATUS[f.status].label}
                    </Badge>
                    {f.category && <Badge variant="outline" size="sm">{f.category}</Badge>}
                  </Group>
                  <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{f.body}</Text>
                  {f.resolution_note && (
                    <Text size="sm" c="dimmed">Outcome: {f.resolution_note}</Text>
                  )}
                  <Text size="xs" c="dimmed">
                    {new Date(f.created_at).toLocaleString()} · from a {f.submitted_by_role}
                  </Text>
                </Stack>
                <Stack gap={4}>
                  {f.status === "new" && canReview && (
                    <Button size="xs" onClick={() => begin(f, "under_review")}>
                      Start review
                    </Button>
                  )}
                  {f.status === "under_review" && (canReview || canResolve) && open && (
                    <>
                      <Button size="xs" color="green"
                              onClick={() => begin(f, "resolved")}>Resolve</Button>
                      <Button size="xs" variant="default"
                              onClick={() => begin(f, "closed")}>Close</Button>
                    </>
                  )}
                </Stack>
              </Group>
            </Card>
          );
        })}
      </Stack>

      <SubmitModal opened={writing} onClose={() => setWriting(false)} />

      <FormModal
        opened={action != null} onClose={() => setAction(null)}
        title={reviewing ? "Initial review"
          : action?.to === "resolved" ? "Resolve feedback" : "Close feedback"}
        subtitle={action?.feedback.subject}
        submitLabel={reviewing ? "Mark under review" : "Confirm"}
        submitting={move.isPending} disabled={!text.trim()}
        onSubmit={() => action && move.mutate(
          { id: action.feedback.id, to_status: action.to,
            ...(reviewing ? { category: text } : { note: text }) },
          { onSuccess: () => setAction(null),
            onError: (e) => notifications.show({
              color: "red", title: "Could not update", message: errorMessage(e) }) },
        )}
      >
        {reviewing ? (
          <TextInput label="Category" required value={text}
                     placeholder="e.g. Infrastructure, Academics"
                     onChange={(e) => setText(e.currentTarget.value)} />
        ) : (
          <Textarea label="How was this handled?" required autosize minRows={3}
                    maxLength={500} value={text}
                    onChange={(e) => setText(e.currentTarget.value)} />
        )}
      </FormModal>
    </Container>
  );
}

function SubmitModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const submit = useSubmitFeedback();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  return (
    <FormModal
      opened={opened} onClose={onClose} title="Give feedback"
      subtitle="Only you and the department administrators can read this"
      submitLabel="Submit" submitting={submit.isPending}
      disabled={!subject.trim() || !body.trim()} error={submit.error}
      onSubmit={() => submit.mutate({ subject, body }, {
        onSuccess: () => { setSubject(""); setBody(""); onClose(); },
      })}
    >
      <Stack>
        <TextInput label="Subject" required maxLength={200} value={subject}
                   onChange={(e) => setSubject(e.currentTarget.value)} />
        <Textarea label="Message" required autosize minRows={4} value={body}
                  onChange={(e) => setBody(e.currentTarget.value)} />
      </Stack>
    </FormModal>
  );
}
