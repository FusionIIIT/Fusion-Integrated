import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { FaBook, FaBullhorn, FaFileAlt, FaFolderOpen, FaTasks } from "react-icons/fa";
import { Link, useParams } from "react-router-dom";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCourseAnnouncements,
  useCourseAssignments,
  useCourseDetail,
  useCourseMaterials,
} from "../api/hooks";

export default function CourseWorkspacePage() {
  const { courseId } = useParams<{ courseId: string }>();
  const id = Number(courseId);

  const { data: course, isLoading, error } = useCourseDetail(id);
  const { data: materials } = useCourseMaterials(id);
  const { data: announcements } = useCourseAnnouncements(id);
  const { data: assignments } = useCourseAssignments(id);

  if (error) {
    return (
      <Container size="lg" py="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  if (isLoading || !course) {
    return (
      <Container size="lg" py="md">
        <Text c="dimmed">Loading course workspace...</Text>
      </Container>
    );
  }

  const isStaff = course.user_role === "faculty" || course.user_role === "ta";

  return (
    <Container size="lg" py="md">
      <PageHeader
        title={`${course.course_code}: ${course.title}`}
        subtitle={`Role: ${(course.user_role || "Student").toUpperCase()}`}
      />

      <Tabs defaultValue="materials" variant="outline">
        <Tabs.List mb="md">
          <Tabs.Tab value="materials" leftSection={<FaFolderOpen />}>
            Course Materials
          </Tabs.Tab>
          <Tabs.Tab value="assignments" leftSection={<FaTasks />}>
            Assignments
          </Tabs.Tab>
          <Tabs.Tab value="announcements" leftSection={<FaBullhorn />}>
            Announcements
          </Tabs.Tab>
          <Tabs.Tab value="syllabus" leftSection={<FaBook />}>
            Syllabus & Schedule
          </Tabs.Tab>
        </Tabs.List>

        {/* Materials Tab */}
        <Tabs.Panel value="materials">
          {!materials || materials.length === 0 ? (
            <Card withBorder p="lg">
              <Text c="dimmed">No course materials published yet.</Text>
            </Card>
          ) : (
            <Stack gap="md">
              {materials.map((mat) => (
                <Card key={mat.id} withBorder p="md" radius="sm">
                  <Group justify="space-between" mb="xs">
                    <Title order={5}>{mat.title}</Title>
                    <Badge color="blue" variant="light">
                      {mat.section_or_week}
                    </Badge>
                  </Group>
                  <Text size="sm" c="dimmed" mb="xs">
                    {mat.description}
                  </Text>
                  {mat.content && (
                    <Text size="sm" mb="xs">
                      {mat.content}
                    </Text>
                  )}
                  {mat.file_url && (
                    <Button
                      component="a"
                      href={mat.file_url}
                      target="_blank"
                      size="xs"
                      variant="light"
                      leftSection={<FaFileAlt />}
                    >
                      Open File
                    </Button>
                  )}
                </Card>
              ))}
            </Stack>
          )}
        </Tabs.Panel>

        {/* Assignments Tab */}
        <Tabs.Panel value="assignments">
          {!assignments || assignments.length === 0 ? (
            <Card withBorder p="lg">
              <Text c="dimmed">No assignments available.</Text>
            </Card>
          ) : (
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Assignment</Table.Th>
                  <Table.Th>Submission Type</Table.Th>
                  <Table.Th>Points</Table.Th>
                  <Table.Th>Due Date</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {assignments.map((asgn) => (
                  <Table.Tr key={asgn.id}>
                    <Table.Td fw={500}>{asgn.title}</Table.Td>
                    <Table.Td>
                      <Badge variant="dot">{asgn.submission_type.toUpperCase()}</Badge>
                    </Table.Td>
                    <Table.Td>{asgn.points_possible} pts</Table.Td>
                    <Table.Td>{new Date(asgn.due_date).toLocaleString()}</Table.Td>
                    <Table.Td>
                      <Badge color={asgn.status === "available" ? "green" : "gray"}>
                        {asgn.status.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          component={Link}
                          to={`/lms/assignment/${asgn.id}`}
                          size="xs"
                          variant="light"
                        >
                          View & Submit
                        </Button>
                        {isStaff && (
                          <Button
                            component={Link}
                            to={`/lms/grading/${asgn.id}`}
                            size="xs"
                            variant="outline"
                            color="teal"
                          >
                            Grade
                          </Button>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Tabs.Panel>

        {/* Announcements Tab */}
        <Tabs.Panel value="announcements">
          {!announcements || announcements.length === 0 ? (
            <Card withBorder p="lg">
              <Text c="dimmed">No course announcements posted yet.</Text>
            </Card>
          ) : (
            <Stack gap="md">
              {announcements.map((ann) => (
                <Card key={ann.id} withBorder p="md" radius="sm">
                  <Group justify="space-between" mb="xs">
                    <Title order={5}>{ann.title}</Title>
                    <Text size="xs" c="dimmed">
                      {new Date(ann.posted_at).toLocaleString()}
                    </Text>
                  </Group>
                  <Text size="sm">{ann.content}</Text>
                  {ann.is_ta_announcement && (
                    <Badge size="xs" color="teal" variant="light" mt="xs">
                      Posted by TA
                    </Badge>
                  )}
                </Card>
              ))}
            </Stack>
          )}
        </Tabs.Panel>

        {/* Syllabus Tab */}
        <Tabs.Panel value="syllabus">
          <Stack gap="md">
            <Card withBorder p="md">
              <Title order={5} mb="xs">
                Syllabus
              </Title>
              <Text size="sm">{course.syllabus || "No syllabus entered."}</Text>
            </Card>
            <Card withBorder p="md">
              <Title order={5} mb="xs">
                Class Schedule
              </Title>
              <Text size="sm">{course.schedule || "No schedule specified."}</Text>
            </Card>
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
