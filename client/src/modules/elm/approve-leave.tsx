import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Table,
  Text,
} from "@mantine/core";

const initialQueue = [
  {
    id: "ELM-2026-014",
    employee: "Aditi Nair",
    type: "Sick leave",
    startDate: "2026-11-13",
    endDate: "2026-11-14",
    days: 2,
    reason: "Doctor's appointment and recovery.",
    status: "Pending",
  },
  {
    id: "ELM-2026-018",
    employee: "Rohan Verma",
    type: "Annual leave",
    startDate: "2026-11-20",
    endDate: "2026-11-27",
    days: 8,
    reason: "Family visit and travel.",
    status: "Pending",
  },
  {
    id: "ELM-2026-022",
    employee: "Sana Iqbal",
    type: "Casual leave",
    startDate: "2026-11-25",
    endDate: "2026-11-25",
    days: 1,
    reason: "Personal commitment.",
    status: "Pending",
  },
];

export default function ApproveLeavePage() {
  const [queue, setQueue] = useState(initialQueue);

  const updateStatus = (id: string, nextStatus: "Approved" | "Rejected") => {
    setQueue((current) =>
      current
        .map((item) => (item.id === id ? { ...item, status: nextStatus } : item))
        .filter((item) => item.status === "Pending"),
    );
  };

  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <div>
          <Text size="sm" tt="uppercase" c="blue" fw={700}>ELM</Text>
          <Text fz="2rem" fw={700}>Approve leave requests</Text>
          <Text c="dimmed" size="sm">
            Review pending requests and approve or reject them based on eligibility and business rules.
          </Text>
        </div>

        {queue.length === 0 ? (
          <Card withBorder radius="md" p="xl">
            <Text fw={600} ta="center">No pending leave applications</Text>
          </Card>
        ) : (
          <Card withBorder radius="md" p="lg">
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Employee</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {queue.map((item) => (
                  <Table.Tr key={item.id}>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text fw={600}>{item.employee}</Text>
                        <Text size="xs" c="dimmed">{item.id}</Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>{item.type}</Table.Td>
                    <Table.Td>
                      {item.startDate} to {item.endDate}
                    </Table.Td>
                    <Table.Td>{item.days}</Table.Td>
                    <Table.Td>{item.reason}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" color="green" onClick={() => updateStatus(item.id, "Approved")}>
                          Approve
                        </Button>
                        <Button size="xs" color="red" variant="light" onClick={() => updateStatus(item.id, "Rejected")}>
                          Reject
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        )}

        <Card withBorder radius="md" p="lg">
          <Group justify="space-between" align="center">
            <Text fw={700}>Queue summary</Text>
            <Badge variant="light" color="blue">{queue.length} pending</Badge>
          </Group>
          <Text mt="sm" c="dimmed" size="sm">
            Decisions are logged for audit and can be reviewed by the reporting workflow.
          </Text>
        </Card>
      </Stack>
    </Container>
  );
}
