import {
  Alert, Card, Container, Grid, Group, Progress, SimpleGrid, Stack, Table, Text,
} from "@mantine/core";
import { FaChartBar, FaInfoCircle } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useStats } from "../api/hooks";

function Metric({ label, value, hint }: {
  label: string; value: string | number | null | undefined; hint?: string;
}) {
  return (
    <Card padding="md" withBorder>
      <Text size="xs" c="dimmed" tt="uppercase">{label}</Text>
      <Text fw={700} size="xl" mt={2}>{value ?? "—"}</Text>
      {hint && <Text size="xs" c="dimmed" mt={2}>{hint}</Text>}
    </Card>
  );
}

export default function ReportsPage() {
  const { data, isPending, error } = useStats();
  const { can } = useAuth();
  const isStaff = can("placement_cell.report.view");

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  if (isPending) return <Container size="lg"><Text c="dimmed">Loading…</Text></Container>;

  // Too few placements to publish safely. An "anonymous" aggregate over a
  // handful of people is not anonymous, so the server suppresses it entirely.
  if (data && data.available === false) {
    return (
      <Container size="lg">
        <PageHeader title="Placement Statistics" subtitle={data.season} />
        <Alert variant="light" color="blue" icon={<FaInfoCircle />}
          title="Statistics are not published yet">
          <Text size="sm">
            {data.reason
              ?? "There is not enough data to publish figures for this season."}
          </Text>
        </Alert>
      </Container>
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title={isStaff ? "Placement Reports" : "Placement Statistics"}
        subtitle={isStaff
          ? `Operational figures for ${data?.season}`
          : `Anonymised figures for ${data?.season}`}
      />

      <SimpleGrid cols={{ base: 2, sm: 4 }} mb="md">
        <Metric label="Registered" value={data?.registered} />
        <Metric label="Placed" value={data?.placed} />
        <Metric
          label="Median CTC"
          value={data?.median_ctc ? `${data.median_ctc} LPA` : null}
        />
        <Metric
          label="Highest CTC"
          value={data?.max_ctc ? `${data.max_ctc} LPA` : null}
        />
      </SimpleGrid>

      {typeof data?.placement_rate === "number" && (
        <Card padding="lg" mb="md">
          <Group justify="space-between" mb={6}>
            <Text fw={600}>Placement rate</Text>
            <Text fw={700}>{data.placement_rate}%</Text>
          </Group>
          <Progress value={data.placement_rate} size="lg" color="teal" />
        </Card>
      )}

      <Grid>
        <Grid.Col span={{ base: 12, md: isStaff ? 7 : 12 }}>
          <Card padding="lg">
            <Group gap="xs" mb="sm">
              <FaChartBar size={13} />
              <Text fw={600}>By company</Text>
            </Group>
            {/* Small cells are suppressed server-side: a per-company count of
                one or two identifies the individual. */}
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Company</Table.Th>
                  <Table.Th ta="right">Placed</Table.Th>
                  {isStaff && <Table.Th ta="right">Highest CTC</Table.Th>}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(isStaff
                  ? (data?.by_company ?? []).map((c) => ({
                      name: c.company__name, placed: c.placed, top: c.top }))
                  : (data?.companies ?? []).map((c) => ({
                      name: c.company, placed: c.placed, top: null }))
                ).map((c) => (
                  <Table.Tr key={c.name}>
                    <Table.Td>{c.name}</Table.Td>
                    <Table.Td ta="right">{c.placed}</Table.Td>
                    {isStaff && <Table.Td ta="right">{c.top ?? "—"}</Table.Td>}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {!isStaff && (
              <Text size="xs" c="dimmed" mt="sm">
                Companies with very few placements are not listed, so that no
                individual can be identified from these figures.
              </Text>
            )}
          </Card>
        </Grid.Col>

        {isStaff && (
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Card padding="lg">
              <Text fw={600} mb="sm">Applications by status</Text>
              <Stack gap={6}>
                {Object.entries(data?.applications_by_status ?? {}).map(
                  ([status, n]) => (
                    <Group key={status} justify="space-between">
                      <Text size="sm">{status.replace(/_/g, " ")}</Text>
                      <Text size="sm" fw={600}>{n}</Text>
                    </Group>
                  ))}
              </Stack>
              <Group justify="space-between" mt="md">
                <Text size="sm" c="dimmed">Debarred</Text>
                <Text size="sm" fw={600}>{data?.debarred ?? 0}</Text>
              </Group>
            </Card>
          </Grid.Col>
        )}
      </Grid>
    </Container>
  );
}
