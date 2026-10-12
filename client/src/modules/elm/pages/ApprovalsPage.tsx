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
} from "@mantine/core";

interface ApprovalsPageProps {
  role: "unit_head" | "establishment" | "sanction";
}

export default function ApprovalsPage({ role }: ApprovalsPageProps) {
  const titles = {
    unit_head: "Unit Head Leave Reviews",
    establishment: "Establishment Verification Queue",
    sanction: "Competent Authority Sanction Decisions",
  };

  const pendingList = [
    {
      id: 201,
      employeeName: "Dr. A. Verma",
      category: "EL",
      days: 4,
      period: "2026-11-10 to 2026-11-13",
      substitute: "Accepted (Dr. K. Patel)",
      stationLeave: "Yes (Delhi conference)",
    },
  ];

  return (
    <Stack gap="lg">
      <Title order={2}>{titles[role]}</Title>
      <Text c="dimmed" size="sm">
        Process leave applications awaiting your review or sanction decision.
      </Text>

      <Card withBorder radius="md" p="md">
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Employee</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Days</Table.Th>
              <Table.Th>Period</Table.Th>
              <Table.Th>Substitute Status</Table.Th>
              <Table.Th>Station Leave</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {pendingList.map((p) => (
              <Table.Tr key={p.id}>
                <Table.Td>#{p.id}</Table.Td>
                <Table.Td>{p.employeeName}</Table.Td>
                <Table.Td><Badge color="blue">{p.category}</Badge></Table.Td>
                <Table.Td>{p.days}</Table.Td>
                <Table.Td>{p.period}</Table.Td>
                <Table.Td><Badge color="teal" variant="light">{p.substitute}</Badge></Table.Td>
                <Table.Td>{p.stationLeave}</Table.Td>
                <Table.Td>
                  {role === "unit_head" && (
                    <Group gap="xs">
                      <Button size="xs" color="teal">Recommend</Button>
                      <Button size="xs" color="orange" variant="light">Not Recommend</Button>
                    </Group>
                  )}
                  {role === "establishment" && (
                    <Button size="xs" color="blue">Verify & Route</Button>
                  )}
                  {role === "sanction" && (
                    <Group gap="xs">
                      <Button size="xs" color="teal">Sanction</Button>
                      <Button size="xs" color="red" variant="subtle">Reject</Button>
                    </Group>
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
