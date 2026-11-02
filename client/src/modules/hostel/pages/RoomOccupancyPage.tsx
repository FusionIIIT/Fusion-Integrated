import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Progress,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { FaExchangeAlt } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useAllotments,
  useHostels,
  useRoomExchange,
  useRooms,
} from "../api/hooks";
import type { Room } from "../api/types";

export default function RoomOccupancyPage() {
  const { can } = useAuth();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const { data: hostels } = useHostels();
  const { data: rooms, isPending: roomsPending, error: roomsError } = useRooms({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
  });
  const { data: allotments } = useAllotments({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
    is_active: true,
  });

  const exchangeMutation = useRoomExchange();

  const [exchangeModalOpen, setExchangeModalOpen] = useState(false);
  const [student1, setStudent1] = useState<string | null>(null);
  const [targetRoom, setTargetRoom] = useState<string | null>(null);
  const [student2, setStudent2] = useState<string | null>(null);
  const [exchangeReason, setExchangeReason] = useState("");

  if (roomsError) {
    return (
      <Container size="xl">
        <ErrorState error={roomsError} />
      </Container>
    );
  }

  const hostelOptions = (hostels ?? []).map((h) => ({
    value: String(h.id),
    label: `${h.name} (${h.code})`,
  }));

  const activeResidents = (allotments ?? []).map((a) => ({
    value: String(a.student_user_id),
    label: `${a.student_roll_number} - ${a.student_name} (Room ${a.room_number})`,
  }));

  const availableRoomsList = (rooms ?? [])
    .filter((r) => r.is_available && r.available_beds > 0)
    .map((r) => ({
      value: String(r.id),
      label: `Room ${r.room_number} (${r.available_beds} beds free)`,
    }));

  const handleExecuteExchange = async () => {
    if (!selectedHostel || !student1 || !targetRoom) return;
    await exchangeMutation.mutateAsync({
      hostel_id: Number(selectedHostel),
      student_user_id_1: Number(student1),
      target_room_id: Number(targetRoom),
      student_user_id_2: student2 ? Number(student2) : undefined,
      reason: exchangeReason,
    });
    setExchangeModalOpen(false);
    setStudent1(null);
    setTargetRoom(null);
    setStudent2(null);
    setExchangeReason("");
  };

  const totalCap = rooms?.reduce((sum, r) => sum + r.capacity, 0) ?? 0;
  const totalOcc = rooms?.reduce((sum, r) => sum + r.current_occupancy, 0) ?? 0;
  const occPct = totalCap > 0 ? Math.round((totalOcc / totalCap) * 100) : 0;

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Room Occupancy & Exchanges"
        subtitle="Live bed-level occupancy monitoring and caretaker room exchange workflows"
        action={
          can("hostel.room.manage") && (
            <Button
              leftSection={<FaExchangeAlt size={12} />}
              onClick={() => setExchangeModalOpen(true)}
              disabled={!selectedHostel}
            >
              Caretaker Room Exchange
            </Button>
          )
        }
      />

      {/* FILTER & OCCUPANCY SUMMARY */}
      <Card withBorder padding="md" mb="md">
        <Group justify="space-between" wrap="wrap">
          <Select
            label="Filter by Hostel"
            placeholder="Select hostel to view floor & room breakdown"
            data={hostelOptions}
            value={selectedHostel}
            onChange={setSelectedHostel}
            clearable
            style={{ width: 320 }}
          />

          <Stack gap={4} align="flex-end">
            <Text size="xs" c="dimmed">Hostel Capacity Utilization</Text>
            <Group gap="xs">
              <Text fw={700} size="sm">{totalOcc} / {totalCap} beds filled</Text>
              <Badge color={occPct > 90 ? "red" : occPct > 70 ? "orange" : "teal"}>{occPct}%</Badge>
            </Group>
            <Progress value={occPct} w={180} size="sm" color={occPct > 90 ? "red" : "teal"} />
          </Stack>
        </Group>
      </Card>

      {/* ROOMS TABLE */}
      <Card withBorder padding="md">
        <DataTable<Room>
          rows={rooms ?? []}
          loading={roomsPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "hostel", header: "Hostel", render: (r) => r.hostel_name },
            { key: "room", header: "Room #", render: (r) => <Text fw={600}>{r.room_number}</Text> },
            { key: "floor", header: "Floor", render: (r) => r.floor },
            { key: "type", header: "Type", render: (r) => r.room_type.toUpperCase() },
            {
              key: "occupancy",
              header: "Occupancy / Capacity",
              render: (r) => (
                <Group gap="xs">
                  <Text size="sm">{r.current_occupancy} / {r.capacity}</Text>
                  <Progress value={(r.current_occupancy / r.capacity) * 100} w={60} size="xs" />
                </Group>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Badge color={r.available_beds > 0 ? "teal" : "red"}>
                  {r.available_beds > 0 ? `${r.available_beds} beds free` : "Full"}
                </Badge>
              ),
            },
          ]}
          empty={{
            title: "No Rooms Registered",
            description: "No rooms match the selected hostel filter.",
          }}
        />
      </Card>

      {/* CARETAKER ROOM EXCHANGE MODAL */}
      <Modal opened={exchangeModalOpen} onClose={() => setExchangeModalOpen(false)} title="Caretaker Individual Room Exchange">
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            Under BR-HM-010, the system prevents room occupancy from exceeding defined capacity.
            You can move a resident to a free bed or perform a mutual swap with another resident.
          </Text>

          <Select
            label="Select Student to Move"
            required
            placeholder="Choose resident..."
            data={activeResidents}
            value={student1}
            onChange={setStudent1}
          />

          <Select
            label="Target Room (Destination)"
            required
            placeholder="Select target room..."
            data={availableRoomsList}
            value={targetRoom}
            onChange={setTargetRoom}
          />

          <Select
            label="Optional: Second Student for Mutual Swap"
            placeholder="Leave empty if moving into a vacant bed"
            data={activeResidents.filter((a) => a.value !== student1)}
            value={student2}
            onChange={setStudent2}
            clearable
          />

          <TextInput
            label="Reason for Exchange"
            placeholder="e.g. Mutual consent, medical recommendation, maintenance"
            value={exchangeReason}
            onChange={(e) => setExchangeReason(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setExchangeModalOpen(false)}>Cancel</Button>
            <Button
              loading={exchangeMutation.isPending}
              onClick={handleExecuteExchange}
              disabled={!student1 || !targetRoom}
            >
              Execute Room Exchange
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
