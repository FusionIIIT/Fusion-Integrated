import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  Paper,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import {
  useCourse,
  useCourseMaterials,
  useCourseAssignments,
  useCourseAnnouncements,
} from "../api/hooks";
import { AnnouncementItem } from "../components/AnnouncementItem";
import { AssignmentItem } from "../components/AssignmentItem";
import { MaterialItem } from "../components/MaterialItem";

export const CourseWorkspacePage: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const cId = Number(courseId);

  const { data: course, isLoading: isCourseLoading } = useCourse(cId);
  const { data: materials = [], isLoading: isMaterialsLoading } = useCourseMaterials(cId);
  const { data: assignments = [], isLoading: isAssignmentsLoading } = useCourseAssignments(cId);
  const { data: announcements = [], isLoading: isAnnouncementsLoading } = useCourseAnnouncements(cId);

  if (isCourseLoading) {
    return (
      <Group justify="center" p="xl">
        <Loader size="md" />
        <Text c="dimmed">Loading course workspace...</Text>
      </Group>
    );
  }

  if (!course) {
    return (
      <Alert color="red" title="Course Not Found" m="md">
        The requested course does not exist or you do not have permission to access it.
      </Alert>
    );
  }

  return (
    <Stack gap="lg" p="md">
      {/* Course Header Banner */}
      <Card withBorder padding="lg" radius="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Group gap="xs" mb="xs">
              <Badge size="lg" color="blue" variant="filled">
                {course.code}
              </Badge>
              <Badge size="lg" variant="outline">
                AY {course.academic_year} Sem {course.semester}
              </Badge>
            </Group>
            <Title order={1}>{course.name}</Title>
            <Text c="dimmed" mt="xs" style={{ maxWidth: 700 }}>
              {course.description || "No description provided."}
            </Text>
          </div>

          <Stack gap="xs">
            <Group gap="xs">
              <Button
                variant="light"
                color="teal"
                onClick={() => navigate(`/courses/${cId}/grading`)}
              >
                Faculty Grading
              </Button>
              <Button
                variant="light"
                color="yellow"
                onClick={() => navigate(`/courses/${cId}/ta-grading`)}
              >
                TA Evaluation
              </Button>
            </Group>
            <Group gap="xs">
              <Button
                variant="default"
                size="xs"
                onClick={() => navigate(`/courses/${cId}/grades`)}
              >
                My Grades
              </Button>
              <Button
                variant="subtle"
                size="xs"
                color="gray"
                onClick={() => navigate(`/courses/${cId}/observer`)}
              >
                Observer View
              </Button>
            </Group>
          </Stack>
        </Group>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <Tabs.List>
          <Tabs.Tab value="overview">Overview</Tabs.Tab>
          <Tabs.Tab value="materials">Materials ({materials.length})</Tabs.Tab>
          <Tabs.Tab value="assignments">Assignments ({assignments.length})</Tabs.Tab>
          <Tabs.Tab value="announcements">Announcements ({announcements.length})</Tabs.Tab>
        </Tabs.List>

        {/* Overview Tab */}
        <Tabs.Panel value="overview" pt="md">
          <Grid>
            <Grid.Col span={{ base: 12, md: 7 }}>
              <Stack gap="md">
                <Card withBorder padding="md">
                  <Title order={3} mb="sm">Recent Announcements</Title>
                  {isAnnouncementsLoading ? (
                    <Loader size="sm" />
                  ) : announcements.length === 0 ? (
                    <Text c="dimmed" size="sm">No announcements yet.</Text>
                  ) : (
                    <Stack gap="sm">
                      {announcements.slice(0, 3).map((a) => (
                        <AnnouncementItem key={a.id} announcement={a} />
                      ))}
                    </Stack>
                  )}
                  {announcements.length > 3 && (
                    <Button
                      variant="subtle"
                      size="xs"
                      mt="sm"
                      onClick={() => navigate(`/courses/${cId}/announcements`)}
                    >
                      View all announcements
                    </Button>
                  )}
                </Card>

                <Card withBorder padding="md">
                  <Title order={3} mb="sm">Recent Materials</Title>
                  {isMaterialsLoading ? (
                    <Loader size="sm" />
                  ) : materials.length === 0 ? (
                    <Text c="dimmed" size="sm">No materials uploaded yet.</Text>
                  ) : (
                    <Stack gap="sm">
                      {materials.slice(0, 3).map((m) => (
                        <MaterialItem key={m.id} material={m} />
                      ))}
                    </Stack>
                  )}
                </Card>
              </Stack>
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 5 }}>
              <Card withBorder padding="md">
                <Group justify="space-between" mb="sm">
                  <Title order={3}>Upcoming Assignments</Title>
                  <Button
                    size="xs"
                    variant="subtle"
                    onClick={() => navigate(`/courses/${cId}/assignments`)}
                  >
                    View All
                  </Button>
                </Group>
                {isAssignmentsLoading ? (
                  <Loader size="sm" />
                ) : assignments.length === 0 ? (
                  <Text c="dimmed" size="sm">No assignments active.</Text>
                ) : (
                  <Stack gap="sm">
                    {assignments.slice(0, 4).map((a) => (
                      <Paper key={a.id} withBorder p="xs">
                        <Group justify="space-between">
                          <Text fw={600} size="sm">{a.title}</Text>
                          <Badge size="xs" color="blue">
                            {a.points_possible} pts
                          </Badge>
                        </Group>
                        <Text size="xs" c="dimmed">
                          Due: {new Date(a.due_date).toLocaleDateString()}
                        </Text>
                      </Paper>
                    ))}
                  </Stack>
                )}
              </Card>
            </Grid.Col>
          </Grid>
        </Tabs.Panel>

        {/* Materials Tab */}
        <Tabs.Panel value="materials" pt="md">
          <Group justify="space-between" mb="md">
            <Title order={3}>Course Modules & Materials</Title>
            <Button onClick={() => navigate(`/courses/${cId}/materials`)}>
              Manage Materials
            </Button>
          </Group>
          {materials.length === 0 ? (
            <Paper withBorder p="xl" style={{ textAlign: "center" }}>
              <Text c="dimmed">No materials available in this course.</Text>
            </Paper>
          ) : (
            <Stack gap="sm">
              {materials.map((m) => (
                <MaterialItem key={m.id} material={m} />
              ))}
            </Stack>
          )}
        </Tabs.Panel>

        {/* Assignments Tab */}
        <Tabs.Panel value="assignments" pt="md">
          <Group justify="space-between" mb="md">
            <Title order={3}>Course Assignments</Title>
            <Button onClick={() => navigate(`/courses/${cId}/assignments`)}>
              Manage Assignments
            </Button>
          </Group>
          {assignments.length === 0 ? (
            <Paper withBorder p="xl" style={{ textAlign: "center" }}>
              <Text c="dimmed">No assignments published for this course.</Text>
            </Paper>
          ) : (
            <Stack gap="sm">
              {assignments.map((a) => (
                <AssignmentItem
                  key={a.id}
                  assignment={a}
                  onOpenSubmit={() =>
                    navigate(`/courses/${cId}/assignments/${a.id}`)
                  }
                />
              ))}
            </Stack>
          )}
        </Tabs.Panel>

        {/* Announcements Tab */}
        <Tabs.Panel value="announcements" pt="md">
          <Group justify="space-between" mb="md">
            <Title order={3}>Course Announcements</Title>
            <Button onClick={() => navigate(`/courses/${cId}/announcements`)}>
              Manage Announcements
            </Button>
          </Group>
          {announcements.length === 0 ? (
            <Paper withBorder p="xl" style={{ textAlign: "center" }}>
              <Text c="dimmed">No announcements posted yet.</Text>
            </Paper>
          ) : (
            <Stack gap="sm">
              {announcements.map((a) => (
                <AnnouncementItem key={a.id} announcement={a} />
              ))}
            </Stack>
          )}
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
};

export default CourseWorkspacePage;
