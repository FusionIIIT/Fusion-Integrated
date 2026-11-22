import { Alert, Badge, Card, Container, Stack, Table, Text } from "@mantine/core";
import { FaFileInvoiceDollar } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useMonthlyBills } from "../api/hooks";

export default function MyBillsPage() {
  const { data: bills, isLoading, error } = useMonthlyBills();

  if (error) {
    return (
      <Container size="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="md">
      <PageHeader title="My Monthly Bills" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          View your monthly mess charges, rebate deductions, and finalized totals.
        </Text>

        <Card withBorder padding="md">
          {isLoading ? (
            <Text c="dimmed">Loading bills...</Text>
          ) : !bills || bills.length === 0 ? (
            <Alert color="gray" icon={<FaFileInvoiceDollar />}>
              No bills published for your account yet.
            </Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Month</Table.Th>
                  <Table.Th>Served Days (₹)</Table.Th>
                  <Table.Th>Special Meals (₹)</Table.Th>
                  <Table.Th>Rebate Deduction (₹)</Table.Th>
                  <Table.Th>Total Due (₹)</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bills.map((b) => (
                  <Table.Tr key={b.id}>
                    <Table.Td fw={600}>{b.month}</Table.Td>
                    <Table.Td>₹{b.served_day_charges}</Table.Td>
                    <Table.Td>₹{b.special_meal_charges}</Table.Td>
                    <Table.Td c="green">-₹{b.rebate_deductions}</Table.Td>
                    <Table.Td fw={700}>₹{b.total}</Table.Td>
                    <Table.Td>
                      <StatusBadge status={b.state} />
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
