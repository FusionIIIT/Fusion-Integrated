import { useEffect, useState } from "react";
import {
  Badge, Card, Container, Stack, Table, Text, Title
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function CalendarsPage() {
  const [holidays, setHolidays] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/v1/elm/calendars/holidays")
      .then((r) => r.json())
      .then(setHolidays)
      .catch(console.error);
  }, []);

  return (
    <Container size="md">
      <PageHeader
        title="Holiday Calendar"
        subtitle="Currently effective published institute holidays and Restricted Holidays (RH)"
      />

      <Card shadow="sm" padding="md" withBorder>
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Date</Table.Th>
              <Table.Th>Holiday Name</Table.Th>
              <Table.Th>Type</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {holidays.map((h) => (
              <Table.Tr key={h.id}>
                <Table.Td>{h.date}</Table.Td>
                <Table.Td fw={500}>{h.name}</Table.Td>
                <Table.Td>
                  <Badge color={h.is_restricted_holiday ? "orange" : "blue"}>
                    {h.is_restricted_holiday ? "Restricted Holiday (RH)" : "Closed Holiday"}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
            {holidays.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={3}>
                  <Text ta="center" c="dimmed" py="md">No published holidays available.</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
