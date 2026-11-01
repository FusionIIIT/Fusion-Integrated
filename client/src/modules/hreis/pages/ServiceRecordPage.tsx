import {
  Badge,
  Card,
  Container,
  Grid,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Timeline,
  Title,
} from "@mantine/core";
import { FaBriefcase, FaUserTie } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useMyServiceRecord } from "../api/hooks";

export default function ServiceRecordPage() {
  const { data: record, error } = useMyServiceRecord();
  const { session } = useAuth();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const balances = record?.leave_balances ?? {};
  const history = record?.service_history ?? [];

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="My Employee Service Record"
        subtitle="Comprehensive electronic service book, entitlement quotas, and career history (BR-HR-003, BR-HR-004)"
      />

      <Grid gutter="lg">
        {/* Profile and Designation Card */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder padding="lg" radius="md" mb="lg">
            <Group mb="md">
              <ThemeIcon size={44} radius="xl" color="blue" variant="light">
                <FaUserTie size={24} />
              </ThemeIcon>
              <div>
                <Title order={4}>{session?.user.display_name ?? "Employee"}</Title>
                <Text size="xs" c="dimmed">
                  User ID: {record?.user_id}
                </Text>
              </div>
            </Group>

            <Stack gap="sm">
              <Paper withBorder p="xs" radius="sm">
                <Text size="xs" c="dimmed">Permanent PF / Employee ID</Text>
                <Text size="sm" fw={600}>{record?.employee_id || "PF-Auto"}</Text>
              </Paper>
              <Paper withBorder p="xs" radius="sm">
                <Text size="xs" c="dimmed">Department</Text>
                <Text size="sm" fw={600}>{record?.department || "General"}</Text>
              </Paper>
              <Paper withBorder p="xs" radius="sm">
                <Text size="xs" c="dimmed">Designation</Text>
                <Text size="sm" fw={600}>{record?.designation || "Not Assigned"}</Text>
              </Paper>
              <Paper withBorder p="xs" radius="sm">
                <Text size="xs" c="dimmed">Category</Text>
                <Badge color={record?.category === "faculty" ? "blue" : "teal"} variant="light" mt={2}>
                  {record?.category?.toUpperCase()}
                </Badge>
              </Paper>
              <Paper withBorder p="xs" radius="sm">
                <Text size="xs" c="dimmed">Date of Joining / Appointment</Text>
                <Text size="sm">{record?.appointment_date || "—"}</Text>
              </Paper>
              <Paper withBorder p="xs" radius="sm">
                <Text size="xs" c="dimmed">Retirement Status</Text>
                <StatusBadge status={record?.retirement_status || "active"} />
              </Paper>
            </Stack>
          </Card>
        </Grid.Col>

        {/* Leave Balances and History */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder padding="lg" radius="md" mb="lg">
            <Title order={4} mb="md">
              Current Leave Quotas & Balances
            </Title>
            <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
              {Object.entries(balances).map(([type, days]) => (
                <Paper key={type} withBorder p="sm" radius="sm">
                  <Text size="xs" c="dimmed" tt="capitalize">
                    {type} Leave
                  </Text>
                  <Text size="lg" fw={700} c="blue">
                    {days} <Text span size="xs" fw={400} c="dimmed">days</Text>
                  </Text>
                </Paper>
              ))}
            </SimpleGrid>
          </Card>

          {/* Service History Timeline */}
          <Card withBorder padding="lg" radius="md">
            <Title order={4} mb="md">
              Service Timeline & Roles
            </Title>
            {history.length === 0 ? (
              <Timeline active={0} bulletSize={24} lineWidth={2}>
                <Timeline.Item
                  bullet={<FaBriefcase size={12} />}
                  title={record?.designation || "Initial Appointment"}
                >
                  <Text c="dimmed" size="xs">
                    Department of {record?.department || "General"}
                  </Text>
                  <Text size="xs" mt={4}>
                    Joined on {record?.appointment_date || "Record Creation Date"}
                  </Text>
                </Timeline.Item>
              </Timeline>
            ) : (
              <Timeline active={history.length - 1} bulletSize={24} lineWidth={2}>
                {history.map((h, idx) => (
                  <Timeline.Item
                    key={idx}
                    bullet={<FaBriefcase size={12} />}
                    title={h.designation}
                  >
                    <Text c="dimmed" size="xs">
                      {h.department}
                    </Text>
                    <Text size="xs" mt={4}>
                      {h.start_date} {h.end_date ? `to ${h.end_date}` : "— Present"}
                    </Text>
                  </Timeline.Item>
                ))}
              </Timeline>
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
