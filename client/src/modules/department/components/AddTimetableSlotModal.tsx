import { useState } from "react";
import { Select, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { useAddTimetableSlot } from "../api/hooks";

interface Props {
  opened: boolean;
  onClose: () => void;
  timetableId: number;
}

const DAYS = [
  { value: "Monday", label: "Monday" },
  { value: "Tuesday", label: "Tuesday" },
  { value: "Wednesday", label: "Wednesday" },
  { value: "Thursday", label: "Thursday" },
  { value: "Friday", label: "Friday" },
  { value: "Saturday", label: "Saturday" },
];

export function AddTimetableSlotModal({ opened, onClose, timetableId }: Props) {
  const [day, setDay] = useState("Monday");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [subject, setSubject] = useState("");
  const [room, setRoom] = useState("");

  const addSlot = useAddTimetableSlot();

  const handleSubmit = async () => {
    if (!subject.trim() || !startTime || !endTime) return;
    try {
      await addSlot.mutateAsync({
        timetable: timetableId,
        day,
        start_time: startTime + ":00",
        end_time: endTime + ":00",
        subject: subject.trim(),
        room: room.trim(),
      });
      notifications.show({
        title: "Slot Added",
        message: `${subject} added on ${day} at ${startTime}-${endTime}.`,
        color: "teal",
      });
      setSubject("");
      setRoom("");
      onClose();
    } catch (e) {
      notifications.show({
        title: "Failed to Add Slot",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Add Timetable Slot"
      subtitle="Schedule a class or lab session"
      onSubmit={handleSubmit}
      submitting={addSlot.isPending}
      disabled={!subject.trim() || !startTime || !endTime}
    >
      <Stack gap="sm">
        <Select
          label="Day of Week"
          data={DAYS}
          value={day}
          onChange={(v) => setDay(v || "Monday")}
          required
        />
        <TextInput
          label="Subject / Course"
          placeholder="e.g. CS362 Software Engineering"
          required
          value={subject}
          onChange={(e) => setSubject(e.currentTarget.value)}
        />
        <TextInput
          label="Room / Lab"
          placeholder="e.g. L-101 or Computer Lab 3"
          value={room}
          onChange={(e) => setRoom(e.currentTarget.value)}
        />
        <TextInput
          label="Start Time (HH:MM)"
          placeholder="09:00"
          required
          value={startTime}
          onChange={(e) => setStartTime(e.currentTarget.value)}
        />
        <TextInput
          label="End Time (HH:MM)"
          placeholder="10:00"
          required
          value={endTime}
          onChange={(e) => setEndTime(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
