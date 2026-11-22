import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Table, Text, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncements, usePublishAnnouncement } from "../api/hooks";

export default function AnnouncementsPage() {
  const { data: announcements, isLoading, error } = useAnnouncements();
  const publish = usePublishAnnouncement();

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const handlePublish = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;

    publish.mutate(
      { title: title.trim(), body: body.trim() },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Published", message: "Mess announcement published to students." });
          setTitle("");
          setBody("");
        },
        onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
      }
    );
  };

  if (error) {
    return <Container size="md"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="md">
      <PageHeader title="Mess Announcements" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <form onSubmit={handlePublish}>
            <Stack gap="sm">
              <Text fw={600}>Publish Mess Announcement</Text>
              <TextInput label="Title" placeholder="e.g. Special Dinner on Friday" required value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
              <Textarea label="Announcement Body" placeholder="Details of the announcement..." minRows={3} required value={body} onChange={(e) => setBody(e.currentTarget.value)} />
              <Group justify="flex-end">
                <Button type="submit" loading={publish.isPending}>Publish Announcement</Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Recent Announcements</Text>
          {isLoading ? (
            <Text c="dimmed">Loading announcements...</Text>
          ) : !announcements || announcements.length === 0 ? (
            <Alert color="gray">No announcements published yet.</Alert>
          ) : (
            <Stack gap="sm">
              {announcements.map((a) => (
                <Card key={a.id} withBorder padding="sm">
                  <Group justify="space-between" mb={4}>
                    <Text fw={600}>{a.title}</Text>
                    <Text size="xs" c="dimmed">{new Date(a.published_at).toLocaleString()}</Text>
                  </Group>
                  <Text size="sm">{a.body}</Text>
                </Card>
              ))}
            </Stack>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
