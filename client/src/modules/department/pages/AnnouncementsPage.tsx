import { useState } from "react";
import { Badge, Button, Card, Group, NumberInput, Select, Stack, Text, TextInput, Textarea } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAnnouncements, useDeleteAnnouncement, useEditAnnouncement, useHideAnnouncement,
  usePublishAnnouncement,
} from "../api/hooks";
import type { Announcement, AnnouncementInput, AudienceRole } from "../api/types";
import { ActionError, PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

const AUDIENCES = [
  { value: "all", label: "Everyone" },
  { value: "student", label: "Students" },
  { value: "faculty", label: "Faculty" },
  { value: "dept_admin", label: "Dept_Admin" },
  { value: "hod", label: "HOD" },
];

const BLANK: AnnouncementInput = { title: "", body: "", audience_role: "all", programme: "", batch_year: null };

export default function AnnouncementsPage() {
  const { data, isPending, error } = useAnnouncements();
  const can = useCanAct();
  const hide = useHideAnnouncement();
  const remove = useDeleteAnnouncement();
  const { dialog: form, setDialog: setForm, opened } = useDialog<AnnouncementInput>();
  const [editing, setEditing] = useState<Announcement | null>(null);
  const rows = data?.results ?? [];
  const close = () => { setForm(null); setEditing(null); };

  function startEdit(a: Announcement) {
    setEditing(a);
    setForm({ title: a.title, body: a.body, audience_role: a.audience_role, programme: a.programme, batch_year: a.batch_year });
  }

  return (
    <PageBody
      isPending={isPending} error={error} isEmpty={rows.length === 0}
      emptyTitle="No announcements for you yet"
      overlays={<AnnouncementDialog form={form} editing={editing} opened={opened} setForm={setForm} onClose={close} />}
      header={(
        <PageHeader
          title="Announcements" subtitle="Department notices for your role, programme and year"
          action={can("department.announcement.create") && (
            <Button onClick={() => { setEditing(null); setForm(BLANK); }}>Publish announcement</Button>
          )}
        />
      )}
    >
      <ActionError errors={[hide.error, remove.error]} />
      <Stack gap="md">
        {rows.map((a) => (
          <AnnouncementCard key={a.id} a={a} onEdit={startEdit} onHide={(id) => hide.mutate(id)}
            onDelete={(id) => remove.mutate(id)} />
        ))}
      </Stack>
    </PageBody>
  );
}

function AnnouncementDialog({ form, editing, opened, setForm, onClose }: {
  form: AnnouncementInput | null; editing: Announcement | null; opened: boolean;
  setForm: (f: AnnouncementInput) => void; onClose: () => void;
}) {
  const publish = usePublishAnnouncement();
  const edit = useEditAnnouncement();
  const save = editing ? edit : publish;

  function submit() {
    if (!form) return;
    const done = { onSuccess: onClose };
    if (editing) edit.mutate({ id: editing.id, ...form }, done);
    else publish.mutate(form, done);
  }

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title={editing ? "Edit announcement" : "Publish announcement"}
      submitLabel={editing ? "Save" : "Publish"} onSubmit={submit}
      submitting={save.isPending} error={save.error}
    >
      {form && (
        <Stack>
          <TextInput label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.currentTarget.value })} />
          <Textarea label="Text" minRows={4} value={form.body}
            onChange={(e) => setForm({ ...form, body: e.currentTarget.value })} />
          <Select label="Audience" data={AUDIENCES} value={form.audience_role} allowDeselect={false}
            onChange={(v) => setForm({ ...form, audience_role: (v ?? "all") as AudienceRole })} />
          <TextInput label="Programme (empty for all)" value={form.programme}
            onChange={(e) => setForm({ ...form, programme: e.currentTarget.value })} />
          <NumberInput label="Batch year (empty for all)" value={form.batch_year ?? ""}
            onChange={(v) => setForm({ ...form, batch_year: typeof v === "number" ? v : null })} />
        </Stack>
      )}
    </FormModal>
  );
}

function AnnouncementCard({ a, onEdit, onHide, onDelete }: {
  a: Announcement; onEdit: (a: Announcement) => void; onHide: (id: number) => void; onDelete: (id: number) => void;
}) {
  const can = useCanAct();
  return (
    <Card withBorder padding="lg">
      <Group justify="space-between" align="flex-start">
        <Stack gap={4} style={{ flex: 1 }}>
          <Group gap="xs">
            <Text fw={600}>{a.title}</Text>
            <Badge variant="light">{a.audience_role}</Badge>
            {a.status === "hidden" && <Badge color="gray">hidden</Badge>}
          </Group>
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{a.body}</Text>
          <Text size="xs" c="dimmed">
            {[a.programme, a.batch_year].filter(Boolean).join(" · ") || "All programmes and years"}
          </Text>
        </Stack>
        {a.status === "active" && (
          <Group gap="xs">
            {can("department.announcement.update") && (
              <>
                <Button size="xs" variant="light" onClick={() => onEdit(a)}>Edit</Button>
                <Button size="xs" variant="light" color="gray" onClick={() => onHide(a.id)}>Hide</Button>
              </>
            )}
            {can("department.announcement.delete") && (
              <Button size="xs" variant="light" color="red" onClick={() => onDelete(a.id)}>Delete</Button>
            )}
          </Group>
        )}
      </Group>
    </Card>
  );
}
