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
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaPlus, FaBed } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useGuestBookingDecision,
  useGuestBookings,
  useHostels,
  useRooms,
  useSubmitGuestBooking,
} from "../api/hooks";
import type { GuestRoomBooking } from "../api/types";

export default function GuestRoomPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string | null>("all");

  const {
    data: bookings,
    isPending,
    error,
  } = useGuestBookings({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
    status: activeTab !== "all" ? activeTab! : undefined,
  });

  const submitMutation = useSubmitGuestBooking();
  const decisionMutation = useGuestBookingDecision();

  // Booking modal
  const [bookModalOpen, setBookModalOpen] = useState(false);
  const [bHostelId, setBHostelId] = useState<string | null>(null);
  const [bGuestName, setBGuestName] = useState("");
  const [bRelation, setBRelation] = useState<string | null>("Parents");
  const [bGender, setBGender] = useState<string | null>("male");
  const [bCheckIn, setBCheckIn] = useState("");
  const [bCheckOut, setBCheckOut] = useState("");
  const [bNumGuests, setBNumGuests] = useState<number | string>(1);
  const [bReason, setBReason] = useState("");

  // Decision modal
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState<GuestRoomBooking | null>(null);
  const [decisionType, setDecisionType] = useState<"approved" | "rejected">("approved");
  const [assignedRoomId, setAssignedRoomId] = useState<string | null>(null);
  const [decisionRemarks, setDecisionRemarks] = useState("");

  // Rooms for assigned hostel
  const { data: rooms } = useRooms({
    hostel_id: selectedBooking ? selectedBooking.hostel : undefined,
  });

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleBook = async () => {
    if (!bHostelId || !bGuestName || !bCheckIn || !bCheckOut) return;
    await submitMutation.mutateAsync({
      hostel: Number(bHostelId),
      guest_name: bGuestName,
      guest_relation: bRelation || "Relative",
      guest_gender: bGender || "other",
      check_in_date: bCheckIn,
      check_out_date: bCheckOut,
      number_of_guests: Number(bNumGuests) || 1,
      reason: bReason,
    });
    setBookModalOpen(false);
    setBGuestName("");
    setBCheckIn("");
    setBCheckOut("");
    setBReason("");
  };

  const handleDecision = async () => {
    if (!selectedBooking) return;
    await decisionMutation.mutateAsync({
      id: selectedBooking.id,
      decision: decisionType,
      assigned_room_id: decisionType === "approved" && assignedRoomId ? Number(assignedRoomId) : undefined,
      remarks: decisionRemarks,
    });
    setDecisionModalOpen(false);
    setDecisionRemarks("");
    setAssignedRoomId(null);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "requested":
        return <Badge color="blue">Requested</Badge>;
      case "approved":
        return <Badge color="teal">Approved</Badge>;
      case "rejected":
        return <Badge color="red">Rejected</Badge>;
      case "cancelled":
        return <Badge color="gray">Cancelled</Badge>;
      default:
        return <Badge color="gray">{status}</Badge>;
    }
  };

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Hostel Guest Room Management"
          subtitle="Process guest room booking requests, verify eligibility, and allocate rooms"
          action={
            <Button
              leftSection={<FaPlus />}
              onClick={() => {
                if (hostels && hostels.length > 0 && hostels[0]) {
                  setBHostelId(String(hostels[0].id));
                }
                setBookModalOpen(true);
              }}
            >
              Book Guest Room
            </Button>
          }
        />

        <Card withBorder radius="md">
          <Group justify="space-between" mb="md">
            <Select
              placeholder="Filter by hostel"
              clearable
              value={selectedHostel}
              onChange={setSelectedHostel}
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              style={{ width: 280 }}
            />

            <Tabs value={activeTab} onChange={setActiveTab}>
              <Tabs.List>
                <Tabs.Tab value="all">All Requests</Tabs.Tab>
                <Tabs.Tab value="requested">Pending Decision</Tabs.Tab>
                <Tabs.Tab value="approved">Approved</Tabs.Tab>
                <Tabs.Tab value="rejected">Rejected</Tabs.Tab>
              </Tabs.List>
            </Tabs>
          </Group>

          <DataTable<GuestRoomBooking>
            rows={bookings || []}
            loading={isPending}
            rowKey={(r) => r.id}
            columns={[
              {
                key: "id",
                header: "ID",
                render: (r) => <Text size="sm" fw={600}>#{r.id}</Text>,
              },
              {
                key: "hostel",
                header: "Hostel & Room",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm" fw={500}>{r.hostel_name}</Text>
                    <Text size="xs" c="dimmed">
                      {r.assigned_room_number ? `Room ${r.assigned_room_number}` : "Room not assigned"}
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "student",
                header: "Requested By",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm">{r.student_name || "Unknown"}</Text>
                    <Text size="xs" c="dimmed">{r.student_roll_number}</Text>
                  </Stack>
                ),
              },
              {
                key: "guest",
                header: "Guest Details",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm" fw={500}>{r.guest_name} ({r.guest_relation})</Text>
                    <Text size="xs" c="dimmed">
                      {r.number_of_guests} guest(s) • {r.guest_gender}
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "dates",
                header: "Stay Period",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="xs" fw={500}>{r.check_in_date} to {r.check_out_date}</Text>
                    <Text size="xs" c="dimmed">{r.reason || "No remarks"}</Text>
                  </Stack>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (r) => getStatusBadge(r.status),
              },
              {
                key: "actions",
                header: "Actions",
                render: (r) => (
                  <Group gap="xs">
                    {r.status === "requested" && (
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<FaBed />}
                        onClick={() => {
                          setSelectedBooking(r);
                          setDecisionType("approved");
                          setDecisionRemarks("");
                          setAssignedRoomId(null);
                          setDecisionModalOpen(true);
                        }}
                      >
                        Review
                      </Button>
                    )}
                  </Group>
                ),
              },
            ]}
            empty={{
              title: "No Guest Bookings",
              description: "No guest room bookings match the current filter.",
            }}
          />
        </Card>

        {/* Modal: Book Guest Room */}
        <Modal
          opened={bookModalOpen}
          onClose={() => setBookModalOpen(false)}
          title="Request Guest Room Booking"
          size="lg"
        >
          <Stack gap="sm">
            <Select
              label="Hostel"
              required
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              value={bHostelId}
              onChange={setBHostelId}
            />

            <Group grow>
              <TextInput
                label="Guest Name"
                required
                placeholder="Full name of primary guest"
                value={bGuestName}
                onChange={(e) => setBGuestName(e.target.value)}
              />
              <Select
                label="Relation to Student"
                required
                data={[
                  { value: "Parents", label: "Parents / Guardian" },
                  { value: "Sibling", label: "Brother / Sister" },
                  { value: "Relative", label: "Other Relative" },
                  { value: "Official Guest", label: "Official / Academic Visitor" },
                ]}
                value={bRelation}
                onChange={setBRelation}
              />
            </Group>

            <Group grow>
              <Select
                label="Guest Gender"
                required
                data={[
                  { value: "male", label: "Male" },
                  { value: "female", label: "Female" },
                  { value: "other", label: "Other" },
                ]}
                value={bGender}
                onChange={setBGender}
              />
              <NumberInput
                label="Number of Guests"
                required
                min={1}
                max={4}
                value={bNumGuests}
                onChange={setBNumGuests}
              />
            </Group>

            <Group grow>
              <TextInput
                label="Check-In Date"
                type="date"
                required
                value={bCheckIn}
                onChange={(e) => setBCheckIn(e.target.value)}
              />
              <TextInput
                label="Check-Out Date"
                type="date"
                required
                value={bCheckOut}
                onChange={(e) => setBCheckOut(e.target.value)}
              />
            </Group>

            <Textarea
              label="Purpose of Visit"
              placeholder="Convocation, medical visit, campus arrival, etc."
              minRows={2}
              value={bReason}
              onChange={(e) => setBReason(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setBookModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={submitMutation.isPending}
                disabled={!bHostelId || !bGuestName || !bCheckIn || !bCheckOut}
                onClick={handleBook}
              >
                Submit Booking Request
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Review Booking */}
        <Modal
          opened={decisionModalOpen}
          onClose={() => setDecisionModalOpen(false)}
          title={`Review Guest Booking #${selectedBooking?.id}`}
          size="md"
        >
          <Stack gap="sm">
            <Card withBorder p="xs">
              <Text size="sm" fw={600}>{selectedBooking?.guest_name} ({selectedBooking?.guest_relation})</Text>
              <Text size="xs" c="dimmed">
                Student: {selectedBooking?.student_name} ({selectedBooking?.student_roll_number})
              </Text>
              <Text size="xs" c="dimmed">
                Period: {selectedBooking?.check_in_date} to {selectedBooking?.check_out_date} ({selectedBooking?.number_of_guests} guests)
              </Text>
            </Card>

            <Select
              label="Decision"
              required
              data={[
                { value: "approved", label: "Approve Booking" },
                { value: "rejected", label: "Reject Booking" },
              ]}
              value={decisionType}
              onChange={(v) => setDecisionType(v as "approved" | "rejected")}
            />

            {decisionType === "approved" && (
              <Select
                label="Assign Guest Room"
                placeholder="Select available room"
                clearable
                data={(rooms || [])
                  .filter((r) => r.room_type === "guest" || r.available_beds > 0)
                  .map((r) => ({
                    value: String(r.id),
                    label: `Room ${r.room_number} (Floor ${r.floor}, ${r.room_type}, ${r.available_beds} beds free)`,
                  }))}
                value={assignedRoomId}
                onChange={setAssignedRoomId}
              />
            )}

            <Textarea
              label="Remarks / Conditions"
              placeholder="e.g. Valid ID proof required at reception upon check-in"
              minRows={2}
              value={decisionRemarks}
              onChange={(e) => setDecisionRemarks(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setDecisionModalOpen(false)}>
                Cancel
              </Button>
              <Button
                color={decisionType === "approved" ? "teal" : "red"}
                loading={decisionMutation.isPending}
                onClick={handleDecision}
              >
                Confirm {decisionType === "approved" ? "Approval" : "Rejection"}
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
