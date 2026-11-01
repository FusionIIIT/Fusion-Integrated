import { useState } from "react";
import {
  Stack,
  SimpleGrid,
  Paper,
  Text,
  Title,
  Group,
  Table,
  Badge,
  Button,
  TextInput,
  Progress,
  Loader,
  Alert,
} from "@mantine/core";
import {
  FaFileDownload,
  FaCheckCircle,
  FaTimesCircle,
  FaUserShield,
  FaCalendarAlt,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditReport } from "../api/hooks";

export default function AuditReportsPage() {
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 30 * 86400000).toISOString().split("T")[0]
  );
  const [endDate, setEndDate] = useState(
    new Date().toISOString().split("T")[0]
  );

  const { data, isLoading, error } = useAuditReport({
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  });

  const formatAction = (action: string) => {
    return action
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  const handleExportCSV = () => {
    if (!data) return;
    const rows = [
      ["Metric", "Value"],
      ["Total Operations", data.total_actions],
      ["Successful Operations", data.success_count],
      ["Failed Operations", data.failure_count],
      ["Rejected Operations", data.rejected_count],
      [],
      ["Action Breakdown", "Count"],
      ...data.actions_breakdown.map((a) => [a.action, a.count]),
      [],
      ["Top Administrative Actors", "Operations Count"],
      ...data.top_actors.map((u) => [u.actor_username, u.count]),
    ];

    const csvContent =
      "data:text/csv;charset=utf-8," +
      rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `SystemAdmin_Audit_Report_${startDate}_to_${endDate}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="Audit & Compliance Reports"
        subtitle="Aggregated institutional analytics, administrative usage trends, and compliance auditing"
        action={
          <Button
            leftSection={<FaFileDownload size={14} />}
            variant="outline"
            onClick={handleExportCSV}
            disabled={!data || data.total_actions === 0}
          >
            Export CSV Report
          </Button>
        }
      />

      {/* Date Range Selector */}
      <Paper withBorder p="md" radius="md">
        <Group justify="space-between">
          <Group>
            <TextInput
              label="Start Date"
              type="date"
              leftSection={<FaCalendarAlt size={14} />}
              value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
            />
            <TextInput
              label="End Date"
              type="date"
              leftSection={<FaCalendarAlt size={14} />}
              value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
            />
          </Group>
          <Text size="sm" c="dimmed">
            Reporting Period: {startDate} to {endDate}
          </Text>
        </Group>
      </Paper>

      {isLoading && (
        <Stack align="center" justify="center" p="xl">
          <Loader />
          <Text c="dimmed">Compiling audit metrics...</Text>
        </Stack>
      )}

      {error && (
        <Alert color="red" title="Error">
          Failed to generate audit report metrics.
        </Alert>
      )}

      {data && (
        <>
          {/* Summary KPI Cards */}
          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
            <Paper withBorder p="md" radius="md">
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Total Operations
              </Text>
              <Text size="xl" fw={700} mt="xs">
                {data.total_actions.toLocaleString()}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                Recorded audit events in range
              </Text>
            </Paper>

            <Paper withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Success Rate
                </Text>
                <FaCheckCircle color="#2f9e44" size={16} />
              </Group>
              <Text size="xl" fw={700} c="green" mt="xs">
                {data.total_actions > 0
                  ? ((data.success_count / data.total_actions) * 100).toFixed(1)
                  : 0}
                %
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                {data.success_count} successful operations
              </Text>
            </Paper>

            <Paper withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Failed Operations
                </Text>
                <FaTimesCircle color="#e03131" size={16} />
              </Group>
              <Text size="xl" fw={700} c={data.failure_count > 0 ? "red" : "gray"} mt="xs">
                {data.failure_count}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                Errors and exceptions logged
              </Text>
            </Paper>

            <Paper withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Policy Rejections
                </Text>
                <FaUserShield color="#f59f00" size={16} />
              </Group>
              <Text size="xl" fw={700} c={data.rejected_count > 0 ? "orange" : "gray"} mt="xs">
                {data.rejected_count}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                SoD / boundary check denials
              </Text>
            </Paper>
          </SimpleGrid>

          {/* Breakdown Tables */}
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            {/* Action Distribution */}
            <Paper withBorder p="md" radius="md">
              <Title order={5} mb="sm">
                Administrative Actions Distribution
              </Title>
              <Table verticalSpacing="xs">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Action Type</Table.Th>
                    <Table.Th>Count</Table.Th>
                    <Table.Th>Distribution</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.actions_breakdown.map((item) => {
                    const pct = data.total_actions > 0
                      ? (item.count / data.total_actions) * 100
                      : 0;
                    return (
                      <Table.Tr key={item.action}>
                        <Table.Td>
                          <Text size="sm" fw={500}>{formatAction(item.action)}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge variant="light" color="blue">
                            {item.count}
                          </Badge>
                        </Table.Td>
                        <Table.Td style={{ width: "40%" }}>
                          <Group gap="xs">
                            <Progress value={pct} size="sm" style={{ flex: 1 }} />
                            <Text size="xs" c="dimmed" w={40}>
                              {pct.toFixed(0)}%
                            </Text>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                  {data.actions_breakdown.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={3} style={{ textAlign: "center", padding: "1.5rem" }}>
                        <Text c="dimmed">No operations recorded in this timeframe.</Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Paper>

            {/* Top Administrative Actors */}
            <Paper withBorder p="md" radius="md">
              <Title order={5} mb="sm">
                Most Active System Operators
              </Title>
              <Table verticalSpacing="xs">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Operator Username</Table.Th>
                    <Table.Th>Total Events Executed</Table.Th>
                    <Table.Th>Proportion</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.top_actors.map((actor) => {
                    const pct = data.total_actions > 0
                      ? (actor.count / data.total_actions) * 100
                      : 0;
                    return (
                      <Table.Tr key={actor.actor_username}>
                        <Table.Td>
                          <Text size="sm" fw={600}>{actor.actor_username}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge color="violet">{actor.count}</Badge>
                        </Table.Td>
                        <Table.Td style={{ width: "40%" }}>
                          <Group gap="xs">
                            <Progress value={pct} color="grape" size="sm" style={{ flex: 1 }} />
                            <Text size="xs" c="dimmed" w={40}>
                              {pct.toFixed(0)}%
                            </Text>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                  {data.top_actors.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={3} style={{ textAlign: "center", padding: "1.5rem" }}>
                        <Text c="dimmed">No actor records found.</Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Paper>
          </SimpleGrid>
        </>
      )}
    </Stack>
  );
}
