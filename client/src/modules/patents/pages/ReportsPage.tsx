import { Card, Container, SimpleGrid, Stack, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSummary } from "../api";

export default function ReportsPage() {
  const { data, error, isPending } = useSummary();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  if (isPending || !data) return null;

  return (
    <Container size="xl">
      <PageHeader title="Reports" subtitle="Applications by status, as you are allowed to see them" />
      <Stack gap="lg">
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          <Card padding="lg">
            <Text size="xs" c="dimmed" tt="uppercase">Applications</Text>
            <Text size="xl" fw={700}>{data.total}</Text>
          </Card>
          <Card padding="lg">
            <Text size="xs" c="dimmed" tt="uppercase">Approved budget</Text>
            <Text size="xl" fw={700}>₹ {data.approved_budget}</Text>
          </Card>
        </SimpleGrid>
        <Card padding="lg">
          <Text fw={600} mb="sm">By status</Text>
          {Object.keys(data.by_status).length === 0 ? (
            <Text size="sm" c="dimmed">No applications yet.</Text>
          ) : (
            <Table striped>
              <Table.Tbody>
                {Object.entries(data.by_status).map(([label, n]) => (
                  <Table.Tr key={label}>
                    <Table.Td>{label}</Table.Td>
                    <Table.Td ta="right">{n}</Table.Td>
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
