import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Group,
  SimpleGrid,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { FaCalendarAlt, FaListAlt, FaUsers } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useArrivalsDeparturesReport,
  useDailyOccupancyReport,
  usePendingApprovalsReport,
  useStayExceptionsReport,
} from "../api/hooks";

export default function CaretakerReportsPage() {
  const [reportDate, setReportDate] = useState<string>(new Date().toISOString().slice(0, 10));

  const { data: occReport, error: occError } = useDailyOccupancyReport(reportDate);
  const { data: arrDepReport } = useArrivalsDeparturesReport(reportDate);
  const { data: pendingReport } = usePendingApprovalsReport();
  const { data: exceptions } = useStayExceptionsReport();

  if (occError) {
    return (
      <Container size="xl">
        <ErrorState error={occError} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Caretaker Operations & Reports"
        subtitle="Operational reports: daily room occupancy, arrivals/departures, pending work queues, and stay exceptions."
      />

      <Group mb="md" justify="space-between">
        <TextInput
          label="Target Operations Date"
          type="date"
          value={reportDate}
          onChange={(e) => setReportDate(e.currentTarget.value)}
        />
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">
        <Card padding="md" withBorder>
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Occupied Rooms Today
              </Text>
              <Text fw={700} size="xl">
                {occReport?.total_rooms_occupied ?? 0}
              </Text>
            </div>
            <FaUsers size={24} color="#228be6" />
          </Group>
        </Card>
        <Card padding="md" withBorder>
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Expected Arrivals
              </Text>
              <Text fw={700} size="xl">
                {arrDepReport?.arrivals_count ?? 0}
              </Text>
            </div>
            <FaCalendarAlt size={24} color="#12b886" />
          </Group>
        </Card>
        <Card padding="md" withBorder>
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Pending Caretaker Review
              </Text>
              <Text fw={700} size="xl">
                {pendingReport?.pending_caretaker_review ?? 0}
              </Text>
            </div>
            <FaListAlt size={24} color="#fd7e14" />
          </Group>
        </Card>
      </SimpleGrid>

      <Tabs defaultValue="occupancy">
        <Tabs.List mb="md">
          <Tabs.Tab value="occupancy">Room Occupancy List</Tabs.Tab>
          <Tabs.Tab value="arrivals">Arrivals & Departures</Tabs.Tab>
          <Tabs.Tab value="exceptions">
            Stay Exceptions ({exceptions?.length ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="occupancy">
          <Card padding="lg" withBorder>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Room Number</Table.Th>
                  <Table.Th>Room Type</Table.Th>
                  <Table.Th>Occupancy</Table.Th>
                  <Table.Th>Booking Reference</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {occReport?.rooms?.length ? (
                  occReport.rooms.map((r, i) => (
                    <Table.Tr key={i}>
                      <Table.Td fw={600}>Room {r.room_number}</Table.Td>
                      <Table.Td>{r.room_type}</Table.Td>
                      <Table.Td style={{ textTransform: "capitalize" }}>{r.occupancy_type}</Table.Td>
                      <Table.Td>{r.booking_reference}</Table.Td>
                    </Table.Tr>
                  ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={4}>
                      <Text c="dimmed">No rooms occupied on this date.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="arrivals">
          <Card padding="lg" withBorder>
            <Text fw={600} mb="sm">
              Arrivals for {reportDate}
            </Text>
            <Table striped mb="lg">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Reference</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {arrDepReport?.arrivals?.length ? (
                  arrDepReport.arrivals.map((a) => (
                    <Table.Tr key={a.id}>
                      <Table.Td fw={600}>{a.booking_reference}</Table.Td>
                      <Table.Td>Cat {a.visitor_category}</Table.Td>
                      <Table.Td>{a.status}</Table.Td>
                    </Table.Tr>
                  ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={3}>
                      <Text c="dimmed">No arrivals scheduled.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>

            <Text fw={600} mb="sm">
              Departures for {reportDate}
            </Text>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Reference</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {arrDepReport?.departures?.length ? (
                  arrDepReport.departures.map((d) => (
                    <Table.Tr key={d.id}>
                      <Table.Td fw={600}>{d.booking_reference}</Table.Td>
                      <Table.Td>{d.status}</Table.Td>
                    </Table.Tr>
                  ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={2}>
                      <Text c="dimmed">No departures scheduled.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="exceptions">
          <Card padding="lg" withBorder>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Booking</Table.Th>
                  <Table.Th>Exception Type</Table.Th>
                  <Table.Th>Details</Table.Th>
                  <Table.Th>Triggered At</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {exceptions?.length ? (
                  exceptions.map((e) => (
                    <Table.Tr key={e.id}>
                      <Table.Td fw={600}>{e.booking_reference}</Table.Td>
                      <Table.Td>
                        <Badge color={e.alert_type === "overstay" ? "red" : "orange"}>
                          {e.alert_type.toUpperCase()}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{e.details}</Table.Td>
                      <Table.Td>{new Date(e.triggered_at).toLocaleString()}</Table.Td>
                      <Table.Td>
                        <Badge variant="outline">{e.status}</Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={5}>
                      <Text c="dimmed">No active stay exceptions detected.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
