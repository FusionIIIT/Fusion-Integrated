import { Alert, Card, Container, SimpleGrid, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSupervisoryReport } from "../api/hooks";

export default function SupervisoryReportsPage() {
  const { data: report, isLoading, error } = useSupervisoryReport();

  if (error) {
    return <Container size="md"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="md">
      <PageHeader title="Mess Supervisory Reports (Warden)" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">Executive and supervisory metrics for period: {report?.period || "Current"}</Text>
        {isLoading ? (
          <Text c="dimmed">Loading supervisory report...</Text>
        ) : !report ? (
          <Alert color="gray">No supervisory data available.</Alert>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Total Billed Amount</Text>
              <Text fw={700} size="xl">₹{report.total_billed_amount}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Total Rebate Deductions</Text>
              <Text fw={700} size="xl" c="green">₹{report.total_rebate_deductions}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Special Food Charges</Text>
              <Text fw={700} size="xl">₹{report.total_special_food_charges}</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Survey Participation Rate</Text>
              <Text fw={700} size="xl" c="blue">{report.survey_participation_rate}%</Text>
            </Card>
            <Card withBorder padding="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Student Feedback Count</Text>
              <Text fw={700} size="xl">{report.feedback_count}</Text>
            </Card>
          </SimpleGrid>
        )}
      </Stack>
    </Container>
  );
}
