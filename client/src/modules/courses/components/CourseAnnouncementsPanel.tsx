import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  TbCalendar,
  TbEdit,
  TbPlus,
  TbSpeakerphone,
  TbTrash,
  TbUser,
} from "react-icons/tb";

import {
  deleteAnnouncement,
  useCourseAnnouncements,
} from "../api/hooks";
import type { CourseAnnouncement } from "../api/types";
import { AnnouncementModal } from "./AnnouncementModal";

interface CourseAnnouncementsPanelProps {
  workspaceId: number;
  canManage: boolean;
}

export function CourseAnnouncementsPanel({
  workspaceId,
  canManage,
}: CourseAnnouncementsPanelProps) {
  const { data, loading, error, refetch } = useCourseAnnouncements(workspaceId);
  const [modalOpened, setModalOpened] = useState(false);
  const [selectedAnnouncement, setSelectedAnnouncement] =
    useState<CourseAnnouncement | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleOpenCreate = () => {
    setSelectedAnnouncement(null);
    setModalOpened(true);
  };

  const handleOpenEdit = (ann: CourseAnnouncement) => {
    setSelectedAnnouncement(ann);
    setModalOpened(true);
  };

  const handleDelete = async (annId: number) => {
    if (!window.confirm("Are you sure you want to delete this announcement?")) {
      return;
    }
    setActionError(null);
    try {
      await deleteAnnouncement(workspaceId, annId);
      refetch();
    } catch (err: unknown) {
      setActionError(
        err instanceof Error
          ? err.message
          : "Failed to delete announcement.",
      );
    }
  };

  const announcements = data?.results ?? [];

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={4}>Course Announcements</Title>
          <Text size="xs" c="dimmed">
            Course-wide updates, notices, and reminders
          </Text>
        </div>
        {canManage && (
          <Button
            leftSection={<TbPlus size={16} />}
            onClick={handleOpenCreate}
            size="sm"
          >
            Post Announcement
          </Button>
        )}
      </Group>

      {error && (
        <Alert color="red" title="Error">
          {error}
        </Alert>
      )}

      {actionError && (
        <Alert color="red" title="Action Error" withCloseButton onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}

      {loading && (
        <Group justify="center" py="xl">
          <Loader size="md" />
        </Group>
      )}

      {!loading && announcements.length === 0 && (
        <Paper withBorder p="xl" ta="center" radius="md">
          <Group justify="center" mb="xs">
            <TbSpeakerphone size={32} color="gray" />
          </Group>
          <Text fw={500} c="dimmed">
            No announcements posted yet
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {canManage
              ? "Use the 'Post Announcement' button above to send updates to your course."
              : "Course announcements from instructors will appear here."}
          </Text>
        </Paper>
      )}

      {!loading && announcements.length > 0 && (
        <Stack gap="md">
          {announcements.map((ann) => {
            const formattedDate = ann.published_at
              ? new Date(ann.published_at).toLocaleString()
              : new Date(ann.created_at).toLocaleString();

            return (
              <Card key={ann.id} withBorder shadow="xs" p="md" radius="sm">
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                  <div style={{ flex: 1, minWidth: 260 }}>
                    <Group gap="xs" mb={4}>
                      <Title order={5}>{ann.title}</Title>
                      {ann.is_published ? (
                        <Badge color="teal" size="sm" variant="light">
                          Published
                        </Badge>
                      ) : (
                        <Badge color="yellow" size="sm" variant="light">
                          Draft (Faculty Only)
                        </Badge>
                      )}
                    </Group>
                    <Group gap="md" c="dimmed" style={{ fontSize: "0.8rem" }}>
                      <Group gap={4}>
                        <TbUser size={14} />
                        <span>{ann.author_name || "Faculty Instructor"}</span>
                      </Group>
                      <Group gap={4}>
                        <TbCalendar size={14} />
                        <span>{formattedDate}</span>
                      </Group>
                    </Group>
                  </div>

                  {canManage && (
                    <Group gap="xs">
                      <Button
                        variant="subtle"
                        size="xs"
                        leftSection={<TbEdit size={14} />}
                        onClick={() => handleOpenEdit(ann)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<TbTrash size={14} />}
                        onClick={() => handleDelete(ann.id)}
                      >
                        Delete
                      </Button>
                    </Group>
                  )}
                </Group>

                <Divider my="sm" />

                <Text
                  size="sm"
                  style={{
                    whiteSpace: "pre-line",
                    lineHeight: 1.6,
                    wordBreak: "break-word",
                  }}
                >
                  {ann.body}
                </Text>
              </Card>
            );
          })}
        </Stack>
      )}

      <AnnouncementModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        workspaceId={workspaceId}
        announcement={selectedAnnouncement}
        onSuccess={refetch}
      />
    </Stack>
  );
}

