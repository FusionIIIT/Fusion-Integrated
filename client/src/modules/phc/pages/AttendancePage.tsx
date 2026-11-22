import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle, FaUserCheck } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMarkAttendance, useSchedule } from "../api/hooks";
import type { DoctorAttendance } from "../api/types";

const STATUSES = [
  { value: "available", label: "Available" },
  { value: "departed", label: "Departed" },
];

type AttendanceRow = {
  doctor_name: string;
  date: string;
  status: "available" | "departed";
};

export default function AttendancePage() {
  const { can } = useAuth();
  const canManage = can("phc.schedule.manage");
  const canView = can("phc.schedule.view");
  const { data, error } = useSchedule(canView);
  const mark = useMarkAttendance();
  const [doctor, setDoctor] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [status, setStatus] = useState<string | null>("available");
  const [marks, setMarks] = useState<DoctorAttendance[]>([]);

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  const today: AttendanceRow[] = Object.entries(data?.attendance ?? {})
    .map(([doctor_name, value]) => ({ doctor_name, date, status: value }));
  const recent: AttendanceRow[] = marks.map((m) => ({
    doctor_name: m.doctor_name, date: m.date, status: m.status,
  }));
  const rows = [
    ...recent,
    ...today.filter((t) => !recent.some((r) => r.doctor_name === t.doctor_name)),
  ];

  function submit() {
    mark.mutate(
      { doctor_name: doctor.trim(), date, status: status as "available" | "departed" },
      {
        onSuccess: (saved) => {
          setMarks((prev) => [saved, ...prev.filter(
            (m) => !(m.doctor_name === saved.doctor_name && m.date === saved.date))]);
          setDoctor("");
          notifications.show({
            color: "green", title: "Attendance recorded",
            message: `${saved.doctor_name} is now ${saved.status}.`,
          });
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record attendance", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Doctor Attendance"
        subtitle="Mark a doctor available or departed for the day"
      />

      {!canView && (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
          <Text size="sm">
            Live status needs the schedule-view permission. Marks you make in
            this session are still listed below.
          </Text>
        </Alert>
      )}
      {mark.error && <ErrorState error={mark.error} />}

      {canManage ? (
        <Card padding="lg" mb="md">
          <Stack gap="md">
            <Group grow>
              <TextInput
                label="Doctor name" required value={doctor}
                onChange={(e) => setDoctor(e.currentTarget.value)}
                placeholder="Name as it appears on the schedule" maxLength={120}
              />
              <TextInput
                label="Date" type="date" required value={date}
                onChange={(e) => setDate(e.currentTarget.value)}
              />
            </Group>
            <Select
              label="Status" required data={STATUSES} value={status}
              onChange={setStatus} allowDeselect={false}
            />
            <Group justify="flex-end">
              <Button
                onClick={submit} loading={mark.isPending}
                disabled={!doctor.trim() || !date || !status}
              >
                Record attendance
              </Button>
            </Group>
          </Stack>
        </Card>
      ) : (
        <Alert variant="light" color="red" mb="md">
          You do not have permission to mark attendance.
        </Alert>
      )}

      <Card padding="lg">
        <DataTable<AttendanceRow>
          rows={rows}
          rowKey={(r) => `${r.doctor_name}-${r.date}`}
          minWidth={640}
          columns={[
            { key: "doctor_name", header: "Doctor",
              render: (r) => <Text fw={600}>{r.doctor_name}</Text> },
            { key: "date", header: "Date",
              render: (r) => new Date(r.date).toLocaleDateString() },
            {
              key: "status", header: "Status",
              render: (r) => (
                <Badge
                  color={r.status === "available" ? "green" : "gray"}
                  variant="light" size="sm"
                >
                  {r.status}
                </Badge>
              ),
            },
          ]}
          empty={{
            icon: FaUserCheck,
            title: "No attendance recorded yet",
            description: "Today's statuses and marks made here will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
