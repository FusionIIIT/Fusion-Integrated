import { Alert, Card, Container, Stack, Table, Text } from "@mantine/core";
import { FaChartPie } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useVacationSurveySummary } from "../api/hooks";

export default function SurveySummaryPage() {
  const { data: summaries, isLoading, error } = useVacationSurveySummary();

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="Vacation Survey Summaries" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Aggregated response statistics for food continuity decisions.
        </Text>

        <Card withBorder padding="md">
          {isLoading ? (
            <Text c="dimmed">Loading survey summaries...</Text>
          ) : !summaries || summaries.length === 0 ? (
            <Alert color="gray" icon={<FaChartPie />}>No survey responses recorded yet.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Vacation</Table.Th>
                  <Table.Th>Deadline</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Yes</Table.Th>
                  <Table.Th>No</Table.Th>
                  <Table.Th>Default-No</Table.Th>
                  <Table.Th>Total Responses</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {summaries.map((s) => (
                  <Table.Tr key={s.survey_id}>
                    <Table.Td>#{s.survey_id}</Table.Td>
                    <Table.Td fw={600}>{s.vacation}</Table.Td>
                    <Table.Td>{new Date(s.response_deadline).toLocaleString()}</Table.Td>
                    <Table.Td><StatusBadge status={s.is_open ? "active" : "closed"} /></Table.Td>
                    <Table.Td c="teal" fw={700}>{s.yes}</Table.Td>
                    <Table.Td c="gray">{s.no}</Table.Td>
                    <Table.Td c="orange">{s.default_no}</Table.Td>
                    <Table.Td fw={600}>{s.total}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
