import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBook, FaCalendarAlt, FaChalkboardTeacher, FaEdit } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourseDetail, useCourses, useUpdateCourse } from "../api/hooks";

export default function CoursesPage() {
  const { data: courses, isPending, error } = useCourses();
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [editing, setEditing] = useState(false);
  const [syllabus, setSyllabus] = useState("");
  const [scheduleInfo, setScheduleInfo] = useState("");

  const activeId = selectedCourseId ?? courses?.[0]?.course_id ?? null;
  const { data: courseDetail, isPending: isDetailPending } = useCourseDetail(activeId);
  const updateCourse = useUpdateCourse();
  const { can } = useAuth();
  const canUpdate = can("lms.workspace.update");

  if (error) {
    return (
      <Container size="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  const courseOptions = (courses ?? []).map((c) => ({
    value: String(c.course_id),
    label: `${c.course_code}: ${c.title} (${c.role})`,
  }));

  const startEdit = () => {
    if (courseDetail) {
      setSyllabus(courseDetail.syllabus || "");
      setScheduleInfo(courseDetail.schedule_info || "");
      setEditing(true);
    }
  };

  const handleUpdate = () => {
    if (!activeId) return;
    updateCourse.mutate(
      {
        courseId: activeId,
        syllabus,
        schedule_info: scheduleInfo,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Course Updated",
            message: "Course workspace details have been updated successfully.",
          });
          setEditing(false);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Update Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  };

  return (
    <Container size="md">
      <PageHeader
        title="Courses & Workspaces"
        subtitle="Manage syllabi, schedules, and view enrolled course details"
        action={
          canUpdate && courseDetail ? (
            <Button leftSection={<FaEdit size={14} />} onClick={startEdit}>
              Edit Course Details
            </Button>
          ) : undefined
        }
      />

      {isPending && <Text c="dimmed">Loading your enrolled courses…</Text>}

      {!isPending && (courses ?? []).length === 0 && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={8}>
            <FaBook size={28} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No active course enrollments found</Text>
            <Text size="sm" c="dimmed">
              You are not currently enrolled as a student, TA, observer, or instructor in any course.
            </Text>
          </Stack>
        </Card>
      )}

      {courseOptions.length > 0 && (
        <Stack gap="lg">
          <Select
            label="Select Active Course"
            data={courseOptions}
            value={activeId ? String(activeId) : null}
            onChange={(val) => setSelectedCourseId(val ? Number(val) : null)}
            allowDeselect={false}
          />

          {isDetailPending && <Text c="dimmed">Loading course workspace details…</Text>}

          {courseDetail && (
            <Stack gap="md">
              <Card padding="lg" withBorder>
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Group gap="xs">
                      <Text fw={700} size="xl">
                        {courseDetail.course_code}: {courseDetail.title}
                      </Text>
                      <Badge variant="filled" color="blue">
                        ID: {courseDetail.course_id}
                      </Badge>
                    </Group>
                    <Text size="sm" c="dimmed" mt={4}>
                      Official academic workspace
                    </Text>
                  </div>
                </Group>
              </Card>

              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <Card padding="lg" withBorder>
                  <Group gap="xs" mb="sm">
                    <FaBook color="var(--mantine-color-blue-6)" />
                    <Text fw={600}>Syllabus</Text>
                  </Group>
                  <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                    {courseDetail.syllabus || "No syllabus has been published yet."}
                  </Text>
                </Card>

                <Card padding="lg" withBorder>
                  <Group gap="xs" mb="sm">
                    <FaCalendarAlt color="var(--mantine-color-teal-6)" />
                    <Text fw={600}>Schedule & Venue</Text>
                  </Group>
                  <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                    {courseDetail.schedule_info || "No schedule information provided yet."}
                  </Text>
                </Card>
              </SimpleGrid>

              <Card padding="lg" withBorder>
                <Group gap="xs" mb="sm">
                  <FaChalkboardTeacher color="var(--mantine-color-indigo-6)" />
                  <Text fw={600}>Teaching Staff Roster</Text>
                </Group>
                <Stack gap="xs">
                  <div>
                    <Text size="sm" fw={500}>
                      Instructors:
                    </Text>
                    <Group gap="xs" mt={4}>
                      {courseDetail.instructors.length > 0 ? (
                        courseDetail.instructors.map((uid) => (
                          <Badge key={uid} variant="light" color="blue">
                            Faculty (User {uid})
                          </Badge>
                        ))
                      ) : (
                        <Text size="xs" c="dimmed">
                          None assigned
                        </Text>
                      )}
                    </Group>
                  </div>

                  <div>
                    <Text size="sm" fw={500}>
                      Teaching Assistants:
                    </Text>
                    <Group gap="xs" mt={4}>
                      {courseDetail.teaching_assistants.length > 0 ? (
                        courseDetail.teaching_assistants.map((uid) => (
                          <Badge key={uid} variant="light" color="grape">
                            TA (User {uid})
                          </Badge>
                        ))
                      ) : (
                        <Text size="xs" c="dimmed">
                          None assigned
                        </Text>
                      )}
                    </Group>
                  </div>
                </Stack>
              </Card>
            </Stack>
          )}
        </Stack>
      )}

      <FormModal
        opened={editing}
        onClose={() => setEditing(false)}
        title="Edit Course Workspace Details"
        subtitle="Update the syllabus and schedule information for this course"
        onSubmit={handleUpdate}
        submitting={updateCourse.isPending}
        submitLabel="Save Changes"
      >
        <Stack gap="md">
          <Textarea
            label="Syllabus"
            placeholder="Course outline, topics, textbook references..."
            autosize
            minRows={4}
            value={syllabus}
            onChange={(e) => setSyllabus(e.currentTarget.value)}
          />
          <TextInput
            label="Schedule & Venue"
            placeholder="e.g. MWF 10:00 - 11:00 AM, Lecture Hall 1"
            value={scheduleInfo}
            onChange={(e) => setScheduleInfo(e.currentTarget.value)}
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
