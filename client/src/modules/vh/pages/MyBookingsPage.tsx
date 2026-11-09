import {
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Grid,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useState } from "react";
import { FaEdit, FaFileInvoice, FaPlus, FaPrint, FaTimes } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import {
  useBookings,
  useCreateModification,
  usePrintableBooking,
  useRequestCancellation,
} from "../api/hooks";
import type { Booking, BookingStatus } from "../api/types";

function getStatusBadgeColor(status: BookingStatus) {
  switch (status) {
    case "PENDING":
      return "yellow";
    case "FORWARDED":
      return "blue";
    case "APPROVED":
      return "teal";
    case "ROOM_ALLOTTED":
      return "cyan";
    case "CHECKED_IN":
      return "green";
    case "CHECKED_OUT":
      return "gray";
    case "CANCELLATION_REQUESTED":
      return "orange";
    case "CANCELLED":
    case "REJECTED":
      return "red";
    default:
      return "gray";
  }
}

export default function MyBookingsPage() {
  const navigate = useNavigate();
  const { data: bookings, isLoading } = useBookings();
  const requestCancellation = useRequestCancellation();
  const createModification = useCreateModification();

  // Modals state
  const [selectedBookingId, setSelectedBookingId] = useState<number | null>(null);
  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [modifyModalOpen, setModifyModalOpen] = useState(false);
  const [modCheckIn, setModCheckIn] = useState("");
  const [modCheckOut, setModCheckOut] = useState("");
  const [modRooms, setModRooms] = useState<number | string>(1);
  const [modReason, setModReason] = useState("");

  const { data: slipData, isLoading: loadingSlip } = usePrintableBooking(selectedBookingId || 0);

  const handleOpenPrint = (id: number) => {
    setSelectedBookingId(id);
    setPrintModalOpen(true);
  };

  const handleOpenCancel = (booking: Booking) => {
    setSelectedBookingId(booking.id);
    setCancelReason("");
    setCancelModalOpen(true);
  };

  const handleOpenModify = (booking: Booking) => {
    setSelectedBookingId(booking.id);
    setModCheckIn(booking.check_in_date);
    setModCheckOut(booking.check_out_date);
    setModRooms(booking.number_of_rooms);
    setModReason("");
    setModifyModalOpen(true);
  };

  const handleConfirmCancelRequest = async () => {
    if (!selectedBookingId) return;
    await requestCancellation.mutateAsync({
      id: selectedBookingId,
      reason: cancelReason,
    });
    setCancelModalOpen(false);
  };

  const handleConfirmModifyRequest = async () => {
    if (!selectedBookingId) return;
    await createModification.mutateAsync({
      booking: selectedBookingId,
      new_check_in_date: modCheckIn || undefined,
      new_check_out_date: modCheckOut || undefined,
      new_number_of_rooms: Number(modRooms) || undefined,
      reason: modReason,
    });
    setModifyModalOpen(false);
  };

  return (
    <Container size="xl" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>My Submitted Bookings</Title>
          <Text c="dimmed" size="sm">
            Track requisition status, view and print confirmation slips, or request modifications and cancellations (UC-VH-002)
          </Text>
        </div>
        <Button leftSection={<FaPlus />} onClick={() => navigate("/vh/request")}>
          New Booking Requisition
        </Button>
      </Group>

      <Card withBorder radius="md" p="md">
        {isLoading ? (
          <Group justify="center" p="xl">
            <Loader />
          </Group>
        ) : !bookings || bookings.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            You have no submitted bookings yet. Click &ldquo;New Booking Requisition&rdquo; to book accommodation.
          </Text>
        ) : (
          <Table.ScrollContainer minWidth={900}>
            <Table verticalSpacing="sm" striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Booking Ref</Table.Th>
                  <Table.Th>Visitor Name</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Rooms</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Allotted Room(s)</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bookings.map((b) => {
                  const canCancel = !["CHECKED_IN", "CHECKED_OUT", "CANCELLED", "CANCELLATION_REQUESTED"].includes(b.status);
                  const canModify = !["CHECKED_IN", "CHECKED_OUT", "CANCELLED"].includes(b.status);
                  const roomsStr = b.allotments?.map((a) => a.room_number).join(", ") || "-";

                  return (
                    <Table.Tr key={b.id}>
                      <Table.Td>
                        <Text fw={500} size="sm">
                          {b.booking_reference}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{b.visitor_name}</Text>
                        <Text size="xs" c="dimmed">{b.visitor_phone || b.visitor_email}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{b.check_in_date} to {b.check_out_date}</Text>
                      </Table.Td>
                      <Table.Td>{b.number_of_rooms}</Table.Td>
                      <Table.Td>
                        <Badge color={getStatusBadgeColor(b.status)} variant="light">
                          {b.status.replace("_", " ")}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{roomsStr}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<FaPrint size={12} />}
                            onClick={() => handleOpenPrint(b.id)}
                          >
                            Slip
                          </Button>
                          {canModify && (
                            <Button
                              size="xs"
                              variant="subtle"
                              color="blue"
                              leftSection={<FaEdit size={12} />}
                              onClick={() => handleOpenModify(b)}
                            >
                              Modify
                            </Button>
                          )}
                          {canCancel && (
                            <Button
                              size="xs"
                              variant="subtle"
                              color="red"
                              leftSection={<FaTimes size={12} />}
                              onClick={() => handleOpenCancel(b)}
                            >
                              Cancel
                            </Button>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>

      {/* Printable Confirmation Slip Modal (UC-VH-002, AFR-VH-003) */}
      <Modal
        opened={printModalOpen}
        onClose={() => setPrintModalOpen(false)}
        title="Official Visitors Hostel Confirmation Slip"
        size="lg"
      >
        {loadingSlip || !slipData ? (
          <Group justify="center" p="xl"><Loader /></Group>
        ) : (
          <Paper p="md" withBorder>
            <Stack gap="xs">
              <Title order={4} ta="center" c="blue">{slipData.title}</Title>
              <Divider my="xs" />
              <Grid>
                <Grid.Col span={6}><Text size="sm" fw={700}>Booking Ref:</Text> <Text size="sm">{slipData.booking_reference}</Text></Grid.Col>
                <Grid.Col span={6}><Text size="sm" fw={700}>Status:</Text> <Badge color={getStatusBadgeColor(slipData.status)}>{slipData.status}</Badge></Grid.Col>
                <Grid.Col span={6}><Text size="sm" fw={700}>Visitor Name:</Text> <Text size="sm">{slipData.visitor_name}</Text></Grid.Col>
                <Grid.Col span={6}><Text size="sm" fw={700}>Category:</Text> <Text size="sm">{slipData.category}</Text></Grid.Col>
                <Grid.Col span={6}><Text size="sm" fw={700}>Check-In Date:</Text> <Text size="sm">{slipData.check_in_date}</Text></Grid.Col>
                <Grid.Col span={6}><Text size="sm" fw={700}>Check-Out Date:</Text> <Text size="sm">{slipData.check_out_date}</Text></Grid.Col>
                <Grid.Col span={6}><Text size="sm" fw={700}>Rooms Requested:</Text> <Text size="sm">{slipData.number_of_rooms}</Text></Grid.Col>
                <Grid.Col span={6}><Text size="sm" fw={700}>Allotted Rooms:</Text> <Text size="sm">{slipData.allotted_rooms?.join(", ") || "Awaiting Allotment"}</Text></Grid.Col>
                <Grid.Col span={12}><Text size="sm" fw={700}>Visit Purpose:</Text> <Text size="sm">{slipData.visit_purpose}</Text></Grid.Col>
                <Grid.Col span={12}><Text size="sm" fw={700}>Billing Responsibility:</Text> <Text size="sm">{slipData.billing_responsibility}</Text></Grid.Col>
              </Grid>
              {slipData.bill && (
                <Paper withBorder p="xs" mt="sm" bg="gray.0">
                  <Text size="sm" fw={700}><FaFileInvoice /> Billing Details:</Text>
                  <Text size="xs">Room: Rs {slipData.bill.room_charges} | Meals: Rs {slipData.bill.meal_charges} | Total: Rs {slipData.bill.total_amount} ({slipData.bill.is_settled ? "Settled in Cash" : "Pending Settlement"})</Text>
                </Paper>
              )}
              <Group justify="flex-end" mt="md">
                <Button variant="default" onClick={() => window.print()}>Print / Save PDF</Button>
                <Button onClick={() => setPrintModalOpen(false)}>Close</Button>
              </Group>
            </Stack>
          </Paper>
        )}
      </Modal>

      {/* Cancellation Request Modal (UC-VH-007, BR-VH-006..009) */}
      <Modal
        opened={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Request Booking Cancellation"
      >
        <Stack gap="sm">
          <Text size="sm">
            Cancellation charges will be computed according to the institute notice schedule:
            <br />• 7 or more days prior: <b>0% fee</b>
            <br />• Within 7 days: <b>25% of one-day rent</b>
            <br />• Same day or after: <b>50% of one-day rent</b>
          </Text>
          <Textarea
            label="Reason for Cancellation"
            placeholder="Please specify reason"
            required
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCancelModalOpen(false)}>Back</Button>
            <Button color="red" loading={requestCancellation.isPending} onClick={handleConfirmCancelRequest}>
              Confirm Request Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modification Request Modal (UC-VH-006, BR-VH-010) */}
      <Modal
        opened={modifyModalOpen}
        onClose={() => setModifyModalOpen(false)}
        title="Request Booking Modification"
      >
        <Stack gap="sm">
          <TextInput
            label="New Check-In Date"
            type="date"
            value={modCheckIn}
            onChange={(e) => setModCheckIn(e.target.value)}
          />
          <TextInput
            label="New Check-Out Date"
            type="date"
            value={modCheckOut}
            onChange={(e) => setModCheckOut(e.target.value)}
          />
          <NumberInput
            label="New Number of Rooms"
            min={1}
            max={10}
            value={modRooms}
            onChange={setModRooms}
          />
          <Textarea
            label="Modification Reason"
            placeholder="Explain why dates/rooms need changing"
            required
            value={modReason}
            onChange={(e) => setModReason(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModifyModalOpen(false)}>Back</Button>
            <Button loading={createModification.isPending} onClick={handleConfirmModifyRequest}>
              Submit Modification Request
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}

