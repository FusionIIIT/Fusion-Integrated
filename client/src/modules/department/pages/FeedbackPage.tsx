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
  const { dialog, setDialog, opened } = useDialog<Dialog>();
  const rows = data?.results ?? [];

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
      overlays={<FeedbackDialog dialog={dialog} opened={opened} setDialog={setDialog} />}
    >
      <Stack gap="md">
        {rows.map((fb) => <FeedbackCard key={fb.id} fb={fb} onOpen={setDialog} />)}
      </Stack>
    </PageBody>
  );
}

function FeedbackDialog({ dialog, opened, setDialog }: {
  dialog: Dialog | null; opened: boolean; setDialog: (d: Dialog | null) => void;
}) {
  const submitFb = useSubmitFeedback();
  const review = useReviewFeedback();
  const dispose = useDisposeFeedback();
  const note = useAddFeedbackNote();
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
    <FormModal
      opened={opened} onClose={() => setDialog(null)} onSubmit={submit}
      title={dialog ? TITLES[dialog.kind] : ""} submitting={active.isPending} error={active.error}
    >
      {dialog && <DialogFields dialog={dialog} onChange={setDialog} />}
    </FormModal>
  );
}

const OUTCOMES = [{ value: "resolved", label: "Resolved" }, { value: "closed", label: "Closed" }];

function DialogFields({ dialog, onChange }: { dialog: Dialog; onChange: (d: Dialog) => void }) {
  if (dialog.kind === "submit") {
    return (
      <Stack>
        <TextInput label="Subject" value={dialog.subject}
          onChange={(e) => onChange({ ...dialog, subject: e.currentTarget.value })} />
        <Textarea label="Feedback" minRows={4} value={dialog.body}
          onChange={(e) => onChange({ ...dialog, body: e.currentTarget.value })} />
      </Stack>
    );
  }
  if (dialog.kind === "review") {
    return (
      <Stack>
        <Select label="Category (optional)" clearable value={dialog.category || null}
          data={FEEDBACK_CATEGORIES.map((c) => ({ value: c, label: c }))}
          onChange={(v) => onChange({ ...dialog, category: v ?? "" })} />
        <Select label="Close now as a simple issue (optional)" clearable value={dialog.disposition || null}
          data={OUTCOMES} onChange={(v) => onChange({ ...dialog, disposition: v ?? "" })} />
        <Textarea label="Note to the submitter" value={dialog.note}
          onChange={(e) => onChange({ ...dialog, note: e.currentTarget.value })} />
      </Stack>
    );
  }
  if (dialog.kind === "dispose") {
    return (
      <Stack>
        <Select label="Outcome" allowDeselect={false} value={dialog.outcome} data={OUTCOMES}
          onChange={(v) => onChange({ ...dialog, outcome: v === "closed" ? "closed" : "resolved" })} />
        <Textarea label="Note to the submitter" value={dialog.note}
          onChange={(e) => onChange({ ...dialog, note: e.currentTarget.value })} />
      </Stack>
    );
  }
  return (
    <Textarea label="Oversight note" value={dialog.body}
      onChange={(e) => onChange({ ...dialog, body: e.currentTarget.value })} />
  );
}

function FeedbackCard({ fb, onOpen }: { fb: Feedback; onOpen: (d: Dialog) => void }) {
  const can = useCanAct();
  return (
    <Card withBorder padding="lg">
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
            <Button size="xs" onClick={() => onOpen({ kind: "review", fb, category: "", disposition: "", note: "" })}>
              Review
            </Button>
          )}
          {fb.status === "under_review" && can("department.feedback_resolution.create") && (
            <>
              <Button size="xs" onClick={() => onOpen({ kind: "dispose", fb, outcome: "resolved", note: "" })}>
                Resolve or close
              </Button>
              <Button size="xs" variant="light" onClick={() => onOpen({ kind: "note", fb, body: "" })}>
                Add note
              </Button>
            </>
          )}
        </Group>
      </Group>
    </Card>
  );
}
