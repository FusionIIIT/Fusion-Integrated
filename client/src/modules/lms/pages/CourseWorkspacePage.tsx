import { useEffect, useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
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
  Table,
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
  FaBullhorn,
  FaCalendarAlt,
  FaChalkboardTeacher,
  FaClock,
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
  FaTasks,
  FaTrash,
  FaUserGraduate,
} from "react-icons/fa";


import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  type CourseAssignmentItem,
  type CourseMaterialItem,
  type CourseWorkspaceDetail,
  type CreateAssignmentPayload,
  type CreateMaterialPayload,
  type UpdateAssignmentPayload,
  type UpdateCourseWorkspacePayload,
  type UpdateMaterialPayload,
  useAssignmentDeadline,
  useAssignmentExtensions,
  useCourseAnnouncements,
  useCourseAssignments,
  useCourseMaterials,
  useCourses,
  useCourseWorkspace,
  useCreateAssignment,
  useCreateMaterial,
  useDeleteAssignment,
  useDeleteMaterial,
  useGrantExtension,
  usePostCourseAnnouncement,
  useRevokeExtension,
  useUpdateAssignment,
  useUpdateCourseWorkspace,
  useUpdateDeadlineWindow,
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

function renderWindowStatusBadge(status?: string) {
  switch (status) {
    case "open":
      return (
        <Badge color="green" variant="light">
          Window Open
        </Badge>
      );
    case "late_allowed":
      return (
        <Badge color="yellow" variant="light">
          Late Submissions Allowed
        </Badge>
      );
    case "closed":
      return (
        <Badge color="red" variant="light">
          Submissions Closed
        </Badge>
      );
    case "not_open":
    default:
      return (
        <Badge color="gray" variant="light">
          No Deadline
        </Badge>
      );
  }
}

function AssignmentDeadlineSection({
  courseCode,
  assignmentId,
}: {
  courseCode: string;
  assignmentId: number;
}) {
  const { data: deadline, isPending } = useAssignmentDeadline(courseCode, assignmentId);
  if (isPending || !deadline) return null;

  return (
    <Paper p="sm" withBorder radius="sm" bg="gray.0">
      <Group justify="space-between" align="center" mb={6}>
        <Text size="xs" fw={700} c="dimmed" tt="uppercase">
          Deadline & Submission Window
        </Text>
        {renderWindowStatusBadge(deadline.window_status)}
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
        <div>
          <Text size="xs" c="dimmed">
            Original Due Date
          </Text>
          <Text size="sm" fw={500}>
            {deadline.original_due_at
              ? new Date(deadline.original_due_at).toLocaleString()
              : "No due date set"}
          </Text>
        </div>
        <div>
          <Text size="xs" c="dimmed">
            Cutoff / Closes At
          </Text>
          <Text size="sm" fw={500}>
            {deadline.closes_at
              ? new Date(deadline.closes_at).toLocaleString()
              : "No hard cutoff (closes at due date)"}
          </Text>
        </div>
        <div>
          <Text size="xs" c="dimmed">
            Late Policy
          </Text>
          <Text size="sm" fw={500}>
            {deadline.allow_late
              ? "Late submissions permitted"
              : "Strict deadline — no late submissions"}
          </Text>
        </div>
        <div>
          <Text size="xs" c="dimmed">
            Your Effective Deadline
          </Text>
          <Text
            size="sm"
            fw={600}
            c={deadline.is_extended ? "violet.7" : undefined}
          >
            {deadline.effective_due_at
              ? new Date(deadline.effective_due_at).toLocaleString()
              : "None"}
          </Text>
        </div>
      </SimpleGrid>

      {deadline.is_extended && (
        <Alert color="violet" mt="xs" p="xs" title="Individual Extension Active">
          <Text size="xs">
            You have received an extension until{" "}
            <strong>
              {deadline.extended_due_at
                ? new Date(deadline.extended_due_at).toLocaleString()
                : ""}
            </strong>
            .{deadline.extension_reason && ` Reason: ${deadline.extension_reason}`}
          </Text>
        </Alert>
      )}

      {deadline.can_manage_deadlines && (
        <Text size="xs" c="dimmed" mt="xs">
          Total active extensions for this assignment: {deadline.total_extensions}
        </Text>
      )}
    </Paper>
  );
}

interface DeadlinesModalProps {
  opened: boolean;
  onClose: () => void;
  courseCode: string;
  assignment: CourseAssignmentItem | null;
}

function DeadlinesModal({ opened, onClose, courseCode, assignment }: DeadlinesModalProps) {
  const assignmentId = assignment?.id ?? null;
  const { data: deadlineInfo, isPending: deadlineLoading } = useAssignmentDeadline(
    courseCode,
    assignmentId,
  );
  const { data: extensions = [], isPending: extensionsLoading } = useAssignmentExtensions(
    courseCode,
    assignmentId,
    opened,
  );

  const updateWindowMutation = useUpdateDeadlineWindow();
  const grantExtensionMutation = useGrantExtension();
  const revokeExtensionMutation = useRevokeExtension();

  const [dueAt, setDueAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [allowLate, setAllowLate] = useState(false);

  const [targetUserId, setTargetUserId] = useState<string>("");
  const [extendedDueAt, setExtendedDueAt] = useState("");
  const [extensionReason, setExtensionReason] = useState("");

  useEffect(() => {
    if (assignment) {
      setDueAt(assignment.due_at ? assignment.due_at.slice(0, 16) : "");
      setClosesAt(assignment.closes_at ? assignment.closes_at.slice(0, 16) : "");
      setAllowLate(Boolean(assignment.allow_late));
    }
  }, [assignment, opened]);

  if (!assignment) return null;

  function handleSaveWindow() {
    if (!assignment) return;
    updateWindowMutation.mutate(
      {
        code: courseCode,
        assignmentId: assignment.id,
        body: {
          due_at: dueAt || null,
          closes_at: closesAt || null,
          allow_late: allowLate,
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Deadline Window Updated",
            message: "Submission window and deadline policies have been saved.",
            color: "teal",
          });
        },
        onError: (err) => {
          notifications.show({
            title: "Could not update deadline window",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  }

  function handleGrantExtension() {
    if (!assignment || !targetUserId || !extendedDueAt) {
      notifications.show({
        title: "Missing Information",
        message: "Please enter a student user ID and extended due date.",
        color: "yellow",
      });
      return;
    }
    const studentId = parseInt(targetUserId, 10);
    if (isNaN(studentId) || studentId <= 0) {
      notifications.show({
        title: "Invalid Student ID",
        message: "Student User ID must be a positive integer.",
        color: "yellow",
      });
      return;
    }

    grantExtensionMutation.mutate(
      {
        code: courseCode,
        assignmentId: assignment.id,
        body: {
          student_user_id: studentId,
          extended_due_at: extendedDueAt,
          reason: extensionReason.trim(),
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Extension Granted",
            message: `Deadline extension granted for student #${studentId}.`,
            color: "teal",
          });
          setTargetUserId("");
          setExtendedDueAt("");
          setExtensionReason("");
        },
        onError: (err) => {
          notifications.show({
            title: "Could not grant extension",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  }

  function handleRevokeExtension(extId: number, studentName: string) {
    if (!assignment) return;
    if (!window.confirm(`Revoke deadline extension for ${studentName}?`)) return;

    revokeExtensionMutation.mutate(
      {
        code: courseCode,
        assignmentId: assignment.id,
        extensionId: extId,
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Extension Revoked",
            message: `Deadline extension for ${studentName} was removed.`,
            color: "teal",
          });
        },
        onError: (err) => {
          notifications.show({
            title: "Could not revoke extension",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <FaClock size={16} />
          <Title order={4}>Deadline & Extension Management</Title>
        </Group>
      }
      size="lg"
      centered
    >
      <Stack gap="md">
        <div>
          <Text fw={600} size="md">
            {assignment.title}
          </Text>
          <Text size="xs" c="dimmed">
            Course: {courseCode} | Assignment ID: {assignment.id}
          </Text>
        </div>

        {deadlineLoading ? (
          <Group justify="center" p="md">
            <Loader size="sm" />
          </Group>
        ) : (
          <Paper p="sm" withBorder radius="sm" bg="gray.0">
            <Group justify="space-between" align="center">
              <div>
                <Text size="xs" c="dimmed">
                  Current Status
                </Text>
                <Text size="sm" fw={600}>
                  {deadlineInfo?.window_status
                    ? deadlineInfo.window_status.toUpperCase().replace("_", " ")
                    : "UNKNOWN"}
                </Text>
              </div>
              <div>{renderWindowStatusBadge(deadlineInfo?.window_status)}</div>
            </Group>
          </Paper>
        )}

        <Tabs defaultValue="window">
          <Tabs.List>
            <Tabs.Tab value="window">Submission Window</Tabs.Tab>
            <Tabs.Tab
              value="extensions"
              rightSection={
                extensions.length > 0 ? (
                  <Badge size="xs" circle variant="light" color="indigo">
                    {extensions.length}
                  </Badge>
                ) : null
              }
            >
              Student Extensions
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="window" pt="md">
            <Stack gap="md">
              <TextInput
                label="Assignment Due Date & Time"
                type="datetime-local"
                value={dueAt}
                onChange={(e) => setDueAt(e.currentTarget.value)}
                description="Standard deadline for all enrolled students without individual extensions."
              />

              <TextInput
                label="Window Cutoff / Closes At"
                type="datetime-local"
                value={closesAt}
                onChange={(e) => setClosesAt(e.currentTarget.value)}
                description="Hard cutoff timestamp after which no submissions are accepted."
              />

              <Checkbox
                label="Allow late submissions"
                description="When enabled, students can submit after the due date up until the closing cutoff."
                checked={allowLate}
                onChange={(e) => setAllowLate(e.currentTarget.checked)}
              />

              <Group justify="flex-end" mt="sm">
                <Button
                  color="indigo"
                  onClick={handleSaveWindow}
                  loading={updateWindowMutation.isPending}
                >
                  Save Window Settings
                </Button>
              </Group>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="extensions" pt="md">
            <Stack gap="md">
              <div>
                <Text size="sm" fw={600}>
                  Active Individual Extensions
                </Text>
                <Text size="xs" c="dimmed">
                  Extensions override the due date for specific students. Only faculty can grant or revoke extensions.
                </Text>
              </div>

              {extensionsLoading ? (
                <Loader size="sm" />
              ) : extensions.length === 0 ? (
                <Text size="sm" c="dimmed" fs="italic">
                  No individual extensions have been granted for this assignment.
                </Text>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Student</Table.Th>
                      <Table.Th>Extended Due Date</Table.Th>
                      <Table.Th>Reason</Table.Th>
                      <Table.Th>Granted By</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {extensions.map((ext) => (
                      <Table.Tr key={ext.id}>
                        <Table.Td>
                          <Text size="xs" fw={600}>
                            {ext.student_name}
                          </Text>
                          <Text size="xs" c="dimmed">
                            ID: {ext.user_id}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" fw={600} c="violet.7">
                            {new Date(ext.extended_due_at).toLocaleString()}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{ext.reason || "—"}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{ext.granted_by_name}</Text>
                        </Table.Td>
                        <Table.Td>
                          <ActionIcon
                            size="sm"
                            color="red"
                            variant="subtle"
                            title="Revoke Extension"
                            onClick={() => handleRevokeExtension(ext.id, ext.student_name)}
                            loading={revokeExtensionMutation.isPending}
                          >
                            <FaTrash size={12} />
                          </ActionIcon>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}

              <Divider my="xs" />

              <div>
                <Text size="sm" fw={600} mb="xs">
                  Grant Student Extension
                </Text>
                <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                  <TextInput
                    label="Student User ID"
                    placeholder="e.g. 2"
                    type="number"
                    value={targetUserId}
                    onChange={(e) => setTargetUserId(e.currentTarget.value)}
                    required
                  />
                  <TextInput
                    label="Extended Due Date & Time"
                    type="datetime-local"
                    value={extendedDueAt}
                    onChange={(e) => setExtendedDueAt(e.currentTarget.value)}
                    required
                  />
                </SimpleGrid>
                <TextInput
                  mt="sm"
                  label="Reason / Notes"
                  placeholder="e.g. Medical excuse, Dean approval"
                  value={extensionReason}
                  onChange={(e) => setExtensionReason(e.currentTarget.value)}
                />
                <Group justify="flex-end" mt="sm">
                  <Button
                    size="sm"
                    color="teal"
                    onClick={handleGrantExtension}
                    loading={grantExtensionMutation.isPending}
                  >
                    Grant Extension
                  </Button>
                </Group>
              </div>
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Modal>
  );
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

  const {
    data: announcementsData,
    isPending: announcementsLoading,
    error: announcementsError,
  } = useCourseAnnouncements(selectedCode);

  const {
    data: assignmentsData,
    isPending: assignmentsLoading,
    error: assignmentsError,
  } = useCourseAssignments(selectedCode);

  const updateMutation = useUpdateCourseWorkspace();
  const createMaterialMutation = useCreateMaterial();
  const updateMaterialMutation = useUpdateMaterial();
  const deleteMaterialMutation = useDeleteMaterial();
  const postAnnouncementMutation = usePostCourseAnnouncement();
  const createAssignmentMutation = useCreateAssignment();
  const updateAssignmentMutation = useUpdateAssignment();
  const deleteAssignmentMutation = useDeleteAssignment();

  const [editOpened, setEditOpened] = useState(false);
  const [editForm, setEditForm] = useState<UpdateCourseWorkspacePayload>({});

  // Announcements state
  const [postAnnouncementOpened, setPostAnnouncementOpened] = useState(false);
  const [announcementTitle, setAnnouncementTitle] = useState("");
  const [announcementContent, setAnnouncementContent] = useState("");

  // Assignment states
  const [addAssignmentOpened, setAddAssignmentOpened] = useState(false);
  const [addAssignmentForm, setAddAssignmentForm] = useState<CreateAssignmentPayload>({
    title: "",
    instructions: "",
    submission_type: "file",
    points_possible: 100,
    status: "draft",
    due_at: "",
    release_at: "",
    closes_at: "",
    allow_late: false,
    file: null,
  });

  const [editAssignmentOpened, setEditAssignmentOpened] = useState(false);
  const [editingAssignmentId, setEditingAssignmentId] = useState<number | null>(null);
  const [editAssignmentForm, setEditAssignmentForm] = useState<UpdateAssignmentPayload>({});

  const [assignmentDetailOpened, setAssignmentDetailOpened] = useState(false);
  const [viewingAssignment, setViewingAssignment] = useState<CourseAssignmentItem | null>(null);

  const [deadlineModalOpened, setDeadlineModalOpened] = useState(false);
  const [deadlineAssignment, setDeadlineAssignment] = useState<CourseAssignmentItem | null>(null);

  function openDeadlineModal(a: CourseAssignmentItem) {
    setDeadlineAssignment(a);
    setDeadlineModalOpened(true);
  }

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

  function handlePostAnnouncement() {
    if (!selectedCode) return;
    if (!announcementTitle.trim()) {
      notifications.show({
        title: "Validation error",
        message: "Announcement title cannot be empty.",
        color: "red",
      });
      return;
    }
    if (announcementTitle.trim().length > 200) {
      notifications.show({
        title: "Validation error",
        message: "Announcement title cannot exceed 200 characters.",
        color: "red",
      });
      return;
    }
    if (!announcementContent.trim()) {
      notifications.show({
        title: "Validation error",
        message: "Announcement content cannot be empty.",
        color: "red",
      });
      return;
    }

    postAnnouncementMutation.mutate(
      {
        code: selectedCode,
        body: {
          title: announcementTitle.trim(),
          content: announcementContent.trim(),
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Announcement Posted",
            message: "Course announcement posted successfully.",
            color: "teal",
          });
          setAnnouncementTitle("");
          setAnnouncementContent("");
          setPostAnnouncementOpened(false);
        },
        onError: (err) => {
          notifications.show({
            title: "Could not post announcement",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  }

  function handleCreateAssignment() {
    if (!selectedCode) return;
    if (!addAssignmentForm.title.trim()) {
      notifications.show({
        title: "Validation error",
        message: "Assignment title cannot be empty.",
        color: "red",
      });
      return;
    }
    createAssignmentMutation.mutate(
      { code: selectedCode, body: addAssignmentForm },
      {
        onSuccess: () => {
          notifications.show({
            title: "Assignment Created",
            message: "Course assignment has been created successfully.",
            color: "teal",
          });
          setAddAssignmentOpened(false);
          setAddAssignmentForm({
            title: "",
            instructions: "",
            submission_type: "file",
            points_possible: 100,
            status: "draft",
            due_at: "",
            release_at: "",
            closes_at: "",
            allow_late: false,
            file: null,
          });
        },
        onError: (err) => {
          notifications.show({
            title: "Could not create assignment",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  }

  function openEditAssignmentModal(a: CourseAssignmentItem) {
    setEditingAssignmentId(a.id);
    setEditAssignmentForm({
      title: a.title,
      instructions: a.instructions,
      submission_type: a.submission_type,
      points_possible: a.points_possible,
      status: a.status,
      due_at: a.due_at ? a.due_at.slice(0, 16) : "",
      release_at: a.release_at ? a.release_at.slice(0, 16) : "",
      closes_at: a.closes_at ? a.closes_at.slice(0, 16) : "",
      allow_late: a.allow_late ?? false,
      file: null,
    });
    setEditAssignmentOpened(true);
  }

  function handleSaveAssignment() {
    if (!selectedCode || editingAssignmentId === null) return;
    updateAssignmentMutation.mutate(
      {
        code: selectedCode,
        assignmentId: editingAssignmentId,
        body: editAssignmentForm,
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Assignment Updated",
            message: "Course assignment details updated successfully.",
            color: "teal",
          });
          setEditAssignmentOpened(false);
          setEditingAssignmentId(null);
        },
        onError: (err) => {
          notifications.show({
            title: "Could not update assignment",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  }

  function handleDeleteAssignment(assignmentId: number, title: string) {
    if (!selectedCode) return;
    if (!window.confirm(`Are you sure you want to delete assignment "${title}"?`)) {
      return;
    }
    deleteAssignmentMutation.mutate(
      { code: selectedCode, assignmentId },
      {
        onSuccess: () => {
          notifications.show({
            title: "Assignment Deleted",
            message: `Assignment "${title}" was removed.`,
            color: "teal",
          });
        },
        onError: (err) => {
          notifications.show({
            title: "Could not delete assignment",
            message: errorMessage(err),
            color: "red",
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
          <Tabs.Tab
            value="announcements"
            leftSection={<FaBullhorn size={14} />}
            rightSection={
              announcementsData?.total_count !== undefined ? (
                <Badge size="xs" variant="light" circle>
                  {announcementsData.total_count}
                </Badge>
              ) : null
            }
          >
            Announcements
          </Tabs.Tab>
          <Tabs.Tab
            value="assignments"
            leftSection={<FaTasks size={14} />}
            rightSection={
              assignmentsData?.total_count !== undefined ? (
                <Badge size="xs" variant="light" circle>
                  {assignmentsData.total_count}
                </Badge>
              ) : null
            }
          >
            Assignments
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

        {/* TAB 3: ANNOUNCEMENTS (CFR-LMS-005, UC-LMS-005, UC-LMS-006, BR-LMS-008) */}
        <Tabs.Panel value="announcements">
          <Stack gap="lg">
            <Group justify="space-between" align="center">
              <div>
                <Title order={3}>Course Announcements</Title>
                <Text size="sm" c="dimmed">
                  Official notices and updates for {workspace.code} - {workspace.title}
                </Text>
              </div>

              {announcementsData?.can_post ? (
                <Button
                  leftSection={<FaPlus size={14} />}
                  onClick={() => setPostAnnouncementOpened(true)}
                  color="indigo"
                >
                  Post Announcement
                </Button>
              ) : (
                <Badge variant="outline" color={roleBadgeColor(workspace.role)}>
                  {roleLabel(workspace.role)} (Read-only)
                </Badge>
              )}
            </Group>

            {announcementsLoading ? (
              <Group justify="center" p="xl">
                <Loader size="md" />
              </Group>
            ) : announcementsError ? (
              <Alert icon={<FaInfoCircle size={16} />} title="Error loading announcements" color="red">
                {errorMessage(announcementsError)}
              </Alert>
            ) : !announcementsData?.announcements || announcementsData.announcements.length === 0 ? (
              <Paper p="xl" withBorder radius="md" style={{ textAlign: "center" }}>
                <ThemeIcon size={48} radius="xl" color="gray" variant="light" mb="sm">
                  <FaBullhorn size={24} />
                </ThemeIcon>
                <Title order={4} mb="xs">
                  No Announcements Yet
                </Title>
                <Text size="sm" c="dimmed" maw={420} mx="auto">
                  There are currently no announcements posted for this course.
                  {announcementsData?.can_post
                    ? " Click 'Post Announcement' above to publish the first notice."
                    : " Check back later for updates from your course instructors."}
                </Text>
              </Paper>
            ) : (
              <Stack gap="md">
                {announcementsData.announcements.map((ann) => (
                  <Card key={ann.id} padding="lg" radius="md" withBorder shadow="xs">
                    <Group justify="space-between" align="flex-start" mb="xs">
                      <div>
                        <Title order={4}>{ann.title}</Title>
                        <Group gap="xs" mt={4}>
                          <Badge size="xs" variant="light" color={roleBadgeColor(ann.author_role)}>
                            {ann.author_name} ({roleLabel(ann.author_role)})
                          </Badge>
                          {ann.created_at && (
                            <Group gap={4}>
                              <FaCalendarAlt size={12} color="gray" />
                              <Text size="xs" c="dimmed">
                                {new Date(ann.created_at).toLocaleString(undefined, {
                                  dateStyle: "medium",
                                  timeStyle: "short",
                                })}
                              </Text>
                            </Group>
                          )}
                        </Group>
                      </div>
                    </Group>
                    <Divider my="sm" />
                    <Text size="sm" style={{ whiteSpace: "pre-line", lineHeight: 1.6 }}>
                      {ann.content}
                    </Text>
                  </Card>
                ))}
              </Stack>
            )}
          </Stack>
        </Tabs.Panel>

        {/* TAB 4: ASSIGNMENTS (CFR-LMS-006, CFR-LMS-007) */}
        <Tabs.Panel value="assignments">
          <Stack gap="lg">
            <Group justify="space-between" align="center">
              <div>
                <Title order={3}>Course Assignments</Title>
                <Text size="sm" c="dimmed">
                  Manage and view assignments, instructions, and due dates for {workspace.code} - {workspace.title}
                </Text>
              </div>

              {assignmentsData?.can_manage ? (
                <Button
                  leftSection={<FaPlus size={14} />}
                  onClick={() => setAddAssignmentOpened(true)}
                  color="indigo"
                >
                  Create Assignment
                </Button>
              ) : (
                <Badge variant="outline" color={roleBadgeColor(workspace.role)}>
                  {roleLabel(workspace.role)} (Read-only)
                </Badge>
              )}
            </Group>

            {assignmentsLoading ? (
              <Group justify="center" p="xl">
                <Loader size="md" />
              </Group>
            ) : assignmentsError ? (
              <Alert icon={<FaInfoCircle size={16} />} title="Error loading assignments" color="red">
                {errorMessage(assignmentsError)}
              </Alert>
            ) : !assignmentsData?.assignments || assignmentsData.assignments.length === 0 ? (
              <Paper p="xl" withBorder radius="md" style={{ textAlign: "center" }}>
                <ThemeIcon size={48} radius="xl" color="gray" variant="light" mb="sm">
                  <FaTasks size={24} />
                </ThemeIcon>
                <Title order={4} mb="xs">
                  No Assignments Yet
                </Title>
                <Text size="sm" c="dimmed" maw={420} mx="auto">
                  There are currently no assignments published for this course.
                  {assignmentsData?.can_manage
                    ? " Click 'Create Assignment' above to draft the first assignment."
                    : " Check back later for updates from your course instructors."}
                </Text>
              </Paper>
            ) : (
              <Stack gap="md">
                {assignmentsData.assignments.map((asg) => (
                  <Card key={asg.id} padding="lg" radius="md" withBorder shadow="xs">
                    <Group justify="space-between" align="flex-start" mb="xs">
                      <div>
                        <Group gap="sm" align="center">
                          <Title order={4}>{asg.title}</Title>
                          <Badge
                            size="sm"
                            variant="filled"
                            color={
                              asg.status === "published"
                                ? "green"
                                : asg.status === "scheduled"
                                ? "orange"
                                : "gray"
                            }
                          >
                            {asg.status.toUpperCase()}
                          </Badge>
                          <Badge size="sm" variant="light" color="blue">
                            {asg.submission_type === "file"
                              ? "File Upload"
                              : asg.submission_type === "text"
                              ? "Text Entry"
                              : "Link Submission"}
                          </Badge>
                          <Badge size="sm" variant="light" color="violet">
                            {asg.points_possible} pts
                          </Badge>
                        </Group>

                        <Group gap="md" mt={6} wrap="wrap">
                          {asg.due_at && (
                            <Group gap={4}>
                              <FaCalendarAlt size={12} color="gray" />
                              <Text size="xs" c="dimmed">
                                Due: {new Date(asg.due_at).toLocaleString(undefined, {
                                  dateStyle: "medium",
                                  timeStyle: "short",
                                })}
                              </Text>
                            </Group>
                          )}
                          {asg.closes_at && (
                            <Text size="xs" c="dimmed">
                              Cutoff: {new Date(asg.closes_at).toLocaleString(undefined, {
                                dateStyle: "medium",
                                timeStyle: "short",
                              })}
                            </Text>
                          )}
                          {asg.allow_late && (
                            <Badge size="xs" variant="outline" color="yellow">
                              Late Submissions Allowed
                            </Badge>
                          )}
                          {asg.release_at && asg.status === "scheduled" && (
                            <Text size="xs" c="orange">
                              Releases: {new Date(asg.release_at).toLocaleString(undefined, {
                                dateStyle: "medium",
                                timeStyle: "short",
                              })}
                            </Text>
                          )}
                        </Group>
                      </div>

                      {assignmentsData.can_manage && (
                        <Group gap="xs">
                          <ActionIcon
                            variant="subtle"
                            color="teal"
                            onClick={() => openDeadlineModal(asg)}
                            title="Manage Deadlines & Extensions"
                          >
                            <FaClock size={14} />
                          </ActionIcon>
                          <ActionIcon
                            variant="subtle"
                            color="blue"
                            onClick={() => openEditAssignmentModal(asg)}
                            title="Edit Assignment"
                          >
                            <FaEdit size={14} />
                          </ActionIcon>
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            onClick={() => handleDeleteAssignment(asg.id, asg.title)}
                            title="Delete Assignment"
                          >
                            <FaTrash size={14} />
                          </ActionIcon>
                        </Group>
                      )}
                    </Group>

                    <Divider my="sm" />

                    {asg.instructions ? (
                      <Text size="sm" lineClamp={3} style={{ whiteSpace: "pre-line", lineHeight: 1.6 }}>
                        {asg.instructions}
                      </Text>
                    ) : (
                      <Text size="sm" c="dimmed" fs="italic">
                        No instructions provided.
                      </Text>
                    )}

                    <Group justify="space-between" align="center" mt="md">
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<FaEye size={12} />}
                        onClick={() => {
                          setViewingAssignment(asg);
                          setAssignmentDetailOpened(true);
                        }}
                      >
                        View Details & Instructions
                      </Button>

                      {asg.has_file && (
                        <Button
                          component="a"
                          href={`/api/v1/lms/courses/${workspace.code}/assignments/${asg.id}/download`}
                          download={asg.file_name}
                          size="xs"
                          variant="light"
                          leftSection={<FaDownload size={12} />}
                        >
                          {asg.file_name || "Download Attachment"}
                        </Button>
                      )}
                    </Group>
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
      {/* Post Announcement Modal (Faculty only, UC-LMS-005) */}
      <Modal
        opened={postAnnouncementOpened}
        onClose={() => setPostAnnouncementOpened(false)}
        title={`Post Course Announcement (${workspace?.code})`}
        size="lg"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Announcement Title"
            placeholder="e.g. Midterm Exam Schedule and Room Assignments"
            value={announcementTitle}
            onChange={(e) => setAnnouncementTitle(e.currentTarget.value)}
            required
            maxLength={200}
            description="Clear and concise summary of the announcement (up to 200 characters)."
          />

          <Textarea
            label="Announcement Content"
            placeholder="Enter the full announcement details, instructions, or updates..."
            value={announcementContent}
            onChange={(e) => setAnnouncementContent(e.currentTarget.value)}
            minRows={6}
            required
            description="Plain text or markdown content visible course-wide to enrolled students, TAs, and observers."
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setPostAnnouncementOpened(false)}>
              Cancel
            </Button>
            <Button
              color="indigo"
              onClick={handlePostAnnouncement}
              loading={postAnnouncementMutation.isPending}
              leftSection={<FaBullhorn size={14} />}
            >
              Post Announcement
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Create Assignment Modal (Faculty only, UC-LMS-007, BR-LMS-009) */}
      <Modal
        opened={addAssignmentOpened}
        onClose={() => setAddAssignmentOpened(false)}
        title={`Create Assignment (${workspace?.code})`}
        size="lg"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Assignment Title"
            placeholder="e.g. Homework 1: ER Modeling and Relational Algebra"
            value={addAssignmentForm.title}
            onChange={(e) =>
              setAddAssignmentForm({ ...addAssignmentForm, title: e.currentTarget.value })
            }
            required
            maxLength={200}
          />

          <Textarea
            label="Instructions"
            placeholder="Detailed instructions, guidelines, requirements..."
            value={addAssignmentForm.instructions ?? ""}
            onChange={(e) =>
              setAddAssignmentForm({ ...addAssignmentForm, instructions: e.currentTarget.value })
            }
            minRows={4}
          />

          <Group grow>
            <Select
              label="Submission Type"
              value={addAssignmentForm.submission_type}
              data={[
                { value: "file", label: "File Upload" },
                { value: "text", label: "Text Entry" },
                { value: "link", label: "Website Link" },
              ]}
              onChange={(val) =>
                val &&
                setAddAssignmentForm({
                  ...addAssignmentForm,
                  submission_type: val as "file" | "text" | "link",
                })
              }
              required
            />

            <TextInput
              label="Points Possible"
              type="number"
              value={addAssignmentForm.points_possible ?? 100}
              onChange={(e) =>
                setAddAssignmentForm({
                  ...addAssignmentForm,
                  points_possible: Number(e.currentTarget.value) || 0,
                })
              }
              required
            />
          </Group>

          <Group grow>
            <Select
              label="Initial Status"
              value={addAssignmentForm.status}
              data={[
                { value: "draft", label: "Draft (not visible to students)" },
                { value: "published", label: "Published (immediately visible)" },
                { value: "scheduled", label: "Scheduled (released at specified date)" },
              ]}
              onChange={(val) =>
                val &&
                setAddAssignmentForm({
                  ...addAssignmentForm,
                  status: val as "draft" | "published" | "scheduled",
                })
              }
            />

            <TextInput
              label="Due Date & Time"
              type="datetime-local"
              value={addAssignmentForm.due_at ?? ""}
              onChange={(e) =>
                setAddAssignmentForm({ ...addAssignmentForm, due_at: e.currentTarget.value })
              }
            />
          </Group>

          <Group grow>
            <TextInput
              label="Cutoff / Closes At (Optional)"
              type="datetime-local"
              value={addAssignmentForm.closes_at ?? ""}
              onChange={(e) =>
                setAddAssignmentForm({ ...addAssignmentForm, closes_at: e.currentTarget.value })
              }
              description="Hard cutoff after which no submissions are accepted."
            />
            <Checkbox
              mt="xl"
              label="Allow late submissions"
              description="Permit submissions between due date and cutoff."
              checked={addAssignmentForm.allow_late ?? false}
              onChange={(e) =>
                setAddAssignmentForm({ ...addAssignmentForm, allow_late: e.currentTarget.checked })
              }
            />
          </Group>

          {addAssignmentForm.status === "scheduled" && (
            <TextInput
              label="Release Date & Time"
              type="datetime-local"
              value={addAssignmentForm.release_at ?? ""}
              onChange={(e) =>
                setAddAssignmentForm({ ...addAssignmentForm, release_at: e.currentTarget.value })
              }
              required
              description="Assignment remains hidden from students until this release timestamp."
            />
          )}

          <FileInput
            label="Optional Attachment"
            placeholder="Select file (e.g. worksheet, starter code, rubric)"
            value={addAssignmentForm.file ?? null}
            onChange={(file) => setAddAssignmentForm({ ...addAssignmentForm, file })}
            clearable
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAddAssignmentOpened(false)}>
              Cancel
            </Button>
            <Button
              color="indigo"
              onClick={handleCreateAssignment}
              loading={createAssignmentMutation.isPending}
            >
              Create Assignment
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Edit Assignment Modal (Faculty only, UC-LMS-007) */}
      <Modal
        opened={editAssignmentOpened}
        onClose={() => setEditAssignmentOpened(false)}
        title={`Edit Assignment (${workspace?.code})`}
        size="lg"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Assignment Title"
            value={editAssignmentForm.title ?? ""}
            onChange={(e) =>
              setEditAssignmentForm({ ...editAssignmentForm, title: e.currentTarget.value })
            }
            required
            maxLength={200}
          />

          <Textarea
            label="Instructions"
            value={editAssignmentForm.instructions ?? ""}
            onChange={(e) =>
              setEditAssignmentForm({
                ...editAssignmentForm,
                instructions: e.currentTarget.value,
              })
            }
            minRows={4}
          />

          <Group grow>
            <Select
              label="Submission Type"
              value={editAssignmentForm.submission_type ?? "file"}
              data={[
                { value: "file", label: "File Upload" },
                { value: "text", label: "Text Entry" },
                { value: "link", label: "Website Link" },
              ]}
              onChange={(val) =>
                val &&
                setEditAssignmentForm({
                  ...editAssignmentForm,
                  submission_type: val as "file" | "text" | "link",
                })
              }
            />

            <TextInput
              label="Points Possible"
              type="number"
              value={editAssignmentForm.points_possible ?? 100}
              onChange={(e) =>
                setEditAssignmentForm({
                  ...editAssignmentForm,
                  points_possible: Number(e.currentTarget.value) || 0,
                })
              }
            />
          </Group>

          <Group grow>
            <Select
              label="Status"
              value={editAssignmentForm.status ?? "draft"}
              data={[
                { value: "draft", label: "Draft" },
                { value: "published", label: "Published" },
                { value: "scheduled", label: "Scheduled" },
              ]}
              onChange={(val) =>
                val &&
                setEditAssignmentForm({
                  ...editAssignmentForm,
                  status: val as "draft" | "published" | "scheduled",
                })
              }
            />

            <TextInput
              label="Due Date & Time"
              type="datetime-local"
              value={editAssignmentForm.due_at ?? ""}
              onChange={(e) =>
                setEditAssignmentForm({ ...editAssignmentForm, due_at: e.currentTarget.value })
              }
            />
          </Group>

          <Group grow>
            <TextInput
              label="Cutoff / Closes At (Optional)"
              type="datetime-local"
              value={editAssignmentForm.closes_at ?? ""}
              onChange={(e) =>
                setEditAssignmentForm({ ...editAssignmentForm, closes_at: e.currentTarget.value })
              }
              description="Hard cutoff after which no submissions are accepted."
            />
            <Checkbox
              mt="xl"
              label="Allow late submissions"
              description="Permit submissions between due date and cutoff."
              checked={editAssignmentForm.allow_late ?? false}
              onChange={(e) =>
                setEditAssignmentForm({ ...editAssignmentForm, allow_late: e.currentTarget.checked })
              }
            />
          </Group>

          {editAssignmentForm.status === "scheduled" && (
            <TextInput
              label="Release Date & Time"
              type="datetime-local"
              value={editAssignmentForm.release_at ?? ""}
              onChange={(e) =>
                setEditAssignmentForm({
                  ...editAssignmentForm,
                  release_at: e.currentTarget.value,
                })
              }
            />
          )}

          <FileInput
            label="Replace Attachment"
            placeholder="Select replacement file"
            value={editAssignmentForm.file ?? null}
            onChange={(file) => setEditAssignmentForm({ ...editAssignmentForm, file })}
            clearable
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setEditAssignmentOpened(false)}>
              Cancel
            </Button>
            <Button
              color="indigo"
              onClick={handleSaveAssignment}
              loading={updateAssignmentMutation.isPending}
            >
              Save Changes
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* View Assignment Details Modal */}
      <Modal
        opened={assignmentDetailOpened}
        onClose={() => setAssignmentDetailOpened(false)}
        title={viewingAssignment?.title ?? "Assignment Details"}
        size="lg"
        centered
      >
        {viewingAssignment && (
          <Stack gap="md">
            <Group justify="space-between" align="center">
              <Group gap="xs">
                <Badge
                  size="sm"
                  color={
                    viewingAssignment.status === "published"
                      ? "green"
                      : viewingAssignment.status === "scheduled"
                      ? "orange"
                      : "gray"
                  }
                >
                  {viewingAssignment.status.toUpperCase()}
                </Badge>
                <Badge size="sm" variant="light" color="blue">
                  {viewingAssignment.submission_type === "file"
                    ? "File Upload"
                    : viewingAssignment.submission_type === "text"
                    ? "Text Entry"
                    : "Website Link"}
                </Badge>
                <Badge size="sm" variant="light" color="violet">
                  {viewingAssignment.points_possible} pts
                </Badge>
              </Group>

              {viewingAssignment.due_at && (
                <Text size="xs" c="dimmed">
                  Due: {new Date(viewingAssignment.due_at).toLocaleString()}
                </Text>
              )}
            </Group>

            <Divider />

            <div>
              <Text size="sm" fw={600} mb="xs">
                Instructions:
              </Text>
              <Paper p="md" withBorder radius="sm" bg="gray.0">
                <Text style={{ whiteSpace: "pre-line", lineHeight: 1.6 }} size="sm">
                  {viewingAssignment.instructions || "No instructions provided."}
                </Text>
              </Paper>
            </div>

            <AssignmentDeadlineSection
              courseCode={workspace.code}
              assignmentId={viewingAssignment.id}
            />

            {viewingAssignment.has_file && (
              <Group justify="space-between" align="center" mt="xs">
                <Text size="xs" c="dimmed">
                  Attachment: {viewingAssignment.file_name} ({formatBytes(viewingAssignment.file_size)})
                </Text>
                <Button
                  component="a"
                  href={`/api/v1/lms/courses/${workspace.code}/assignments/${viewingAssignment.id}/download`}
                  download={viewingAssignment.file_name}
                  size="xs"
                  variant="light"
                  leftSection={<FaDownload size={12} />}
                >
                  Download File
                </Button>
              </Group>
            )}

            <Group justify="space-between" mt="md">
              {assignmentsData?.can_manage && (
                <Button
                  variant="light"
                  color="teal"
                  leftSection={<FaClock size={14} />}
                  onClick={() => {
                    setAssignmentDetailOpened(false);
                    openDeadlineModal(viewingAssignment);
                  }}
                >
                  Manage Deadlines & Extensions
                </Button>
              )}
              <Button variant="default" onClick={() => setAssignmentDetailOpened(false)}>
                Close
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      <DeadlinesModal
        opened={deadlineModalOpened}
        onClose={() => {
          setDeadlineModalOpened(false);
          setDeadlineAssignment(null);
        }}
        courseCode={workspace?.code ?? ""}
        assignment={deadlineAssignment}
      />

    </Container>
  );
}
