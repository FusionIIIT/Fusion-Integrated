import { Badge, Card, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";

import { leaveBalances, leaveRequests } from "../data";

export default function LeaveDashboardPage() {
  return (
    <Stack gap="lg">
      <Title order={2}>Leave Dashboard</Title>

      <SimpleGrid cols={{ base: 1, md: 3 }}>
        {leaveBalances.slice(0, 3).map((balance) => (
          <Card key={balance.code} withBorder radius="md" p="lg">
            <Text fw={600}>{balance.label}</Text>
            <Text c="dimmed" mt="xs">
              {balance.available} days remaining
            </Text>
            <Badge variant="light" mt="sm">
              {balance.used} used / {balance.entitled} entitled
            </Badge>
          </Card>
        ))}
      </SimpleGrid>

      <Card withBorder radius="md" p="lg">
        <Title order={3} mb="md">Recent leave requests</Title>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Request</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {leaveRequests.map((request) => (
              <Table.Tr key={request.id}>
                <Table.Td>{request.leave_type}</Table.Td>
                <Table.Td>
                  {request.start_date} to {request.end_date}
                </Table.Td>
                <Table.Td>{request.days_requested}</Table.Td>
                <Table.Td>
                  <Badge color={request.status === "approved" ? "green" : "yellow"}>
                    {request.status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  );
}
