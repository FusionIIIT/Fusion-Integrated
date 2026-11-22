import {
  Badge,
  Card,
  Container,
  Grid,
  Group,
  Loader,
  Paper,
  Progress,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaListAlt,
  FaStar,
  FaSyncAlt,
} from "react-icons/fa";

import { useReportsSummary } from "../api/hooks";

export function ReportsPage() {
  const { data: summary, isLoading } = useReportsSummary();

  if (isLoading) {
    return (
      <Container size="xl" py="xl">
        <Stack align="center">
          <Loader size="lg" />
          <Text size="sm" c="dimmed">
            Compiling CMS operational reports...
          </Text>
        </Stack>
      </Container>
    );
  }

  const byStatus = summary?.by_status || {};
  const byPriority = summary?.by_priority || {};
  const byCategory = summary?.by_category || [];
  const total = summary?.total_complaints || 0;

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <div>
          <Title order={2}>Complaints Reports & Analytics</Title>
          <Text c="dimmed" size="sm">
            Institutional operational metrics, resolution efficiency, and SLA performance.
          </Text>
        </div>

        {/* Top KPI Cards */}
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Paper withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Total Complaints
                </Text>
                <FaListAlt color="#228be6" />
              </Group>
              <Title order={2} mt="xs">
                {total}
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                All time registered complaints
              </Text>
            </Paper>
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Paper withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  In Progress
                </Text>
                <FaSyncAlt color="#fab005" />
              </Group>
              <Title order={2} mt="xs">
                {byStatus["in_progress"] || 0}
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                Active operational handling
              </Text>
            </Paper>
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Paper withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Resolved & Closed
                </Text>
                <FaCheckCircle color="#12b886" />
              </Group>
              <Title order={2} mt="xs">
                {(byStatus["resolved"] || 0) + (byStatus["closed"] || 0)}
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                Successfully completed resolutions
              </Text>
            </Paper>
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
            <Paper withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Satisfaction Score
                </Text>
                <FaStar color="#f59f00" />
              </Group>
              <Title order={2} mt="xs">
                {summary?.average_rating ? `${summary.average_rating} / 5` : "N/A"}
              </Title>
              <Text size="xs" c="dimmed" mt={4}>
                Based on {summary?.total_feedback || 0} user ratings
              </Text>
            </Paper>
          </Grid.Col>
        </Grid>

        {/* SLA & Escalation Cards */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card withBorder p="md" radius="md">
              <Group justify="space-between" mb="sm">
                <Title order={4}>Escalation & SLA Health</Title>
                <FaExclamationTriangle color="#e03131" />
              </Group>
              <Stack gap="sm">
                <Group justify="space-between">
                  <Text size="sm">Escalated Complaints (Manual + SLA)</Text>
                  <Badge color="red" size="lg">
                    {summary?.escalated_count || 0}
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Active Breached SLAs</Text>
                  <Badge color="orange" size="lg">
                    {summary?.sla_breached_count || 0}
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm">Total Rejected Submissions</Text>
                  <Badge color="gray" size="lg">
                    {byStatus["rejected"] || 0}
                  </Badge>
                </Group>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card withBorder p="md" radius="md">
              <Title order={4} mb="sm">
                Priority Distribution
              </Title>
              <Stack gap="sm">
                <div>
                  <Group justify="space-between" mb={4}>
                    <Text size="sm">High Priority (24h SLA)</Text>
                    <Text size="sm" fw={700}>
                      {byPriority["high"] || 0}
                    </Text>
                  </Group>
                  <Progress
                    color="red"
                    value={total ? ((byPriority["high"] || 0) / total) * 100 : 0}
                  />
                </div>
                <div>
                  <Group justify="space-between" mb={4}>
                    <Text size="sm">Medium Priority (48h SLA)</Text>
                    <Text size="sm" fw={700}>
                      {byPriority["medium"] || 0}
                    </Text>
                  </Group>
                  <Progress
                    color="orange"
                    value={total ? ((byPriority["medium"] || 0) / total) * 100 : 0}
                  />
                </div>
                <div>
                  <Group justify="space-between" mb={4}>
                    <Text size="sm">Low Priority (72h SLA)</Text>
                    <Text size="sm" fw={700}>
                      {byPriority["low"] || 0}
                    </Text>
                  </Group>
                  <Progress
                    color="blue"
                    value={total ? ((byPriority["low"] || 0) / total) * 100 : 0}
                  />
                </div>
              </Stack>
            </Card>
          </Grid.Col>
        </Grid>

        {/* Category Breakdown Table */}
        <Card withBorder radius="md" p="md">
          <Title order={4} mb="md">
            Complaints by Category
          </Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category Name</Table.Th>
                <Table.Th>Total Logged</Table.Th>
                <Table.Th>Share of Total</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {byCategory.map((cat) => (
                <Table.Tr key={cat.id}>
                  <Table.Td fw={500}>{cat.name}</Table.Td>
                  <Table.Td>{cat.count}</Table.Td>
                  <Table.Td>
                    {total > 0 ? `${Math.round((cat.count / total) * 100)}%` : "0%"}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>
    </Container>
  );
}

export default ReportsPage;

