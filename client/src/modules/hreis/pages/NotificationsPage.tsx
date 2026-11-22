import { Button, Card, Container, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMarkNotificationRead, useNotifications } from "../api/hooks";

export default function NotificationsPage() {
  const { can } = useAuth();
  const markRead = useMarkNotificationRead();
  const { data, error, isPending } = useNotifications();
  return (
    <Container size="lg">
      <PageHeader title="HR Notifications"
        subtitle="Notices addressed to you through your current HR session" />
      {isPending && <Text c="dimmed">Loading notifications...</Text>}
      {error && <ErrorState error={error} />}
      {data && (
        <Stack>
          {data.results.length === 0 &&
            <Card withBorder><Text c="dimmed">No notifications yet.</Text></Card>}
          {data.results.map((notification) => (
            <Card key={notification.id} withBorder>
              <Text fw={600}>{notification.title}</Text>
              <Text size="sm" mt="xs">{notification.message}</Text>
              <Text size="xs" c="dimmed" mt="sm">
                {new Date(notification.created_at).toLocaleString()}
              </Text>
              {notification.read_at ? <Text size="xs" c="dimmed">Read</Text>
                : can("hreis.notification.view") && <Button variant="light" size="xs" mt="sm"
                  loading={markRead.isPending} onClick={() => markRead.mutate({ id: notification.id }, {
                    onError: (failure) => notifications.show({ position: "top-center", color: "red",
                      title: "Could not mark notification read", message: errorMessage(failure) }),
                  })}>Mark as read</Button>}
            </Card>
          ))}
        </Stack>
      )}
    </Container>
  );
}
