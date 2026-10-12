import { Alert, Card, Container, Stack, Table, Text } from "@mantine/core";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveCalendars } from "../api";

export default function CalendarPage() {
  const calendars = useLeaveCalendars();
  if (calendars.error) return <Container size="md"><ErrorState error={calendars.error} /></Container>;
  const published = calendars.data?.results ?? [];
  return <Container size="md">
    <PageHeader title="Holiday and RH calendar" subtitle="Dates from the currently published institute calendar." />
    <Stack>
      {published.length === 0 && <Alert color="gray">No published holiday calendar is available.</Alert>}
      {published.map((calendar) => <Card key={calendar.id} withBorder>
        <Text fw={600} mb="sm">{calendar.year} · revision {calendar.revision}</Text>
        {calendar.holidays.length === 0 ? <Text size="sm" c="dimmed">No holiday dates listed.</Text> :
          <Table striped><Table.Thead><Table.Tr><Table.Th>Date</Table.Th><Table.Th>Description</Table.Th><Table.Th>Type</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{calendar.holidays.map((holiday, index) => <Table.Tr key={`${holiday.date}-${index}`}>
              <Table.Td>{holiday.date}</Table.Td><Table.Td>{holiday.description ?? "—"}</Table.Td>
              <Table.Td>{holiday.restricted_holiday || holiday.type === "RH" ? "Restricted holiday" : holiday.type ?? "Holiday"}</Table.Td>
            </Table.Tr>)}</Table.Tbody>
          </Table>}
      </Card>)}
    </Stack>
  </Container>;
}
