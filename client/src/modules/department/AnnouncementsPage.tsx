import { Button, Container, Loader, Paper, Stack, Text } from "@mantine/core";
import { useInfiniteQuery } from "@tanstack/react-query";

import { useAuth } from "../../auth/AuthProvider";
import { http } from "../../lib/http";
import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";
import { ManageAnnouncements, PublishAnnouncement } from "./AnnouncementEditor";
import { useDepartmentCan } from "./DepartmentLayout";

interface Announcement {
  id: number;
  content: string;
  published_at: string;
}

interface AnnouncementPage {
  next: string | null;
  results: Announcement[];
}

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export default function AnnouncementsPage() {
  const { session } = useAuth();
  const can = useDepartmentCan();
  const query = useInfiniteQuery({
    queryKey: ["department", "announcements", session?.user.id, session?.active_role],
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam, signal }) => (
      await http.get<AnnouncementPage>("/department/announcements", {
        params: { cursor: pageParam }, signal,
      })
    ).data,
    getNextPageParam: (page) => page.next
      ? new URL(page.next, window.location.origin).searchParams.get("cursor")
      : null,
    gcTime: 0,
  });
  const announcements = query.data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <Container size="md" py="lg">
      <PageHeader title="Department announcements" />
      {can("department.announcement.publish") && (
        <Stack mb="lg"><PublishAnnouncement /></Stack>
      )}
      {query.isPending && <Loader aria-label="Loading announcements" />}
      {query.isError && <ErrorState error={query.error} />}
      {query.isSuccess && announcements.length === 0 && (
        <Text c="dimmed">There are no announcements for you right now.</Text>
      )}
      {announcements.length > 0 && (
        <Stack component="ul" p={0} m={0} style={{ listStyle: "none" }}>
          {announcements.map((announcement) => (
            <Paper key={announcement.id} component="li" withBorder p="md">
              <Text component="time" dateTime={announcement.published_at} size="sm" c="dimmed">
                {dateFormat.format(new Date(announcement.published_at))}
              </Text>
              <Text mt={4} style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                {announcement.content}
              </Text>
            </Paper>
          ))}
        </Stack>
      )}
      {query.hasNextPage && (
        <Button mt="md" variant="default" loading={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}>
          Load more announcements
        </Button>
      )}
      {can("department.announcement.manage") && (
        <Stack mt="lg"><ManageAnnouncements /></Stack>
      )}
    </Container>
  );
}
