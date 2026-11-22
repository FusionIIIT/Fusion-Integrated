import { Button, Group, NumberInput, Select, SimpleGrid, Table, TextInput } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDeleteSlot, useEditSlot, useTimetable, useUploadSlots } from "../api/hooks";
import type { TimetableSlotInput } from "../api/types";
import { ActionError, PageBody, useDialog } from "../components/PageBody";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const BLANK: TimetableSlotInput = {
  kind: "class", programme: "", batch_year: null, course_code: "", day_of_week: 0,
  starts_at: "09:00", ends_at: "10:00", room: "",
};

export default function TimetablePage() {
  const { can } = useAuth();
  const { data, isPending, error } = useTimetable();
  const upload = useUploadSlots();
  const edit = useEditSlot();
  const remove = useDeleteSlot();
  const { dialog: form, setDialog: setForm, opened } = useDialog<TimetableSlotInput & { id?: number }>();
  const rows = data ?? [];
  const save = form?.id ? edit : upload;

  function submit() {
    if (!form) return;
    const done = { onSuccess: () => setForm(null) };
    const { id, ...slot } = form;
    if (id) edit.mutate({ id, ...slot }, done);
    else upload.mutate([slot], done);
  }

  return (
    <PageBody
      isPending={isPending} error={error} isEmpty={rows.length === 0} emptyTitle="No timetable published yet"
      header={(
        <PageHeader
          title="Timetable" subtitle="Class and lab slots; overlapping slots are never saved"
          action={can("department.timetable.create") && <Button onClick={() => setForm(BLANK)}>Add slot</Button>}
        />
      )}
      overlays={(
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
            </SimpleGrid>
          )}
        </FormModal>
      )}
    >
      <ActionError errors={[remove.error]} />
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
                    <Button size="xs" variant="light" onClick={() => setForm({ ...s, starts_at: s.starts_at.slice(0, 5),
                      ends_at: s.ends_at.slice(0, 5) })}>Edit</Button>
                    <Button size="xs" variant="light" color="red" onClick={() => remove.mutate(s.id)}>Remove</Button>
                  </Group>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </PageBody>
  );
}
