import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Progress,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExchangeAlt, FaPlus, FaTools } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAllotments,
  useCreateRoom,
  useHostels,
  useRoomExchange,
  useRooms,
  useUpdateRoomStatus,
} from "../api/hooks";
import type { Room } from "../api/types";

export default function RoomOccupancyPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: roomsData, error: roomsError } = useRooms({ hostel_id: hostelId });
  const { data: allotmentsData } = useAllotments({ hostel_id: hostelId, status: "active" });

  const createRoom = useCreateRoom();
  const updateStatus = useUpdateRoomStatus();
  const exchangeRooms = useRoomExchange();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [exchangeModalOpen, setExchangeModalOpen] = useState(false);
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);

  // New room state
  const [newRoomHostel, setNewRoomHostel] = useState<string | null>(null);
  const [newRoomNumber, setNewRoomNumber] = useState("");
  const [newFloor, setNewFloor] = useState<number | string>(1);
  const [newCapacity, setNewCapacity] = useState<number | string>(2);

  // Status update state
  const [targetStatus, setTargetStatus] = useState<string>("maintenance");
  const [statusRemarks, setStatusRemarks] = useState("");

  // Exchange state
  const [allotmentA, setAllotmentA] = useState<string | null>(null);
  const [allotmentB, setAllotmentB] = useState<string | null>(null);
  const [exchangeReason, setExchangeReason] = useState("");

  const handleCreateRoom = async () => {
    if (!newRoomHostel) return;
    try {
      await createRoom.mutateAsync({
        hostel: Number(newRoomHostel),
        room_number: newRoomNumber,
        floor: Number(newFloor),
        capacity: Number(newCapacity),
      });
      notifications.show({ title: "Success", message: "Room added successfully", color: "green" });
      setCreateModalOpen(false);
      setNewRoomNumber("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to create room", color: "red" });
    }
  };

  const handleUpdateStatus = async () => {
    if (!selectedRoom) return;
    try {
      await updateStatus.mutateAsync({
        id: selectedRoom.id,
        status: targetStatus,
        remarks: statusRemarks,
      });
      notifications.show({ title: "Success", message: "Room status updated", color: "green" });
      setStatusModalOpen(false);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to update room status", color: "red" });
    }
  };

  const handleExchange = async () => {
    if (!allotmentA || !allotmentB) return;
    try {
      await exchangeRooms.mutateAsync({
        allotment_a_id: Number(allotmentA),
        allotment_b_id: Number(allotmentB),
        reason: exchangeReason,
      });
      notifications.show({ title: "Success", message: "Room exchange completed successfully", color: "green" });
      setExchangeModalOpen(false);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to exchange rooms", color: "red" });
    }
  };

  if (roomsError) return <Container size="xl"><ErrorState error={roomsError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const rooms = roomsData?.results ?? [];
  const allotments = allotmentsData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Rooms & Occupancy"
        subtitle="View bed capacity, room maintenance states, and mutual room swaps"
        action={
          <Group>
            <Button variant="light" leftSection={<FaExchangeAlt size={14} />} onClick={() => setExchangeModalOpen(true)}>
              Room Swap
            </Button>
            <Button leftSection={<FaPlus size={14} />} onClick={() => setCreateModalOpen(true)}>
              Add Room
            </Button>
          </Group>
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
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Room Number</Table.Th>
              <Table.Th>Floor</Table.Th>
              <Table.Th>Occupancy / Capacity</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rooms.map((r) => {
              const pct = r.capacity > 0 ? Math.round((r.current_occupancy / r.capacity) * 100) : 0;
              return (
                <Table.Tr key={r.id}>
                  <Table.Td fw={600}>{r.hostel_name || r.hostel_code || `Hostel #${r.hostel}`}</Table.Td>
                  <Table.Td fw={700}>Room {r.room_number}</Table.Td>
                  <Table.Td>Floor {r.floor}</Table.Td>
                  <Table.Td>
                    <Group gap="xs" style={{ minWidth: 160 }}>
                      <Text size="xs">{r.current_occupancy} / {r.capacity} beds</Text>
                      <Progress value={pct} size="sm" style={{ flex: 1 }} color={pct >= 100 ? "red" : pct > 0 ? "teal" : "gray"} />
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={r.status === "full" ? "red" : r.status === "occupied" ? "teal" : r.status === "available" ? "green" : "orange"}>
                      {r.status.toUpperCase()}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Button
                      variant="subtle"
                      size="xs"
                      leftSection={<FaTools size={12} />}
                      onClick={() => {
                        setSelectedRoom(r);
                        setTargetStatus(r.status);
                        setStatusModalOpen(true);
                      }}
                    >
                      Status
                    </Button>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Modal: Create Room */}
      <Modal opened={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Add Room" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={newRoomHostel}
            onChange={setNewRoomHostel}
          />
          <TextInput label="Room Number" placeholder="e.g. 101, A-204" required value={newRoomNumber} onChange={(e) => setNewRoomNumber(e.target.value)} />
          <NumberInput label="Floor" min={0} max={15} required value={newFloor} onChange={setNewFloor} />
          <NumberInput label="Bed Capacity" min={1} max={6} required value={newCapacity} onChange={setNewCapacity} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            <Button loading={createRoom.isPending} onClick={handleCreateRoom}>Save Room</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Update Status */}
      <Modal opened={statusModalOpen} onClose={() => setStatusModalOpen(false)} title={`Update Status: Room ${selectedRoom?.room_number}`} centered>
        <Stack gap="sm">
          <Select
            label="Room State"
            required
            data={[
              { value: "available", label: "Available" },
              { value: "occupied", label: "Occupied" },
              { value: "maintenance", label: "Under Maintenance" },
              { value: "blocked", label: "Blocked" },
            ]}
            value={targetStatus}
            onChange={(val) => val && setTargetStatus(val)}
          />
          <TextInput label="Maintenance / Block Remarks" placeholder="Reason for status change" value={statusRemarks} onChange={(e) => setStatusRemarks(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setStatusModalOpen(false)}>Cancel</Button>
            <Button loading={updateStatus.isPending} onClick={handleUpdateStatus}>Update Status</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Room Swap */}
      <Modal opened={exchangeModalOpen} onClose={() => setExchangeModalOpen(false)} title="Mutual Room Swap" centered>
        <Stack gap="sm">
          <Select
            label="Student 1 Allotment"
            placeholder="Select first resident"
            required
            data={allotments.map((a) => ({
              value: String(a.id),
              label: `Student #${a.student_user_id} (Room ${a.room_number || a.room})`,
            }))}
            value={allotmentA}
            onChange={setAllotmentA}
          />
          <Select
            label="Student 2 Allotment"
            placeholder="Select second resident"
            required
            data={allotments
              .filter((a) => String(a.id) !== allotmentA)
              .map((a) => ({
                value: String(a.id),
                label: `Student #${a.student_user_id} (Room ${a.room_number || a.room})`,
              }))}
            value={allotmentB}
            onChange={setAllotmentB}
          />
          <TextInput label="Reason for Swap" placeholder="Mutual agreement / medical reasons" value={exchangeReason} onChange={(e) => setExchangeReason(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setExchangeModalOpen(false)}>Cancel</Button>
            <Button loading={exchangeRooms.isPending} onClick={handleExchange}>Confirm Swap</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
