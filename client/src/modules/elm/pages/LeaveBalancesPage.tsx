import React, { useEffect, useState } from "react";
import {
  Badge,
  Card,
  Container,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage, http } from "../../../lib/http";
import type { LeaveBalance } from "../types";

export const LeaveBalancesPage: React.FC = () => {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBalances = async () => {
      try {
        const res = await http.get<LeaveBalance[]>("/elm/balances");
        setBalances(res.data);
      } catch (err) {
        notifications.show({
          title: "Error",
          message: errorMessage(err),
          color: "red",
        });
      } finally {
        setLoading(false);
      }
    };
    void fetchBalances();
  }, []);

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>My Leave Balances</Title>
          <Text c="dimmed" size="sm">
            Current year leave entitlements, consumption, and available quotas.
          </Text>
        </div>

        {loading ? (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} height={120} radius="md" />
            ))}
          </SimpleGrid>
        ) : (
          <>
            <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
              {balances.map((b) => (
                <Card key={b.id} withBorder shadow="xs" radius="md" p="md">
                  <Group justify="space-between" mb="xs">
                    <Text fw={600} size="md">
                      {b.category_display}
                    </Text>
                    <Badge color="blue" variant="light">
                      {b.leave_category}
                    </Badge>
                  </Group>
                  <Text size="xl" fw={700} c="indigo">
                    {b.available} Days
                  </Text>
                  <Text size="xs" c="dimmed" mt="xs">
                    Credited: {b.credited} | Used: {b.used}
                  </Text>
                </Card>
              ))}
            </SimpleGrid>

            <Card withBorder shadow="xs" radius="md">
              <Title order={4} mb="md">
                Detailed Balance Statement
              </Title>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Category Code</Table.Th>
                    <Table.Th>Description</Table.Th>
                    <Table.Th>Year</Table.Th>
                    <Table.Th>Annual Credited</Table.Th>
                    <Table.Th>Total Used</Table.Th>
                    <Table.Th>Available Remaining</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {balances.map((b) => (
                    <Table.Tr key={b.id}>
                      <Table.Td fw={600}>{b.leave_category}</Table.Td>
                      <Table.Td>{b.category_display}</Table.Td>
                      <Table.Td>{b.year}</Table.Td>
                      <Table.Td>{b.credited}</Table.Td>
                      <Table.Td>{b.used}</Table.Td>
                      <Table.Td fw={700} c={parseFloat(b.available) > 0 ? "teal" : "dimmed"}>
                        {b.available}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
          </>
        )}
      </Stack>
    </Container>
  );
};

export default LeaveBalancesPage;
