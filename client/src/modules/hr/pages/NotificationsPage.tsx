import { Card, Container, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useNotifications } from "../api/hooks";

export default function NotificationsPage() {
  const { data, isPending, error } = useNotifications();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return <Container size="xl">
    <PageHeader title="HR Notifications" subtitle="Updates addressed to your employee account" />
    {isPending ? <Text>Loading notifications…</Text> : data?.results.length ? (
      <Stack>{data.results.map((notification) => (
        <Card withBorder key={notification.id}><Stack gap="xs">
          <Text fw={700}>{notification.subject}</Text><Text size="sm">{notification.body}</Text>
          <Text size="xs" c="dimmed">{notification.topic} · {new Date(notification.created_at).toLocaleString()}</Text>
        </Stack></Card>
      ))}</Stack>
    ) : <Text c="dimmed">You have no HR notifications.</Text>}
  </Container>;
}