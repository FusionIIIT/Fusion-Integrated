import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
  Badge,
  Select,
  Switch,
  SimpleGrid,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaPlus, FaThumbtack } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncements, useCreateAnnouncement } from "../api/hooks";
import type { DepartmentAnnouncement } from "../api/types";

export default function AnnouncementsPage() {
  const { data, error } = useAnnouncements();
  const createMutation = useCreateAnnouncement();

  const [modalOpened, setModalOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [department, setDepartment] = useState("Computer Science & Engineering");
  const [targetAudience, setTargetAudience] = useState("ALL");
  const [isPinned, setIsPinned] = useState(false);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const announcements = data ?? [];

  function handleCreate() {
    if (!title.trim() || !content.trim()) {
      notifications.show({ color: "red", message: "Title and content are required." });
      return;
    }

    createMutation.mutate(
      {
        title: title.trim(),
        content: content.trim(),
        department: department.trim(),
        target_audience: targetAudience.trim(),
        is_pinned: isPinned,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Announcement Published",
            message: "Department announcement has been posted.",
          });
          setModalOpened(false);
          setTitle("");
          setContent("");
          setIsPinned(false);
        },
        onError: (err) => {
          notifications.show({ color: "red", message: errorMessage(err) });
        },
      }
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Department Announcements"
        subtitle="Notices, seminar announcements, and academic updates"
        action={
          <Button
            leftSection={<FaPlus />}
            onClick={() => setModalOpened(true)}
          >
            Post Announcement
          </Button>
        }
      />

      {announcements.length === 0 ? (
        <Card padding="xl" withBorder style={{ textAlign: "center" }}>
          <FaBullhorn size={32} color="#adb5bd" />
          <Text fw={600} mt="sm">No Announcements</Text>
          <Text size="sm" c="dimmed">There are no department announcements posted yet.</Text>
        </Card>
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
          {announcements.map((ann: DepartmentAnnouncement) => (
            <Card key={ann.id} padding="lg" radius="md" withBorder>
              <Group justify="space-between" mb="xs">
                <Group gap="xs">
                  {ann.is_pinned && (
                    <Badge color="red" leftSection={<FaThumbtack size={10} />} size="xs">
                      Pinned
                    </Badge>
                  )}
                  <Badge variant="light" color="blue" size="xs">
                    {ann.department || "General"}
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed">{new Date(ann.created_at).toLocaleDateString()}</Text>
              </Group>

              <Text fw={700} size="md" mb="xs">{ann.title}</Text>
              <Text size="sm" c="gray.7" style={{ whiteSpace: "pre-wrap" }}>
                {ann.content}
              </Text>

              <Group justify="space-between" mt="md" pt="xs" style={{ borderTop: "1px solid #f1f3f5" }}>
                <Text size="xs" c="dimmed">Posted by: {ann.posted_by_name || "Admin"}</Text>
                <Badge variant="outline" size="xs">{ann.target_audience}</Badge>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      )}

      {/* Post Modal */}
      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title={<Text fw={700}>Post Department Announcement</Text>}
      >
        <Stack gap="md">
          <TextInput
            label="Announcement Title"
            placeholder="e.g. Call for Graduate Seminar Submissions"
            required
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />
          <Textarea
            label="Announcement Body"
            placeholder="Details of the announcement or notice..."
            minRows={4}
            required
            value={content}
            onChange={(e) => setContent(e.currentTarget.value)}
          />
          <TextInput
            label="Department"
            value={department}
            onChange={(e) => setDepartment(e.currentTarget.value)}
          />
          <Select
            label="Target Audience"
            data={["ALL", "STUDENTS", "FACULTY", "SCHOLARS"]}
            value={targetAudience}
            onChange={(val) => setTargetAudience(val || "ALL")}
          />
          <Switch
            label="Pin announcement to top"
            checked={isPinned}
            onChange={(e) => setIsPinned(e.currentTarget.checked)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpened(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} loading={createMutation.isPending}>
              Publish
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
