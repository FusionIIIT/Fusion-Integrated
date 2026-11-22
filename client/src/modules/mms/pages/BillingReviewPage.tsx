import { Alert, Button, Card, Container, Group, Stack, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useFinalizeBill,
  useGenerateMonthlyBills,
  useMonthlyBills,
  usePublishBill,
} from "../api/hooks";

export default function BillingReviewPage() {
  const { data: bills, isLoading, error } = useMonthlyBills();
  const generate = useGenerateMonthlyBills();
  const finalize = useFinalizeBill();
  const publish = usePublishBill();

  const handleGenerate = () => {
    generate.mutate(undefined, {
      onSuccess: (res) => notifications.show({ color: "green", title: "Generation Succeeded", message: `Generated ${res.generated_count} bills.` }),
      onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
    });
  };

  const handleFinalize = (id: number) => {
    finalize.mutate(id, {
      onSuccess: () => notifications.show({ color: "green", title: "Finalized", message: `Bill #${id} finalized.` }),
      onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
    });
  };

  const handlePublish = (id: number) => {
    publish.mutate(id, {
      onSuccess: () => notifications.show({ color: "green", title: "Published", message: `Bill #${id} published to student.` }),
      onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
    });
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="Monthly Billing Review" />
      <Stack gap="lg">
        <Group justify="space-between">
          <Text size="sm" c="dimmed">Generate, inspect, finalize, and publish monthly student mess bills.</Text>
          <Button onClick={handleGenerate} loading={generate.isPending} color="blue">Generate Monthly Bills</Button>
        </Group>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">All Student Bills ({bills?.length ?? 0})</Text>
          {isLoading ? (
            <Text c="dimmed">Loading...</Text>
          ) : !bills || bills.length === 0 ? (
            <Alert color="gray">No bills generated yet.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Student</Table.Th>
                  <Table.Th>Month</Table.Th>
                  <Table.Th>Served Days (₹)</Table.Th>
                  <Table.Th>Special (₹)</Table.Th>
                  <Table.Th>Rebates (₹)</Table.Th>
                  <Table.Th>Total (₹)</Table.Th>
                  <Table.Th>State</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bills.map((b) => (
                  <Table.Tr key={b.id}>
                    <Table.Td>#{b.id}</Table.Td>
                    <Table.Td>{b.student_user_id || b.user_id}</Table.Td>
                    <Table.Td>{b.month}</Table.Td>
                    <Table.Td>₹{b.served_day_charges}</Table.Td>
                    <Table.Td>₹{b.special_meal_charges}</Table.Td>
                    <Table.Td c="green">-₹{b.rebate_deductions}</Table.Td>
                    <Table.Td fw={700}>₹{b.total}</Table.Td>
                    <Table.Td><StatusBadge status={b.state} /></Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {b.state === "generated" && (
                          <Button size="xs" color="indigo" onClick={() => handleFinalize(b.id)} loading={finalize.isPending}>Finalize</Button>
                        )}
                        {b.state === "finalized" && (
                          <Button size="xs" color="green" onClick={() => handlePublish(b.id)} loading={publish.isPending}>Publish</Button>
                        )}
                        {b.state === "published" && (
                          <Text size="xs" c="dimmed">Published</Text>
                        )}
                      </Group>
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
