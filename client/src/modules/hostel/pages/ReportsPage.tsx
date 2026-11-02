import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Grid,
  Group,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
} from "@mantine/core";
import {
  FaBed,
  FaCalendarCheck,
  FaTools,
  FaMoneyBillWave,
  FaPlaneDeparture,
  FaShieldAlt,
} from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useHostels, useOperationalReport } from "../api/hooks";

export default function ReportsPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [reportType, setReportType] = useState<string | null>("occupancy");

  const {
    data: report,
    isPending,
    error,
  } = useOperationalReport(reportType || "occupancy", selectedHostel ? Number(selectedHostel) : undefined);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Hostel Operational & Supervisory Reports"
          subtitle="Institute-wide & hostel-specific analytics, capacity metrics, attendance trends, and financial summaries"
        />

        <Group justify="space-between">
          <Select
            placeholder="Select Hostel (Leave empty for Institute-wide)"
            clearable
            value={selectedHostel}
            onChange={setSelectedHostel}
            data={(hostels || []).map((h) => ({
              value: String(h.id),
              label: `${h.name} (${h.code})`,
            }))}
            style={{ width: 320 }}
          />

          <Tabs value={reportType} onChange={setReportType}>
            <Tabs.List>
              <Tabs.Tab value="occupancy" leftSection={<FaBed />}>
                Occupancy
              </Tabs.Tab>
              <Tabs.Tab value="attendance" leftSection={<FaCalendarCheck />}>
                Attendance
              </Tabs.Tab>
              <Tabs.Tab value="complaints" leftSection={<FaTools />}>
                Complaints
              </Tabs.Tab>
              <Tabs.Tab value="fines" leftSection={<FaMoneyBillWave />}>
                Fines & Dues
              </Tabs.Tab>
              <Tabs.Tab value="leaves" leftSection={<FaPlaneDeparture />}>
                Leaves
              </Tabs.Tab>
              <Tabs.Tab value="dashboard_summary" leftSection={<FaShieldAlt />}>
                Executive Overview
              </Tabs.Tab>
            </Tabs.List>
          </Tabs>
        </Group>

        {isPending ? (
          <Text size="sm">Generating report metrics...</Text>
        ) : !report ? (
          <Text size="sm" c="dimmed">No report data generated.</Text>
        ) : (
          <Stack gap="md">
            {/* Occupancy Report */}
            {reportType === "occupancy" && (
              <>
                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Total Institute Capacity</Text>
                      <Text size="xl" fw={700}>{report.summary?.total_capacity || 0} Beds</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Current Occupancy</Text>
                      <Text size="xl" fw={700} c="blue">{report.summary?.total_occupancy || 0} Students</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Vacant / Available Beds</Text>
                      <Text size="xl" fw={700} c="teal">{report.summary?.available_beds || 0} Beds</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Utilization Rate</Text>
                      <Text size="xl" fw={700} c="indigo">{report.summary?.utilization_percentage || 0}%</Text>
                    </Card>
                  </Grid.Col>
                </Grid>

                <Card withBorder radius="md" p="md">
                  <Text fw={600} mb="sm">Hostel Breakdown</Text>
                  <Table striped highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Hostel Name</Table.Th>
                        <Table.Th>Code</Table.Th>
                        <Table.Th>Total Rooms</Table.Th>
                        <Table.Th>Capacity</Table.Th>
                        <Table.Th>Occupied</Table.Th>
                        <Table.Th>Available</Table.Th>
                        <Table.Th>Utilization %</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {(report.hostels || []).map((h: any) => (
                        <Table.Tr key={h.hostel_id}>
                          <Table.Td fw={500}>{h.hostel_name}</Table.Td>
                          <Table.Td>{h.hostel_code}</Table.Td>
                          <Table.Td>{h.total_rooms}</Table.Td>
                          <Table.Td>{h.capacity}</Table.Td>
                          <Table.Td>{h.occupancy}</Table.Td>
                          <Table.Td>{h.available}</Table.Td>
                          <Table.Td>
                            <Badge color={h.utilization > 85 ? "red" : h.utilization > 60 ? "blue" : "teal"}>
                              {h.utilization}%
                            </Badge>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Card>
              </>
            )}

            {/* Attendance Report */}
            {reportType === "attendance" && (
              <>
                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Total Roll-Call Records</Text>
                      <Text size="xl" fw={700}>{report.summary?.total_records || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Present Count</Text>
                      <Text size="xl" fw={700} c="teal">{report.summary?.present || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Absent Count</Text>
                      <Text size="xl" fw={700} c="red">{report.summary?.absent || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Official Leave</Text>
                      <Text size="xl" fw={700} c="orange">{report.summary?.on_leave || 0}</Text>
                    </Card>
                  </Grid.Col>
                </Grid>
                <Card withBorder radius="md" p="md">
                  <Text fw={600} mb="xs">Overall Attendance Metric</Text>
                  <Badge size="xl" color="teal">
                    Attendance Percentage: {report.summary?.overall_attendance_pct || 0}%
                  </Badge>
                </Card>
              </>
            )}

            {/* Complaints Report */}
            {reportType === "complaints" && (
              <>
                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6, md: 2.4 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Total Complaints</Text>
                      <Text size="xl" fw={700}>{report.summary?.total_complaints || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 2.4 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Resolved</Text>
                      <Text size="xl" fw={700} c="teal">{report.summary?.resolved || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 2.4 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">In Progress</Text>
                      <Text size="xl" fw={700} c="yellow">{report.summary?.in_progress || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 2.4 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Escalated to Warden</Text>
                      <Text size="xl" fw={700} c="red">{report.summary?.escalated_to_warden || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 2.4 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Resolution Rate</Text>
                      <Text size="xl" fw={700} c="blue">{report.summary?.resolution_rate || 0}%</Text>
                    </Card>
                  </Grid.Col>
                </Grid>

                <Card withBorder radius="md" p="md">
                  <Text fw={600} mb="sm">Breakdown by Category</Text>
                  <Table striped>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Category</Table.Th>
                        <Table.Th>Total Count</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {(report.by_category || []).map((cat: any) => (
                        <Table.Tr key={cat.category}>
                          <Table.Td fw={500}>{cat.category?.toUpperCase()}</Table.Td>
                          <Table.Td>{cat.count}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Card>
              </>
            )}

            {/* Fines Report */}
            {reportType === "fines" && (
              <>
                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Total Fines Imposed</Text>
                      <Text size="xl" fw={700}>{report.summary?.total_fines || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Total Fine Assessed</Text>
                      <Text size="xl" fw={700}>₹{Number(report.summary?.total_amount || 0).toLocaleString()}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Total Paid / Collected</Text>
                      <Text size="xl" fw={700} c="teal">₹{Number(report.summary?.paid_amount || 0).toLocaleString()}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Outstanding Dues</Text>
                      <Text size="xl" fw={700} c="red">₹{Number(report.summary?.unpaid_amount || 0).toLocaleString()}</Text>
                    </Card>
                  </Grid.Col>
                </Grid>

                <Card withBorder radius="md" p="md">
                  <Text fw={600} mb="sm">Fines by Infraction Type</Text>
                  <Table striped>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Violation Type</Table.Th>
                        <Table.Th>Number of Fines</Table.Th>
                        <Table.Th>Total Amount (₹)</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {(report.by_type || []).map((t: any) => (
                        <Table.Tr key={t.fine_type}>
                          <Table.Td fw={500}>{t.fine_type?.toUpperCase()}</Table.Td>
                          <Table.Td>{t.count}</Table.Td>
                          <Table.Td>₹{Number(t.amount || 0).toLocaleString()}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Card>
              </>
            )}

            {/* Leaves Report */}
            {reportType === "leaves" && (
              <>
                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Total Leave Requests</Text>
                      <Text size="xl" fw={700}>{report.summary?.total_requests || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Approved Leaves</Text>
                      <Text size="xl" fw={700} c="teal">{report.summary?.approved || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Rejected Leaves</Text>
                      <Text size="xl" fw={700} c="red">{report.summary?.rejected || 0}</Text>
                    </Card>
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <Card withBorder p="md" radius="md">
                      <Text size="xs" c="dimmed">Pending Review</Text>
                      <Text size="xl" fw={700} c="yellow">{report.summary?.pending || 0}</Text>
                    </Card>
                  </Grid.Col>
                </Grid>

                <Card withBorder radius="md" p="md">
                  <Text fw={600} mb="sm">Leaves by Category</Text>
                  <Table striped>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Leave Type</Table.Th>
                        <Table.Th>Request Count</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {(report.by_type || []).map((t: any) => (
                        <Table.Tr key={t.leave_type}>
                          <Table.Td fw={500}>{t.leave_type?.toUpperCase()}</Table.Td>
                          <Table.Td>{t.count}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Card>
              </>
            )}

            {/* Executive Overview */}
            {reportType === "dashboard_summary" && (
              <Grid>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Card withBorder p="lg" radius="md">
                    <Text size="xs" c="dimmed">Total Hostels</Text>
                    <Text size="2rem" fw={700}>{report.total_hostels || 0}</Text>
                  </Card>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Card withBorder p="lg" radius="md">
                    <Text size="xs" c="dimmed">Active Residents</Text>
                    <Text size="2rem" fw={700} c="blue">{report.active_residents || 0}</Text>
                  </Card>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Card withBorder p="lg" radius="md">
                    <Text size="xs" c="dimmed">Occupancy Rate</Text>
                    <Text size="2rem" fw={700} c="teal">{report.occupancy_rate || 0}%</Text>
                  </Card>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Card withBorder p="lg" radius="md">
                    <Text size="xs" c="dimmed">Pending Leaves</Text>
                    <Text size="2rem" fw={700} c="orange">{report.pending_leaves || 0}</Text>
                  </Card>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Card withBorder p="lg" radius="md">
                    <Text size="xs" c="dimmed">Active Complaints</Text>
                    <Text size="2rem" fw={700} c="red">{report.active_complaints || 0}</Text>
                  </Card>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
                  <Card withBorder p="lg" radius="md">
                    <Text size="xs" c="dimmed">Total Bed Capacity</Text>
                    <Text size="2rem" fw={700} c="indigo">{report.total_capacity || 0}</Text>
                  </Card>
                </Grid.Col>
              </Grid>
            )}
          </Stack>
        )}
      </Stack>
    </Container>
  );
}
