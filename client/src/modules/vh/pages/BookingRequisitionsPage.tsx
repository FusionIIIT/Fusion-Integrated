import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Divider,
  Grid,
  Group,
  Loader,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  FaBed,
  FaCalendarCheck,
  FaClipboardCheck,
  FaExclamationCircle,
  FaExclamationTriangle,
  FaFilter,
  FaPrint,
  FaSearch,
} from "react-icons/fa";

import {
  useAllotRoom,
  useBookings,
  useConfirmCancellation,
  useForwardBooking,
  usePrintableBooking,
  useRejectBooking,
  useRoomAvailability,
  useRooms,
} from "../api/hooks";
import type { Booking, BookingStatus } from "../api/types";

function getStatusBadge(status: BookingStatus) {
  switch (status) {
    case "PENDING":
      return <Badge color="yellow" variant="light">Pending Review</Badge>;
    case "FORWARDED":
      return <Badge color="blue" variant="light">Forwarded</Badge>;
    case "APPROVED":
      return <Badge color="teal" variant="light">Approved</Badge>;
    case "ROOM_ALLOTTED":
      return <Badge color="cyan" variant="filled">Room Allotted</Badge>;
    case "CHECKED_IN":
      return <Badge color="green" variant="filled">Checked In</Badge>;
    case "CHECKED_OUT":
      return <Badge color="gray" variant="outline">Checked Out</Badge>;
    case "CANCELLATION_REQUESTED":
      return <Badge color="orange" variant="filled">Cancel Requested</Badge>;
    case "CANCELLED":
      return <Badge color="red" variant="outline">Cancelled</Badge>;
    case "REJECTED":
      return <Badge color="red" variant="light">Rejected</Badge>;
    default:
      return <Badge color="gray">{status}</Badge>;
  }
}

export default function BookingRequisitionsPage() {
  const { data: bookings, isLoading, refetch } = useBookings();
  const { data: allRooms } = useRooms();
  const forwardBooking = useForwardBooking();
  const rejectBooking = useRejectBooking();
  const allotRoom = useAllotRoom();
  const confirmCancellation = useConfirmCancellation();

  // Search and filter
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<string | null>("pending");

  // Action Modals State
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [forwardModalOpen, setForwardModalOpen] = useState(false);
  const [forwardRemarks, setForwardRemarks] = useState("");
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectRemarks, setRejectRemarks] = useState("");
  const [allotModalOpen, setAllotModalOpen] = useState(false);
  const [selectedRoomIds, setSelectedRoomIds] = useState<number[]>([]);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [slipModalOpen, setSlipModalOpen] = useState(false);
  const [viewSlipBookingId, setViewSlipBookingId] = useState<number | null>(null);

  // Availability Checker Widget State
  const [checkInFilter, setCheckInFilter] = useState("");
  const [checkOutFilter, setCheckOutFilter] = useState("");
  const { data: availableRooms, isLoading: loadingAvailability } = useRoomAvailability(
    checkInFilter,
    checkOutFilter,
  );

  const { data: slipData, isLoading: loadingSlip } = usePrintableBooking(viewSlipBookingId || 0);

  // Filter bookings according to active tab and search query
  const filteredBookings = (bookings || []).filter((b) => {
    const matchesQuery =
      b.booking_reference.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.visitor_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.category_code?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.visitor_phone.includes(searchQuery);

    if (!matchesQuery) return false;

    if (activeTab === "pending") return b.status === "PENDING";
    if (activeTab === "allotment") return b.status === "APPROVED";
    if (activeTab === "cancellations") return b.status === "CANCELLATION_REQUESTED";
    if (activeTab === "all") return true;
    return true;
  });

  const pendingCount = (bookings || []).filter((b) => b.status === "PENDING").length;
  const allotmentCount = (bookings || []).filter((b) => b.status === "APPROVED").length;
  const cancellationCount = (bookings || []).filter((b) => b.status === "CANCELLATION_REQUESTED").length;

  // Handlers
  const handleOpenForward = (booking: Booking) => {
    setSelectedBooking(booking);
    setForwardRemarks("");
    setForwardModalOpen(true);
  };

  const handleConfirmForward = async () => {
    if (!selectedBooking) return;
    await forwardBooking.mutateAsync({
      id: selectedBooking.id,
      remarks: forwardRemarks,
    });
    setForwardModalOpen(false);
    setSelectedBooking(null);
  };

  const handleOpenReject = (booking: Booking) => {
    setSelectedBooking(booking);
    setRejectRemarks("");
    setRejectModalOpen(true);
  };

  const handleConfirmReject = async () => {
    if (!selectedBooking) return;
    await rejectBooking.mutateAsync({
      id: selectedBooking.id,
      remarks: rejectRemarks,
    });
    setRejectModalOpen(false);
    setSelectedBooking(null);
  };

  const handleOpenAllot = (booking: Booking) => {
    setSelectedBooking(booking);
    setSelectedRoomIds([]);
    setAllotModalOpen(true);
  };

  const handleConfirmAllot = async () => {
    if (!selectedBooking || selectedRoomIds.length === 0) return;
    await allotRoom.mutateAsync({
      id: selectedBooking.id,
      room_ids: selectedRoomIds,
    });
    setAllotModalOpen(false);
    setSelectedBooking(null);
  };

  const handleOpenCancelConfirm = (booking: Booking) => {
    setSelectedBooking(booking);
    setCancelModalOpen(true);
  };

  const handleConfirmCancellation = async () => {
    if (!selectedBooking) return;
    await confirmCancellation.mutateAsync(selectedBooking.id);
    setCancelModalOpen(false);
    setSelectedBooking(null);
  };

  const handleViewSlip = (bookingId: number) => {
    setViewSlipBookingId(bookingId);
    setSlipModalOpen(true);
  };

  const toggleRoomSelection = (roomId: number) => {
    setSelectedRoomIds((prev) =>
      prev.includes(roomId) ? prev.filter((id) => id !== roomId) : [...prev, roomId],
    );
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Booking Requisitions Management</Title>
            <Text c="dimmed" size="sm">
              Caretaker review queue, room allotment, and cancellation processing (UC-VH-002, UC-VH-004, UC-VH-005)
            </Text>
          </div>
          <Group>
            <Button variant="default" onClick={() => refetch()} leftSection={<FaClipboardCheck />}>
              Refresh
            </Button>
          </Group>
        </Group>

        {/* Quick Stats Banner */}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Pending Review
                </Text>
                <Title order={3}>{pendingCount}</Title>
              </div>
              <FaClipboardCheck size={26} color="#fab005" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Awaiting Allotment
                </Text>
                <Title order={3}>{allotmentCount}</Title>
              </div>
              <FaBed size={26} color="#20c997" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Cancellation Requests
                </Text>
                <Title order={3}>{cancellationCount}</Title>
              </div>
              <FaExclamationCircle size={26} color="#fd7e14" />
            </Group>
          </Paper>
        </SimpleGrid>

        {/* Room Availability Checker Card */}
        <Card withBorder radius="md" p="md" bg="gray.0">
          <Group justify="space-between" mb="xs">
            <Group>
              <FaSearch color="#228be6" />
              <Text fw={600} size="sm">Quick Room Availability Checker</Text>
            </Group>
            {checkInFilter && checkOutFilter && availableRooms && (
              <Badge color="blue" variant="filled">
                {availableRooms.length} Rooms Available
              </Badge>
            )}
          </Group>
          <Grid>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput
                type="date"
                label="Check-In Date"
                size="xs"
                value={checkInFilter}
                onChange={(e) => setCheckInFilter(e.target.value)}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput
                type="date"
                label="Check-Out Date"
                size="xs"
                value={checkOutFilter}
                onChange={(e) => setCheckOutFilter(e.target.value)}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }} style={{ display: "flex", alignItems: "flex-end" }}>
              <Button
                size="xs"
                variant="light"
                onClick={() => {
                  setCheckInFilter("");
                  setCheckOutFilter("");
                }}
              >
                Clear Check
              </Button>
            </Grid.Col>
          </Grid>

          {checkInFilter && checkOutFilter && (
            <div style={{ marginTop: 12 }}>
              {loadingAvailability ? (
                <Loader size="xs" />
              ) : availableRooms && availableRooms.length > 0 ? (
                <Group gap="xs">
                  {availableRooms.map((r) => (
                    <Badge key={r.id} color="teal" variant="light">
                      Room {r.room_number} ({r.room_type})
                    </Badge>
                  ))}
                </Group>
              ) : (
                <Text size="xs" c="red">No rooms available for the selected date range.</Text>
              )}
            </div>
          )}
        </Card>

        {/* Main Tabs and Table */}
        <Card withBorder radius="md" p="md">
          <Tabs value={activeTab} onChange={setActiveTab}>
            <Group justify="space-between" mb="md">
              <Tabs.List>
                <Tabs.Tab value="pending" rightSection={<Badge size="xs" circle color="yellow">{pendingCount}</Badge>}>
                  Pending Review
                </Tabs.Tab>
                <Tabs.Tab value="allotment" rightSection={<Badge size="xs" circle color="teal">{allotmentCount}</Badge>}>
                  Approved & Allotment
                </Tabs.Tab>
                <Tabs.Tab value="cancellations" rightSection={<Badge size="xs" circle color="orange">{cancellationCount}</Badge>}>
                  Cancellation Requests
                </Tabs.Tab>
                <Tabs.Tab value="all">All Requisitions</Tabs.Tab>
              </Tabs.List>

              <TextInput
                placeholder="Search visitor, ref, phone..."
                size="xs"
                leftSection={<FaFilter size={12} />}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </Group>

            <Tabs.Panel value={activeTab || "pending"}>
              {isLoading ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : filteredBookings.length === 0 ? (
                <Alert icon={<FaCalendarCheck size={16} />} title="No requisitions found" color="blue">
                  No bookings found matching current filters.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Reference</Table.Th>
                      <Table.Th>Visitor Details</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Dates (Stay)</Table.Th>
                      <Table.Th>Rooms</Table.Th>
                      <Table.Th>Billing</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {filteredBookings.map((b) => (
                      <Table.Tr key={b.id}>
                        <Table.Td>
                          <Text fw={600} size="sm">{b.booking_reference}</Text>
                          <Text size="xs" c="dimmed">ID: {b.id}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text fw={500} size="sm">{b.visitor_name}</Text>
                          <Text size="xs" c="dimmed">{b.visitor_phone}</Text>
                          <Text size="xs" c="dimmed">{b.visitor_email}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge variant="outline">Cat {b.category_code || b.visitor_category}</Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" fw={500}>{b.check_in_date} to</Text>
                          <Text size="xs" fw={500}>{b.check_out_date}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{b.number_of_rooms} Room(s)</Text>
                          <Text size="xs" c="dimmed">{b.number_of_occupants} Occupant(s)</Text>
                          {b.allotments && b.allotments.length > 0 && (
                            <Group gap={4} mt={2}>
                              {b.allotments.map((a) => (
                                <Badge key={a.id} size="xs" color="cyan">
                                  #{a.room_number}
                                </Badge>
                              ))}
                            </Group>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Badge size="xs" variant="dot">
                            {b.billing_responsibility}
                          </Badge>
                        </Table.Td>
                        <Table.Td>{getStatusBadge(b.status)}</Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            {b.status === "PENDING" && (
                              <>
                                <Button
                                  size="xs"
                                  color="blue"
                                  variant="light"
                                  onClick={() => handleOpenForward(b)}
                                >
                                  Forward
                                </Button>
                                <Button
                                  size="xs"
                                  color="red"
                                  variant="subtle"
                                  onClick={() => handleOpenReject(b)}
                                >
                                  Reject
                                </Button>
                              </>
                            )}

                            {b.status === "APPROVED" && (
                              <Button
                                size="xs"
                                color="teal"
                                leftSection={<FaBed size={12} />}
                                onClick={() => handleOpenAllot(b)}
                              >
                                Allot Room
                              </Button>
                            )}

                            {b.status === "CANCELLATION_REQUESTED" && (
                              <Button
                                size="xs"
                                color="orange"
                                variant="filled"
                                onClick={() => handleOpenCancelConfirm(b)}
                              >
                                Confirm Cancel
                              </Button>
                            )}

                            <Button
                              size="xs"
                              variant="default"
                              onClick={() => handleViewSlip(b.id)}
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
          </Tabs>
        </Card>
      </Stack>

      {/* Forward Requisition Modal */}
      <Modal
        opened={forwardModalOpen}
        onClose={() => setForwardModalOpen(false)}
        title={<Text fw={600}>Forward Booking to VH In-Charge</Text>}
      >
        <Stack gap="md">
          <Text size="sm">
            Forward booking requisition <b>{selectedBooking?.booking_reference}</b> ({selectedBooking?.visitor_name}) to the VH In-Charge for administrative approval.
          </Text>
          <Textarea
            label="Caretaker Remarks (Optional)"
            placeholder="Add operational notes or room suitability remarks..."
            value={forwardRemarks}
            onChange={(e) => setForwardRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setForwardModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="blue"
              loading={forwardBooking.isPending}
              onClick={handleConfirmForward}
            >
              Forward Booking
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Reject Requisition Modal */}
      <Modal
        opened={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title={<Text fw={600} c="red">Reject Booking Requisition</Text>}
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to reject requisition <b>{selectedBooking?.booking_reference}</b>?
          </Text>
          <Textarea
            required
            label="Rejection Reason"
            placeholder="Provide explicit reason for requisition rejection..."
            value={rejectRemarks}
            onChange={(e) => setRejectRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRejectModalOpen(false)}>
              Back
            </Button>
            <Button
              color="red"
              loading={rejectBooking.isPending}
              disabled={!rejectRemarks.trim()}
              onClick={handleConfirmReject}
            >
              Confirm Reject
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Room Allotment Modal */}
      <Modal
        opened={allotModalOpen}
        onClose={() => setAllotModalOpen(false)}
        title={<Text fw={600}>Allot Rooms ({selectedBooking?.booking_reference})</Text>}
        size="lg"
      >
        <Stack gap="md">
          <Text size="sm">
            Allot <b>{selectedBooking?.number_of_rooms}</b> room(s) for <b>{selectedBooking?.visitor_name}</b> (Dates: {selectedBooking?.check_in_date} to {selectedBooking?.check_out_date}).
          </Text>

          <Text size="xs" fw={700} c="dimmed" tt="uppercase">
            Available Rooms
          </Text>

          <SimpleGrid cols={2} spacing="xs">
            {(allRooms || [])
              .filter((r) => r.status === "AVAILABLE")
              .map((room) => {
                const isSelected = selectedRoomIds.includes(room.id);
                return (
                  <Paper
                    key={room.id}
                    withBorder
                    p="xs"
                    radius="sm"
                    style={{
                      cursor: "pointer",
                      borderColor: isSelected ? "#228be6" : undefined,
                      backgroundColor: isSelected ? "#e7f5ff" : undefined,
                    }}
                    onClick={() => toggleRoomSelection(room.id)}
                  >
                    <Group justify="space-between">
                      <Group gap="xs">
                        <Checkbox checked={isSelected} readOnly />
                        <div>
                          <Text fw={600} size="sm">Room {room.room_number}</Text>
                          <Text size="xs" c="dimmed">
                            {room.room_type} • Floor {room.floor}
                          </Text>
                        </div>
                      </Group>
                      <Badge size="xs" color="teal">Available</Badge>
                    </Group>
                  </Paper>
                );
              })}
          </SimpleGrid>

          <Text size="xs" c="dimmed">
            Selected: {selectedRoomIds.length} of {selectedBooking?.number_of_rooms} required.
          </Text>

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setAllotModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="teal"
              loading={allotRoom.isPending}
              disabled={selectedRoomIds.length === 0}
              onClick={handleConfirmAllot}
            >
              Confirm Allotment
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Confirm Cancellation Modal */}
      <Modal
        opened={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title={<Text fw={600} c="orange">Confirm Cancellation</Text>}
      >
        <Stack gap="md">
          <Alert icon={<FaExclamationTriangle size={16} />} color="orange">
            The indenter requested cancellation. Reason: &quot;{selectedBooking?.cancellation_reason}&quot;.
          </Alert>
          <Text size="sm">
            Confirming cancellation will finalize the booking state as <b>CANCELLED</b>, release allotted rooms, and calculate the applicable cancellation charge.
          </Text>
          {selectedBooking?.calculated_cancellation_charge && (
            <Paper p="xs" withBorder>
              <Text size="sm" fw={600}>
                Estimated Cancellation Charge: ₹{selectedBooking.calculated_cancellation_charge}
              </Text>
            </Paper>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="orange"
              loading={confirmCancellation.isPending}
              onClick={handleConfirmCancellation}
            >
              Confirm and Process Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Printable Booking Slip Modal */}
      <Modal
        opened={slipModalOpen}
        onClose={() => setSlipModalOpen(false)}
        title={<Text fw={600}>Visitors Hostel Booking Slip</Text>}
        size="lg"
      >
        {loadingSlip ? (
          <Group justify="center" p="xl">
            <Loader size="md" />
          </Group>
        ) : slipData ? (
          <Stack gap="md">
            <Paper withBorder p="md" radius="sm">
              <Group justify="space-between" mb="xs">
                <div>
                  <Title order={4}>{slipData.title}</Title>
                  <Text size="xs" c="dimmed">Generated on {slipData.generated_at}</Text>
                </div>
                {getStatusBadge(slipData.status)}
              </Group>
              <Divider my="sm" />
              <Grid>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Booking Reference:</Text>
                  <Text fw={600}>{slipData.booking_reference}</Text>
                </Grid.Col>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Visitor Name:</Text>
                  <Text fw={600}>{slipData.visitor_name}</Text>
                </Grid.Col>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Stay Period:</Text>
                  <Text>{slipData.check_in_date} to {slipData.check_out_date}</Text>
                </Grid.Col>
                <Grid.Col span={6}>
                  <Text size="xs" c="dimmed">Category / Billing:</Text>
                  <Text>{slipData.category} • {slipData.billing_responsibility}</Text>
                </Grid.Col>
                <Grid.Col span={12}>
                  <Text size="xs" c="dimmed">Allotted Rooms:</Text>
                  <Text fw={500}>
                    {slipData.allotted_rooms && slipData.allotted_rooms.length > 0
                      ? slipData.allotted_rooms.join(", ")
                      : "Pending Allotment"}
                  </Text>
                </Grid.Col>
              </Grid>
            </Paper>

            <Group justify="flex-end">
              <Button variant="default" onClick={() => window.print()}>
                Print Slip
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
