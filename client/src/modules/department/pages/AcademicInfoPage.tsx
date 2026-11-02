import { Card, Container, Group, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDepartmentDetails, useTimetable } from "../api/hooks";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function AcademicInfoPage() {
  const timetable = useTimetable();
  const details = useDepartmentDetails();
  if (timetable.error) return <Container size="md"><ErrorState error={timetable.error} /></Container>;
  if (details.error) return <Container size="md"><ErrorState error={details.error} /></Container>;

  const programs = details.data?.general.programmes;
  return (
    <Container size="md">
      <PageHeader title="Academic information and timetable"
        subtitle="Programme information and timetable entries applicable to your account." />
      <Stack gap="lg">
        <section>
          <Text fw={700} mb="sm">Department programmes</Text>
          {programs == null ? <Text c="dimmed">Programme information has not been published.</Text>
            : <Card withBorder padding="md"><Text>{Array.isArray(programs)
              ? programs.join(", ") : String(programs)}</Text></Card>}
        </section>
        <section>
          <Text fw={700} mb="sm">Applicable timetable</Text>
          {timetable.isPending ? <Text c="dimmed">Loading timetable…</Text>
            : (timetable.data ?? []).length === 0
              ? <Card withBorder><Text c="dimmed">No timetable entries are available for your programme and year.</Text></Card>
              : <Stack gap="xs">{(timetable.data ?? []).map((row) => (
                <Card key={row.id} withBorder padding="md">
                  <Group justify="space-between">
                    <Stack gap={2}>
                      <Text fw={700}>{row.course}</Text>
                      <Text size="sm">{DAYS[row.day - 1]}, {row.starts_at.slice(0, 5)}–{row.ends_at.slice(0, 5)}</Text>
                    </Stack>
                    <Text size="sm" c="dimmed">{row.room}</Text>
                  </Group>
                </Card>
              ))}</Stack>}
        </section>
      </Stack>
    </Container>
  );
}
