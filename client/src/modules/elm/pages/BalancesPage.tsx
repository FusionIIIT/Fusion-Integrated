import { Badge, Card, Container, Group, SimpleGrid, Table, Text, Title } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useLeaveBalances } from "../api/hooks";

export default function BalancesPage() {
  const { data: balances, isPending, error } = useLeaveBalances();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances"
        subtitle="Annual leave accounts, entitlements, and carry-forward allocations (BR-EL-002–009)"
      />

      {isPending ? (
        <Text c="dimmed">Loading balances...</Text>
      ) : (
        <>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} mb="lg">
            {(balances ?? []).map((b) => (
              <Card key={b.id} withBorder shadow="sm" radius="md" padding="md">
                <Group justify="space-between" mb="xs">
                  <Text fw={700} size="lg">{b.category}</Text>
                  <Badge color="blue" variant="light">{b.year}</Badge>
                </Group>
                <Text size="xl" fw={800} c="blue.7">
                  {b.balance} <Text span size="sm" fw={400} c="dimmed">days remaining</Text>
                </Text>
                <Group mt="md" justify="space-between">
                  <Text size="xs" c="dimmed">Entitled: {b.entitlement}d</Text>
                  <Text size="xs" c="dimmed">Used: {b.used}d</Text>
                  <Text size="xs" c="dimmed">Carried: {b.carried_forward}d</Text>
                </Group>
              </Card>
            ))}
          </SimpleGrid>

          <Card withBorder radius="md">
            <Title order={4} mb="md">Detailed Leave Ledger</Title>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Year</Table.Th>
                  <Table.Th>Entitlement</Table.Th>
                  <Table.Th>Carried Forward</Table.Th>
                  <Table.Th>Used</Table.Th>
                  <Table.Th>Available Balance</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(balances ?? []).map((b) => (
                  <Table.Tr key={b.id}>
                    <Table.Td fw={600}>{b.category}</Table.Td>
                    <Table.Td>{b.year}</Table.Td>
                    <Table.Td>{b.entitlement} days</Table.Td>
                    <Table.Td>{b.carried_forward} days</Table.Td>
                    <Table.Td>{b.used} days</Table.Td>
                    <Table.Td fw={700} c="blue.6">{b.balance} days</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </>
      )}
    </Container>
  );
}
