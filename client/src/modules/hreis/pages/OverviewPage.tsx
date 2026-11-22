import {
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCalendarAlt,
  FaCheckCircle,
  FaCoins,
  FaFileAlt,
  FaIdCard,
  FaPlaneDeparture,
} from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDashboardStats,
  useMarkNotificationRead,
  useMyServiceRecord,
  useNotifications,
} from "../api/hooks";

export default function OverviewPage() {
  const navigate = useNavigate();
  const { session } = useAuth();
  const { data: stats, error: statsError } = useDashboardStats();
  const { data: record, isPending: recordLoading } = useMyServiceRecord();
  const { data: notifs } = useNotifications();
  const markRead = useMarkNotificationRead();

  if (statsError) {
    return (
      <Container size="xl">
        <ErrorState error={statsError} />
      </Container>
    );
  }

  const unreadNotifs = notifs?.filter((n) => !n.is_read) ?? [];

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Human Resources Dashboard"
        subtitle={`Welcome back, ${session?.user.display_name ?? "Employee"}`}
      />

      {/* Quick Status and Balance Metrics */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg" mb="xl">
        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Casual Leave Balance
            </Text>
            <ThemeIcon color="blue" variant="light" size="lg" radius="md">
              <FaCalendarAlt size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt={12}>
            <Text fw={700} size="xl">
              {stats?.leave_balances?.casual ?? record?.leave_balances?.casual ?? "—"} days
            </Text>
          </Group>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Medical Leave Balance
            </Text>
            <ThemeIcon color="teal" variant="light" size="lg" radius="md">
              <FaCheckCircle size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt={12}>
            <Text fw={700} size="xl">
              {stats?.leave_balances?.medical ?? record?.leave_balances?.medical ?? "—"} days
            </Text>
          </Group>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              CPDA Available Balance
            </Text>
            <ThemeIcon color="grape" variant="light" size="lg" radius="md">
              <FaCoins size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt={12}>
            <Text fw={700} size="xl">
              ₹{Number(stats?.cpda_balance ?? record?.cpda_balance ?? 0).toLocaleString("en-IN")}
            </Text>
          </Group>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              LTC Eligible Block
            </Text>
            <ThemeIcon color="orange" variant="light" size="lg" radius="md">
              <FaPlaneDeparture size={18} />
            </ThemeIcon>
          </Group>
          <Group align="flex-end" gap="xs" mt={12}>
            <Text fw={700} size="xl">
              {stats?.ltc_eligible_block ?? record?.ltc_eligible_block ?? "2026-2029"}
            </Text>
          </Group>
        </Paper>
      </SimpleGrid>

      {/* Main Grid: Quick Actions and Recent Activity */}
      <Grid gutter="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder padding="lg" radius="md" mb="lg">
            <Title order={4} mb="md">
              Quick Actions
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <Button
                variant="light"
                color="blue"
                leftSection={<FaCalendarAlt />}
                onClick={() => navigate("/hr/leaves")}
              >
                Apply for Leave
              </Button>
              <Button
                variant="light"
                color="orange"
                leftSection={<FaPlaneDeparture />}
                onClick={() => navigate("/hr/ltc")}
              >
                Submit LTC Claim
              </Button>
              <Button
                variant="light"
                color="grape"
                leftSection={<FaCoins />}
                onClick={() => navigate("/hr/cpda")}
              >
                Claim CPDA Allowance
              </Button>
              <Button
                variant="light"
                color="teal"
                leftSection={<FaFileAlt />}
                onClick={() => navigate("/hr/appraisals")}
              >
                Annual Appraisal Form
              </Button>
              <Button
                variant="light"
                color="indigo"
                leftSection={<FaIdCard />}
                onClick={() => navigate("/hr/service-record")}
              >
                View My Service Record
              </Button>
            </SimpleGrid>
          </Card>

          {/* Service Record Overview */}
          <Card withBorder padding="lg" radius="md">
            <Title order={4} mb="md">
              Employment Profile
            </Title>
            {recordLoading ? (
              <Text c="dimmed">Loading service record details...</Text>
            ) : (
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Designation:</Text>
                  <Text size="sm" fw={600}>{record?.designation || "Not Assigned"}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Department:</Text>
                  <Text size="sm" fw={600}>{record?.department || "General"}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">PF / Employee ID:</Text>
                  <Text size="sm" fw={600}>{record?.employee_id || "PF-Auto"}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Employment Category:</Text>
                  <Badge color={record?.category === "faculty" ? "blue" : "cyan"} variant="light">
                    {record?.category?.toUpperCase()}
                  </Badge>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Appointment Date:</Text>
                  <Text size="sm">{record?.appointment_date || "—"}</Text>
                </Group>
              </Stack>
            )}
          </Card>
        </Grid.Col>

        {/* Notifications and Reminders */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder padding="lg" radius="md">
            <Group justify="space-between" mb="md">
              <Title order={4}>Notifications & Reminders</Title>
              {unreadNotifs.length > 0 && (
                <Badge color="red" variant="filled">
                  {unreadNotifs.length} new
                </Badge>
              )}
            </Group>

            {unreadNotifs.length === 0 ? (
              <Text c="dimmed" size="sm" py="md">
                No new notifications or pending reminders.
              </Text>
            ) : (
              <Stack gap="sm">
                {unreadNotifs.slice(0, 5).map((n) => (
                  <Paper key={n.id} withBorder p="sm" radius="sm">
                    <Group justify="space-between" align="flex-start" wrap="nowrap">
                      <div>
                        <Text size="sm" fw={600}>
                          {n.title}
                        </Text>
                        <Text size="xs" c="dimmed" mt={2}>
                          {n.message}
                        </Text>
                        <Text size="xs" c="dimmed" mt={4}>
                          {new Date(n.created_at).toLocaleDateString()}
                        </Text>
                      </div>
                      <Button
                        size="xs"
                        variant="subtle"
                        onClick={() => {
                          markRead.mutate(n.id, {
                            onSuccess: () => {
                              notifications.show({
                                title: "Marked as read",
                                message: "Notification dismissed",
                                color: "teal",
                              });
                            },
                          });
                        }}
                      >
                        Dismiss
                      </Button>
                    </Group>
                  </Paper>
                ))}
              </Stack>
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
