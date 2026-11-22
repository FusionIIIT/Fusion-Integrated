import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Table, Text, TextInput,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateSchedule, useMarkAttendance, usePublishSchedule, useSchedules, useUpdateSchedule,
} from "../api/hooks";
import type { Schedule, Slot } from "../api/types";
import { ListStates } from "../components/ListStates";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const BLANK_SLOT: Slot = { day_of_week: 0, start_time: "", end_time: "" };

function StatusBadge({ status }: { status: Schedule["today_status"] }) {
  if (status === "available") return <Badge color="green">Available</Badge>;
  if (status === "departed") return <Badge color="gray">Departed</Badge>;
  return <Badge color="yellow" variant="light">Not marked today</Badge>;
}

function ScheduleForm({ editing, onClose }: { editing: Schedule | "new"; onClose: () => void }) {
  const create = useCreateSchedule();
  const update = useUpdateSchedule();
  const start = editing === "new" ? null : editing;
  const [doctor, setDoctor] = useState(start?.doctor_name ?? "");
  const [specialization, setSpecialization] = useState(start?.specialization ?? "");
  const [slots, setSlots] = useState<Slot[]>(start?.slots.map((s) => ({
    day_of_week: s.day_of_week, start_time: s.start_time.slice(0, 5),
    end_time: s.end_time.slice(0, 5),
  })) ?? [BLANK_SLOT]);
  const mutation = start ? update : create;

  const setSlot = (i: number, patch: Partial<Slot>) =>
    setSlots(slots.map((s, j) => (j === i ? { ...s, ...patch } : s)));

  const submit = () => {
    const body = { doctor_name: doctor, specialization, slots };
    const done = { onSuccess: onClose };
    if (start) update.mutate({ id: start.id, ...body }, done);
    else create.mutate(body, done);
  };

  return (
    <FormModal
      opened onClose={onClose} title={start ? "Edit schedule" : "New doctor schedule"}
      onSubmit={submit} submitting={mutation.isPending} error={mutation.error}
      disabled={!doctor.trim() || slots.some((s) => !s.start_time || !s.end_time)}
      disabledReason="Enter the doctor's name and a start and end time for every day."
    >
      <Stack>
        <TextInput label="Doctor name" required value={doctor}
          onChange={(e) => setDoctor(e.currentTarget.value)} />
        <TextInput label="Specialization" value={specialization}
          onChange={(e) => setSpecialization(e.currentTarget.value)} />
        {slots.map((slot, i) => (
          <Group key={i} align="flex-end" grow>
            <Select label={`Day ${i + 1}`} value={String(slot.day_of_week)}
              data={DAYS.map((d, n) => ({ value: String(n), label: d }))}
              onChange={(v) => setSlot(i, { day_of_week: Number(v ?? 0) })} />
            <TextInput label="From" type="time" value={slot.start_time}
              onChange={(e) => setSlot(i, { start_time: e.currentTarget.value })} />
            <TextInput label="To" type="time" value={slot.end_time}
              onChange={(e) => setSlot(i, { end_time: e.currentTarget.value })} />
            <Button variant="subtle" color="red" disabled={slots.length === 1}
              aria-label={`Remove day ${i + 1}`}
              onClick={() => setSlots(slots.filter((_, j) => j !== i))}>Remove</Button>
          </Group>
        ))}
        <Button variant="light" onClick={() => setSlots([...slots, BLANK_SLOT])}>Add day</Button>
      </Stack>
    </FormModal>
  );
}

export default function SchedulePage() {
  const { can } = useAuth();
  const { data, isPending, error } = useSchedules();
  const publish = usePublishSchedule();
  const attendance = useMarkAttendance();
  const [editing, setEditing] = useState<Schedule | "new" | null>(null);
  const rows = data ?? [];
  const actionError = publish.error ?? attendance.error;

  return (
    <Container size="lg">
      <PageHeader
        title="Doctor schedule"
        subtitle="The weekly schedule and whether each doctor is in today"
        action={can("phc.schedule.create") && (
          <Button onClick={() => setEditing("new")}>New schedule</Button>
        )}
      />
      {actionError != null && <Text c="red" mb="sm">{errorMessage(actionError)}</Text>}
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No doctor schedule has been published yet" />
      <Stack>
        {rows.map((s) => (
          <Card key={s.id} withBorder padding="lg">
            <Group justify="space-between" mb="xs">
              <div>
                <Text fw={700}>{s.doctor_name}</Text>
                <Text size="sm" c="dimmed">{s.specialization}</Text>
              </div>
              <Group gap="xs">
                {!s.is_published && <Badge color="orange" variant="light">Draft</Badge>}
                <StatusBadge status={s.today_status} />
              </Group>
            </Group>
            <Table>
              <Table.Tbody>
                {s.slots.map((slot) => (
                  <Table.Tr key={`${slot.day_of_week}-${slot.start_time}`}>
                    <Table.Td>{slot.day_label}</Table.Td>
                    <Table.Td>{slot.start_time.slice(0, 5)}–{slot.end_time.slice(0, 5)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            <Group mt="sm" gap="xs">
              {can("phc.schedule.update") && (
                <Button size="xs" variant="default" onClick={() => setEditing(s)}>Edit</Button>
              )}
              {can("phc.schedule.publish") && !s.is_published && (
                <Button size="xs" onClick={() => publish.mutate(s.id)}>Publish</Button>
              )}
              {can("phc.attendance.update") && (
                <>
                  <Button size="xs" color="green" variant="light"
                    onClick={() => attendance.mutate({ id: s.id, status: "available" })}>
                    Mark available
                  </Button>
                  <Button size="xs" color="gray" variant="light"
                    onClick={() => attendance.mutate({ id: s.id, status: "departed" })}>
                    Mark departed
                  </Button>
                </>
              )}
            </Group>
          </Card>
        ))}
      </Stack>
      {editing && <ScheduleForm editing={editing} onClose={() => setEditing(null)} />}
    </Container>
  );
}
