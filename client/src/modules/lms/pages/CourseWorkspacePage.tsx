import { useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Divider,
  FileInput,
  Grid,
  Group,
  Modal,
  Paper,
  Select,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaArrowLeft,
  FaBook,
  FaBullhorn,
  FaCalendarAlt,
  FaClipboardList,
  FaClock,
  FaCog,
  FaDownload,
  FaExternalLinkAlt,
  FaFileAlt,
  FaPlus,
  FaThumbtack,
  FaTrash,
  FaUsers,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAddCourseMember,
  useCourse,
  useCourseAnnouncements,
  useCourseAssignments,
  useCourseMaterials,
  useCourseRoster,
  useCreateAnnouncement,
  useCreateAssignment,
  useCreateMaterial,
  useDeleteMaterial,
  useUpdateCourse,
} from "../api/hooks";
import type {
  CourseMaterial,
  MaterialType,
  Role,
  SubmissionType,
} from "../api/types";

const ROLE_COLORS: Record<string, string> = {
  faculty: "blue",
  ta: "violet",
  student: "teal",
  observer: "gray",
};

export default function CourseWorkspacePage({ courseIdProp }: { courseIdProp?: number } = {}) {
  const { courseId } = useParams<{ courseId: string }>();
  const [searchParams] = useSearchParams();
  const id = courseIdProp ?? Number(courseId || searchParams.get("courseId"));
  const navigate = useNavigate();
  const { session } = useAuth();
  const user = session?.user;

  const { data: course, isPending: coursePending, error: courseError } = useCourse(id);
  const { data: materials, isPending: materialsPending } = useCourseMaterials(id);
  const { data: announcements, isPending: announcementsPending } = useCourseAnnouncements(id);
  const { data: assignments, isPending: assignmentsPending } = useCourseAssignments(id);
  const { data: roster, isPending: rosterPending } = useCourseRoster(id);

  const updateCourse = useUpdateCourse(id);
  const createMaterial = useCreateMaterial(id);
  const deleteMaterial = useDeleteMaterial(0, id);
  const createAnnouncement = useCreateAnnouncement(id);
  const createAssignment = useCreateAssignment(id);
  const addMember = useAddCourseMember(id);

  // Modals
  const [settingsOpened, setSettingsOpened] = useState(false);
  const [materialModalOpened, setMaterialModalOpened] = useState(false);
  const [announcementModalOpened, setAnnouncementModalOpened] = useState(false);
  const [assignmentModalOpened, setAssignmentModalOpened] = useState(false);
  const [memberModalOpened, setMemberModalOpened] = useState(false);
  const [viewNoteModal, setViewNoteModal] = useState<CourseMaterial | null>(null);

  // Settings form
  const [editSyllabus, setEditSyllabus] = useState("");
  const [editSchedule, setEditSchedule] = useState("");
  const [editAllowTaAnnouncements, setEditAllowTaAnnouncements] = useState(false);
  const [editAllowTaGrading, setEditAllowTaGrading] = useState(false);

  // Material form
  const [matTitle, setMatTitle] = useState("");
  const [matType, setMatType] = useState<MaterialType>("note");
  const [matSection, setMatSection] = useState("General");
  const [matContent, setMatContent] = useState("");
  const [matLinkUrl, setMatLinkUrl] = useState("");
  const [matFile, setMatFile] = useState<File | null>(null);
  const [matStatus, setMatStatus] = useState("published");
  const [matReleaseDate, setMatReleaseDate] = useState("");

  // Announcement form
  const [ancTitle, setAncTitle] = useState("");
  const [ancContent, setAncContent] = useState("");
  const [ancPinned, setAncPinned] = useState(false);

  // Assignment form
  const [asgnTitle, setAsgnTitle] = useState("");
  const [asgnInstructions, setAsgnInstructions] = useState("");
  const [asgnType, setAsgnType] = useState<SubmissionType>("file");
  const [asgnPoints, setAsgnPoints] = useState(100);
  const [asgnDueDate, setAsgnDueDate] = useState("");
  const [asgnReleaseDate, setAsgnReleaseDate] = useState("");
  const [asgnStatus, setAsgnStatus] = useState("published");
  const [asgnAllowLate, setAsgnAllowLate] = useState(true);

  // Roster form
  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState<Role>("student");

  if (courseError) {
    return (
      <Container size="lg" py="md">
        <ErrorState error={courseError} />
      </Container>
    );
  }

  if (coursePending || !course) {
    return (
      <Container size="lg" py="md">
        <Text c="dimmed">Loading workspace...</Text>
      </Container>
    );
  }

  const role = (course.my_role || "student") as Role;
  const isFaculty = role === "faculty" || user?.kind === "faculty" || user?.kind === "admin";
  const isTa = role === "ta";
  const canAnnounce = isFaculty || (isTa && course.allow_ta_announcements);

  const handleOpenSettings = () => {
    setEditSyllabus(course.syllabus || "");
    setEditSchedule(course.schedule || "");
    setEditAllowTaAnnouncements(course.allow_ta_announcements);
    setEditAllowTaGrading(course.allow_ta_grading);
    setSettingsOpened(true);
  };

  const handleSaveSettings = () => {
    updateCourse.mutate(
      {
        syllabus: editSyllabus,
        schedule: editSchedule,
        allow_ta_announcements: editAllowTaAnnouncements,
        allow_ta_grading: editAllowTaGrading,
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Course settings saved",
            message: "Syllabus and delegation rules updated.",
            color: "green",
          });
          setSettingsOpened(false);
        },
        onError: (err) => {
          notifications.show({
            title: "Failed to save settings",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  };

  const handleCreateMaterial = () => {
    if (!matTitle.trim()) return;

    if (matType === "file" && matFile) {
      const formData = new FormData();
      formData.append("title", matTitle);
      formData.append("material_type", "file");
      formData.append("section", matSection);
      formData.append("status", matStatus);
      if (matReleaseDate) formData.append("release_date", new Date(matReleaseDate).toISOString());
      formData.append("file_attachment", matFile);

      createMaterial.mutate(formData, {
        onSuccess: () => {
          notifications.show({ title: "Material uploaded", message: "File material published.", color: "green" });
          setMaterialModalOpened(false);
          resetMatForm();
        },
        onError: (err) => {
          notifications.show({ title: "Upload failed", message: errorMessage(err), color: "red" });
        },
      });
    } else {
      createMaterial.mutate(
        {
          title: matTitle,
          material_type: matType,
          section: matSection,
          content: matContent,
          link_url: matLinkUrl,
          status: matStatus as any,
          release_date: matReleaseDate ? new Date(matReleaseDate).toISOString() : null,
        },
        {
          onSuccess: () => {
            notifications.show({ title: "Material added", message: "Course material has been added.", color: "green" });
            setMaterialModalOpened(false);
            resetMatForm();
          },
          onError: (err) => {
            notifications.show({ title: "Error creating material", message: errorMessage(err), color: "red" });
          },
        },
      );
    }
  };

  const resetMatForm = () => {
    setMatTitle("");
    setMatType("note");
    setMatSection("General");
    setMatContent("");
    setMatLinkUrl("");
    setMatFile(null);
    setMatStatus("published");
    setMatReleaseDate("");
  };

  const handleCreateAnnouncement = () => {
    if (!ancTitle.trim() || !ancContent.trim()) return;
    createAnnouncement.mutate(
      {
        title: ancTitle,
        content: ancContent,
        is_pinned: ancPinned,
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Announcement posted",
            message: "Broadcasted to enrolled students and staff.",
            color: "green",
          });
          setAnnouncementModalOpened(false);
          setAncTitle("");
          setAncContent("");
          setAncPinned(false);
        },
        onError: (err) => {
          notifications.show({
            title: "Failed to post",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  };

  const handleCreateAssignment = () => {
    if (!asgnTitle.trim() || !asgnInstructions.trim() || !asgnDueDate) return;
    createAssignment.mutate(
      {
        title: asgnTitle,
        instructions: asgnInstructions,
        submission_type: asgnType,
        points_possible: asgnPoints,
        due_date: new Date(asgnDueDate).toISOString(),
        release_date: asgnReleaseDate ? new Date(asgnReleaseDate).toISOString() : null,
        status: asgnStatus as any,
        allow_late_submissions: asgnAllowLate,
      },
      {
        onSuccess: (newAsgn) => {
          notifications.show({
            title: "Assignment created",
            message: `${newAsgn.title} is now active.`,
            color: "green",
          });
          setAssignmentModalOpened(false);
          setAsgnTitle("");
          setAsgnInstructions("");
          setAsgnDueDate("");
          setAsgnReleaseDate("");
        },
        onError: (err) => {
          notifications.show({
            title: "Failed to create assignment",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  };

  const handleAddMember = () => {
    const uid = parseInt(memberUserId, 10);
    if (!uid) return;
    addMember.mutate(
      { user_id: uid, role: memberRole },
      {
        onSuccess: () => {
          notifications.show({
            title: "Member added",
            message: `User ${uid} assigned role ${memberRole.toUpperCase()}.`,
            color: "green",
          });
          setMemberModalOpened(false);
          setMemberUserId("");
        },
        onError: (err) => {
          notifications.show({
            title: "Failed to enroll member",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  };

  return (
    <Container size="lg" py="md">
      {/* Back button */}
      <Button
        variant="subtle"
        size="xs"
        leftSection={<FaArrowLeft size={12} />}
        onClick={() => navigate("/lms/courses")}
        mb="xs"
      >
        Back to Courses
      </Button>

      {/* Header Banner */}
      <Card
        withBorder
        padding="lg"
        radius="md"
        mb="lg"
        style={{
          background: "linear-gradient(135deg, #10192e 0%, #1e3a5f 100%)",
          color: "#fff",
        }}
      >
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <div>
            <Group gap="xs" mb={4}>
              <Badge variant="filled" color="indigo" size="md">
                {course.code}
              </Badge>
              <Badge color={ROLE_COLORS[role] ?? "gray"} variant="filled" size="md">
                {role.toUpperCase()}
              </Badge>
              {!course.is_active && (
                <Badge color="red" variant="filled" size="md">
                  INACTIVE
                </Badge>
              )}
            </Group>
            <Title order={2} style={{ color: "#fff" }}>
              {course.name}
            </Title>
            <Text size="sm" c="rgba(255, 255, 255, 0.75)" mt={2}>
              <FaCalendarAlt style={{ verticalAlign: "middle", marginRight: 6 }} />
              {course.semester} {course.academic_year}
            </Text>
          </div>

          {isFaculty && (
            <Button
              variant="light"
              color="gray"
              leftSection={<FaCog size={14} />}
              onClick={handleOpenSettings}
              styles={{ root: { backgroundColor: "rgba(255,255,255,0.15)", color: "#fff" } }}
            >
              Course Settings
            </Button>
          )}
        </Group>
      </Card>

      {/* Main Tabbed Interface */}
      <Tabs defaultValue="overview" color="indigo">
        <Tabs.List mb="md">
          <Tabs.Tab value="overview" leftSection={<FaBook size={14} />}>
            Overview &amp; Syllabus
          </Tabs.Tab>
          <Tabs.Tab value="materials" leftSection={<FaFileAlt size={14} />}>
            Course Materials ({materials?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="announcements" leftSection={<FaBullhorn size={14} />}>
            Announcements ({announcements?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="assignments" leftSection={<FaClipboardList size={14} />}>
            Assignments ({assignments?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="roster" leftSection={<FaUsers size={14} />}>
            Roster &amp; Staff ({roster?.length ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Overview & Syllabus */}
        <Tabs.Panel value="overview">
          <Grid>
            <Grid.Col span={{ base: 12, md: 8 }}>
              <Card withBorder padding="lg" radius="md" mb="md">
                <Title order={4} mb="xs">
                  Syllabus &amp; Course Outline
                </Title>
                <Divider mb="sm" />
                <Text style={{ whiteSpace: "pre-wrap" }} size="sm">
                  {course.syllabus || "No syllabus has been uploaded or configured for this course yet."}
                </Text>
              </Card>

              <Card withBorder padding="lg" radius="md">
                <Title order={4} mb="xs">
                  Weekly Class &amp; Lab Schedule
                </Title>
                <Divider mb="sm" />
                <Text style={{ whiteSpace: "pre-wrap" }} size="sm">
                  {course.schedule || "Class timings and lecture hall schedule have not been posted."}
                </Text>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 4 }}>
              <Card withBorder padding="md" radius="md" mb="md">
                <Title order={5} mb="xs">
                  Instructional Staff
                </Title>
                <Divider mb="sm" />
                <Stack gap="xs">
                  <Text fw={600} size="sm">
                    Instructors:
                  </Text>
                  {course.instructors.map((inst) => (
                    <Group key={inst.user_id} justify="space-between">
                      <Text size="sm">User #{inst.user_id}</Text>
                      {inst.is_primary && (
                        <Badge size="xs" color="blue">
                          Primary
                        </Badge>
                      )}
                    </Group>
                  ))}
                  <Divider my={4} />
                  <Text fw={600} size="sm">
                    Teaching Assistants:
                  </Text>
                  {course.tas.length === 0 && (
                    <Text size="xs" c="dimmed">
                      No TAs assigned yet.
                    </Text>
                  )}
                  {course.tas.map((ta) => (
                    <Text key={ta.user_id} size="sm">
                      User #{ta.user_id}
                    </Text>
                  ))}
                </Stack>
              </Card>

              {isFaculty && (
                <Card withBorder padding="md" radius="md">
                  <Title order={5} mb="xs">
                    Delegation Policies
                  </Title>
                  <Divider mb="sm" />
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Text size="xs">TA Announcements:</Text>
                      <Badge color={course.allow_ta_announcements ? "green" : "gray"} size="xs">
                        {course.allow_ta_announcements ? "ALLOWED" : "RESTRICTED"}
                      </Badge>
                    </Group>
                    <Group justify="space-between">
                      <Text size="xs">TA Grading:</Text>
                      <Badge color={course.allow_ta_grading ? "green" : "gray"} size="xs">
                        {course.allow_ta_grading ? "ALLOWED" : "RESTRICTED"}
                      </Badge>
                    </Group>
                  </Stack>
                </Card>
              )}
            </Grid.Col>
          </Grid>
        </Tabs.Panel>

        {/* Tab 2: Materials */}
        <Tabs.Panel value="materials">
          <Group justify="space-between" mb="md">
            <div>
              <Title order={4}>Course Content &amp; Modules</Title>
              <Text size="xs" c="dimmed">
                Lecture notes, reference links, and laboratory manuals
              </Text>
            </div>
            {isFaculty && (
              <Button
                leftSection={<FaPlus size={12} />}
                size="sm"
                color="indigo"
                onClick={() => setMaterialModalOpened(true)}
              >
                Add Material
              </Button>
            )}
          </Group>

          {materialsPending && <Text c="dimmed">Loading course materials...</Text>}

          {!materialsPending && (!materials || materials.length === 0) && (
            <Card withBorder padding="xl" style={{ textAlign: "center" }}>
              <ThemeIcon size={40} radius="xl" color="gray" variant="light" mb="xs">
                <FaFileAlt size={20} />
              </ThemeIcon>
              <Text fw={600}>No materials published</Text>
              <Text size="xs" c="dimmed">
                Instructional resources for this course will appear here once released.
              </Text>
            </Card>
          )}

          <Stack gap="sm">
            {materials?.map((m) => (
              <Card key={m.id} withBorder padding="md" radius="md">
                <Group justify="space-between" align="center" wrap="nowrap">
                  <Group gap="sm" style={{ flex: 1 }}>
                    <ThemeIcon
                      size={36}
                      radius="md"
                      color={
                        m.material_type === "link"
                          ? "cyan"
                          : m.material_type === "file"
                            ? "orange"
                            : "blue"
                      }
                      variant="light"
                    >
                      {m.material_type === "link" ? (
                        <FaExternalLinkAlt size={16} />
                      ) : (
                        <FaFileAlt size={16} />
                      )}
                    </ThemeIcon>
                    <div>
                      <Group gap="xs">
                        <Text fw={600} size="sm">
                          {m.title}
                        </Text>
                        <Badge size="xs" variant="outline" color="gray">
                          {m.section}
                        </Badge>
                        <StatusBadge status={m.status} />
                        {m.release_date && (
                          <Text size="xs" c="dimmed">
                            <FaClock style={{ verticalAlign: "middle", marginRight: 4 }} />
                            Release: {new Date(m.release_date).toLocaleDateString()}
                          </Text>
                        )}
                      </Group>
                      {m.material_type === "file" && (
                        <Text size="xs" c="dimmed">
                          Attachment: {m.file_name} ({(m.file_size / 1024).toFixed(1)} KB)
                        </Text>
                      )}
                      {m.material_type === "note" && (
                        <Text size="xs" c="dimmed" lineClamp={1}>
                          {m.content}
                        </Text>
                      )}
                    </div>
                  </Group>

                  <Group gap="xs">
                    {m.material_type === "link" && (
                      <Button
                        component="a"
                        href={m.link_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        size="xs"
                        variant="light"
                        leftSection={<FaExternalLinkAlt size={11} />}
                      >
                        Open Link
                      </Button>
                    )}
                    {m.material_type === "note" && (
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => setViewNoteModal(m)}
                      >
                        Read Note
                      </Button>
                    )}
                    {m.material_type === "file" && (
                      <Button
                        component="a"
                        href={`/media/lms/materials/${m.file_name}`}
                        download
                        size="xs"
                        variant="light"
                        leftSection={<FaDownload size={11} />}
                      >
                        Download
                      </Button>
                    )}
                    {isFaculty && (
                      <ActionIcon
                        color="red"
                        variant="subtle"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Delete material "${m.title}"?`)) {
                            deleteMaterial.mutate(undefined, {
                              onSuccess: () => notifications.show({ title: "Deleted", message: "Material deleted.", color: "green" }),
                            });
                          }
                        }}
                      >
                        <FaTrash size={12} />
                      </ActionIcon>
                    )}
                  </Group>
                </Group>
              </Card>
            ))}
          </Stack>
        </Tabs.Panel>

        {/* Tab 3: Announcements */}
        <Tabs.Panel value="announcements">
          <Group justify="space-between" mb="md">
            <div>
              <Title order={4}>Course Announcements</Title>
              <Text size="xs" c="dimmed">
                Updates and important deadlines broadcasted to the course
              </Text>
            </div>
            {canAnnounce && (
              <Button
                leftSection={<FaPlus size={12} />}
                size="sm"
                color="indigo"
                onClick={() => setAnnouncementModalOpened(true)}
              >
                Post Announcement
              </Button>
            )}
          </Group>

          {announcementsPending && <Text c="dimmed">Loading announcements...</Text>}

          {!announcementsPending && (!announcements || announcements.length === 0) && (
            <Card withBorder padding="xl" style={{ textAlign: "center" }}>
              <ThemeIcon size={40} radius="xl" color="gray" variant="light" mb="xs">
                <FaBullhorn size={20} />
              </ThemeIcon>
              <Text fw={600}>No announcements posted</Text>
              <Text size="xs" c="dimmed">
                Course notifications will appear here.
              </Text>
            </Card>
          )}

          <Stack gap="md">
            {announcements?.map((a) => (
              <Card
                key={a.id}
                withBorder
                padding="md"
                radius="md"
                style={
                  a.is_pinned
                    ? { borderLeft: "4px solid var(--mantine-color-indigo-6)" }
                    : undefined
                }
              >
                <Group justify="space-between" align="flex-start" mb="xs">
                  <Group gap="xs">
                    {a.is_pinned && (
                      <Badge color="indigo" variant="filled" size="sm" leftSection={<FaThumbtack size={10} />}>
                        PINNED
                      </Badge>
                    )}
                    <Text fw={700} size="md">
                      {a.title}
                    </Text>
                  </Group>
                  <Text size="xs" c="dimmed">
                    {new Date(a.created_at).toLocaleString()}
                  </Text>
                </Group>

                <Text size="sm" style={{ whiteSpace: "pre-wrap" }} mb="sm">
                  {a.content}
                </Text>

                <Divider mb="xs" />
                <Group justify="space-between">
                  <Text size="xs" c="dimmed">
                    Posted by: <strong>{a.posted_by_name || `User #${a.posted_by_user_id}`}</strong>
                  </Text>
                  <Badge size="xs" color={ROLE_COLORS[a.posted_by_role] ?? "gray"} variant="light">
                    {a.posted_by_role.toUpperCase()}
                  </Badge>
                </Group>
              </Card>
            ))}
          </Stack>
        </Tabs.Panel>

        {/* Tab 4: Assignments */}
        <Tabs.Panel value="assignments">
          <Group justify="space-between" mb="md">
            <div>
              <Title order={4}>Course Assignments</Title>
              <Text size="xs" c="dimmed">
                Required tasks, homework, and laboratory submissions
              </Text>
            </div>
            {isFaculty && (
              <Button
                leftSection={<FaPlus size={12} />}
                size="sm"
                color="indigo"
                onClick={() => setAssignmentModalOpened(true)}
              >
                Create Assignment
              </Button>
            )}
          </Group>

          {assignmentsPending && <Text c="dimmed">Loading assignments...</Text>}

          {!assignmentsPending && (!assignments || assignments.length === 0) && (
            <Card withBorder padding="xl" style={{ textAlign: "center" }}>
              <ThemeIcon size={40} radius="xl" color="gray" variant="light" mb="xs">
                <FaClipboardList size={20} />
              </ThemeIcon>
              <Text fw={600}>No assignments posted</Text>
              <Text size="xs" c="dimmed">
                Assignments created for this course will appear here.
              </Text>
            </Card>
          )}

          <Stack gap="sm">
            {assignments?.map((asgn) => {
              const mySub = asgn.my_submission;
              return (
                <Card
                  key={asgn.id}
                  withBorder
                  padding="md"
                  radius="md"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/lms/assignments?assignmentId=${asgn.id}`)}
                >
                  <Group justify="space-between" align="center" wrap="nowrap">
                    <div style={{ flex: 1 }}>
                      <Group gap="xs" mb={2}>
                        <Text fw={700} size="md">
                          {asgn.title}
                        </Text>
                        <StatusBadge status={asgn.status} />
                        <Badge size="xs" variant="outline" color="gray">
                          {asgn.submission_type.toUpperCase()}
                        </Badge>
                      </Group>
                      <Group gap="md">
                        <Text size="xs" c="dimmed">
                          Points: <strong>{asgn.points_possible}</strong>
                        </Text>
                        <Text size="xs" c="dimmed">
                          Due: <strong>{new Date(asgn.due_date).toLocaleString()}</strong>
                        </Text>
                        {isFaculty && (
                          <Text size="xs" c="indigo">
                            Submissions: <strong>{asgn.submissions_count ?? 0}</strong>
                          </Text>
                        )}
                      </Group>
                    </div>

                    <Group gap="xs">
                      {role === "student" && (
                        <div>
                          {mySub ? (
                            <Badge color="green" variant="light" size="md">
                              Submitted {mySub.status === "late" ? "(Late)" : ""}
                            </Badge>
                          ) : (
                            <Badge color="orange" variant="light" size="md">
                              Pending
                            </Badge>
                          )}
                        </div>
                      )}
                      <Button variant="subtle" size="xs" color="indigo">
                        {isFaculty || isTa ? "View & Grade &rarr;" : "View Details &rarr;"}
                      </Button>
                    </Group>
                  </Group>
                </Card>
              );
            })}
          </Stack>
        </Tabs.Panel>

        {/* Tab 5: Roster */}
        <Tabs.Panel value="roster">
          <Group justify="space-between" mb="md">
            <div>
              <Title order={4}>Course Members &amp; Roster</Title>
              <Text size="xs" c="dimmed">
                Enrolled students, instructors, teaching assistants, and observers
              </Text>
            </div>
            {isFaculty && (
              <Button
                leftSection={<FaPlus size={12} />}
                size="sm"
                color="indigo"
                onClick={() => setMemberModalOpened(true)}
              >
                Enroll Member
              </Button>
            )}
          </Group>

          {rosterPending && <Text c="dimmed">Loading roster...</Text>}

          <Table highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>User ID</Table.Th>
                <Table.Th>Name / Identity</Table.Th>
                <Table.Th>Email</Table.Th>
                <Table.Th>Course Role</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Enrolled On</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {roster?.map((m) => (
                <Table.Tr key={m.id}>
                  <Table.Td>#{m.user_id}</Table.Td>
                  <Table.Td>
                    {m.user_display_name || `User #${m.user_id}`}
                    {m.is_primary_instructor && (
                      <Badge size="xs" color="blue" ml="xs">
                        Primary Instructor
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>{m.user_email || "—"}</Table.Td>
                  <Table.Td>
                    <Badge color={ROLE_COLORS[m.role] ?? "gray"} variant="light" size="sm">
                      {m.role.toUpperCase()}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={m.is_active ? "green" : "gray"} size="xs">
                      {m.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{new Date(m.created_at).toLocaleDateString()}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Tabs.Panel>
      </Tabs>

      {/* Course Settings Modal */}
      <FormModal
        opened={settingsOpened}
        onClose={() => setSettingsOpened(false)}
        title="Course Settings"
        subtitle={`Configure policies and content for ${course.code}`}
        onSubmit={handleSaveSettings}
        submitLabel="Save Changes"
        submitting={updateCourse.isPending}
      >
        <Stack gap="md">
          <Textarea
            label="Syllabus"
            placeholder="Course syllabus..."
            rows={4}
            value={editSyllabus}
            onChange={(e) => setEditSyllabus(e.currentTarget.value)}
          />

          <Textarea
            label="Class &amp; Lab Schedule"
            placeholder="Class days, time, lecture room..."
            rows={3}
            value={editSchedule}
            onChange={(e) => setEditSchedule(e.currentTarget.value)}
          />

          <Group justify="space-between">
            <div>
              <Text size="sm" fw={600}>
                TA Announcements
              </Text>
              <Text size="xs" c="dimmed">
                Allow teaching assistants to post announcements (BR-LMS-007)
              </Text>
            </div>
            <Switch
              checked={editAllowTaAnnouncements}
              onChange={(e) => setEditAllowTaAnnouncements(e.currentTarget.checked)}
            />
          </Group>

          <Group justify="space-between">
            <div>
              <Text size="sm" fw={600}>
                TA Grading Authority
              </Text>
              <Text size="xs" c="dimmed">
                Allow teaching assistants to evaluate submissions (BR-LMS-017)
              </Text>
            </div>
            <Switch
              checked={editAllowTaGrading}
              onChange={(e) => setEditAllowTaGrading(e.currentTarget.checked)}
            />
          </Group>
        </Stack>
      </FormModal>

      {/* Add Material Modal */}
      <FormModal
        opened={materialModalOpened}
        onClose={() => setMaterialModalOpened(false)}
        title="Add Course Material"
        subtitle="Publish notes, web links, or file documents"
        onSubmit={handleCreateMaterial}
        submitLabel="Add Material"
        submitting={createMaterial.isPending}
        disabled={!matTitle.trim()}
        disabledReason="Material Title is required."
      >
        <Stack gap="md">
          <TextInput
            label="Title"
            placeholder="e.g. Lecture 03 - Normalization"
            required
            value={matTitle}
            onChange={(e) => setMatTitle(e.currentTarget.value)}
          />

          <Grid>
            <Grid.Col span={6}>
              <Select
                label="Material Type"
                data={[
                  { value: "note", label: "Note / Markdown" },
                  { value: "link", label: "External Link" },
                  { value: "file", label: "File Upload" },
                ]}
                value={matType}
                onChange={(v) => setMatType((v as MaterialType) || "note")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Module / Section"
                placeholder="e.g. Week 1, Lab 2, Reference"
                value={matSection}
                onChange={(e) => setMatSection(e.currentTarget.value)}
              />
            </Grid.Col>
          </Grid>

          {matType === "note" && (
            <Textarea
              label="Content / Text"
              placeholder="Enter note or lecture summary..."
              rows={4}
              required
              value={matContent}
              onChange={(e) => setMatContent(e.currentTarget.value)}
            />
          )}

          {matType === "link" && (
            <TextInput
              label="Link URL"
              placeholder="https://..."
              required
              value={matLinkUrl}
              onChange={(e) => setMatLinkUrl(e.currentTarget.value)}
            />
          )}

          {matType === "file" && (
            <FileInput
              label="File Attachment"
              placeholder="Choose file (.pdf, .zip, .docx...)"
              required
              value={matFile}
              onChange={setMatFile}
            />
          )}

          <Grid>
            <Grid.Col span={6}>
              <Select
                label="Publication Status"
                data={[
                  { value: "published", label: "Published" },
                  { value: "draft", label: "Draft (hidden from students)" },
                ]}
                value={matStatus}
                onChange={(v) => setMatStatus(v || "published")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Scheduled Release Date (Optional)"
                type="datetime-local"
                value={matReleaseDate}
                onChange={(e) => setMatReleaseDate(e.currentTarget.value)}
              />
            </Grid.Col>
          </Grid>
        </Stack>
      </FormModal>

      {/* Post Announcement Modal */}
      <FormModal
        opened={announcementModalOpened}
        onClose={() => setAnnouncementModalOpened(false)}
        title="Post Course Announcement"
        subtitle="Broadcast notification to all enrolled users"
        onSubmit={handleCreateAnnouncement}
        submitLabel="Post Announcement"
        submitting={createAnnouncement.isPending}
        disabled={!ancTitle.trim() || !ancContent.trim()}
        disabledReason="Title and Content are required."
      >
        <Stack gap="md">
          <TextInput
            label="Announcement Title"
            placeholder="e.g. Quiz 1 Rescheduled"
            required
            value={ancTitle}
            onChange={(e) => setAncTitle(e.currentTarget.value)}
          />

          <Textarea
            label="Content"
            placeholder="Provide full details of the announcement..."
            rows={4}
            required
            value={ancContent}
            onChange={(e) => setAncContent(e.currentTarget.value)}
          />

          <Group justify="space-between">
            <div>
              <Text size="sm" fw={600}>
                Pin Announcement
              </Text>
              <Text size="xs" c="dimmed">
                Keep this announcement stickied at the top of the course board
              </Text>
            </div>
            <Switch checked={ancPinned} onChange={(e) => setAncPinned(e.currentTarget.checked)} />
          </Group>
        </Stack>
      </FormModal>

      {/* Create Assignment Modal */}
      <FormModal
        opened={assignmentModalOpened}
        onClose={() => setAssignmentModalOpened(false)}
        title="Create Assignment"
        subtitle="Specify instructions, deadlines, and submission rules"
        onSubmit={handleCreateAssignment}
        submitLabel="Create Assignment"
        submitting={createAssignment.isPending}
        disabled={!asgnTitle.trim() || !asgnInstructions.trim() || !asgnDueDate}
        disabledReason="Title, Instructions, and Due Date are mandatory."
      >
        <Stack gap="md">
          <TextInput
            label="Assignment Title"
            placeholder="e.g. Lab 4: Query Optimization"
            required
            value={asgnTitle}
            onChange={(e) => setAsgnTitle(e.currentTarget.value)}
          />

          <Textarea
            label="Instructions &amp; Problem Statement"
            placeholder="Detailed instructions for the assignment..."
            rows={4}
            required
            value={asgnInstructions}
            onChange={(e) => setAsgnInstructions(e.currentTarget.value)}
          />

          <Grid>
            <Grid.Col span={6}>
              <Select
                label="Submission Mode"
                data={[
                  { value: "file", label: "File Upload (.zip, .pdf, code)" },
                  { value: "text", label: "Text Response" },
                  { value: "link", label: "Repository / Drive Link" },
                ]}
                value={asgnType}
                onChange={(v) => setAsgnType((v as SubmissionType) || "file")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Points Possible"
                type="number"
                min={1}
                required
                value={asgnPoints}
                onChange={(e) => setAsgnPoints(parseInt(e.currentTarget.value, 10) || 100)}
              />
            </Grid.Col>
          </Grid>

          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="Due Date &amp; Time"
                type="datetime-local"
                required
                value={asgnDueDate}
                onChange={(e) => setAsgnDueDate(e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Scheduled Release Date (Optional)"
                type="datetime-local"
                value={asgnReleaseDate}
                onChange={(e) => setAsgnReleaseDate(e.currentTarget.value)}
              />
            </Grid.Col>
          </Grid>

          <Grid>
            <Grid.Col span={6}>
              <Select
                label="Status"
                data={[
                  { value: "published", label: "Published (Visible immediately)" },
                  { value: "draft", label: "Draft (Saved privately)" },
                ]}
                value={asgnStatus}
                onChange={(v) => setAsgnStatus(v || "published")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <Group justify="space-between" mt="lg">
                <div>
                  <Text size="sm" fw={600}>
                    Allow Late Submissions
                  </Text>
                  <Text size="xs" c="dimmed">
                    Mark as Late after deadline
                  </Text>
                </div>
                <Switch
                  checked={asgnAllowLate}
                  onChange={(e) => setAsgnAllowLate(e.currentTarget.checked)}
                />
              </Group>
            </Grid.Col>
          </Grid>
        </Stack>
      </FormModal>

      {/* Enroll Member Modal */}
      <FormModal
        opened={memberModalOpened}
        onClose={() => setMemberModalOpened(false)}
        title="Enroll Course Member"
        subtitle="Add a student, teaching assistant, or observer"
        onSubmit={handleAddMember}
        submitLabel="Enroll Member"
        submitting={addMember.isPending}
        disabled={!memberUserId.trim()}
        disabledReason="User ID is required."
      >
        <Stack gap="md">
          <TextInput
            label="User ID"
            placeholder="e.g. 101"
            type="number"
            required
            value={memberUserId}
            onChange={(e) => setMemberUserId(e.currentTarget.value)}
          />

          <Select
            label="Role in Course"
            data={[
              { value: "student", label: "Student" },
              { value: "ta", label: "Teaching Assistant (TA)" },
              { value: "observer", label: "Observer (Read-only auditor)" },
              { value: "faculty", label: "Co-Instructor (Faculty)" },
            ]}
            value={memberRole}
            onChange={(v) => setMemberRole((v as Role) || "student")}
          />
        </Stack>
      </FormModal>

      {/* Read Note Modal */}
      <Modal
        opened={!!viewNoteModal}
        onClose={() => setViewNoteModal(null)}
        title={viewNoteModal?.title}
        centered
        size="lg"
      >
        <Box py="sm">
          <Text size="xs" c="dimmed" mb="sm">
            Section: {viewNoteModal?.section} | Released:{" "}
            {viewNoteModal?.created_at ? new Date(viewNoteModal.created_at).toLocaleDateString() : ""}
          </Text>
          <Paper withBorder p="md" bg="var(--mantine-color-gray-0)">
            <Text style={{ whiteSpace: "pre-wrap" }} size="sm">
              {viewNoteModal?.content}
            </Text>
          </Paper>
        </Box>
      </Modal>
    </Container>
  );
}
