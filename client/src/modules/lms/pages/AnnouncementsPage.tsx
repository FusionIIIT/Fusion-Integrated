import React, { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourseAnnouncements } from "../api/hooks";
import { AnnouncementItem } from "../components/AnnouncementItem";
import { CreateAnnouncementModal } from "../components/CreateAnnouncementModal";

export interface AnnouncementsPageProps {
  courseId?: number;
}

export const AnnouncementsPage: React.FC<AnnouncementsPageProps> = ({
  courseId: propCourseId,
}) => {
  const { courseId: paramCourseId } = useParams<{ courseId: string }>();
  const courseId = propCourseId ?? (paramCourseId ? parseInt(paramCourseId) : 0);

  const [modalOpened, setModalOpened] = useState(false);

  const {
    data: announcements,
    isLoading,
    isError,
    error,
  } = useCourseAnnouncements(courseId);

  const sortedAnnouncements = React.useMemo(() => {
    if (!announcements) return [];
    return [...announcements].sort((a, b) => {
      if (a.is_pinned && !b.is_pinned) return -1;
      if (!a.is_pinned && b.is_pinned) return 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [announcements]);

  return (
    <Stack gap="lg">
      <PageHeader
        title="Course Announcements"
        subtitle="Important updates, schedule notifications, and instructor notices"
        action={
          <Group gap="xs">
            <Button variant="filled" size="sm" onClick={() => setModalOpened(true)}>
              New Announcement
            </Button>
          </Group>
        }
      />

      {isLoading && (
        <Center py="xl">
          <Loader size="lg" />
        </Center>
      )}

      {isError && (
        <Alert color="red" title="Failed to Load Announcements">
          {error instanceof Error ? error.message : "Unable to retrieve course announcements."}
        </Alert>
      )}

      {!isLoading && sortedAnnouncements.length > 0 && (
        <Stack gap="sm">
          {sortedAnnouncements.map((a) => (
            <AnnouncementItem key={a.id} announcement={a} />
          ))}
        </Stack>
      )}

      {!isLoading && sortedAnnouncements.length === 0 && (
        <Paper withBorder p="xl" radius="md" ta="center">
          <Text c="dimmed">No announcements published for this course yet.</Text>
        </Paper>
      )}

      <CreateAnnouncementModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        courseId={courseId}
      />
    </Stack>
  );
};

export default AnnouncementsPage;
