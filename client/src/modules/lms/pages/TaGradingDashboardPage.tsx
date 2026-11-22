import React, { useState } from "react";
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
  Select,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import {
  useCourse,
  useCourseAssignments,
  useAssignmentSubmissions,
  useGrades,
  getFileDownloadUrl,
} from "../api/hooks";
import type { Submission } from "../api/types";
import { GradingModal } from "../components/GradingModal";

export const TaGradingDashboardPage: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const cId = Number(courseId);

  const { data: course, isLoading: isCourseLoading } = useCourse(cId);
  const { data: assignments = [], isLoading: isAssignmentsLoading } = useCourseAssignments(cId);
  const { data: allGrades = [] } = useGrades();

  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);

  const currentAssignment = assignments.find(
    (a) => a.id.toString() === selectedAssignmentId
  );

  const { data: submissions = [], isLoading: isSubmissionsLoading } =
    useAssignmentSubmissions(selectedAssignmentId ? Number(selectedAssignmentId) : 0);

  // Map submissions to grades
  const gradeMap = new Map(allGrades.map((g) => [g.submission, g]));

  const assignmentOptions = assignments.map((a) => ({
    value: a.id.toString(),
    label: `${a.title} (Max: ${a.points_possible} pts)`,
  }));

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Teaching Assistant Evaluation Console</Title>
          <Text c="dimmed">
            {isCourseLoading ? "Loading course..." : `${course?.code} — ${course?.name}`}
          </Text>
        </div>
        <Button variant="default" onClick={() => navigate(`/courses/${cId}`)}>
          Back to Course
        </Button>
      </Group>

      <Alert
        color="yellow"
        title="Institutional Policy Notice (BW-LMS-05 / ISS-LMS-002)"
      >
        Teaching Assistants record preliminary <strong>draft evaluations</strong> and feedback for student submissions.
        Official grade release to students is reserved exclusively for Course Instructors.
      </Alert>

      <Card withBorder padding="md">
        <Group align="flex-end">
          <Select
            label="Select Assignment to Evaluate"
            placeholder="Choose an assignment"
            data={assignmentOptions}
            value={selectedAssignmentId}
            onChange={(val) => {
              setSelectedAssignmentId(val);
              setSelectedSubmission(null);
            }}
            style={{ minWidth: 320 }}
          />
          {selectedAssignmentId && currentAssignment && (
            <Group gap="xs">
              <Badge variant="light" color="blue">
                Due: {new Date(currentAssignment.due_date).toLocaleString()}
              </Badge>
              <Badge variant="light" color="gray">
                Max Score: {currentAssignment.points_possible}
              </Badge>
            </Group>
          )}
        </Group>
      </Card>

      {!selectedAssignmentId ? (
        <Paper withBorder p="xl" style={{ textAlign: "center" }}>
          <Text c="dimmed">Please select an assignment from the dropdown above to view student submissions.</Text>
        </Paper>
      ) : isSubmissionsLoading || isAssignmentsLoading ? (
        <Group justify="center" p="xl">
          <Loader size="md" />
          <Text c="dimmed">Loading submissions...</Text>
        </Group>
      ) : submissions.length === 0 ? (
        <Alert color="blue" title="No Submissions">
          There are currently no student submissions for this assignment.
        </Alert>
      ) : (
        <Card withBorder padding="none">
          <Table striped highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Student ID</Table.Th>
                <Table.Th>Version</Table.Th>
                <Table.Th>Submitted At</Table.Th>
                <Table.Th>Timing</Table.Th>
                <Table.Th>Content / File</Table.Th>
                <Table.Th>Grading Status</Table.Th>
                <Table.Th>Score</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {submissions.map((sub) => {
                const grade = gradeMap.get(sub.id);
                const isReleased = Boolean(grade && !grade.is_draft && grade.released_at);
                const isDraft = Boolean(grade && grade.is_draft);

                return (
                  <Table.Tr key={sub.id}>
                    <Table.Td>
                      <Text fw={600}>Student #{sub.student_user_id}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="outline">v{sub.version}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{new Date(sub.submitted_at).toLocaleString()}</Text>
                    </Table.Td>
                    <Table.Td>
                      {sub.status === "late" ? (
                        <Badge color="red" variant="filled">Late</Badge>
                      ) : (
                        <Badge color="green" variant="light">On Time</Badge>
                      )}
                    </Table.Td>
                    <Table.Td>
                      {sub.file_storage_key ? (
                        <Anchor
                          href={getFileDownloadUrl(sub.file_storage_key)}
                          target="_blank"
                          size="sm"
                        >
                          Download File
                        </Anchor>
                      ) : sub.link_url ? (
                        <Anchor href={sub.link_url} target="_blank" size="sm">
                          Link
                        </Anchor>
                      ) : sub.content_text ? (
                        <Text size="sm" lineClamp={1}>
                          {sub.content_text}
                        </Text>
                      ) : (
                        <Text size="sm" c="dimmed">—</Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      {isReleased ? (
                        <Badge color="green" variant="filled">Released by Faculty</Badge>
                      ) : isDraft ? (
                        <Badge color="yellow" variant="filled">Draft Recorded</Badge>
                      ) : (
                        <Badge color="gray" variant="light">Pending Draft</Badge>
                      )}
                    </Table.Td>
                    <Table.Td>
                      {grade ? (
                        <Text fw={600}>
                          {grade.points_awarded} / {currentAssignment?.points_possible}
                        </Text>
                      ) : (
                        <Text c="dimmed">—</Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        variant={grade ? "light" : "filled"}
                        onClick={() => setSelectedSubmission(sub)}
                      >
                        {grade ? "Edit Draft" : "Draft Evaluation"}
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {selectedSubmission && currentAssignment && (
        <GradingModal
          opened={Boolean(selectedSubmission)}
          onClose={() => setSelectedSubmission(null)}
          submission={selectedSubmission}
          assignment={currentAssignment}
          userRole="ta"
        />
      )}
    </Stack>
  );
};

export default TaGradingDashboardPage;
