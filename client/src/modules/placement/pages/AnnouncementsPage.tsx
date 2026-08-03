import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Text, Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAnnouncements, usePublishAnnouncement, useWithdrawAnnouncement,
} from "../api/hooks";
import type { Announcement } from "../api/types";

const TOPICS = [
  { value: "drive", label: "Placement drive" },
  { value: "company_visit", label: "Company visit" },
  { value: "training", label: "Training session" },
  { value: "workshop", label: "Workshop" },
  { value: "internship", label: "Internship programme" },
  { value: "general", label: "General" },
];

const AUDIENCES = [
  { value: "students", label: "All students" },
  { value: "registered", label: "Registered students" },
  { value: "alumni", label: "Alumni" },
  { value: "all", label: "Everyone" },
];

export default function AnnouncementsPage() {
  const { data, isPending, error } = useAnnouncements();
  const { can } = useAuth();
  const [writing, setWriting] = useState(false);
  const [withdrawing, setWithdrawing] = useState<Announcement | null>(null);
  const [reason, setReason] = useState("");
  const withdraw = useWithdrawAnnouncement();

  const canPublish = can("placement_cell.announcement.publish");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader
        title="Announcements"
        subtitle="Drives, company visits, training sessions and workshops"
        action={canPublish && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setWriting(true)}>
            Publish
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
          <Card
            key={a.id} padding="lg" withBorder
            // Withdrawn notices stay visible to staff, marked so nobody acts on them.
            style={a.is_withdrawn ? { opacity: 0.6 } : undefined}
          >
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={4} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700}>{a.title}</Text>
                  <Badge variant="light" size="sm">
                    {TOPICS.find((t) => t.value === a.topic)?.label ?? a.topic}
                  </Badge>
                  {a.is_withdrawn && (
                    <Badge color="red" variant="light" size="sm">withdrawn</Badge>
                  )}
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{a.body}</Text>
                <Text size="xs" c="dimmed">
                  {a.published_at
                    ? new Date(a.published_at).toLocaleString() : "unpublished"}
                  {a.published_by_role ? ` · ${a.published_by_role}` : ""}
                </Text>
                {a.is_withdrawn && a.withdrawn_reason && (
                  <Text size="xs" c="red">Withdrawn: {a.withdrawn_reason}</Text>
                )}
              </Stack>
              {canPublish && !a.is_withdrawn && (
                <Button
                  size="xs" variant="subtle" color="red"
                  onClick={() => { setWithdrawing(a); setReason(""); }}
                >
                  Withdraw
                </Button>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      <PublishModal opened={writing} onClose={() => setWriting(false)} />

      <FormModal
        opened={withdrawing != null} onClose={() => setWithdrawing(null)}
        title="Withdraw this announcement"
        subtitle="It stays in the history, marked as withdrawn — nothing is deleted"
        onSubmit={() => withdrawing && withdraw.mutate(
          { id: withdrawing.id, reason },
          {
            onSuccess: () => setWithdrawing(null),
            onError: (e) => notifications.show({
              color: "red", title: "Could not withdraw",
              message: errorMessage(e),
            }),
          },
        )}
        submitLabel="Withdraw" danger submitting={withdraw.isPending}
        disabled={!reason.trim()}
      >
        <Textarea
          label="Reason" required autosize minRows={3} value={reason}
          onChange={(e) => setReason(e.currentTarget.value)} maxLength={300}
        />
      </FormModal>
    </Container>
  );
}

function PublishModal({ opened, onClose }: {
  opened: boolean; onClose: () => void;
}) {
  const publish = usePublishAnnouncement();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [topic, setTopic] = useState<string | null>("general");
  const [audience, setAudience] = useState<string | null>("students");

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Publish an announcement"
      subtitle="Students in the selected audience are notified"
      onSubmit={() => publish.mutate(
        { title, body, topic, audience },
        {
          onSuccess: () => {
            notifications.show({
              color: "green", title: "Published",
              message: "The announcement is live.",
            });
            setTitle(""); setBody("");
            onClose();
          },
        },
      )}
      submitLabel="Publish" submitting={publish.isPending} error={publish.error}
      disabled={!title.trim() || !body.trim()}
    >
      <Stack gap="md">
        <TextInput
          label="Title" required value={title} maxLength={200}
          onChange={(e) => setTitle(e.currentTarget.value)}
        />
        <Textarea
          label="Body" required autosize minRows={5} value={body}
          onChange={(e) => setBody(e.currentTarget.value)}
        />
        <Group grow>
          <Select label="Topic" data={TOPICS} value={topic} onChange={setTopic} />
          <Select
            label="Audience" data={AUDIENCES} value={audience}
            onChange={setAudience}
          />
        </Group>
      </Stack>
    </FormModal>
  );
}
