import { Alert, Card, Loader, SimpleGrid, Stack, Text, Title } from "@mantine/core";

import { useDashboardMetrics } from "../api/hooks";

export default function DashboardPage() {
  const { data, isLoading, isError } = useDashboardMetrics();

  if (isLoading) {
    return (
      <Stack align="center" justify="center" p="xl" data-testid="loading-spinner">
        <Loader size="lg" />
        <Text c="dimmed">Loading administrative metrics...</Text>
      </Stack>
    );
  }

  if (isError || !data) {
    return (
      <Alert color="red" title="Error loading dashboard" data-testid="error-message">
        Unable to retrieve dashboard metrics from the administrative API.
      </Alert>
    );
  }

  return (
    <Stack gap="lg" p="md">
      <Title order={2}>Super Admin Dashboard</Title>
      <Text c="dimmed">Institute ERP Administrative Control Plane Overview</Text>

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
        <Card withBorder padding="lg" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Total Users</Text>
          <Text size="xl" fw={700}>{data.total_users}</Text>
        </Card>
        <Card withBorder padding="lg" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Active Users</Text>
          <Text size="xl" fw={700} c="green">{data.active_users}</Text>
        </Card>
        <Card withBorder padding="lg" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Deactivated Users</Text>
          <Text size="xl" fw={700} c="orange">{data.deactivated_users}</Text>
        </Card>
        <Card withBorder padding="lg" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Archived (Reversible)</Text>
          <Text size="xl" fw={700} c="blue">{data.archived_reversible_users}</Text>
        </Card>
        <Card withBorder padding="lg" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Archived (Permanent)</Text>
          <Text size="xl" fw={700} c="gray">{data.archived_permanent_users}</Text>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
