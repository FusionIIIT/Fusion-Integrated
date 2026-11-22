import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  TbAlertCircle,
  TbCalendar,
  TbClipboardList,
  TbClock,
  TbEdit,
  TbPlus,
  TbTrash,
  TbUpload,
  TbUser,
  TbUsers,
} from "react-icons/tb";

import {
  deleteAssignment,
  useCourseAssignments,
} from "../api/hooks";
import type { CourseAssignment } from "../api/types";
import { AssignmentModal } from "./AssignmentModal";
import { FacultySubmissionsModal } from "./FacultySubmissionsModal";
import { StudentSubmissionModal } from "./StudentSubmissionModal";

interface CourseAssignmentsPanelProps {
  workspaceId: number;
  canManage: boolean;
  viewerRole?: string | null;
}

export function CourseAssignmentsPanel({
  workspaceId,
  canManage,
  viewerRole,
}: CourseAssignmentsPanelProps) {
  const { data, loading, error, refetch } = useCourseAssignments(workspaceId);
  const [modalOpened, setModalOpened] = useState(false);
  const [selectedAssignment, setSelectedAssignment] =
    useState<CourseAssignment | null>(null);
  const [studentModalOpened, setStudentModalOpened] = useState(false);
  const [facultyModalOpened, setFacultyModalOpened] = useState(false);
  const [activeAssignment, setActiveAssignment] =
    useState<CourseAssignment | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleOpenCreate = () => {
    setSelectedAssignment(null);
    setModalOpened(true);
  };

  const handleOpenEdit = (asgn: CourseAssignment) => {
    setSelectedAssignment(asgn);
    setModalOpened(true);
  };

  const handleDelete = async (asgnId: number) => {
    if (!window.confirm("Are you sure you want to delete this assignment?")) {
      return;
    }
    setActionError(null);
    try {
      await deleteAssignment(workspaceId, asgnId);
      refetch();
    } catch (err: unknown) {
      setActionError(
        err instanceof Error
          ? err.message
          : "Failed to delete assignment.",
      );
    }
  };

  const assignments = data?.results ?? [];

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={4}>Course Assignments</Title>
          <Text size="xs" c="dimmed">
            Course assignments, problem sets, and guidelines
          </Text>
        </div>
        {canManage && (
          <Button
            leftSection={<TbPlus size={16} />}
            onClick={handleOpenCreate}
            size="sm"
          >
            Create Assignment
          </Button>
        )}
      </Group>

      {error && (
        <Alert color="red" title="Error">
          {error}
        </Alert>
      )}

      {actionError && (
        <Alert color="red" title="Action Error" withCloseButton onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}

      {loading && (
        <Group justify="center" py="xl">
          <Loader size="md" />
        </Group>
      )}

      {!loading && assignments.length === 0 && (
        <Paper withBorder p="xl" ta="center" radius="md">
          <Group justify="center" mb="xs">
            <TbClipboardList size={32} color="gray" />
          </Group>
          <Text fw={500} c="dimmed">
            No assignments published yet
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {canManage
              ? "Use the 'Create Assignment' button above to post assignments for this course."
              : "Course assignments from instructors will appear here."}
          </Text>
        </Paper>
      )}

      {!loading && assignments.length > 0 && (
        <Stack gap="md">
          {assignments.map((asgn) => {
            const formattedDate = asgn.published_at
              ? new Date(asgn.published_at).toLocaleString()
              : new Date(asgn.created_at).toLocaleString();

            const formattedDueDate = asgn.due_at
              ? new Date(asgn.due_at).toLocaleString()
              : null;

            return (
              <Card key={asgn.id} withBorder shadow="xs" p="md" radius="sm">
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                  <div style={{ flex: 1, minWidth: 260 }}>
                    <Group gap="xs" mb={4} wrap="wrap">
                      <Title order={5}>{asgn.title}</Title>
                      {asgn.is_published ? (
                        <Badge color="teal" size="sm" variant="light">
                          Published
                        </Badge>
                      ) : (
                        <Badge color="yellow" size="sm" variant="light">
                          Draft (Faculty Only)
                        </Badge>
                      )}
                      {asgn.due_at ? (
                        asgn.has_passed ? (
                          <Badge
                            color="red"
                            size="sm"
                            variant="filled"
                            leftSection={<TbAlertCircle size={12} />}
                          >
                            Deadline Passed
                          </Badge>
                        ) : (
                          <Badge
                            color="blue"
                            size="sm"
                            variant="light"
                            leftSection={<TbClock size={12} />}
                          >
                            Due: {formattedDueDate}
                          </Badge>
                        )
                      ) : (
                        <Badge color="gray" size="sm" variant="outline">
                          No deadline
                        </Badge>
                      )}
                    </Group>
                    <Group gap="md" c="dimmed" style={{ fontSize: "0.8rem" }} wrap="wrap">
                      <Group gap={4}>
                        <TbUser size={14} />
                        <span>{asgn.author_name || "Faculty Instructor"}</span>
                      </Group>
                      <Group gap={4}>
                        <TbCalendar size={14} />
                        <span>{formattedDate}</span>
                      </Group>
                      {asgn.due_at && (
                        <Group gap={4} c={asgn.has_passed ? "red" : undefined}>
                          <TbClock size={14} />
                          <span>
                            {asgn.has_passed ? "Expired: " : "Deadline: "}
                            {formattedDueDate}
                          </span>
                        </Group>
                      )}
                    </Group>
                  </div>

                  <Group gap="xs" wrap="wrap">
                    {canManage && (
                      <>
                        <Button
                          variant="subtle"
                          size="xs"
                          leftSection={<TbEdit size={14} />}
                          onClick={() => handleOpenEdit(asgn)}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="subtle"
                          color="red"
                          size="xs"
                          leftSection={<TbTrash size={14} />}
                          onClick={() => handleDelete(asgn.id)}
                        >
                          Delete
                        </Button>
                      </>
                    )}

                    {(canManage || viewerRole === "ta") && (
                      <Button
                        variant="light"
                        size="xs"
                        leftSection={<TbUsers size={14} />}
                        onClick={() => {
                          setActiveAssignment(asgn);
                          setFacultyModalOpened(true);
                        }}
                      >
                        Submissions
                      </Button>
                    )}

                    {(viewerRole === "student" || (!canManage && viewerRole !== "observer" && viewerRole !== "ta")) && (
                      <Button
                        variant="filled"
                        color="indigo"
                        size="xs"
                        leftSection={<TbUpload size={14} />}
                        onClick={() => {
                          setActiveAssignment(asgn);
                          setStudentModalOpened(true);
                        }}
                      >
                        Submit Work
                      </Button>
                    )}
                  </Group>
                </Group>

                {asgn.description && (
                  <Text size="sm" mt="xs" c="dimmed" style={{ lineHeight: 1.5 }}>
                    {asgn.description}
                  </Text>
                )}

                {asgn.instructions && (
                  <>
                    <Divider my="sm" />
                    <Text size="xs" fw={600} c="dimmed" mb={4}>
                      Instructions & Problem Details:
                    </Text>
                    <Text
                      size="sm"
                      style={{
                        whiteSpace: "pre-line",
                        lineHeight: 1.6,
                        background: "#f8f9fa",
                        padding: "10px",
                        borderRadius: "4px",
                        wordBreak: "break-word",
                      }}
                    >
                      {asgn.instructions}
                    </Text>
                  </>
                )}
              </Card>
            );
          })}
        </Stack>
      )}

      <AssignmentModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        workspaceId={workspaceId}
        assignment={selectedAssignment}
        onSuccess={refetch}
      />

      <StudentSubmissionModal
        opened={studentModalOpened}
        onClose={() => setStudentModalOpened(false)}
        workspaceId={workspaceId}
        assignment={activeAssignment}
        onSuccess={refetch}
      />

      <FacultySubmissionsModal
        opened={facultyModalOpened}
        onClose={() => setFacultyModalOpened(false)}
        workspaceId={workspaceId}
        assignment={activeAssignment}
        viewerRole={viewerRole}
      />
    </Stack>
  );
}

