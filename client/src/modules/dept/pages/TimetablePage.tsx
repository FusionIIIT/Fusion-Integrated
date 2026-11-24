import { useState } from "react";
import { Alert, Button, Card, Container, Group, Modal, NumberInput, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { useSaveTimetable, useTimetables } from "../api/hooks";

export default function TimetablePage() {
  const { can } = useAuth();
  const { data: entries, isLoading } = useTimetables();
  const saveTimetable = useSaveTimetable();

  const [createOpened, setCreateOpened] = useState(false);
  const [program, setProgram] = useState("B.Tech CSE");
  const [year, setYear] = useState<number | string>(2026);
  const [semester, setSemester] = useState<number | string>(1);
  const [day, setDay] = useState("0");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [courseCode, setCourseCode] = useState("");
  const [courseName, setCourseName] = useState("");
  const [instructorId, setInstructorId] = useState("");
  const [room, setRoom] = useState("");

  const canManage = can("dept.timetable.manage");

  const handleSave = async () => {
    if (!courseCode.trim() || !instructorId.trim() || !room.trim()) return;
    await saveTimetable.mutateAsync({
      program,
      academic_year: Number(year),
      semester: Number(semester),
      day_of_week: Number(day),
      start_time: startTime.length === 5 ? `${startTime}:00` : startTime,
      end_time: endTime.length === 5 ? `${endTime}:00` : endTime,
      course_code: courseCode,
      course_name: courseName,
      instructor_id: instructorId,
      room_or_lab: room,
    });
    setCourseCode("");
    setCourseName("");
    setInstructorId("");
    setRoom("");
    setCreateOpened(false);
  };

  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Timetables</Title>
          <Text c="dimmed">Conflict-free class and laboratory schedules</Text>
        </div>
        {canManage && (
          <Button onClick={() => setCreateOpened(true)}>Add Schedule Slot</Button>
        )}
      </Group>

      {isLoading && <Text>Loading timetables...</Text>}

      {entries && entries.length === 0 && (
        <Alert title="No Timetable Entries" color="blue">
          No schedule entries have been added for this department.
        </Alert>
      )}

      {entries && entries.length > 0 && (
        <Card withBorder shadow="sm" radius="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Day</Table.Th>
                <Table.Th>Time</Table.Th>
                <Table.Th>Course</Table.Th>
                <Table.Th>Program</Table.Th>
                <Table.Th>Instructor</Table.Th>
                <Table.Th>Room / Lab</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {entries.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td fw={500}>{days[t.day_of_week] || `Day ${t.day_of_week}`}</Table.Td>
                  <Table.Td>{`${t.start_time.slice(0, 5)} - ${t.end_time.slice(0, 5)}`}</Table.Td>
                  <Table.Td>{`${t.course_code}: ${t.course_name}`}</Table.Td>
                  <Table.Td>{`${t.program} (Sem ${t.semester})`}</Table.Td>
                  <Table.Td>{t.instructor_id}</Table.Td>
                  <Table.Td fw={500}>{t.room_or_lab}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <Modal opened={createOpened} onClose={() => setCreateOpened(false)} title="Add Timetable Slot">
        <Stack gap="sm">
          <TextInput label="Program" value={program} onChange={(e) => setProgram(e.target.value)} required />
          <Group grow>
            <NumberInput label="Year" value={year} onChange={setYear} required />
            <NumberInput label="Semester" value={semester} onChange={setSemester} min={1} max={8} required />
          </Group>
          <Select
            label="Day of Week"
            data={days.map((d, i) => ({ value: String(i), label: d }))}
            value={day}
            onChange={(val) => setDay(val ?? "0")}
            required
          />
          <Group grow>
            <TextInput label="Start Time (HH:MM)" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
            <TextInput label="End Time (HH:MM)" value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
          </Group>
          <TextInput label="Course Code" placeholder="e.g. CS201" value={courseCode} onChange={(e) => setCourseCode(e.target.value)} required />
          <TextInput label="Course Name" placeholder="e.g. Data Structures" value={courseName} onChange={(e) => setCourseName(e.target.value)} required />
          <TextInput label="Instructor ID" placeholder="Faculty username / ID" value={instructorId} onChange={(e) => setInstructorId(e.target.value)} required />
          <TextInput label="Room / Lab" placeholder="e.g. Room 101 or Lab 2" value={room} onChange={(e) => setRoom(e.target.value)} required />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateOpened(false)}>Cancel</Button>
            <Button onClick={handleSave} loading={saveTimetable.isPending}>Save Slot</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
