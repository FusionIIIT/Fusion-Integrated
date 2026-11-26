import {
  Badge, Card, Container, Stack, Text, Group,
} from "@mantine/core";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useFeedback } from "../api/hooks";

export default function FeedbackPage() {
  const { data, isPending, error } = useFeedback();

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader title="Feedback" subtitle="View submitted feedback" />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <Text fw={600}>No feedback submitted yet</Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((feedback) => (
          <Card
            key={feedback.id} padding="lg" withBorder
          >
            <Stack gap={3}>
              <Text fw={700}>{feedback.body}</Text>
              <Group justify="space-between" align="center">
                <Text size="sm" c="dimmed">
                  Submitted on: {feedback.created_at ? new Date(feedback.created_at).toLocaleDateString() : "N/A"}
                </Text>
                <Badge color={feedback.state === "resolved" ? "green" : feedback.state === "pending" ? "blue" : "orange"}>
                  {feedback.state}
                </Badge>
              </Group>
            </Stack>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
