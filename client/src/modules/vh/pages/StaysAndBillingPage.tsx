import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Loader,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  FaBed,
  FaCalendarCheck,
  FaCheckCircle,
  FaFileInvoiceDollar,
  FaMoneyBillWave,
  FaPrint,
  FaReceipt,
  FaSignInAlt,
  FaSignOutAlt,
} from "react-icons/fa";

import {
  useBills,
  useBookings,
  useCheckIn,
  useCheckOut,
  usePrintableBooking,
  useSettleBill,
} from "../api/hooks";
import type { Bill } from "../api/types";

export default function StaysAndBillingPage() {
  const { data: bookings, isLoading: loadingBookings, refetch: refetchBookings } = useBookings();
  const { data: bills, isLoading: loadingBills, refetch: refetchBills } = useBills();

  const checkIn = useCheckIn();
  const checkOut = useCheckOut();
  const settleBill = useSettleBill();

  const [activeTab, setActiveTab] = useState<string | null>("stays");
  const [stayFilter, setStayFilter] = useState<"allotted" | "checked_in" | "all">("checked_in");

  // Settlement Modal State
  const [selectedBill, setSelectedBill] = useState<Bill | null>(null);
  const [settleModalOpen, setSettleModalOpen] = useState(false);
  const [settleNotes, setSettleNotes] = useState("");

  // Printable slip state
  const [slipModalOpen, setSlipModalOpen] = useState(false);
  const [viewBookingId, setViewBookingId] = useState<number | null>(null);
  const { data: slipData, isLoading: loadingSlip } = usePrintableBooking(viewBookingId || 0);

  // Filter bookings for stays
  const allottedBookings = (bookings || []).filter((b) => b.status === "ROOM_ALLOTTED");
  const checkedInBookings = (bookings || []).filter((b) => b.status === "CHECKED_IN");

  const displayedStays = (bookings || []).filter((b) => {
    if (stayFilter === "allotted") return b.status === "ROOM_ALLOTTED";
    if (stayFilter === "checked_in") return b.status === "CHECKED_IN";
    return b.status === "ROOM_ALLOTTED" || b.status === "CHECKED_IN" || b.status === "CHECKED_OUT";
  });

  // Calculate bill metrics
  const totalSettled = (bills || [])
    .filter((b) => b.is_settled)
    .reduce((sum, b) => sum + parseFloat(b.total_amount || "0"), 0);

  const totalPending = (bills || [])
    .filter((b) => !b.is_settled)
    .reduce((sum, b) => sum + parseFloat(b.total_amount || "0"), 0);

  // Actions
  const handleCheckIn = async (bookingId: number) => {
    await checkIn.mutateAsync(bookingId);
  };

  const handleCheckOut = async (bookingId: number) => {
    await checkOut.mutateAsync(bookingId);
  };

  const handleOpenSettle = (bill: Bill) => {
    setSelectedBill(bill);
    setSettleNotes("Cash settlement verified with guest signature.");
    setSettleModalOpen(true);
  };

  const handleConfirmSettle = async () => {
    if (!selectedBill) return;
    await settleBill.mutateAsync({
      id: selectedBill.id,
      notes: settleNotes,
    });
    setSettleModalOpen(false);
    setSelectedBill(null);
  };

  const handleOpenSlip = (bookingId: number) => {
    setViewBookingId(bookingId);
    setSlipModalOpen(true);
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Stays & Billing Management</Title>
            <Text c="dimmed" size="sm">
              Operational check-in, check-out, bill generation, and cash settlement (UC-VH-006, UC-VH-008, BR-VH-006)
            </Text>
          </div>
          <Group>
            <Button
              variant="default"
              onClick={() => {
                refetchBookings();
                refetchBills();
              }}
              leftSection={<FaReceipt />}
            >
              Refresh
            </Button>
          </Group>
        </Group>

        {/* Overview Stats */}
        <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="md">
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Currently Checked In
                </Text>
                <Title order={3}>{checkedInBookings.length}</Title>
              </div>
              <FaBed size={26} color="#40c057" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Awaiting Check-In
                </Text>
                <Title order={3}>{allottedBookings.length}</Title>
              </div>
              <FaSignInAlt size={26} color="#228be6" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Settled Revenue
                </Text>
                <Title order={3}>₹{totalSettled.toFixed(2)}</Title>
              </div>
              <FaMoneyBillWave size={26} color="#12b886" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Pending Settlement
                </Text>
                <Title order={3}>₹{totalPending.toFixed(2)}</Title>
              </div>
              <FaFileInvoiceDollar size={26} color="#fa5252" />
            </Group>
          </Paper>
        </SimpleGrid>

        {/* Tabs: Stays Management & Bills */}
        <Card withBorder radius="md" p="md">
          <Tabs value={activeTab} onChange={setActiveTab}>
            <Tabs.List mb="md">
              <Tabs.Tab
                value="stays"
                leftSection={<FaBed size={14} />}
                rightSection={<Badge size="xs" circle color="green">{checkedInBookings.length}</Badge>}
              >
                Guest Stays & Operations
              </Tabs.Tab>
              <Tabs.Tab
                value="bills"
                leftSection={<FaReceipt size={14} />}
                rightSection={<Badge size="xs" circle color="blue">{(bills || []).length}</Badge>}
              >
                Hostel Bills & Settlements
              </Tabs.Tab>
            </Tabs.List>

            {/* Stays Tab */}
            <Tabs.Panel value="stays">
              {/* Filter Sub-nav */}
              <Group mb="md" justify="space-between">
                <Group>
                  <Button
                    size="xs"
                    variant={stayFilter === "checked_in" ? "filled" : "default"}
                    color="green"
                    onClick={() => setStayFilter("checked_in")}
                  >
                    Checked In ({checkedInBookings.length})
                  </Button>
                  <Button
                    size="xs"
                    variant={stayFilter === "allotted" ? "filled" : "default"}
                    color="blue"
                    onClick={() => setStayFilter("allotted")}
                  >
                    Awaiting Check-In ({allottedBookings.length})
                  </Button>
                  <Button
                    size="xs"
                    variant={stayFilter === "all" ? "filled" : "default"}
                    onClick={() => setStayFilter("all")}
                  >
                    All Stays
                  </Button>
                </Group>
              </Group>

              {loadingBookings ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : displayedStays.length === 0 ? (
                <Alert icon={<FaCalendarCheck size={16} />} title="No active stays" color="blue">
                  No guest stays found under selected filter.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Booking Ref</Table.Th>
                      <Table.Th>Visitor & Contact</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Stay Dates</Table.Th>
                      <Table.Th>Allotted Room(s)</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {displayedStays.map((b) => (
                      <Table.Tr key={b.id}>
                        <Table.Td>
                          <Text fw={600} size="sm">{b.booking_reference}</Text>
                          <Text size="xs" c="dimmed">{b.billing_responsibility}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text fw={600} size="sm">{b.visitor_name}</Text>
                          <Text size="xs" c="dimmed">{b.visitor_phone}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge variant="outline">Cat {b.category_code || b.visitor_category}</Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" fw={500}>{b.check_in_date} to</Text>
                          <Text size="xs" fw={500}>{b.check_out_date}</Text>
                        </Table.Td>
                        <Table.Td>
                          {b.allotments && b.allotments.length > 0 ? (
                            <Group gap={4}>
                              {b.allotments.map((a) => (
                                <Badge
                                  key={a.id}
                                  size="sm"
                                  color={a.is_overstay ? "red" : a.is_no_show ? "orange" : "teal"}
                                >
                                  Room {a.room_number}
                                </Badge>
                              ))}
                            </Group>
                          ) : (
                            <Text size="xs" c="dimmed">Not Allotted</Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            color={
                              b.status === "CHECKED_IN"
                                ? "green"
                                : b.status === "ROOM_ALLOTTED"
                                ? "cyan"
                                : "gray"
                            }
                          >
                            {b.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            {b.status === "ROOM_ALLOTTED" && (
                              <Button
                                size="xs"
                                color="green"
                                leftSection={<FaSignInAlt size={12} />}
                                loading={checkIn.isPending}
                                onClick={() => handleCheckIn(b.id)}
                              >
                                Check In
                              </Button>
                            )}

                            {b.status === "CHECKED_IN" && (
                              <Button
                                size="xs"
                                color="orange"
                                leftSection={<FaSignOutAlt size={12} />}
                                loading={checkOut.isPending}
                                onClick={() => handleCheckOut(b.id)}
                              >
                                Check Out
                              </Button>
                            )}

                            <Button
                              size="xs"
                              variant="default"
                              onClick={() => handleOpenSlip(b.id)}
                            >
                              <FaPrint size={12} />
                            </Button>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>

            {/* Bills Tab */}
            <Tabs.Panel value="bills">
              {loadingBills ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : (bills || []).length === 0 ? (
                <Alert icon={<FaReceipt size={16} />} title="No bills found" color="blue">
                  No hostel bills have been generated yet. Check out a guest to generate a bill.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Bill ID</Table.Th>
                      <Table.Th>Booking Ref</Table.Th>
                      <Table.Th>Room Charges</Table.Th>
                      <Table.Th>Meal Charges</Table.Th>
                      <Table.Th>Cancellation</Table.Th>
                      <Table.Th>Total Amount</Table.Th>
                      <Table.Th>Settlement Status</Table.Th>
                      <Table.Th>Settled At</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(bills || []).map((bill) => (
                      <Table.Tr key={bill.id}>
                        <Table.Td>
                          <Text fw={600} size="sm">#{bill.id}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text fw={500} size="sm">{bill.booking_reference}</Text>
                        </Table.Td>
                        <Table.Td>₹{bill.room_charges}</Table.Td>
                        <Table.Td>₹{bill.meal_charges}</Table.Td>
                        <Table.Td>₹{bill.cancellation_charges}</Table.Td>
                        <Table.Td>
                          <Text fw={700} size="sm" c="blue">
                            ₹{bill.total_amount}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            color={bill.is_settled ? "teal" : "red"}
                            variant={bill.is_settled ? "filled" : "outline"}
                          >
                            {bill.is_settled ? "SETTLED" : "PENDING"}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">
                            {bill.settled_at ? new Date(bill.settled_at).toLocaleString() : "—"}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          {!bill.is_settled ? (
                            <Button
                              size="xs"
                              color="teal"
                              leftSection={<FaMoneyBillWave size={12} />}
                              onClick={() => handleOpenSettle(bill)}
                            >
                              Settle Cash
                            </Button>
                          ) : (
                            <Group gap="xs">
                              <FaCheckCircle size={14} color="#12b886" />
                              <Text size="xs" c="teal" fw={500}>Finalized</Text>
                            </Group>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>
          </Tabs>
        </Card>
      </Stack>

      {/* Settle Bill Modal */}
      <Modal
        opened={settleModalOpen}
        onClose={() => setSettleModalOpen(false)}
        title={<Text fw={600}>Settle Hostel Bill #{selectedBill?.id}</Text>}
      >
        <Stack gap="md">
          <Paper withBorder p="md" bg="gray.0">
            <Group justify="space-between" mb="xs">
              <Text size="sm" c="dimmed">Booking Reference:</Text>
              <Text fw={600}>{selectedBill?.booking_reference}</Text>
            </Group>
            <Group justify="space-between" mb="xs">
              <Text size="sm" c="dimmed">Room Charges:</Text>
              <Text>₹{selectedBill?.room_charges}</Text>
            </Group>
            <Group justify="space-between" mb="xs">
              <Text size="sm" c="dimmed">Meal Charges:</Text>
              <Text>₹{selectedBill?.meal_charges}</Text>
            </Group>
            {selectedBill?.cancellation_charges !== "0.00" && (
              <Group justify="space-between" mb="xs">
                <Text size="sm" c="dimmed">Cancellation Charges:</Text>
                <Text>₹{selectedBill?.cancellation_charges}</Text>
              </Group>
            )}
            <Divider my="xs" />
            <Group justify="space-between">
              <Text fw={700}>Total Payable:</Text>
              <Text fw={700} size="lg" c="blue">
                ₹{selectedBill?.total_amount}
              </Text>
            </Group>
          </Paper>

          <Textarea
            required
            label="Guest Verification Notes"
            placeholder="E.g., Cash collected, verified against official receipt."
            value={settleNotes}
            onChange={(e) => setSettleNotes(e.target.value)}
          />

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSettleModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="teal"
              loading={settleBill.isPending}
              disabled={!settleNotes.trim()}
              onClick={handleConfirmSettle}
            >
              Mark Bill as Settled
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Slip Modal */}
      <Modal
        opened={slipModalOpen}
        onClose={() => setSlipModalOpen(false)}
        title={<Text fw={600}>Booking & Stay Slip</Text>}
      >
        {loadingSlip ? (
          <Group justify="center" p="xl">
            <Loader size="md" />
          </Group>
        ) : slipData ? (
          <Stack gap="sm">
            <Text fw={600}>{slipData.title}</Text>
            <Text size="sm">Ref: <b>{slipData.booking_reference}</b></Text>
            <Text size="sm">Visitor: {slipData.visitor_name} ({slipData.visitor_phone})</Text>
            <Text size="sm">Dates: {slipData.check_in_date} to {slipData.check_out_date}</Text>
            <Text size="sm">Rooms: {slipData.allotted_rooms?.join(", ") || "None"}</Text>
            <Text size="sm">Billing: {slipData.billing_responsibility}</Text>
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => window.print()}>
                Print
              </Button>
              <Button color="blue" onClick={() => setSlipModalOpen(false)}>
                Close
              </Button>
            </Group>
          </Stack>
        ) : null}
      </Modal>
    </Container>
  );
}
