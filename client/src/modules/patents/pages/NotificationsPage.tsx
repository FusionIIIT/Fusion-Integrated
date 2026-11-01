import { Badge, Button, Card, Container, Group, Text } from "@mantine/core";
import { useNavigate } from "react-router-dom";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { type Notice, useMarkRead, useNotices } from "../api";

export default function NotificationsPage() {
  const { data, error, isPending } = useNotices();
  const markRead = useMarkRead();
  const navigate = useNavigate();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Notifications" subtitle="Status changes on applications you are part of" />
      <Card padding="lg">
        <DataTable<Notice>
          rows={data ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={640}
          columns={[
            {
              key: "message", header: "Message",
              render: (r) => (
                <Group gap="xs" wrap="nowrap">
                  {!r.read && <Badge size="xs">New</Badge>}
                  <Text size="sm" fw={r.read ? 400 : 600}>{r.message}</Text>
                </Group>
              ),
            },
            {
              key: "when", header: "When",
              render: (r) => <Text size="xs" c="dimmed">{new Date(r.created_at).toLocaleString()}</Text>,
            },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  {r.application_id && (
                    <Button size="xs" variant="light"
                      onClick={() => navigate(`/patents/applications/${r.application_id}`)}>Open</Button>
                  )}
                  {!r.read && (
                    <Button size="xs" variant="subtle" onClick={() => markRead.mutate(r.id)}>Mark read</Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{ title: "No notifications", description: "You're all caught up." }}
        />
      </Card>
    </Container>
  );
}
