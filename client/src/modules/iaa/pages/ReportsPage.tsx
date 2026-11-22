import {
  Button,
  Card,
  Container,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDashboardSummary } from "../api/hooks";

export default function ReportsPage() {
  const { data: summary, isPending, error } = useDashboardSummary();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleExport = () => {
    window.location.href = "/api/v1/iaa/reports/export/";
  };

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Financial Reports & Analytics"
          subtitle="Operational turnaround metrics, status distribution, and ledger reporting."
          action={
            <Button variant="outline" onClick={handleExport}>
              Export CSV Report
            </Button>
          }
        />

        {isPending ? (
          <Text>Loading dashboard summary...</Text>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Total Requests
              </Text>
              <Title order={2}>{summary?.requests.total_count ?? 0}</Title>
              <Text size="sm" mt="xs">
                Total Volume: ₹{summary?.requests.total_amount.toLocaleString() ?? 0}
              </Text>
            </Card>

            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Travel Claims
              </Text>
              <Title order={2}>{summary?.travel.total_count ?? 0}</Title>
              <Text size="sm" mt="xs">
                Total Volume: ₹{summary?.travel.total_amount.toLocaleString() ?? 0}
              </Text>
            </Card>

            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Open Anomalies
              </Text>
              <Title order={2} c="orange">
                {summary?.anomalies.by_status.open ?? 0}
              </Title>
              <Text size="sm" mt="xs">
                Total Flagged: {summary?.anomalies.total_count ?? 0}
              </Text>
            </Card>

            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Audit Observations
              </Text>
              <Title order={2} c="blue">
                {summary?.audit.total_count ?? 0}
              </Title>
              <Text size="sm" mt="xs">
                Closed: {summary?.audit.by_status.closed ?? 0}
              </Text>
            </Card>
          </SimpleGrid>
        )}
      </Stack>
    </Container>
  );
}
