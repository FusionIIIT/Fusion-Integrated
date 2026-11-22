import { Button, Container, FileInput, Group, NumberInput, Paper, Select, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";
import { useDepartmentAction, useDepartmentFeed, useDepartmentRecord } from "./api";
import { useDepartmentCan } from "./DepartmentLayout";
import { FeedState } from "./FeedState";

interface Slot {
  id: number; title: string; kind: string; term: string; day: number;
  starts_at: string; ends_at: string; programme: string; batch_year: number;
  room: string; instructor_id: number;
}
interface AcademicContext { programme: string; batch_year: number | null }

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function SlotEditor({ initial, close }: { initial?: Slot; close: () => void }) {
  const action = useDepartmentAction();
  const [slot, setSlot] = useState(initial ?? {
    title: "", kind: "class", term: "", day: 0, starts_at: "", ends_at: "", programme: "",
    batch_year: new Date().getFullYear(), room: "", instructor_id: 0,
  });
  const change = <K extends keyof typeof slot>(key: K, value: (typeof slot)[K]) =>
    setSlot((old) => ({ ...old, [key]: value }));
  const fields = [["title", "Class or lab title"], ["term", "Term"], ["programme", "Programme"], ["room", "Room"]] as const;

  return (
    <Paper withBorder p="md" component="form" onSubmit={(event) => {
      event.preventDefault();
      action.mutate(initial
        ? { path: `timetable/${initial.id}`, method: "put", data: slot }
        : { path: "timetable", data: { slots: [slot] } }, { onSuccess: close });
    }}>
      <Stack>
        {fields.map(([key, label]) => (
          <TextInput key={key} label={label} required value={slot[key]}
            onChange={(event) => change(key, event.currentTarget.value)} />
        ))}
        <Group grow>
          <Select label="Type" data={[{ value: "class", label: "Class" }, { value: "lab", label: "Lab" }]}
            value={slot.kind} allowDeselect={false} onChange={(value) => { if (value) change("kind", value); }} />
          <Select label="Day" data={days.map((label, index) => ({ label, value: String(index) }))}
            value={String(slot.day)} allowDeselect={false} onChange={(value) => change("day", Number(value))} />
        </Group>
        <Group grow>
          <TextInput label="Start time" type="time" required value={slot.starts_at.slice(0, 5)}
            onChange={(event) => change("starts_at", event.currentTarget.value)} />
          <TextInput label="End time" type="time" required value={slot.ends_at.slice(0, 5)}
            onChange={(event) => change("ends_at", event.currentTarget.value)} />
        </Group>
        <Group grow>
          <NumberInput label="Batch year" min={1900} max={2200} allowDecimal={false} required
            value={slot.batch_year || ""} onChange={(value) => change("batch_year", Number(value))} />
          <NumberInput label="Instructor ID" min={1} allowDecimal={false} required
            value={slot.instructor_id || ""} onChange={(value) => change("instructor_id", Number(value))} />
        </Group>
        <Group>
          <Button type="submit" loading={action.isPending}>Save timetable slot</Button>
          <Button variant="default" onClick={close}>Cancel</Button>
        </Group>
        {action.isError && <ErrorState error={action.error} />}
      </Stack>
    </Paper>
  );
}

function TimetableUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const action = useDepartmentAction();

  async function upload() {
    if (!file) return;
    setError("");
    try {
      const slots: unknown = JSON.parse(await file.text());
      if (!Array.isArray(slots)) throw new Error();
      action.mutate({ path: "timetable", data: { slots } }, { onSuccess: () => setFile(null) });
    } catch {
      setError("Choose a JSON file containing a list of timetable slots.");
    }
  }

  return (
    <Stack>
      <Group align="end">
        <FileInput label="Upload timetable (JSON)" accept="application/json,.json" value={file}
          onChange={setFile} error={error} />
        <Button variant="default" loading={action.isPending} disabled={!file} onClick={() => void upload()}>
          Upload timetable
        </Button>
      </Group>
      {action.isError && <ErrorState error={action.error} />}
    </Stack>
  );
}

export default function TimetablePage() {
  const can = useDepartmentCan();
  const editable = can("department.timetable.update");
  const [editor, setEditor] = useState<number | "new" | null>(null);
  const feed = useDepartmentFeed<Slot>("timetable");
  const context = useDepartmentRecord<AcademicContext>("academic-context", !editable);
  return (
    <Container size="md" py="lg">
      <PageHeader title="Academic timetable" />
      <Stack>
        {!editable && context.data?.programme && (
          <Text fw={600}>{context.data.programme}{context.data.batch_year && ` · Batch ${context.data.batch_year}`}</Text>
        )}
        {editable && <TimetableUpload />}
        {editable && editor === "new" && <SlotEditor close={() => setEditor(null)} />}
        {editable && editor !== "new" && (
          <Group><Button onClick={() => setEditor("new")}>Add timetable slot</Button></Group>
        )}
        {feed.rows.map((slot) => editor === slot.id
          ? <SlotEditor key={slot.id} initial={slot} close={() => setEditor(null)} />
          : (
            <Paper key={slot.id} withBorder p="md">
              <Group justify="space-between">
                <Stack gap={2}>
                  <Text fw={600}>{slot.title}</Text>
                  <Text>{days[slot.day]} · {slot.starts_at.slice(0, 5)}–{slot.ends_at.slice(0, 5)} · {slot.room}</Text>
                  <Text c="dimmed" size="sm">{slot.term} · {slot.programme} {slot.batch_year} · {slot.kind}</Text>
                </Stack>
                {editable && <Button variant="default" onClick={() => setEditor(slot.id)}>Edit</Button>}
              </Group>
            </Paper>
          ))}
        <FeedState query={feed} empty="There are no applicable timetable slots." />
      </Stack>
    </Container>
  );
}
