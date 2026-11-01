import { Stack, Table, Text, Box } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDoctorSchedules } from "../api/hooks";
import type { DoctorSchedule } from "../api/types";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export function DoctorSchedulePage() {
  const { data: schedulesData } = useDoctorSchedules();

  if (!schedulesData?.results.length) {
    return (
      <Box p="md">
        <Text c="dimmed" ta="center">No schedules published yet.</Text>
      </Box>
    );
  }

  const rows = schedulesData.results.map((schedule: DoctorSchedule) => ({
    id: schedule.id,
    doctor: schedule.doctor_name,
    specialization: schedule.specialization,
    dayName: DAYS[schedule.day_of_week] || "Unknown",
    timeRange: `${schedule.start_time} - ${schedule.end_time}`,
    status: schedule.is_present ? "Present" : "Not in",
  }));

  return (
    <Stack>
      <PageHeader title="Doctor Schedules" />
      <Table striped hoverable>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>Doctor</Table.Th>
            <Table.Th>Specialization</Table.Th>
            <Table.Th>Day</Table.Th>
            <Table.Th>Time</Table.Th>
            <Table.Th>Status</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row) => (
            <Table.Tr key={row.id}>
              <Table.Td>{row.id}</Table.Td>
              <Table.Td>{row.doctor}</Table.Td>
              <Table.Td>{row.specialization}</Table.Td>
              <Table.Td>{row.dayName}</Table.Td>
              <Table.Td>{row.timeRange}</Table.Td>
              <Table.Td>
                <Badge color={row.status === "Present" ? "green" : "gray"} variant="light">
                  {row.status}
                </Badge>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}

export default DoctorSchedulePage;
