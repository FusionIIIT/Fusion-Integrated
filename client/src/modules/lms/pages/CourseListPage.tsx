import { Badge, Button, Card, Container, Group, SimpleGrid, Text, Title } from "@mantine/core";
import { FaBookOpen } from "react-icons/fa";
import { Link } from "react-router-dom";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useUserCourses } from "../api/hooks";

function roleColor(role: string) {
  switch (role) {
    case "faculty":
      return "indigo";
    case "ta":
      return "teal";
    case "observer":
      return "gray";
    case "student":
    default:
      return "blue";
  }
}

export default function CourseListPage() {
  const { data: courses, isLoading, error } = useUserCourses();

  if (error) {
    return (
      <Container size="lg" py="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Course Management (LMS)"
        subtitle="Access dedicated workspaces for courses you are enrolled in or assigned to"
      />

      {isLoading ? (
        <Text c="dimmed">Loading your enrolled courses...</Text>
      ) : !courses || courses.length === 0 ? (
        <Card withBorder p="xl" radius="md">
          <Text c="dimmed" ta="center">
            You are not currently enrolled in or assigned to any courses.
          </Text>
        </Card>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
          {courses.map((membership) => (
            <Card key={membership.id} withBorder shadow="sm" radius="md" p="md">
              <Group justify="space-between" mb="xs">
                <Badge color={roleColor(membership.role)} variant="light">
                  {membership.role.toUpperCase()}
                </Badge>
                <Text size="xs" c="dimmed">
                  {membership.course_code}
                </Text>
              </Group>

              <Title order={4} mb="xs" lineClamp={2}>
                {membership.course_title}
              </Title>

              <Group justify="space-between" mt="md">
                <Button
                  component={Link}
                  to={`/lms/course/${membership.course}`}
                  variant="light"
                  color="blue"
                  leftSection={<FaBookOpen />}
                  fullWidth
                >
                  Open Workspace
                </Button>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Container>
  );
}
