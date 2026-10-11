import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useLeaveApplications,
  useLeaveBalances,
  useWithdrawLeaveApplication,
} from "../api/hooks";
import type { LeaveApplicationStatus } from "../api/types";

const STATUS_COLOR: Record<LeaveApplicationStatus, string> = {
  pending: "yellow",
  recommended: "blue",
  approved: "green",
  rejected: "red",
  withdrawn: "gray",
  cancelled: "gray",
};

export default function LeaveDashboardPage() {
  const balances = useLeaveBalances();
  const applications = useLeaveApplications();
  const withdraw = useWithdrawLeaveApplication();

  if (balances.error) {
    return (
      <Container size="lg">
        <ErrorState error={balances.error} />
      </Container>
    );
  }
  if (applications.error) {
    return (
      <Container size="lg">
        <ErrorState error={applications.error} />
      </Container>
    );
  }

  const balanceList = balances.data?.results ?? [];
  const appList = applications.data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="Leave Dashboard"
        subtitle="Your current leave balances and submitted applications"
      />
      <Stack gap="lg">
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
          {balanceList.map((b) => (
            <Card key={b.id} withBorder padding="md">
              <Group justify="space-between" mb="xs">
                <Text fw={600}>{b.leave_type.name}</Text>
                <Badge variant="light">{b.leave_type.code}</Badge>
              </Group>
              <Text size="xl" fw={700}>
                {b.remaining} days remaining
              </Text>
              <Text size="xs" c="dimmed" mt="xs">
                Allocated: {b.allocated} | Used: {b.used} | Pending: {b.pending}
              </Text>
            </Card>
          ))}
        </SimpleGrid>

        <Card withBorder padding="lg">
          <Text fw={600} mb="md">
            My Leave Applications
          </Text>
          {appList.length === 0 ? (
            <Text size="sm" c="dimmed">
              No leave applications found.
            </Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {appList.map((app) => (
                  <Table.Tr key={app.id}>
                    <Table.Td>{app.leave_type.name}</Table.Td>
                    <Table.Td>
                      {app.start_date} to {app.end_date}
                    </Table.Td>
                    <Table.Td>{app.total_days}</Table.Td>
                    <Table.Td>
                      <Badge color={STATUS_COLOR[app.status]} variant="light">
                        {app.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {app.status === "pending" && (
                        <Button
                          size="xs"
                          color="red"
                          variant="subtle"
                          loading={withdraw.isPending}
                          onClick={() => withdraw.mutate(app.id)}
                        >
                          Withdraw
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
