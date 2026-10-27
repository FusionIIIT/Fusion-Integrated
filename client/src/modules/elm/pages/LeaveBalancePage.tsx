import { Card, Container, Table } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useLeaveBalances } from "../api/hooks";

export default function LeaveBalancePage() {
  const { data: balances, isPending, error } = useLeaveBalances();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balance & Entitlements"
        subtitle="Current year credit, consumed days, and available leave quota"
      />

      <Card padding="lg" shadow="xs" radius="md">
        <Table highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Category</Table.Th>
              <Table.Th>Year</Table.Th>
              <Table.Th>Credited</Table.Th>
              <Table.Th>Used</Table.Th>
              <Table.Th>Remaining</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isPending ? (
              <Table.Tr><Table.Td colSpan={5}>Loading balances...</Table.Td></Table.Tr>
            ) : !balances || balances.length === 0 ? (
              <Table.Tr><Table.Td colSpan={5}>No balance records available.</Table.Td></Table.Tr>
            ) : (
              balances.map((b, idx) => {
                const credited = parseFloat(b.credited) || 0;
                const used = parseFloat(b.used) || 0;
                const remaining = (credited - used).toFixed(1);
                return (
                  <Table.Tr key={idx}>
                    <Table.Td><strong>{b.leave_type__code}</strong></Table.Td>
                    <Table.Td>{b.year}</Table.Td>
                    <Table.Td>{b.credited}</Table.Td>
                    <Table.Td>{b.used}</Table.Td>
                    <Table.Td style={{ fontWeight: 600, color: Number(remaining) > 0 ? "teal" : "gray" }}>
                      {remaining}
                    </Table.Td>
                  </Table.Tr>
                );
              })
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
