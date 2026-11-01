import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, MultiSelect, Stack, TagsInput, Text,
  Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAnnouncements, usePublishAnnouncement, useSetAnnouncementStatus,
} from "../api/hooks";

const ROLES = [
  { value: "student", label: "Students" },
  { value: "faculty", label: "Faculty" },
];

function targeting(a: { target_roles: string[]; target_programmes: string[];
                        target_years: number[] }) {
  const parts = [
    a.target_roles.length ? a.target_roles.join(" & ") : "everyone",
    ...a.target_programmes,
    ...a.target_years.map(String),
  ];
  return parts.join(" · ");
}

export default function AnnouncementsPage() {
  const { data, isPending, error } = useAnnouncements();
  const { can } = useAuth();
  const setStatus = useSetAnnouncementStatus();
  const [writing, setWriting] = useState(false);

  const canPublish = can("dept.announcement.publish");
  const canModerate = can("dept.announcement.manage");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;
  const rows = data ?? [];

  const act = (id: number, status: string) => setStatus.mutate({ id, status }, {
    onError: (e) => notifications.show({
      color: "red", title: "Could not update", message: errorMessage(e),
    }),
  });

  return (
    <Container size="md">
      <PageHeader
        title="Announcements"
        subtitle="Notices from the department, filtered to what concerns you"
        action={canPublish && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setWriting(true)}>
            New announcement
          </Button>
        )}
      />

      {isPending && <Text c="dimmed">Loading…</Text>}
      {!isPending && rows.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <FaBullhorn size={24} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>Nothing announced yet</Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((a) => (
          <Card key={a.id} padding="lg" withBorder
                style={a.status === "hidden" ? { opacity: 0.6 } : undefined}>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={4} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700}>{a.title}</Text>
                  {a.status === "hidden" && (
                    <Badge color="gray" variant="light" size="sm">hidden</Badge>
                  )}
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{a.body}</Text>
                <Text size="xs" c="dimmed">
                  {new Date(a.created_at).toLocaleString()} · {a.published_by_role}
                  {" · for "}{targeting(a)}
                </Text>
              </Stack>
              {canModerate && (
                <Group gap={4} wrap="nowrap">
                  <Button size="xs" variant="subtle"
                          onClick={() => act(a.id, a.status === "hidden" ? "active" : "hidden")}>
                    {a.status === "hidden" ? "Unhide" : "Hide"}
                  </Button>
                  <Button size="xs" variant="subtle" color="red"
                          onClick={() => window.confirm("Delete this announcement?")
                            && act(a.id, "deleted")}>
                    Delete
                  </Button>
                </Group>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      <PublishModal opened={writing} onClose={() => setWriting(false)} />
    </Container>
  );
}

function PublishModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const publish = usePublishAnnouncement();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [programmes, setProgrammes] = useState<string[]>([]);
  const [years, setYears] = useState<string[]>([]);

  const yearsValid = years.every((y) => /^\d{4}$/.test(y));

  return (
    <FormModal
      opened={opened} onClose={onClose} title="New announcement"
      subtitle="Leave a target empty to reach everyone on that axis"
      submitLabel="Publish" submitting={publish.isPending}
      disabled={!title.trim() || !body.trim() || !yearsValid}
      disabledReason={!yearsValid ? "Years must be four digits" : undefined}
      error={publish.error}
      onSubmit={() => publish.mutate(
        { title, body, target_roles: roles, target_programmes: programmes,
          target_years: years.map(Number) },
        { onSuccess: () => {
            setTitle(""); setBody(""); setRoles([]); setProgrammes([]); setYears([]);
            onClose();
          } },
      )}
    >
      <Stack>
        <TextInput label="Title" required maxLength={200} value={title}
                   onChange={(e) => setTitle(e.currentTarget.value)} />
        <Textarea label="Message" required autosize minRows={4} value={body}
                  onChange={(e) => setBody(e.currentTarget.value)} />
        <MultiSelect label="Audience" data={ROLES} value={roles}
                     onChange={setRoles} placeholder="Students and faculty" clearable />
        <TagsInput label="Programmes" value={programmes} onChange={setProgrammes}
                   placeholder="e.g. B.Tech — press Enter" />
        <TagsInput label="Batch years" value={years} onChange={setYears}
                   placeholder="e.g. 2024 — press Enter"
                   error={yearsValid ? undefined : "Use four-digit years"} />
      </Stack>
    </FormModal>
  );
}
