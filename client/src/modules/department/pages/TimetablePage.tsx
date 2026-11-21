import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaClock, FaMapMarkerAlt, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateTimetable,
  useDepartments,
  useTimetableSlots,
  useTimetables,
} from "../api/hooks";
import { AddTimetableSlotModal } from "../components/AddTimetableSlotModal";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function TimetablePage() {
  const { can } = useAuth();
  const { data: depts } = useDepartments();
  const defaultDept = depts?.[0];
  const deptId = defaultDept?.id;

  const { data: timetables, isPending: ttLoading, error: ttError } = useTimetables(deptId);
  const activeTimetable = timetables?.[0];
  const { data: slots, isPending: slotsLoading, error: slotsError } = useTimetableSlots(
    activeTimetable?.id
  );

  const createTimetable = useCreateTimetable();
  const [slotModal, setSlotModal] = useState(false);

  const canManage = can("department.timetable.manage");

  if (ttError || slotsError) {
    return <Container size="lg"><ErrorState error={ttError || slotsError} /></Container>;
  }

  const handleInitTimetable = async () => {
    if (!deptId) return;
    try {
      await createTimetable.mutateAsync({
        department: deptId,
        title: "Monsoon Semester 2026",
        academic_year: "2026-2027",
        programme: "BTech",
      });
      notifications.show({
        title: "Timetable Created",
        message: "New semester schedule created successfully.",
        color: "teal",
      });
    } catch {
      notifications.show({
        title: "Failed",
        message: "Could not create timetable schedule.",
        color: "red",
      });
    }
  };

  return (
    <Container size="lg">
      <PageHeader
        title="Department Timetable & Schedules"
        subtitle={
          activeTimetable
            ? `${activeTimetable.title} · ${activeTimetable.programme} (${activeTimetable.academic_year})`
            : "Classroom and lab scheduling"
        }
        action={
          <Group gap="xs">
            {!activeTimetable && canManage && deptId && (
              <Button
                leftSection={<FaPlus size={12} />}
                loading={createTimetable.isPending}
                onClick={handleInitTimetable}
              >
                Create Semester Schedule
              </Button>
            )}
            {activeTimetable && canManage && (
              <Button
                leftSection={<FaPlus size={12} />}
                onClick={() => setSlotModal(true)}
              >
                Add Schedule Slot
              </Button>
            )}
          </Group>
        }
      />

      {ttLoading && <Text c="dimmed">Loading schedule…</Text>}

      {!ttLoading && !activeTimetable && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={6}>
            <FaCalendarAlt size={28} color="var(--mantine-color-gray-5)" />
            <Title order={4}>No timetable defined</Title>
            <Text size="sm" c="dimmed">
              Department administrators can create the semester schedule above.
            </Text>
          </Stack>
        </Card>
      )}

      {activeTimetable && (
        <Stack gap="md">
          {slotsLoading && <Text c="dimmed">Loading slots…</Text>}

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            {DAYS.map((day) => {
              const daySlots = (slots || []).filter(
                (s) => s.day.toLowerCase() === day.toLowerCase()
              );
              return (
                <Card key={day} padding="md" withBorder>
                  <Group justify="space-between" mb="xs">
                    <Text fw={700} size="md">
                      {day}
                    </Text>
                    <Badge variant="light" size="xs">
                      {daySlots.length} session(s)
                    </Badge>
                  </Group>

                  {daySlots.length === 0 ? (
                    <Text size="xs" c="dimmed" fs="italic">
                      No classes scheduled.
                    </Text>
                  ) : (
                    <Stack gap="xs">
                      {daySlots.map((slot) => (
                        <Card key={slot.id} padding="xs" withBorder radius="sm">
                          <Group justify="space-between" align="flex-start">
                            <div>
                              <Text fw={600} size="sm">
                                {slot.subject}
                              </Text>
                              <Group gap="xs" mt={2}>
                                <Group gap={4}>
                                  <FaClock size={11} color="var(--mantine-color-gray-6)" />
                                  <Text size="xs" c="dimmed">
                                    {slot.start_time.slice(0, 5)} - {slot.end_time.slice(0, 5)}
                                  </Text>
                                </Group>
                                {slot.room && (
                                  <Group gap={4}>
                                    <FaMapMarkerAlt size={11} color="var(--mantine-color-gray-6)" />
                                    <Text size="xs" c="dimmed">
                                      {slot.room}
                                    </Text>
                                  </Group>
                                )}
                              </Group>
                            </div>

                            {slot.faculty_user_id && (
                              <Badge size="xs" variant="outline">
                                Faculty #{slot.faculty_user_id}
                              </Badge>
                            )}
                          </Group>
                        </Card>
                      ))}
                    </Stack>
                  )}
                </Card>
              );
            })}
          </SimpleGrid>
        </Stack>
      )}

      {activeTimetable && (
        <AddTimetableSlotModal
          opened={slotModal}
          onClose={() => setSlotModal(false)}
          timetableId={activeTimetable.id}
        />
      )}
    </Container>
  );
}
