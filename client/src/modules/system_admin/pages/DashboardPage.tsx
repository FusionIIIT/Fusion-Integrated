import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  FaArchive,
  FaCheckCircle,
  FaExclamationTriangle,
  FaFileImport,
  FaPlus,
  FaShieldAlt,
  FaUserGraduate,
  FaUsers,
  FaUserTie,
} from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDashboardMetrics } from "../api/hooks";
import { BulkUserModal } from "../components/BulkUserModal";
import { CreateUserModal } from "../components/CreateUserModal";

export default function DashboardPage() {
  const { data: metrics, isPending, error } = useDashboardMetrics();
  const [creatingUser, setCreatingUser] = useState(false);
  const [bulkImporting, setBulkImporting] = useState(false);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const users = metrics?.users ?? {
    total: 0,
    active: 0,
    deactivated: 0,
    archived: 0,
    students: 0,
    faculty: 0,
    staff: 0,
  };

  const archival = metrics?.archival ?? {
    reversible: 0,
    permanent: 0,
    pending_purge: 0,
  };

  const security = metrics?.security ?? {
    failed_logins_24h: 0,
    alerts: 0,
  };

  return (
    <Container size="xl">
      <PageHeader
        title="System Administration"
        subtitle="Institute identity directory overview, delegation controls, and health telemetry"
        action={
          <Group gap="xs">
            <Button
              variant="default"
              leftSection={<FaFileImport size={12} />}
              onClick={() => setBulkImporting(true)}
            >
              Bulk Import
            </Button>
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setCreatingUser(true)}
            >
              Create User
            </Button>
          </Group>
        }
      />

      {/* KPI Cards Row */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="lg">
        <Card padding="md" withBorder radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Active Users
            </Text>
            <ThemeIcon color="teal" variant="light" size="sm">
              <FaUsers size={12} />
            </ThemeIcon>
          </Group>
          <Title order={2} mt="xs">
            {isPending ? "—" : users.active}
          </Title>
          <Text size="xs" c="dimmed" mt={4}>
            Out of {users.total} total accounts
          </Text>
        </Card>

        <Card padding="md" withBorder radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Deactivated
            </Text>
            <ThemeIcon color="orange" variant="light" size="sm">
              <FaExclamationTriangle size={12} />
            </ThemeIcon>
          </Group>
          <Title order={2} mt="xs">
            {isPending ? "—" : users.deactivated}
          </Title>
          <Text size="xs" c="dimmed" mt={4}>
            Disabled credentials / departures
          </Text>
        </Card>

        <Card padding="md" withBorder radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Archived Window Open
            </Text>
            <ThemeIcon color="yellow" variant="light" size="sm">
              <FaArchive size={12} />
            </ThemeIcon>
          </Group>
          <Title order={2} mt="xs">
            {isPending ? "—" : archival.reversible}
          </Title>
          <Text size="xs" c="dimmed" mt={4}>
            {archival.pending_purge} pending IT Head purge
          </Text>
        </Card>

        <Card padding="md" withBorder radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Security Alerts
            </Text>
            <ThemeIcon
              color={security.alerts > 0 ? "red" : "green"}
              variant="light"
              size="sm"
            >
              <FaShieldAlt size={12} />
            </ThemeIcon>
          </Group>
          <Title order={2} mt="xs">
            {isPending ? "—" : security.alerts}
          </Title>
          <Text size="xs" c="dimmed" mt={4}>
            {security.failed_logins_24h} failed login attempts in 24h
          </Text>
        </Card>
      </SimpleGrid>

      {/* Breakdown Section */}
      <Grid mb="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card padding="lg" withBorder radius="md" h="100%">
            <Title order={4} mb="xs">
              User Population Breakdown
            </Title>
            <Text size="xs" c="dimmed" mb="md">
              Demographic breakdown across students, faculty, and administrative staff
            </Text>

            <Stack gap="md">
              <div>
                <Group justify="space-between" mb={4}>
                  <Group gap="xs">
                    <ThemeIcon color="blue" size="xs" variant="light">
                      <FaUserGraduate size={10} />
                    </ThemeIcon>
                    <Text size="sm">Students</Text>
                  </Group>
                  <Text size="sm" fw={600}>
                    {users.students} (
                    {users.total
                      ? Math.round((users.students / users.total) * 100)
                      : 0}
                    %)
                  </Text>
                </Group>
                <Progress
                  value={
                    users.total ? (users.students / users.total) * 100 : 0
                  }
                  color="blue"
                  size="sm"
                />
              </div>

              <div>
                <Group justify="space-between" mb={4}>
                  <Group gap="xs">
                    <ThemeIcon color="violet" size="xs" variant="light">
                      <FaUserTie size={10} />
                    </ThemeIcon>
                    <Text size="sm">Faculty</Text>
                  </Group>
                  <Text size="sm" fw={600}>
                    {users.faculty} (
                    {users.total
                      ? Math.round((users.faculty / users.total) * 100)
                      : 0}
                    %)
                  </Text>
                </Group>
                <Progress
                  value={
                    users.total ? (users.faculty / users.total) * 100 : 0
                  }
                  color="violet"
                  size="sm"
                />
              </div>

              <div>
                <Group justify="space-between" mb={4}>
                  <Group gap="xs">
                    <ThemeIcon color="teal" size="xs" variant="light">
                      <FaUsers size={10} />
                    </ThemeIcon>
                    <Text size="sm">Staff & Administration</Text>
                  </Group>
                  <Text size="sm" fw={600}>
                    {users.staff} (
                    {users.total ? Math.round((users.staff / users.total) * 100) : 0}
                    %)
                  </Text>
                </Group>
                <Progress
                  value={users.total ? (users.staff / users.total) * 100 : 0}
                  color="teal"
                  size="sm"
                />
              </div>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card padding="lg" withBorder radius="md" h="100%">
            <Title order={4} mb="xs">
              System Health & Policies
            </Title>
            <Text size="xs" c="dimmed" mb="md">
              Operational parameters and scheduled sweep status
            </Text>

            <Stack gap="sm">
              <Group justify="space-between">
                <Text size="sm">Scheduled Sweeps:</Text>
                <Badge color="green" variant="light" size="sm">
                  Active (Hourly)
                </Badge>
              </Group>
              <Group justify="space-between">
                <Text size="sm">Dual-Auth Governance:</Text>
                <Badge color="blue" variant="light" size="sm">
                  Enforced (CW-SA-01)
                </Badge>
              </Group>
              <Group justify="space-between">
                <Text size="sm">Self-Modification Guard:</Text>
                <Badge color="blue" variant="light" size="sm">
                  Active (BR-SA-028)
                </Badge>
              </Group>
              <Group justify="space-between">
                <Text size="sm">Bulk Operations Cap:</Text>
                <Text size="sm" fw={600}>
                  1,000 records
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="sm">Archival Reversible Window:</Text>
                <Text size="sm" fw={600}>
                  180 Days
                </Text>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>

      <CreateUserModal
        opened={creatingUser}
        onClose={() => setCreatingUser(false)}
      />

      <BulkUserModal
        opened={bulkImporting}
        onClose={() => setBulkImporting(false)}
      />
    </Container>
  );
}
