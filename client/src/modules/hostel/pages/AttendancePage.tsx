import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Radio,
  Select,
  Table,
  Text,
  TextInput,
  } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAllotments, useAttendance, useHostels, useRecordAttendance } from "../api/hooks";
import type { AttendanceStatus } from "../api/types";

export default function AttendancePage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [attendanceDate, setAttendanceDate] = useState<string>(new Date().toISOString().slice(0, 10));

  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;
  const { data: hostelsData } = useHostels();
  const { data: allotmentsData } = useAllotments({ hostel_id: hostelId, status: "active" });
  const { data: attendanceData, error: attendanceError } = useAttendance({
    hostel_id: hostelId,
    date: attendanceDate,
  });

  const recordAttendance = useRecordAttendance();

  // Local state mapping student_user_id -> status and remarks
  const [attendanceMap, setAttendanceMap] = useState<Record<number, { status: AttendanceStatus; remarks: string }>>({});

  const allotments = allotmentsData?.results ?? [];
  const existingRecords = attendanceData?.results ?? [];

  useEffect(() => {
    const initial: Record<number, { status: AttendanceStatus; remarks: string }> = {};
    allotments.forEach((a) => {
      const match = existingRecords.find((r) => r.student_user_id === a.student_user_id);
      initial[a.student_user_id] = {
        status: match ? match.status : "present",
        remarks: match ? match.remarks : "",
      };
    });
    setAttendanceMap(initial);
  }, [allotmentsData, attendanceData]);

  const handleStatusChange = (studentId: number, status: AttendanceStatus) => {
    setAttendanceMap((prev) => ({
      ...prev,
      [studentId]: {
        status,
        remarks: prev[studentId]?.remarks ?? "",
      },
    }));
  };

  const handleRemarksChange = (studentId: number, remarks: string) => {
    setAttendanceMap((prev) => ({
      ...prev,
      [studentId]: {
        status: prev[studentId]?.status ?? "present",
        remarks,
      },
    }));
  };

  const handleSave = async () => {
    if (!hostelId) return;
    const records = Object.entries(attendanceMap).map(([studentId, data]) => ({
      student_user_id: Number(studentId),
      status: data.status,
      remarks: data.remarks,
    }));

    try {
      await recordAttendance.mutateAsync({
        hostel_id: hostelId,
        attendance_date: attendanceDate,
        records,
      });
      notifications.show({ title: "Success", message: "Attendance records saved", color: "green" });
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to record attendance", color: "red" });
    }
  };

  if (attendanceError) return <Container size="xl"><ErrorState error={attendanceError} /></Container>;

  const hostels = hostelsData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Student Attendance"
        subtitle="Mandatory night roll-call and biometric / manual attendance logging"
        action={
          <Button
            leftSection={<FaCheckCircle size={14} />}
            loading={recordAttendance.isPending}
            disabled={!hostelId || allotments.length === 0}
            onClick={handleSave}
          >
            Submit Night Roll-Call
          </Button>
        }
      />

      <Card withBorder radius="md" mb="lg">
        <Group align="flex-end">
          <Select
            label="Hostel"
            placeholder="Select hostel"
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={selectedHostel}
            onChange={setSelectedHostel}
            style={{ minWidth: 260 }}
          />
          <TextInput
            label="Attendance Date"
            type="date"
            value={attendanceDate}
            onChange={(e) => setAttendanceDate(e.target.value)}
          />
        </Group>
      </Card>

      {!hostelId ? (
        <Card withBorder p="xl" radius="md">
          <Text c="dimmed" ta="center">Please select a hostel to begin attendance logging.</Text>
        </Card>
      ) : allotments.length === 0 ? (
        <Card withBorder p="xl" radius="md">
          <Text c="dimmed" ta="center">No active allotments found in this hostel.</Text>
        </Card>
      ) : (
        <Card withBorder radius="md">
          <Table highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Student</Table.Th>
                <Table.Th>Room & Bed</Table.Th>
                <Table.Th>Roll-Call Status</Table.Th>
                <Table.Th>Remarks / Notes</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {allotments.map((a) => {
                const current = attendanceMap[a.student_user_id] || { status: "present", remarks: "" };
                return (
                  <Table.Tr key={a.id}>
                    <Table.Td fw={600}>
                      {a.student_name ? `${a.student_name} (${a.student_roll_number || a.student_user_id})` : `Student #${a.student_user_id}`}
                    </Table.Td>
                    <Table.Td>Room {a.room_number || a.room} (Bed {a.bed_number})</Table.Td>
                    <Table.Td>
                      <Radio.Group
                        value={current.status}
                        onChange={(val) => handleStatusChange(a.student_user_id, val as AttendanceStatus)}
                      >
                        <Group gap="md">
                          <Radio value="present" label="Present" color="green" />
                          <Radio value="absent" label="Absent" color="red" />
                          <Radio value="on_leave" label="On Leave" color="blue" />
                        </Group>
                      </Radio.Group>
                    </Table.Td>
                    <Table.Td>
                      <TextInput
                        placeholder="Optional remarks"
                        size="xs"
                        value={current.remarks}
                        onChange={(e) => handleRemarksChange(a.student_user_id, e.target.value)}
                      />
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Container>
  );
}
