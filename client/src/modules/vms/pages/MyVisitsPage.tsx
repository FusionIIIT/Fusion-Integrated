import { Badge, Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBell, FaCheckDouble } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useArrivals, useInbox, useMarkAllRead, useMarkRead } from "../api/hooks";
import type { VmsNotification } from "../api/types";
import { formatDateTime } from "../format";

export default function MyVisitsPage() {
  const { can } = useAuth();
  const inbox = useInbox();
  const arrivals = useArrivals(can("vms.request.view_assigned"));
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();

  if (inbox.error) return <Container size="md"><ErrorState error={inbox.error} /></Container>;

  const rows = inbox.data?.results ?? [];
  const unread = rows.filter((n) => !n.read_at).length;

  function onError(e: unknown) {
    notifications.show({ color: "red", message: errorMessage(e) });
  }

  return (
    <Container size="md">
      <PageHeader
        title="My Visits"
        subtitle="Requests waiting for you, visitor arrivals and updates about your visits"
        action={(
          <Button
            variant="default" leftSection={<FaCheckDouble size={12} />}
            disabled={unread === 0} loading={markAll.isPending}
            onClick={() => markAll.mutate(undefined, { onError })}
          >
            Mark all read
          </Button>
        )}
      />

      {(arrivals.data?.results.length ?? 0) > 0 && (
        <Stack gap="xs" mb="lg">
          <Text fw={600}>Visitors who have arrived</Text>
          {arrivals.data?.results.map((a) => (
            <Card key={a.notification.id} withBorder padding="sm">
              <Group justify="space-between" wrap="nowrap">
                <Text size="sm">{a.notification.subject}</Text>
                <Text size="xs" c="dimmed">{formatDateTime(a.checked_in_at)}</Text>
              </Group>
              {a.notification.body && <Text size="xs" c="dimmed">{a.notification.body}</Text>}
            </Card>
          ))}
        </Stack>
      )}

      <DataTable<VmsNotification>
        rows={rows}
        loading={inbox.isPending}
        rowKey={(n) => n.id}
        minWidth={560}
        empty={{ icon: FaBell, title: "No notifications yet",
          description: "Visit requests and updates will appear here." }}
        columns={[
          { key: "subject", header: "Update", render: (n) => (
            <Stack gap={0}>
              <Group gap={6}>
                <Text size="sm" fw={n.read_at ? 400 : 600}>{n.subject}</Text>
                {!n.read_at && <Badge size="xs" color="blue" variant="light">new</Badge>}
              </Group>
              {n.body && <Text size="xs" c="dimmed">{n.body}</Text>}
            </Stack>
          ) },
          { key: "created_at", header: "When", render: (n) => formatDateTime(n.created_at) },
          { key: "action", header: "", align: "right", render: (n) => (
            n.read_at ? null : (
              <Button
                size="compact-xs" variant="subtle"
                loading={markRead.isPending && markRead.variables === n.id}
                onClick={() => markRead.mutate(n.id, { onError })}
              >
                Mark read
              </Button>
            )
          ) },
        ]}
      />
    </Container>
  );
}
