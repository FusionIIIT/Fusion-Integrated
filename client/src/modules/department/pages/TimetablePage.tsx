import { Card, Container, Stack, Text } from "@mantine/core";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useTimetable } from "../api/hooks";

export default function TimetablePage() {
  const { data, isPending, error } = useTimetable();

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader title="Timetable" subtitle="View the weekly schedule" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <Text fw={600}>No timetable entries found</Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((entry) => (
          <Card
            key={entry.id} padding="lg" withBorder
          >
            <Stack gap="xs">
              <Text fw={700}>{entry.title}</Text>
              <Text size="sm">
                {entry.weekday} - {entry.start_time} to {entry.end_time} in {entry.room}
              </Text>
            </Stack>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
