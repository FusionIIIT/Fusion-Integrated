import {
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { Link } from "react-router-dom";
import {
  FaCalendarAlt,
  FaCheckCircle,
  FaClock,
  FaPlus,
} from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLeaveBalances, useLeaveRequests } from "../api/hooks";

export default function LeaveOverviewPage() {
  const { data: balances, isLoading: loadingBalances, error: errBalances } = useLeaveBalances();
  const { data: requests, isLoading: loadingRequests, error: errRequests } = useLeaveRequests();

  if (errBalances || errRequests) {
    return (
      <Container size="xl">
        <ErrorState error={errBalances || errRequests} />
      </Container>
    );
  }

  const recentRequests = (requests || []).slice(0, 5);
  const pendingApprovals = (requests || []).filter(
    (r) =>
      r.status === "unit_head_queue" ||
      r.status === "establishment" ||
      r.status === "final_decision"
  ).length;

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Leave Management System (ELM)"
        description="View annual quotas, manage leave applications, and track approval workflows."
        action={
          <Group>
            <Button
              component={Link}
              to="/leave/apply"
              leftSection={<FaPlus />}
              variant="filled"
            >
              Apply Leave
            </Button>
          </Group>
        }
      />

      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="lg">
        <Card withBorder padding="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              Casual Leave (CL)
            </Text>
            <FaCalendarAlt />
          </Group>
          <Text fw={700} fz="xl" mt="sm">
            {balances?.find((b) => b.category === "CL")?.available ?? 8} Days
          </Text>
          <Text fz="xs" c="dimmed">
            Available for immediate absence
          </Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              Earned Leave (EL)
            </Text>
            <FaCheckCircle />
          </Group>
          <Text fw={700} fz="xl" mt="sm">
            {balances?.find((b) => b.category === "EL")?.available ?? 30} Days
          </Text>
          <Text fz="xs" c="dimmed">
            Accumulated credited quota
          </Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              Restricted Holiday (RH)
            </Text>
            <FaCalendarAlt />
          </Group>
          <Text fw={700} fz="xl" mt="sm">
            {balances?.find((b) => b.category === "RH")?.available ?? 2} Days
          </Text>
          <Text fz="xs" c="dimmed">
            Calendar year entitlement
          </Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              In-Flight Applications
            </Text>
            <FaClock />
          </Group>
          <Text fw={700} fz="xl" mt="sm">
            {pendingApprovals}
          </Text>
          <Text fz="xs" c="dimmed">
            Requests currently under review
          </Text>
        </Card>
      </SimpleGrid>

      <Card withBorder radius="md" p="md" mb="lg">
        <Group justify="space-between" mb="md">
          <Title order={4}>Recent Leave Applications</Title>
          <Button component={Link} to="/leave/my-requests" variant="subtle" size="xs">
            View All Requests
          </Button>
        </Group>

        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Category</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Duration</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Submitted</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {recentRequests.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <Text ta="center" c="dimmed" py="sm">
                    No recent leave requests found.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              recentRequests.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>
                    <Badge variant="light">{r.category}</Badge>
                  </Table.Td>
                  <Table.Td>
                    {r.start_date} to {r.end_date}
                  </Table.Td>
                  <Table.Td>{r.days_count} day(s)</Table.Td>
                  <Table.Td>
                    <StatusBadge status={r.status} />
                  </Table.Td>
                  <Table.Td>
                    {new Date(r.created_at).toLocaleDateString()}
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
