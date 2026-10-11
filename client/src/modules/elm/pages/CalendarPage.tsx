import {
  Badge, Card, Container, Group, Stack, Text, Title,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCalendar } from "../api/hooks";

export default function CalendarPage() {
  const { data, isPending, error } = useCalendar();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const published = data && "published_at" in data;

  return (
    <Container size="xl">
      <PageHeader
        title="Holiday Calendar"
        subtitle="The currently effective published calendar — RH requests match its restricted holidays"
      />
      {isPending ? (
        <Text c="dimmed">Loading…</Text>
      ) : !published ? (
        <Text c="dimmed">No calendar has been published yet.</Text>
      ) : (
        <>
          <Title order={4} mb="sm">{data.name} — {data.year}</Title>
          <Stack>
            {data.holidays.map((h) => (
              <Card key={h.id} withBorder radius="md" p="sm">
                <Group justify="space-between">
                  <Text>{h.date} — {h.label}</Text>
                  <Badge
                    variant="light"
                    color={h.kind === "restricted_holiday" ? "violet" : "blue"}
                  >
                    {h.kind === "restricted_holiday" ? "Restricted Holiday" : "Holiday"}
                  </Badge>
                </Group>
              </Card>
            ))}
          </Stack>
        </>
      )}
    </Container>
  );
}
