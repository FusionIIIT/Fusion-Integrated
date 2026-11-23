import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaPlus, FaTrash } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncements, useCourses, useCreateAnnouncement, useDeleteAnnouncement } from "../api/hooks";

export default function AnnouncementsPage() {
  const { data: courses } = useCourses();
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const activeId = selectedCourseId ?? courses?.[0]?.course_id ?? null;

  const { data: announcements, isPending, error } = useAnnouncements(activeId);
  const createAnnouncement = useCreateAnnouncement();
  const deleteAnnouncement = useDeleteAnnouncement();
  const { can } = useAuth();

  const canCreate = can("lms.announcement.create");
  const canDelete = can("lms.announcement.delete");

  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  if (error) {
    return (
      <Container size="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  const courseOptions = (courses ?? []).map((c) => ({
    value: String(c.course_id),
    label: `${c.course_code}: ${c.title}`,
  }));

  const handleCreate = () => {
    if (!activeId || !title.trim() || !content.trim()) return;

    createAnnouncement.mutate(
      {
        course_id: activeId,
        title,
        content,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Announcement Posted",
            message: "The announcement has been broadcast to all enrolled students.",
          });
          setCreating(false);
          setTitle("");
          setContent("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Posting Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  };

  const handleDelete = (annId: number) => {
    if (confirm("Are you sure you want to delete this announcement?")) {
      deleteAnnouncement.mutate(annId, {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Deleted",
            message: "Announcement has been removed.",
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Delete Failed",
            message: errorMessage(err),
          });
        },
      });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Announcements"
        subtitle="Important class updates, schedule changes, and reminders"
        action={
          canCreate && activeId ? (
            <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
              New Announcement
            </Button>
          ) : undefined
        }
      />

      {courseOptions.length > 0 && (
        <Select
          label="Select Course"
          data={courseOptions}
          value={activeId ? String(activeId) : null}
          onChange={(val) => setSelectedCourseId(val ? Number(val) : null)}
          allowDeselect={false}
          mb="lg"
        />
      )}

      {isPending && <Text c="dimmed">Loading announcements…</Text>}

      {!isPending && (!announcements || announcements.length === 0) && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={8}>
            <FaBullhorn size={28} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No announcements posted yet</Text>
            <Text size="sm" c="dimmed">
              Instructors or TAs will post announcements regarding exams, assignments, or classes here.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {(announcements ?? []).map((ann) => (
          <Card key={ann.id} padding="lg" withBorder>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={4} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700} size="md">
                    {ann.title}
                  </Text>
                  <Badge
                    size="sm"
                    variant="light"
                    color={ann.author_role === "INSTRUCTOR" ? "blue" : "grape"}
                  >
                    {ann.author_role}
                  </Badge>
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {ann.content}
                </Text>
                <Text size="xs" c="dimmed" mt={4}>
                  Posted {new Date(ann.created_at).toLocaleString()} by User {ann.author_id}
                </Text>
              </Stack>
              {canDelete && (
                <ActionIcon
                  color="red"
                  variant="subtle"
                  onClick={() => handleDelete(ann.id)}
                >
                  <FaTrash size={14} />
                </ActionIcon>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Post Course Announcement"
        subtitle="Broadcast an announcement to everyone in this course"
        onSubmit={handleCreate}
        submitting={createAnnouncement.isPending}
        submitLabel="Post Announcement"
      >
        <Stack gap="md">
          <TextInput
            label="Announcement Title"
            placeholder="e.g. Midterm Exam Venue Changed"
            required
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />
          <Textarea
            label="Content"
            placeholder="Write announcement details..."
            required
            autosize
            minRows={4}
            value={content}
            onChange={(e) => setContent(e.currentTarget.value)}
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
