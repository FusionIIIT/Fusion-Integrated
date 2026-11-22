import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  MultiSelect,
  Select,
  Stack,
  Tabs,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCalendarCheck,
  FaCheckCircle,
  FaDoorOpen,
  FaSignOutAlt,
  FaTimesCircle,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAllotRooms,
  useBookings,
  useRoomAvailability,
} from "../api/hooks";
import type { Booking, OccupancyType } from "../api/types";

export default function StayManagementPage() {
  const { data: bookings, isPending, error } = useBookings();
  const [allottingBooking, setAllottingBooking] = useState<Booking | null>(null);
  const [selectedRooms, setSelectedRooms] = useState<string[]>([]);
  const [occupancyType, setOccupancyType] = useState<OccupancyType>("single");

  const allotMutation = useAllotRooms(allottingBooking?.id ?? 0);

  const { data: availableRooms } = useRoomAvailability({
    arrival_date: allottingBooking?.arrival_date,
    departure_date: allottingBooking?.departure_date,
  });

  const handleAllotSubmit = async () => {
    if (!allottingBooking || selectedRooms.length === 0) return;
    try {
      await allotMutation.mutateAsync({
        room_ids: selectedRooms.map(Number),
        occupancy_type: occupancyType,
      });
      notifications.show({ color: "teal", message: "Rooms allotted successfully." });
      setAllottingBooking(null);
      setSelectedRooms([]);
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleCheckIn = async (b: Booking) => {
    const { http } = await import("../../../lib/http");
    try {
      await http.post(`/vh/bookings/${b.id}/checkin/`, {});
      notifications.show({ color: "teal", message: `Guest checked in for ${b.booking_reference}.` });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleCheckOut = async (b: Booking) => {
    const { http } = await import("../../../lib/http");
    try {
      await http.post(`/vh/bookings/${b.id}/checkout/`, { verified_by_guest: true });
      notifications.show({ color: "teal", message: `Guest checked out for ${b.booking_reference}. Bill generated.` });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleConfirmCancel = async (b: Booking) => {
    const { http } = await import("../../../lib/http");
    try {
      await http.post(`/vh/bookings/${b.id}/confirm-cancellation/`, {});
      notifications.show({ color: "teal", message: `Cancellation confirmed for ${b.booking_reference}.` });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const approved = (bookings ?? []).filter(
    (b) => b.status === "approved" || b.status === "approved_offline"
  );
  const allotted = (bookings ?? []).filter((b) => b.status === "room_allotted");
  const checkedIn = (bookings ?? []).filter((b) => b.status === "checked_in");
  const cancellations = (bookings ?? []).filter((b) => b.status === "cancellation_requested");

  return (
    <Container size="xl">
      <PageHeader
        title="Stay & Front Desk Management"
        subtitle="Operational desk for room allotment, guest check-in, check-out, and cancellation confirmations."
      />

      <Tabs defaultValue="allotment">
        <Tabs.List mb="md">
          <Tabs.Tab value="allotment">Awaiting Allotment ({approved.length})</Tabs.Tab>
          <Tabs.Tab value="checkin">Awaiting Check-in ({allotted.length})</Tabs.Tab>
          <Tabs.Tab value="active">Active Guests / Check-out ({checkedIn.length})</Tabs.Tab>
          <Tabs.Tab value="cancellations">Pending Cancellations ({cancellations.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="allotment">
          <Card padding="lg" withBorder>
            <DataTable<Booking>
              rows={approved}
              loading={isPending}
              rowKey={(r) => r.id}
              empty={{
                icon: FaCalendarCheck,
                title: "No bookings awaiting room allotment",
                description: "Approved bookings ready for room assignment will appear here.",
              }}
              columns={[
                {
                  key: "ref",
                  header: "Reference",
                  render: (r: Booking) => <Text fw={600}>{r.booking_reference}</Text>,
                },
                {
                  key: "visitor",
                  header: "Visitor",
                  render: (r: Booking) => r.visitors[0]?.name ?? "Guest",
                },
                {
                  key: "dates",
                  header: "Dates",
                  render: (r: Booking) => `${r.arrival_date} to ${r.departure_date}`,
                },
                {
                  key: "rooms",
                  header: "Rooms Needed",
                  render: (r: Booking) => r.number_of_rooms,
                },
                {
                  key: "actions",
                  header: "Action",
                  align: "right",
                  render: (r: Booking) => (
                    <Button
                      size="xs"
                      color="blue"
                      leftSection={<FaDoorOpen size={12} />}
                      onClick={() => {
                        setAllottingBooking(r);
                        setSelectedRooms([]);
                      }}
                    >
                      Allot Rooms
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="checkin">
          <Card padding="lg" withBorder>
            <DataTable<Booking>
              rows={allotted}
              loading={isPending}
              rowKey={(r) => r.id}
              empty={{
                icon: FaCalendarCheck,
                title: "No bookings awaiting check-in",
                description: "Bookings with allotted rooms will appear here when guests arrive.",
              }}
              columns={[
                {
                  key: "ref",
                  header: "Reference",
                  render: (r: Booking) => <Text fw={600}>{r.booking_reference}</Text>,
                },
                {
                  key: "visitor",
                  header: "Visitor",
                  render: (r: Booking) => r.visitors[0]?.name ?? "Guest",
                },
                {
                  key: "allotted",
                  header: "Allotted Rooms",
                  render: (r: Booking) =>
                    r.allotments.map((a) => a.room.room_number).join(", ") || "None",
                },
                {
                  key: "actions",
                  header: "Action",
                  align: "right",
                  render: (r: Booking) => (
                    <Button
                      size="xs"
                      color="teal"
                      leftSection={<FaCheckCircle size={12} />}
                      onClick={() => handleCheckIn(r)}
                    >
                      Record Check-In
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="active">
          <Card padding="lg" withBorder>
            <DataTable<Booking>
              rows={checkedIn}
              loading={isPending}
              rowKey={(r) => r.id}
              empty={{
                icon: FaCalendarCheck,
                title: "No currently checked-in guests",
                description: "Guests actively residing in the hostel will appear here.",
              }}
              columns={[
                {
                  key: "ref",
                  header: "Reference",
                  render: (r: Booking) => <Text fw={600}>{r.booking_reference}</Text>,
                },
                {
                  key: "visitor",
                  header: "Visitor",
                  render: (r: Booking) => r.visitors[0]?.name ?? "Guest",
                },
                {
                  key: "rooms",
                  header: "Rooms",
                  render: (r: Booking) =>
                    r.allotments.map((a) => a.room.room_number).join(", "),
                },
                {
                  key: "checkin",
                  header: "Check-in Time",
                  render: (r: Booking) =>
                    r.checkin_time ? new Date(r.checkin_time).toLocaleString() : "—",
                },
                {
                  key: "actions",
                  header: "Action",
                  align: "right",
                  render: (r: Booking) => (
                    <Button
                      size="xs"
                      color="orange"
                      leftSection={<FaSignOutAlt size={12} />}
                      onClick={() => handleCheckOut(r)}
                    >
                      Check-Out & Bill
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="cancellations">
          <Card padding="lg" withBorder>
            <DataTable<Booking>
              rows={cancellations}
              loading={isPending}
              rowKey={(r) => r.id}
              empty={{
                icon: FaCalendarCheck,
                title: "No pending cancellations",
                description: "Guest cancellation requests requiring confirmation will show here.",
              }}
              columns={[
                {
                  key: "ref",
                  header: "Reference",
                  render: (r: Booking) => <Text fw={600}>{r.booking_reference}</Text>,
                },
                {
                  key: "visitor",
                  header: "Visitor",
                  render: (r: Booking) => r.visitors[0]?.name ?? "Guest",
                },
                {
                  key: "reason",
                  header: "Reason",
                  render: (r: Booking) => r.cancellation_reason || "None specified",
                },
                {
                  key: "charge",
                  header: "Cancellation Charge",
                  render: (r: Booking) => `${r.cancellation_charge_percentage}%`,
                },
                {
                  key: "actions",
                  header: "Action",
                  align: "right",
                  render: (r: Booking) => (
                    <Button
                      size="xs"
                      color="red"
                      leftSection={<FaTimesCircle size={12} />}
                      onClick={() => handleConfirmCancel(r)}
                    >
                      Confirm Cancellation
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Room Allotment Modal */}
      <Modal
        opened={Boolean(allottingBooking)}
        onClose={() => setAllottingBooking(null)}
        title="Allot Rooms to Approved Booking"
      >
        <Stack gap="md">
          <Text size="sm">
            Allotting rooms for <strong>{allottingBooking?.booking_reference}</strong> ({allottingBooking?.number_of_rooms} rooms requested).
          </Text>
          <MultiSelect
            label="Select Available Rooms"
            placeholder="Pick room(s)"
            required
            data={
              availableRooms?.map((r) => ({
                value: String(r.id),
                label: `Room ${r.room_number} (${r.room_type})`,
              })) ?? []
            }
            value={selectedRooms}
            onChange={setSelectedRooms}
          />
          <Select
            label="Occupancy Type"
            data={[
              { value: "single", label: "Single Occupancy" },
              { value: "double", label: "Double Occupancy" },
            ]}
            value={occupancyType}
            onChange={(val) => setOccupancyType((val as OccupancyType) || "single")}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setAllottingBooking(null)}>
              Cancel
            </Button>
            <Button
              color="blue"
              loading={allotMutation.isPending}
              onClick={handleAllotSubmit}
            >
              Confirm Allotment
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
