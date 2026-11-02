import { useState } from "react";
import {
  Card,
  Container,
  Grid,
  Group,
  Progress,
  Select,
  SimpleGrid,
  Table,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { FaBed, FaChartBar, FaCheckCircle } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useExecutiveSummary, useHostelReports, useHostels } from "../api/hooks";

export default function ReportsPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: reportsData, error: reportsError } = useHostelReports({ hostel_id: hostelId });
  const { data: summaryData } = useExecutiveSummary();

  if (reportsError) return <Container size="xl"><ErrorState error={reportsError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const occupancyList = reportsData?.occupancy ?? [];
  const attendanceList = reportsData?.attendance ?? [];
  const complaintsStats = reportsData?.complaints ?? {};
  const finesStats = reportsData?.fines ?? {};

  return (
    <Container size="xl">
      <PageHeader
        title="Operational Reports & Analytics"
        subtitle="Executive summaries, occupancy rates, complaint resolution turnaround, and revenue analytics"
      />

      <Group mb="md">
        <Select
          placeholder="Filter by hostel"
          clearable
          data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
          value={selectedHostel}
          onChange={setSelectedHostel}
          style={{ width: 280 }}
        />
      </Group>

      {/* KPI Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="lg">
        <Card withBorder shadow="xs" radius="md" p="md">
          <Text size="xs" c="dimmed" fw={700} tt="uppercase">Complaints Resolved</Text>
          <Text fw={700} size="xl" mt="xs">
            {complaintsStats.resolved_count ?? 0} / {complaintsStats.total_complaints ?? 0}
          </Text>
          <Text size="xs" c="teal" mt={4}>
            {complaintsStats.resolution_rate_percent ?? 0}% resolution rate
          </Text>
        </Card>

        <Card withBorder shadow="xs" radius="md" p="md">
          <Text size="xs" c="dimmed" fw={700} tt="uppercase">Escalated to Warden</Text>
          <Text fw={700} size="xl" mt="xs" c="orange">
            {complaintsStats.escalated_count ?? 0}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>Requires administrative action</Text>
        </Card>

        <Card withBorder shadow="xs" radius="md" p="md">
          <Text size="xs" c="dimmed" fw={700} tt="uppercase">Fines Collected</Text>
          <Text fw={700} size="xl" mt="xs" c="green">
            Rs. {finesStats.paid_amount ?? 0}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>Out of Rs. {finesStats.total_amount ?? 0} total dues</Text>
        </Card>

        <Card withBorder shadow="xs" radius="md" p="md">
          <Text size="xs" c="dimmed" fw={700} tt="uppercase">Pending Dues</Text>
          <Text fw={700} size="xl" mt="xs" c="red">
            Rs. {finesStats.pending_amount ?? 0}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>Unpaid disciplinary fines</Text>
        </Card>
      </SimpleGrid>

      <Tabs defaultValue="occupancy" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="occupancy" leftSection={<FaBed size={14} />}>
            Room Occupancy & Capacity
          </Tabs.Tab>
          <Tabs.Tab value="attendance" leftSection={<FaCheckCircle size={14} />}>
            Attendance Summaries
          </Tabs.Tab>
          <Tabs.Tab value="executive" leftSection={<FaChartBar size={14} />}>
            Cross-Hostel Executive Summary
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="occupancy">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Hostel</Table.Th>
                  <Table.Th>Total Rooms</Table.Th>
                  <Table.Th>Capacity</Table.Th>
                  <Table.Th>Occupied Beds</Table.Th>
                  <Table.Th>Available Beds</Table.Th>
                  <Table.Th>Utilization %</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {occupancyList.map((row: any) => (
                  <Table.Tr key={row.hostel_id}>
                    <Table.Td fw={600}>{row.hostel_name} ({row.hostel_code})</Table.Td>
                    <Table.Td>{row.total_rooms}</Table.Td>
                    <Table.Td>{row.total_capacity}</Table.Td>
                    <Table.Td>{row.total_occupied}</Table.Td>
                    <Table.Td>{row.available_beds}</Table.Td>
                    <Table.Td>
                      <Group gap="xs" style={{ minWidth: 140 }}>
                        <Text size="xs">{row.occupancy_rate_percent}%</Text>
                        <Progress value={row.occupancy_rate_percent} size="sm" style={{ flex: 1 }} color={row.occupancy_rate_percent > 85 ? "teal" : "blue"} />
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="attendance">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Hostel</Table.Th>
                  <Table.Th>Present Logs</Table.Th>
                  <Table.Th>Absent Logs</Table.Th>
                  <Table.Th>On Leave</Table.Th>
                  <Table.Th>Total Recorded</Table.Th>
                  <Table.Th>Attendance %</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {attendanceList.map((row: any) => (
                  <Table.Tr key={row.hostel_id}>
                    <Table.Td fw={600}>{row.hostel_name}</Table.Td>
                    <Table.Td c="green">{row.present_count}</Table.Td>
                    <Table.Td c="red">{row.absent_count}</Table.Td>
                    <Table.Td c="blue">{row.leave_count}</Table.Td>
                    <Table.Td>{row.total_records}</Table.Td>
                    <Table.Td fw={700}>{row.attendance_percent}%</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="executive">
          <Card withBorder radius="md" p="lg">
            <Title order={4} mb="md">Institute-Wide Executive Summary</Title>
            <Grid gutter="lg">
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder p="md">
                  <Text size="sm" fw={600} mb="xs">Premises & Infrastructure</Text>
                  <Text size="sm">Total Hostels: {summaryData?.infrastructure?.total_hostels ?? 0}</Text>
                  <Text size="sm">Active Premises: {summaryData?.infrastructure?.active_hostels ?? 0}</Text>
                  <Text size="sm">Total Rooms: {summaryData?.infrastructure?.total_rooms ?? 0}</Text>
                  <Text size="sm">Overall Capacity: {summaryData?.infrastructure?.overall_capacity ?? 0} beds</Text>
                  <Text size="sm">Current Residents: {summaryData?.infrastructure?.active_residents ?? 0}</Text>
                </Card>
              </Grid.Col>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Card withBorder p="md">
                  <Text size="sm" fw={600} mb="xs">Operations & Turnaround</Text>
                  <Text size="sm">Open Complaints: {summaryData?.operations?.open_complaints ?? 0}</Text>
                  <Text size="sm">Resolved Complaints: {summaryData?.operations?.resolved_complaints ?? 0}</Text>
                  <Text size="sm">Pending Extended Stays: {summaryData?.operations?.pending_extended_stays ?? 0}</Text>
                  <Text size="sm">Unpaid Disciplinary Fines: {summaryData?.operations?.unpaid_fines_count ?? 0}</Text>
                </Card>
              </Grid.Col>
            </Grid>
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
