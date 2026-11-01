import {
  Alert,
  Badge,
  Card,
  Grid,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  FaArchive,
  FaCheckCircle,
  FaExclamationTriangle,
  FaHistory,
  FaIdBadge,
  FaShieldAlt,
  FaUsers,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAdminDashboard } from "../api/hooks";

export default function DashboardPage() {
  const { data: metrics, isLoading, error } = useAdminDashboard();

  if (isLoading) {
    return (
      <Stack align="center" justify="center" py={80}>
        <Loader size="lg" />
        <Text c="dimmed">Loading Super Admin control plane telemetry...</Text>
      </Stack>
    );
  }

  if (error || !metrics) {
    return (
      <Alert color="red" title="Failed to load dashboard metrics" icon={<FaExclamationTriangle />}>
        Unable to communicate with the System Admin control plane. Verify permissions and session.
      </Alert>
    );
  }

  const { users, roles, archival, security, recent_activity } = metrics;

  return (
    <Stack gap="lg">
      <PageHeader
        title="System Administration Dashboard"
        subtitle="Operational telemetry, identity management, and compliance control plane"
        action={
          <Group>
            <Badge
              size="lg"
              color={security.system_health === "nominal" ? "green" : "red"}
              leftSection={
                security.system_health === "nominal" ? (
                  <FaCheckCircle size={12} />
                ) : (
                  <FaExclamationTriangle size={12} />
                )
              }
            >
              System Health: {security.system_health.toUpperCase()}
            </Badge>
          </Group>
        }
      />

      {security.consecutive_failed_login_alert && (
        <Alert
          color="red"
          title="Security Alert: Consecutive Failed Login Threshold Exceeded"
          icon={<FaExclamationTriangle />}
        >
          Five consecutive failed Super Admin login attempts detected (BR-SA-024). Review audit logs and active operator sessions immediately.
        </Alert>
      )}

      {/* Top Telemetry Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Total Users
            </Text>
            <ThemeIcon color="blue" variant="light" size={36} radius="md">
              <FaUsers size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt="sm">
            <Text fw={700} size="xl">
              {users.total}
            </Text>
            <Text c="green" size="sm" fw={500}>
              {users.active} active
            </Text>
          </Group>
          <Text size="xs" c="dimmed" mt={4}>
            {users.deactivated} deactivated · {users.archived} archived
          </Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Active Roles
            </Text>
            <ThemeIcon color="violet" variant="light" size={36} radius="md">
              <FaIdBadge size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt="sm">
            <Text fw={700} size="xl">
              {roles.active_assignments}
            </Text>
            <Text c="dimmed" size="sm">
              / {roles.total_definitions} definitions
            </Text>
          </Group>
          <Text size="xs" c="dimmed" mt={4}>
            {roles.upcoming_expiries_30d} expiring in 30 days
          </Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Archived Data
            </Text>
            <ThemeIcon color="orange" variant="light" size={36} radius="md">
              <FaArchive size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt="sm">
            <Text fw={700} size="xl">
              {archival.archived_data_records}
            </Text>
            <Text c="dimmed" size="sm">
              historical records
            </Text>
          </Group>
          <Text size="xs" c={archival.pending_purge_authorizations > 0 ? "orange" : "dimmed"} mt={4}>
            {archival.pending_purge_authorizations} pending purge authorizations
          </Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Security & Sessions
            </Text>
            <ThemeIcon color="teal" variant="light" size={36} radius="md">
              <FaShieldAlt size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt="sm">
            <Text fw={700} size="xl">
              {security.active_sessions}
            </Text>
            <Text c="dimmed" size="sm">
              active sessions
            </Text>
          </Group>
          <Text size="xs" c={security.failed_logins_last_24h > 0 ? "red" : "dimmed"} mt={4}>
            {security.failed_logins_last_24h} failed logins (24h)
          </Text>
        </Paper>
      </SimpleGrid>

      {/* Breakdown Grid */}
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder radius="md" p="md">
            <Title order={4} mb="xs">
              User Directory Breakdown
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              Distribution of institution identities managed across Fusion.
            </Text>
            <Stack gap="xs">
              {Object.entries(users.by_type || {}).map(([type, count]) => (
                <Group key={type} justify="space-between" p="xs" style={{ background: "var(--mantine-color-gray-0)", borderRadius: 6 }}>
                  <Text fw={600} tt="capitalize">
                    {type}
                  </Text>
                  <Badge variant="outline" size="lg">
                    {count}
                  </Badge>
                </Group>
              ))}
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder radius="md" p="md">
            <Group justify="space-between" mb="xs">
              <Title order={4}>Recent Audit Activity</Title>
              <ThemeIcon variant="subtle" color="gray">
                <FaHistory size={16} />
              </ThemeIcon>
            </Group>
            <Text size="sm" c="dimmed" mb="md">
              Immutable log stream of control plane modifications (CFR-SA-017).
            </Text>

            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Timestamp</Table.Th>
                  <Table.Th>Actor</Table.Th>
                  <Table.Th>Action</Table.Th>
                  <Table.Th>Result</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {recent_activity.map((act) => (
                  <Table.Tr key={act.id}>
                    <Table.Td style={{ whiteSpace: "nowrap" }}>
                      <Text size="xs" c="dimmed">
                        {new Date(act.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        {act.actor_username}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {act.action}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <StatusBadge status={act.result} />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
