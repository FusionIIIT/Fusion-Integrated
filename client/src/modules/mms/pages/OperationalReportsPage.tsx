import { Alert, Card, Container, SimpleGrid, Stack, Text } from "@mantine/core";
import { FaFileInvoice, FaUsers, FaUtensils } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useOperationalReport } from "../api/hooks";

export default function OperationalReportsPage() {
  const { data: report, isLoading, error } = useOperationalReport();

  if (error) {
    return <Container size="md"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="md">
      <PageHeader title="Mess Operational Reports" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">Operational summaries for active cycle: {report?.period || "Current"}</Text>
        {isLoading ? (
          <Text c="dimmed">Loading operational report...</Text>
        ) : !report ? (
          <Alert color="gray">No operational data available.</Alert>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Registered Students</Text>
              <Text fw={700} size="xl">{report.total_registered_students}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Pending Registrations</Text>
              <Text fw={700} size="xl" c="orange">{report.pending_registrations}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Active Rebates</Text>
              <Text fw={700} size="xl" c="blue">{report.active_rebates}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Pending Special Food</Text>
              <Text fw={700} size="xl" c="teal">{report.pending_special_food}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Bills Generated</Text>
              <Text fw={700} size="xl">{report.bills_generated}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Feedback Entries</Text>
              <Text fw={700} size="xl">{report.feedback_count}</Text>
            </Card>
          </SimpleGrid>
        )}
      </Stack>
    </Container>
  );
}
