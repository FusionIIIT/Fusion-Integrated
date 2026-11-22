import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import CourseWorkspacePage from "./CourseWorkspacePage";
import {
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCalendarAlt,
  FaClipboardList,
  FaFileAlt,
  FaGraduationCap,
  FaPlus,
  FaSearch,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourses, useCreateCourse } from "../api/hooks";
import type { Role } from "../api/types";

const ROLE_COLORS: Record<string, string> = {
  faculty: "blue",
  ta: "violet",
  student: "teal",
  observer: "gray",
};

export default function CoursesListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedCourseId = searchParams.get("courseId");

  const { data: courses, isPending, error } = useCourses();
  const { can, session } = useAuth();
  const user = session?.user;
  const createCourse = useCreateCourse();

  const [search, setSearch] = useState("");
  const [semesterFilter, setSemesterFilter] = useState<string | null>("all");
  const [modalOpened, setModalOpened] = useState(false);

  // New course form state
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [semester, setSemester] = useState("Monsoon");
  const [syllabus, setSyllabus] = useState("");
  const [schedule, setSchedule] = useState("");
  const [allowTaAnnouncements, setAllowTaAnnouncements] = useState(false);
  const [allowTaGrading, setAllowTaGrading] = useState(false);

  if (selectedCourseId) {
    return <CourseWorkspacePage courseIdProp={Number(selectedCourseId)} />;
  }

  const canCreate = can("lms.course.create") || user?.kind === "faculty" || user?.kind === "admin";

  const handleCreate = () => {
    if (!code.trim() || !name.trim()) return;
    createCourse.mutate(
      {
        code: code.trim().toUpperCase(),
        name: name.trim(),
        academic_year: academicYear.trim(),
        semester: semester.trim(),
        syllabus: syllabus.trim(),
        schedule: schedule.trim(),
        allow_ta_announcements: allowTaAnnouncements,
        allow_ta_grading: allowTaGrading,
      },
      {
        onSuccess: (newCourse) => {
          notifications.show({
            title: "Course created",
            message: `Workspace for ${newCourse.code} has been initialized.`,
            color: "green",
          });
          setModalOpened(false);
          setCode("");
          setName("");
          setSyllabus("");
          setSchedule("");
          navigate(`/lms/courses?courseId=${newCourse.id}`);
        },
        onError: (err) => {
          notifications.show({
            title: "Creation failed",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  };

  if (error) {
    return (
      <Container size="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  const courseList = courses ?? [];
  const filteredCourses = courseList.filter((c) => {
    const matchesSearch =
      c.code.toLowerCase().includes(search.toLowerCase()) ||
      c.name.toLowerCase().includes(search.toLowerCase());
    const matchesSemester =
      semesterFilter === "all" || !semesterFilter || c.semester.toLowerCase() === semesterFilter.toLowerCase();
    return matchesSearch && matchesSemester;
  });

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Course Workspaces"
        subtitle="Manage enrolled courses, syllabi, materials, assignments, and grading"
        action={
          canCreate && (
            <Button
              leftSection={<FaPlus size={14} />}
              onClick={() => setModalOpened(true)}
              color="indigo"
            >
              Create Course
            </Button>
          )
        }
      />

      <Card withBorder mb="lg" padding="md">
        <Group justify="space-between" wrap="wrap">
          <TextInput
            placeholder="Search by course code or title..."
            leftSection={<FaSearch size={14} color="var(--mantine-color-gray-5)" />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: 1, minWidth: 260 }}
          />
          <Select
            placeholder="Filter by semester"
            data={[
              { value: "all", label: "All Semesters" },
              { value: "Monsoon", label: "Monsoon Semester" },
              { value: "Winter", label: "Winter Semester" },
              { value: "Summer", label: "Summer Semester" },
            ]}
            value={semesterFilter}
            onChange={setSemesterFilter}
            style={{ width: 200 }}
          />
        </Group>
      </Card>

      {isPending && <Text c="dimmed">Loading course workspaces...</Text>}

      {!isPending && filteredCourses.length === 0 && (
        <Card padding="xl" withBorder style={{ textAlign: "center" }}>
          <Stack align="center" gap="xs">
            <ThemeIcon size={50} radius="xl" color="gray" variant="light">
              <FaGraduationCap size={26} />
            </ThemeIcon>
            <Text fw={600} size="lg">
              No courses found
            </Text>
            <Text c="dimmed" size="sm" maw={400}>
              {search
                ? "No course matches your search keyword."
                : "You are not enrolled in or managing any active courses."}
            </Text>
          </Stack>
        </Card>
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
        {filteredCourses.map((c) => {
          const role = (c.my_role || "student") as Role;
          return (
            <Card
              key={c.id}
              withBorder
              shadow="sm"
              padding="lg"
              radius="md"
              style={{
                cursor: "pointer",
                transition: "transform 0.15s ease, box-shadow 0.15s ease",
              }}
              onClick={() => navigate(`/lms/courses?courseId=${c.id}`)}
            >
              <Group justify="space-between" align="flex-start" mb="xs">
                <div>
                  <Badge variant="filled" color="indigo" size="sm" mb={4}>
                    {c.code}
                  </Badge>
                  <Text fw={700} size="md" lineClamp={1}>
                    {c.name}
                  </Text>
                </div>
                <Badge color={ROLE_COLORS[role] ?? "gray"} variant="light" size="sm">
                  {role.toUpperCase()}
                </Badge>
              </Group>

              <Group gap="xs" mb="md">
                <Text size="xs" c="dimmed">
                  <FaCalendarAlt style={{ verticalAlign: "middle", marginRight: 4 }} />
                  {c.semester} {c.academic_year}
                </Text>
              </Group>

              <Text size="sm" c="dimmed" lineClamp={2} mb="md">
                {c.syllabus || "No syllabus outline published yet."}
              </Text>

              <Group
                justify="space-between"
                pt="xs"
                style={{ borderTop: "1px solid var(--mantine-color-gray-2)" }}
              >
                <Group gap="md">
                  <Text size="xs" c="dimmed" title="Materials">
                    <FaFileAlt style={{ verticalAlign: "middle", marginRight: 4 }} />
                    {c.materials_count ?? 0}
                  </Text>
                  <Text size="xs" c="dimmed" title="Assignments">
                    <FaClipboardList style={{ verticalAlign: "middle", marginRight: 4 }} />
                    {c.assignments_count ?? 0}
                  </Text>
                </Group>
                <Button variant="subtle" size="xs" color="indigo">
                  Open Workspace &rarr;
                </Button>
              </Group>
            </Card>
          );
        })}
      </SimpleGrid>

      {/* Create Course Modal */}
      <FormModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title="Create Course Workspace"
        subtitle="Initialize a new academic course workspace (CFR-LMS-001)"
        onSubmit={handleCreate}
        submitLabel="Create Workspace"
        submitting={createCourse.isPending}
        disabled={!code.trim() || !name.trim()}
        disabledReason="Course Code and Course Title are required."
      >
        <Stack gap="md">
          <Grid>
            <Grid.Col span={4}>
              <TextInput
                label="Course Code"
                placeholder="e.g. CS302"
                required
                value={code}
                onChange={(e) => setCode(e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={8}>
              <TextInput
                label="Course Title"
                placeholder="e.g. Database Management Systems"
                required
                value={name}
                onChange={(e) => setName(e.currentTarget.value)}
              />
            </Grid.Col>
          </Grid>

          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="Academic Year"
                placeholder="e.g. 2026-2027"
                required
                value={academicYear}
                onChange={(e) => setAcademicYear(e.currentTarget.value)}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <Select
                label="Semester"
                data={["Monsoon", "Winter", "Summer"]}
                value={semester}
                onChange={(v) => setSemester(v || "Monsoon")}
              />
            </Grid.Col>
          </Grid>

          <Textarea
            label="Syllabus Overview"
            placeholder="Course outline, learning outcomes, textbook references..."
            rows={3}
            value={syllabus}
            onChange={(e) => setSyllabus(e.currentTarget.value)}
          />

          <Textarea
            label="Weekly Class & Lab Schedule"
            placeholder="e.g. Lectures: Mon/Wed 10:00 - 11:30 AM (Room L101), Lab: Fri 2:00 - 5:00 PM"
            rows={2}
            value={schedule}
            onChange={(e) => setSchedule(e.currentTarget.value)}
          />

          <Group justify="space-between" mt="xs">
            <div>
              <Text size="sm" fw={600}>
                Allow TAs to Post Announcements
              </Text>
              <Text size="xs" c="dimmed">
                Delegate authority to course teaching assistants (BR-LMS-007)
              </Text>
            </div>
            <Switch
              checked={allowTaAnnouncements}
              onChange={(e) => setAllowTaAnnouncements(e.currentTarget.checked)}
            />
          </Group>

          <Group justify="space-between">
            <div>
              <Text size="sm" fw={600}>
                Allow TAs to Evaluate Submissions
              </Text>
              <Text size="xs" c="dimmed">
                Permit teaching assistants to enter evaluation scores and feedback (BR-LMS-017)
              </Text>
            </div>
            <Switch
              checked={allowTaGrading}
              onChange={(e) => setAllowTaGrading(e.currentTarget.checked)}
            />
          </Group>
        </Stack>
      </FormModal>
    </Container>
  );
}
