import { useEffect, useState } from "react";
import {
  Card,
  Container,
  Group,
  SimpleGrid,
  Table,
  Text,
  Title,
  Loader,
  Alert,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { elmApi } from "../api/elmApi";
import type { LeaveBalance } from "../types";

export default function LeaveBalancesPage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBalances = async () => {
      try {
        const data = await elmApi.getBalances();
        setBalances(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load leave balances.");
      } finally {
        setLoading(false);
      }
    };
    fetchBalances();
  }, []);

  if (loading) {
    return (
      <Container size="xl" py="lg">
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      </Container>
    );
  }

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Leave Ledger & Entitlements"
        subtitle="Detailed summary of annual credit, carry-forward, consumption, and balance rules."
      />

      {error && (
        <Alert color="red" mb="md" title="Notice">
          {error}
        </Alert>
      )}

      <Card withBorder radius="md" mb="xl">
        <Table verticalSpacing="md" striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Leave Category</Table.Th>
              <Table.Th>Annual Credited</Table.Th>
              <Table.Th>Carried Forward</Table.Th>
              <Table.Th>Total Entitled</Table.Th>
              <Table.Th>Consumed / Availed</Table.Th>
              <Table.Th>Pending Approval</Table.Th>
              <Table.Th>Available Balance</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {balances.map((b) => (
              <Table.Tr key={b.id}>
                <Table.Td fw={700}>{b.category}</Table.Td>
                <Table.Td>{b.credited} days</Table.Td>
                <Table.Td>{b.carried_forward} days</Table.Td>
                <Table.Td fw={600}>{b.credited + b.carried_forward} days</Table.Td>
                <Table.Td c="red">{b.consumed} days</Table.Td>
                <Table.Td c="orange">{b.pending} days</Table.Td>
                <Table.Td fw={800} c="blue">
                  {b.available_balance} days
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Title order={4} mb="sm">
        Institutional Leave Rules & Carry-Forward Policies
      </Title>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Card withBorder padding="md">
          <Text fw={700} c="blue">
            Casual Leave (CL) & Restricted Holiday (RH)
          </Text>
          <Text size="sm" mt="xs">
            - CL: 8 days/year for all employees. Supports first-half and second-half requests (0.5d). Unused CL lapses at year end.
          </Text>
          <Text size="sm" mt="xs">
            - RH: 2 days/year per employee for applicable Restricted Holidays listed in the published calendar. Unused RH lapses at year end.
          </Text>
        </Card>

        <Card withBorder padding="md">
          <Text fw={700} c="blue">
            Earned Leave (EL) & Vacation Leave (VL)
          </Text>
          <Text size="sm" mt="xs">
            - EL: Non-faculty receive 30 days/year; unused EL carries forward.
          </Text>
          <Text size="sm" mt="xs">
            - VL: Faculty receive 60 VL days during vacation periods in the Academic Calendar. At year end, unused VL converts to EL at 2 VL : 1 EL and carries forward.
          </Text>
        </Card>

        <Card withBorder padding="md">
          <Text fw={700} c="blue">
            Special Casual Leave (SCL)
          </Text>
          <Text size="sm" mt="xs">
            - Up to 15 days/year for special purposes admissible by the Sanctioning Authority. Unused SCL lapses at year end.
          </Text>
        </Card>

        <Card withBorder padding="md">
          <Text fw={700} c="blue">
            Commuted Leave (COL)
          </Text>
          <Text size="sm" mt="xs">
            - 20 days/year; medical evidence may be required. Unused COL carries forward. Continuous day counting applies.
          </Text>
        </Card>
      </SimpleGrid>
    </Container>
  );
}
