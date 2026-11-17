import React, { useEffect, useState } from "react";
import { Card, Container, Grid, Group, Loader, Table, Text, Title, Badge } from "@mantine/core";
import { leaveApi, type LeaveBalance } from "../api/leaveApi";

export default function LeaveBalancesPage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    leaveApi
      .getMyBalances()
      .then((data) => {
        setBalances(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load balances");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  return (
    <Container size="lg" py="xl">
      <Title order={2} mb="lg">
        Leave Balances
      </Title>
      {error && (
        <Card withBorder p="md" mb="lg" c="red">
          <Text>{error}</Text>
        </Card>
      )}

      <Grid mb="xl">
        {balances.map((b) => (
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }} key={b.id}>
            <Card withBorder shadow="sm" radius="md" p="md">
              <Group justify="space-between" mb="xs">
                <Text fw={600} size="lg">
                  {b.leave_type_code}
                </Text>
                <Badge color="blue" variant="light">
                  {b.year}
                </Badge>
              </Group>
              <Text size="sm" c="dimmed" mb="md">
                {b.leave_type_name}
              </Text>
              <Group justify="space-between">
                <div>
                  <Text size="xs" c="dimmed">
                    Allocated
                  </Text>
                  <Text fw={500}>{b.allocated_days} d</Text>
                </div>
                <div>
                  <Text size="xs" c="dimmed">
                    Used
                  </Text>
                  <Text fw={500}>{b.used_days} d</Text>
                </div>
                <div>
                  <Text size="xs" c="dimmed">
                    Remaining
                  </Text>
                  <Text fw={700} c={b.remaining_days > 0 ? "teal" : "red"}>
                    {b.remaining_days} d
                  </Text>
                </div>
              </Group>
            </Card>
          </Grid.Col>
        ))}
      </Grid>

      <Card withBorder radius="md">
        <Title order={4} mb="md">
          Summary Table
        </Title>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Code</Table.Th>
              <Table.Th>Leave Type</Table.Th>
              <Table.Th>Allocated</Table.Th>
              <Table.Th>Used</Table.Th>
              <Table.Th>Remaining</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {balances.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td fw={600}>{row.leave_type_code}</Table.Td>
                <Table.Td>{row.leave_type_name}</Table.Td>
                <Table.Td>{row.allocated_days} days</Table.Td>
                <Table.Td>{row.used_days} days</Table.Td>
                <Table.Td fw={600} c={row.remaining_days > 0 ? "teal" : "red"}>
                  {row.remaining_days} days
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
