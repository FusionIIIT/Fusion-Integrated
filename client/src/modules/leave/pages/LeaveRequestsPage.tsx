import { Badge, Card, Stack, Table, Title } from "@mantine/core";

import { leaveRequests } from "../data";

export default function LeaveRequestsPage() {
  return (
    <Stack gap="md">
      <Title order={2}>My Leave Requests</Title>
      <Card withBorder radius="md" p="lg">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {leaveRequests.map((request) => (
              <Table.Tr key={request.id}>
                <Table.Td>{request.id}</Table.Td>
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
