import { useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Modal, Stack, Text, TextInput, Textarea, Title } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { useAnnouncements, useCreateAnnouncement } from "../api/hooks";

export default function AnnouncementsPage() {
  const { can } = useAuth();
  const { data: announcements, isLoading } = useAnnouncements();
  const createAnnouncement = useCreateAnnouncement();

  const [opened, setOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [targetRole, setTargetRole] = useState("ALL");

  const canCreate = can("dept.announcement.create");

  const handleSubmit = async () => {
    if (!title.trim() || !content.trim()) return;
    await createAnnouncement.mutateAsync({
      title,
      content,
      target_role: targetRole,
    });
    setTitle("");
    setContent("");
    setOpened(false);
  };

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Announcements</Title>
          <Text c="dimmed">Official updates, circulars, and notices</Text>
        </div>
        {canCreate && (
          <Button onClick={() => setOpened(true)}>Post Announcement</Button>
        )}
      </Group>

      {isLoading && <Text>Loading announcements...</Text>}

      {announcements && announcements.length === 0 && (
        <Alert title="No Announcements" color="blue">
          There are no active announcements for your cohort at this time.
        </Alert>
      )}

      <Stack gap="md">
        {announcements?.map((a) => (
          <Card key={a.id} withBorder shadow="sm" radius="md">
            <Group justify="space-between" mb="xs">
              <Title order={4}>{a.title}</Title>
              <Group gap="xs">
                <Badge color="blue">{a.target_role}</Badge>
                <Badge color="gray">{new Date(a.created_at).toLocaleDateString()}</Badge>
              </Group>
            </Group>
            <Text style={{ whiteSpace: "pre-wrap" }}>{a.content}</Text>
          </Card>
        ))}
      </Stack>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Create Announcement">
        <Stack gap="sm">
          <TextInput
            label="Title"
            placeholder="Announcement Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
          <Textarea
            label="Content"
            placeholder="Details of the announcement"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            minRows={3}
            required
          />
          <TextInput
            label="Target Role"
            placeholder="ALL / STUDENT / FACULTY / DEPT_ADMIN"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleSubmit} loading={createAnnouncement.isPending}>Publish</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
