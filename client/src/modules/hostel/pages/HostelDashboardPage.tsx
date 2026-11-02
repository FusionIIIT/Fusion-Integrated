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
  Paper,
} from "@mantine/core";
import { Link } from "react-router-dom";
import {
  FaBuilding,
  FaBed,
  FaUserCheck,
  FaExclamationTriangle,
  FaCalendarAlt,
  FaBell,
  FaFileAlt,
  FaReceipt,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useNotifications,
  useNotices,
  useOperationalReport,
  useMarkNotificationRead,
} from "../api/hooks";

export default function HostelDashboardPage() {
  const { session, can } = useAuth();
  const { data: stats, error: statsError } = useOperationalReport("dashboard_summary");
  const { data: notices } = useNotices();
  const { data: notifications } = useNotifications();
  const markRead = useMarkNotificationRead();

  if (statsError) {
    return (
      <Container size="xl">
        <ErrorState error={statsError} />
      </Container>
    );
  }

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;
  const displayName = session?.user?.display_name || "User";
  const userRole = session?.active_role || session?.user?.kind || "Resident";

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Management Dashboard"
        subtitle={`Welcome, ${displayName} (${userRole})`}
        action={
          unreadCount > 0 ? (
            <Badge color="red" size="lg" variant="filled" leftSection={<FaBell />}>
              {unreadCount} Unread Notifications
            </Badge>
          ) : undefined
        }
      />

      {/* Top Metric Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="lg">
        <Card withBorder padding="lg" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Active Hostels</Text>
            <ThemeIcon color="blue" variant="light" size="lg" radius="md">
              <FaBuilding size={18} />
            </ThemeIcon>
          </Group>
          <Text fw={700} fz="xl" mt="xs">{stats?.total_hostels ?? "—"}</Text>
          <Text c="dimmed" size="xs" mt={4}>Institute-wide active residences</Text>
        </Card>

        <Card withBorder padding="lg" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Room Occupancy</Text>
            <ThemeIcon color="teal" variant="light" size="lg" radius="md">
              <FaBed size={18} />
            </ThemeIcon>
          </Group>
          <Text fw={700} fz="xl" mt="xs">
            {stats?.total_occupancy ?? 0} / {stats?.total_capacity ?? 0}
          </Text>
          <Text c="teal" size="xs" mt={4} fw={500}>
            {stats?.occupancy_rate ?? 0}% capacity utilized
          </Text>
        </Card>

        <Card withBorder padding="lg" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Pending Leaves</Text>
            <ThemeIcon color="orange" variant="light" size="lg" radius="md">
              <FaCalendarAlt size={18} />
            </ThemeIcon>
          </Group>
          <Text fw={700} fz="xl" mt="xs">{stats?.pending_leaves ?? 0}</Text>
          <Text c="dimmed" size="xs" mt={4}>Awaiting Caretaker review</Text>
        </Card>

        <Card withBorder padding="lg" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Active Complaints</Text>
            <ThemeIcon color="red" variant="light" size="lg" radius="md">
              <FaExclamationTriangle size={18} />
            </ThemeIcon>
          </Group>
          <Text fw={700} fz="xl" mt="xs">{stats?.active_complaints ?? 0}</Text>
          <Text c="dimmed" size="xs" mt={4}>Unresolved / Escalated</Text>
        </Card>
      </SimpleGrid>

      <Grid gutter="md">
        {/* Quick Links & Module Navigation */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder padding="lg" radius="md" h="100%">
            <Text fw={600} fz="md" mb="md">Quick Actions & Services</Text>

            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
              <Paper
                component={Link}
                to="/hostel/allotments"
                withBorder
                p="md"
                radius="md"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Group>
                  <ThemeIcon color="blue" size="md" radius="md"><FaBed /></ThemeIcon>
                  <Stack gap={2}>
                    <Text fw={500} size="sm">Room Allotments</Text>
                    <Text size="xs" c="dimmed">Apply, allot, and vacate</Text>
                  </Stack>
                </Group>
              </Paper>

              <Paper
                component={Link}
                to="/hostel/attendance"
                withBorder
                p="md"
                radius="md"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Group>
                  <ThemeIcon color="teal" size="md" radius="md"><FaUserCheck /></ThemeIcon>
                  <Stack gap={2}>
                    <Text fw={500} size="sm">Student Attendance</Text>
                    <Text size="xs" c="dimmed">Daily night roll-call roster</Text>
                  </Stack>
                </Group>
              </Paper>

              <Paper
                component={Link}
                to="/hostel/leaves"
                withBorder
                p="md"
                radius="md"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Group>
                  <ThemeIcon color="orange" size="md" radius="md"><FaCalendarAlt /></ThemeIcon>
                  <Stack gap={2}>
                    <Text fw={500} size="sm">Hostel Leaves</Text>
                    <Text size="xs" c="dimmed">Leave requests & approvals</Text>
                  </Stack>
                </Group>
              </Paper>

              <Paper
                component={Link}
                to="/hostel/complaints"
                withBorder
                p="md"
                radius="md"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Group>
                  <ThemeIcon color="red" size="md" radius="md"><FaExclamationTriangle /></ThemeIcon>
                  <Stack gap={2}>
                    <Text fw={500} size="sm">Complaints</Text>
                    <Text size="xs" c="dimmed">Electrical, plumbing & repairs</Text>
                  </Stack>
                </Group>
              </Paper>

              <Paper
                component={Link}
                to="/hostel/fines"
                withBorder
                p="md"
                radius="md"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Group>
                  <ThemeIcon color="yellow" size="md" radius="md"><FaReceipt /></ThemeIcon>
                  <Stack gap={2}>
                    <Text fw={500} size="sm">Disciplinary Fines</Text>
                    <Text size="xs" c="dimmed">Imposed fines & dues</Text>
                  </Stack>
                </Group>
              </Paper>

              <Paper
                component={Link}
                to="/hostel/reports"
                withBorder
                p="md"
                radius="md"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <Group>
                  <ThemeIcon color="indigo" size="md" radius="md"><FaFileAlt /></ThemeIcon>
                  <Stack gap={2}>
                    <Text fw={500} size="sm">Operational Reports</Text>
                    <Text size="xs" c="dimmed">Occupancy & supervisory stats</Text>
                  </Stack>
                </Group>
              </Paper>
            </SimpleGrid>

            {can("hostel.master.manage") && (
              <Group mt="lg" justify="flex-end">
                <Button component={Link} to="/hostel/masters" variant="light" size="xs">
                  Manage Hostel Masters & Staff Roles
                </Button>
              </Group>
            )}
          </Card>
        </Grid.Col>

        {/* Notices & Bulletins */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder padding="lg" radius="md" h="100%">
            <Group justify="space-between" mb="sm">
              <Text fw={600} fz="md">Recent Bulletins & Notices</Text>
              <Button component={Link} to="/hostel/notices" variant="subtle" size="xs">
                View All
              </Button>
            </Group>

            {notices && notices.length > 0 ? (
              <Stack gap="xs">
                {notices.slice(0, 4).map((notice) => (
                  <Card key={notice.id} withBorder padding="sm" radius="sm">
                    <Group justify="space-between" mb={4}>
                      <Badge size="xs" color={notice.category === "emergency" ? "red" : "blue"}>
                        {notice.category}
                      </Badge>
                      <Text size="xs" c="dimmed">
                        {new Date(notice.created_at).toLocaleDateString()}
                      </Text>
                    </Group>
                    <Text fw={600} size="sm" lineClamp={1}>{notice.title}</Text>
                    <Text size="xs" c="dimmed" lineClamp={2}>{notice.body}</Text>
                  </Card>
                ))}
              </Stack>
            ) : (
              <Text size="sm" c="dimmed" ta="center" py="xl">
                No active notices posted.
              </Text>
            )}
          </Card>
        </Grid.Col>
      </Grid>

      {/* Notifications list if any */}
      {notifications && notifications.length > 0 && (
        <Card withBorder padding="md" radius="md" mt="md">
          <Group justify="space-between" mb="xs">
            <Text fw={600} size="sm">Activity & System Notifications</Text>
            <Badge size="xs" variant="outline">{notifications.length} Total</Badge>
          </Group>
          <Stack gap="xs">
            {notifications.slice(0, 3).map((n) => (
              <Group key={n.id} justify="space-between" p="xs" style={{ background: n.is_read ? "transparent" : "var(--mantine-color-blue-0)" }}>
                <Stack gap={2}>
                  <Text fw={n.is_read ? 400 : 600} size="sm">{n.title}</Text>
                  <Text size="xs" c="dimmed">{n.message}</Text>
                </Stack>
                {!n.is_read && (
                  <Button size="xs" variant="subtle" onClick={() => markRead.mutate(n.id)}>
                    Mark Read
                  </Button>
                )}
              </Group>
            ))}
          </Stack>
        </Card>
      )}
    </Container>
  );
}
