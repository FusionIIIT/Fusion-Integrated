import { Badge, Button, Card, Group, Select, Stack, Text, TextInput, Textarea } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAddFeedbackNote, useDisposeFeedback, useFeedback, useReviewFeedback, useSubmitFeedback,
} from "../api/hooks";
import { FEEDBACK_CATEGORIES, type Feedback } from "../api/types";
import { PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

type Dialog =
  | { kind: "submit"; subject: string; body: string }
  | { kind: "review"; fb: Feedback; category: string; disposition: string; note: string }
  | { kind: "dispose"; fb: Feedback; outcome: "resolved" | "closed"; note: string }
  | { kind: "note"; fb: Feedback; body: string };

const TITLES = { submit: "Submit feedback", review: "Initial review", dispose: "Resolve or close", note: "Add oversight note" };

export default function FeedbackPage() {
  const can = useCanAct();
  const { data, isPending, error } = useFeedback();
  const submitFb = useSubmitFeedback();
  const review = useReviewFeedback();
  const dispose = useDisposeFeedback();
  const note = useAddFeedbackNote();
  const { dialog: dialog, setDialog: setDialog, opened } = useDialog<Dialog>();
  const rows = data?.results ?? [];
  const active = { submit: submitFb, review, dispose, note }[dialog?.kind ?? "submit"];

  function submit() {
    if (!dialog) return;
    const done = { onSuccess: () => setDialog(null) };
    if (dialog.kind === "submit") submitFb.mutate({ subject: dialog.subject, body: dialog.body }, done);
    if (dialog.kind === "review") {
      review.mutate({ id: dialog.fb.id, category: dialog.category, disposition: dialog.disposition, note: dialog.note }, done);
    }
    if (dialog.kind === "dispose") dispose.mutate({ id: dialog.fb.id, outcome: dialog.outcome, note: dialog.note }, done);
    if (dialog.kind === "note") note.mutate({ id: dialog.fb.id, body: dialog.body }, done);
  }

  return (
    <PageBody
      isPending={isPending} error={error} isEmpty={rows.length === 0} emptyTitle="No feedback to show"
      header={(
        <PageHeader
          title="Feedback" subtitle="Confidential: only you and the department office see your feedback"
          action={can("department.feedback.create") && (
            <Button onClick={() => setDialog({ kind: "submit", subject: "", body: "" })}>Submit feedback</Button>
          )}
        />
      )}
      overlays={(
        <FormModal
          opened={opened} onClose={() => setDialog(null)} onSubmit={submit}
          title={dialog ? TITLES[dialog.kind] : ""} submitting={active.isPending} error={active.error}
        >
          {dialog?.kind === "submit" && (
            <Stack>
              <TextInput label="Subject" value={dialog.subject}
                onChange={(e) => setDialog({ ...dialog, subject: e.currentTarget.value })} />
              <Textarea label="Feedback" minRows={4} value={dialog.body}
                onChange={(e) => setDialog({ ...dialog, body: e.currentTarget.value })} />
            </Stack>
          )}
          {dialog?.kind === "review" && (
            <Stack>
              <Select label="Category (optional)" clearable value={dialog.category || null}
                data={FEEDBACK_CATEGORIES.map((c) => ({ value: c, label: c }))}
                onChange={(v) => setDialog({ ...dialog, category: v ?? "" })} />
              <Select label="Close now as a simple issue (optional)" clearable value={dialog.disposition || null}
                data={[{ value: "resolved", label: "Resolved" }, { value: "closed", label: "Closed" }]}
                onChange={(v) => setDialog({ ...dialog, disposition: v ?? "" })} />
              <Textarea label="Note to the submitter" value={dialog.note}
                onChange={(e) => setDialog({ ...dialog, note: e.currentTarget.value })} />
            </Stack>
          )}
          {dialog?.kind === "dispose" && (
            <Stack>
              <Select label="Outcome" allowDeselect={false} value={dialog.outcome}
                data={[{ value: "resolved", label: "Resolved" }, { value: "closed", label: "Closed" }]}
                onChange={(v) => setDialog({ ...dialog, outcome: v === "closed" ? "closed" : "resolved" })} />
              <Textarea label="Note to the submitter" value={dialog.note}
                onChange={(e) => setDialog({ ...dialog, note: e.currentTarget.value })} />
            </Stack>
          )}
          {dialog?.kind === "note" && (
            <Textarea label="Oversight note" value={dialog.body}
              onChange={(e) => setDialog({ ...dialog, body: e.currentTarget.value })} />
          )}
        </FormModal>
      )}
    >
      <Stack gap="md">
        {rows.map((fb) => (
          <Card key={fb.id} withBorder padding="lg">
            <Group justify="space-between" align="flex-start">
              <Stack gap={4} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={600}>{fb.subject}</Text>
                  <StatusBadge status={fb.status} />
                  {fb.category && <Badge variant="outline">{fb.category}</Badge>}
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{fb.body}</Text>
                {fb.resolution_note && <Text size="sm" c="dimmed">Outcome: {fb.resolution_note}</Text>}
                {fb.notes.map((n) => <Text key={n.id} size="xs" c="dimmed">Note: {n.body}</Text>)}
              </Stack>
              <Group gap="xs">
                {fb.status === "new" && can("department.feedback.review") && (
                  <Button size="xs" onClick={() => setDialog({ kind: "review", fb, category: "", disposition: "", note: "" })}>
                    Review
                  </Button>
                )}
                {fb.status === "under_review" && can("department.feedback_resolution.create") && (
                  <>
                    <Button size="xs" onClick={() => setDialog({ kind: "dispose", fb, outcome: "resolved", note: "" })}>
                      Resolve or close
                    </Button>
                    <Button size="xs" variant="light" onClick={() => setDialog({ kind: "note", fb, body: "" })}>
                      Add note
                    </Button>
                  </>
                )}
              </Group>
            </Group>
          </Card>
        ))}
      </Stack>
    </PageBody>
  );
}
