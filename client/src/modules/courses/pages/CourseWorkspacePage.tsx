import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Grid,
  Group,
  Loader,
  Paper,
  Select,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconBook,
  IconCalendar,
  IconEdit,
  IconInfoCircle,
  IconUserCheck,
  IconUsers,
} from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useWorkspaceDetail, useWorkspaces } from "../api/hooks";
import { WorkspaceEditModal } from "../components/WorkspaceEditModal";

export default function CourseWorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: workspacesData, loading: loadingList, error: listError } = useWorkspaces();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editOpened, setEditOpened] = useState(false);

  // Sync selectedId with query param or first available workspace
  useEffect(() => {
    if (!workspacesData || workspacesData.results.length === 0) return;

    const paramId = searchParams.get("course");
    if (paramId) {
      const parsed = parseInt(paramId, 10);
      if (workspacesData.results.some((w) => w.id === parsed)) {
        setSelectedId(parsed);
        return;
      }
    }
    // Default to the first course
    const first = workspacesData.results[0].id;
    setSelectedId(first);
    setSearchParams({ course: String(first) });
  }, [workspacesData, searchParams, setSearchParams]);

  const {
    data: workspace,
    loading: loadingDetail,
    error: detailError,
    refetch: refetchDetail,
  } = useWorkspaceDetail(selectedId);

  const handleSelectCourse = (val: string | null) => {
    if (!val) return;
    const nextId = parseInt(val, 10);
    setSelectedId(nextId);
    setSearchParams({ course: String(nextId) });
  };

  if (loadingList) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      </Container>
    );
  }

  if (listError) {
    return (
      <Container size="lg" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
          {listError}
        </Alert>
      </Container>
    );
  }

  if (!workspacesData || workspacesData.results.length === 0) {
    return (
      <Container size="lg" py="xl">
        <Alert
          icon={<IconInfoCircle size={16} />}
          title="No Course Workspaces Found"
          color="blue"
        >
          You are not currently enrolled in, assigned to, or linked to any course
          workspaces (BR-LMS-001).
        </Alert>
      </Container>
    );
  }

  const courseOptions = workspacesData.results.map((w) => ({
    value: String(w.id),
    label: `${w.code} — ${w.title} (${w.semester})`,
  }));

  const roleLabelMap: Record<string, { label: string; color: string }> = {
    instructor: { label: "Faculty Instructor", color: "blue" },
    ta: { label: "Teaching Assistant", color: "teal" },
    student: { label: "Enrolled Student", color: "indigo" },
    observer: { label: "Observer (Read-Only)", color: "gray" },
  };

  const roleMeta =
    workspace?.viewer_role && roleLabelMap[workspace.viewer_role]
      ? roleLabelMap[workspace.viewer_role]
      : { label: "Member", color: "gray" };

  return (
    <Container size="lg" py="md">
      {/* Top course switcher & title bar */}
      <Card withBorder shadow="xs" mb="lg" p="md">
        <Group justify="space-between" wrap="wrap" gap="md">
          <div>
            <Title order={3}>Course Management</Title>
            <Text size="xs" c="dimmed">
              Select an enrolled or assigned course workspace
            </Text>
          </div>
          <div style={{ minWidth: 280 }}>
            <Select
              data={courseOptions}
              value={selectedId ? String(selectedId) : null}
              onChange={handleSelectCourse}
              placeholder="Select Course Workspace"
              searchable
            />
          </div>
        </Group>
      </Card>

      {loadingDetail && (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      )}

      {detailError && (
        <Alert icon={<IconAlertCircle size={16} />} title="Access Refused" color="red">
          {detailError}
        </Alert>
      )}

      {workspace && !loadingDetail && (
        <Stack gap="lg">
          {/* Course Workspace Header */}
          <Paper withBorder p="lg" radius="md">
            <Group justify="space-between" align="flex-start" wrap="wrap">
              <div>
                <Group gap="xs" mb="xs">
                  <Badge size="lg" variant="filled" color="dark">
                    {workspace.code}
                  </Badge>
                  <Badge variant="outline" color={roleMeta.color}>
                    {roleMeta.label}
                  </Badge>
                  <Badge variant="dot" color="blue">
                    {workspace.semester} · {workspace.academic_year}
                  </Badge>
                  <Badge variant="default">{workspace.credits} Credits</Badge>
                </Group>
                <Title order={2}>{workspace.title}</Title>
                {workspace.description && (
                  <Text size="sm" c="dimmed" mt="xs" maw={800}>
                    {workspace.description}
                  </Text>
                )}
              </div>

              {/* Faculty configuration button: rendered ONLY for assigned faculty instructors */}
              {workspace.can_manage && (
                <Button
                  leftSection={<IconEdit size={16} />}
                  onClick={() => setEditOpened(true)}
                >
                  Edit Workspace Details
                </Button>
              )}
            </Group>

            {/* Modular Navigation Tabs (Extensible for Materials & Announcements) */}
            <Tabs defaultValue="home" mt="xl">
              <Tabs.List>
                <Tabs.Tab value="home" leftSection={<IconBook size={14} />}>
                  Course Home
                </Tabs.Tab>
                <Tabs.Tab value="materials" disabled>
                  Materials (Next Stage)
                </Tabs.Tab>
                <Tabs.Tab value="announcements" disabled>
                  Announcements (Next Stage)
                </Tabs.Tab>
                <Tabs.Tab value="assignments" disabled>
                  Assignments (Future Labs)
                </Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="home" pt="md">
                <Grid gutter="md">
                  {/* Left Column: Syllabus & Schedule */}
                  <Grid.Col span={{ base: 12, md: 8 }}>
                    <Stack gap="md">
                      {/* Syllabus Card (AFR-LMS-001.2) */}
                      <Card withBorder shadow="xs" p="md">
                        <Group gap="xs" mb="sm">
                          <IconBook size={18} />
                          <Title order={4}>Course Syllabus</Title>
                        </Group>
                        <Divider mb="sm" />
                        {workspace.syllabus ? (
                          <Text
                            size="sm"
                            style={{ whiteSpace: "pre-line", lineHeight: 1.6 }}
                          >
                            {workspace.syllabus}
                          </Text>
                        ) : (
                          <Text size="sm" c="dimmed" fs="italic">
                            No syllabus published for this course yet.
                          </Text>
                        )}
                      </Card>

                      {/* Schedule Card (AFR-LMS-001.2) */}
                      <Card withBorder shadow="xs" p="md">
                        <Group gap="xs" mb="sm">
                          <IconCalendar size={18} />
                          <Title order={4}>Class & Lab Schedule</Title>
                        </Group>
                        <Divider mb="sm" />
                        {workspace.schedule ? (
                          <Text
                            size="sm"
                            style={{ whiteSpace: "pre-line", lineHeight: 1.6 }}
                          >
                            {workspace.schedule}
                          </Text>
                        ) : (
                          <Text size="sm" c="dimmed" fs="italic">
                            Schedule has not been announced yet.
                          </Text>
                        )}
                      </Card>
                    </Stack>
                  </Grid.Col>

                  {/* Right Column: Instructors & Teaching Assistants */}
                  <Grid.Col span={{ base: 12, md: 4 }}>
                    <Stack gap="md">
                      {/* Instructors Card (AFR-LMS-001.2) */}
                      <Card withBorder shadow="xs" p="md">
                        <Group gap="xs" mb="sm">
                          <IconUserCheck size={18} />
                          <Title order={4}>Instructors</Title>
                        </Group>
                        <Divider mb="sm" />
                        {workspace.instructors.length > 0 ? (
                          <Stack gap="sm">
                            {workspace.instructors.map((inst) => (
                              <Group key={inst.user_id} gap="sm" wrap="nowrap">
                                <Avatar color="blue" radius="xl">
                                  {inst.name.charAt(0)}
                                </Avatar>
                                <div style={{ overflow: "hidden" }}>
                                  <Text size="sm" fw={500} lineClamp={1}>
                                    {inst.name}
                                  </Text>
                                  {inst.department && (
                                    <Text size="xs" c="dimmed" lineClamp={1}>
                                      {inst.department}
                                    </Text>
                                  )}
                                  {inst.email && (
                                    <Text
                                      size="xs"
                                      component="a"
                                      href={`mailto:${inst.email}`}
                                      c="blue"
                                      lineClamp={1}
                                    >
                                      {inst.email}
                                    </Text>
                                  )}
                                </div>
                              </Group>
                            ))}
                          </Stack>
                        ) : (
                          <Text size="sm" c="dimmed" fs="italic">
                            No instructor assigned.
                          </Text>
                        )}
                      </Card>

                      {/* Teaching Assistants Card (AFR-LMS-001.2, AFR-LMS-014.1) */}
                      <Card withBorder shadow="xs" p="md">
                        <Group gap="xs" mb="sm">
                          <IconUsers size={18} />
                          <Title order={4}>Teaching Assistants</Title>
                        </Group>
                        <Divider mb="sm" />
                        {workspace.tas.length > 0 ? (
                          <Stack gap="sm">
                            {workspace.tas.map((ta) => (
                              <Group key={ta.user_id} gap="sm" wrap="nowrap">
                                <Avatar color="teal" radius="xl">
                                  {ta.name.charAt(0)}
                                </Avatar>
                                <div style={{ overflow: "hidden" }}>
                                  <Text size="sm" fw={500} lineClamp={1}>
                                    {ta.name}
                                  </Text>
                                  {ta.department && (
                                    <Text size="xs" c="dimmed" lineClamp={1}>
                                      {ta.department}
                                    </Text>
                                  )}
                                  {ta.email && (
                                    <Text
                                      size="xs"
                                      component="a"
                                      href={`mailto:${ta.email}`}
                                      c="blue"
                                      lineClamp={1}
                                    >
                                      {ta.email}
                                    </Text>
                                  )}
                                </div>
                              </Group>
                            ))}
                          </Stack>
                        ) : (
                          <Text size="sm" c="dimmed" fs="italic">
                            No teaching assistant assigned.
                          </Text>
                        )}
                      </Card>
                    </Stack>
                  </Grid.Col>
                </Grid>
              </Tabs.Panel>
            </Tabs>
          </Paper>

          {/* Faculty Edit Modal (AFR-LMS-002.1, AFR-LMS-002.2) */}
          {workspace.can_manage && (
            <WorkspaceEditModal
              opened={editOpened}
              onClose={() => setEditOpened(false)}
              workspace={workspace}
              onSaved={refetchDetail}
            />
          )}
        </Stack>
      )}
    </Container>
  );
}
