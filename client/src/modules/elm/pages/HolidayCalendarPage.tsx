import { Badge, Card, Container, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHolidays } from "../api/hooks";
import type { Holiday } from "../api/types";

export default function HolidayCalendarPage() {
  const { data: holidays, isPending, error } = useHolidays();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Holiday Calendar"
        subtitle="Institutional list of closed public holidays and restricted holidays (RH)"
      />

      <Card padding="lg" withBorder>
        {isPending ? (
          <Text c="dimmed">Loading holidays...</Text>
        ) : !holidays?.length ? (
          <Text c="dimmed">No holidays listed in the calendar.</Text>
        ) : (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th>Holiday Description</Table.Th>
                <Table.Th>Type</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {holidays.map((h: Holiday) => (
                <Table.Tr key={h.id}>
                  <Table.Td fw={500}>{h.date}</Table.Td>
                  <Table.Td>{h.description}</Table.Td>
                  <Table.Td>
                    {h.is_rh ? (
                      <Badge color="orange" variant="light">Restricted Holiday (RH)</Badge>
                    ) : (
                      <Badge color="green" variant="light">Public Holiday</Badge>
                    )}
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

