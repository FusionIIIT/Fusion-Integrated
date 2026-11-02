import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, MultiSelect, Stack, Text, Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAnnouncementAction, useAnnouncements, useCreateAnnouncement,
} from "../api/hooks";
import type { Announcement } from "../api/types";

const ROLE_OPTIONS = [
  { value: "student", label: "Students" },
  { value: "faculty", label: "Faculty" },
  { value: "dept_admin", label: "Department administrators" },
  { value: "hod", label: "HOD" },
];

const emptyForm = {
  title: "", body: "", target_roles: [] as string[],
  programmes: "", academic_years: "",
};

function splitList(value: string) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

export default function AnnouncementsPage() {
  const { can } = useAuth();
  const { data = [], error, isPending } = useAnnouncements();
  const create = useCreateAnnouncement();
  const action = useAnnouncementAction();
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState<Announcement | null>(null);
  const canCreate = can("department.announcement.create");
  const canManage = can("department.announcement.manage");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  function payload() {
    return {
      title: form.title.trim(), body: form.body.trim(),
      target_roles: form.target_roles,
      target_programmes: splitList(form.programmes),
      target_academic_years: splitList(form.academic_years),
    };
  }

  function save() {
    if (editing) {
      action.mutate({ id: editing.id, action: "edit", payload: payload() }, {
        onSuccess: () => {
          notifications.show({ title: "Announcement updated", message: "Changes are saved." });
          setEditing(null); setForm(emptyForm);
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not update announcement", message: errorMessage(e),
        }),
      });
    } else {
      create.mutate(payload(), {
        onSuccess: () => {
          notifications.show({ title: "Announcement published", message: "It is now available to its target audience." });
          setForm(emptyForm);
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not publish announcement", message: errorMessage(e),
        }),
      });
    }
  }

  function edit(row: Announcement) {
    setEditing(row);
    setForm({
      title: row.title, body: row.body, target_roles: row.target_roles,
      programmes: row.target_programmes.join(", "),
      academic_years: row.target_academic_years.join(", "),
    });
  }

  function manage(row: Announcement, next: "hide" | "delete") {
    action.mutate({ id: row.id, action: next }, {
      onError: (e) => notifications.show({
        color: "red", title: "Could not update announcement", message: errorMessage(e),
      }),
    });
  }

  const busy = create.isPending || action.isPending;
  return (
    <Container size="md">
      <PageHeader title="Department announcements"
        subtitle="Updates shown to the roles, programmes and years selected by their author." />

      {(canCreate || editing) && (
        <Card withBorder padding="lg" mb="lg">
          <Stack>
            <Text fw={700}>{editing ? "Edit announcement" : "Publish an announcement"}</Text>
            <TextInput label="Title" value={form.title} maxLength={180}
              onChange={(e) => setForm({ ...form, title: e.currentTarget.value })} />
            <Textarea label="Message" minRows={4} value={form.body}
              onChange={(e) => setForm({ ...form, body: e.currentTarget.value })} />
            <MultiSelect label="Target roles" data={ROLE_OPTIONS}
              value={form.target_roles}
              onChange={(target_roles) => setForm({ ...form, target_roles })} />
            <TextInput label="Target programmes" placeholder="CSE, ECE"
              description="Enter one or more exact programme names, separated by commas."
              value={form.programmes}
              onChange={(e) => setForm({ ...form, programmes: e.currentTarget.value })} />
            <TextInput label="Target academic years" placeholder="2026, 2027"
              description="Enter one or more academic year values, separated by commas."
              value={form.academic_years}
              onChange={(e) => setForm({ ...form, academic_years: e.currentTarget.value })} />
            <Group>
              <Button onClick={save} loading={busy} disabled={
                !form.title.trim() || !form.body.trim() || !form.target_roles.length
                || !splitList(form.programmes).length || !splitList(form.academic_years).length
              }>{editing ? "Save changes" : "Publish"}</Button>
              {editing && <Button variant="default" onClick={() => {
                setEditing(null); setForm(emptyForm);
              }}>Cancel edit</Button>}
            </Group>
          </Stack>
        </Card>
      )}

      <Stack gap="sm">
        {isPending && <Text c="dimmed">Loading announcements…</Text>}
        {!isPending && data.length === 0 && (
          <Card withBorder><Text c="dimmed">No relevant announcements yet.</Text></Card>
        )}
        {data.map((row) => (
          <Card key={row.id} withBorder padding="lg">
            <Stack gap="xs">
              <Group justify="space-between" align="flex-start">
                <Text fw={700}>{row.title}</Text>
                {row.status !== "active" && <Badge color="gray">{row.status}</Badge>}
              </Group>
              <Text style={{ whiteSpace: "pre-wrap" }}>{row.body}</Text>
              <Text size="xs" c="dimmed">
                Roles: {row.target_roles.join(", ")} · Programmes: {row.target_programmes.join(", ")}
                {" · Years: "}{row.target_academic_years.join(", ")}
              </Text>
              {canManage && row.status === "active" && (
                <Group>
                  <Button size="xs" variant="light" onClick={() => edit(row)}>Edit</Button>
                  <Button size="xs" variant="light" color="orange"
                    onClick={() => manage(row, "hide")}>Hide</Button>
                  <Button size="xs" variant="light" color="red"
                    onClick={() => manage(row, "delete")}>Delete</Button>
                </Group>
              )}
            </Stack>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
