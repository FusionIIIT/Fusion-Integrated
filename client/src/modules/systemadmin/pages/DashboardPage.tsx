import { useState } from "react";
import {
  SimpleGrid,
  Card,
  Text,
  Title,
  Group,
  Stack,
  Badge,
  Table,
  Button,
  Alert,
  Loader,
  Paper,
  Divider,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDashboardMetrics, useRoles } from "../api/hooks";
import { CreateUserModal } from "../components/UserModals";
import { AssignRoleModal } from "../components/RoleModals";

export default function DashboardPage() {
  const { data: metrics, isLoading, error } = useDashboardMetrics();
  const { data: rolesData } = useRoles();

  const [createUserOpen, setCreateUserOpen] = useState(false);
  const [assignRoleOpen, setAssignRoleOpen] = useState(false);

  if (isLoading) {
    return (
      <Stack align="center" justify="center" p="xl" style={{ minHeight: 300 }}>
        <Loader size="lg" />
        <Text c="dimmed">Loading system administration metrics...</Text>
      </Stack>
    );
  }

  if (error || !metrics) {
    return (
      <Alert color="red" title="Error Loading Dashboard">
        Could not retrieve real-time monitoring metrics. Please verify system health.
      </Alert>
    );
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title="System Administration Dashboard"
        subtitle="Real-time institutional control plane metrics and security monitoring"
        action={
          <Group gap="sm">
            <Button variant="default" onClick={() => setCreateUserOpen(true)}>+ New User</Button>
            <Button onClick={() => setAssignRoleOpen(true)}>+ Assign Role</Button>
          </Group>
        }
      />

      {/* KPI Cards Grid */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }}>
        <Card withBorder padding="md" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Basic Users</Text>
          <Group justify="space-between" mt="xs">
            <Title order={2}>{metrics.users.total}</Title>
            <Badge color="green" variant="light">{metrics.users.active} Active</Badge>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">
            {metrics.users.deactivated} deactivated • {metrics.users.archived} archived
          </Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Role Assignments</Text>
          <Group justify="space-between" mt="xs">
            <Title order={2}>{metrics.roles.active_assignments}</Title>
            <Badge color="blue" variant="light">{metrics.roles.total_defined} Defined</Badge>
          </Group>
          <Text size="xs" c={metrics.roles.expiring_soon_count > 0 ? "orange" : "dimmed"} mt="xs">
            {metrics.roles.expiring_soon_count} expiring within 30 days
          </Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Singular Roles Vacant</Text>
          <Group justify="space-between" mt="xs">
            <Title order={2} c={metrics.roles.vacant_singular_count > 0 ? "red" : "dark"}>
              {metrics.roles.vacant_singular_count}
            </Title>
            <Badge color={metrics.roles.vacant_singular_count > 0 ? "red" : "gray"} variant="light">
              {metrics.roles.vacant_singular_count > 0 ? "Attention Needed" : "Full Coverage"}
            </Badge>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">Key institutional offices without an active holder</Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Purge & Security Alerts</Text>
          <Group justify="space-between" mt="xs">
            <Title order={2} c={metrics.archival.pending_purge_requests > 0 ? "orange" : "dark"}>
              {metrics.archival.pending_purge_requests}
            </Title>
            <Badge color={metrics.security.unresolved_alerts > 0 ? "red" : "green"} variant="light">
              {metrics.security.unresolved_alerts} Unresolved
            </Badge>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">
            {metrics.security.active_sessions} active admin session(s)
          </Text>
        </Card>
      </SimpleGrid>

      {/* Vacant Singular Roles Warning */}
      {metrics.roles.vacant_singular_count > 0 && (
        <Paper withBorder p="md" radius="md" style={{ borderColor: "#ffa94d" }}>
          <Group justify="space-between" mb="xs">
            <Stack gap={2}>
              <Title order={4} c="orange">Vacant Key Offices (Singular Roles)</Title>
              <Text size="xs" c="dimmed">
                The following singular institutional roles require an active appointment.
              </Text>
            </Stack>
            <Button size="xs" component={Link} to="/systemadmin/assignments">
              Manage Assignments
            </Button>
          </Group>
          <Table mt="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Role Code</Table.Th>
                <Table.Th>Office / Role Name</Table.Th>
                <Table.Th>Department / Scope</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {metrics.roles.vacant_singular_roles.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td><Badge variant="outline">{r.code}</Badge></Table.Td>
                  <Table.Td fw={500}>{r.name}</Table.Td>
                  <Table.Td>{r.module_or_dept || "Institute-wide"}</Table.Td>
                  <Table.Td>
                    <Button size="xs" variant="light" onClick={() => setAssignRoleOpen(true)}>
                      Assign Holder
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      {/* Quick Navigation and Recent Audit Stream */}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {/* User Distribution */}
        <Card withBorder padding="md" radius="md">
          <Title order={4} mb="xs">User Directory Breakdown</Title>
          <Stack gap="xs">
            {metrics.users.by_type.map((t) => (
              <Group key={t.user_type} justify="space-between">
                <Text size="sm" tt="capitalize">{t.user_type}s</Text>
                <Badge variant="light" size="lg">{t.count}</Badge>
              </Group>
            ))}
            <Divider my="xs" />
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Reversible Archived Users:</Text>
              <Text size="sm" fw={600}>{metrics.archival.reversible_users}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Permanent Non-Restorable Users:</Text>
              <Text size="sm" fw={600}>{metrics.archival.permanent_users}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Historical Data Batches Archived:</Text>
              <Text size="sm" fw={600}>{metrics.archival.historical_batches}</Text>
            </Group>
          </Stack>
        </Card>

        {/* Recent Audit Actions Stream */}
        <Card withBorder padding="md" radius="md">
          <Group justify="space-between" mb="xs">
            <Title order={4}>Recent Audit Trail</Title>
            <Button size="xs" variant="subtle" component={Link} to="/systemadmin/audit">
              View All Logs
            </Button>
          </Group>
          <Table verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Timestamp</Table.Th>
                <Table.Th>Actor</Table.Th>
                <Table.Th>Action</Table.Th>
                <Table.Th>Result</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {metrics.security.recent_actions.map((a) => (
                <Table.Tr key={a.id}>
                  <Table.Td>
                    <Text size="xs">{new Date(a.timestamp).toLocaleTimeString()}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" fw={500}>{a.actor_username}</Text>
                  </Table.Td>
                  <Table.Td><Badge size="xs" variant="dot">{a.action}</Badge></Table.Td>
                  <Table.Td>
                    <Badge size="xs" color={a.result === "SUCCESS" ? "green" : "red"}>
                      {a.result}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      </SimpleGrid>

      {/* Modals */}
      <CreateUserModal opened={createUserOpen} onClose={() => setCreateUserOpen(false)} />
      {rolesData && (
        <AssignRoleModal
          roles={rolesData.results}
          opened={assignRoleOpen}
          onClose={() => setAssignRoleOpen(false)}
        />
      )}
    </Stack>
  );
}
