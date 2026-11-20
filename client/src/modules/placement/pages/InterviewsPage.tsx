import { useState } from "react";
import {
  Badge, Button, Card, Checkbox, Container, Group, NumberInput, Select, Stack, Text, TextInput, Textarea,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaPlus, FaUserPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAddCandidates, useApplications, usePostings, useRounds, useScheduleRound,
} from "../api/hooks";
import type { InterviewRound } from "../api/types";
import { LoadMore } from "../components/LoadMore";

const KINDS = [
  { value: "test", label: "Written / online test" },
  { value: "gd", label: "Group discussion" },
  { value: "tech", label: "Technical interview" },
  { value: "hr", label: "HR interview" },
  { value: "other", label: "Other" },
];

export default function InterviewsPage() {
  const list = useRounds();
  const { data, isPending, error } = list;
  const [scheduling, setScheduling] = useState(false);
  const [adding, setAdding] = useState<InterviewRound | null>(null);

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
          minWidth={860}
          columns={[
            {
              key: "role", header: "Role",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.posting_title}</Text>
                  <Text size="xs" c="dimmed">Round {r.seq}</Text>
                </Stack>
              ),
            },
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
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Button
                  size="xs" variant="light"
                  leftSection={<FaUserPlus size={10} />}
                  onClick={() => setAdding(r)}
                >
                  Add candidates
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No rounds scheduled",
            description: "Schedule a round, then add shortlisted candidates.",
          }}
        />
      </Card>

      <ScheduleModal opened={scheduling} onClose={() => setScheduling(false)} />
      <AddCandidatesModal round={adding} onClose={() => setAdding(null)} />
      <LoadMore list={list} />
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
          minDate={new Date()}
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

/** PC-UC-009 steps 2-4: put shortlisted candidates into a round, which notifies them. */
function AddCandidatesModal({ round, onClose }: {
  round: InterviewRound | null; onClose: () => void;
}) {
  const add = useAddCandidates();
  const { data } = useApplications(
    round ? { posting: round.posting, status: "shortlisted" } : undefined);
  const [picked, setPicked] = useState<number[]>([]);
  const rows = round ? data?.results ?? [] : [];

  function toggle(id: number) {
    setPicked((p) => p.includes(id) ? p.filter((x) => x !== id) : [...p, id]);
  }

  return (
    <FormModal
      opened={round != null}
      onClose={() => { setPicked([]); onClose(); }}
      title={`Add candidates to round #${round?.seq ?? ""}`}
      subtitle="Everyone you add is emailed the date, time and mode"
      onSubmit={() => round && add.mutate(
        { roundId: round.id, applicationIds: picked },
        {
          onSuccess: (d) => {
            notifications.show({
              color: "green", title: "Candidates scheduled",
              message: `${d.scheduled} candidate(s) notified.`,
            });
            setPicked([]);
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not schedule", message: errorMessage(e),
          }),
        },
      )}
      submitLabel={`Add ${picked.length || ""}`.trim()}
      submitting={add.isPending} error={add.error} disabled={!picked.length}
    >
      {rows.length === 0 ? (
        <Text size="sm" c="dimmed">
          No shortlisted candidates for this posting yet.
        </Text>
      ) : (
        <Stack gap="xs">
          {rows.map((a) => (
            <Checkbox
              key={a.id}
              checked={picked.includes(a.id)}
              onChange={() => toggle(a.id)}
              label={
                <Stack gap={0}>
                  <Text size="sm" fw={500}>{a.candidate?.name ?? `#${a.user_id}`}</Text>
                  <Text size="xs" c="dimmed">
                    {a.candidate?.roll_no}
                    {a.cpi_at_apply ? ` · CPI ${a.cpi_at_apply}` : ""}
                  </Text>
                </Stack>
              }
            />
          ))}
        </Stack>
      )}
    </FormModal>
  );
}
