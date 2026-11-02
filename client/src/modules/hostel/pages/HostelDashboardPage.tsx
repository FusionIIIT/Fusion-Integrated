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
  FaBed,
  FaBell,
  FaBuilding,
  FaCalendarAlt,
  FaCheckCircle,
  FaFileAlt,
  FaReceipt,
  FaWrench,
} from "react-icons/fa";
import { Link } from "react-router-dom";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDashboardStats, useNotices } from "../api/hooks";

export default function HostelDashboardPage() {
  const { data: stats, error } = useDashboardStats();
  const { data: notices } = useNotices({ is_active: true });
  
  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const occupancyRate =
    stats?.total_capacity && stats.total_capacity > 0
      ? Math.round(((stats.total_occupancy ?? 0) / stats.total_capacity) * 100)
      : 0;

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Management Overview"
        subtitle="Operational metrics, student accommodation, and quick actions"
      />

      {/* Student View Card if Student */}
      {!stats?.is_admin && stats?.my_allotment && (
        <Card withBorder shadow="sm" radius="md" mb="lg" p="lg" bg="var(--mantine-color-blue-0)">
          <Group justify="space-between" align="flex-start" wrap="wrap">
            <Stack gap="xs">
              <Group>
                <ThemeIcon size="lg" color="blue" radius="md">
                  <FaBed size={20} />
                </ThemeIcon>
                <div>
                  <Title order={3}>{stats.my_allotment.hostel_name}</Title>
                  <Text c="dimmed" size="sm">
                    Hostel Code: {stats.my_allotment.hostel_code} • Room {stats.my_allotment.room_number} (Bed {stats.my_allotment.bed_number})
                  </Text>
                </div>
              </Group>
              <Text size="sm">Allotted on: {stats.my_allotment.allotment_date}</Text>
            </Stack>
            <Badge size="lg" color="green" variant="filled">
              {stats.my_allotment.status.toUpperCase()} ALLOTMENT
            </Badge>
          </Group>

          <SimpleGrid cols={{ base: 1, sm: 3 }} mt="md">
            <Card withBorder p="sm" radius="sm">
              <Text size="xs" c="dimmed">Active Leaves</Text>
              <Text fw={700} size="xl">{stats.my_pending_leaves ?? 0}</Text>
              <Button component={Link} to="/hostel/leaves" variant="subtle" size="xs" mt="xs">
                Manage Leaves
              </Button>
            </Card>
            <Card withBorder p="sm" radius="sm">
              <Text size="xs" c="dimmed">Open Complaints</Text>
              <Text fw={700} size="xl">{stats.my_open_complaints ?? 0}</Text>
              <Button component={Link} to="/hostel/complaints" variant="subtle" size="xs" mt="xs">
                View Complaints
              </Button>
            </Card>
            <Card withBorder p="sm" radius="sm">
              <Text size="xs" c="dimmed">Pending Fines</Text>
              <Text fw={700} size="xl" c={stats.my_pending_fines ? "red" : "dimmed"}>
                {stats.my_pending_fines ?? 0}
              </Text>
              <Button component={Link} to="/hostel/fines" variant="subtle" size="xs" mt="xs">
                Pay Fines
              </Button>
            </Card>
          </SimpleGrid>
        </Card>
      )}

      {/* Key Metric KPI Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="lg">
        <Card withBorder shadow="xs" radius="md" p="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Total Hostels</Text>
            <ThemeIcon color="blue" variant="light" radius="md">
              <FaBuilding size={16} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">{stats?.hostels_count ?? 0}</Text>
          <Text size="xs" c="dimmed" mt={4}>
            {stats?.active_hostels_count ?? 0} active premises
          </Text>
        </Card>

        <Card withBorder shadow="xs" radius="md" p="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Occupancy</Text>
            <ThemeIcon color="teal" variant="light" radius="md">
              <FaBed size={16} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">
            {stats?.total_occupancy ?? 0} / {stats?.total_capacity ?? 0}
          </Text>
          <Progress value={occupancyRate} color="teal" size="sm" mt="xs" />
          <Text size="xs" c="dimmed" mt={4}>{occupancyRate}% utilization rate</Text>
        </Card>

        <Card withBorder shadow="xs" radius="md" p="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Open Maintenance</Text>
            <ThemeIcon color="orange" variant="light" radius="md">
              <FaWrench size={16} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">{stats?.open_complaints ?? 0}</Text>
          <Text size="xs" c="dimmed" mt={4}>
            {stats?.escalated_complaints ?? 0} escalated to warden
          </Text>
        </Card>

        <Card withBorder shadow="xs" radius="md" p="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Pending Requests</Text>
            <ThemeIcon color="grape" variant="light" radius="md">
              <FaCalendarAlt size={16} />
            </ThemeIcon>
          </Group>
          <Text fw={700} size="xl" mt="xs">
            {(stats?.pending_leaves ?? 0) + (stats?.pending_allotment_requests ?? 0)}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {stats?.pending_leaves ?? 0} leaves, {stats?.pending_guest_bookings ?? 0} guest bookings
          </Text>
        </Card>
      </SimpleGrid>

      <Grid gutter="lg">
        {/* Active Notices & Broadcasts */}
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card withBorder shadow="xs" radius="md" p="md" mb="lg">
            <Group justify="space-between" mb="md">
              <Group gap="xs">
                <FaBell color="#228be6" />
                <Title order={4}>Hostel Notice Board</Title>
              </Group>
              <Button component={Link} to="/hostel/notices" variant="light" size="xs">
                View All Notices
              </Button>
            </Group>

            <Stack gap="sm">
              {notices?.results && notices.results.length > 0 ? (
                notices.results.slice(0, 4).map((notice) => (
                  <Card key={notice.id} withBorder p="sm" radius="sm">
                    <Group justify="space-between">
                      <Text fw={600} size="sm">{notice.title}</Text>
                      <Badge size="xs" variant="outline">{notice.target_audience}</Badge>
                    </Group>
                    <Text size="xs" c="dimmed" mt={4} lineClamp={2}>
                      {notice.content}
                    </Text>
                    <Text size="xs" c="gray.6" mt={4}>
                      Posted on {new Date(notice.created_at).toLocaleDateString()}
                    </Text>
                  </Card>
                ))
              ) : (
                <Text c="dimmed" size="sm">No circulars posted at this time.</Text>
              )}
            </Stack>
          </Card>
        </Grid.Col>

        {/* Quick Operations Menu */}
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card withBorder shadow="xs" radius="md" p="md" mb="lg">
            <Title order={4} mb="md">Quick Actions</Title>
            <Stack gap="xs">
              <Button component={Link} to="/hostel/allotments" variant="light" leftSection={<FaBed size={14} />} fullWidth justify="flex-start">
                Allotments & Requests
              </Button>
              <Button component={Link} to="/hostel/attendance" variant="light" leftSection={<FaCheckCircle size={14} />} fullWidth justify="flex-start">
                Daily Night Attendance
              </Button>
              <Button component={Link} to="/hostel/complaints" variant="light" leftSection={<FaWrench size={14} />} fullWidth justify="flex-start">
                Report Issue / Complaint
              </Button>
              <Button component={Link} to="/hostel/leaves" variant="light" leftSection={<FaCalendarAlt size={14} />} fullWidth justify="flex-start">
                Apply for Leave
              </Button>
              <Button component={Link} to="/hostel/guest-rooms" variant="light" leftSection={<FaBed size={14} />} fullWidth justify="flex-start">
                Book Guest Room
              </Button>
              <Button component={Link} to="/hostel/fines" variant="light" leftSection={<FaReceipt size={14} />} fullWidth justify="flex-start">
                Dues & Fine Records
              </Button>
              <Button component={Link} to="/hostel/reports" variant="light" leftSection={<FaFileAlt size={14} />} fullWidth justify="flex-start">
                Operational Reports
              </Button>
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
