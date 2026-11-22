import { Alert, Card, Container, Group, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncementHistory } from "../api/hooks";

export default function AnnouncementHistoryPage() {
  const { data: announcements, isLoading, error } = useAnnouncementHistory();

  if (error) {
    return <Container size="md"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="md">
      <PageHeader title="Announcement History" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">Complete historical archive of all mess announcements published.</Text>
        {isLoading ? (
          <Text c="dimmed">Loading history...</Text>
        ) : !announcements || announcements.length === 0 ? (
          <Alert color="gray">No announcement history found.</Alert>
        ) : (
          announcements.map((a) => (
            <Card key={a.id} withBorder padding="md">
              <Group justify="space-between" mb="xs">
                <Text fw={600} size="md">{a.title}</Text>
                <Text size="xs" c="dimmed">{new Date(a.published_at).toLocaleString()}</Text>
              </Group>
              <Text size="sm">{a.body}</Text>
            </Card>
          ))
        )}
      </Stack>
    </Container>
  );
}
