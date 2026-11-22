import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import {
  FaArchive,
  FaCheckCircle,
  FaIdBadge,
  FaShieldAlt,
  FaSlidersH,
  FaUserCog,
  FaUsers,
} from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { adminApi } from "../api/client";
import type { DashboardMetrics } from "../api/types";

export default function DashboardPage() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi
      .getDashboard()
      .then((data) => setMetrics(data))
      .catch((err) => console.error("Failed to load dashboard metrics", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="System Administration Dashboard"
        subtitle="Institutional identity governance, role directory, archival control, and security monitoring."
      />

      <Grid mb="lg">
        <Grid.Col span={{ base: 12, md: 8 }}>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            {/* Users Metric Card */}
            <Card withBorder padding="lg" radius="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" c="dimmed" fw={600}>
                  USER POPULATION
                </Text>
                <ThemeIcon color="blue" variant="light" size="lg" radius="md">
                  <FaUsers size={18} />
                </ThemeIcon>
              </Group>
              <Title order={2}>{loading ? "..." : metrics?.users.total ?? 0}</Title>
              <Group mt="xs" gap="xs">
                <Badge color="green" variant="light">
                  {metrics?.users.active ?? 0} Active
                </Badge>
                <Badge color="yellow" variant="light">
                  {metrics?.users.deactivated ?? 0} Deactivated
                </Badge>
                <Badge color="gray" variant="light">
                  {metrics?.users.archived ?? 0} Archived
                </Badge>
              </Group>
            </Card>

            {/* Roles Metric Card */}
            <Card withBorder padding="lg" radius="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" c="dimmed" fw={600}>
                  ACTIVE ROLES & POSITIONS
                </Text>
                <ThemeIcon color="teal" variant="light" size="lg" radius="md">
                  <FaIdBadge size={18} />
                </ThemeIcon>
              </Group>
              <Title order={2}>{loading ? "..." : metrics?.roles.active_assignments ?? 0}</Title>
              <Group mt="xs" gap="xs">
                <Badge color="red" variant="light">
                  {metrics?.roles.vacant_singular_roles ?? 0} Vacant Key Roles
                </Badge>
                <Badge color="orange" variant="light">
                  {metrics?.roles.approaching_expiries_30d ?? 0} Expiring Soon
                </Badge>
              </Group>
            </Card>

            {/* Security Monitoring Card */}
            <Card withBorder padding="lg" radius="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" c="dimmed" fw={600}>
                  SECURITY & AUTH MONITORING
                </Text>
                <ThemeIcon color="red" variant="light" size="lg" radius="md">
                  <FaShieldAlt size={18} />
                </ThemeIcon>
              </Group>
              <Title order={2}>{loading ? "..." : metrics?.security.failed_logins_24h ?? 0}</Title>
              <Text size="xs" c="dimmed" mt="xs">
                Failed logins past 24h | {metrics?.security.total_audit_events ?? 0} Audit events
              </Text>
            </Card>

            {/* Archival Volume Card */}
            <Card withBorder padding="lg" radius="md">
              <Group justify="space-between" mb="xs">
                <Text size="sm" c="dimmed" fw={600}>
                  ARCHIVE & PURGE CONTROL
                </Text>
                <ThemeIcon color="grape" variant="light" size="lg" radius="md">
                  <FaArchive size={18} />
                </ThemeIcon>
              </Group>
              <Title order={2}>{loading ? "..." : metrics?.archives.archived_users ?? 0}</Title>
              <Text size="xs" c="dimmed" mt="xs">
                {metrics?.archives.pending_purge_authorizations ?? 0} Pending dual-auth purge decisions
              </Text>
            </Card>
          </SimpleGrid>
        </Grid.Col>

        {/* Quick Operations & System Health */}
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Stack gap="md">
            <Card withBorder padding="lg" radius="md">
              <Group justify="space-between" mb="sm">
                <Text fw={600}>Platform Health</Text>
                <Badge color="green" leftSection={<FaCheckCircle size={12} />}>
                  Operational
                </Badge>
              </Group>
              <Stack gap="xs" mt="xs">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Database
                  </Text>
                  <Text size="sm" fw={500}>
                    PostgreSQL 16 (Connected)
                  </Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    IAM Integration
                  </Text>
                  <Text size="sm" fw={500}>
                    Online (Port 8001)
                  </Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Dual Auth Policy
                  </Text>
                  <Text size="sm" fw={500}>
                    Active (Enforced)
                  </Text>
                </Group>
              </Stack>
            </Card>

            <Card withBorder padding="lg" radius="md">
              <Text fw={600} mb="sm">
                Administrative Shortcuts
              </Text>
              <Stack gap="xs">
                <Button
                  variant="light"
                  leftSection={<FaUserCog />}
                  onClick={() => navigate("/system_admin/users")}
                  fullWidth
                >
                  Manage Users
                </Button>
                <Button
                  variant="light"
                  color="teal"
                  leftSection={<FaIdBadge />}
                  onClick={() => navigate("/system_admin/roles")}
                  fullWidth
                >
                  Assign / Reassign Role
                </Button>
                <Button
                  variant="light"
                  color="grape"
                  leftSection={<FaArchive />}
                  onClick={() => navigate("/system_admin/archives")}
                  fullWidth
                >
                  Archive Control & Restoration
                </Button>
                <Button
                  variant="light"
                  color="gray"
                  leftSection={<FaSlidersH />}
                  onClick={() => navigate("/system_admin/config")}
                  fullWidth
                >
                  System Parameters
                </Button>
              </Stack>
            </Card>
          </Stack>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
