import {
  Button,
  Card,
  Container,
  Group,
  Paper,
  SimpleGrid,
  Table,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLeaveBalances, useMyApplications, useWithdrawLeave } from "../api/hooks";

export default function MyLeavesPage() {
  const navigate = useNavigate();
  const balancesQuery = useLeaveBalances();
  const applicationsQuery = useMyApplications();
  const withdrawMutation = useWithdrawLeave();

  if (balancesQuery.error) {
    return (
      <Container size="lg">
        <ErrorState error={balancesQuery.error} />
      </Container>
    );
  }

  const handleWithdraw = async (id: number) => {
    if (!window.confirm("Are you sure you want to withdraw this pending leave request?")) {
      return;
    }
    try {
      await withdrawMutation.mutateAsync({
        id,
        payload: { remarks: "Withdrawn by employee" },
      });
      notifications.show({
        color: "green",
        title: "Withdrawn",
        message: "Leave application has been withdrawn.",
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Action Failed",
        message: errorMessage(err),
      });
    }
  };

  const applications = applicationsQuery.data ?? [];
  const balances = balancesQuery.data ?? [];

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <PageHeader
          title="My Leaves"
          subtitle="View your active leave entitlements, current balances, and submitted applications."
        />
        <Button onClick={() => navigate("/elm/apply")}>+ Apply for Leave</Button>
      </Group>

      {/* Balances Grid */}
      <Text fw={600} size="md" mb="xs">
        Current Year Entitlements & Balances
      </Text>
      <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} spacing="md" mb="xl">
        {balances.map((b) => (
          <Card key={b.id} withBorder p="sm" radius="md">
            <Text size="xs" c="dimmed" fw={600}>
              {b.category.code}
            </Text>
            <Text size="xl" fw={700} c="blue">
              {b.balance}
            </Text>
            <Text size="xs" c="dimmed">
              Quota: {b.credited} | Used: {b.consumed}
            </Text>
          </Card>
        ))}
      </SimpleGrid>

      {/* Applications Table */}
      <Text fw={600} size="md" mb="xs">
        Application History
      </Text>
      <Paper withBorder radius="md">
        {applications.length === 0 ? (
          <Text p="xl" ta="center" c="dimmed">
            No leave applications found. Click "Apply for Leave" above to create one.
          </Text>
        ) : (
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Station Leave</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Submitted On</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {applications.map((app) => {
                const canWithdraw = [
                  "pending_substitute",
                  "submitted",
                  "pending_sanction",
                ].includes(app.status);

                return (
                  <Table.Tr key={app.id}>
                    <Table.Td>#{app.id}</Table.Td>
                    <Table.Td fw={500}>
                      {app.category_name} ({app.category_code})
                    </Table.Td>
                    <Table.Td>
                      {app.start_date} to {app.end_date}
                      {app.half_day !== "none" && (
                        <Text size="xs" c="dimmed">
                          ({app.half_day.replace("_", " ")})
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>{app.days_count}</Table.Td>
                    <Table.Td>{app.station_leave ? "Yes" : "No"}</Table.Td>
                    <Table.Td>
                      <StatusBadge status={app.status} />
                    </Table.Td>
                    <Table.Td>
                      {new Date(app.created_at).toLocaleDateString()}
                    </Table.Td>
                    <Table.Td>
                      {canWithdraw && (
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          loading={withdrawMutation.isPending}
                          onClick={() => handleWithdraw(app.id)}
                        >
                          Withdraw
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Container>
  );
}
