import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaClock, FaUserMd } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateDoctor,
  useDoctorAvailability,
  useMarkDoctorAttendance,
  useSaveDoctorSchedule,
} from "../api/hooks";

export default function DoctorAvailabilityPage() {
  const { can } = useAuth();
  const isStaff = can("phc.doctor_schedule.manage");

  const { data: availability, isPending, error } = useDoctorAvailability();

  // Modals
  const [attendanceModalOpen, setAttendanceModalOpen] = useState(false);
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [doctorModalOpen, setDoctorModalOpen] = useState(false);

  // Form states
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | null>(null);
  const [attendanceStatus, setAttendanceStatus] = useState<string>("Available");
  const [attendanceRemarks, setAttendanceRemarks] = useState("");

  const [scheduleDay, setScheduleDay] = useState("Monday");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("13:00");
  const [roomNumber, setRoomNumber] = useState("OPD-1");

  const [doctorName, setDoctorName] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  const markAttendanceMutation = useMarkDoctorAttendance();
  const saveScheduleMutation = useSaveDoctorSchedule();
  const createDoctorMutation = useCreateDoctor();

  const handleMarkAttendance = async () => {
    if (!selectedDoctorId) return;
    try {
      await markAttendanceMutation.mutateAsync({
        doctor_id: Number(selectedDoctorId),
        status: attendanceStatus,
        remarks: attendanceRemarks,
      });
      notifications.show({
        title: "Attendance Updated",
        message: "Doctor real-time status updated successfully.",
        color: "teal",
      });
      setAttendanceModalOpen(false);
    } catch {
      notifications.show({
        title: "Error",
        message: "Failed to update attendance.",
        color: "red",
      });
    }
  };

  const handleCreateDoctor = async () => {
    if (!doctorName || !specialization) return;
    try {
      await createDoctorMutation.mutateAsync({
        name: doctorName,
        specialization,
        contact_phone: contactPhone,
        is_visiting: true,
      });
      notifications.show({
        title: "Doctor Added",
        message: `Dr. ${doctorName} registered successfully.`,
        color: "teal",
      });
      setDoctorModalOpen(false);
      setDoctorName("");
      setSpecialization("");
      setContactPhone("");
    } catch {
      notifications.show({
        title: "Error",
        message: "Failed to register doctor.",
        color: "red",
      });
    }
  };

  const handleSaveSchedule = async () => {
    if (!selectedDoctorId) return;
    try {
      await saveScheduleMutation.mutateAsync({
        doctor_id: Number(selectedDoctorId),
        day_of_week: scheduleDay,
        start_time: startTime,
        end_time: endTime,
        room_number: roomNumber,
        is_published: true,
      });
      notifications.show({
        title: "Schedule Saved",
        message: "Weekly schedule added and published.",
        color: "teal",
      });
      setScheduleModalOpen(false);
    } catch {
      notifications.show({
        title: "Error",
        message: "Failed to save schedule.",
        color: "red",
      });
    }
  };

  if (error) return <ErrorState error={error} />;

  const doctorOptions = (availability || []).map((d) => ({
    value: String(d.doctor_id),
    label: `Dr. ${d.doctor_name} (${d.specialization})`,
  }));

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Doctor Schedule & Availability"
        subtitle="Weekly OPD visiting schedule and current-day real-time attendance status (PHC-BR-01)"
        action={
          isStaff && (
            <Group>
              <Button leftSection={<FaUserMd />} variant="light" onClick={() => setDoctorModalOpen(true)}>
                Add Doctor
              </Button>
              <Button leftSection={<FaCalendarAlt />} variant="light" onClick={() => setScheduleModalOpen(true)}>
                Add Schedule
              </Button>
              <Button leftSection={<FaClock />} color="blue" onClick={() => setAttendanceModalOpen(true)}>
                Mark Attendance
              </Button>
            </Group>
          )
        }
      />

      {isPending ? (
        <Text c="dimmed">Loading doctor availability...</Text>
      ) : !availability || availability.length === 0 ? (
        <Card withBorder p="xl" radius="md">
          <Text c="dimmed" ta="center">
            No doctors or published schedules currently available.
          </Text>
        </Card>
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
          {availability.map((doc) => {
            const att = doc.today_attendance;
            const statusColor =
              att.status === "Available"
                ? "green"
                : att.status === "Departed"
                ? "orange"
                : att.status === "On-Leave"
                ? "red"
                : "gray";

            return (
              <Card key={doc.doctor_id} withBorder shadow="sm" radius="md" p="md">
                <Group justify="space-between" mb="xs">
                  <Group>
                    <FaUserMd size={22} color="#1c7ed6" />
                    <div>
                      <Text fw={600} size="lg">
                        Dr. {doc.doctor_name}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {doc.specialization} {doc.is_visiting ? "• Visiting Specialist" : "• Permanent"}
                      </Text>
                    </div>
                  </Group>
                  <Badge color={statusColor} variant="filled" size="md">
                    Today: {att.status}
                  </Badge>
                </Group>

                {att.remarks && (
                  <Text size="xs" c="dimmed" mb="xs" fs="italic">
                    Note: {att.remarks}
                  </Text>
                )}

                <Text fw={500} size="sm" mt="sm" mb={4}>
                  Master Weekly Schedule:
                </Text>
                {doc.weekly_schedule.length === 0 ? (
                  <Text size="xs" c="dimmed">
                    No active published slots for this week.
                  </Text>
                ) : (
                  <Table striped highlightOnHover withTableBorder withColumnBorders>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Day</Table.Th>
                        <Table.Th>Timings</Table.Th>
                        <Table.Th>Room / OPD</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {doc.weekly_schedule.map((s) => (
                        <Table.Tr key={s.id}>
                          <Table.Td fw={500}>{s.day_of_week}</Table.Td>
                          <Table.Td>
                            {s.start_time} - {s.end_time}
                          </Table.Td>
                          <Table.Td>{s.room_number || "OPD"}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                )}
              </Card>
            );
          })}
        </SimpleGrid>
      )}

      {/* Mark Attendance Modal */}
      <Modal opened={attendanceModalOpen} onClose={() => setAttendanceModalOpen(false)} title="Update Live Doctor Attendance">
        <Stack>
          <Select
            label="Select Doctor"
            placeholder="Choose visiting doctor"
            data={doctorOptions}
            value={selectedDoctorId}
            onChange={setSelectedDoctorId}
            required
          />
          <Select
            label="Real-time Status"
            data={["Available", "Departed", "On-Leave"]}
            value={attendanceStatus}
            onChange={(v) => setAttendanceStatus(v || "Available")}
            required
          />
          <TextInput
            label="Remarks (optional)"
            placeholder="e.g. Arrived at 09:15 AM"
            value={attendanceRemarks}
            onChange={(e) => setAttendanceRemarks(e.currentTarget.value)}
          />
          <Button fullWidth onClick={handleMarkAttendance} loading={markAttendanceMutation.isPending}>
            Update Status
          </Button>
        </Stack>
      </Modal>

      {/* Add Schedule Modal */}
      <Modal opened={scheduleModalOpen} onClose={() => setScheduleModalOpen(false)} title="Add Master Weekly Schedule Slot">
        <Stack>
          <Select
            label="Doctor"
            placeholder="Select doctor"
            data={doctorOptions}
            value={selectedDoctorId}
            onChange={setSelectedDoctorId}
            required
          />
          <Select
            label="Day of Week"
            data={["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
            value={scheduleDay}
            onChange={(v) => setScheduleDay(v || "Monday")}
            required
          />
          <Group grow>
            <TextInput label="Start Time" value={startTime} onChange={(e) => setStartTime(e.currentTarget.value)} required />
            <TextInput label="End Time" value={endTime} onChange={(e) => setEndTime(e.currentTarget.value)} required />
          </Group>
          <TextInput label="Room / OPD Number" value={roomNumber} onChange={(e) => setRoomNumber(e.currentTarget.value)} />
          <Button fullWidth onClick={handleSaveSchedule} loading={saveScheduleMutation.isPending}>
            Publish Slot
          </Button>
        </Stack>
      </Modal>

      {/* Add Doctor Modal */}
      <Modal opened={doctorModalOpen} onClose={() => setDoctorModalOpen(false)} title="Register Doctor Profile">
        <Stack>
          <TextInput
            label="Doctor Full Name"
            placeholder="e.g. Ramesh Chandra"
            value={doctorName}
            onChange={(e) => setDoctorName(e.currentTarget.value)}
            required
          />
          <TextInput
            label="Specialization"
            placeholder="e.g. General Physician, Dermatologist, Orthopedic"
            value={specialization}
            onChange={(e) => setSpecialization(e.currentTarget.value)}
            required
          />
          <TextInput
            label="Contact Phone"
            placeholder="e.g. +91 9876543210"
            value={contactPhone}
            onChange={(e) => setContactPhone(e.currentTarget.value)}
          />
          <Button fullWidth onClick={handleCreateDoctor} loading={createDoctorMutation.isPending}>
            Save Doctor
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
