import { useState } from "react";
import {
  Button,
  Group,
  Stack,
  Text,
  Title,
  Select,
  TextInput,
  Table,
  ActionIcon,
  Box,
} from "@mantine/core";
import { notification } from "@mantine/notifications";
import { useDoctorSchedules, useCreateSchedule, usePublishSchedule, useSetPresence } from "../api/hooks";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export function ManageSchedulePage() {
  const schedulesQuery = useDoctorSchedules();
  const createMutation = useCreateSchedule();
  const publishMutation = usePublishSchedule();
  const presenceMutation = useSetPresence();

  const [newDoctor, setNewDoctor] = useState("");
  const [newSpecialization, setNewSpecialization] = useState("");
  const [newDay, setNewDay] = useState<string>("Monday");
  const [newStartTime, setNewStartTime] = useState("");
  const [newEndTime, setNewEndTime] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDoctor || !newSpecialization || !newStartTime || !newEndTime) return;

    createMutation.mutate({
      doctor_name: newDoctor,
      specialization: newSpecialization,
      day_of_week: DAYS.indexOf(newDay),
      start_time: newStartTime,
      end_time: newEndTime,
      published: false,
      is_present: false,
    });

    setNewDoctor("");
    setNewSpecialization("");
    setNewDay("Monday");
    setNewStartTime("");
    setNewEndTime("");
  };

  const handlePublish = (id: number) => {
    publishMutation.mutate({ id });
  };

  const handlePresenceToggle = (id: number, current: boolean) => {
    presenceMutation.mutate({ id, isPresent: !current });
  };

  return (
    <Box p="md">
      <PageHeader title="Manage Schedules" subtitle="Create and manage doctor availability" />

      <Group justify="space-between" mb="md">
        <Stack gap={4} w="100%">
          <TextInput
            label="Doctor Name"
            placeholder="Dr. Smith"
            value={newDoctor}
            onChange={(e) => setNewDoctor(e.target.value)}
          />
          <TextInput
            label="Specialization"
            placeholder="Cardiology"
            value={newSpecialization}
            onChange={(e) => setNewSpecialization(e.target.value)}
          />
          <Select
            label="Day of Week"
            data={DAYS}
            value={newDay}
            onChange={(val) => setNewDay(val || "Monday")}
          />
          <TextInput
            type="time"
            label="Start Time"
            placeholder="09:00"
            value={newStartTime}
            onChange={(e) => setNewStartTime(e.target.value)}
          />
          <TextInput
            type="time"
            label="End Time"
            placeholder="17:00"
            value={newEndTime}
            onChange={(e) => setNewEndTime(e.target.value)}
          />
          <Button onClick={handleSubmit} disabled={createMutation.isPending}>
            Create Schedule
          </Button>
        </Stack>
      </Group>

      <Table striped highlightOnHover>
        <Table.Column key="id" label="ID" accessorKey="id" />
        <Table.Column key="doctor" label="Doctor" accessorKey="doctor_name" />
        <Table.Column key="spec" label="Specialization" accessorKey="specialization" />
        <Table.Column key="day" label="Day" accessorKey="day_of_week" cell={(info) => DAYS[info.row.original.day_of_week]} />
        <Table.Column key="time" label="Time Range" accessorKey="start_time" />
        <Table.Column key="pub" label="Status" accessorKey="published">
          {(info) => (
            <Group gap={4}>
              {info.row.original.published ? (
                <ActionIcon color="green" variant="light">
                  Published
                </ActionIcon>
              ) : (
                <Button size="xs" onClick={() => handlePublish(info.row.original.id)}>
                  Publish
                </Button>
              )}
              <ActionIcon
                color={info.row.original.is_present ? "green" : "red"}
                variant="light"
                onClick={() => handlePresenceToggle(info.row.original.id, info.row.original.is_present)}
              >
                {info.row.original.is_present ? "Present" : "Absent"}
              </ActionIcon>
            </Group>
          )}
        </Table.Column>
      </Table>

      {schedulesQuery.error && (
        <notification
          title="Error loading schedules"
          message={errorMessage(schedulesQuery.error)}
          color="red"
        />
      )}
    </Box>
  );
}
