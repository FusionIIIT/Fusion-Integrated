import { useState } from "react";
import {
  Alert, Button, Card, Container, Group, Select, Stack, Text, TextInput, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCalendarAlt, FaInfoCircle, FaPlus, FaRegCalendarCheck,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateSchedule, useMaintainSchedule, usePublishSchedule, useSchedule,
} from "../api/hooks";
import type { DoctorSchedule } from "../api/types";

const DAYS = [
  { value: "0", label: "Monday" }, { value: "1", label: "Tuesday" },
  { value: "2", label: "Wednesday" }, { value: "3", label: "Thursday" },
  { value: "4", label: "Friday" }, { value: "5", label: "Saturday" },
  { value: "6", label: "Sunday" },
];

export default function StaffSchedulePage() {
  const { can } = useAuth();
  const canView = can("phc.schedule.view");
  const { data, isPending, error } = useSchedule(canView);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<DoctorSchedule | null>(null);
  const [drafts, setDrafts] = useState<DoctorSchedule[]>([]);
  const publish = usePublishSchedule();
  const canManage = can("phc.schedule.manage");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function doPublish(s: DoctorSchedule) {
    publish.mutate(s.id, {
      onSuccess: () => {
        setDrafts((prev) => prev.filter((d) => d.id !== s.id));
        notifications.show({
          color: "green", title: "Schedule published",
          message: `${s.doctor_name}'s slot is now visible to patients.`,
        });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not publish", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Manage Doctor Schedule"
        subtitle="Create weekly slots, maintain them, then publish for patients"
        action={canManage && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
            New slot
          </Button>
        )}
      />

      {canManage && (
        <Card padding="lg" mb="md">
          <Title order={5} mb="sm">Unpublished slots</Title>
          <DataTable<DoctorSchedule>
            rows={drafts}
            rowKey={(r) => r.id}
            minWidth={760}
            columns={[
              { key: "doctor", header: "Doctor",
                render: (r) => <Text fw={600}>{r.doctor_name}</Text> },
              { key: "day", header: "Day",
                render: (r) => DAYS[r.day_of_week]?.label ?? "—" },
              { key: "time", header: "Time",
                render: (r) => `${r.start_time} – ${r.end_time}` },
              {
                key: "action", header: "", align: "right",
                render: (r) => (
                  <Button
                    size="xs" variant="light" loading={publish.isPending}
                    onClick={() => doPublish(r)}
                  >
                    Publish
                  </Button>
                ),
              },
            ]}
            empty={{
              icon: FaRegCalendarCheck,
              title: "No unpublished slots",
              description: "Slots created here stay hidden until they are published.",
            }}
          />
        </Card>
      )}

      {!canView && (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
          The published list needs the schedule-view permission. Drafts created
          here are still shown above.
        </Alert>
      )}

      <Card padding="lg">
        <Title order={5} mb="sm">Published slots</Title>
        <DataTable<DoctorSchedule>
          rows={data?.schedules ?? []}
          loading={canView && isPending}
          rowKey={(r) => r.id}
          minWidth={820}
          columns={[
            { key: "doctor", header: "Doctor",
              render: (r) => <Text fw={600}>{r.doctor_name}</Text> },
            { key: "day", header: "Day",
              render: (r) => DAYS[r.day_of_week]?.label ?? "—" },
            { key: "time", header: "Time",
              render: (r) => `${r.start_time} – ${r.end_time}` },
            {
              key: "published", header: "Published",
              render: (r) => r.published_at
                ? new Date(r.published_at).toLocaleString() : "—",
            },
            {
              key: "actions", header: "", align: "right",
              render: (r) => canManage && (
                <Button size="xs" variant="subtle" onClick={() => setEditing(r)}>
                  Edit
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No published slots",
            description: "Create a slot above, then publish it for patients.",
          }}
        />
      </Card>

      {canManage && (
        <>
          <CreateModal
            opened={creating} onClose={() => setCreating(false)}
            onCreated={(s) => setDrafts((prev) => [...prev, s])}
          />
          <MaintainModal
            key={editing?.id ?? "none"}
            schedule={editing} onClose={() => setEditing(null)}
          />
        </>
      )}
    </Container>
  );
}

function CreateModal({ opened, onClose, onCreated }: {
  opened: boolean;
  onClose: () => void;
  onCreated: (s: DoctorSchedule) => void;
}) {
  const create = useCreateSchedule();
  const [name, setName] = useState("");
  const [day, setDay] = useState<string | null>("0");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Create a doctor slot"
      subtitle="Saved as a draft until you publish it"
      onSubmit={() => create.mutate(
        {
          doctor_name: name.trim(), day_of_week: Number(day),
          start_time: start, end_time: end,
        },
        {
          onSuccess: (s) => {
            onCreated(s);
            setName(""); setDay("0"); setStart(""); setEnd("");
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not create slot", message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Create" submitting={create.isPending}
      error={create.error}
      disabled={!name.trim() || day == null || !start || !end}
      disabledReason="A doctor, day and both times are required."
    >
      <Stack gap="md">
        <TextInput
          label="Doctor name" required value={name}
          onChange={(e) => setName(e.currentTarget.value)} maxLength={120}
        />
        <Select label="Day of week" required data={DAYS} value={day} onChange={setDay} />
        <Group grow>
          <TextInput
            label="Start time" type="time" required value={start}
            onChange={(e) => setStart(e.currentTarget.value)}
          />
          <TextInput
            label="End time" type="time" required value={end}
            onChange={(e) => setEnd(e.currentTarget.value)}
          />
        </Group>
      </Stack>
    </FormModal>
  );
}

function MaintainModal({ schedule, onClose }: {
  schedule: DoctorSchedule | null;
  onClose: () => void;
}) {
  const maintain = useMaintainSchedule();
  const [day, setDay] = useState<string | null>(
    schedule ? String(schedule.day_of_week) : null);
  const [start, setStart] = useState(schedule?.start_time.slice(0, 5) ?? "");
  const [end, setEnd] = useState(schedule?.end_time.slice(0, 5) ?? "");

  return (
    <FormModal
      opened={schedule != null} onClose={onClose}
      title={`Maintain ${schedule?.doctor_name ?? ""} slot`}
      subtitle="Changes are audited against the schedule id"
      onSubmit={() => schedule && maintain.mutate(
        {
          id: schedule.id, day_of_week: Number(day),
          start_time: start, end_time: end,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green", title: "Slot updated",
              message: "The published schedule has been refreshed.",
            });
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not update slot", message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Save changes" submitting={maintain.isPending}
      error={maintain.error}
      disabled={day == null || !start || !end}
    >
      <Stack gap="md">
        <TextInput label="Doctor name" value={schedule?.doctor_name ?? ""} disabled />
        <Select label="Day of week" required data={DAYS} value={day} onChange={setDay} />
        <Group grow>
          <TextInput
            label="Start time" type="time" required value={start}
            onChange={(e) => setStart(e.currentTarget.value)}
          />
          <TextInput
            label="End time" type="time" required value={end}
            onChange={(e) => setEnd(e.currentTarget.value)}
          />
        </Group>
      </Stack>
    </FormModal>
  );
}
