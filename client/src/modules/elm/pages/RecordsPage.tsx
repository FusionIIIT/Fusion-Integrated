import {
  Badge, Card, Container, Group, Stack, Text, Title,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRecords, useElmContext } from "../api/hooks";

export default function RecordsPage() {
  const { data: records, isPending, error } = useRecords();
  const { data: context } = useElmContext();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Records"
        subtitle={context?.designation_name
          ? "Your records — Officers see the book"
          : "Leave on the books"}
      />
      {isPending ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <Stack>
          {(records ?? []).map((r) => (
            <Card key={r.id} withBorder radius="md" p="md">
              <Group justify="space-between">
                <Title order={5}>
                  {r.category} · {r.start_date} → {r.end_date} · {r.days} day(s)
                </Title>
                <Badge
                  color={r.status === "cancelled" ? "red" : "green"}
                  variant="light"
                >
                  {r.status}
                </Badge>
              </Group>
              <Text size="sm" c="dimmed">
                {r.leave_year}
                {r.station_leave ? " · station leave" : ""}
                {r.actual_end_date ? ` · ended ${r.actual_end_date}` : ""}
              </Text>
            </Card>
          ))}
          {(records ?? []).length === 0 && (
            <Text c="dimmed">No records yet.</Text>
          )}
        </Stack>
      )}
    </Container>
  );
}
