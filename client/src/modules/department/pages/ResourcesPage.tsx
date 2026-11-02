import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Tabs, Text,
  TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateResource, useCreateTimetableEntry, useResources,
  useTimetable, useUpdateResource, useUpdateTimetableEntry,
} from "../api/hooks";
import type { ResourceProfile, TimetableEntry } from "../api/types";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const blankTimetable = {
  programme: "", academic_year: "", course: "", day: "1", starts_at: "",
  ends_at: "", room: "",
};

export default function ResourcesPage() {
  const { can } = useAuth();
  const resources = useResources();
  const canViewTimetable = can("department.timetable.view");
  const timetable = useTimetable(canViewTimetable);
  const createResource = useCreateResource();
  const updateResource = useUpdateResource();
  const createEntry = useCreateTimetableEntry();
  const updateEntry = useUpdateTimetableEntry();
  const [resourceName, setResourceName] = useState("");
  const [resourceDescription, setResourceDescription] = useState("");
  const [resourceLocation, setResourceLocation] = useState("");
  const [resourceEquipment, setResourceEquipment] = useState("");
  const [editingResource, setEditingResource] = useState<ResourceProfile | null>(null);
  const [slot, setSlot] = useState(blankTimetable);
  const [editingSlot, setEditingSlot] = useState<TimetableEntry | null>(null);
  const canManageResources = can("department.resource.manage");
  const canManageTimetable = can("department.timetable.manage");

  if (resources.error) return <Container size="md"><ErrorState error={resources.error} /></Container>;
  if (timetable.error) return <Container size="md"><ErrorState error={timetable.error} /></Container>;

  function saveResource() {
    const payload = {
      name: resourceName.trim(), description: resourceDescription,
      location: resourceLocation,
      equipment: resourceEquipment.split(",").map((x) => x.trim()).filter(Boolean),
    };
    const options = {
      onSuccess: () => {
        setResourceName(""); setResourceDescription(""); setResourceLocation("");
        setResourceEquipment(""); setEditingResource(null);
      },
      onError: (e: unknown) => notifications.show({
        color: "red", title: "Could not save resource", message: errorMessage(e),
      }),
    };
    if (editingResource) updateResource.mutate({ id: editingResource.id, payload }, options);
    else createResource.mutate(payload, options);
  }

  function editResource(row: ResourceProfile) {
    setEditingResource(row); setResourceName(row.name);
    setResourceDescription(row.description); setResourceLocation(row.location);
    setResourceEquipment(row.equipment.join(", "));
  }

  function saveTimetable() {
    const payload = { ...slot, day: Number(slot.day) };
    const options = {
      onSuccess: () => { setSlot(blankTimetable); setEditingSlot(null); },
      onError: (e: unknown) => notifications.show({
        color: "red", title: "Could not save timetable", message: errorMessage(e),
      }),
    };
    if (editingSlot) updateEntry.mutate({ id: editingSlot.id, payload }, options);
    else createEntry.mutate(payload, options);
  }

  function editTimetable(row: TimetableEntry) {
    setEditingSlot(row);
    setSlot({ ...row, day: String(row.day), starts_at: row.starts_at.slice(0, 5),
      ends_at: row.ends_at.slice(0, 5) });
  }

  return (
    <Container size="lg">
      <PageHeader title="Department resources"
        subtitle="Lab profiles support Faculty planning. Dept_Admin manages resources and timetables." />

      <Tabs defaultValue="resources">
        <Tabs.List mb="md">
          <Tabs.Tab value="resources">Lab resources</Tabs.Tab>
          {canViewTimetable && <Tabs.Tab value="timetable">Timetable</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel value="resources">
          <Stack gap="md">
            {canManageResources && (
              <Card withBorder padding="lg">
                <Stack>
                  <Text fw={700}>{editingResource ? "Edit lab resource" : "Add a lab resource"}</Text>
                  <Group grow>
                    <TextInput label="Resource or lab name" value={resourceName}
                      onChange={(e) => setResourceName(e.currentTarget.value)} />
                    <TextInput label="Location" value={resourceLocation}
                      onChange={(e) => setResourceLocation(e.currentTarget.value)} />
                  </Group>
                  <Textarea label="Description" value={resourceDescription}
                    onChange={(e) => setResourceDescription(e.currentTarget.value)} />
                  <TextInput label="Equipment" description="Separate items with commas."
                    value={resourceEquipment}
                    onChange={(e) => setResourceEquipment(e.currentTarget.value)} />
                  <Group>
                    <Button onClick={saveResource} disabled={!resourceName.trim()}
                      loading={createResource.isPending || updateResource.isPending}>
                      {editingResource ? "Save resource" : "Add resource"}
                    </Button>
                    {editingResource && <Button variant="default" onClick={() => {
                      setEditingResource(null); setResourceName(""); setResourceDescription("");
                      setResourceLocation(""); setResourceEquipment("");
                    }}>Cancel</Button>}
                  </Group>
                </Stack>
              </Card>
            )}
            {resources.isPending ? <Text c="dimmed">Loading resources…</Text>
              : (resources.data ?? []).length === 0
                ? <Card withBorder><Text c="dimmed">No lab resource profiles yet.</Text></Card>
                : (resources.data ?? []).map((row) => (
                  <Card key={row.id} withBorder padding="md">
                    <Group justify="space-between" align="flex-start">
                      <Stack gap={4}>
                        <Text fw={700}>{row.name}</Text>
                        {row.location && <Text size="sm" c="dimmed">{row.location}</Text>}
                        {row.description && <Text size="sm">{row.description}</Text>}
                        {row.equipment.length > 0 && <Text size="sm">Equipment: {row.equipment.join(", ")}</Text>}
                      </Stack>
                      {canManageResources && <Button size="xs" variant="light"
                        onClick={() => editResource(row)}>Edit</Button>}
                    </Group>
                  </Card>
                ))}
          </Stack>
        </Tabs.Panel>

        {canViewTimetable && <Tabs.Panel value="timetable">
          <Stack gap="md">
            {canManageTimetable && (
              <Card withBorder padding="lg">
                <Stack>
                  <Text fw={700}>{editingSlot ? "Modify timetable slot" : "Add a timetable slot"}</Text>
                  <Group grow>
                    <TextInput label="Course" value={slot.course}
                      onChange={(e) => setSlot({ ...slot, course: e.currentTarget.value })} />
                    <Select label="Day" data={DAYS.map((label, i) => ({ value: String(i + 1), label }))}
                      value={slot.day} onChange={(day) => setSlot({ ...slot, day: day ?? "1" })} />
                    <TextInput type="time" label="Starts" value={slot.starts_at}
                      onChange={(e) => setSlot({ ...slot, starts_at: e.currentTarget.value })} />
                    <TextInput type="time" label="Ends" value={slot.ends_at}
                      onChange={(e) => setSlot({ ...slot, ends_at: e.currentTarget.value })} />
                    <TextInput label="Room" value={slot.room}
                      onChange={(e) => setSlot({ ...slot, room: e.currentTarget.value })} />
                  </Group>
                  <Group grow>
                    <TextInput label="Programme" value={slot.programme}
                      onChange={(e) => setSlot({ ...slot, programme: e.currentTarget.value })} />
                    <TextInput label="Academic year" value={slot.academic_year}
                      onChange={(e) => setSlot({ ...slot, academic_year: e.currentTarget.value })} />
                  </Group>
                  <Group>
                    <Button onClick={saveTimetable}
                      loading={createEntry.isPending || updateEntry.isPending}
                      disabled={!slot.course.trim() || !slot.room.trim() || !slot.starts_at || !slot.ends_at}>
                      {editingSlot ? "Save timetable change" : "Add timetable slot"}
                    </Button>
                    {editingSlot && <Button variant="default" onClick={() => {
                      setSlot(blankTimetable); setEditingSlot(null);
                    }}>Cancel</Button>}
                  </Group>
                  <Text size="xs" c="dimmed">Overlapping room slots are blocked when saved.</Text>
                </Stack>
              </Card>
            )}
            {timetable.isPending ? <Text c="dimmed">Loading timetable…</Text>
              : (timetable.data ?? []).length === 0
                ? <Card withBorder><Text c="dimmed">No applicable timetable entries.</Text></Card>
                : (timetable.data ?? []).map((row) => (
                  <Card key={row.id} withBorder padding="md">
                    <Group justify="space-between">
                      <Stack gap={2}>
                        <Text fw={700}>{row.course} · {DAYS[row.day - 1]}</Text>
                        <Text size="sm">{row.starts_at.slice(0, 5)}–{row.ends_at.slice(0, 5)} · {row.room}</Text>
                        <Text size="xs" c="dimmed">{row.programme} {row.academic_year}</Text>
                      </Stack>
                      {canManageTimetable && <Button size="xs" variant="light"
                        onClick={() => editTimetable(row)}>Edit</Button>}
                    </Group>
                  </Card>
                ))}
          </Stack>
        </Tabs.Panel>}

      </Tabs>
    </Container>
  );
}
