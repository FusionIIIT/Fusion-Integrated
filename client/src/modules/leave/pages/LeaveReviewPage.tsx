import { Badge, Card, Stack, Table, Title } from "@mantine/core";

import { reviewItems } from "../data";

export default function LeaveReviewPage() {
  return (
    <Stack gap="md">
      <Title order={2}>Review Requests</Title>
      <Card withBorder radius="md" p="lg">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Employee</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {reviewItems.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>{item.employee}</Table.Td>
                <Table.Td>{item.leave_type}</Table.Td>
                <Table.Td>
                  {item.start_date} to {item.end_date}
                </Table.Td>
                <Table.Td>{item.days_requested}</Table.Td>
                <Table.Td>
                  <Badge color={item.status === "recommended" ? "blue" : "yellow"}>
                    {item.status}
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
