import { Badge, Card, Container, Group, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDashboard } from "../api/hooks";

export default function NotificationsPage() {
  const { data, isPending, error } = useDashboard();
  if (error) return <Container size="md"><ErrorState error={error} /></Container>;
  const pending = Object.entries(data?.pending ?? {});
  const rows = data?.notifications ?? [];
  return (
    <Container size="md">
      <PageHeader title="Notifications" subtitle="What is waiting on your active role" />
      {isPending ? <Text c="dimmed">Loading…</Text> : (
        <Stack gap="md">
          <Group>
            {pending.length === 0 && <Text size="sm" c="dimmed">No pending actions.</Text>}
            {pending.map(([k, n]) => (
              <Badge key={k} size="lg" variant={n > 0 ? "filled" : "light"}>
                {k.replace(/_/g, " ")}: {n}
              </Badge>
            ))}
          </Group>
          {rows.length === 0 && (
            <Card padding="xl"><Text fw={600} ta="center">No notifications yet</Text></Card>
          )}
          {rows.map((n) => (
            <Card key={n.id} padding="sm">
              <Text size="sm">{n.message}</Text>
              <Text size="xs" c="dimmed">{new Date(n.created_at).toLocaleString()}</Text>
            </Card>
          ))}
        </Stack>
      )}
    </Container>
  );
}
