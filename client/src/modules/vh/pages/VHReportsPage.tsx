import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  FaBed,
  FaChartBar,
  FaCheckCircle,
  FaClipboardList,
  FaExclamationCircle,
  FaExclamationTriangle,
  FaFileInvoiceDollar,
  FaHotel,
  FaMoneyBillWave,
  FaSync,
  FaUserClock,
  FaUsers,
} from "react-icons/fa";

import { useCaretakerReport, useInChargeReport, useScanAlerts } from "../api/hooks";

export default function VHReportsPage() {
  const {
    data: inchargeReport,
    isLoading: loadingIncharge,
    refetch: refetchIncharge,
  } = useInChargeReport();

  const {
    data: caretakerReport,
    isLoading: loadingCaretaker,
    refetch: refetchCaretaker,
  } = useCaretakerReport();

  const scanAlerts = useScanAlerts();

  const [activeTab, setActiveTab] = useState<string | null>("incharge");
  const [scanResult, setScanResult] = useState<string | null>(null);

  const handleRunScan = async () => {
    setScanResult(null);
    const res = await scanAlerts.mutateAsync();
    setScanResult(
      `Scan complete: ${res.no_shows_detected} no-show(s), ${res.overstays_detected} overstay(s), ${res.inventory_alerts_active} low stock alert(s).`,
    );
    refetchCaretaker();
    refetchIncharge();
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Visitors Hostel Analytics & Reports</Title>
            <Text c="dimmed" size="sm">
              Supervisory overviews, operational shift logs, and stay exception monitoring (UC-VH-010, BR-VH-010)
            </Text>
          </div>
          <Group>
            <Button
              color="indigo"
              variant="light"
              leftSection={<FaUserClock />}
              loading={scanAlerts.isPending}
              onClick={handleRunScan}
            >
              Run Exception Scan
            </Button>
            <Button
              variant="default"
              onClick={() => {
                refetchIncharge();
                refetchCaretaker();
              }}
              leftSection={<FaSync />}
            >
              Refresh
            </Button>
          </Group>
        </Group>

        {scanResult && (
          <Alert
            icon={<FaCheckCircle size={16} />}
            title="Automated Audit Completed"
            color="teal"
            withCloseButton
            onClose={() => setScanResult(null)}
          >
            {scanResult}
          </Alert>
        )}

        <Card withBorder radius="md" p="md">
          <Tabs value={activeTab} onChange={setActiveTab}>
            <Tabs.List mb="md">
              <Tabs.Tab value="incharge" leftSection={<FaChartBar size={14} />}>
                In-Charge Supervisory Overview
              </Tabs.Tab>
              <Tabs.Tab value="caretaker" leftSection={<FaClipboardList size={14} />}>
                Caretaker Operational Logs
              </Tabs.Tab>
              <Tabs.Tab
                value="exceptions"
                leftSection={<FaExclamationTriangle size={14} />}
                rightSection={
                  caretakerReport?.unresolved_alerts?.length ? (
                    <Badge size="xs" circle color="red">
                      {caretakerReport.unresolved_alerts.length}
                    </Badge>
                  ) : undefined
                }
              >
                Stay Exceptions & Alerts
              </Tabs.Tab>
            </Tabs.List>

            {/* TAB 1: IN-CHARGE REPORT */}
            <Tabs.Panel value="incharge">
              {loadingIncharge ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : inchargeReport ? (
                <Stack gap="lg">
                  {/* Revenue Summary Banner */}
                  <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="md">
                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Total Revenue
                          </Text>
                          <Title order={3}>
                            ₹{inchargeReport.revenue_summary.total_revenue}
                          </Title>
                        </div>
                        <FaMoneyBillWave size={26} color="#12b886" />
                      </Group>
                    </Paper>

                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Room Charges
                          </Text>
                          <Title order={3}>
                            ₹{inchargeReport.revenue_summary.room_charges}
                          </Title>
                        </div>
                        <FaHotel size={26} color="#228be6" />
                      </Group>
                    </Paper>

                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Meal Charges
                          </Text>
                          <Title order={3}>
                            ₹{inchargeReport.revenue_summary.meal_charges}
                          </Title>
                        </div>
                        <FaFileInvoiceDollar size={26} color="#fab005" />
                      </Group>
                    </Paper>

                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Pending Settlement
                          </Text>
                          <Title order={3} c="red">
                            ₹{inchargeReport.revenue_summary.total_pending_settlement}
                          </Title>
                        </div>
                        <FaExclamationCircle size={26} color="#fa5252" />
                      </Group>
                    </Paper>
                  </SimpleGrid>

                  {/* Booking Status Summary */}
                  <Grid>
                    <Grid.Col span={{ base: 12, md: 6 }}>
                      <Card withBorder radius="md" p="md">
                        <Title order={4} mb="sm">Bookings Breakdown by Status</Title>
                        <Text size="xs" c="dimmed" mb="md">
                          Total Requisitions Logged: <b>{inchargeReport.booking_summary.total_bookings}</b>
                        </Text>
                        <Table withTableBorder>
                          <Table.Thead>
                            <Table.Tr>
                              <Table.Th>Status</Table.Th>
                              <Table.Th>Count</Table.Th>
                            </Table.Tr>
                          </Table.Thead>
                          <Table.Tbody>
                            {Object.entries(inchargeReport.booking_summary.by_status).map(
                              ([status, count]) => (
                                <Table.Tr key={status}>
                                  <Table.Td>
                                    <Badge size="sm">{status}</Badge>
                                  </Table.Td>
                                  <Table.Td>
                                    <Text fw={600}>{count}</Text>
                                  </Table.Td>
                                </Table.Tr>
                              ),
                            )}
                          </Table.Tbody>
                        </Table>
                      </Card>
                    </Grid.Col>

                    {/* Category Occupancy Breakdown */}
                    <Grid.Col span={{ base: 12, md: 6 }}>
                      <Card withBorder radius="md" p="md">
                        <Title order={4} mb="sm">Category-Wise Demand</Title>
                        <Text size="xs" c="dimmed" mb="md">
                          Distribution across visitor categories A through D
                        </Text>
                        <Table withTableBorder>
                          <Table.Thead>
                            <Table.Tr>
                              <Table.Th>Category</Table.Th>
                              <Table.Th>Name</Table.Th>
                              <Table.Th>Bookings</Table.Th>
                              <Table.Th>Rooms</Table.Th>
                            </Table.Tr>
                          </Table.Thead>
                          <Table.Tbody>
                            {inchargeReport.category_occupancy.map((cat) => (
                              <Table.Tr key={cat.category_code}>
                                <Table.Td>
                                  <Badge color="blue" variant="filled">
                                    Cat {cat.category_code}
                                  </Badge>
                                </Table.Td>
                                <Table.Td>{cat.category_name}</Table.Td>
                                <Table.Td>
                                  <Text fw={600}>{cat.bookings_count}</Text>
                                </Table.Td>
                                <Table.Td>
                                  <Text fw={600}>{cat.total_rooms_booked}</Text>
                                </Table.Td>
                              </Table.Tr>
                            ))}
                          </Table.Tbody>
                        </Table>
                      </Card>
                    </Grid.Col>
                  </Grid>

                  {/* Inventory Health Card */}
                  <Card withBorder radius="md" p="md">
                    <Title order={4} mb="sm">Hostel Inventory Health</Title>
                    <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
                      <Paper p="sm" withBorder bg="gray.0">
                        <Text size="xs" c="dimmed">Tracked Items:</Text>
                        <Text fw={700} size="lg">
                          {inchargeReport.inventory_usage.total_inventory_items}
                        </Text>
                      </Paper>
                      <Paper p="sm" withBorder bg="gray.0">
                        <Text size="xs" c="dimmed">Below Threshold Items:</Text>
                        <Text fw={700} size="lg" c="red">
                          {inchargeReport.inventory_usage.items_below_threshold.length}
                        </Text>
                      </Paper>
                      <Paper p="sm" withBorder bg="gray.0">
                        <Text size="xs" c="dimmed">Pending Restock Approvals:</Text>
                        <Text fw={700} size="lg" c="orange">
                          {inchargeReport.inventory_usage.replenishments_pending}
                        </Text>
                      </Paper>
                    </SimpleGrid>
                  </Card>
                </Stack>
              ) : null}
            </Tabs.Panel>

            {/* TAB 2: CARETAKER REPORT */}
            <Tabs.Panel value="caretaker">
              {loadingCaretaker ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : caretakerReport ? (
                <Stack gap="lg">
                  {/* Daily Occupancy Snapshot */}
                  <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="md">
                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Checked-In Guests
                          </Text>
                          <Title order={3}>
                            {caretakerReport.daily_occupancy.checked_in_guests}
                          </Title>
                        </div>
                        <FaUsers size={26} color="#40c057" />
                      </Group>
                    </Paper>

                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Occupied Rooms
                          </Text>
                          <Title order={3}>
                            {caretakerReport.daily_occupancy.occupied_rooms}
                          </Title>
                        </div>
                        <FaBed size={26} color="#228be6" />
                      </Group>
                    </Paper>

                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Available Rooms
                          </Text>
                          <Title order={3}>
                            {caretakerReport.daily_occupancy.available_rooms}
                          </Title>
                        </div>
                        <FaHotel size={26} color="#12b886" />
                      </Group>
                    </Paper>

                    <Paper withBorder p="md" radius="md">
                      <Group justify="space-between">
                        <div>
                          <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                            Maintenance Rooms
                          </Text>
                          <Title order={3}>
                            {caretakerReport.daily_occupancy.maintenance_rooms}
                          </Title>
                        </div>
                        <FaExclamationTriangle size={26} color="#fa5252" />
                      </Group>
                    </Paper>
                  </SimpleGrid>

                  {/* Upcoming Arrivals & Departures */}
                  <Grid>
                    <Grid.Col span={{ base: 12, md: 6 }}>
                      <Card withBorder radius="md" p="md">
                        <Title order={4} mb="sm">Upcoming Arrivals</Title>
                        {caretakerReport.upcoming_arrivals.length === 0 ? (
                          <Text size="sm" c="dimmed">No upcoming arrivals scheduled.</Text>
                        ) : (
                          <Table withTableBorder>
                            <Table.Thead>
                              <Table.Tr>
                                <Table.Th>Ref</Table.Th>
                                <Table.Th>Visitor</Table.Th>
                                <Table.Th>Check-In Date</Table.Th>
                                <Table.Th>Rooms</Table.Th>
                              </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                              {caretakerReport.upcoming_arrivals.map((arr) => (
                                <Table.Tr key={arr.id}>
                                  <Table.Td>
                                    <Text fw={600} size="xs">{arr.booking_reference}</Text>
                                  </Table.Td>
                                  <Table.Td>{arr.visitor_name}</Table.Td>
                                  <Table.Td>
                                    <Text size="xs">{arr.check_in_date}</Text>
                                  </Table.Td>
                                  <Table.Td>{arr.number_of_rooms}</Table.Td>
                                </Table.Tr>
                              ))}
                            </Table.Tbody>
                          </Table>
                        )}
                      </Card>
                    </Grid.Col>

                    <Grid.Col span={{ base: 12, md: 6 }}>
                      <Card withBorder radius="md" p="md">
                        <Title order={4} mb="sm">Upcoming Departures</Title>
                        {caretakerReport.upcoming_departures.length === 0 ? (
                          <Text size="sm" c="dimmed">No upcoming departures scheduled.</Text>
                        ) : (
                          <Table withTableBorder>
                            <Table.Thead>
                              <Table.Tr>
                                <Table.Th>Ref</Table.Th>
                                <Table.Th>Visitor</Table.Th>
                                <Table.Th>Check-Out Date</Table.Th>
                              </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                              {caretakerReport.upcoming_departures.map((dep) => (
                                <Table.Tr key={dep.id}>
                                  <Table.Td>
                                    <Text fw={600} size="xs">{dep.booking_reference}</Text>
                                  </Table.Td>
                                  <Table.Td>{dep.visitor_name}</Table.Td>
                                  <Table.Td>
                                    <Text size="xs">{dep.check_out_date}</Text>
                                  </Table.Td>
                                </Table.Tr>
                              ))}
                            </Table.Tbody>
                          </Table>
                        )}
                      </Card>
                    </Grid.Col>
                  </Grid>
                </Stack>
              ) : null}
            </Tabs.Panel>

            {/* TAB 3: EXCEPTIONS & ALERTS */}
            <Tabs.Panel value="exceptions">
              <Stack gap="md">
                {/* No-Shows Table */}
                <Card withBorder radius="md" p="md">
                  <Title order={4} mb="xs">No-Show Exceptions</Title>
                  <Text size="xs" c="dimmed" mb="sm">
                    Guests who failed to check in on their allotted check-in date
                  </Text>
                  {!caretakerReport?.no_show_logs?.length ? (
                    <Alert icon={<FaCheckCircle size={16} />} color="teal">
                      No stay no-shows detected.
                    </Alert>
                  ) : (
                    <Table striped withTableBorder>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Ref</Table.Th>
                          <Table.Th>Visitor</Table.Th>
                          <Table.Th>Room</Table.Th>
                          <Table.Th>Expected Check-In</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {caretakerReport.no_show_logs.map((log) => (
                          <Table.Tr key={log.booking_id}>
                            <Table.Td>
                              <Text fw={600} size="sm">{log.booking_reference}</Text>
                            </Table.Td>
                            <Table.Td>{log.visitor_name}</Table.Td>
                            <Table.Td>
                              <Badge color="orange">Room {log.room_number}</Badge>
                            </Table.Td>
                            <Table.Td>{log.expected_check_in}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  )}
                </Card>

                {/* Overstays Table */}
                <Card withBorder radius="md" p="md">
                  <Title order={4} mb="xs">Overstay Exceptions</Title>
                  <Text size="xs" c="dimmed" mb="sm">
                    Guests remaining in residence past their designated check-out date
                  </Text>
                  {!caretakerReport?.overstay_logs?.length ? (
                    <Alert icon={<FaCheckCircle size={16} />} color="teal">
                      No unauthorized overstays detected.
                    </Alert>
                  ) : (
                    <Table striped withTableBorder>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Ref</Table.Th>
                          <Table.Th>Visitor</Table.Th>
                          <Table.Th>Room</Table.Th>
                          <Table.Th>Expected Check-Out</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {caretakerReport.overstay_logs.map((log) => (
                          <Table.Tr key={log.booking_id}>
                            <Table.Td>
                              <Text fw={600} size="sm">{log.booking_reference}</Text>
                            </Table.Td>
                            <Table.Td>{log.visitor_name}</Table.Td>
                            <Table.Td>
                              <Badge color="red">Room {log.room_number}</Badge>
                            </Table.Td>
                            <Table.Td>{log.expected_check_out}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  )}
                </Card>

                {/* Unresolved Alerts Table */}
                <Card withBorder radius="md" p="md">
                  <Title order={4} mb="xs">Active System Alerts</Title>
                  {!caretakerReport?.unresolved_alerts?.length ? (
                    <Alert icon={<FaCheckCircle size={16} />} color="teal">
                      No unresolved system alerts.
                    </Alert>
                  ) : (
                    <Table striped withTableBorder>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>ID</Table.Th>
                          <Table.Th>Type</Table.Th>
                          <Table.Th>Alert Message</Table.Th>
                          <Table.Th>Timestamp</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {caretakerReport.unresolved_alerts.map((alert) => (
                          <Table.Tr key={alert.id}>
                            <Table.Td>#{alert.id}</Table.Td>
                            <Table.Td>
                              <Badge color="red">{alert.alert_type}</Badge>
                            </Table.Td>
                            <Table.Td>{alert.message}</Table.Td>
                            <Table.Td>
                              <Text size="xs">{new Date(alert.created_at).toLocaleString()}</Text>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  )}
                </Card>
              </Stack>
            </Tabs.Panel>
          </Tabs>
        </Card>
      </Stack>
    </Container>
  );
}
