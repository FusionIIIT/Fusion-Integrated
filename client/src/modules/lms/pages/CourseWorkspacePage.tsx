import { useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  FileInput,
  Grid,
  Group,
  Loader,
  Modal,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Tabs,
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
  FaDownload,
  FaEdit,
  FaEnvelope,
  FaExternalLinkAlt,
  FaEye,
  FaFileAlt,
  FaFolderOpen,
  FaInfoCircle,
  FaPlus,
  FaStickyNote,
  FaTrash,
  FaUserGraduate,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  type CourseMaterialItem,
  type CourseWorkspaceDetail,
  type CreateMaterialPayload,
  type UpdateCourseWorkspacePayload,
  type UpdateMaterialPayload,
  useCourses,
  useCourseMaterials,
  useCourseWorkspace,
  useCreateMaterial,
  useDeleteMaterial,
  useUpdateCourseWorkspace,
  useUpdateMaterial,
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

function formatBytes(bytes: number | null): string {
  if (!bytes || bytes === 0) return "";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
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

  const {
    data: materialsData,
    isPending: materialsLoading,
    error: materialsError,
  } = useCourseMaterials(selectedCode);

  const updateMutation = useUpdateCourseWorkspace();
  const createMaterialMutation = useCreateMaterial();
  const updateMaterialMutation = useUpdateMaterial();
  const deleteMaterialMutation = useDeleteMaterial();

  const [editOpened, setEditOpened] = useState(false);
  const [editForm, setEditForm] = useState<UpdateCourseWorkspacePayload>({});

  // Materials modal states
  const [addMaterialOpened, setAddMaterialOpened] = useState(false);
  const [addMaterialForm, setAddMaterialForm] = useState<CreateMaterialPayload>({
    title: "",
    section_title: "",
    section_type: "module",
    material_type: "file",
    status: "published",
    description: "",
    link_url: "",
    content: "",
    file: null,
    release_at: "",
  });

  const [editMaterialOpened, setEditMaterialOpened] = useState(false);
  const [editingMaterialId, setEditingMaterialId] = useState<number | null>(null);
  const [editMaterialForm, setEditMaterialForm] = useState<UpdateMaterialPayload>({});

  const [noteReaderOpened, setNoteReaderOpened] = useState(false);
  const [readingNote, setReadingNote] = useState<CourseMaterialItem | null>(null);

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

  function handleCreateMaterial() {
    if (!selectedCode) return;
    createMaterialMutation.mutate(
      { code: selectedCode, body: addMaterialForm },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Material Added",
            message: "Course material has been successfully added.",
          });
          setAddMaterialOpened(false);
          setAddMaterialForm({
            title: "",
            section_title: "",
            section_type: "module",
            material_type: "file",
            status: "published",
            description: "",
            link_url: "",
            content: "",
            file: null,
            release_at: "",
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Could not add material",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function openEditMaterialModal(m: CourseMaterialItem) {
    setEditingMaterialId(m.id);
    setEditMaterialForm({
      title: m.title,
      section_title: m.section_title,
      section_type: m.section_type,
      material_type: m.material_type,
      status: m.status,
      description: m.description,
      link_url: m.link_url,
      content: m.content,
      release_at: m.release_at ? m.release_at.substring(0, 16) : "",
    });
    setEditMaterialOpened(true);
  }

  function handleUpdateMaterial() {
    if (!selectedCode || !editingMaterialId) return;
    updateMaterialMutation.mutate(
      { code: selectedCode, materialId: editingMaterialId, body: editMaterialForm },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Material Updated",
            message: "Course material has been updated.",
          });
          setEditMaterialOpened(false);
          setEditingMaterialId(null);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Could not update material",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function handleDeleteMaterial(m: CourseMaterialItem) {
    if (!selectedCode) return;
    if (!window.confirm(`Are you sure you want to delete material "${m.title}"?`)) return;

    deleteMaterialMutation.mutate(
      { code: selectedCode, materialId: m.id },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Material Deleted",
            message: `Deleted "${m.title}".`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Could not delete material",
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
          You are viewing this workspace as an assigned Teaching Assistant (AFR-LMS-014.1). You have
          read-only access to course details and published materials. Course structure and material
          creation are managed by Faculty (AFR-LMS-014.2, AFR-LMS-014.5, BR-LMS-004).
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
          actions and unpublished materials are restricted (AFR-LMS-015.4, BR-LMS-003).
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

      {/* Workspace Navigation Tabs: Overview & Course Materials */}
      <Tabs defaultValue="overview" mb="xl">
        <Tabs.List mb="lg">
          <Tabs.Tab value="overview" leftSection={<FaBook size={14} />}>
            Course Overview
          </Tabs.Tab>
          <Tabs.Tab
            value="materials"
            leftSection={<FaFolderOpen size={14} />}
            rightSection={
              materialsData?.total_count !== undefined ? (
                <Badge size="xs" variant="light" circle>
                  {materialsData.total_count}
                </Badge>
              ) : null
            }
          >
            Course Materials
          </Tabs.Tab>
        </Tabs.List>

        {/* TAB 1: COURSE OVERVIEW (Syllabus, Schedule, Instructors & TAs) */}
        <Tabs.Panel value="overview">
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
        </Tabs.Panel>

        {/* TAB 2: COURSE MATERIALS (CFR-LMS-003, CFR-LMS-004) */}
        <Tabs.Panel value="materials">
          <Stack gap="lg">
            {/* Header controls for Materials tab */}
            <Group justify="space-between" align="center">
              <Stack gap={2}>
                <Title order={3}>Course Materials</Title>
                <Text size="sm" c="dimmed">
                  Organized curriculum materials, lecture notes, links, and documents (modules or
                  weekly sections)
                </Text>
              </Stack>

              {materialsData?.can_manage && (
                <Button
                  leftSection={<FaPlus size={14} />}
                  onClick={() => setAddMaterialOpened(true)}
                >
                  Add Course Material
                </Button>
              )}
            </Group>

            {materialsLoading ? (
              <Paper p="xl" withBorder style={{ textAlign: "center" }}>
                <Loader size="md" />
                <Text c="dimmed" mt="sm">
                  Loading course materials...
                </Text>
              </Paper>
            ) : materialsError ? (
              <ErrorState error={materialsError} />
            ) : !materialsData || materialsData.sections.length === 0 ? (
              <Paper p="xl" withBorder style={{ textAlign: "center" }}>
                <ThemeIcon size={56} radius="xl" color="blue" variant="light" mb="md">
                  <FaFolderOpen size={28} />
                </ThemeIcon>
                <Title order={4}>No materials available</Title>
                <Text c="dimmed" mt="xs">
                  {materialsData?.can_manage
                    ? "Click 'Add Course Material' above to upload files, share links, or post lecture notes."
                    : "No published course materials are currently available for this course."}
                </Text>
              </Paper>
            ) : (
              <Stack gap="xl">
                {materialsData.sections.map((sec) => (
                  <Card key={sec.section_title} padding="lg" radius="md" withBorder shadow="xs">
                    <Group justify="space-between" mb="md">
                      <Group gap="xs">
                        <ThemeIcon color="blue" variant="light" size="md">
                          <FaFolderOpen size={16} />
                        </ThemeIcon>
                        <Title order={4}>{sec.section_title}</Title>
                        <Badge size="sm" variant="outline" color="gray">
                          {sec.section_type === "week" ? "Weekly Section" : "Module"}
                        </Badge>
                      </Group>

                      <Text size="xs" c="dimmed">
                        {sec.materials.length} item{sec.materials.length === 1 ? "" : "s"}
                      </Text>
                    </Group>

                    <Divider mb="sm" />

                    <Stack gap="sm">
                      {sec.materials.map((m) => (
                        <Paper key={m.id} p="md" withBorder radius="sm">
                          <Group justify="space-between" align="flex-start">
                            <Group gap="md" align="flex-start">
                              <ThemeIcon
                                size="lg"
                                radius="md"
                                color={
                                  m.material_type === "file"
                                    ? "blue"
                                    : m.material_type === "link"
                                    ? "teal"
                                    : "violet"
                                }
                                variant="light"
                              >
                                {m.material_type === "file" ? (
                                  <FaFileAlt size={18} />
                                ) : m.material_type === "link" ? (
                                  <FaExternalLinkAlt size={16} />
                                ) : (
                                  <FaStickyNote size={18} />
                                )}
                              </ThemeIcon>

                              <Stack gap={3}>
                                <Group gap="xs">
                                  <Text fw={600} size="sm">
                                    {m.title}
                                  </Text>
                                  <Badge
                                    size="xs"
                                    variant="light"
                                    color={
                                      m.material_type === "file"
                                        ? "blue"
                                        : m.material_type === "link"
                                        ? "teal"
                                        : "violet"
                                    }
                                  >
                                    {m.material_type.toUpperCase()}
                                  </Badge>

                                  {/* Faculty visibility status badges */}
                                  {materialsData.can_manage && (
                                    <>
                                      {m.status === "draft" && (
                                        <Badge size="xs" color="yellow" variant="filled">
                                          Draft
                                        </Badge>
                                      )}
                                      {m.status === "scheduled" && (
                                        <Badge size="xs" color="indigo" variant="light">
                                          Scheduled
                                        </Badge>
                                      )}
                                      {m.status === "published" && (
                                        <Badge size="xs" color="green" variant="light">
                                          Published
                                        </Badge>
                                      )}
                                    </>
                                  )}
                                </Group>

                                {m.description && (
                                  <Text size="xs" c="dimmed">
                                    {m.description}
                                  </Text>
                                )}

                                {m.material_type === "file" && m.file_name && (
                                  <Text size="xs" c="dimmed">
                                    File: {m.file_name} {m.file_size ? `(${formatBytes(m.file_size)})` : ""}
                                  </Text>
                                )}

                                {m.material_type === "link" && m.link_url && (
                                  <Text size="xs" c="blue" style={{ wordBreak: "break-all" }}>
                                    {m.link_url}
                                  </Text>
                                )}

                                {m.status === "scheduled" && m.release_at && (
                                  <Text size="xs" c="indigo">
                                    Scheduled Release: {new Date(m.release_at).toLocaleString()}
                                  </Text>
                                )}
                              </Stack>
                            </Group>

                            {/* Action Buttons */}
                            <Group gap="xs">
                              {m.material_type === "file" && (
                                <Button
                                  component="a"
                                  href={`/api/v1/lms/courses/${workspace.code}/materials/${m.id}/download`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  size="xs"
                                  variant="light"
                                  color="blue"
                                  leftSection={<FaDownload size={12} />}
                                >
                                  Download
                                </Button>
                              )}

                              {m.material_type === "link" && (
                                <Button
                                  component="a"
                                  href={m.link_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  size="xs"
                                  variant="light"
                                  color="teal"
                                  leftSection={<FaExternalLinkAlt size={12} />}
                                >
                                  Open Link
                                </Button>
                              )}

                              {m.material_type === "note" && (
                                <Button
                                  size="xs"
                                  variant="light"
                                  color="violet"
                                  leftSection={<FaEye size={12} />}
                                  onClick={() => {
                                    setReadingNote(m);
                                    setNoteReaderOpened(true);
                                  }}
                                >
                                  Read Note
                                </Button>
                              )}

                              {materialsData.can_manage && (
                                <>
                                  <ActionIcon
                                    variant="subtle"
                                    color="gray"
                                    onClick={() => openEditMaterialModal(m)}
                                    title="Edit Material"
                                  >
                                    <FaEdit size={14} />
                                  </ActionIcon>
                                  <ActionIcon
                                    variant="subtle"
                                    color="red"
                                    onClick={() => handleDeleteMaterial(m)}
                                    title="Delete Material"
                                  >
                                    <FaTrash size={14} />
                                  </ActionIcon>
                                </>
                              )}
                            </Group>
                          </Group>
                        </Paper>
                      ))}
                    </Stack>
                  </Card>
                ))}
              </Stack>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>

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

      {/* Add Course Material Modal (CFR-LMS-003, AFR-LMS-003.1, AFR-LMS-003.2, AFR-LMS-003.3) */}
      <Modal
        opened={addMaterialOpened}
        onClose={() => setAddMaterialOpened(false)}
        title="Add Course Material"
        size="lg"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Material Title"
            placeholder="e.g. Lecture 1 Slides, Syllabus PDF, Reference Link..."
            required
            value={addMaterialForm.title}
            onChange={(e) =>
              setAddMaterialForm({ ...addMaterialForm, title: e.currentTarget.value })
            }
          />

          <Group grow>
            <TextInput
              label="Section Title"
              placeholder="e.g. Module 1: Foundations or Week 1"
              required
              value={addMaterialForm.section_title}
              onChange={(e) =>
                setAddMaterialForm({ ...addMaterialForm, section_title: e.currentTarget.value })
              }
            />

            <Select
              label="Section Organization Model"
              value={addMaterialForm.section_type}
              data={[
                { value: "module", label: "Module" },
                { value: "week", label: "Weekly Section" },
              ]}
              onChange={(val) =>
                val &&
                setAddMaterialForm({
                  ...addMaterialForm,
                  section_type: val as "module" | "week",
                })
              }
            />
          </Group>

          <Select
            label="Material Type"
            value={addMaterialForm.material_type}
            data={[
              { value: "file", label: "File Upload (PDF, Slides, Document)" },
              { value: "link", label: "Web Link / URL" },
              { value: "note", label: "Lecture Note / Text" },
            ]}
            onChange={(val) =>
              val &&
              setAddMaterialForm({
                ...addMaterialForm,
                material_type: val as "file" | "link" | "note",
              })
            }
          />

          {addMaterialForm.material_type === "file" && (
            <FileInput
              label="Select File"
              placeholder="Click to upload file"
              leftSection={<FaFileAlt size={14} />}
              value={addMaterialForm.file}
              onChange={(file) => setAddMaterialForm({ ...addMaterialForm, file })}
            />
          )}

          {addMaterialForm.material_type === "link" && (
            <TextInput
              label="Link URL"
              placeholder="https://example.com/materials"
              required
              value={addMaterialForm.link_url ?? ""}
              onChange={(e) =>
                setAddMaterialForm({ ...addMaterialForm, link_url: e.currentTarget.value })
              }
            />
          )}

          {addMaterialForm.material_type === "note" && (
            <Textarea
              label="Note Content"
              placeholder="Enter note text, reading guidelines, or key points..."
              required
              minRows={4}
              value={addMaterialForm.content ?? ""}
              onChange={(e) =>
                setAddMaterialForm({ ...addMaterialForm, content: e.currentTarget.value })
              }
            />
          )}

          <Textarea
            label="Description (Optional)"
            placeholder="Brief summary for students..."
            value={addMaterialForm.description ?? ""}
            onChange={(e) =>
              setAddMaterialForm({ ...addMaterialForm, description: e.currentTarget.value })
            }
          />

          <Select
            label="Publication Lifecycle"
            value={addMaterialForm.status}
            data={[
              { value: "published", label: "Publish Immediately (Visible to Students)" },
              { value: "draft", label: "Save as Draft (Restricted to Faculty)" },
              { value: "scheduled", label: "Schedule Future Release (AFR-LMS-003.3)" },
            ]}
            onChange={(val) =>
              val &&
              setAddMaterialForm({
                ...addMaterialForm,
                status: val as "draft" | "published" | "scheduled",
              })
            }
          />

          {addMaterialForm.status === "scheduled" && (
            <TextInput
              label="Scheduled Release Date & Time"
              type="datetime-local"
              description="Material will remain hidden from students until this release time is reached."
              required
              value={addMaterialForm.release_at ?? ""}
              onChange={(e) =>
                setAddMaterialForm({ ...addMaterialForm, release_at: e.currentTarget.value })
              }
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAddMaterialOpened(false)}>
              Cancel
            </Button>
            <Button
              loading={createMaterialMutation.isPending}
              onClick={handleCreateMaterial}
            >
              Add Material
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Edit Course Material Modal */}
      <Modal
        opened={editMaterialOpened}
        onClose={() => setEditMaterialOpened(false)}
        title="Edit Course Material"
        size="lg"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Material Title"
            required
            value={editMaterialForm.title ?? ""}
            onChange={(e) =>
              setEditMaterialForm({ ...editMaterialForm, title: e.currentTarget.value })
            }
          />

          <Group grow>
            <TextInput
              label="Section Title"
              required
              value={editMaterialForm.section_title ?? ""}
              onChange={(e) =>
                setEditMaterialForm({ ...editMaterialForm, section_title: e.currentTarget.value })
              }
            />

            <Select
              label="Section Organization Model"
              value={editMaterialForm.section_type ?? "module"}
              data={[
                { value: "module", label: "Module" },
                { value: "week", label: "Weekly Section" },
              ]}
              onChange={(val) =>
                val &&
                setEditMaterialForm({
                  ...editMaterialForm,
                  section_type: val as "module" | "week",
                })
              }
            />
          </Group>

          {editMaterialForm.material_type === "link" && (
            <TextInput
              label="Link URL"
              value={editMaterialForm.link_url ?? ""}
              onChange={(e) =>
                setEditMaterialForm({ ...editMaterialForm, link_url: e.currentTarget.value })
              }
            />
          )}

          {editMaterialForm.material_type === "note" && (
            <Textarea
              label="Note Content"
              minRows={4}
              value={editMaterialForm.content ?? ""}
              onChange={(e) =>
                setEditMaterialForm({ ...editMaterialForm, content: e.currentTarget.value })
              }
            />
          )}

          <Textarea
            label="Description"
            value={editMaterialForm.description ?? ""}
            onChange={(e) =>
              setEditMaterialForm({ ...editMaterialForm, description: e.currentTarget.value })
            }
          />

          <Select
            label="Publication Lifecycle"
            value={editMaterialForm.status ?? "published"}
            data={[
              { value: "published", label: "Published (Visible to Students)" },
              { value: "draft", label: "Draft (Restricted to Faculty)" },
              { value: "scheduled", label: "Scheduled Release" },
            ]}
            onChange={(val) =>
              val &&
              setEditMaterialForm({
                ...editMaterialForm,
                status: val as "draft" | "published" | "scheduled",
              })
            }
          />

          {editMaterialForm.status === "scheduled" && (
            <TextInput
              label="Scheduled Release Date & Time"
              type="datetime-local"
              value={editMaterialForm.release_at ?? ""}
              onChange={(e) =>
                setEditMaterialForm({ ...editMaterialForm, release_at: e.currentTarget.value })
              }
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setEditMaterialOpened(false)}>
              Cancel
            </Button>
            <Button
              loading={updateMaterialMutation.isPending}
              onClick={handleUpdateMaterial}
            >
              Save Changes
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Note Reader Modal */}
      <Modal
        opened={noteReaderOpened}
        onClose={() => setNoteReaderOpened(false)}
        title={readingNote ? `${readingNote.section_title} — ${readingNote.title}` : "Lecture Note"}
        size="lg"
        centered
      >
        {readingNote && (
          <Stack gap="md">
            {readingNote.description && (
              <Text size="sm" c="dimmed">
                {readingNote.description}
              </Text>
            )}
            <Divider />
            <Paper p="md" withBorder radius="sm" bg="gray.0">
              <Text style={{ whiteSpace: "pre-line" }} size="sm">
                {readingNote.content || "No content available."}
              </Text>
            </Paper>
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setNoteReaderOpened(false)}>
                Close
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
