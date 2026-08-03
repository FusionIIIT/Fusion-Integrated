import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Text,
  Textarea, TextInput,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePostings, useRounds, useScheduleRound } from "../api/hooks";
import type { InterviewRound } from "../api/types";

const KINDS = [
  { value: "test", label: "Written / online test" },
  { value: "gd", label: "Group discussion" },
  { value: "tech", label: "Technical interview" },
  { value: "hr", label: "HR interview" },
  { value: "other", label: "Other" },
];

export default function InterviewsPage() {
  const { data, isPending, error } = useRounds();
  const [scheduling, setScheduling] = useState(false);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Interviews"
        subtitle="Scheduled rounds. Shortlisted candidates are notified automatically."
        action={
          <Button leftSection={<FaPlus size={12} />}
            onClick={() => setScheduling(true)}>
            Schedule a round
          </Button>
        }
      />

      <Card padding="lg">
        <DataTable<InterviewRound>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            { key: "seq", header: "Round", align: "right",
              render: (r) => `#${r.seq}` },
            {
              key: "kind", header: "Type",
              render: (r) => (
                <Badge variant="default" size="sm">
                  {KINDS.find((k) => k.value === r.kind)?.label ?? r.kind}
                </Badge>
              ),
            },
            {
              key: "mode", header: "Mode",
              render: (r) => (
                <Badge color={r.mode === "online" ? "blue" : "grape"}
                  variant="light" size="sm">
                  {r.mode}
                </Badge>
              ),
            },
            { key: "starts_at", header: "When",
              render: (r) => new Date(r.starts_at).toLocaleString() },
            {
              key: "where", header: "Where",
              render: (r) => (
                <Text size="sm" lineClamp={1}>
                  {r.mode === "online" ? r.meeting_url : r.venue}
                </Text>
              ),
            },
            { key: "capacity", header: "Capacity", align: "right",
              render: (r) => r.capacity?.toString() ?? "—" },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No rounds scheduled",
            description: "Schedule a round, then add shortlisted candidates.",
          }}
        />
      </Card>

      <ScheduleModal opened={scheduling} onClose={() => setScheduling(false)} />
    </Container>
  );
}

function ScheduleModal({ opened, onClose }: {
  opened: boolean; onClose: () => void;
}) {
  const postings = usePostings();
  const schedule = useScheduleRound();

  const [postingId, setPostingId] = useState<string | null>(null);
  const [kind, setKind] = useState<string | null>("tech");
  const [mode, setMode] = useState<string | null>("online");
  const [startsAt, setStartsAt] = useState<Date | null>(null);
  const [venue, setVenue] = useState("");
  const [url, setUrl] = useState("");
  const [capacity, setCapacity] = useState<number | string>("");
  const [instructions, setInstructions] = useState("");

  // Online needs a link, offline a venue; the database enforces this too.
  const locationOk = mode === "online" ? url.trim() !== "" : venue.trim() !== "";

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Schedule an interview round"
      subtitle="Date, time slot and mode are all recorded"
      onSubmit={() => schedule.mutate(
        {
          posting_id: postingId ? Number(postingId) : undefined,
          kind, mode,
          starts_at: startsAt ? startsAt.toISOString() : undefined,
          venue, meeting_url: url,
          capacity: capacity === "" ? null : Number(capacity),
          instructions,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green", title: "Round scheduled",
              message: "Add shortlisted candidates to notify them.",
            });
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not schedule", message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Schedule" submitting={schedule.isPending}
      error={schedule.error}
      disabled={!postingId || !startsAt || !locationOk}
    >
      <Stack gap="md">
        <Select
          label="Posting" required searchable value={postingId}
          onChange={setPostingId}
          data={(postings.data?.results ?? []).map((p) => ({
            value: String(p.id), label: `${p.title} — ${p.company?.name}`,
          }))}
        />
        <Group grow>
          <Select label="Round type" data={KINDS} value={kind} onChange={setKind} />
          <Select
            label="Mode" required value={mode} onChange={setMode}
            data={[{ value: "online", label: "Online" },
              { value: "offline", label: "Offline" }]}
          />
        </Group>
        <DateTimePicker
          label="Starts at" required value={startsAt} onChange={setStartsAt}
        />
        {mode === "online" ? (
          <TextInput
            label="Meeting link" required value={url}
            onChange={(e) => setUrl(e.currentTarget.value)}
            placeholder="https://…"
          />
        ) : (
          <TextInput
            label="Venue" required value={venue}
            onChange={(e) => setVenue(e.currentTarget.value)}
          />
        )}
        <NumberInput
          label="Capacity" value={capacity} onChange={setCapacity} min={1}
          description="Leave blank for no limit"
        />
        <Textarea
          label="Instructions for candidates" autosize minRows={2}
          value={instructions}
          onChange={(e) => setInstructions(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
