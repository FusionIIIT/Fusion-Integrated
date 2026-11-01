import React from "react";
import {
  Card,
  Title,
  Table,
  Badge,
  Button,
  Stack,
  Text,
  Group,
  SimpleGrid,
  Paper,
} from "@mantine/core";

export default function MyLeavesPage() {
  const balances = [
    { category: "CL", label: "Casual Leave", total: 8, availed: 1.5, available: 6.5 },
    { category: "RH", label: "Restricted Holiday", total: 2, availed: 0, available: 2 },
    { category: "SCL", label: "Special Casual Leave", total: 15, availed: 0, available: 15 },
    { category: "EL", label: "Earned Leave", total: 30, availed: 5, available: 25 },
    { category: "COL", label: "Commuted Leave", total: 20, availed: 0, available: 20 },
  ];

  const applications = [
    {
      id: 101,
      category: "CL",
      startDate: "2026-10-20",
      endDate: "2026-10-20",
      days: 0.5,
      reason: "Personal urgent work (First half)",
      status: "approved",
    },
    {
      id: 102,
      category: "EL",
      startDate: "2026-11-02",
      endDate: "2026-11-06",
      days: 5.0,
      reason: "Family function outside Jabalpur",
      status: "awaiting_unit_head",
    },
  ];

  return (
    <Stack gap="lg">
      <Title order={2}>My Leaves & Balances</Title>

      {/* Balance Cards */}
      <SimpleGrid cols={{ base: 1, sm: 3, md: 5 }}>
        {balances.map((b) => (
          <Paper key={b.category} withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              {b.label} ({b.category})
            </Text>
            <Title order={3} mt="xs">
              {b.available} <Text span size="sm" c="dimmed">/ {b.total}</Text>
            </Title>
            <Text size="xs" c="dimmed" mt={4}>
              Availed: {b.availed} days
            </Text>
          </Paper>
        ))}
      </SimpleGrid>

      {/* Applications Table */}
      <Card withBorder radius="md" p="md">
        <Title order={4} mb="md">Application History</Title>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {applications.map((app) => (
              <Table.Tr key={app.id}>
                <Table.Td>#{app.id}</Table.Td>
                <Table.Td><Badge color="blue">{app.category}</Badge></Table.Td>
                <Table.Td>{app.startDate} to {app.endDate}</Table.Td>
                <Table.Td>{app.days}</Table.Td>
                <Table.Td>{app.reason}</Table.Td>
                <Table.Td>
                  <Badge color={app.status === "approved" ? "teal" : "yellow"}>
                    {app.status.replace(/_/g, " ")}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {app.status === "awaiting_unit_head" && (
                    <Button size="xs" color="red" variant="subtle">
                      Withdraw
                    </Button>
                  )}
                  {app.status === "approved" && (
                    <Button size="xs" color="gray" variant="subtle">
                      Cancel
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  );
}
