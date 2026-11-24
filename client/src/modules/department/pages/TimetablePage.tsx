import { Button, Group, NumberInput, Select, SimpleGrid, Table, TextInput } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDeleteSlot, useEditSlot, useProfiles, useTimetable, useUploadSlots } from "../api/hooks";
import type { TimetableSlot, TimetableSlotInput } from "../api/types";
import { ActionError, PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const BLANK: TimetableSlotInput = {
  kind: "class", programme: "", batch_year: null, course_code: "", day_of_week: 0,
  starts_at: "09:00", ends_at: "10:00", room: "", instructor_user_id: null,
};

type SlotForm = TimetableSlotInput & { id?: number };

export default function TimetablePage() {
  const can = useCanAct();
  const { data, isPending, error } = useTimetable();
  const remove = useDeleteSlot();
  const { dialog: form, setDialog: setForm, opened } = useDialog<SlotForm>();
  const rows = data ?? [];

  return (
    <PageBody
      isPending={isPending} error={error} isEmpty={rows.length === 0} emptyTitle="No timetable published yet"
      header={(
        <PageHeader
          title="Timetable" subtitle="Class and lab slots; overlapping slots are never saved"
          action={can("department.timetable.create") && <Button onClick={() => setForm(BLANK)}>Add slot</Button>}
        />
      )}
      overlays={<SlotDialog form={form} opened={opened} setForm={setForm} />}
    >
      <ActionError errors={[remove.error]} />
      <SlotTable rows={rows} onEdit={(s) => setForm({ ...s, starts_at: s.starts_at.slice(0, 5), ends_at: s.ends_at.slice(0, 5) })}
        onRemove={(id) => remove.mutate(id)} />
    </PageBody>
  );
}

function SlotDialog({ form, opened, setForm }: {
  form: SlotForm | null; opened: boolean; setForm: (f: SlotForm | null) => void;
}) {
  const upload = useUploadSlots();
  const edit = useEditSlot();
  const save = form?.id ? edit : upload;

  function submit() {
    if (!form) return;
    const done = { onSuccess: () => setForm(null) };
    const { id, ...slot } = form;
    if (id) edit.mutate({ id, ...slot }, done);
    else upload.mutate([slot], done);
  }

  return (
    <FormModal
      opened={opened} onClose={() => setForm(null)} onSubmit={submit}
      title={form?.id ? "Edit slot" : "Add slot"} submitting={save.isPending} error={save.error}
    >
      {form && (
        <SimpleGrid cols={2}>
          <Select label="Kind" allowDeselect={false} value={form.kind}
            data={[{ value: "class", label: "Class" }, { value: "lab", label: "Lab" }]}
            onChange={(v) => setForm({ ...form, kind: v === "lab" ? "lab" : "class" })} />
          <TextInput label="Course code" value={form.course_code}
            onChange={(e) => setForm({ ...form, course_code: e.currentTarget.value })} />
          <Select label="Day" allowDeselect={false} value={String(form.day_of_week)}
            data={DAYS.map((d, i) => ({ value: String(i), label: d }))}
            onChange={(v) => setForm({ ...form, day_of_week: Number(v ?? 0) })} />
          <TextInput label="Room" value={form.room} onChange={(e) => setForm({ ...form, room: e.currentTarget.value })} />
          <TextInput label="Starts (HH:MM)" value={form.starts_at}
            onChange={(e) => setForm({ ...form, starts_at: e.currentTarget.value })} />
          <TextInput label="Ends (HH:MM)" value={form.ends_at}
            onChange={(e) => setForm({ ...form, ends_at: e.currentTarget.value })} />
          <TextInput label="Programme" value={form.programme}
            onChange={(e) => setForm({ ...form, programme: e.currentTarget.value })} />
          <NumberInput label="Batch year" value={form.batch_year ?? ""}
            onChange={(v) => setForm({ ...form, batch_year: typeof v === "number" ? v : null })} />
          <InstructorSelect value={form.instructor_user_id ?? null}
            onChange={(id) => setForm({ ...form, instructor_user_id: id })} />
        </SimpleGrid>
      )}
    </FormModal>
  );
}

// AFR-DEPT-026 (Q2): the Students of this programme and batch are this Faculty member's course.
function InstructorSelect({ value, onChange }: { value: number | null; onChange: (id: number | null) => void }) {
  const { data } = useProfiles();
  const faculty = (data?.results ?? []).filter((p) => p.kind === "faculty" && p.user_id != null && p.is_active);
  return (
    <Select label="Instructor" placeholder="Not set" clearable value={value == null ? null : String(value)}
      data={faculty.map((p) => ({ value: String(p.user_id), label: p.display_name }))}
      onChange={(v) => onChange(v ? Number(v) : null)} />
  );
}

function SlotTable({ rows, onEdit, onRemove }: {
  rows: TimetableSlot[]; onEdit: (s: TimetableSlot) => void; onRemove: (id: number) => void;
}) {
  const can = useCanAct();
  return (
    <Table striped withTableBorder>
      <Table.Thead>
        <Table.Tr><Table.Th>Day</Table.Th><Table.Th>Time</Table.Th><Table.Th>Course</Table.Th>
          <Table.Th>Kind</Table.Th><Table.Th>Room</Table.Th><Table.Th>For</Table.Th><Table.Th /></Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.map((s) => (
          <Table.Tr key={s.id}>
            <Table.Td>{DAYS[s.day_of_week]}</Table.Td>
            <Table.Td>{s.starts_at.slice(0, 5)}–{s.ends_at.slice(0, 5)}</Table.Td>
            <Table.Td>{s.course_code}</Table.Td>
            <Table.Td>{s.kind}</Table.Td>
            <Table.Td>{s.room}</Table.Td>
            <Table.Td>{[s.programme, s.batch_year].filter(Boolean).join(" ") || "All"}</Table.Td>
            <Table.Td>
              {can("department.timetable.update") && (
                <Group gap="xs">
                  <Button size="xs" variant="light" onClick={() => onEdit(s)}>Edit</Button>
                  <Button size="xs" variant="light" color="red" onClick={() => onRemove(s.id)}>Remove</Button>
                </Group>
              )}
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
