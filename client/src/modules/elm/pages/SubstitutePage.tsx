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

export default function SubstitutePage() {
  const pendingRequests = [
    {
      id: 104,
      applicantName: "Prof. R. Sharma",
      category: "EL",
      period: "2026-11-05 to 2026-11-09",
      duties: "CS302 Lectures and Lab session",
    },
  ];

  return (
    <Stack gap="lg">
      <Title order={2}>Substitute Responsibility Requests</Title>
      <Text c="dimmed" size="sm">
        Review colleague requests nominating you to cover duties during their absence.
      </Text>

      <Card withBorder radius="md" p="md">
        {pendingRequests.length === 0 ? (
          <Text c="dimmed">No pending substitute requests.</Text>
        ) : (
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Applicant</Table.Th>
                <Table.Th>Leave Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Coverage Description</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pendingRequests.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>{r.applicantName}</Table.Td>
                  <Table.Td><Badge color="blue">{r.category}</Badge></Table.Td>
                  <Table.Td>{r.period}</Table.Td>
                  <Table.Td>{r.duties}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button size="xs" color="teal">Accept</Button>
                      <Button size="xs" color="red" variant="subtle">Decline</Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
