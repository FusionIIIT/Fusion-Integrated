import { Card, Container, Stack, Text } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useNotifications } from "../api/hooks";
import { ListStates } from "../components/ListStates";

export default function NotificationsPage() {
  const { data, isPending, error } = useNotifications();
  const rows = data?.results ?? [];
  return (
    <Container size="md">
      <PageHeader title="Notifications" subtitle="Updates on your claims and requisitions" />
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No notifications" />
      <Stack>
        {rows.map((n) => (
          <Card key={n.id} withBorder padding="md">
            <Text>{n.message}</Text>
            <Text size="xs" c="dimmed">{new Date(n.created_at).toLocaleString()}</Text>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
