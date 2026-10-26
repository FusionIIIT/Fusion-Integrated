import { Badge, Card, Container, Group, Stack, Table, Text } from "@mantine/core";

const initialApplications = [
  {
    id: "ELM-2026-001",
    type: "Annual leave",
    startDate: "2026-11-01",
    endDate: "2026-11-05",
    days: 5,
    status: "Approved",
    approver: "Dr. Mehta",
  },
  {
    id: "ELM-2026-014",
    type: "Sick leave",
    startDate: "2026-11-13",
    endDate: "2026-11-14",
    days: 2,
    status: "Pending",
    approver: "Awaiting review",
  },
  {
    id: "ELM-2026-027",
    type: "Personal leave",
    startDate: "2026-12-03",
    endDate: "2026-12-04",
    days: 2,
    status: "Rejected",
    approver: "Prof. Rao",
  },
];

const statusColors: Record<string, string> = {
  Approved: "green",
  Pending: "yellow",
  Rejected: "red",
};

export default function MyLeaveApplicationsPage() {
  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <div>
          <Text size="sm" tt="uppercase" c="blue" fw={700}>ELM</Text>
          <Text fz="2rem" fw={700}>My leave applications</Text>
          <Text c="dimmed" size="sm">
            Track every request and review the current status with the relevant approver.
          </Text>
        </div>

        <Card withBorder radius="md" p="lg">
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Application</Table.Th>
                <Table.Th>Leave type</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Approver</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {initialApplications.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td fw={600}>{item.id}</Table.Td>
                  <Table.Td>{item.type}</Table.Td>
                  <Table.Td>
                    {item.startDate} to {item.endDate}
                  </Table.Td>
                  <Table.Td>{item.days}</Table.Td>
                  <Table.Td>
                    <Badge color={statusColors[item.status] ?? "gray"} variant="light">
                      {item.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{item.approver}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>

        <Card withBorder radius="md" p="lg">
          <Group justify="space-between" align="center">
            <Text fw={700}>Summary</Text>
            <Badge variant="light" color="blue">3 requests</Badge>
          </Group>
          <Text mt="sm" c="dimmed" size="sm">
            1 approved, 1 pending, and 1 rejected request are visible in your history.
          </Text>
        </Card>
      </Stack>
    </Container>
  );
}
