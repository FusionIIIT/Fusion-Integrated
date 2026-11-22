// Real-time scoped PSM dashboard and recent communication history (PSM-UC-030, BR-PSM-006).
import { Badge, Card, Container, SimpleGrid, Skeleton, Stack, Text, Title } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePsmDashboard, usePsmNotifications } from "../api/hooks";

export default function DashboardPage() {
  const { data, isPending, error } = usePsmDashboard();
  const notifs = usePsmNotifications();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Procurement & Stores Dashboard" subtitle="Real-time status within your role scope" />
      {isPending ? (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
          <Skeleton height={90} />
          <Skeleton height={90} />
          <Skeleton height={90} />
          <Skeleton height={90} />
        </SimpleGrid>
      ) : data ? (
        <Stack gap="lg">
          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
            <Card padding="md" withBorder>
              <Text size="xs" c="dimmed">Total Indents</Text>
              <Title order={2}>{data.indents_total}</Title>
              <Text size="xs" c="dimmed">{data.indents_pending_approval} pending approval</Text>
            </Card>
            <Card padding="md" withBorder>
              <Text size="xs" c="dimmed">Purchase Orders</Text>
              <Title order={2}>{data.purchase_orders_total}</Title>
            </Card>
            <Card padding="md" withBorder>
              <Text size="xs" c="dimmed">Open Discrepancies</Text>
              <Title order={2}>{data.open_discrepancies}</Title>
              <Text size="xs" c="dimmed">{data.pending_transfers} pending transfers</Text>
            </Card>
            <Card padding="md" withBorder>
              <Text size="xs" c="dimmed">Invoices on Hold</Text>
              <Title order={2}>{data.invoices_on_hold}</Title>
              <Text size="xs" c="dimmed">{data.invoices_pending_payment} ready for payment</Text>
            </Card>
          </SimpleGrid>

          <Card padding="lg" withBorder>
            <Title order={4} mb="sm">Recent Notifications</Title>
            {notifs.error ? (
              <ErrorState error={notifs.error} />
            ) : notifs.isPending ? (
              <Skeleton height={60} />
            ) : (notifs.data?.results.length ?? 0) === 0 ? (
              <Text size="sm" c="dimmed">No notifications yet.</Text>
            ) : (
              <Stack gap="xs">
                {notifs.data?.results.slice(0, 8).map((n) => (
                  <Card key={n.id} padding="sm" withBorder>
                    <Badge size="xs" variant="light" mb={4}>{n.topic}</Badge>
                    <Text fw={600} size="sm">{n.subject}</Text>
                    <Text size="xs" c="dimmed">{n.body}</Text>
                  </Card>
                ))}
              </Stack>
            )}
          </Card>
        </Stack>
      ) : (
        <Text c="dimmed">No dashboard data available.</Text>
      )}
    </Container>
  );
}
