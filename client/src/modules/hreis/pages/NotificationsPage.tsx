import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Paper,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBell } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMarkNotificationRead, useNotifications } from "../api/hooks";

export default function NotificationsPage() {
  const { data: notifs, isPending, error } = useNotifications();
  const markRead = useMarkNotificationRead();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="System Notifications & Alerts"
        subtitle="Automated alerts for leave submissions, claims verifications, reminders, and policy updates (BR-HR-024)"
      />

      <Card padding="lg" withBorder radius="md">
        {isPending ? (
          <Text size="sm" c="dimmed">Loading notifications...</Text>
        ) : notifs?.length === 0 ? (
          <Stack align="center" py="xl">
            <FaBell size={32} color="gray" />
            <Text fw={600}>No notifications</Text>
            <Text size="sm" c="dimmed">You have no system alerts at this time.</Text>
          </Stack>
        ) : (
          <Stack gap="sm">
            {notifs?.map((n) => (
              <Paper
                key={n.id}
                withBorder
                p="md"
                radius="sm"
                bg={n.is_read ? undefined : "blue.0"}
              >
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Group gap="xs" mb={4}>
                      <Text size="sm" fw={600}>
                        {n.title}
                      </Text>
                      <Badge
                        size="xs"
                        variant="light"
                        color={
                          n.category === "approval"
                            ? "teal"
                            : n.category === "rejection"
                            ? "red"
                            : n.category === "reminder"
                            ? "orange"
                            : "blue"
                        }
                      >
                        {n.category.toUpperCase()}
                      </Badge>
                      {!n.is_read && (
                        <Badge size="xs" color="red" variant="filled">
                          New
                        </Badge>
                      )}
                    </Group>
                    <Text size="sm">{n.message}</Text>
                    <Text size="xs" c="dimmed" mt={4}>
                      {new Date(n.created_at).toLocaleString()}
                    </Text>
                  </div>
                  {!n.is_read && (
                    <Button
                      size="xs"
                      variant="subtle"
                      onClick={() => {
                        markRead.mutate(n.id, {
                          onSuccess: () => {
                            notifications.show({
                              title: "Dismissed",
                              message: "Marked as read",
                              color: "teal",
                            });
                          },
                        });
                      }}
                    >
                      Mark Read
                    </Button>
                  )}
                </Group>
              </Paper>
            ))}
          </Stack>
        )}
      </Card>
    </Container>
  );
}
