import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  useCourse,
  useCourseMaterials,
  useCourseAssignments,
  useCourseAnnouncements,
  getFileDownloadUrl,
} from "../api/hooks";

export const ObserverCourseViewPage: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const cId = Number(courseId);

  const { data: course, isLoading: isCourseLoading } = useCourse(cId);
  const { data: materials = [], isLoading: isMaterialsLoading } = useCourseMaterials(cId);
  const { data: assignments = [], isLoading: isAssignmentsLoading } = useCourseAssignments(cId);
  const { data: announcements = [], isLoading: isAnnouncementsLoading } = useCourseAnnouncements(cId);

  const isLoading =
    isCourseLoading || isMaterialsLoading || isAssignmentsLoading || isAnnouncementsLoading;

  if (isLoading) {
    return (
      <Group justify="center" p="xl">
        <Loader size="md" />
        <Text c="dimmed">Loading observer view...</Text>
      </Group>
    );
  }

  if (!course) {
    return (
      <Alert color="red" title="Course Not Found" m="md">
        The requested course is not accessible.
      </Alert>
    );
  }

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Group gap="xs">
            <Badge size="lg" color="indigo">
              Auditor / Observer Mode
            </Badge>
            <Badge size="lg" variant="outline">
              {course.code}
            </Badge>
          </Group>
          <Title order={1} mt="xs">
            {course.name}
          </Title>
          <Text c="dimmed">AY {course.academic_year} Sem {course.semester}</Text>
        </div>
        <Button variant="default" onClick={() => navigate(`/courses/${cId}`)}>
          Back to Workspace
        </Button>
      </Group>

      <Alert color="indigo" title="Observer Privacy & Access Notice">
        You are viewing this course in read-only observer mode. Institutional student submission
        records, student identity data, and academic grading logs are confidential and concealed.
      </Alert>

      {/* Course Overview */}
      <Card withBorder padding="md">
        <Title order={3} mb="xs">
          Course Syllabus & Description
        </Title>
        <Text size="sm">{course.description || "No description provided for this course."}</Text>
      </Card>

      {/* Public Announcements */}
      <Card withBorder padding="md">
        <Title order={3} mb="md">
          Public Announcements ({announcements.length})
        </Title>
        {announcements.length === 0 ? (
          <Text c="dimmed" size="sm">No announcements published.</Text>
        ) : (
          <Stack gap="sm">
            {announcements.map((a) => (
              <Paper key={a.id} withBorder p="sm">
                <Group justify="space-between" mb="xs">
                  <Text fw={600}>{a.title}</Text>
                  <Text size="xs" c="dimmed">
                    {new Date(a.created_at).toLocaleString()}
                  </Text>
                </Group>
                <Text size="sm">{a.content}</Text>
              </Paper>
            ))}
          </Stack>
        )}
      </Card>

      {/* Curriculum Materials */}
      <Card withBorder padding="md">
        <Title order={3} mb="md">
          Curriculum Materials ({materials.length})
        </Title>
        {materials.length === 0 ? (
          <Text c="dimmed" size="sm">No materials published yet.</Text>
        ) : (
          <Stack gap="sm">
            {materials.map((m) => (
              <Paper key={m.id} withBorder p="sm">
                <Group justify="space-between">
                  <div>
                    <Text fw={600}>{m.title}</Text>
                    <Text size="xs" c="dimmed">
                      {m.note_content || "Course study material"}
                    </Text>
                  </div>
                  {m.material_type === "file" && m.file_storage_key && (
                    <Anchor
                      href={getFileDownloadUrl(m.file_storage_key)}
                      target="_blank"
                      size="sm"
                    >
                      Download Material
                    </Anchor>
                  )}
                  {m.material_type === "link" && m.link_url && (
                    <Anchor
                      href={m.link_url}
                      target="_blank"
                      size="sm"
                    >
                      Visit Resource
                    </Anchor>
                  )}
                </Group>
              </Paper>
            ))}
          </Stack>
        )}
      </Card>

      {/* Course Assignments Syllabus */}
      <Card withBorder padding="md">
        <Title order={3} mb="md">
          Assignment Syllabi ({assignments.length})
        </Title>
        {assignments.length === 0 ? (
          <Text c="dimmed" size="sm">No assignments posted for this course.</Text>
        ) : (
          <Stack gap="sm">
            {assignments.map((a) => (
              <Paper key={a.id} withBorder p="sm">
                <Group justify="space-between" mb="xs">
                  <Text fw={600}>{a.title}</Text>
                  <Group gap="xs">
                    <Badge variant="light">Max Score: {a.points_possible}</Badge>
                    <Badge variant="outline">
                      Due: {new Date(a.due_date).toLocaleDateString()}
                    </Badge>
                  </Group>
                </Group>
                <Text size="sm">{a.description}</Text>
              </Paper>
            ))}
          </Stack>
        )}
      </Card>
    </Stack>
  );
};

export default ObserverCourseViewPage;
