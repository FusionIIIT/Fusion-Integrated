import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  SegmentedControl,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { FaSave, FaCalendarDay } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useAllotments,
  useAttendance,
  useHostels,
  useRecordAttendance,
} from "../api/hooks";
import type { AttendanceRecord } from "../api/types";

export default function AttendancePage() {
  const { can } = useAuth();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(() => new Date().toISOString().split("T")[0] || "");

  const { data: hostels } = useHostels();
  const { data: attendance, isPending: attPending, error: attError } = useAttendance({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
    date: selectedDate,
  });
  const { data: allotments } = useAllotments({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
    is_active: true,
  });

  const recordMutation = useRecordAttendance();

  // Local state for batch attendance editing
  const [statusMap, setStatusMap] = useState<Record<number, "present" | "absent" | "on_leave">>({});
  const [remarksMap, setRemarksMap] = useState<Record<number, string>>({});

  if (attError) {
    return (
      <Container size="xl">
        <ErrorState error={attError} />
      </Container>
    );
  }

  const hostelOptions = (hostels ?? []).map((h) => ({
    value: String(h.id),
    label: `${h.name} (${h.code})`,
  }));

  const canRecord = can("hostel.attendance.record");

  const handleSaveAttendance = async () => {
    if (!selectedHostel || !allotments) return;

    const records = allotments.map((a) => ({
      student_user_id: a.student_user_id,
      student_roll_number: a.student_roll_number,
      student_name: a.student_name,
      status: statusMap[a.student_user_id] ?? "present",
      remarks: remarksMap[a.student_user_id] ?? "",
    }));

    await recordMutation.mutateAsync({
      hostel_id: Number(selectedHostel),
      date: selectedDate,
      records,
    });
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Student Attendance Roll-Call"
        subtitle="Record daily night roll-call roster and track student presence / absences"
        action={
          canRecord && selectedHostel && (
            <Button
              leftSection={<FaSave size={12} />}
              loading={recordMutation.isPending}
              onClick={handleSaveAttendance}
            >
              Save Daily Roll-Call
            </Button>
          )
        }
      />

      <Card withBorder padding="md" mb="md">
        <Group justify="space-between" wrap="wrap">
          <Group>
            <Select
              label="Select Hostel"
              placeholder="Choose hostel"
              data={hostelOptions}
              value={selectedHostel}
              onChange={setSelectedHostel}
              clearable
              style={{ width: 280 }}
            />
            <TextInput
              label="Attendance Date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.currentTarget.value)}
              leftSection={<FaCalendarDay size={12} />}
            />
          </Group>

          {selectedHostel && (
            <Badge size="lg" variant="light" color="blue">
              {allotments?.length ?? 0} Registered Residents
            </Badge>
          )}
        </Group>
      </Card>

      <Card withBorder padding="md">
        {canRecord && selectedHostel ? (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Room #</Table.Th>
                <Table.Th>Roll Number</Table.Th>
                <Table.Th>Student Name</Table.Th>
                <Table.Th style={{ width: 280 }}>Attendance Status</Table.Th>
                <Table.Th>Remarks / Reason</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {allotments && allotments.length > 0 ? (
                allotments.map((a) => {
                  const currentStatus = statusMap[a.student_user_id] ?? "present";
                  const currentRemark = remarksMap[a.student_user_id] ?? "";
                  return (
                    <Table.Tr key={a.id}>
                      <Table.Td fw={600}>{a.room_number}</Table.Td>
                      <Table.Td>{a.student_roll_number}</Table.Td>
                      <Table.Td>{a.student_name}</Table.Td>
                      <Table.Td>
                        <SegmentedControl
                          size="xs"
                          value={currentStatus}
                          onChange={(val) =>
                            setStatusMap((prev) => ({
                              ...prev,
                              [a.student_user_id]: val as "present" | "absent" | "on_leave",
                            }))
                          }
                          data={[
                            { label: "Present", value: "present" },
                            { label: "Absent", value: "absent" },
                            { label: "On Leave", value: "on_leave" },
                          ]}
                          color={
                            currentStatus === "present"
                              ? "teal"
                              : currentStatus === "absent"
                              ? "red"
                              : "orange"
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <TextInput
                          size="xs"
                          placeholder="Optional remark..."
                          value={currentRemark}
                          onChange={(e) =>
                            setRemarksMap((prev) => ({
                              ...prev,
                              [a.student_user_id]: e.currentTarget.value,
                            }))
                          }
                        />
                      </Table.Td>
                    </Table.Tr>
                  );
                })
              ) : (
                <Table.Tr>
                  <Table.Td colSpan={5} style={{ textAlign: "center" }}>
                    No active residents found in this hostel.
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        ) : (
          <DataTable<AttendanceRecord>
            rows={attendance ?? []}
            loading={attPending}
            rowKey={(r) => r.id}
            columns={[
              { key: "date", header: "Date", render: (r) => r.date },
              { key: "hostel", header: "Hostel", render: (r) => r.hostel_name },
              { key: "roll", header: "Roll Number", render: (r) => <Text fw={600}>{r.student_roll_number}</Text> },
              { key: "name", header: "Student Name", render: (r) => r.student_name },
              {
                key: "status",
                header: "Status",
                render: (r) => (
                  <Badge
                    color={
                      r.status === "present" ? "teal" : r.status === "absent" ? "red" : "orange"
                    }
                  >
                    {r.status.toUpperCase()}
                  </Badge>
                ),
              },
              { key: "remarks", header: "Remarks", render: (r) => r.remarks || "—" },
            ]}
            empty={{
              title: "No Attendance Records",
              description: "Select a hostel and date to view or record attendance.",
            }}
          />
        )}
      </Card>
    </Container>
  );
}
