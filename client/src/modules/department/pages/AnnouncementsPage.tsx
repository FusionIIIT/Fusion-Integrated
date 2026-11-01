import { Text, Container, Stack, Card } from "@mantine/core";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncements } from "../api/hooks";
// Removed unused import: import type { Announcement } from "../api/types";

export default function AnnouncementsPage() {
  const { data, isPending, error } = useAnnouncements();

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader title="Announcements" subtitle="Latest departmental announcements" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <Text fw={600}>No announcements found.</Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((a) => (
          <Card
            key={a.id} padding="lg" withBorder
          >
            <Stack gap={4}>
              <Text fw={700}>{a.title}</Text>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{a.body}</Text>
            </Stack>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
