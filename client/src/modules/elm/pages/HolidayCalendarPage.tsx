import { Badge, Card, Container, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHolidayCalendar } from "../api/hooks";

export default function HolidayCalendarPage() {
  const calendar = useHolidayCalendar();

  if (calendar.error) {
    return (
      <Container size="md">
        <ErrorState error={calendar.error} />
      </Container>
    );
  }

  const holidays = calendar.data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader
        title="Holiday Calendar"
        subtitle="Institute gazetted and restricted holidays"
      />
      <Card withBorder padding="lg">
        {holidays.length === 0 ? (
          <Text size="sm" c="dimmed">
            No holidays published yet.
          </Text>
        ) : (
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th>Holiday</Table.Th>
                <Table.Th>Category</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {holidays.map((h) => (
                <Table.Tr key={h.id}>
                  <Table.Td>{h.date}</Table.Td>
                  <Table.Td>{h.title}</Table.Td>
                  <Table.Td>
                    <Badge
                      color={h.is_restricted ? "orange" : "teal"}
                      variant="light"
                    >
                      {h.is_restricted ? "Restricted Holiday (RH)" : "Holiday"}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Container>
  );
}
