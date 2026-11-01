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
  TextInput,
  Select,
} from "@mantine/core";

export default function AdminPage() {
  const holidays = [
    { date: "2026-01-26", name: "Republic Day", type: "closed" },
    { date: "2026-03-25", name: "Holi", type: "closed" },
    { date: "2026-04-14", name: "Ambedkar Jayanti", type: "restricted" },
    { date: "2026-08-15", name: "Independence Day", type: "closed" },
    { date: "2026-10-02", name: "Gandhi Jayanti", type: "closed" },
  ];

  return (
    <Stack gap="lg">
      <Title order={2}>Leave Administration & Calendars</Title>
      <Text c="dimmed" size="sm">
        Maintain annual holiday calendars, publish Restricted Holidays (RH), and execute year-end processing.
      </Text>

      <Card withBorder radius="md" p="md">
        <Group justify="space-between" mb="md">
          <Title order={4}>Published Holiday Calendar (2026)</Title>
          <Button size="xs" color="blue">Add Holiday / RH</Button>
        </Group>

        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Date</Table.Th>
              <Table.Th>Holiday Name</Table.Th>
              <Table.Th>Type</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {holidays.map((h) => (
              <Table.Tr key={h.date}>
                <Table.Td>{h.date}</Table.Td>
                <Table.Td>{h.name}</Table.Td>
                <Table.Td>
                  <Badge color={h.type === "closed" ? "red" : "violet"}>
                    {h.type === "closed" ? "Closed Holiday" : "Restricted Holiday (RH)"}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Card withBorder radius="md" p="md">
        <Title order={4} mb="xs">Year-End Leave Ledger Processing (EVT-01)</Title>
        <Text size="sm" c="dimmed" mb="md">
          Lapses unused CL/RH/SCL, converts Faculty VL to EL at 2:1 ratio, and carries forward EL/COL to next calendar year.
        </Text>
        <Button color="orange" variant="light">
          Run Year-End Processing
        </Button>
      </Card>
    </Stack>
  );
}
