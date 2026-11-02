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
  Switch,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBed, FaDoorOpen, FaPlus, FaSignOutAlt } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAccommodationRequests,
  useAllotments,
  useCreateAccommodationRequest,
  useCreateAllotment,
  useHostels,
  useRooms,
  useVacateAllotment,
} from "../api/hooks";
import type { RoomAllotment } from "../api/types";

export default function AllotmentManagementPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: allotmentsData, error: allotmentsError } = useAllotments({ hostel_id: hostelId });
  const { data: requestsData } = useAccommodationRequests({ hostel_id: hostelId });
  const { data: roomsData } = useRooms({ hostel_id: hostelId, status: "available" });

  const createRequest = useCreateAccommodationRequest();
  const createAllotment = useCreateAllotment();
  const vacateAllotment = useVacateAllotment();

  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [allotModalOpen, setAllotModalOpen] = useState(false);
  const [vacateModalOpen, setVacateModalOpen] = useState(false);
  const [selectedAllotment, setSelectedAllotment] = useState<RoomAllotment | null>(null);

  // Request form state
  const [reqStudentId, setReqStudentId] = useState<number | string>(1001);
  const [reqHostelId, setReqHostelId] = useState<string | null>(null);
  const [reqReason, setReqReason] = useState("");
  const [reqAcadYear, setReqAcadYear] = useState("2026-27");
  const [reqSemester, setReqSemester] = useState<number | string>(1);

  // Allotment form state
  const [allotStudentId, setAllotStudentId] = useState<number | string>(1001);
  const [allotHostelId, setAllotHostelId] = useState<string | null>(null);
  const [allotRoomId, setAllotRoomId] = useState<string | null>(null);
  const [allotBedNumber, setAllotBedNumber] = useState("A");

  // Vacate form state
  const [vacateRemarks, setVacateRemarks] = useState("");
  const [vacateClearance, setVacateClearance] = useState(true);

  const handleCreateRequest = async () => {
    if (!reqHostelId) return;
    try {
      await createRequest.mutateAsync({
        student_user_id: Number(reqStudentId),
        preferred_hostel: Number(reqHostelId),
        reason: reqReason,
        academic_year: reqAcadYear,
        semester: Number(reqSemester),
      });
      notifications.show({ title: "Success", message: "Accommodation request submitted", color: "green" });
      setRequestModalOpen(false);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to submit request", color: "red" });
    }
  };

  const handleCreateAllotment = async () => {
    if (!allotHostelId || !allotRoomId) return;
    try {
      await createAllotment.mutateAsync({
        student_user_id: Number(allotStudentId),
        hostel: Number(allotHostelId),
        room: Number(allotRoomId),
        bed_number: allotBedNumber,
      });
      notifications.show({ title: "Success", message: "Room allotted successfully", color: "green" });
      setAllotModalOpen(false);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to allot room", color: "red" });
    }
  };

  const handleVacate = async () => {
    if (!selectedAllotment) return;
    try {
      await vacateAllotment.mutateAsync({
        id: selectedAllotment.id,
        remarks: vacateRemarks,
        clearance: vacateClearance,
      });
      notifications.show({ title: "Success", message: "Room vacated successfully", color: "green" });
      setVacateModalOpen(false);
      setSelectedAllotment(null);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to vacate", color: "red" });
    }
  };

  if (allotmentsError) return <Container size="xl"><ErrorState error={allotmentsError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const allotments = allotmentsData?.results ?? [];
  const requests = requestsData?.results ?? [];
  const rooms = roomsData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Allotments & Requests"
        subtitle="Manage student accommodation applications, bed allocations, and vacation clearances"
        action={
          <Group>
            <Button variant="light" leftSection={<FaPlus size={14} />} onClick={() => setRequestModalOpen(true)}>
              Apply for Room
            </Button>
            <Button leftSection={<FaBed size={14} />} onClick={() => setAllotModalOpen(true)}>
              Allot Room & Bed
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

      <Tabs defaultValue="allotments" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="allotments" leftSection={<FaBed size={14} />}>
            Active Allotments ({allotments.length})
          </Tabs.Tab>
          <Tabs.Tab value="requests" leftSection={<FaDoorOpen size={14} />}>
            Accommodation Requests ({requests.length})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="allotments">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Student</Table.Th>
                  <Table.Th>Hostel</Table.Th>
                  <Table.Th>Room & Bed</Table.Th>
                  <Table.Th>Allotted On</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {allotments.map((a) => (
                  <Table.Tr key={a.id}>
                    <Table.Td fw={600}>
                      {a.student_name ? `${a.student_name} (${a.student_roll_number || a.student_user_id})` : `Student #${a.student_user_id}`}
                    </Table.Td>
                    <Table.Td>{a.hostel_name || a.hostel_code || `Hostel #${a.hostel}`}</Table.Td>
                    <Table.Td>Room {a.room_number || a.room} • Bed {a.bed_number}</Table.Td>
                    <Table.Td>{a.allotment_date}</Table.Td>
                    <Table.Td>
                      <Badge color={a.status === "active" ? "green" : "gray"}>
                        {a.status.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {a.status === "active" && (
                        <Button
                          variant="subtle"
                          color="red"
                          size="xs"
                          leftSection={<FaSignOutAlt size={12} />}
                          onClick={() => {
                            setSelectedAllotment(a);
                            setVacateModalOpen(true);
                          }}
                        >
                          Vacate
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="requests">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Student</Table.Th>
                  <Table.Th>Preferred Hostel</Table.Th>
                  <Table.Th>Academic Year</Table.Th>
                  <Table.Th>Semester</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {requests.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td fw={600}>
                      {r.student_name || `Student #${r.student_user_id}`}
                    </Table.Td>
                    <Table.Td>{r.preferred_hostel_name || `Hostel #${r.preferred_hostel}`}</Table.Td>
                    <Table.Td>{r.academic_year}</Table.Td>
                    <Table.Td>Semester {r.semester}</Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>
                      <Badge color={r.status === "approved" ? "green" : r.status === "pending" ? "yellow" : "gray"}>
                        {r.status.toUpperCase()}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Modal: Submit Accommodation Request */}
      <Modal opened={requestModalOpen} onClose={() => setRequestModalOpen(false)} title="Apply for Hostel Accommodation" centered>
        <Stack gap="sm">
          <NumberInput label="Student User ID" required value={reqStudentId} onChange={setReqStudentId} />
          <Select
            label="Preferred Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={reqHostelId}
            onChange={setReqHostelId}
          />
          <TextInput label="Academic Year" required value={reqAcadYear} onChange={(e) => setReqAcadYear(e.target.value)} />
          <NumberInput label="Semester" min={1} max={10} required value={reqSemester} onChange={setReqSemester} />
          <Textarea label="Reason for Request" required value={reqReason} onChange={(e) => setReqReason(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRequestModalOpen(false)}>Cancel</Button>
            <Button loading={createRequest.isPending} onClick={handleCreateRequest}>Submit Application</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Allot Room */}
      <Modal opened={allotModalOpen} onClose={() => setAllotModalOpen(false)} title="Direct Room Allotment" centered>
        <Stack gap="sm">
          <NumberInput label="Student User ID" required value={allotStudentId} onChange={setAllotStudentId} />
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={allotHostelId}
            onChange={(val) => {
              setAllotHostelId(val);
              setAllotRoomId(null);
            }}
          />
          <Select
            label="Available Room"
            required
            disabled={!allotHostelId}
            data={rooms
              .filter((r) => String(r.hostel) === allotHostelId)
              .map((r) => ({
                value: String(r.id),
                label: `Room ${r.room_number} (Occupancy: ${r.current_occupancy}/${r.capacity})`,
              }))}
            value={allotRoomId}
            onChange={setAllotRoomId}
          />
          <TextInput label="Bed Identifier" placeholder="e.g. A, B, or 1" required value={allotBedNumber} onChange={(e) => setAllotBedNumber(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAllotModalOpen(false)}>Cancel</Button>
            <Button loading={createAllotment.isPending} onClick={handleCreateAllotment}>Confirm Allotment</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Vacate Room */}
      <Modal opened={vacateModalOpen} onClose={() => setVacateModalOpen(false)} title="Vacate Room Allotment" centered>
        <Stack gap="sm">
          <Text size="sm">
            Are you sure you want to vacate room for Student #{selectedAllotment?.student_user_id}?
          </Text>
          <Switch
            label="No-dues and inventory inspection clearance verified"
            checked={vacateClearance}
            onChange={(e) => setVacateClearance(e.currentTarget.checked)}
          />
          <Textarea
            label="Vacation Remarks"
            placeholder="Condition of room / checkout notes"
            value={vacateRemarks}
            onChange={(e) => setVacateRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setVacateModalOpen(false)}>Cancel</Button>
            <Button color="red" loading={vacateAllotment.isPending} onClick={handleVacate}>Confirm Vacation</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
