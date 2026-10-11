import { useEffect, useState } from "react";
import {
  Card,
  SimpleGrid,
  Text,
  Title,
  Stack,
  Loader,
  Center,
  Badge,
  Group,
  Button,
  Table,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { fetchMyBalances, fetchMyApplications } from "../api";
import type { LeaveBalance, LeaveApplication } from "../types";

const LEAVE_NAMES: Record<string, string> = {
  CL: "Casual Leave",
  RH: "Restricted Holiday",
  SCL: "Special Casual Leave",
  EL: "Earned Leave",
  VL: "Vacation Leave",
  COL: "Commuted / Medical Leave",
};

export default function DashboardPage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchMyBalances(), fetchMyApplications()])
      .then(([b, a]) => {
        setBalances(b);
        setApplications(a);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Center h="50vh">
        <Loader />
      </Center>
    );
  }

  const recent = applications.slice(0, 5);

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Employee Leave Dashboard</Title>
          <Text c="dimmed">Overview of your leave entitlements and current requests</Text>
        </div>
        <Button component={Link} to="/elm/apply" color="blue">
          Apply For Leave
        </Button>
      </Group>

      <div>
        <Title order={4} mb="sm">
          Leave Balances (2026)
        </Title>
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
          {balances.map((b) => (
            <Card key={b.id} withBorder shadow="sm" radius="md" p="md">
              <Group justify="space-between" mb="xs">
                <Text fw={600} size="md">
                  {LEAVE_NAMES[b.leave_type] || b.leave_type}
                </Text>
                <Badge color="blue" variant="light">
                  {b.leave_type}
                </Badge>
              </Group>
              <Text size="xl" fw={700} c="blue">
                {b.available_balance} days available
              </Text>
              <Group mt="sm" gap="xs">
                <Text size="xs" c="dimmed">
                  Allocated: {b.allocated}
                </Text>
                <Text size="xs" c="dimmed">•</Text>
                <Text size="xs" c="dimmed">
                  Availed: {b.availed}
                </Text>
                <Text size="xs" c="dimmed">•</Text>
                <Text size="xs" c="dimmed">
                  Pending: {b.pending}
                </Text>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      </div>

      <Card withBorder shadow="sm" radius="md" p="md">
        <Group justify="space-between" mb="md">
          <Title order={4}>Recent Leave Applications</Title>
          <Button component={Link} to="/elm/history" variant="subtle" size="xs">
            View All
          </Button>
        </Group>

        {recent.length === 0 ? (
          <Text c="dimmed" size="sm">
            No recent leave applications.
          </Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Type</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Station Leave</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {recent.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td fw={500}>{app.leave_type}</Table.Td>
                  <Table.Td>
                    {app.start_date} to {app.end_date}
                  </Table.Td>
                  <Table.Td>{app.days_requested}</Table.Td>
                  <Table.Td>
                    {app.station_leave ? (
                      <Badge color="orange" size="xs">
                        Yes
                      </Badge>
                    ) : (
                      "No"
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Badge
                      color={
                        app.status === "APPROVED"
                          ? "green"
                          : app.status === "REJECTED" || app.status === "CANCELLED"
                          ? "red"
                          : "yellow"
                      }
                    >
                      {app.status}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
