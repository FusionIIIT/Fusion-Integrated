import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaDoorOpen, FaPlus, FaSignOutAlt } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateGuestRoomBooking,
  useDecideGuestRoomBooking,
  useGuestRooms,
  useHostels,
} from "../api/hooks";
import type { GuestRoomBooking } from "../api/types";

export default function GuestRoomPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: bookingsData, error: bookingsError } = useGuestRooms({ hostel_id: hostelId });

  const createBooking = useCreateGuestRoomBooking();
  const decideBooking = useDecideGuestRoomBooking();

  const [bookingModalOpen, setBookingModalOpen] = useState(false);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState<GuestRoomBooking | null>(null);

  // Form state
  const [guestHostelId, setGuestHostelId] = useState<string | null>(null);
  const [guestName, setGuestName] = useState("");
  const [relationship, setRelationship] = useState("Father");
  const [numGuests, setNumGuests] = useState<number | string>(1);
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [purpose, setPurpose] = useState("");

  // Decision state
  const [decision, setDecision] = useState<string>("approved");
  const [allocatedRoom, setAllocatedRoom] = useState("G-01");
  const [charges, setCharges] = useState<number | string>(500);
  const [decisionRemarks, setDecisionRemarks] = useState("");

  const handleBooking = async () => {
    if (!guestHostelId) return;
    try {
      await createBooking.mutateAsync({
        hostel: Number(guestHostelId),
        guest_name: guestName,
        relationship,
        num_guests: Number(numGuests),
        check_in_date: checkIn,
        check_out_date: checkOut,
        purpose,
      });
      notifications.show({ title: "Success", message: "Guest room booking requested", color: "green" });
      setBookingModalOpen(false);
      setGuestName("");
      setPurpose("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to submit booking", color: "red" });
    }
  };

  const handleDecision = async () => {
    if (!selectedBooking) return;
    try {
      await decideBooking.mutateAsync({
        id: selectedBooking.id,
        decision,
        allocated_room_number: allocatedRoom,
        charges: Number(charges),
        remarks: decisionRemarks,
      });
      notifications.show({ title: "Success", message: `Booking marked as ${decision}`, color: "green" });
      setDecisionModalOpen(false);
      setSelectedBooking(null);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to update booking", color: "red" });
    }
  };

  if (bookingsError) return <Container size="xl"><ErrorState error={bookingsError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const bookings = bookingsData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Guest Rooms"
        subtitle="Manage visitor accommodations, guest house reservations, tariffs, and check-in / check-out cycles"
        action={
          <Button leftSection={<FaPlus size={14} />} onClick={() => setBookingModalOpen(true)}>
            Book Guest Room
          </Button>
        }
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

      <Card withBorder radius="md">
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Student</Table.Th>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Guest Name & Relation</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Room / Tariff</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {bookings.map((b) => (
              <Table.Tr key={b.id}>
                <Table.Td fw={600}>{b.student_name || `Student #${b.student_user_id}`}</Table.Td>
                <Table.Td>{b.hostel_name || `Hostel #${b.hostel}`}</Table.Td>
                <Table.Td>
                  <Text size="sm" fw={600}>{b.guest_name}</Text>
                  <Text size="xs" c="dimmed">{b.relationship} ({b.num_guests} guests)</Text>
                </Table.Td>
                <Table.Td>
                  {b.check_in_date} to {b.check_out_date}
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{b.allocated_room_number ? `Room ${b.allocated_room_number}` : "Not assigned"}</Text>
                  <Text size="xs" c="dimmed">Rs. {b.charges}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={b.status === "checked_in" ? "teal" : b.status === "approved" ? "green" : b.status === "checked_out" ? "gray" : b.status === "pending" ? "yellow" : "red"}>
                    {b.status.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {b.status === "pending" && (
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<FaCheck size={12} />}
                      onClick={() => {
                        setSelectedBooking(b);
                        setDecision("approved");
                        setDecisionModalOpen(true);
                      }}
                    >
                      Review
                    </Button>
                  )}
                  {b.status === "approved" && (
                    <Button
                      size="xs"
                      color="teal"
                      variant="subtle"
                      leftSection={<FaDoorOpen size={12} />}
                      onClick={() => {
                        setSelectedBooking(b);
                        setDecision("checked_in");
                        setDecisionModalOpen(true);
                      }}
                    >
                      Check-In
                    </Button>
                  )}
                  {b.status === "checked_in" && (
                    <Button
                      size="xs"
                      color="gray"
                      variant="subtle"
                      leftSection={<FaSignOutAlt size={12} />}
                      onClick={() => {
                        setSelectedBooking(b);
                        setDecision("checked_out");
                        setDecisionModalOpen(true);
                      }}
                    >
                      Check-Out
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Modal: Book Guest Room */}
      <Modal opened={bookingModalOpen} onClose={() => setBookingModalOpen(false)} title="Guest Room Booking Request" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={guestHostelId}
            onChange={setGuestHostelId}
          />
          <TextInput label="Guest Full Name" placeholder="e.g. Ramesh Kumar Poddar" required value={guestName} onChange={(e) => setGuestName(e.target.value)} />
          <Select
            label="Relationship to Resident"
            required
            data={[
              { value: "Father", label: "Father" },
              { value: "Mother", label: "Mother" },
              { value: "Brother", label: "Brother" },
              { value: "Sister", label: "Sister" },
              { value: "Guardian", label: "Legal Guardian" },
              { value: "Other", label: "Other Family Member" },
            ]}
            value={relationship}
            onChange={(val) => val && setRelationship(val)}
          />
          <NumberInput label="Number of Guests" min={1} max={4} required value={numGuests} onChange={setNumGuests} />
          <Group grow>
            <TextInput label="Check-In Date" type="date" required value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
            <TextInput label="Check-Out Date" type="date" required value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
          </Group>
          <Textarea label="Purpose of Visit" placeholder="Convocation, medical, family visit" required value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setBookingModalOpen(false)}>Cancel</Button>
            <Button loading={createBooking.isPending} onClick={handleBooking}>Submit Request</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Review / Check-In / Check-Out Decision */}
      <Modal opened={decisionModalOpen} onClose={() => setDecisionModalOpen(false)} title={`Guest Room Decision: ${decision.toUpperCase()}`} centered>
        <Stack gap="sm">
          <Text size="sm">
            Booking #{selectedBooking?.id} for {selectedBooking?.guest_name} ({selectedBooking?.relationship})
          </Text>
          <Select
            label="Decision Status"
            required
            data={[
              { value: "approved", label: "Approve Booking" },
              { value: "rejected", label: "Reject Booking" },
              { value: "checked_in", label: "Guest Checked-In" },
              { value: "checked_out", label: "Guest Checked-Out" },
            ]}
            value={decision}
            onChange={(val) => val && setDecision(val)}
          />
          {decision === "approved" && (
            <>
              <TextInput label="Allocated Guest Room Number" placeholder="e.g. G-01" value={allocatedRoom} onChange={(e) => setAllocatedRoom(e.target.value)} />
              <NumberInput label="Tariff Charges (Rs.)" min={0} value={charges} onChange={setCharges} />
            </>
          )}
          <Textarea label="Remarks / Notes" placeholder="Special requirements / receipt info" value={decisionRemarks} onChange={(e) => setDecisionRemarks(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setDecisionModalOpen(false)}>Cancel</Button>
            <Button loading={decideBooking.isPending} onClick={handleDecision}>Confirm Update</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
