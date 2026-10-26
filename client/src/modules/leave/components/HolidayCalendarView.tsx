import {
  Badge,
  Card,
  Center,
  Loader,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
} from "@mantine/core";
import { useState } from "react";
import { FaCalendarAlt, FaSun } from "react-icons/fa";

import { useHolidays, useVacations } from "../api/hooks";

export function HolidayCalendarView() {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState<number>(currentYear);

  const { data: holidays, isPending: holidaysPending } = useHolidays(selectedYear);
  const { data: vacations, isPending: vacationsPending } = useVacations(selectedYear);

  const closedHolidays = holidays?.filter((h) => h.is_closed_holiday) ?? [];
  const restrictedHolidays = holidays?.filter((h) => h.is_restricted_holiday) ?? [];

  return (
    <Stack gap="md">
      <Select
        label="Calendar Year"
        style={{ width: 140 }}
        value={String(selectedYear)}
        onChange={(v) => setSelectedYear(Number(v) || currentYear)}
        data={[
          { value: String(currentYear - 1), label: String(currentYear - 1) },
          { value: String(currentYear), label: String(currentYear) },
          { value: String(currentYear + 1), label: String(currentYear + 1) },
        ]}
      />

      <Tabs defaultValue="closed">
        <Tabs.List>
          <Tabs.Tab value="closed" leftSection={<FaCalendarAlt />}>Closed Holidays ({closedHolidays.length})</Tabs.Tab>
          <Tabs.Tab value="restricted" leftSection={<FaCalendarAlt />}>Restricted Holidays ({restrictedHolidays.length})</Tabs.Tab>
          <Tabs.Tab value="vacations" leftSection={<FaSun />}>Academic Vacations ({vacations?.length ?? 0})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="closed" pt="md">
          <Card withBorder padding="md" radius="md">
            {holidaysPending ? (
              <Center py="xl"><Loader size="md" /></Center>
            ) : closedHolidays.length === 0 ? (
              <Center py="xl"><Text c="dimmed">No closed holidays published for {selectedYear}.</Text></Center>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Date</Table.Th>
                    <Table.Th>Holiday Name</Table.Th>
                    <Table.Th>Status</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {closedHolidays.map((h) => (
                    <Table.Tr key={h.id}>
                      <Table.Td fw={500}>{h.date}</Table.Td>
                      <Table.Td>{h.name}</Table.Td>
                      <Table.Td><Badge color="green">Closed Holiday</Badge></Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="restricted" pt="md">
          <Card withBorder padding="md" radius="md">
            {holidaysPending ? (
              <Center py="xl"><Loader size="md" /></Center>
            ) : restrictedHolidays.length === 0 ? (
              <Center py="xl"><Text c="dimmed">No restricted holidays published for {selectedYear}.</Text></Center>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Date</Table.Th>
                    <Table.Th>Restricted Holiday Name</Table.Th>
                    <Table.Th>Applicability</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {restrictedHolidays.map((h) => (
                    <Table.Tr key={h.id}>
                      <Table.Td fw={500}>{h.date}</Table.Td>
                      <Table.Td>{h.name}</Table.Td>
                      <Table.Td><Badge color="orange">Max 2 Days/Year</Badge></Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="vacations" pt="md">
          <Card withBorder padding="md" radius="md">
            {vacationsPending ? (
              <Center py="xl"><Loader size="md" /></Center>
            ) : !vacations || vacations.length === 0 ? (
              <Center py="xl"><Text c="dimmed">No vacation periods published for {selectedYear}.</Text></Center>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Vacation Schedule</Table.Th>
                    <Table.Th>Start Date</Table.Th>
                    <Table.Th>End Date</Table.Th>
                    <Table.Th>Note</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {vacations.map((v) => (
                    <Table.Tr key={v.id}>
                      <Table.Td fw={600}>{v.name}</Table.Td>
                      <Table.Td>{v.start_date}</Table.Td>
                      <Table.Td>{v.end_date}</Table.Td>
                      <Table.Td><Badge color="teal">Faculty VL Permitted</Badge></Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
