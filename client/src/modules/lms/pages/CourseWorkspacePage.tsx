import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Grid,
  Group,
  Loader,
  Modal,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useSearchParams } from "react-router-dom";
import {
  FaArrowLeft,
  FaBook,
  FaCalendarAlt,
  FaChalkboardTeacher,
  FaEdit,
  FaEnvelope,
  FaEye,
  FaInfoCircle,
  FaUserGraduate,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  type CourseWorkspaceDetail,
  type UpdateCourseWorkspacePayload,
  useCourses,
  useCourseWorkspace,
  useUpdateCourseWorkspace,
} from "../api/hooks";

function roleBadgeColor(role: string): string {
  switch (role) {
    case "faculty":
      return "indigo";
    case "ta":
      return "cyan";
    case "observer":
      return "orange";
    case "student":
    default:
      return "teal";
  }
}

function roleLabel(role: string): string {
  switch (role) {
    case "faculty":
      return "Faculty Instructor";
    case "ta":
      return "Teaching Assistant";
    case "observer":
      return "Course Observer";
    case "student":
    default:
      return "Student";
  }
}

export default function CourseWorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedCode = searchParams.get("code");

  const { data: coursesData, isPending: coursesLoading, error: coursesError } = useCourses();
  const {
    data: workspace,
    isPending: workspaceLoading,
    error: workspaceError,
  } = useCourseWorkspace(selectedCode);

  const updateMutation = useUpdateCourseWorkspace();
  const [editOpened, setEditOpened] = useState(false);
  const [editForm, setEditForm] = useState<UpdateCourseWorkspacePayload>({});

  if (coursesError) {
    return (
      <Container size="xl">
        <ErrorState error={coursesError} />
      </Container>
    );
  }

  function handleSelectCourse(code: string) {
    setSearchParams({ code });
  }

  function handleBackToCourses() {
    setSearchParams({});
  }

  function openEditModal(ws: CourseWorkspaceDetail) {
    setEditForm({
      title: ws.title,
      description: ws.description,
      syllabus: ws.syllabus,
      schedule: ws.schedule,
      status: ws.status,
    });
    setEditOpened(true);
  }

  function handleSaveCourseDetails() {
    if (!selectedCode) return;
    updateMutation.mutate(
      { code: selectedCode, body: editForm },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Course details updated",
            message: "The course workspace configuration has been saved.",
          });
          setEditOpened(false);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Could not update course",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  // 1. Course Listing View (when no course code is selected)
  if (!selectedCode) {
    const courses = coursesData?.results ?? [];

    return (
      <Container size="xl">
        <PageHeader
          title="My Courses"
          subtitle="Access your active course workspaces, course details, syllabus, and schedules"
        />

        {coursesLoading ? (
          <Paper p="xl" withBorder style={{ textAlign: "center" }}>
            <Loader size="md" />
            <Text c="dimmed" mt="sm">
              Loading your course workspaces...
            </Text>
          </Paper>
        ) : courses.length === 0 ? (
          <Paper p="xl" withBorder style={{ textAlign: "center" }}>
            <ThemeIcon size={56} radius="xl" color="gray" variant="light" mb="md">
              <FaBook size={28} />
            </ThemeIcon>
            <Title order={4}>No courses found</Title>
            <Text c="dimmed" mt="xs">
              You are currently not enrolled in or assigned to any active course workspaces.
            </Text>
          </Paper>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
            {courses.map((c) => (
              <Card key={c.code} padding="lg" radius="md" withBorder shadow="sm">
                <Stack justify="space-between" h="100%">
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Badge color="blue" variant="filled" size="lg">
                        {c.code}
                      </Badge>
                      <Badge color={roleBadgeColor(c.role)} variant="light">
                        {roleLabel(c.role)}
                      </Badge>
                    </Group>

                    <Title order={4} mt="xs">
                      {c.title}
                    </Title>

                    {c.description && (
                      <Text c="dimmed" size="sm" lineClamp={2}>
                        {c.description}
                      </Text>
                    )}

                    {c.schedule && (
                      <Group gap="xs" mt="xs">
                        <ThemeIcon size="sm" variant="transparent" color="gray">
                          <FaCalendarAlt size={12} />
                        </ThemeIcon>
                        <Text size="xs" c="dimmed">
                          {c.schedule}
                        </Text>
                      </Group>
                    )}
                  </Stack>

                  <Button
                    mt="md"
                    variant="light"
                    color="blue"
                    fullWidth
                    onClick={() => handleSelectCourse(c.code)}
                  >
                    Enter Workspace
                  </Button>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </Container>
    );
  }

  // 2. Dedicated Course Workspace Detail View
  if (workspaceError) {
    return (
      <Container size="xl">
        <Button
          variant="subtle"
          leftSection={<FaArrowLeft size={12} />}
          onClick={handleBackToCourses}
          mb="md"
        >
          Back to My Courses
        </Button>
        <ErrorState error={workspaceError} />
      </Container>
    );
  }

  if (workspaceLoading || !workspace) {
    return (
      <Container size="xl">
        <Button
          variant="subtle"
          leftSection={<FaArrowLeft size={12} />}
          onClick={handleBackToCourses}
          mb="md"
        >
          Back to My Courses
        </Button>
        <Paper p="xl" withBorder style={{ textAlign: "center" }}>
          <Loader size="md" />
          <Text c="dimmed" mt="sm">
            Opening course workspace for {selectedCode}...
          </Text>
        </Paper>
      </Container>
    );
  }

  return (
    <Container size="xl">
      <Group justify="space-between" mb="md">
        <Button
          variant="subtle"
          leftSection={<FaArrowLeft size={12} />}
          onClick={handleBackToCourses}
        >
          Back to My Courses
        </Button>

        {coursesData?.results && coursesData.results.length > 1 && (
          <Select
            label="Switch Course"
            placeholder="Select another course"
            value={selectedCode}
            data={coursesData.results.map((c) => ({
              value: c.code,
              label: `${c.code}: ${c.title}`,
            }))}
            onChange={(val) => val && handleSelectCourse(val)}
            w={320}
          />
        )}
      </Group>

      {/* Role-specific banners for TA and Observer restrictions */}
      {workspace.role === "ta" && (
        <Alert
          icon={<FaInfoCircle size={16} />}
          title="Teaching Assistant Access"
          color="cyan"
          variant="light"
          mb="lg"
        >
          You are viewing this workspace as an assigned Teaching Assistant (AFR-LMS-014.1). Course
          structure and syllabus configuration are managed by Faculty (AFR-LMS-014.5).
        </Alert>
      )}

      {workspace.role === "observer" && (
        <Alert
          icon={<FaEye size={16} />}
          title="Observer Read-Only Access"
          color="orange"
          variant="light"
          mb="lg"
        >
          You are viewing this course as an Observer with read-only access (AFR-LMS-015.1). Write
          actions and individual student records are restricted (AFR-LMS-015.4, BR-LMS-003).
        </Alert>
      )}

      {/* Course Workspace Header */}
      <Paper p="lg" radius="md" withBorder shadow="xs" mb="lg">
        <Group justify="space-between" align="flex-start">
          <Stack gap="xs">
            <Group gap="xs">
              <Badge size="xl" color="blue" variant="filled">
                {workspace.code}
              </Badge>
              <StatusBadge status={workspace.status} />
              <Badge color={roleBadgeColor(workspace.role)} variant="light">
                {roleLabel(workspace.role)}
              </Badge>
            </Group>

            <Title order={2} mt="xs">
              {workspace.title}
            </Title>

            {workspace.description && (
              <Text c="dimmed" size="md">
                {workspace.description}
              </Text>
            )}
          </Stack>

          {workspace.can_edit && (
            <Button
              leftSection={<FaEdit size={14} />}
              onClick={() => openEditModal(workspace)}
            >
              Configure Course
            </Button>
          )}
        </Group>
      </Paper>

      {/* Main Workspace Grid: Syllabus, Schedule, Instructors & TAs */}
      <Grid gutter="lg">
        {/* Left Column: Syllabus & Schedule */}
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Stack gap="lg">
            {/* Syllabus Section (AFR-LMS-001.2) */}
            <Card padding="lg" radius="md" withBorder>
              <Group gap="xs" mb="sm">
                <ThemeIcon color="blue" variant="light" size="md">
                  <FaBook size={16} />
                </ThemeIcon>
                <Title order={3}>Course Syllabus</Title>
              </Group>
              <Divider mb="md" />

              {workspace.syllabus ? (
                <Text style={{ whiteSpace: "pre-line" }} size="sm">
                  {workspace.syllabus}
                </Text>
              ) : (
                <Text c="dimmed" fs="italic" size="sm">
                  No syllabus has been published for this course yet.
                </Text>
              )}
            </Card>

            {/* Schedule Section (AFR-LMS-001.2) */}
            <Card padding="lg" radius="md" withBorder>
              <Group gap="xs" mb="sm">
                <ThemeIcon color="teal" variant="light" size="md">
                  <FaCalendarAlt size={16} />
                </ThemeIcon>
                <Title order={3}>Class Schedule & Timings</Title>
              </Group>
              <Divider mb="md" />

              {workspace.schedule ? (
                <Text size="sm">{workspace.schedule}</Text>
              ) : (
                <Text c="dimmed" fs="italic" size="sm">
                  Class schedule has not been announced yet.
                </Text>
              )}
            </Card>
          </Stack>
        </Grid.Col>

        {/* Right Column: Instructors and Teaching Assistants */}
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Stack gap="lg">
            {/* Instructors Section (AFR-LMS-001.2) */}
            <Card padding="lg" radius="md" withBorder>
              <Group gap="xs" mb="sm">
                <ThemeIcon color="indigo" variant="light" size="md">
                  <FaChalkboardTeacher size={16} />
                </ThemeIcon>
                <Title order={4}>Instructors</Title>
              </Group>
              <Divider mb="md" />

              {workspace.instructors.length === 0 ? (
                <Text c="dimmed" size="xs">
                  No instructors assigned.
                </Text>
              ) : (
                <Stack gap="sm">
                  {workspace.instructors.map((ins) => (
                    <Paper key={ins.user_id} p="xs" withBorder radius="sm">
                      <Group justify="space-between">
                        <Stack gap={2}>
                          <Text fw={600} size="sm">
                            {ins.display_name}
                          </Text>
                          {ins.department && (
                            <Text size="xs" c="dimmed">
                              {ins.department}
                            </Text>
                          )}
                        </Stack>
                        {ins.email && (
                          <Button
                            component="a"
                            href={`mailto:${ins.email}`}
                            size="compact-xs"
                            variant="subtle"
                            leftSection={<FaEnvelope size={10} />}
                          >
                            Email
                          </Button>
                        )}
                      </Group>
                    </Paper>
                  ))}
                </Stack>
              )}
            </Card>

            {/* Teaching Assistants Section (AFR-LMS-001.2) */}
            <Card padding="lg" radius="md" withBorder>
              <Group gap="xs" mb="sm">
                <ThemeIcon color="cyan" variant="light" size="md">
                  <FaUserGraduate size={16} />
                </ThemeIcon>
                <Title order={4}>Teaching Assistants</Title>
              </Group>
              <Divider mb="md" />

              {workspace.teaching_assistants.length === 0 ? (
                <Text c="dimmed" size="xs">
                  No teaching assistants assigned.
                </Text>
              ) : (
                <Stack gap="sm">
                  {workspace.teaching_assistants.map((ta) => (
                    <Paper key={ta.user_id} p="xs" withBorder radius="sm">
                      <Group justify="space-between">
                        <Stack gap={2}>
                          <Text fw={600} size="sm">
                            {ta.display_name}
                          </Text>
                          {ta.department && (
                            <Text size="xs" c="dimmed">
                              {ta.department}
                            </Text>
                          )}
                        </Stack>
                        {ta.email && (
                          <Button
                            component="a"
                            href={`mailto:${ta.email}`}
                            size="compact-xs"
                            variant="subtle"
                            leftSection={<FaEnvelope size={10} />}
                          >
                            Email
                          </Button>
                        )}
                      </Group>
                    </Paper>
                  ))}
                </Stack>
              )}
            </Card>
          </Stack>
        </Grid.Col>
      </Grid>

      {/* Faculty Course Configuration Modal (AFR-LMS-002.1, AFR-LMS-002.2) */}
      <Modal
        opened={editOpened}
        onClose={() => setEditOpened(false)}
        title={`Configure Course Workspace (${workspace.code})`}
        size="lg"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Course Title"
            required
            value={editForm.title ?? ""}
            onChange={(e) => setEditForm({ ...editForm, title: e.currentTarget.value })}
          />

          <Textarea
            label="Course Description"
            value={editForm.description ?? ""}
            onChange={(e) => setEditForm({ ...editForm, description: e.currentTarget.value })}
            minRows={2}
          />

          <TextInput
            label="Class Schedule"
            placeholder="e.g. Mon/Wed 10:00 AM - 11:30 AM (Room L-201)"
            value={editForm.schedule ?? ""}
            onChange={(e) => setEditForm({ ...editForm, schedule: e.currentTarget.value })}
          />

          <Textarea
            label="Course Syllabus"
            placeholder="Outline weekly syllabus, lecture topics, reference books..."
            value={editForm.syllabus ?? ""}
            onChange={(e) => setEditForm({ ...editForm, syllabus: e.currentTarget.value })}
            minRows={5}
          />

          <Select
            label="Publication Status"
            value={editForm.status ?? "published"}
            data={[
              { value: "published", label: "Published (Visible to Enrolled Students)" },
              { value: "draft", label: "Draft (Restricted to Faculty)" },
            ]}
            onChange={(val) =>
              val && setEditForm({ ...editForm, status: val as "draft" | "published" })
            }
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setEditOpened(false)}>
              Cancel
            </Button>
            <Button
              loading={updateMutation.isPending}
              onClick={handleSaveCourseDetails}
            >
              Save Configuration
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
